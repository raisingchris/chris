"""Receive files into the private inbox. Signed download URLs never leave this module."""
from __future__ import annotations

import hashlib
import io
import os
import re
from pathlib import Path
from urllib.parse import urlparse

import httpx

from agent.paths import safe_path

MAX_BYTES = 50 * 1024 * 1024


class AttachmentError(ValueError):
    """A recoverable attachment failure; messages must contain no URLs or credentials."""


def list_attachments(email_id: str) -> list[dict]:
    import resend
    result, after = [], None
    while True:
        page = resend.Emails.Receiving.Attachments.list(
            email_id, params={"limit": 100, **({"after": after} if after else {})})
        rows = page.get("data", [])
        result.extend(rows)
        if not page.get("has_more"):
            return result
        if not rows or not rows[-1].get("id") or rows[-1]["id"] == after:
            raise AttachmentError("invalid attachment pagination")
        after = rows[-1]["id"]


def download(url: str) -> bytes:
    # Only provider-generated CDN URLs, never URLs supplied in the webhook or email body.
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in {"inbound-cdn.resend.com", "cdn.resend.app"} or parsed.username or parsed.password:
        raise AttachmentError("unexpected attachment download host")
    try:
        with httpx.stream("GET", url, timeout=60, follow_redirects=False) as response:
            response.raise_for_status()
            out = bytearray()
            for chunk in response.iter_bytes():
                out.extend(chunk)
                if len(out) > MAX_BYTES:
                    raise AttachmentError("attachment exceeds 50 MiB")
            return bytes(out)
    except httpx.HTTPError:
        raise AttachmentError("attachment download failed; will retry") from None


def clean_pdf(raw: bytes) -> bytes:
    """Rebuild pages without document metadata or embedded document attachments."""
    from pypdf import PdfReader, PdfWriter
    reader = PdfReader(io.BytesIO(raw))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.metadata = None
    for obj in writer._objects:
        if isinstance(obj, dict):
            for key in ("/Metadata", "/PieceInfo"):
                obj.pop(key, None)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def save(repo: Path, email_id: str, attachment: dict, clean, fetch=download) -> tuple[Path, str]:
    ident = str(attachment.get("id") or "")
    if not ident:
        raise AttachmentError("attachment has no id")
    # Never use a sender's directory path, name, or attachment id as a path component.
    name = str(attachment.get("filename") or "attachment").replace("\\", "/").split("/")[-1]
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", clean(name)).strip(".-")[:120] or "attachment"
    bucket = hashlib.sha256(email_id.encode()).hexdigest()[:24]
    prefix = hashlib.sha256(ident.encode()).hexdigest()[:16]
    path = safe_path(repo, Path("memory/inbox/attachments") / bucket / f"{prefix}-{name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path = safe_path(repo, path)
    raw = fetch(str(attachment.get("download_url") or ""))
    if len(raw) > MAX_BYTES:
        raise AttachmentError("attachment exceeds 50 MiB")
    expected = attachment.get("size")
    if expected is not None and int(expected) != len(raw):
        raise AttachmentError("incomplete attachment download; will retry")
    if raw.startswith(b"%PDF-"):
        raw = clean_pdf(raw)
    temp = safe_path(repo, path.with_name(path.name + ".part"))
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o640)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
    os.replace(temp, path)
    return path, name
