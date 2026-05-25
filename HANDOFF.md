# HANDOFF — zotero-mcp

> ⚠ **2026-05-25 方向转向:本文件已降级为历史参考。**
> 项目不再从零自建,改为 fork `54yyyu/zotero-mcp` 在其上裁剪 + 扩展。
> **当前事实来源 = `CLAUDE.md`(决策对账)+ `PROGRESS.md`(任务进度)。**
> 下方内容是原"从零自建"brainstorming 阶段的记录,D1/D7/D12/D13/D14/D19 等已被 CLAUDE.md 覆盖。

_Last checkpoint: 2026-05-19 · `superpowers:brainstorming` 接近收尾 · **22 条决策已锁定** · 设计第 1–6 段全部 approved · **spec 已写,待 Yun 评审**_

这份文档让新 Claude Code session 能冷启动接手。配套文件:`DESIGN.html`(设计本体)、`CLAUDE.md`(项目指令)。

---

## 这个项目是什么

从零自建一个 **Local-API-only 的 Zotero MCP server**(Python),替代现有受限的第三方包 `zotero-mcp-server`。
Yun 要完全掌控代码库,按自己的文献工作流长期演进。核心工作流:
按论文名检索 → 入库 Zotero → 抽取全文 → 把阅读笔记写回 Zotero 条目(UI 中可见)。

---

## 当前进度

正在走 `superpowers:brainstorming` 流程(把想法打磨成设计 → spec → 实现计划)。

| 阶段 | 状态 |
|---|---|
| 探索项目上下文 | ✅ 完成 |
| 澄清提问(动机/语言/仓库/范围) | ✅ 完成 |
| 方案对比(3 方案,选定 Local API only) | ✅ 完成 |
| 设计第 1 段:架构与模块划分 | ✅ **approved (2026-05-14)** |
| 设计第 2 段:工具清单 | ✅ **approved (2026-05-14)** |
| 设计第 3 段:数据流 | ✅ **approved (2026-05-15)** |
| 设计第 4 段:错误处理 | ✅ **approved (2026-05-15)** |
| 设计第 5 段:测试策略 | ✅ **approved (2026-05-19)** |
| 设计第 6 段:风险细化 | ✅ **approved (2026-05-19)** |
| 写 spec 文档 + 自检 | ✅ **完成 (2026-05-19)** — 见 `.docs/plans/2026-05-19-zotero-mcp-spec.md` |
| **Yun 评审 spec** | 🔄 **下一步** |
| Spike 1+3+4 (throwaway 脚本) | ⬜ 时机待定(Q7 留作下次,见下) |
| 转入 `writing-plans` skill 出实现计划 | ⬜ 待 |

> ⚠ 还没写任何代码。brainstorming 的 HARD-GATE:设计未全部呈现并经 Yun 批准前,不写代码、不 scaffold。

---

## 决策日志(已锁定)

