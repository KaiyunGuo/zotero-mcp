# zotero-mcp — Spec

_Date: 2026-05-19 · Status: draft, awaiting Yun review_
_Authoritative design: `D:\Claude\zotero-mcp\DESIGN.html` (设计第 1–6 段全部 approved)_

本 spec 是 `DESIGN.html` 的浓缩版，用作 `superpowers:writing-plans` skill 的输入。设计动机、方案对比、详细叙述见原文。

---

## 1. 目标

从零自建一个 **Local-API-only 的 Zotero MCP server**(Python)，替代功能受限的第三方包 `zotero-mcp-server` 0.3.0。Yun 一人长期演进，按自己的文献工作流。

**核心工作流**：按论文名检索 → 入库 Zotero → 抽取全文 → 把阅读笔记写回 Zotero 条目(UI 中可见)。

## 2. 范围 (v1)

| Bundle | 工具数 | 内容 |
|---|---|---|
| 检索 / 元数据 / 全文 | 6 | search, search_by_citekey, get_item, get_children, get_fulltext, get_recent |
| 入库 / 元数据更新 | 4 | add_by_doi, add_by_url, add_from_file, update_item |
| 笔记 | 4 | create_note, update_note, get_notes, delete_note |
| 组织 | 7 | list_collections, create_collection, add_to_collection, remove_from_collection, list_tags, set_tags, get_annotations |
| 实验性 | 1 | find_pdf ⭐ |
| **总计** | **22** | |

**out-of-scope**：semantic search；`add_by_name`(title→DOI 由 LLM WebFetch 完成，见 D11)；auto-merge 重复条目(D15)；Zotero <7.0 兼容(D17 硬抛错)。

## 3. 已锁定的决策 (22 条)

| # | 决策 |
|---|---|
| D1 | 从零自建，不修补现有包 |
| D2 | 语言 = Python(3.11+) |
| D3 | 独立仓库 `D:\Claude\zotero-mcp\` |
| D4 | **Local API only**(不碰 SQLite，不用 Web API) |
| D5 | v1 范围 = 4 个能力包 + Find Available PDF |
| D6 | 架构分层：`server.py` → `client.py` → pyzotero(仅传输层) |
| D7 | 不引入 `models.py` 数据类；`client.py` 直接返回 dict |
| D8 | 配置极简：仅可选 Local API base URL |
| D9 | 替换 `~/.claude.json` 全局 `zotero` 注册(**Yun 手动**) |
| D10 | citekey 支持 = BBT 软依赖；启动探测一次缓存 capability flag |
| D11 | `add_by_name` 不进 MCP；title→DOI 由 LLM WebFetch 完成 |
| D12 | `find_pdf` = 关键路径；`add_by_doi/url` 默认 `find_pdf_fallback=True` 兜底 |
| D13 | 笔记 I/O = markdown 与 HTML 双路(`content_format` 参数) |
| D14 | tag 操作 = 合一 `zotero_set_tags(mode="add"/"remove"/"replace")` |
| D15 | 重复条目 = surface 不 auto-merge；检测优先级 DOI > URL > 标题模糊(阈值 0.85) |
| D16 | 元数据更新 = `zotero_update_item(mode="merge")`，仅 merge |
| D17 | Zotero 版本门：`version < 7.0` 时写工具硬抛 `ZoteroVersionError` |
| D18 | 日志默认 = WARNING(stderr)；stdout 严禁写日志 |
| D19 | 测试 = 两层(unit + live integration)；不建 mock HTTP fixture 层；error-path 测试允许 inline 用 `responses` |
| D20 | 测试隔离 = dedicated collection `__zotero_mcp_test__` + `__test__` tag + teardown |
| D21 | TDD 姿态混合：纯逻辑严格 / `client.py` 伴随 / `server.py` 滞后到 e2e |
| D22 | v1 不上 CI；本地 git pre-commit hook 跑 `pytest tests/unit/` |

## 4. 架构

```
MCP client (Claude Code)
      │  stdio
      ▼
server.py        ← FastMCP，定义 22 个工具，工具体极薄(参数校验 + 委派)
      ▼
client.py        ← ZoteroClient：把 Zotero Local API 包装成领域方法
      ▼
pyzotero (local=True)  ← 仅作传输层(分页、userID-0、HTTP 重试)
      ▼
Zotero Local API   http://localhost:23119/api/

      [可选旁路]  BBT JSON-RPC   http://localhost:23119/better-bibtex/json-rpc
