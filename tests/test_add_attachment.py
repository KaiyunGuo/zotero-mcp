"""Tests for zotero_add_attachment (server.add_attachment, TASK-006).

Attaches an existing local file to an existing item as an imported_file
attachment, reusing the attachment_both + WebDAV path (mirrors add_from_file).
"""

from zotero_mcp import server
from conftest import FakeZotero  # noqa: I001

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _AttachZotero(FakeZotero):
    """FakeZotero extended with attachment_both tracking."""

    def __init__(self):
        super().__init__()
        self.attachments = []

    def attachment_both(self, files, parentid=None, **kwargs):
        self.attachments.append({"files": files, "parentid": parentid})
        # Mirror pyzotero's Zupload result shape so _extract_attachment_key works.
        return {"success": [{"key": "ATTACH01"}], "unchanged": [], "failure": []}


def _patch_path_valid(monkeypatch):
    """Patch os.path functions so the file path appears valid."""
    monkeypatch.setattr("os.path.exists", lambda p: True)
    monkeypatch.setattr("os.path.isfile", lambda p: True)
    monkeypatch.setattr("os.path.islink", lambda p: False)
    monkeypatch.setattr("os.path.isabs", lambda p: p.startswith("/"))
    monkeypatch.setattr("os.path.realpath", lambda p: p)


def _patch_hybrid_mode(monkeypatch, write_zot):
    """Patch _get_write_client to return (read_zot, write_zot)."""
    read_zot = _AttachZotero()
    monkeypatch.setattr(
        "zotero_mcp.tools._helpers._get_write_client",
        lambda ctx: (read_zot, write_zot),
    )
    return read_zot


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

class TestHappyPath:
    def test_attaches_file_to_existing_item(self, monkeypatch, dummy_ctx):
        zot = _AttachZotero()
        _patch_path_valid(monkeypatch)
        _patch_hybrid_mode(monkeypatch, zot)
        monkeypatch.setattr(
            "zotero_mcp.webdav.is_webdav_configured", lambda: False
        )

        result = server.add_attachment(
            item_key="PARENT01",
            file_path="/Users/test/notes/paper.html",
            ctx=dummy_ctx,
        )

        assert len(zot.attachments) == 1
        att = zot.attachments[0]
        assert att["files"][0] == ("paper.html", "/Users/test/notes/paper.html")
        assert att["parentid"] == "PARENT01"
        assert "PARENT01" in result
        assert "paper.html" in result

    def test_title_overrides_basename(self, monkeypatch, dummy_ctx):
        zot = _AttachZotero()
        _patch_path_valid(monkeypatch)
        _patch_hybrid_mode(monkeypatch, zot)
        monkeypatch.setattr(
            "zotero_mcp.webdav.is_webdav_configured", lambda: False
        )

        server.add_attachment(
            item_key="PARENT01",
            file_path="/Users/test/notes/paper.html",
            title="Reading notes",
            ctx=dummy_ctx,
        )

        att = zot.attachments[0]
        assert att["files"][0] == ("Reading notes", "/Users/test/notes/paper.html")

    def test_any_extension_allowed(self, monkeypatch, dummy_ctx):
        """Unlike add_from_file, no extension whitelist — .txt attaches fine."""
        zot = _AttachZotero()
        _patch_path_valid(monkeypatch)
        _patch_hybrid_mode(monkeypatch, zot)
        monkeypatch.setattr(
            "zotero_mcp.webdav.is_webdav_configured", lambda: False
        )

        result = server.add_attachment(
            item_key="PARENT01",
            file_path="/Users/test/data/notes.txt",
            ctx=dummy_ctx,
        )
        assert len(zot.attachments) == 1
        assert "notes.txt" in result


# ---------------------------------------------------------------------------
# WebDAV branch
# ---------------------------------------------------------------------------

