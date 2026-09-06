"""Mail bridge between Chris and her two anonymous parents.

Outbound: handle (``parent-a``) → real address, signed, sent via Resend, archived
with the handle (never the real address). Inbound: Resend ``email.received``
webhook → raw event archived → sender mapped to handle → quoted history and
signatures stripped → ``memory/inbox/<date>-<slug>.md``. Real parent addresses
never appear in anything written under ``repo_dir``.

Dependencies (archive, config) are injected; this module imports neither.
"""

from __future__ import annotations

import html as _html
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

SIGNATURE = (
    "\n\n— Chris\n"
    "I'm an AI. Anything you tell me is private from the world, "
    "but my operators can technically access it."
)

SUMMARY_FOOTER = "Reply to this email and Chris reads it in the morning. Assignments welcome."

_QUOTE_START = re.compile(r"^(On .* wrote:|-----Original Message-----)\s*$")
_EMAIL_IN_ANGLE = re.compile(r"<([^<>]+@[^<>]+)>")


def _default_fetch_body(email_id: str) -> dict:
    """Fetch a received email's body via the Resend SDK.

    ``resend.Emails.Receiving.get`` → GET /emails/receiving/{id} → ReceivedEmail
    with ``text`` / ``html`` fields.
    """
    import resend

    got = resend.Emails.Receiving.get(email_id)
    return {"text": got.get("text"), "html": got.get("html")}


class Mail:
    def __init__(
        self,
        repo_dir: Path,
        archive_append: Callable[[str, dict], str],
        parents: dict[str, str],
        chris_email: str,
        resend_api_key: str | None = None,
        dry_run: bool = False,
        fetch_body: Callable[[str], dict] | None = None,
    ):
        self.repo_dir = Path(repo_dir)
        self.archive_append = archive_append
        self.parents = {h: a for h, a in parents.items() if a}
        self.chris_email = chris_email
        self.resend_api_key = resend_api_key
        self.dry_run = dry_run
        self.fetch_body = fetch_body or _default_fetch_body
        self.inbox_dir = self.repo_dir / "memory" / "inbox"

    # --- mapping -------------------------------------------------------------

    def resolve(self, to: str) -> str:
        return self.parents.get(to, to)

    def handle_for(self, address: str) -> str | None:
        """Handle for a real parent address (accepts ``Name <addr>``)."""
        m = _EMAIL_IN_ANGLE.search(address)
        addr = (m.group(1) if m else address).strip().lower()
        for handle, real in self.parents.items():
            if real.lower() == addr:
                return handle
        return None

    def map_addresses(self, text: str) -> str:
        """Replace every real parent address and its local-part with the handle."""
        for handle, real in self.parents.items():
            local = real.split("@", 1)[0]
            for needle in (real, local):
                text = re.sub(re.escape(needle), handle, text, flags=re.IGNORECASE)
        return text

    # --- outbound ------------------------------------------------------------

    def send(
        self,
        to: str | list[str],
        subject: str,
        body: str,
        in_reply_to: str | None = None,
        reply_to: str | None = None,
    ) -> dict:
        given = [to] if isinstance(to, str) else list(to)
        text = body.rstrip("\n") + SIGNATURE
        params: dict = {
            "from": self.chris_email,
            "to": [self.resolve(t) for t in given],
            "subject": subject,
            "text": text,
        }
        if reply_to:
            params["reply_to"] = reply_to
        if in_reply_to:
            params["headers"] = {"In-Reply-To": in_reply_to, "References": in_reply_to}

        # Archive with addresses AS GIVEN — never the resolved parent address.
        self.archive_append(
            "mail_out",
            {"kind": "mail_out", "to": given, "subject": subject, "body": text},
        )

        if self.dry_run:
            return {"dry_run": True, **params}

        import resend

        resend.api_key = self.resend_api_key
        result = resend.Emails.send(params)
        return {"dry_run": False, "id": result.get("id"), **params}

    def daily_summary(
        self,
        date: str,
        diary_md: str,
        odometer_line: str,
        spend_line: str,
        inbox_count: int,
    ) -> dict:
        body = "\n".join(
            [
                f"Chris's day, {date}. {inbox_count} new message(s) in her inbox.",
                "",
                diary_md.rstrip(),
                "",
                odometer_line,
                spend_line,
                "",
                SUMMARY_FOOTER,
            ]
        )
        return self.send(
            list(self.parents),
            f"Chris — {date}",
            body,
            reply_to=self.chris_email,
        )

    # --- inbound -------------------------------------------------------------

    def ingest(self, payload: dict) -> Path:
        """Ingest a Resend ``email.received`` webhook event; return the inbox path."""
        ref = self.archive_append("mail_in", payload)

        data = payload.get("data", payload)
        sender = data.get("from", "")
        subject = data.get("subject") or "(no subject)"
        received = data.get("created_at") or payload.get("created_at") or _now_iso()

        body = self.fetch_body(data["email_id"]) if data.get("email_id") else {}
        text = body.get("text") or _html_to_text(body.get("html") or "")

        sender_out = self.handle_for(sender) or sender
        subject_out = self.map_addresses(subject)
        body_out = self.map_addresses(_clean_body(text))

        date = received[:10]
        path = self._unique_path(date, subject_out)
        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "---\n"
            f"from: {sender_out}\n"
            f"subject: {_yaml_str(subject_out)}\n"
            f"received: {received}\n"
            f"archive: {ref}\n"
            "---\n\n"
            f"{body_out}\n"
        )
        return path

    def _unique_path(self, date: str, subject: str) -> Path:
        base = f"{date}-{_slug(subject)}"
        path = self.inbox_dir / f"{base}.md"
        n = 2
        while path.exists():
            path = self.inbox_dir / f"{base}-{n}.md"
            n += 1
        return path

    # --- inbox state ---------------------------------------------------------

    def list_unread(self) -> list[Path]:
        if not self.inbox_dir.exists():
            return []
        return sorted(
            p
            for p in self.inbox_dir.glob("*.md")
            if "\nread: true\n" not in _frontmatter(p.read_text())
        )

    def mark_read(self, path: Path) -> None:
        path = Path(path)
        text = path.read_text()
        if "\nread: true\n" in _frontmatter(text):
            return
        if text.startswith("---\n"):
            head, _, rest = text[4:].partition("\n---\n")
            text = f"---\n{head}\nread: true\n---\n{rest}"
        else:
            text = f"---\nread: true\n---\n{text}"
        path.write_text(text)


# --- helpers -------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _frontmatter(text: str) -> str:
    if not text.startswith("---\n"):
        return ""
    head, _, _ = text[4:].partition("\n---\n")
    return f"\n{head}\n"


def _slug(text: str, limit: int = 40) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:limit].rstrip("-") or "mail"


def _yaml_str(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ") + '"'


def _clean_body(text: str) -> str:
    """Drop quoted history, reply markers and trailing signature."""
    kept: list[str] = []
    for line in text.replace("\r\n", "\n").split("\n"):
        if _QUOTE_START.match(line.strip()):
            break
        if line.lstrip().startswith(">"):
            continue
        kept.append(line)
    out = "\n".join(kept)
    out = out.split("\n-- \n", 1)[0]
    return out.strip()


def _html_to_text(html: str) -> str:
    html = re.sub(r"(?is)<(script|style).*?</\1>", "", html)
    html = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</li>|</tr>", "\n", html)
    text = re.sub(r"<[^>]+>", "", html)
    return _html.unescape(text).strip()
