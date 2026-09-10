"""A sitting: gate on pause and budget, compose the prompt, run, redact, commit.

Kinds: birth (first ever), wake, sitting, sunday, mail (an extra sitting because
mail arrived), continue (the last sitting ended with work pending). Sleep lives in sleep.py.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from agent import gitops, redaction, session, wiring
from agent.paths import UnsafePath, safe_path

log = logging.getLogger("chris.loop")

PROMPTS = Path(__file__).parent / "prompts"
KINDS = ("birth", "wake", "sitting", "sunday", "mail", "continue")
# wake, mail and continue use the sitting prompt; same shape of work, just first of the day /
# woken by mail / picking up where the last one left off.
PROMPT_FILE = {"birth": "birth.md", "wake": "sitting.md", "sitting": "sitting.md", "sunday": "sunday.md",
               "mail": "sitting.md", "continue": "sitting.md"}
# One line the loop puts above the prompt file for some kinds (the prompt files stay generic).
KIND_HEADER = {
    "mail": "You were woken by new mail.",
    "continue": "You are continuing: your last sitting ended with work pending. Pick it up from the handoff.",
}

# Handoff lines that mean "there is more to do" / "there is not" (matched case-insensitively at line start).
PENDING_PREFIXES = ("next:", "- [ ]", "todo:", "pending:")
NOTHING_PENDING = ("nothing pending", "done for now", "no work pending")


def handoff_has_pending(text: str) -> bool:
    """Pure: does a handoff say work is still pending?

    True when some line starts with ``next:``, ``- [ ]``, ``todo:`` or ``pending:`` and no line
    is ``nothing pending`` / ``done for now`` / ``no work pending`` (all case-insensitive; a
    trailing full stop is tolerated). The closing line wins, so she can stop the chain.
    """
    lines = [ln.strip().lower() for ln in (text or "").splitlines()]
    if any(ln.rstrip(".!") in NOTHING_PENDING for ln in lines):
        return False
    return any(ln.startswith(PENDING_PREFIXES) for ln in lines)


def _read(path: Path, repo: Path | None = None, archive=None) -> str:
    """Read a text file, or "" if missing. Repo files go through ``safe_path`` (symlinks refused)."""
    if repo is not None:
        try:
            path = safe_path(repo, path)
        except UnsafePath as exc:
            log.warning("unsafe path skipped: %s", exc)
            if archive is not None:
                archive.append("unsafe_path", {"kind": "unsafe_path", "path": str(path), "error": str(exc)})
            return ""
    try:
        return path.read_text(encoding="utf-8") if path.exists() else ""
    except OSError:
        return ""


def _rread(services, path: Path) -> str:
    """``_read`` for a file inside her repo."""
    return _read(path, services.repo_dir, services.archive)


def diary_entries(repo: Path) -> list[Path]:
    """Human diary entries only (the .agent.md twins are for other agents)."""
    return sorted((repo / "memory" / "diary").glob("????-??-??.md"))


def inbox_subjects(mail) -> list[str]:
    subjects = []
    for p in mail.list_unread():
        subject = p.name
        for line in _read(p).splitlines()[:8]:  # list_unread already refused symlinks
            if line.startswith("subject:"):
                subject = line[len("subject:"):].strip().strip('"')
                break
        subjects.append(f"- {subject} ({p.name})")
    return subjects


def compose_user_prompt(services, kind: str) -> str:
    repo = services.repo_dir
    parts = [_read(PROMPTS / PROMPT_FILE[kind]).rstrip(), "---"]
    if kind in KIND_HEADER:
        parts.insert(0, KIND_HEADER[kind])
    self_dir = repo / "memory" / "wiki" / "self"
    if (self_dir / "character.md").exists():
        parts.append("## memory/wiki/self/character.md\n" + _rread(services, self_dir / "character.md").rstrip())
    if (self_dir / "today.md").exists():
        parts.append("## memory/wiki/self/today.md\n" + _rread(services, self_dir / "today.md").rstrip())
    if (self_dir / "commitments.md").exists():
        # Promises to others live in their own file, not in plan lines (Cairn's advice, 2026-09-09):
        # a promise kept only in a handoff dies in a paraphrase. Read before anything goes out.
        parts.append("## memory/wiki/self/commitments.md\n" + _rread(services, self_dir / "commitments.md").rstrip())
    for p in diary_entries(repo)[-3:]:
        parts.append(f"## memory/diary/{p.name}\n" + _rread(services, p).rstrip())
    handoff = repo / "memory" / "handoff.md"
    if handoff.exists():
        parts.append("## memory/handoff.md\n" + _rread(services, handoff).rstrip())
    subjects = inbox_subjects(services.mail)
    parts.append("## Unread mail\n" + ("\n".join(subjects) if subjects else "(none)"))
    parts.append("## Meters\n" + services.meters_line())
    return "\n\n".join(parts) + "\n"


def is_birth(services) -> bool:
    """Her first sitting ever: no diary yet *and* no birth session in the archive.

    The archive decides, not the diary: a birth that failed or ended before a diary was written
    must not be repeated — the next sitting is an ordinary one (the handoff says what happened).
    """
    if diary_entries(services.repo_dir):
        return False
    return not services.archive.any("session_start", "birth")


def sitting_number(services, today: str) -> int:
    day = services.archive.read_day(today)
    return 1 + sum(1 for r in day if r.get("kind") == "session_start" and r.get("payload", {}).get("kind") != "sleep")


def _note_handoff(repo: Path, line: str, archive=None) -> None:
    try:
        path = safe_path(repo, Path("memory") / "handoff.md")
    except UnsafePath as exc:
        log.warning("handoff not written: %s", exc)
        if archive is not None:
            archive.append("unsafe_path", {"kind": "unsafe_path", "path": "memory/handoff.md", "error": str(exc)})
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(("\n" if path.exists() and path.stat().st_size else "") + line + "\n")


def _short(exc: BaseException, limit: int = 300) -> str:
    return f"{type(exc).__name__}: {str(exc)[:limit]}"


def push_failed_hook(services):
    """``on_push_failed`` for commit_all: archive the stderr excerpt, never raise."""
    def hook(err: str) -> None:
        log.warning("git push failed: %s", err)
        services.archive.append("push_failed", {"kind": "push_failed", "stderr": err[:500]})
    return hook


def redact_and_log(services, ts: str) -> list[dict]:
    """Redact the repo in place; log kinds/counts only (never matched text) beside the private state."""
    report = redaction.clean_tree(services.repo_dir, services.cfg.canaries, exclude=redaction.CONTENT_EXCLUDE)
    if report:
        out = services.state_dir.parent / "redaction" / f"{ts}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=1))
        services.archive.append("redaction", {"files": len(report), "report": report})
    return report


async def run_sitting(services, kind: str = "sitting", query_fn=None, git_run=None, max_turns: int | None = None):
    if kind not in KINDS:
        raise ValueError(f"unknown sitting kind {kind!r}")
    cfg = services.cfg
    if max_turns is None:
        max_turns = getattr(cfg, "max_turns", 80)
    repo = services.repo_dir
    archive = services.archive
    now = datetime.now(archive.tz)
    today = now.strftime("%Y-%m-%d")

    if (services.state_dir / "paused").exists():
        archive.append("sitting_skipped", {"kind": kind, "reason": "paused"})
        return None

    if services.inference.exceeded(cfg.hard_usd):
        spent = services.inference.spent()
        line = f"Sitting skipped: daily food bill hit the hard cap (${spent:.2f} of ${cfg.hard_usd:.2f})."
        archive.append("sitting_skipped", {"kind": kind, "reason": "hard_cap", "spent_usd": spent, "cap_usd": cfg.hard_usd})
        _note_handoff(repo, line)
        return None

    if is_birth(services):
        kind = "birth"

    n = sitting_number(services, today)
    system_prompt = _read(PROMPTS / "fixed.md")
    user_prompt = compose_user_prompt(services, kind)

    result = None
    failure: BaseException | None = None
    try:
        result = await session.run_session(
            services, kind, system_prompt, user_prompt, tools_allowed=session.BUILTIN_TOOLS,
            max_turns=max_turns, query_fn=query_fn,
        )
    except Exception as exc:  # noqa: BLE001 — a failed sitting must still be visible, redacted and committed
        failure = exc
        log.exception("%s sitting failed", kind)
        archive.append("sitting_failed", {"kind": kind, "n": n, "error": type(exc).__name__,
                                          "message": str(exc)[:500]})
        _note_handoff(repo, f"Your {kind} at {now.strftime('%H:%M')} failed: {_short(exc)}", archive)
    else:
        if result.soft_failed:
            archive.append("sitting_incomplete", {"kind": kind, "n": n, "subtype": result.subtype,
                                                  "turns": result.turns, "cost_usd": result.cost_usd})
            _note_handoff(repo, f"Your {kind} at {now.strftime('%H:%M')} stopped at the turn limit "
                                f"before finishing ({result.subtype}).", archive)

    redact_and_log(services, now.strftime("%Y%m%dT%H%M%S"))
    run = git_run or gitops.git
    sha = gitops.commit_all(repo, f"{kind}: {today} sitting {n}", push=not cfg.dry_run, run=run,
                            on_push_failed=push_failed_hook(services), gate=gitops.PushGate.from_services(services))
    if failure is None:
        archive.append("sitting_done", {"kind": kind, "n": n, "cost_usd": result.cost_usd, "turns": result.turns,
                                        "commit": sha, "transcript": result.transcript_ref})
    wiring.note_last_run(services.state_dir, "last_sitting_done", tz=archive.tz, kind=kind,
                         ok=failure is None and not result.soft_failed)
    if failure is None:
        pending = handoff_has_pending(_rread(services, repo / "memory" / "handoff.md"))
        archive.append("sitting_pending", {"kind": "sitting_pending", "pending": pending})
        if pending:
            _request_continuation(services)
    return result


def _request_continuation(services) -> None:
    """Ask the clock for a sitting ``CONTINUATION_MINUTES`` out; a no-op without a scheduler, never raises."""
    sched = getattr(services, "scheduler", None)
    if sched is None:
        return
    try:
        from agent import scheduler as scheduler_module

        scheduler_module.request_continuation(services, sched)
    except Exception as exc:  # noqa: BLE001 — the sitting is already committed; a continuation is a bonus
        log.warning("continuation request failed: %s", exc)