| # | 决策 | 一句话理由 |
|---|---|---|
| D1 | 从零自建,不修补现有包 | 要完全掌控、长期演进 |
| D2 | 语言 = Python | Yun 母语言;MCP Python SDK(FastMCP)成熟;现有包亦 Python 可参考 |
| D3 | 独立仓库 `D:\Claude\zotero-mcp\` | 是工具不是研究内容,该有独立 git 历史 |
| D4 | 连接通道 = **Local API only** | 单路径;消灭 SQLite 路径探测+schema 解析的 bug 类;子笔记原生支持,无需 Web API key |
| D5 | v1 范围 = 全部 4 个能力包 + Find Available PDF | ①检索/元数据/全文 ②入库 ③笔记读写(含子笔记) ④组织:集合/标签/批注 |
| D6 | 架构分层 server.py → client.py → pyzotero | 工具体薄;领域逻辑集中在 ZoteroClient;pyzotero 仅作传输层 |
| D7 | v1 不引入 models.py 数据类 | 数据形状没复杂到需要;client.py 直接返回规整 dict;No premature abstractions |
| D8 | 配置极简:仅可选 Local API base URL | 无 DB 路径、无 API key;砍配置 = 砍 bug |
| D9 | 替换 `~/.claude.json` 全局 `zotero` 注册 | 全局可用;**此编辑需 Yun 手动做**(在 Claude 可写范围外) |
| D10 | citekey 支持 = **BBT 软依赖** | 读 citekey 走 Local API 的 `data.citationKey`(BBT 没装就是 null);`search_by_citekey` 需 BBT,无 BBT 时返回明确错误。启动探测一次并缓存能力 flag |
| D11 | `add_by_name` 不进 MCP;title→DOI 由 LLM WebFetch 完成 | MCP 只做 Zotero 边界内的事;砍掉 CrossRef 依赖。约定写进 `use-zotero-mcp` skill prompt |
| D12 | `find_pdf` = **关键路径** | `add_by_doi/url` 默认 `find_pdf_fallback=True` 兜底;`find_pdf` 的 spike 优先级最高 |
| D13 | 笔记 I/O = **markdown 与 HTML 双路** | `content_format="markdown"`(默认)/`"html"`;读笔记同 |
| D14 | tag 操作 = **合一** `zotero_set_tags(mode=...)` | `mode = "add" / "remove" / "replace"` |
| D15 | 重复条目处理 = **surface,不 auto-merge** | `add_by_*` 加 `force=False` 默认;命中重复退回 `{added:false, duplicates:[...]}` 不入库。检测信号优先级 DOI > URL > 标题模糊(`add_from_file` 兜底,阈值 0.85) |
| D16 | 元数据更新 = **narrow patch 工具** `zotero_update_item` | 仅 `mode="merge"`(v1 不上 replace);LLM 自己 WebFetch 拿新元数据后调用,与 D11 一脉相承(MCP 只做 Zotero 写) |
| D17 | Zotero 版本门 = **硬抛错** | 启动读到 `version < 7.0` → 调写工具直接 `raise ZoteroVersionError`,无宽容模式。本机 v9 永远触发不到,保留作未来兜底 |
| D18 | 日志默认 = **WARNING**(stderr) | env `ZOTERO_MCP_LOG=INFO/DEBUG` 切换。stdout 严禁写日志(留给 MCP JSON-RPC) |
| D19 | 测试 = **两层金字塔**(unit + live integration);**不建 mock HTTP fixture 层** | 单用户、Zotero 永远在跑;mock 漂移代价 > 测试快收益。允许个别 error-path 测试 inline 用 `responses` 打补丁(网络超时/5xx/畸形 JSON),不抽公共 fixture |
| D20 | 测试隔离 = **dedicated collection** `__zotero_mcp_test__` + `__test__` tag + teardown | 共用日常 library;不上专用 Zotero profile(YAGNI;profile 漂移反而掩盖真实 bug) |
| D21 | TDD 姿态 = **混合**(纯逻辑严格 / client.py 伴随 / server.py 滞后到 e2e) | 按文件性质分;纯函数零摩擦严格 TDD,client.py 严格 TDD 会被 Zotero 状态拖死,server.py 薄壳 e2e 更划算 |
| D22 | v1 **不上 CI**;本地 git **pre-commit hook** 跑 `pytest tests/unit/` | 单用户私库,CI 协作把关价值不存在;pre-commit 比 CI 早一步拦截倒退 |

**v1 工具总数**:6 + 4 + 4 + 7 + 1 = **22**(详见 `DESIGN.html` §5)

被否决的:方案 A(Hybrid SQLite+Local API)、方案 C(Web API)。理由见 `DESIGN.html` §3。

---

## 风险与未知

完整 6 项细化见 `DESIGN.html` §11(已 approved)。每项均含"何时 · 验什么 · 通过判据 · Plan B"。关键路径:

1. **Spike 1 — `find_pdf` 可行性 ⭐**:写 spec 前最优先,30 min throwaway 脚本搞定;不过则 §6 数据流改一笔
2. **Spike 2 — pyzotero local 写支持**:写 client.py 写方法前 gate
3. **Spike 3 / 4 / 5 / Item 6**:实现层微调或流程项,接口不变

---

## 环境事实

- Zotero 安装在 `D:\Program Files\Zotero\`(data dir == install dir)
- **Zotero 版本:v9**(2026-05-15 更新)。可能影响 spike 假设——v9 是否暴露了 find_pdf 等客户端动作的 API 端点需在 spike #1 时查 changelog。Local API 写支持在 v9 上几乎确定可用,但仍需在 v9 上冒烟复测
- 旧包:`zotero-mcp-server` 0.3.0,exe 在 `C:\Users\yun\AppData\Roaming\Python\Python311\Scripts\zotero-mcp.exe`,注册在 `~/.claude.json` 带 `ZOTERO_LOCAL=true`
- 本机 Local API(端口 23119)确认可达;Local API 写操作经旧包在更早 Zotero 版本确认可用
- Yun 不要 semantic search
- Python 3.11(见上述 Scripts 路径)

---

## 待定项 (Q7 — 留给下次)

**Spike 1+3+4 throwaway 脚本何时跑？** 三选一(上一 session 已铺好题面,Yun "下次再说"):

- **A. 先 spike 再 writing-plans**:spike 结果回炉锁死设计 → plan 不会因 spike 失败而返工。代价 = plan 阶段被 spike 阻塞 ~30 min
- **B. 先 writing-plans 后 spike**:plan 假设 Spike 1 通过;通不过则 plan patch 一版。好处 = 不阻塞 plan,但可能返工
- **C. 并行**:plan 写 + spike 跑(可交给 Yun 或我跑脚本)

下次 resume 时应优先把这一抉择拿到。

---

## 如何 resume(给新 session 的指引)

1. 读 `CLAUDE.md`、`DESIGN.html`(完整设计本体,第 1–6 段全部 approved)、`.docs/plans/2026-05-19-zotero-mcp-spec.md`(spec)、本文件。
2. 重新进入 `superpowers:brainstorming` skill —— 处于 "User reviews written spec" 这一 gate。
3. **下一步:请 Yun 评审 spec** —— `D:\Claude\zotero-mcp\.docs\plans\2026-05-19-zotero-mcp-spec.md`。spec 是 DESIGN.html 的 markdown 浓缩版(D1–D22 + 工具表 + 数据流 + 测试 + spike 排序),供 `writing-plans` 消化。
4. Yun 评审反馈:
   - 接受 → 把 Q7(spike 时机)拿到答案,然后按选择跑 spike / 或直接转 `superpowers:writing-plans`
   - 要改 → 修 spec,重做自检,再请评审
5. 真正写代码前:仓库已 `git init`(`main` 分支,remote = `KaiyunGuo/full_zotero_mcp`,尚无 commit);按 Yun 的 coding-progress 协议建正式 `PROGRESS.md`(任务追踪格式,与本 HANDOFF 不同)。

> ⚠ Spike 1 是唯一可能反向冲击设计的项:不过会让 spec §6 数据流改一笔(去 find_pdf 兜底支)+ §9 spike 表的 Plan B 落地。其余 spike 不通过都是实现层微调,接口和工具清单不变。
