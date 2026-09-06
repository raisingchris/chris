"""Git as Chris: UTC timestamps, her identity, never force."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Callable

CHRIS_NAME = "Chris"
CHRIS_EMAIL = "chris@raisingchris.com"


def git(repo_dir: str | Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "TZ": "UTC",
        "GIT_AUTHOR_NAME": CHRIS_NAME,
        "GIT_AUTHOR_EMAIL": CHRIS_EMAIL,
        "GIT_COMMITTER_NAME": CHRIS_NAME,
        "GIT_COMMITTER_EMAIL": CHRIS_EMAIL,
    }
    return subprocess.run(["git", *args], cwd=str(repo_dir), env=env, capture_output=True, text=True, check=check)


def has_changes(repo_dir: str | Path, run=git) -> bool:
    return bool(run(repo_dir, "status", "--porcelain").stdout.strip())


def push_repo(repo_dir: str | Path, run=git) -> tuple[bool, str]:
    """Push; never raises. Returns (ok, stderr excerpt). A failed push leaves the commit local."""
    try:
        r = run(repo_dir, "push", check=False)
    except Exception as exc:  # noqa: BLE001 — git missing, network down, timeout
        return False, f"{type(exc).__name__}: {exc}"[:500]
    if getattr(r, "returncode", 0) != 0:
        return False, str(getattr(r, "stderr", "") or "").strip()[:500]
    return True, ""


def unpushed_count(repo_dir: str | Path, run=git) -> int:
    """Commits ahead of the upstream branch; 0 on any error (no upstream, no git)."""
    try:
        r = run(repo_dir, "rev-list", "--count", "@{u}..HEAD", check=False)
        return int(str(r.stdout).strip() or 0) if getattr(r, "returncode", 0) == 0 else 0
    except Exception:  # noqa: BLE001
        return 0


def commit_all(repo_dir: str | Path, message: str, push: bool = True, run=git,
               on_push_failed: Callable[[str], None] | None = None) -> str | None:
    """Stage everything, commit as Chris, optionally push. Returns the commit hash or None if nothing changed.

    A push failure is not fatal: the commit stays local, ``on_push_failed(stderr)`` is called.
    """
    run(repo_dir, "add", "-A")
    if not has_changes(repo_dir, run):
        return None
    run(repo_dir, "commit", "-m", message)
    sha = run(repo_dir, "rev-parse", "HEAD").stdout.strip()
    if push:
        ok, err = push_repo(repo_dir, run)
        if not ok and on_push_failed is not None:
            on_push_failed(err)
    return sha
