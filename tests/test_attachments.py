import io
from pathlib import Path

import httpx
import pytest
from pypdf import PdfReader, PdfWriter

from agent import attachments
from agent.mail import Mail, filed_blank


@pytest.fixture
def setup(tmp_path):
    rows = [dict(id="a1", filename="../../Book.pdf", size=3, download_url="https://inbound-cdn.resend.com/a?secret"),
            dict(id="a2", filename="Book.pdf", size=3, download_url="https://inbound-cdn.resend.com/b?secret", content_disposition="inline")]
    records = []
    mail = Mail(tmp_path, lambda *args: records.append(args) or "archive:2026-09-13#1",
                {"parent-a": "private.person@example.test"}, "chris@raisingchris.com", dry_run=True,
                fetch_body=lambda _: {"text": "", "attachments": rows},
                fetch_attachments=lambda _: rows, download_attachment=lambda _: b"abc")
    event = {"type": "email.received", "data": {"email_id": "e1", "from": "private.person@example.test",
        "subject": "A book", "created_at": "2026-09-13T00:00:00Z", "attachments": rows}}
    return mail, event, records, rows


def test_all_files_inline_collisions_and_private_paths(setup):
    mail, event, records, rows = setup
    path = mail.ingest(event)
    files = list((mail.inbox_dir / "attachments").rglob("*.pdf"))
    assert len(files) == 2 and all(p.read_bytes() == b"abc" for p in files)
    text = path.read_text()
    assert all(p.relative_to(mail.repo_dir).as_posix() in text for p in files)
    assert "attachments_complete: true" in text
    assert not filed_blank(path)
    assert "private.person" not in text and "secret" not in str(records) and "../../" not in str(records)
    mail.fetch_attachments = lambda _: pytest.fail("duplicate must not download")
    assert mail.ingest(event) == path


def test_partial_failure_is_retryable_without_duplicate_mail(setup):
    mail, event, records, rows = setup
    def fail(url):
        if "/b?" in url:
            raise RuntimeError("signed secret URL")
        return b"abc"
    mail.download_attachment = fail
    with pytest.raises(attachments.AttachmentError):
        mail.ingest(event)
    path = next(mail.inbox_dir.glob("*.md"))
    mail.mark_read(path)
    assert "attachments_complete: false" in path.read_text()
    assert "secret" not in path.read_text() and "secret" not in str(records)
    mail.download_attachment = lambda _: b"abc"
    assert mail.ingest(event) == path
    assert "attachments_complete: true" in path.read_text()
    assert "read: true" in path.read_text()
    assert len(list(mail.inbox_dir.glob("*.md"))) == 1
    assert sum(kind == "mail_in" for kind, _ in records) == 1


def test_existing_body_only_message_can_be_backfilled(setup):
    mail, event, records, rows = setup
    mail.fetch_body = lambda _: {"text": "old message"}
    event["data"].pop("attachments")
    path = mail.ingest(event)
    path.write_text(path.read_text().replace("attachments_complete: true\n", ""))
    event["data"]["attachments"] = rows
    assert mail.ingest(event) == path
    assert "attachments_complete: true" in path.read_text()


def test_symlink_attachment_directory_refused(setup, tmp_path):
    mail, event, _, _ = setup
    outside = tmp_path / "outside"
    outside.mkdir()
    mail.inbox_dir.mkdir(parents=True)
    (mail.inbox_dir / "attachments").symlink_to(outside, target_is_directory=True)
    with pytest.raises(attachments.AttachmentError):
        mail.ingest(event)
    assert list(outside.iterdir()) == []


def test_pdf_metadata_removed():
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.add_metadata({"/Author": "Private Parent", "/Creator": "/Users/private/Desktop/book.pdf"})
    original = io.BytesIO()
    writer.write(original)
    cleaned = attachments.clean_pdf(original.getvalue())
    reader = PdfReader(io.BytesIO(cleaned))
    assert len(reader.pages) == 1 and reader.metadata is None
    assert b"Private Parent" not in cleaned and b"/Users/" not in cleaned


def test_list_paginates(monkeypatch):
    import resend
    calls = []
    def page(email_id, params):
        calls.append(params)
        return {"data": [{"id": "b" if "after" in params else "a"}], "has_more": "after" not in params}
    monkeypatch.setattr(resend.Emails.Receiving.Attachments, "list", page)
    assert [a["id"] for a in attachments.list_attachments("mail")] == ["a", "b"]
    assert calls[1]["after"] == "a"


@pytest.mark.parametrize("url", ["http://inbound-cdn.resend.com/a", "https://localhost/key", "https://inbound-cdn.resend.com.evil.test/a"])
def test_download_host_is_provider_only(url):
    with pytest.raises(attachments.AttachmentError):
        attachments.download(url)


def test_truncated_file_not_written(tmp_path):
    with pytest.raises(attachments.AttachmentError, match="incomplete"):
        attachments.save(tmp_path, "e", {"id": "a", "size": 9}, str, lambda _: b"short")
    assert not any(p.is_file() for p in tmp_path.rglob("*"))


def test_download_streams_bytes_without_auth(monkeypatch):
    from contextlib import contextmanager
    @contextmanager
    def stream(method, url, **kwargs):
        assert method == "GET" and kwargs["follow_redirects"] is False
        assert "headers" not in kwargs
        yield httpx.Response(200, content=b"payload", request=httpx.Request("GET", url))
    monkeypatch.setattr(httpx, "stream", stream)
    assert attachments.download("https://inbound-cdn.resend.com/a?secret") == b"payload"


def test_download_errors_hide_signed_url(monkeypatch):
    from contextlib import contextmanager
    @contextmanager
    def stream(method, url, **kwargs):
        yield httpx.Response(403, request=httpx.Request("GET", url))
    monkeypatch.setattr(httpx, "stream", stream)
    with pytest.raises(attachments.AttachmentError) as error:
        attachments.download("https://inbound-cdn.resend.com/a?secret")
    assert "secret" not in str(error.value)


def test_attachment_filename_scrubs_parent_identity(setup):
    mail, event, _, rows = setup
    rows[0]["filename"] = '/Users/private.person/Documents/private.person@example.test.pdf'
    path = mail.ingest(event)
    assert "private.person" not in path.read_text()
    assert "/Users/" not in path.read_text()
    assert not any('private.person' in str(p) for p in mail.inbox_dir.rglob('*'))
