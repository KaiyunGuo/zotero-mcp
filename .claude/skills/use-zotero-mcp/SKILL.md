---
name: use-zotero-mcp
description: Use when adding a paper to Zotero by its title or name (no DOI/URL in hand yet), or when running the search→入库→全文→笔记写回 workflow against this project's Zotero MCP. Covers name→DOI resolution, duplicate handling, and markdown note write-back.
---

# Using the Zotero MCP (按论文名入库 + 笔记写回)

## Core principle

The MCP only does Zotero-boundary work. **Resolving a paper title → DOI is the
LLM's job** (web search / WebFetch / PubMed MCP), NOT a server tool. Once you
have a DOI or URL, the MCP takes over.

## 按论文名入库 workflow

1. **Resolve identifier first.** Given a paper name, find its DOI via WebSearch /
   WebFetch / the PubMed MCP. Prefer an authoritative source (publisher,
   Crossref, PubMed). Confirm title + authors match before trusting a hit.
2. **Add by the strongest identifier you have:**
   - DOI → `zotero_add_by_doi` (auto-fetches metadata + tries the open-access
     PDF cascade: Unpaywall / arXiv / Semantic Scholar / PMC).
   - arXiv / publisher / DOI URL → `zotero_add_by_url`.
   - A local file → `zotero_add_from_file`.
3. **Ambiguity:** multiple plausible matches, or no confident DOI → STOP and ask
   the user which paper. Do not guess-add the wrong DOI.
4. **Duplicates:** if an add reports a duplicate, surface it to the user; do not
   force a second copy.

## 笔记写回

- `zotero_create_note` / `zotero_update_note` default to `content_format="markdown"`
  — write reading notes in Markdown (headings, lists, bold, links, code, tables).
  Raw HTML passes through.
- Notes attach as a **child note** under the paper, visible in Zotero desktop.

## Write requires hybrid mode

Zotero's local API (port 23119) is **read-only**. Creating notes / updating
metadata goes through the **web API** (needs `ZOTERO_API_KEY` + `ZOTERO_LIBRARY_ID`);
the change then syncs down to the desktop. Without those env vars, writes fail or
produce only standalone (unattached) notes.

## Don't

- Don't expect a `find_pdf` / `add_by_name` tool — neither exists by design.
- Don't write notes assuming local-only mode works; confirm hybrid is configured.
