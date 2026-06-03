"""Regression for TASK-009: update_item must strip server-managed read-only
keys (e.g. attachment ``lastRead``) before PUT, or Zotero's web API rejects
the payload with 400 "Invalid keys present: lastRead".
"""

from zotero_mcp import server
from conftest import FakeZotero, _FakeResponse  # noqa: I001


class _RoZotero(FakeZotero):
    """Fake client whose update_item rejects read-only keys like Zotero does."""

    def __init__(self):
        super().__init__()
        self._items = [{
            "key": "ATCH0001",
            "version": 5,
            "data": {
                "key": "ATCH0001",
                "version": 5,
                "itemType": "attachment",
                "linkMode": "imported_url",
                "contentType": "text/html",
                "title": "old title",
                "url": "http://example.com/doc.html",
                "tags": [],
                "collections": [],
                "relations": {},
                "lastRead": 1700000000,  # server-managed, read-only
            },
        }]
        self.updated = []

    def update_item(self, item, **kwargs):
        data = item.get("data", {})
        if "lastRead" in data:
            # Mirror Zotero's 400 rejection of read-only keys.
            raise Exception("400 Bad Request - Invalid keys present: lastRead")
        self.updated.append(item)
        return _FakeResponse(204)


def test_update_item_strips_lastread_on_html_attachment(monkeypatch, dummy_ctx):
    zot = _RoZotero()
    monkeypatch.setattr(
        "zotero_mcp.tools._helpers._get_write_client",
        lambda ctx: (zot, zot),
    )

    result = server.update_item(
        item_key="ATCH0001",
        title="HCE loss — 自定义标题",
        ctx=dummy_ctx,
    )

    assert "Successfully updated" in result, result
    assert zot.updated, "update_item should have written without lastRead"
    written = zot.updated[0]["data"]
    assert "lastRead" not in written
    assert written["title"] == "HCE loss — 自定义标题"


def test_strip_readonly_helper_is_noop_on_regular_item():
    from zotero_mcp.tools import _helpers

    item = {"key": "ABC", "version": 1, "data": {"itemType": "journalArticle",
                                                  "title": "x"}}
    out = _helpers._strip_readonly_item_fields(item)
    assert out is item
    assert out["data"] == {"itemType": "journalArticle", "title": "x"}
