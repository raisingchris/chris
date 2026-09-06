"""Pause, never kill.

A pause is a flag file in ``<state_dir>/paused``. The scheduler checks it before
every job; nothing else changes. On pause the card is frozen, a dated line goes
into ``governance/pause_log.md`` (handle only — never a real identity), Chris gets
``memory/inbox/PAUSED.md`` so she reads why when she wakes, both parents get mail,
and the archive records it. ``release`` undoes the flag and the freeze.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger("chris.pause")

FLAG = "paused"
PAUSE_LOG = Path("governance") / "pause_log.md"
INBOX_NOTE = Path("memory") / "inbox" / "PAUSED.md"

PARENT_GIT_ENV = {
    "TZ": "UTC",
    "GIT_AUTHOR_NAME": "Parent",
    "GIT_AUTHOR_EMAIL": "parent@raisingchris.com",
    "GIT_COMMITTER_NAME": "Parent",
    "GIT_COMMITTER_EMAIL": "parent@raisingchris.com",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def flag_path(state_dir: str | os.PathLike) -> Path:
    return Path(state_dir) / FLAG


def is_paused(state_dir: str | os.PathLike) -> bool:
    return flag_path(state_dir).exists()


def status(state_dir: str | os.PathLike) -> dict | None:
    """The pause record (reason, by, at) or None when not paused."""
    p = flag_path(state_dir)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text() or "{}")
    except json.JSONDecodeError:
        return {"reason": "", "by": "", "at": ""}


def commit_as_parent(repo_dir: str | os.PathLike, message: str, dry_run: bool = False) -> bool:
    """``git add -A && git commit`` as Parent, UTC. Skipped (False) on dry-run or no repo."""
    repo = Path(repo_dir)
    if dry_run or not (repo / ".git").exists():
        log.info("commit skipped (%s): %s", "dry_run" if dry_run else "no git", message)
        return False
    env = {**os.environ, **PARENT_GIT_ENV}
    try:
        subprocess.run(["git", "add", "-A"], cwd=repo, env=env, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-q", "-m", message], cwd=repo, env=env, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        log.warning("commit failed: %s", (e.stderr or b"").decode(errors="replace").strip())
        return False
    return True


def _append_log(repo: Path, line: str) -> None:
    path = repo / PAUSE_LOG
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("# Pause log\n\nEvery pause and unpause, dated. Conditions are in `pause_conditions.md`.\n")
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"\n- {line}\n")


def trigger(services, reason: str, by_handle: str) -> dict:
    """Pause Chris. Idempotent: pausing twice updates the reason and re-logs."""
    cfg = services.cfg
    repo = Path(cfg.repo_dir)
    at = _now().isoformat(timespec="seconds")
    record = {"reason": reason, "by": by_handle, "at": at}

    flag = flag_path(cfg.state_dir)
    flag.parent.mkdir(parents=True, exist_ok=True)
    flag.write_text(json.dumps(record, indent=1))

    try:
        services.card.freeze()
    except Exception as e:  # noqa: BLE001 — a card outage must not block a pause
        log.warning("card.freeze failed during pause: %s", e)

    _append_log(repo, f"{at[:10]} — Paused by a parent. Reason: {reason}")

    note = repo / INBOX_NOTE
    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text(
        "---\n"
        "from: parents\n"
        'subject: "You are paused"\n'
        f"received: {at}\n"
        "---\n\n"
        f"{reason}\n\n"
        "You're paused. Nothing was deleted. Reply on the record when you're back.\n"
    )

    commit_as_parent(repo, "governance: paused", dry_run=cfg.dry_run)
    services.archive.append("pause", {"kind": "pause", "reason": reason, "by": by_handle})

    body = (
        f"Chris was paused by {by_handle}.\n\nReason: {reason}\n\n"
        "The card is frozen and no sittings will run until she is unpaused from the parent page. "
        "Nothing was deleted."
    )
    try:
        services.mail.send(["parent-a", "parent-b"], "Chris paused", body)
    except Exception as e:  # noqa: BLE001
        log.warning("pause mail failed: %s", e)
    return record


def release(services, by_handle: str) -> None:
    """Lift the pause. Safe to call when not paused."""
    cfg = services.cfg
    repo = Path(cfg.repo_dir)
    flag = flag_path(cfg.state_dir)
    if flag.exists():
        flag.unlink()

    try:
        services.card.unfreeze()
    except Exception as e:  # noqa: BLE001
        log.warning("card.unfreeze failed during release: %s", e)

    _append_log(repo, f"{_now().date().isoformat()} — Unpaused.")
    commit_as_parent(repo, "governance: unpaused", dry_run=cfg.dry_run)
    services.archive.append("unpause", {"kind": "unpause", "by": by_handle})