class TestWebDav:
    def test_webdav_push_when_configured(self, monkeypatch, dummy_ctx):
        import zotero_mcp.webdav as _webdav
        zot = _AttachZotero()
        _patch_path_valid(monkeypatch)
        _patch_hybrid_mode(monkeypatch, zot)
        monkeypatch.setattr(_webdav, "is_webdav_configured", lambda: True)

        calls = []

        def fake_upload(attachment_key, file_path, **kwargs):
            calls.append((attachment_key, file_path))
            return ("md5hex", 123)

        monkeypatch.setattr(_webdav, "upload_attachment_to_webdav", fake_upload)

        result = server.add_attachment(
            item_key="PARENT01",
            file_path="/Users/test/notes/paper.html",
            ctx=dummy_ctx,
        )
        assert len(calls) == 1
        assert calls[0][0] == "ATTACH01"
        assert calls[0][1] == "/Users/test/notes/paper.html"
        assert "WebDAV" in result

    def test_no_webdav_push_when_not_configured(self, monkeypatch, dummy_ctx):
        import zotero_mcp.webdav as _webdav
        zot = _AttachZotero()
        _patch_path_valid(monkeypatch)
        _patch_hybrid_mode(monkeypatch, zot)
        monkeypatch.setattr(_webdav, "is_webdav_configured", lambda: False)

        def boom(*args, **kwargs):
            raise AssertionError("must not upload to WebDAV when not configured")

        monkeypatch.setattr(_webdav, "upload_attachment_to_webdav", boom)

        result = server.add_attachment(
            item_key="PARENT01",
            file_path="/Users/test/notes/paper.html",
            ctx=dummy_ctx,
        )
        assert len(zot.attachments) == 1
        assert "WebDAV" not in result

    def test_webdav_failure_is_surfaced_not_fatal(self, monkeypatch, dummy_ctx):
        import zotero_mcp.webdav as _webdav
        zot = _AttachZotero()
        _patch_path_valid(monkeypatch)
        _patch_hybrid_mode(monkeypatch, zot)
        monkeypatch.setattr(_webdav, "is_webdav_configured", lambda: True)

        def boom(*args, **kwargs):
            raise RuntimeError("PUT 507")

        monkeypatch.setattr(_webdav, "upload_attachment_to_webdav", boom)

        result = server.add_attachment(
            item_key="PARENT01",
            file_path="/Users/test/notes/paper.html",
            ctx=dummy_ctx,
        )
        # attachment item still created; warning surfaced
        assert len(zot.attachments) == 1
        assert "WARNING" in result
        assert "PUT 507" in result


# ---------------------------------------------------------------------------
# Validation / error paths
# ---------------------------------------------------------------------------

class TestValidation:
    def test_rejects_symlink(self, monkeypatch, dummy_ctx):
        zot = _AttachZotero()
        _patch_hybrid_mode(monkeypatch, zot)
        monkeypatch.setattr("os.path.islink", lambda p: True)

        result = server.add_attachment(
            item_key="PARENT01",
            file_path="/Users/test/notes/paper.html",
            ctx=dummy_ctx,
        )
        assert "Symlink" in result
        assert len(zot.attachments) == 0

    def test_rejects_relative_path(self, monkeypatch, dummy_ctx):
        zot = _AttachZotero()
        _patch_hybrid_mode(monkeypatch, zot)
        monkeypatch.setattr("os.path.islink", lambda p: False)
        monkeypatch.setattr("os.path.isabs", lambda p: False)

        result = server.add_attachment(
            item_key="PARENT01",
            file_path="notes/paper.html",
            ctx=dummy_ctx,
        )
        assert "absolute path" in result
        assert len(zot.attachments) == 0

    def test_file_not_found(self, monkeypatch, dummy_ctx):
        zot = _AttachZotero()
        _patch_hybrid_mode(monkeypatch, zot)
        monkeypatch.setattr("os.path.islink", lambda p: False)
        monkeypatch.setattr("os.path.isabs", lambda p: True)
        monkeypatch.setattr("os.path.realpath", lambda p: p)
        monkeypatch.setattr("os.path.isfile", lambda p: False)

        result = server.add_attachment(
            item_key="PARENT01",
            file_path="/Users/test/missing.html",
            ctx=dummy_ctx,
        )
        assert "File not found" in result
        assert len(zot.attachments) == 0

    def test_parent_item_not_found(self, monkeypatch, dummy_ctx):
        zot = _AttachZotero()
        read_zot = _patch_hybrid_mode(monkeypatch, zot)
        _patch_path_valid(monkeypatch)

        def raise_404(item_key):
            raise RuntimeError("404 Not Found")

        monkeypatch.setattr(read_zot, "item", raise_404)

        result = server.add_attachment(
            item_key="NOPE0001",
            file_path="/Users/test/notes/paper.html",
            ctx=dummy_ctx,
        )
        assert "not found" in result
        assert "NOPE0001" in result
        assert len(zot.attachments) == 0

    def test_local_only_mode_returns_error(self, monkeypatch, dummy_ctx):
        def raise_value_error(ctx):
            raise ValueError("Write operations require a writable library.")

        monkeypatch.setattr(
            "zotero_mcp.tools._helpers._get_write_client", raise_value_error
        )

        result = server.add_attachment(
            item_key="PARENT01",
            file_path="/Users/test/notes/paper.html",
            ctx=dummy_ctx,
        )
        assert "writable library" in result
