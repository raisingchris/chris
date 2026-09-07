"""Sleep: consolidate the day, then the housekeeping only Python may do.

The model (with read-only tools: built-ins plus ``recall``, ``scratch_read``,
``meters``) updates the wiki, writes both diaries, proposes character diffs and a
note to her parents. Afterwards, in this order and without the model:

1. character diffs without today's evidence are dropped (invariant 6);
2. missing diaries get a one-line stub so every day has a page;
3. council minutes past their seal date are published;
4. card transactions since yesterday become ledger spend rows;
5. the odometer line is re-rendered;
6. the repo is redacted, committed as Chris ("sleep: <date>") and pushed;
7. the parent note (or the diary, if she wrote none) is mailed to both parents,
   with a line for any open tickets, and filed under
   ``memory/wiki/letters/<date>-to-parents.md``.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from agent import character_diff, gitops, loop, pause, session, tickets, tools, wiring
from agent.paths import UnsafePath, safe_path

log = logging.getLogger("chris.sleep")

PROMPT_FILE = loop.PROMPTS / "sleep.md"
SLEEP_TOOLS = ("recall", "scratch_read", "meters")
SLEEP_EXCLUDED = tuple(t for t in tools.TOOL_NAMES if t not in SLEEP_TOOLS)
MAX_TURNS = 60  # default; Config.sleep_max_turns (SLEEP_MAX_TURNS) overrides

PAYLOAD_CHARS = 600
ARCHIVE_CHARS = 150_000
DIARY_STUB = "No diary written tonight."
AGENT_DIARY_STUB = "No agent diary written tonight."


@dataclass
class SleepResult:
    date: str
    skipped: str | None = None
    session: session.SessionResult | None = None
    rejected_diffs: list[str] = field(default_factory=list)
    diary_stubbed: bool = False
    agent_diary_stubbed: bool = False
    unsealed: int = 0
    ledger_rows: int = 0
    odometer_line: str = ""
    commit: str | None = None
    note_source: str = ""
    letter: Path | None = None
    published: list = field(default_factory=list)
    mail: dict | None = None
    failed: str = ""  # "ErrorType: message" if the model session raised


def _safe(services, rel: str) -> Path | None:
    """Repo path through ``safe_path``; on refusal archive ``unsafe_path`` and return None."""
    try:
        return safe_path(services.repo_dir, rel)
    except UnsafePath as exc:
        log.warning("unsafe path skipped: %s", exc)
        services.archive.append("unsafe_path", {"kind": "unsafe_path", "path": rel, "error": str(exc)})
        return None


# --- prompt --------------------------------------------------------------------


def _render_record(rec: dict, clean=None) -> str:
    payload = rec.get("payload", {})
    try:
        body = json.dumps(payload, ensure_ascii=False, default=str)
    except Exception:  # noqa: BLE001
        body = str(payload)
    if clean is not None:
        body = clean(body)  # before truncation, so a name is never cut into an unrecognisable half
    if len(body) > PAYLOAD_CHARS:
        body = body[:PAYLOAD_CHARS] + "…"
    return f"{rec.get('ref', '')} {str(rec.get('ts', ''))[11:19]} [{rec.get('kind', '')}] {body}"


def render_archive(records: list[dict], limit: int = ARCHIVE_CHARS, clean=None) -> str:
    """Today's archive, one compact line per record; the middle is dropped if it runs past `limit`.

    ``clean`` (``Mail.clean``: handles for parent addresses, then redaction) runs over every line —
    the raw archive may hold a parent's display name or a stranger's address.
    """
    lines = [_render_record(r, clean) for r in records]
    text = "\n".join(lines)
    if len(text) <= limit:
        return text or "(nothing archived today)"
    head, tail = [], []
    used = 0
    half = limit // 2
    for ln in lines:
        if used + len(ln) + 1 > half:
            break
        head.append(ln)
        used += len(ln) + 1
    used = 0
    for ln in reversed(lines):
        if used + len(ln) + 1 > half:
            break
        tail.append(ln)
        used += len(ln) + 1
    tail.reverse()
    dropped = len(lines) - len(head) - len(tail)
    marker = f"[… {dropped} records dropped from the middle; use `recall` to reach them …]"
    return "\n".join(head + [marker] + tail)


def compose_user_prompt(services, today: str) -> str:
    repo = services.repo_dir
    parts = [loop._read(PROMPT_FILE).rstrip(), "---",
             "## Today's archive\n" + render_archive(services.archive.read_day(today), clean=services.mail.clean)]
    character = repo / "memory" / "wiki" / "self" / "character.md"
    if character.exists():
        parts.append("## memory/wiki/self/character.md\n" + loop._rread(services, character).rstrip())
    for p in loop.diary_entries(repo)[-3:]:
        parts.append(f"## memory/diary/{p.name}\n" + loop._rread(services, p).rstrip())
    return "\n\n".join(parts) + "\n"


# --- post-session steps ------------------------------------------------------


def enforce_character(services, before: str, today: str) -> list[str]:
    """Write back character.md minus uncited new diffs; return the rejected lines."""
    path = _safe(services, "memory/wiki/self/character.md")
    if path is None:
        return []
    after = loop._read(path)
    today_refs = {r["ref"] for r in services.archive.read_day(today) if r.get("ref")}
    accepted = character_diff.enforce(before, after, services.archive.get, today_refs)
    rejected = [ln for ln in character_diff.diff_lines(after) if ln not in set(character_diff.diff_lines(accepted))]
    if accepted != after:
        path.write_text(accepted, encoding="utf-8")
    if rejected:
        services.archive.append("character_diff_rejected", {"kind": "character_diff_rejected",
                                                            "n": len(rejected), "lines": rejected})
    return rejected


def ensure_diary(services, today: str, agent: bool) -> bool:
    """Write a one-line stub if the model left no diary; True if stubbed."""
    name = f"{today}.agent.md" if agent else f"{today}.md"
    path = _safe(services, f"memory/diary/{name}")
    if path is None:
        return False
    if path.exists() and path.read_text(encoding="utf-8").strip():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text((AGENT_DIARY_STUB if agent else DIARY_STUB) + "\n", encoding="utf-8")
    services.archive.append("diary_stub", {"path": f"memory/diary/{name}"})
    return True


def settle_card(services, now: datetime) -> int:
    """Card transactions since yesterday → ledger spend rows keyed by transaction id."""
    card = services.card
    if services.cfg.dry_run or not getattr(card, "card_id", None) or not hasattr(card, "transactions"):
        return 0
    since = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    try:
        txns = card.transactions(since.isoformat(timespec="seconds"))
    except Exception as exc:  # noqa: BLE001 — a card outage must not stop sleep
        log.warning("card.transactions failed: %s", exc)
        services.archive.append("card_settle_failed", {"error": type(exc).__name__})
        return 0
    n = 0
    for t in txns:
        if not t.get("ref") or t.get("amount") is None:
            continue
        services.ledger.add("spend", abs(float(t["amount"])), str(t.get("ccy") or "USD"),
                            str(t.get("merchant") or ""), "card", ref=str(t["ref"]))
        n += 1
    if n:
        services.archive.append("card_settled", {"rows": n})
    return n


def spend_line(services) -> str:
    cfg = services.cfg
    return (f"Food bill today ${services.inference.spent():.2f} (soft ${cfg.soft_usd:.0f} / hard ${cfg.hard_usd:.0f}). "
            f"Council this week ${services.council_meter.spent():.2f} of ${cfg.council_weekly_usd:.0f}.")


def parent_note(services, today: str) -> tuple[str, str]:
    """(text, source): her note if she wrote one, else the human diary."""
    note = _safe(services, "memory/parent_note.md")
    if note is not None and note.exists() and note.read_text(encoding="utf-8").strip():
        return note.read_text(encoding="utf-8"), "parent_note"
    return loop._rread(services, services.repo_dir / "memory" / "diary" / f"{today}.md"), "diary"


def file_parent_note(services, today: str) -> Path | None:
    """Move memory/parent_note.md to memory/wiki/letters/<date>-to-parents.md (the site reads that folder)."""
    note = _safe(services, "memory/parent_note.md")
    if note is None or not note.exists():
        return None
    dest = _safe(services, f"memory/wiki/letters/{today}-to-parents.md")
    if dest is None:
        return None
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(note.read_text(encoding="utf-8"), encoding="utf-8")
    note.unlink()
    return dest


def publish_parent_mail(services, today: str) -> list[Path]:
    """Letters between Chris and her parents are public (PRD §11), anonymised.

    Every mail she sent to a parent today (from the archive) and every mail a parent sent her
    (from the inbox) is copied into memory/wiki/letters/ as <date>-to-parents-<n>.md /
    <date>-from-<handle>-<n>.md. Identity redaction runs on the whole repo before commit.
    """
    out: list[Path] = []
    letters = _safe(services, "memory/wiki/letters")
    if letters is None:
        return out
    letters.mkdir(parents=True, exist_ok=True)
    handles = set(services.cfg.parent_handles)
    n = 0
    for rec in services.archive.read_day(today):
        if rec.get("kind") != "mail_out":
            continue
        p = rec.get("payload", {})
        to = p.get("to") or []
        if isinstance(to, str):
            to = [to]
        if not any(t in handles for t in to):
            continue
        n += 1
        dest = letters / f"{today}-to-parents-{n}.md"
        if not dest.exists():
            body = p.get("body", "").split("\n\n— Chris\n")[0]
            dest.write_text(f"---\nfrom: chris\nto: {', '.join(to)}\nsubject: {json.dumps(p.get('subject', ''))}\n"
                            f"archive: {rec.get('ref', '')}\n---\n\n{body}\n", encoding="utf-8")
            out.append(dest)
    inbox = _safe(services, "memory/inbox")
    if inbox is not None and inbox.exists():
        m = 0
        for f in sorted(inbox.glob(f"{today}-*.md")):
            text = f.read_text(encoding="utf-8")
            head = text.split("---", 2)[1] if text.startswith("---") else ""
            sender = ""
            for line in head.splitlines():
                if line.startswith("from:"):
                    sender = line.split(":", 1)[1].strip()
            if sender not in handles:
                continue
            m += 1
            dest = letters / f"{today}-from-{sender}-{m}.md"
            if not dest.exists():
                dest.write_text(text, encoding="utf-8")
                out.append(dest)
    return out


# --- entry point -------------------------------------------------------------


async def run_sleep(services, query_fn=None, git_run=None) -> SleepResult:
    cfg = services.cfg
    repo = services.repo_dir
    archive = services.archive
    now = datetime.now(archive.tz)
    today = now.strftime("%Y-%m-%d")
    result = SleepResult(date=today)

    if pause.is_paused(services.state_dir):
        archive.append("sleep_skipped", {"reason": "paused"})
        result.skipped = "paused"
        return result

    character = repo / "memory" / "wiki" / "self" / "character.md"
    before = loop._rread(services, character)

    system_prompt = loop._read(loop.PROMPTS / "fixed.md")
    user_prompt = compose_user_prompt(services, today)
    try:
        result.session = await session.run_session(
            services, "sleep", system_prompt, user_prompt, tools_allowed=session.BUILTIN_TOOLS,
            max_turns=getattr(cfg, "sleep_max_turns", MAX_TURNS), excluded=SLEEP_EXCLUDED, query_fn=query_fn,
        )
    except Exception as exc:  # noqa: BLE001 — the housekeeping below must still run, and the parents must hear
        result.failed = loop._short(exc)
        log.exception("sleep failed")
        archive.append("sleep_failed", {"date": today, "error": type(exc).__name__, "message": str(exc)[:500]})
        loop._note_handoff(repo, f"Your sleep at {now.strftime('%H:%M')} failed: {result.failed}", archive)
    else:
        if result.session.soft_failed:
            archive.append("sleep_incomplete", {"date": today, "subtype": result.session.subtype,
                                                "turns": result.session.turns})
            loop._note_handoff(repo, f"Your sleep at {now.strftime('%H:%M')} stopped at the turn limit "
                                     f"before finishing ({result.session.subtype}).", archive)

    result.rejected_diffs = enforce_character(services, before, today)
    result.diary_stubbed = ensure_diary(services, today, agent=False)
    result.agent_diary_stubbed = ensure_diary(services, today, agent=True)

    try:
        result.unsealed = len(services.council.unseal_due())
    except Exception as exc:  # noqa: BLE001
        log.warning("council.unseal_due failed: %s", exc)

    result.ledger_rows = settle_card(services, now)

    try:
        result.odometer_line = services.odometer.render_line(services.birthday())
    except Exception as exc:  # noqa: BLE001
        log.warning("odometer.render_line failed: %s", exc)
        result.odometer_line = f"Odometer unavailable ({type(exc).__name__})."

    loop.redact_and_log(services, now.strftime("%Y%m%dT%H%M%S"))

    note_md, result.note_source = parent_note(services, today)
    result.letter = file_parent_note(services, today)
    try:
        result.published = publish_parent_mail(services, today)
    except Exception as exc:  # noqa: BLE001
        log.warning("publish_parent_mail failed: %s", exc)
        result.published = []

    run = git_run or gitops.git
    result.commit = gitops.commit_all(repo, f"sleep: {today}", push=not cfg.dry_run, run=run,
                                      on_push_failed=loop.push_failed_hook(services),
                                      gate=gitops.PushGate.from_services(services))

    spend = spend_line(services)
    inbox_count = len(services.mail.list_unread())
    alert = f"Sleep failed tonight: {result.failed}" if result.failed else ""
    try:
        tickets_line = tickets.summary_line(repo)
    except Exception as exc:  # noqa: BLE001
        log.warning("tickets.summary_line failed: %s", exc)
        tickets_line = ""
    try:
        result.mail = services.mail.daily_summary(today, note_md, result.odometer_line, spend, inbox_count,
                                                  alert=alert, tickets_line=tickets_line)
    except Exception as exc:  # noqa: BLE001 — the day is saved; mail is best effort
        log.warning("daily_summary failed: %s", exc)
        archive.append("mail_failed", {"kind": "daily_summary", "error": type(exc).__name__})

    sess = result.session
    archive.append("sleep_done", {
        "date": today, "cost_usd": sess.cost_usd if sess else 0.0, "turns": sess.turns if sess else 0,
        "rejected_diffs": len(result.rejected_diffs), "diary_stubbed": result.diary_stubbed,
        "agent_diary_stubbed": result.agent_diary_stubbed, "unsealed": result.unsealed,
        "ledger_rows": result.ledger_rows, "commit": result.commit, "note_source": result.note_source,
        "transcript": sess.transcript_ref if sess else None, "failed": result.failed or None,
    })
    wiring.note_last_run(services.state_dir, "last_sleep_done", tz=archive.tz, ok=not result.failed)
    return result
