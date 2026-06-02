# zotero-mcp (Yun fork)

贴合 **Yun 个人文献工作流**的 Zotero MCP server。基于 [`54yyyu/zotero-mcp`](https://github.com/54yyyu/zotero-mcp) v0.4.1 演进，按需裁剪 + 扩展。

> 一个人长期维护。设计/进度以 **`PROGRESS.md`** 与 **`CLAUDE.md`** 为准，本 README 只讲「怎么装、怎么用、怎么更新」。

核心工作流：**按论文名检索 → 入库 Zotero → 抽取全文 → 把阅读笔记 / 渲染好的 HTML 写回条目（Zotero UI 可见、随库同步）。**

---

## 这个 fork 和 upstream 的区别

| 方面 | 本 fork |
|---|---|
| 语义搜索 | **已关闭**（代码层注释掉入口，无 ChromaDB / 向量库依赖） |
| 连接模式 | **hybrid**：local API 读 + web API 写；附件文件走 **WebDAV**（坚果云） |
| 安装方式 | 从本仓 **editable 安装**（不走 PyPI 包） |
| 笔记写回 | `zotero_create_note` 默认 **markdown**（自动转 HTML 入库） |
| 富渲染笔记 | 新增 `zotero_add_attachment` —— 把自包含 .html（MathJax/代码高亮）挂到现有条目，浏览器打开完美渲染（note 会被净化，附件不会） |
| OA PDF | `add_by_doi` 内嵌 OA 级联（Unpaywall/arXiv/Semantic Scholar/PMC），命中后**同步推送 WebDAV** |
| 返回风格 | 工具返回 **markdown 字符串**（非 dict） |
| skill 复用 | 本仓同时是 **Claude Code plugin + marketplace**，跨项目装一次即可用（见下） |

---

## 一、安装 MCP server

### 前置
- **Python 3.10+**、**[uv](https://docs.astral.sh/uv/)**
- **Zotero 7+**，并在 `设置 → 高级 → 允许其它应用与 Zotero 通信` 打开本地 API
- 写操作 / WebDAV 需要：Zotero 账号已登录、data sync 走 Zotero、文件 sync 走 WebDAV
- 取一个 **Zotero API key** 与 **library ID**：https://www.zotero.org/settings/keys

### editable 安装

```powershell
uv tool install --editable "D:\Claude\zotero-mcp"
# 需要 PDF 大纲 / 读页 / 本地文件 DOI 抽取时，带上 [pdf] extra：
# uv tool install --editable "D:\Claude\zotero-mcp[pdf]"
```

入口落在 `C:\Users\yun\.local\bin\`：
- `zotero-mcp.exe` —— MCP server（给 Claude Code / Codex 用）
- `zotero-cli.exe` —— 独立 CLI（脚本 / 快速查询，省 token）

可选 extra：`[pdf]`（PyMuPDF，PDF 大纲/读页/本地文件 DOI 抽取）、`[scite]`（引用统计 + 撤稿提醒）。`[semantic]` **不要装**——语义功能本 fork 已关。

> 验证：`zotero-cli search "<关键词>" --limit 1` 能读到真实库即安装成功。

### 环境变量（hybrid + WebDAV）

| 变量 | 说明 |
|---|---|
| `ZOTERO_LOCAL=true` | 走本地 API 读 |
| `ZOTERO_LIBRARY_TYPE=user` | 库类型 |
| `ZOTERO_LIBRARY_ID=<你的 library id>` | web API 写需要 |
| `ZOTERO_API_KEY=<你的 api key>` | web API 写需要 |
| `ZOTERO_WEBDAV_URL=https://dav.jianguoyun.com/dav/<文件夹>/` | 附件文件落点 |
| `ZOTERO_WEBDAV_USERNAME=<你的坚果云邮箱>` | WebDAV 账号 |
| `ZOTERO_WEBDAV_PASSWORD=<坚果云应用密码>` | WebDAV 密码（**非**登录密码） |

> 笔记走 Zotero data sync；OA PDF / `add_attachment` 的文件走 WebDAV。
> **密钥不入库**——只写进下面各客户端的本地配置，仓库里永远只放占位符。

### 注册到 Claude Code（`~/.claude.json` 的 `mcpServers`）

```json
{
  "mcpServers": {
    "zotero": {
      "command": "C:\\Users\\yun\\.local\\bin\\zotero-mcp.exe",
      "env": {
        "ZOTERO_LOCAL": "true",
        "ZOTERO_LIBRARY_TYPE": "user",
        "ZOTERO_LIBRARY_ID": "<你的 library id>",
        "ZOTERO_API_KEY": "<你的 api key>",
        "ZOTERO_WEBDAV_URL": "https://dav.jianguoyun.com/dav/<文件夹>/",
        "ZOTERO_WEBDAV_USERNAME": "<你的坚果云邮箱>",
        "ZOTERO_WEBDAV_PASSWORD": "<坚果云应用密码>"
      }
    }
  }
}
```

### 注册到 Codex（`~/.codex/config.toml`）

```toml
[mcp_servers.zotero]
command = "C:\\Users\\yun\\.local\\bin\\zotero-mcp.exe"

[mcp_servers.zotero.env]
ZOTERO_LOCAL = "true"
ZOTERO_LIBRARY_TYPE = "user"
ZOTERO_LIBRARY_ID = "<你的 library id>"
ZOTERO_API_KEY = "<你的 api key>"
ZOTERO_WEBDAV_URL = "https://dav.jianguoyun.com/dav/<文件夹>/"
ZOTERO_WEBDAV_USERNAME = "<你的坚果云邮箱>"
ZOTERO_WEBDAV_PASSWORD = "<坚果云应用密码>"
PYTHONUTF8 = "1"
```

> **`PYTHONUTF8=1` 是 Codex 专属**：Codex 的 Rust 客户端严格校验 stderr 的 UTF-8，而 FastMCP 启动 banner 含 emoji/制表符，在 Windows 默认编码下不是合法 UTF-8 会触发 WARN。设这个变量即修复。Claude Code 不需要。

改完配置 **重启对应客户端** 生效。

---

## 二、安装 skill（跨项目复用）

工作流知识封装在 skill `use-zotero-mcp` 里。本仓同时是 **Claude Code plugin + marketplace**，装一次即可在**所有 Claude Code 项目**里用。

```
/plugin marketplace add KaiyunGuo/zotero-mcp
/plugin install zotero-mcp@zotero-mcp
```

- 调用：`/zotero-mcp:use-zotero-mcp`
- 当前 session 立即生效：`/reload-plugins`（或新开会话自动加载）
- **Codex 侧不装 plugin**：靠仓库内 `.agents/skills/use-zotero-mcp/SKILL.md` 副本（与 plugin 版保持字节一致）

---

## 三、更新

### 更新 skill（plugin）
```
# 1) 改 skill 后推送（两处副本须同步：skills/ 与 .agents/skills/）
git push
# 2) 各项目拉最新（省略了 version，每个 commit 即新版）
/plugin marketplace update zotero-mcp
```

### 更新 MCP server 代码
editable 安装，`git pull` 后代码即时生效，无需重装：
```powershell
git pull
# 仅当依赖（pyproject）变化时才需重装：
# uv tool install --reinstall --editable "D:\Claude\zotero-mcp"
```
> 运行中的 MCP server 进程不会热重载——改了 server 代码需**重启客户端**。

---

## 四、工具一览

> 返回 markdown 字符串。**★ = 本 fork 自定义/改造**。语义搜索工具已移除。

**检索**：`zotero_search_items` · `zotero_advanced_search` · `zotero_search_by_tag` · `zotero_get_recent` · `zotero_get_collections` · `zotero_get_collection_items` · `zotero_get_tags` · `zotero_search_by_citation_key`（BetterBibTeX，Extra 兜底）

**内容**：`zotero_get_item_metadata`（markdown/json/bibtex）· `zotero_get_item_fulltext` · `zotero_get_item_children` · `zotero_get_pdf_outline`（需 `[pdf]`）

**笔记 / 附件**：`zotero_create_note` ★（默认 markdown→HTML）· `zotero_update_note` · `zotero_get_notes` · `zotero_search_notes` · `zotero_get_annotations` · **`zotero_add_attachment` ★（把任意本地文件/自包含 HTML 挂到现有条目，存 WebDAV）**

**入库 / 管理**：`zotero_add_by_doi` ★（OA PDF 级联 + WebDAV）· `zotero_add_by_url` · `zotero_add_from_file` ★（本地 PDF/EPUB，自动抽 DOI；WebDAV）· `zotero_update_item` · `zotero_batch_update_tags` · `zotero_create_collection` · `zotero_manage_collections` · `zotero_find_duplicates` · `zotero_merge_duplicates`

**关联 / 引用**：`zotero_get_item_related` · `zotero_add_item_relation` · `zotero_remove_item_relation` · `scite_enrich_item` / `scite_enrich_search` / `scite_check_retractions`（需 `[scite]`）

### CLI 快查（`zotero-cli`）
```powershell
zotero-cli search "machine learning" --limit 5
zotero-cli get metadata ABC123 --format bibtex
zotero-cli get fulltext ABC123
zotero-cli add doi 10.1038/s41586-021-03819-2
zotero-cli notes create --item-key ABC123 --text "笔记" --tags idea
zotero-cli -v search "CRISPR"        # -v 看 API 调用过程
```

---

## 五、Troubleshooting

- **读不到库 / 无结果**：确认 Zotero 桌面在运行、本地 API 已开启（`设置 → 高级`）。
- **写操作失败 / 只建出游离笔记**：local API 是**只读**的；写必须有 `ZOTERO_API_KEY` + `ZOTERO_LIBRARY_ID`（hybrid）。
- **刚入库取不到 PDF 正文**：附件经 web API 上传后，桌面端还没把文件同步到本地/WebDAV，**先等一次桌面同步再重试**（详见 PROGRESS「PDF 上传落点」）。
- **公式不渲染**：别用 `create_note`（HTML 会被净化、MathJax 不跑）；写自包含 .html 用 `zotero_add_attachment` 挂为附件，浏览器打开即渲染。HTML 若 CDN 外链 MathJax 需联网，要离线完美则内联 JS。
- **Codex 报 stderr non-UTF-8 (WARN)**：在 Codex 配置加 `PYTHONUTF8=1`（见上）。
- **`zotero-mcp.exe` 报 `uv trampoline failed to canonicalize`**：在沙箱里改用 `uv run ...` 跑，不代表代码坏。

---

## 六、文档地图

| 文件 | 作用 |
|---|---|
| `PROGRESS.md` | **编码任务追踪。新 session 先读这个** |
| `CLAUDE.md` / `AGENTS.md` | 项目约束与工作规范（Claude / Codex 各一份） |
| `skills/use-zotero-mcp/SKILL.md` | 工作流 skill（plugin 规范源）；`.agents/` 下为 Codex 副本 |
| `DESIGN.html` / `HANDOFF.md` / `.docs/plans/*` | 原「从零自建」设计，**历史参考** |

---

## 致谢 / License

Fork of [`54yyyu/zotero-mcp`](https://github.com/54yyyu/zotero-mcp)（MIT）。本 fork 沿用 **MIT**。
