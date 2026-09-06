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
7. the parent note (or the diary, if she wrote none) is mailed to both parents
   and filed under ``memory/letters/<date>-to-parents.md``.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from agent import character_diff, gitops, loop, pause, session, tools

log = logging.getLogger("chris.sleep")

PROMPT_FILE = loop.PROMPTS / "sleep.md"
SLEEP_TOOLS = ("recall", "scratch_read", "meters")
SLEEP_EXCLUDED = tuple(t for t in tools.TOOL_NAMES if t not in SLEEP_TOOLS)
MAX_TURNS = 60

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
    mail: dict | None = None


# --- prompt --------------------------------------------------------------------


def _render_record(rec: dict) -> str:
    payload = rec.get("payload", {})
    try:
        body = json.dumps(payload, ensure_ascii=False, default=str)
    except Exception:  # noqa: BLE001
        body = str(payload)
    if len(body) > PAYLOAD_CHARS:
        body = body[:PAYLOAD_CHARS] + "…"
    return f"{rec.get('ref', '')} {str(rec.get('ts', ''))[11:19]} [{rec.get('kind', '')}] {body}"


def render_archive(records: list[dict], limit: int = ARCHIVE_CHARS) -> str:
    """Today's archive, one compact line per record; the middle is dropped if it runs past `limit`."""
    lines = [_render_record(r) for r in records]
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
             "## Today's archive\n" + render_archive(services.archive.read_day(today))]
    character = repo / "memory" / "wiki" / "self" / "character.md"
    if character.exists():
        parts.append("## memory/wiki/self/character.md\n" + loop._read(character).rstrip())
    for p in loop.diary_entries(repo)[-3:]:
        parts.append(f"## memory/diary/{p.name}\n" + loop._read(p).rstrip())
    return "\n\n".join(parts) + "\n"


# --- post-session steps ------------------------------------------------------


def enforce_character(services, before: str, today: str) -> list[str]:
    """Write back character.md minus uncited new diffs; return the rejected lines."""
    path = services.repo_dir / "memory" / "wiki" / "self" / "character.md"
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
    path = services.repo_dir / "memory" / "diary" / name
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
    note = services.repo_dir / "memory" / "parent_note.md"
    if note.exists() and note.read_text(encoding="utf-8").strip():
        return note.read_text(encoding="utf-8"), "parent_note"
    return loop._read(services.repo_dir / "memory" / "diary" / f"{today}.md"), "diary"


def file_parent_note(services, today: str) -> Path | None:
    """Move memory/parent_note.md to memory/letters/<date>-to-parents.md (it is her working file, not the archive)."""
    note = services.repo_dir / "memory" / "parent_note.md"
    if not note.exists():
        return None
    dest = services.repo_dir / "memory" / "letters" / f"{today}-to-parents.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(note.read_text(encoding="utf-8"), encoding="utf-8")
    note.unlink()
    return dest


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
    before = loop._read(character)

    system_prompt = loop._read(loop.PROMPTS / "fixed.md")
    user_prompt = compose_user_prompt(services, today)
    result.session = await session.run_session(
        services, "sleep", system_prompt, user_prompt, tools_allowed=session.BUILTIN_TOOLS,
        max_turns=MAX_TURNS, excluded=SLEEP_EXCLUDED, query_fn=query_fn,
    )

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

    run = git_run or gitops.git
    result.commit = gitops.commit_all(repo, f"sleep: {today}", push=not cfg.dry_run, run=run)

    spend = spend_line(services)
    inbox_count = len(services.mail.list_unread())
    try:
        result.mail = services.mail.daily_summary(today, note_md, result.odometer_line, spend, inbox_count)
    except Exception as exc:  # noqa: BLE001 — the day is saved; mail is best effort
        log.warning("daily_summary failed: %s", exc)
        archive.append("mail_failed", {"kind": "daily_summary", "error": type(exc).__name__})

    archive.append("sleep_done", {
        "date": today, "cost_usd": result.session.cost_usd, "turns": result.session.turns,
        "rejected_diffs": len(result.rejected_diffs), "diary_stubbed": result.diary_stubbed,
        "agent_diary_stubbed": result.agent_diary_stubbed, "unsealed": result.unsealed,
        "ledger_rows": result.ledger_rows, "commit": result.commit, "note_source": result.note_source,
        "transcript": result.session.transcript_ref,
    })
    return result
