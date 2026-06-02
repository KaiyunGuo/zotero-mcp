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

- [x] **TASK-004** 部署 fork 为 zotero MCP(hybrid 注册) — `uv tool install --editable D:\Claude\zotero-mcp`(入口 `C:\Users\yun\.local\bin\{zotero-mcp,zotero-cli}.exe`,v0.4.1);`~/.claude.json` 的 `zotero` 注册改指向新 exe + 加 hybrid env(`ZOTERO_LOCAL/LIBRARY_TYPE/LIBRARY_ID/API_KEY` + `ZOTERO_WEBDAV_URL/USERNAME/PASSWORD`,坚果云 dav.jianguoyun.com);配置已备份。验证:exe `version` + `zotero-cli search` 读真实库 OK + WebDAV PROPFIND 207(凭据有效)。笔记走 data sync、PDF 附件走 WebDAV。
  (~/.claude.json 在仓库外,无 commit)
  - **待办(已全部完成,见下「端到端实跑结论」)**:① 重启生效 ✅;② 卸旧包 ✅;③ PATH 消歧 ✅。

- [x] **TASK-005** OA PDF 上传走 WebDAV — `_download_and_attach_pdf`(_helpers.py)原用 pyzotero `attachment_both` 上传,落点 Zotero 云存储,WebDAV-storage 桌面取不到(根因见下「端到端实跑结论·新发现」)。修:`attachment_both` 后若 `is_webdav_configured()` 则 `upload_attachment_to_webdav(key, file)`(在 tempdir with 块内,文件未删),照搬 `add_from_file`(write.py:2088)working pattern。`_extract_attachment_key` 移入 `_helpers`(write.py 改引 `_helpers._extract_attachment_key`)。一处修复覆盖 add_by_doi/url/bibtex/csl_json 四入口。**TDD**:先写失败测试(test_pdf_cascade.py 加 `test_webdav_push_when_configured`/`_not_configured`)跑红→实现→30 项绿,全套无新增回归(test_add_from_file.py 2 失败为既有 os.path.isabs+Win/Py3.13 harness bug,stash 验证原 src 同样失败)。my src ruff 零错。
  `22c0f7a` fix: OA PDF 入库同步推送 WebDAV (TASK-005)
  - **live e2e 待重启**:当前 MCP server 进程内存里是旧 `_helpers`(editable 装不热重载运行中进程);重启 Claude Code 后用真实 OA 论文复跑 add_by_doi→确认 `<KEY>.zip` 落 WebDAV→get_item_fulltext 直接读 WebDAV 取回正文→清理。

## 端到端实跑结论(2026-05-25,重启后新 server)
- 新 server 生效:语义工具消失、`zotero_create_note` 在且 `content_format` 默认 markdown。
- 旧包 `zotero-mcp-server 0.3.0` 已卸(先杀 4 个残留旧进程 PID 36132/21456/14480/12756 释放 exe 锁);旧 exe 消失,`zotero-mcp` 解析到 `.local\bin`,PATH 歧义消除。
- 实跑链(测试条目 AlphaFold DOI 10.1038/s41586-021-03819-2,用完已 trash):
  - ✅ `add_by_doi` 入库,PDF 报 attached(source: Unpaywall)
  - ⚠ `get_item_fulltext`:元数据+摘要 OK,但 **PDF 正文取不到** — 本地 storage 404 + WebDAV「Attachment 3TUC98C9 not found」
  - ✅ `create_note` markdown 子笔记:parentItem 正确,h1/h2/h3/strong/em/ul/ol/code/a/table 全部渲染正确(raw_html 读回确认)
- **新发现(待 spike)**:add_by_doi 经 web API 上传 PDF → 落点疑为 **Zotero 云存储**;Yun 桌面文件 sync 走 **WebDAV** → 两者不相交,MCP 传的 PDF 可能既不进 WebDAV、桌面也同步不下来。get_item_fulltext 只查 local+WebDAV 故取不到。需确认是**同步时序**还是**上传路径结构错配**;前者等桌面 sync 后重试即可,后者需改 add_by_doi 上传走 WebDAV 或改用 Zotero 云存储配额。