```

### 模块文件

| 文件 | 职责 |
|---|---|
| `pyproject.toml` | 打包 + console-script 入口 `zotero-mcp` |
| `zotero_mcp/server.py` | MCP 工具定义(薄) |
| `zotero_mcp/client.py` | `ZoteroClient` —— Local API 的领域封装 |
| `zotero_mcp/formatting.py` | JSON↔markdown 渲染 + 笔记 md↔html 转换 |
| `zotero_mcp/config.py` | env 驱动：base URL、超时、全文页数上限 |
| `zotero_mcp/errors.py` | 错误类型 + 预检 + capability 探测 |
| `tests/` | pytest(unit + integration + fixtures) |

## 5. 工具签名(摘录关键)

**Bundle 1 · 检索 / 元数据 / 全文**
- `zotero_search(query, qmode="titleCreatorYear", item_type=None, tag=None, collection_key=None, limit=10)`
- `zotero_search_by_citekey(citekey)` — 需 BBT
- `zotero_get_item(item_key, include_abstract=True)` — `item_key` 接受 Zotero key 或 citekey
- `zotero_get_children(item_key)`
- `zotero_get_fulltext(item_key, max_pages=None)` — 自动找 PDF 附件
- `zotero_get_recent(limit=10)`

**Bundle 2 · 入库 / 更新**
- `zotero_add_by_doi(doi, attach_pdf=True, find_pdf_fallback=True, force=False, collection_key=None)`
- `zotero_add_by_url(url, attach_pdf=True, find_pdf_fallback=True, force=False, collection_key=None)`
- `zotero_add_from_file(file_path, item_type="document", title=None, force=False)`
- `zotero_update_item(item_key, fields, mode="merge")`

**Bundle 3 · 笔记**
- `zotero_create_note(parent_item_key, content, title=None, tags=None, content_format="markdown")`
- `zotero_update_note(note_key, content, title=None, content_format="markdown")`
- `zotero_get_notes(item_key, format="markdown")`
- `zotero_delete_note(note_key)`

**Bundle 4 · 组织**
- `zotero_list_collections()`, `zotero_create_collection(name, parent_key=None)`
- `zotero_add_to_collection(item_key, collection_key)`, `zotero_remove_from_collection(item_key, collection_key)`
- `zotero_list_tags()`, `zotero_set_tags(item_key, tags, mode="add")`
- `zotero_get_annotations(item_key)`

**实验性**
- `zotero_find_pdf(item_key)` 🧪 — spike 优先级最高

### 统一返回形状(关键字段)

| 实体 | 字段 |
|---|---|
| Item | `{key, citekey?, type, title, creators, year, doi, url, abstract?, tags, collection_keys, attachment_keys}` |
| Note | `{key, parent_key, parent_citekey?, title, content_md, tags, date_modified}` |
| Annotation | `{key, parent_attachment_key, parent_citekey?, type, page, text, comment, color, date_modified}` |
| Collection | `{key, name, parent_key?, item_count}` |
| Duplicate result | `{added:false, reason:"duplicate_found", matched_by, duplicates:[Item...], hint}` |

## 6. 数据流(核心工作流)

```
Yun 说 "读 Tran 2019"
  → Claude WebFetch 拿 DOI                                  [LLM 边界，D11]
  → zotero_add_by_doi(doi)
        ├─ 查重 DOI                                          [D15]
        ├─ POST translator → 入库
        └─ 无 PDF → find_pdf 兜底                            [D12]
  → zotero_get_fulltext(item_key)
  → LLM 起草 markdown 笔记
  → zotero_create_note(parent, md, content_format="markdown")
        └─ 内部 md → html
  → Zotero UI 看到子笔记 ✓
