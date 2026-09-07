"""Tickets: requests only a parent can act on, filed as public markdown in the repo.

One file per ticket under ``governance/tickets/<YYYYMMDDTHHMM>-<slug>.md`` (the ``T``
in the stamp, as in council minutes, keeps the nightly redaction from reading the
digits as a phone number)::

    ---
    id: 20260907T1430-a-github-token
    title: A GitHub token
    status: open            # open | done | declined
    opened: 2026-09-07T14:30:00+00:00
    closed: 2026-09-08T09:12:00+00:00   # once resolved
    by: chris               # who opened it; the reply says who closed it
    ---

    <her text: the two-minute checklist>

    ## Reply

    *parent-a, 2026-09-08T09:12:00+00:00 — done*

    <their reply>

Chris opens tickets through the ``ticket`` tool; a parent resolves them from the
parent page, which commits the file as Parent. Both halves live in the same file
so the whole exchange is on the record.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import frontmatter
import yaml

from agent.paths import UnsafePath, safe_path

TICKETS_DIR = Path("governance") / "tickets"
STATUSES = ("open", "done", "declined")
CLOSED = ("done", "declined")
REPLY_HEADING = "## Reply"
_ID_RE = re.compile(r"^\d{8}T\d{4}-[a-z0-9-]{1,50}$")


def slug(text: str, limit: int = 40) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:limit].rstrip("-") or "ticket"


def _iso(now: datetime) -> str:
    return now.isoformat(timespec="seconds")


def _dump(meta: dict, body: str) -> str:
    front = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True, default_flow_style=False).rstrip()
    return f"---\n{front}\n---\n\n{body.rstrip()}\n"


def ticket_path(repo_dir: str | Path, ticket_id: str) -> Path:
    """The file for ``ticket_id``; raises ValueError on a malformed id or a symlinked path."""
    if not _ID_RE.match(ticket_id):
        raise ValueError(f"bad ticket id: {ticket_id!r}")
    try:
        return safe_path(Path(repo_dir), TICKETS_DIR / f"{ticket_id}.md")
    except UnsafePath as exc:
        raise ValueError(str(exc)) from exc


def open_ticket(repo_dir: str | Path, title: str, body: str, now: datetime, by: str = "chris") -> Path:
    """Write a new open ticket and return its path."""
    title = " ".join(str(title).split())
    body = str(body).strip()
    if not title:
        raise ValueError("a ticket needs a title")
    if not body:
        raise ValueError("a ticket needs a body: what exactly should a parent do?")
    stamp = now.strftime("%Y%m%dT%H%M")
    base = f"{stamp}-{slug(title)}"
    tid = base
    n = 2
    while ticket_path(repo_dir, tid).exists():  # two tickets in the same minute
        tid = f"{base}-{n}"
        n += 1
    path = ticket_path(repo_dir, tid)
    path.parent.mkdir(parents=True, exist_ok=True)
    meta = {"id": tid, "title": title, "status": "open", "opened": _iso(now), "by": by}
    path.write_text(_dump(meta, body), encoding="utf-8")
    return path


def _load(path: Path) -> dict | None:
    try:
        post = frontmatter.load(path)
    except Exception:  # noqa: BLE001 — a hand-edited file with broken frontmatter is skipped, not fatal
        return None
    tid = str(post.get("id") or path.stem)
    content = post.content.strip()
    body, _, reply = content.partition(f"\n{REPLY_HEADING}")
    if content.startswith(REPLY_HEADING):
        body, reply = "", content[len(REPLY_HEADING):]
    return {
        "id": tid,
        "title": str(post.get("title") or tid),
        "status": str(post.get("status") or "open"),
        "opened": str(post.get("opened") or ""),
        "closed": str(post.get("closed") or ""),
        "by": str(post.get("by") or ""),
        "body": body.strip(),
        "reply": reply.strip(),
        "path": path,
    }


def list_tickets(repo_dir: str | Path, status: str | None = None) -> list[dict]:
    """Tickets newest first; ``status`` filters to one of open/done/declined."""
    d = Path(repo_dir) / TICKETS_DIR
    if not d.is_dir():
        return []
    out = []
    for p in d.glob("*.md"):
        try:
            p = safe_path(Path(repo_dir), p)
        except UnsafePath:
            continue
        t = _load(p)
        if t is None or (status and t["status"] != status):
            continue
        out.append(t)
    out.sort(key=lambda t: (t["opened"], t["id"]), reverse=True)
    return out


def resolve(repo_dir: str | Path, ticket_id: str, status: str, reply: str, by: str, now: datetime) -> Path:
    """Close a ticket: set status/closed in the frontmatter and append the parent's reply."""
    if status not in CLOSED:
        raise ValueError(f"status must be one of {', '.join(CLOSED)}")
    reply = str(reply).strip()
    if len(reply) < 5:
        raise ValueError("a reply of at least five characters is required")
    path = ticket_path(repo_dir, ticket_id)
    if not path.exists():
        raise FileNotFoundError(f"no ticket {ticket_id}")
    post = frontmatter.load(path)
    if post.get("status") != "open":
        raise ValueError(f"ticket {ticket_id} is already {post.get('status')}")
    meta = dict(post.metadata)
    meta["status"] = status
    meta["closed"] = _iso(now)
    body = post.content.rstrip() + f"\n\n{REPLY_HEADING}\n\n*{by}, {_iso(now)} — {status}*\n\n{reply}\n"
    path.write_text(_dump(meta, body), encoding="utf-8")
    return path


def summary_line(repo_dir: str | Path) -> str:
    """'N open ticket(s): title; title' for the nightly note, or "" when none are open."""
    open_ = list_tickets(repo_dir, "open")
    if not open_:
        return ""
    titles = "; ".join(t["title"] for t in open_[:5]) + (" …" if len(open_) > 5 else "")
    return f"{len(open_)} open ticket(s) for you: {titles}"
