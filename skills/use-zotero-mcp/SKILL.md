---
name: use-zotero-mcp
description: Use when adding a paper to Zotero by its title or name (no DOI/URL in hand yet), checking whether this project's Zotero MCP is usable, troubleshooting MCP/CLI startup, or running the search→入库→全文→笔记写回 workflow. Covers name→DOI resolution, duplicate handling, markdown note write-back, and Windows/Codex runtime pitfalls.
---

# Using the Zotero MCP (按论文名入库 + 笔记写回)

## Core principle

The MCP only does Zotero-boundary work. **Resolving a paper title → DOI is the
LLM's job** (web search / WebFetch / PubMed MCP), NOT a server tool. Once you
have a DOI or URL, the MCP takes over.

## Availability smoke test

1. Prefer direct MCP tools when available. Search for Zotero tools if needed; a
   working Codex session exposes `mcp__zotero` with tools such as `fetch`,
   `zotero_add_by_doi`, `zotero_create_note`, and `zotero_search_items`.
2. Use read-only checks first:
   - `mcp__zotero.fetch(id="<known item key>")` if an item key is known.
   - CLI fallback: `uv run python -m zotero_mcp.cli_standalone get recent --limit 1`.
   - Tool registration: `uv run python -c "import asyncio; from zotero_mcp.server import mcp; print(len(asyncio.run(mcp.list_tools())))"`.
3. Expected healthy state in this project: about 52 registered tools, core tools
   present, and no semantic/database tools.

## Windows/Codex runtime pitfalls

- Do not print `~/.claude.json` or env wholesale; it contains Zotero API/WebDAV
  secrets. If env is needed, set only required variables and redact output.
- If `C:\Users\yun\.local\bin\zotero-mcp.exe` fails with
  `uv trampoline failed to canonicalize script path`, do not conclude the server
  code is broken. In this sandbox, the project still runs via `uv run ...`.
- If `uv` fails to initialize `C:\Users\yun\AppData\Local\uv\cache`, set
  `UV_CACHE_DIR=D:\Claude\zotero-mcp\.uv-cache` for the command.
- If `uv run` needs missing wheels and network is blocked, rerun the same command
  with sandbox escalation; this is dependency download, not a code failure.
- On Windows GBK consoles, `zotero-mcp setup-info` may raise
  `UnicodeEncodeError` because it prints emoji. Set `PYTHONIOENCODING=utf-8` or
  skip `setup-info`; it is diagnostic only.
- In Codex sandbox, `setup-info` may hit `PermissionError` reading
  `C:\Users\yun\.config\zotero-mcp\config.json`. Prefer direct MCP/CLI smoke
  tests above.

## 按论文名入库 workflow

1. **Resolve identifier first.** Given a paper name, find its DOI via WebSearch /
   WebFetch / the PubMed MCP. Prefer an authoritative source (publisher,
   Crossref, PubMed). Confirm title + authors match before trusting a hit.
2. **Add by the strongest identifier you have:**
   - DOI → `zotero_add_by_doi` (auto-fetches metadata + tries the open-access
     PDF cascade: Unpaywall / arXiv / Semantic Scholar / PMC).
   - arXiv / publisher / DOI URL → `zotero_add_by_url`.
   - A local PDF/EPUB as a **new** item → `zotero_add_from_file`.
   - Attach a file to an **existing** item → `zotero_add_attachment(item_key,
     file_path)` (any file type; bytes stored as-is + pushed to WebDAV).
3. **Ambiguity:** multiple plausible matches, or no confident DOI → STOP and ask
   the user which paper. Do not guess-add the wrong DOI.
4. **Duplicates:** if an add reports a duplicate, surface it to the user; do not
   force a second copy.

## 全文抽取(get_item_fulltext)

- 总能拿到**元数据 + 摘要**(来自 Zotero 索引)。**PDF 正文**则需文件实际存在于
  本地 Zotero storage 或 WebDAV 才取得到。
- **刚 `add_by_doi` 后立即取正文可能失败**(本地 storage 404 / WebDAV
  "Attachment not found"):新附件经 web API 上传,桌面端还没把文件同步到
  本地/WebDAV。先等桌面 Zotero 完成一次同步再重试。若持续取不到,见 PROGRESS
  「PDF 上传落点 spike」——疑为 web API 上传落点与 WebDAV 文件 sync 不相交,待确认。
- 只在**确实要读整篇**时调它(返回整篇,常上万 token);检索/浏览不要用。

## 笔记写回

- `zotero_create_note` / `zotero_update_note` default to `content_format="markdown"`
  — write reading notes in Markdown (headings, lists, bold, links, code, tables).
  Raw HTML passes through.
- Notes attach as a **child note** under the paper, visible in Zotero desktop.

## 富渲染笔记(MathJax 公式 / 代码高亮)= 附件,不是 note

- Zotero **净化** note 的 HTML(剥 `<script>`)→ `zotero_create_note` 里的 MathJax
  **不会运行**,公式只能退化成 Unicode/纯文本近似。这是设计使然,救不回来。
- 要公式/代码完美渲染:写一个**自包含 .html**(MathJax + 高亮),用
  `zotero_add_attachment(item_key, file_path)` 挂到条目下。附件不被净化,浏览器
  打开即正确渲染,随库 + WebDAV 同步——取代手动把文件拖进条目。
- caveat:HTML 若用 CDN 外链 MathJax,打开时需联网;要离线也完美须内联 MathJax JS。

## Write requires hybrid mode

Zotero's local API (port 23119) is **read-only**. Creating notes / updating
metadata goes through the **web API** (needs `ZOTERO_API_KEY` + `ZOTERO_LIBRARY_ID`);
the change then syncs down to the desktop. Without those env vars, writes fail or
produce only standalone (unattached) notes.

## Don't

- Don't expect a `find_pdf` / `add_by_name` tool — neither exists by design.
- Don't write notes assuming local-only mode works; confirm hybrid is configured.
