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

## 待办 / 决策悬置
- **find_pdf(原 D12)**:现有 `add_by_doi` 用外置 OA 级联;Yun 倾向 Zotero 自带 find_pdf 更稳。需 spike 验证"Zotero 自带 Find Available PDF 是否经 local API(23119)可达"后再定。
- **Local API only(D4)**:当前以配置锁死;web/hybrid/WebDAV 代码暂留。是否物理删除待定。
- **CLAUDE.md 未纳入版本控制**:被 upstream `.gitignore` 忽略,内容已更新但仅在本地。是否 force-add 待 Yun 定。