```

降级分支(都不阻塞工作流，详见 DESIGN.html §6)：Zotero 未运行、BBT 未装、查重命中、find_pdf 不可触发、全文未索引。

## 7. 错误处理

### 错误类型

```
ZoteroMCPError
├─ ZoteroNotRunningError
├─ ZoteroVersionError
├─ LocalAPIError {ItemNotFoundError, ValidationError, ServerError}
├─ TranslatorError
├─ BBTUnavailableError
└─ FindPDFNotSupportedError
```

### Return vs Raise 纪律

| 类 | 情况 |
|---|---|
| **Raise**(动作未完成) | Zotero 没开 / item 不存在 / 版本 <7.0 / 校验失败 / 5xx / BBT 必需但未装 |
| **Return**(动作完成，结果信息丰富) | 撞重复(D15)；find_pdf 没找到；全文未索引；BBT 未装时 citekey=null |

### 预检两层

- **启动预检**：一次性探测 ① Local API 可达 ② Zotero 版本 ③ BBT JSON-RPC ④ find_pdf；写入 `capabilities` 字典；写一行 stderr
- **每调用预检**：便宜的 HTTP ping；失败则重跑启动预检

### 日志

- stdout 留给 MCP JSON-RPC(绝不写日志到 stdout)
- 所有日志走 stderr，默认 WARNING
- env `ZOTERO_MCP_LOG=INFO/DEBUG` 切换

## 8. 测试策略

### 两层金字塔(D19)

| 层 | 位置 | 性质 | 速度 |
|---|---|---|---|
| unit | `tests/unit/` | 纯函数，无 Zotero | 全跑 <1s |
| live integration | `tests/integration/` | 真打 localhost:23119，每个工具 ≥1 smoke | 全跑数秒 |

**不建通用 mock HTTP fixture 层**。少数 error-path 测试允许 inline 用 `responses` 打补丁(网络超时 / 5xx / 畸形 JSON)。

### 隔离(D20)

共用日常 library，三层防护：
1. 测试创建的 item / note 进固定 collection `__zotero_mcp_test__`
2. 每个对象打 `__test__` tag
3. 用例 teardown；残留靠 tag 兜底批量清理

查询类测试断言加 collection / tag 过滤，避免日常库真数据干扰。

### TDD 姿态(D21)

| 文件 | 姿态 |
|---|---|
| `formatting.py` / `errors.py` / `config.py` | 严格 TDD |
| `client.py` | 测试伴随(每个方法 land 前 ≥1 integration smoke) |
| `server.py` | 滞后到 e2e |

### Capability gating

BBT / find_pdf 相关测试 `pytest.skip` 不可用的能力；探测逻辑与启动预检共用。

### CI(D22)

- v1 不配 GitHub Actions
- 本地 git pre-commit hook 跑 `pytest tests/unit/`
- integration 手动跑

### 目录

```
tests/
├── conftest.py
├── unit/ (test_formatting, test_errors, test_config, test_duplicates)
├── integration/ (test_search, test_add, test_notes, test_organize,
│                test_update_item, test_workflow_e2e)
└── fixtures/sample_items.py
```

## 9. Spike 排序

| Spike | 何时 | 通过判据 | 不通过 Plan B |
|---|---|---|---|
| 1 · `find_pdf` ⭐ | 写代码前最优先 | HTTP 一行让 Zotero ≤10s 抓回 PDF | `add_by_doi/url` 默认 `find_pdf_fallback=False`；`zotero_find_pdf` raise `FindPDFNotSupportedError`；**§6 数据流图删 find_pdf 兜底支** |
| 2 · pyzotero local 写 | 写 client.py 写方法前 | `create/update/delete_items` 走 local 返回 2xx | 写路径绕过 pyzotero，直接 `httpx`；读路径仍用 |
| 3 · BBT JSON-RPC 形状 | 与 #1 同批 | 从已知 citekey 拿回 Zotero key | `search_by_citekey` 走全库扫 + Python 过滤；或直接 raise 提示走 `zotero_search` |
| 4 · citekey 字段位置 | 与 #1 同批 | 锁定 JSON path | 启动时 BBT JSON-RPC 拉缓存反查 |
| 5 · 全文覆盖度 | integration 期(随 `get_fulltext` 自然验) | 已 indexed item 返回 text | 未 indexed → `{text:null, hint}` |
| 6 · `~/.claude.json` 替换 | impl 完成后 | Yun 手动操作成功 | README 提供精确片段 |

**关键路径执行**：Spike 1 + 3 + 4 一个 ~30 min throwaway 脚本一次性跑完(写 spec 之后、writing-plans 之前)。Spike 1 是唯一可能反向冲击设计的一项。

## 10. 环境事实

- Zotero 装在 `D:\Program Files\Zotero\`(data dir == install dir)
- Zotero 版本 = **v9**(远超 7.0 门；find_pdf 需查 v9 changelog 复核)
- 旧包：`zotero-mcp-server` 0.3.0 仍挂在 `~/.claude.json`，Yun 实现完成后手动替换(D9)
- Local API 端口 23119 确认可达；写支持需在 v9 上 spike 复测
- Python 3.11；BBT 安装状态未知(D10 软依赖兼容)
- 不要 semantic search

## 11. 仓库状态

- 已 `git init -b main`，remote `origin` = `https://github.com/KaiyunGuo/full_zotero_mcp.git`
- 尚无 commit，无代码文件
- 现有文档：`CLAUDE.md` / `DESIGN.html` / `HANDOFF.md` / `.docs/plans/2026-05-19-zotero-mcp-spec.md`(本文件)

## 12. Out of this spec

- 实现计划(任务分解、依赖、commit 边界)→ 由 `superpowers:writing-plans` skill 产出
- 代码任务追踪(TASK-XXX)→ 实现期建 `PROGRESS.md`，遵 Yun 的 coding-progress 协议
- 设计动机、方案对比(SQLite hybrid vs Web API 否决理由)、详细叙述 → 见 `DESIGN.html`
