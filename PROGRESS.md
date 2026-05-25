# PROGRESS — zotero-mcp
_Updated: 2026-05-25_

## 背景

2026-05-25 方向转向:不再从零自建,改为 fork `54yyyu/zotero-mcp`(基底 = upstream v0.4.1)
在其上裁剪 + 扩展。remote `origin` 已改为 `https://github.com/KaiyunGuo/zotero-mcp.git`。
决策对账见 `CLAUDE.md`。

## Tasks
- [x] **TASK-001** 关闭语义搜索入口 — 注释掉 MCP 工具注册、search.py 级联兜底、CLI 子命令、_app 启动后台更新,使语义功能完全不可达;独立模块 `semantic_search.py`/`chroma_client.py` 原样留作参考。验证:52 工具注册、0 语义工具、CLI 拒绝 `db`/`--mode semantic`。
  - 入口清单:`tools/search.py`(3 个 `@mcp.tool` + Strategy 4 级联)、`_app.py`(后台更新 task + 未用的 asyncio 标 noqa)、`cli_standalone.py`(`db` 子命令 + `--mode semantic` + `_CMD_MAP`)、`cli.py`(`update-db`/`db-status`/`db-inspect` 子命令注册)
  - 未动:`setup` 向导的语义配置步骤(setup_helper/updater,纯安装时一次性);各处 dispatch 函数体/dead-elif 作休眠死代码保留
  `ee14d8a` feat: 关闭语义搜索入口 (TASK-001)

- [x] **TASK-002** Markdown 笔记写回 — 给 `create_note`/`update_note` 加 `content_format="markdown"`(默认),用 Python-Markdown(extra+sane_lists)把笔记体 markdown→HTML 后再写入 Zotero(原 D13)。raw HTML 透传。新增 `_markdown_to_html` 助手 + `markdown>=3.4` 依赖。验证:5 转换用例 + 15 个既有 note 测试通过 + **hybrid 端到端冒烟通过**(真实库建 markdown 子笔记→读回确认 parentItem 正确、h1/h2/ul/li/strong/a/code 渲染正确→永久删除不留痕)。
  `08159f1` feat: 笔记支持 markdown 写回 (TASK-002)
- [x] **TASK-003** 按论文名入库流程 — Yun 定为 **skill/prompt 约定,不动代码**(保持 D11)。写了项目 skill `.claude/skills/use-zotero-mcp/SKILL.md`:name→DOI 由 LLM 解析(WebSearch/WebFetch/PubMed)→ add_by_doi;歧义停下问、重复 surface;笔记 markdown 写回;写操作需 hybrid。skill 已纳入版本控制(`.gitignore` 改为 `.claude/*` + `!.claude/skills/`,其余 .claude 仍忽略;CLAUDE.md 保持忽略)。偏离 writing-skills 的 subagent baseline 测试(项目约定型 skill + Yun 禁止擅自 spawn subagent)。

## 关键 spike 结论(2026-05-25,Zotero v9 实测)
- **Zotero local `/api/` 只读**:POST 创建=400「Endpoint does not support method」;PATCH/DELETE=501「Method not implemented」。所有写操作必须走 web API 或 connector。
- **connector `/saveItems` 忽略 `parentItem`**:local-only 只能建独立笔记,挂不到论文下。
- **Find Available PDF 无 local API 端点**(findAvailable 全 404):D12 收尾——放弃换 Zotero 自带,**保留外置 OA 级联**。
- **决策 D4 修正**:`local only` → **hybrid(local 读 + web API 写)**。Yun 库已登录账号、data sync 走 Zotero、文件 sync 走 WebDAV,hybrid 可行。子笔记/改元数据均走 web API。

- [x] **TASK-004** 部署 fork 为 zotero MCP(hybrid 注册) — `uv tool install --editable D:\Claude\zotero-mcp`(入口 `C:\Users\yun\.local\bin\{zotero-mcp,zotero-cli}.exe`,v0.4.1);`~/.claude.json` 的 `zotero` 注册改指向新 exe + 加 hybrid env(`ZOTERO_LOCAL/LIBRARY_TYPE/LIBRARY_ID/API_KEY`);配置已备份 `~/.claude.json.bak-20260525-140725`。验证:exe `version` + `zotero-cli search` 读真实库 OK。
  (~/.claude.json 在仓库外,无 commit)
  - **待办**:① 重启 Claude Code 新 server 才生效;② 旧包 `zotero-mcp-server 0.3.0` 因 exe 运行中没卸成(WinError 32),重启后再 `py -3.11 -m pip uninstall zotero-mcp-server`;③ PATH 上新旧 exe 并存(`.local\bin` 与 `AppData\Roaming\...`),卸旧后消歧义。

## 待办 / 决策悬置
- **hybrid 配置**:联调子笔记前需 Yun 提供 `ZOTERO_API_KEY` + `ZOTERO_LIBRARY_ID`(+`LIBRARY_TYPE`);文件走已配的 WebDAV(`ZOTERO_WEBDAV_*`)。
- **Local API only(D4)**:已改 hybrid;web/hybrid/WebDAV 代码保留(现在是必需,不再考虑删)。
- **CLAUDE.md 未纳入版本控制**:被 upstream `.gitignore` 忽略,内容已更新但仅在本地。是否 force-add 待 Yun 定。
