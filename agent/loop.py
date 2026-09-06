"""A sitting: gate on pause and budget, compose the prompt, run, redact, commit.

Kinds: birth (first ever), wake, sitting, sunday. Sleep lives in sleep.py.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from agent import gitops, redaction, session

PROMPTS = Path(__file__).parent / "prompts"
KINDS = ("birth", "wake", "sitting", "sunday")
# wake uses the sitting prompt; it is the same shape of work, just first of the day.
PROMPT_FILE = {"birth": "birth.md", "wake": "sitting.md", "sitting": "sitting.md", "sunday": "sunday.md"}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def diary_entries(repo: Path) -> list[Path]:
    """Human diary entries only (the .agent.md twins are for other agents)."""
    return sorted((repo / "memory" / "diary").glob("????-??-??.md"))


def inbox_subjects(mail) -> list[str]:
    subjects = []
    for p in mail.list_unread():
        subject = p.name
        for line in _read(p).splitlines()[:8]:
            if line.startswith("subject:"):
                subject = line[len("subject:"):].strip().strip('"')
                break
        subjects.append(f"- {subject} ({p.name})")
    return subjects


def compose_user_prompt(services, kind: str) -> str:
    repo = services.repo_dir
    parts = [_read(PROMPTS / PROMPT_FILE[kind]).rstrip(), "---"]
    self_dir = repo / "memory" / "wiki" / "self"
    if (self_dir / "character.md").exists():
        parts.append("## memory/wiki/self/character.md\n" + _read(self_dir / "character.md").rstrip())
    if (self_dir / "today.md").exists():
        parts.append("## memory/wiki/self/today.md\n" + _read(self_dir / "today.md").rstrip())
    for p in diary_entries(repo)[-3:]:
        parts.append(f"## memory/diary/{p.name}\n" + _read(p).rstrip())
    handoff = repo / "memory" / "handoff.md"
    if handoff.exists():
        parts.append("## memory/handoff.md\n" + _read(handoff).rstrip())
    subjects = inbox_subjects(services.mail)
    parts.append("## Unread mail\n" + ("\n".join(subjects) if subjects else "(none)"))
    parts.append("## Meters\n" + services.meters_line())
    return "\n\n".join(parts) + "\n"


def sitting_number(services, today: str) -> int:
    day = services.archive.read_day(today)
    return 1 + sum(1 for r in day if r.get("kind") == "session_start" and r.get("payload", {}).get("kind") != "sleep")


def _note_handoff(repo: Path, line: str) -> None:
    path = repo / "memory" / "handoff.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(("\n" if path.exists() and path.stat().st_size else "") + line + "\n")


def redact_and_log(services, ts: str) -> list[dict]:
    """Redact the repo in place; log kinds/counts only (never matched text) beside the private state."""
    report = redaction.clean_tree(services.repo_dir, services.cfg.canaries)
    if report:
        out = services.state_dir.parent / "redaction" / f"{ts}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=1))
        services.archive.append("redaction", {"files": len(report), "report": report})
    return report


async def run_sitting(services, kind: str = "sitting", query_fn=None, git_run=None, max_turns: int = 80):
    if kind not in KINDS:
        raise ValueError(f"unknown sitting kind {kind!r}")
    cfg = services.cfg
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

    if not diary_entries(repo):
        kind = "birth"

    n = sitting_number(services, today)
    system_prompt = _read(PROMPTS / "fixed.md")
    user_prompt = compose_user_prompt(services, kind)

    result = await session.run_session(
        services, kind, system_prompt, user_prompt, tools_allowed=session.BUILTIN_TOOLS,
        max_turns=max_turns, query_fn=query_fn,
    )

    redact_and_log(services, now.strftime("%Y%m%dT%H%M%S"))
    run = git_run or gitops.git
    sha = gitops.commit_all(repo, f"{kind}: {today} sitting {n}", push=not cfg.dry_run, run=run)
    archive.append("sitting_done", {"kind": kind, "n": n, "cost_usd": result.cost_usd, "turns": result.turns,
                                    "commit": sha, "transcript": result.transcript_ref})
    return result