- [x] **TASK-006** 附件挂现有条目(HTML 渲染笔记) — 新增 `zotero_add_attachment(item_key, file_path, title=None)`:把任意本地文件作 imported_file 附件挂到**现有条目**,复用 `attachment_both` + WebDAV(照搬 add_from_file 上传块)。动机:笔记 HTML 被 Zotero 净化(无 JS→MathJax 死),自包含 .html **附件**不净化、浏览器打开完美渲染公式/代码。补上「附件挂现有条目」这个先前缺口(add_from_file 只能新建条目;无任意扩展名)。无扩展名白名单、校验父条目存在、symlink/相对路径/缺文件均拒绝。`server.py` 注册新工具。**TDD**:test_add_attachment.py 11 项绿(happy/title 覆盖/任意扩展名/WebDAV 配/未配/失败 surface/4 校验路径)。test_pdf_cascade 全绿;test_add_from_file 2 失败为既有 Win/Py3.13 harness bug(非回归)。源文件 ruff 零错。
  - **live e2e 待重启**:运行中 MCP server 内存是旧代码(editable 不热重载);重启后用真实条目跑 `zotero_add_attachment(item_key, 自包含 .html)`→确认 Zotero UI 见附件 + 浏览器打开 MathJax/高亮渲染 + `<KEY>.zip` 落 WebDAV。
  - **MathJax caveat**:若 HTML 用 CDN 外链 MathJax,打开时仍需联网;要离线完美需内联 MathJax JS(工具不关心,生成端注意)。
  `7c5e4f0` feat: zotero_add_attachment 挂文件到现有条目 (TASK-006)

- [x] **TASK-007** 仓库做成 Claude Code plugin(只打包 skill,跨项目复用) — 本仓同时充当 plugin + marketplace:`.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json`(name=zotero-mcp,plugin source=`./`,省略 version→每 commit 即新版)。skill 规范源迁至 `skills/use-zotero-mcp/SKILL.md`(原 `.claude/skills/` 项目级副本已删,避免遮蔽 plugin)。MCP 维持全局注册(plugin 不含 .mcp.json,密钥零暴露)。Codex 侧不装 plugin,靠仓库 `.agents/skills/` 副本,须与 plugin 版字节一致(规则写入 CLAUDE.md/AGENTS.md)。安装:`/plugin marketplace add KaiyunGuo/zotero-mcp` → `/plugin install zotero-mcp@zotero-mcp`,更新=`/plugin marketplace update zotero-mcp`。调用 `/zotero-mcp:use-zotero-mcp`。CLAUDE.md 本地 gitignore 未入库(仅 AGENTS.md 带 sync 规则)。
  `22a551a` feat: 仓库做成 Claude Code plugin 打包 skill (TASK-007)

## 测试基线(2026-05-25,Yun 决策)
全套 `uv run --extra dev pytest -p no:cacheprovider` 基线 = **14 failed + 20 errors + 778 passed**。这 14+20 是**预期既有失败,不修、不重复排查**(Yun 定):
- semantic 悬空测试(`test_description_tokens.py` 全 errors、`test_cli_standalone.py`/`test_lifespan.py`/`test_search_improvements.py` 的 semantic 项)= TASK-001 停语义遗留,语义功能不需要。
- path 校验测试(`test_add_by_bibtex/csl_json` rejects_*、`test_local_db` absolute_path、`test_add_from_file` 2 项)= `os.path` monkeypatch 在 Win+Py3.13 的 harness bug。
- 判回归只看**增量**(TASK-005 加了 +2 passed,无新失败)。

## 合并(2026-05-25)
分支 `rework/local-only-no-semantic`(TASK-001~005)已 **FF 合并回 main** 并 `git push origin main`(`55d43bb..f73b727`);本地特性分支已删。

## 待办 / 决策悬置
- **PDF 上传落点 spike** 已落地为 TASK-005;**live e2e 待重启**(见 TASK-005)。
- **独立 find_pdf 工具**:按 Yun 意延后(OA 级联已内嵌 add_by_doi);需要可补(给已入库缺 PDF 的条目补抓)。
- **Local API only(D4)**:已改 hybrid;web/hybrid/WebDAV 代码保留(现在是必需,不再考虑删)。
- **CLAUDE.md 未纳入版本控制**:被 upstream `.gitignore` 忽略,内容已更新但仅在本地。是否 force-add 待 Yun 定。
