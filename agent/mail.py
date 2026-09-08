"""Mail bridge between Chris and her two anonymous parents.

Outbound: handle (``parent-a``) → real address, signed, sent via Resend, archived
with the handle (never the real address). Inbound: Resend ``email.received``
webhook → parent addresses in the event rewritten to handles → event archived →
quoted history and signatures stripped → body redacted (canaries, foreign
addresses, phones) → ``memory/inbox/<date>-<slug>.md``. Real parent addresses
never appear in anything written under ``repo_dir`` or in the archive.
Strangers' addresses survive in the ``from:`` line of the inbox file (git-ignored)
so she can reply; only the body is redacted.

Dependencies (archive, config) are injected; this module imports neither.
"""

from __future__ import annotations

import copy
import html as _html
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

from agent import redaction
from agent.paths import UnsafePath, safe_path

SIGNATURE = "\n\n— Chris"
# Said once, to each new address, the first time she writes to it. Never to her parents.
DISCLOSURE = ("\nI'm an AI. Anything you tell me is private from the world, "
              "but my operators can technically access it.")
_OLD_DISCLOSURE_TAIL = "but my operators can technically access it."

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
        canaries: Iterable[str] = (),
    ):
        self.repo_dir = Path(repo_dir)
        self.archive_append = archive_append
        self.parents = {h: a for h, a in parents.items() if a}
        self.chris_email = chris_email
        self.resend_api_key = resend_api_key
        self.dry_run = dry_run
        self.fetch_body = fetch_body or _default_fetch_body
        self.canaries = [c for c in canaries if c]
        self.inbox_dir = self.repo_dir / "memory" / "inbox"

    def _safe(self, path: Path) -> Path | None:
        """``safe_path`` inside the repo; refusals are archived as ``unsafe_path`` and yield None."""
        try:
            return safe_path(self.repo_dir, path)
        except UnsafePath as exc:
            self.archive_append("unsafe_path", {"kind": "unsafe_path", "path": str(path), "error": str(exc)})
            return None

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

    def _first_contact(self, addr: str) -> bool:
        """True (and remembers it) the first time she writes to ``addr``. Ledger of addresses lives
        beside the inbox, git-ignored with it."""
        addr = addr.strip().lower()
        path = Path(self.repo_dir) / "memory" / "inbox" / ".contacted"
        try:
            seen = set(path.read_text(encoding="utf-8").split()) if path.exists() else set()
        except OSError:
            seen = set()
        if addr in seen:
            return False
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write(addr + "\n")
        except OSError:
            pass
        return True

    def map_addresses(self, text: str) -> str:
        """Replace every real parent address and its local-part with the handle."""
        for handle, real in self.parents.items():
            local = real.split("@", 1)[0]
            for needle in (real, local):
                text = re.sub(re.escape(needle), handle, text, flags=re.IGNORECASE)
        return text

    def clean(self, text: str) -> str:
        """Handles for parent addresses, then ``redaction.redact`` with the canaries: for anything she reads."""
        return redaction.redact(self.map_addresses(text), self.canaries)[0]

    def _anonymise_event(self, payload: dict) -> dict:
        """A copy of the webhook event with parent addresses (from/to/cc/bcc/reply_to) replaced by handles."""
        event = copy.deepcopy(payload)
        data = event.get("data")
        if not isinstance(data, dict):
            return event
        for key in ("from", "to", "cc", "bcc", "reply_to"):
            if key not in data or data[key] is None:
                continue
            value = data[key]
            if isinstance(value, list):
                data[key] = [self._anonymise_address(v) for v in value]
            else:
                data[key] = self._anonymise_address(value)
        if isinstance(data.get("subject"), str):
            data["subject"] = self.map_addresses(data["subject"])
        return event

    def _anonymise_address(self, value):
        if not isinstance(value, str):
            return value
        handle = self.handle_for(value)
        return handle if handle else self.map_addresses(value)

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
        # She often signs herself; don't stack two signatures or repeat the disclosure.
        clean = body.rstrip("\n")
        lines = clean.split("\n")
        while lines and (lines[-1].strip() in ("", "Chris", "— Chris", "- Chris", "-- Chris")
                         or lines[-1].strip().endswith(_OLD_DISCLOSURE_TAIL)):
            lines.pop()
        clean = "\n".join(lines).rstrip("\n")
        text = clean + SIGNATURE
        # First contact with an address that isn't a parent gets the disclosure once.
        for t in given:
            if t not in self.parents and self._first_contact(t):
                text += DISCLOSURE
                break
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
        alert: str = "",
        tickets_line: str = "",
    ) -> dict:
        """The nightly mail to both parents. ``alert`` (e.g. a failed sleep) goes on the very first line;
        ``tickets_line`` (her open tickets, if any) follows the odometer."""
        body = "\n".join(
            ([alert.rstrip(), ""] if alert else []) + [
                f"Chris's day, {date}. {inbox_count} new message(s) in her inbox.",
                "",
                diary_md.rstrip(),
                "",
                odometer_line,
            ] + ([tickets_line.rstrip()] if tickets_line.strip() else []) + [
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
        """Ingest a Resend ``email.received`` webhook event; return the inbox path.

        Idempotent on ``data.email_id``: a redelivered event returns the existing inbox file
        without archiving or fetching again.
        """
        data = payload.get("data", payload)
        email_id = str(data.get("email_id") or "")
        if email_id:
            existing = self._find_by_email_id(email_id)
            if existing is not None:
                self.archive_append("mail_in_duplicate", {"kind": "mail_in_duplicate", "email_id": email_id})
                return existing

        # Parent addresses become handles *before* the raw event is archived.
        ref = self.archive_append("mail_in", self._anonymise_event(payload))

        sender = data.get("from", "")
        subject = data.get("subject") or "(no subject)"
        received = data.get("created_at") or payload.get("created_at") or _now_iso()

        body = self.fetch_body(email_id) if email_id else {}
        text = body.get("text") or _html_to_text(body.get("html") or "")

        # A parent becomes the handle; a stranger keeps the address so she can reply.
        sender_out = self.handle_for(sender) or self.map_addresses(sender)
        subject_out = self.clean(subject)
        body_out = self.clean(_clean_body(text))

        date = received[:10]
        path = self._unique_path(date, subject_out)
        safe = self._safe(path)
        if safe is None:
            raise UnsafePath(f"inbox path refused: {path.name}")
        path = safe
        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "---\n"
            f"from: {sender_out}\n"
            f"subject: {_yaml_str(subject_out)}\n"
            f"received: {received}\n"
            f"archive: {ref}\n"
            + (f"email_id: {_yaml_str(email_id)}\n" if email_id else "")
            + "---\n\n"
            f"{body_out}\n"
        )
        return path

    def _find_by_email_id(self, email_id: str) -> Path | None:
        if not self.inbox_dir.exists():
            return None
        needle = f"\nemail_id: {_yaml_str(email_id)}\n"
        for p in sorted(self.inbox_dir.glob("*.md")):
            safe = self._safe(p)
            if safe is None:
                continue
            try:
                if needle in _frontmatter(safe.read_text(encoding="utf-8")):
                    return safe
            except OSError:
                continue
        return None

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
        out = []
        for p in sorted(self.inbox_dir.glob("*.md")):
            safe = self._safe(p)
            if safe is None:
                continue
            if "\nread: true\n" not in _frontmatter(safe.read_text()):
                out.append(safe)
        return out

    def mark_read(self, path: Path) -> None:
        path = self._safe(Path(path))
        if path is None:
            return
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
        # A quoted line is "> text" (client-inserted). ">> text" is a person's own reply marker — keep it.
        if re.match(r"^\s*>(\s|$)", line) and not re.match(r"^\s*>>", line):
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
