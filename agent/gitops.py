"""Git as Chris: UTC timestamps, her identity, never force."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

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


def commit_all(repo_dir: str | Path, message: str, push: bool = True, run=git) -> str | None:
    """Stage everything, commit as Chris, optionally push. Returns the commit hash or None if nothing changed."""
    run(repo_dir, "add", "-A")
    if not has_changes(repo_dir, run):
        return None
    run(repo_dir, "commit", "-m", message)
    sha = run(repo_dir, "rev-parse", "HEAD").stdout.strip()
    if push:
        run(repo_dir, "push")
    return sha
