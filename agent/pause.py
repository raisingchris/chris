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
from datetime import datetime, timezone
from pathlib import Path

from agent import gitops, redaction

log = logging.getLogger("chris.pause")

FLAG = "paused"
PAUSE_LOG = Path("governance") / "pause_log.md"
INBOX_NOTE = Path("memory") / "inbox" / "PAUSED.md"


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


def redact_files(repo: Path, paths: list[str], canaries: list[str]) -> list[dict]:
    """Run ``redaction.redact`` over the given repo files in place; report kinds/counts per path."""
    report = []
    for rel in paths:
        p = repo / rel
        if not p.is_file() or p.is_symlink():
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        clean, hits = redaction.redact(text, list(canaries))
        if hits:
            p.write_text(clean, encoding="utf-8")
            report.append({"path": rel, "kinds": [h["kind"] for h in hits], "count": sum(h["count"] for h in hits)})
    return report


def commit_as_parent(repo_dir: str | os.PathLike, message: str, paths: list[str], dry_run: bool = False,
                     canaries: list[str] | tuple[str, ...] = (), push: bool = False,
                     gate: gitops.PushGate | None = None, run=None) -> bool:
    """Redact ``paths`` in place, ``git add -- <paths>`` (never ``-A``) and commit as Parent, UTC.

    Skipped (False) on dry-run, no repo or empty ``paths``. With ``push`` the commit goes out
    through the gated ``gitops.push_repo``; a refused or failed push still returns True (committed).
    """
    repo = Path(repo_dir)
    paths = [str(p) for p in paths if str(p)]
    if dry_run or not (repo / ".git").exists() or not paths:
        log.info("commit skipped (%s): %s", "dry_run" if dry_run else "no git or no paths", message)
        return False
    redact_files(repo, paths, list(canaries))
    run = run or gitops.git_as_parent
    try:
        run(repo, "add", "--", *paths)
        run(repo, "commit", "-q", "-m", message, "--", *paths)
    except Exception as e:  # noqa: BLE001 — CalledProcessError, missing git
        err = getattr(e, "stderr", "") or str(e)
        log.warning("commit failed: %s", str(err).strip()[:500])
        return False
    if push:
        ok, err = gitops.push_repo(repo, run, gate)
        if not ok:
            log.warning("push after parent commit failed: %s", err)
            if gate is not None:
                gate.archive("push_failed", {"stderr": err[:500]})
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

    commit_as_parent(repo, "governance: paused", [PAUSE_LOG.as_posix()], dry_run=cfg.dry_run,
                     canaries=cfg.canaries, push=True, gate=gitops.PushGate.from_services(services))
    services.archive.append("pause", {"kind": "pause", "reason": reason, "by": by_handle})

    body = (
        f"Chris was paused by {by_handle}.\n\nReason: {reason}\n\n"
        "The card is frozen and no sittings will run until she is unpaused from the parent page. "
        "Nothing was deleted."
    )
    try:
        services.mail.send(list(cfg.parent_handles), "Chris paused", body)
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
    commit_as_parent(repo, "governance: unpaused", [PAUSE_LOG.as_posix()], dry_run=cfg.dry_run,
                     canaries=cfg.canaries, push=True, gate=gitops.PushGate.from_services(services))
    services.archive.append("unpause", {"kind": "unpause", "by": by_handle})
