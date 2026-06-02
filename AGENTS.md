# AGENTS.md — zotero-mcp

**Project:** 基于 `54yyyu/zotero-mcp` fork 演进的 Zotero MCP server(Python)
**Role:** 维护者 = Yun(一人长期演进)
**Status:** 已引入 upstream v0.4.1 代码,开始按 Yun 工作流改造。**进度见 `PROGRESS.md`。**

## 这个项目是什么

做一个完全掌控、贴合 Yun 文献工作流的 Zotero MCP server。
核心工作流:按论文名检索 → 入库 Zotero → 抽取全文 → 把阅读笔记写回 Zotero 条目(UI 中可见)。

**方向(2026-05-25 转向):** 不再从零自建。改为 fork 现有成熟项目 `54yyyu/zotero-mcp`,
以它的框架/代码模式为参考,在其上**裁剪 + 添加我们需要的功能**。原"从零自建"设计
(`DESIGN.html` / `HANDOFF.md` / `.docs/plans/...spec.md`)降级为**历史参考**,不再是实现蓝本。

## 关键约束(不可违背)

1. **以实现 Yun 构思为主** — 现有代码是脚手架与模式参考,不是要照单全收。
2. **Local API only** — Yun 只用 local。当前以配置锁死(`ZOTERO_LOCAL=true`);现有的
   web/hybrid/WebDAV 代码暂**保留不删**(沿用其模式),除非另有决定。
3. **无语义搜索** — semantic search 全部功能不需要。入口已注释关闭(见 PROGRESS TASK-001)。
4. **Python** — 遵循 `~/.Codex/rules/coding.md`(snake_case、NumPy docstrings、按职责分文件、无过早抽象)。
5. **沿用现有返回风格** — 工具返回 **markdown 字符串**(非 dict)。先沿用,不改造。

## 现有架构形态(实际代码)

- 分层:`server.py`(注册) + `tools/*.py`(retrieval/search/write/annotations/read_pdf/connectors/scite)
  → `client.py`(连接/锁/HTTP) → `pyzotero`(传输层)
- 工具返回 markdown 字符串给 LLM 读
- citekey:`better_bibtex_client.py` + `search_by_citation_key`(Extra 兜底)
- PDF 抓取:`add_by_doi` 内嵌外置 OA 级联(Unpaywall/arXiv/Semantic Scholar/PMC)

## 决策对账(相对原 DESIGN.html D1–D22)

| 原决策 | 新状态 |
|---|---|
| D1 从零自建 | ❌ **反转** — 基于 fork 扩展 |
| D4 Local API only | ✅ 保留意图;实现=配置锁死,代码暂留多模式 |
| D7 返回 dict / 无 models.py | ⚠ **改为沿用现有 markdown-string** |
| D12 `find_pdf` 独立关键路径 | ⏸ 现有用外置级联;"Zotero 自带 find_pdf 是否经 local API 可达"=**待 spike** |
| D13 笔记 markdown/HTML 双路 | ⏸ 先保留现有 note 代码不动 |
| D14 合一 `set_tags(mode=)` | ❌ **弃用** — 采纳现有 `batch_update_tags` + `update_item`(更强) |
| D19 不建 mock HTTP | ⚠ 现有重度 mock(294 单测);新增测试遵循"不建 mock"意图 |
| 无语义搜索 | ✅ 已关入口(TASK-001) |

## 文档地图

| 文件 | 作用 |
|---|---|
| `PROGRESS.md` | **编码任务追踪。新 session 先读这个** |
| `AGENTS.md` | 本文件 |
| `DESIGN.html` / `HANDOFF.md` / `.docs/plans/*spec.md` | 原从零设计,**历史参考**(已被上表覆盖之处以本文件为准) |
| `README.md` / `docs/` | upstream 原始文档 |

> 仓库:`main` 分支,remote `origin` = `https://github.com/KaiyunGuo/zotero-mcp.git`
> (fork of `54yyyu/zotero-mcp`,基底 commit = upstream v0.4.1)。

## 工作规范

- 与 Yun 协作时每次回复用「Yun」称呼。
- 不确定的设计决策先问,不自作主张。第一性原理思考:目标/动机不清就停下来讨论;路径不是最短就建议更好的。
- Minimal diff:只改任务要求的部分。删/改大块前先看清,与描述不符就先反映。
- 按 `~/.Codex/rules/coding-progress.md` 用 `PROGRESS.md` 追踪每个编码任务;git commit message 精简,细节进 PROGRESS.md。
- 涉及库/框架/API 用法时用 Context7 MCP 查最新文档。
- **skill 单一来源**:规范源 = `skills/use-zotero-mcp/SKILL.md`(Claude Code plugin);改 skill **必须同步** `.agents/skills/use-zotero-mcp/SKILL.md`(本文件机制 = Codex 读)两处字节一致。Codex 不装 plugin,仅靠仓库内 `.agents/` 副本。

