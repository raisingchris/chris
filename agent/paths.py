"""Symlink-safe paths for everything brain reads or writes inside her repo.

Chris can create files in the working tree; brain (a different OS user with the
secrets) later reads and rewrites some of them. A symlink she planted could point
brain at /data/state or her parents' mail. ``safe_path`` refuses any path with a
symlink anywhere in the chain below the repo root, or that resolves outside it.
"""

from __future__ import annotations

import os
from pathlib import Path


class UnsafePath(Exception):
    """The path is a symlink, passes through one, or escapes the repo."""


def _lexical_rel(repo: Path, p: Path) -> Path | None:
    """``p`` relative to ``repo`` without touching the filesystem, or None."""
    try:
        rel = Path(os.path.normpath(p)).relative_to(Path(os.path.normpath(repo)))
    except ValueError:
        return None
    return None if ".." in rel.parts else rel


def safe_path(repo_dir: str | Path, rel_or_abs: str | Path) -> Path:
    """Return the absolute path inside ``repo_dir`` or raise ``UnsafePath``.

    Missing tail components are allowed (the caller may be about to create the
    file); every component that exists is checked for being a symlink.
    """
    repo_given = Path(repo_dir)
    repo = repo_given.resolve()
    p = Path(rel_or_abs)
    if not p.is_absolute():
        p = repo_given / p
    rel = _lexical_rel(repo_given, p)
    if rel is None:
        rel = _lexical_rel(repo, p)
    if rel is None:
        raise UnsafePath(f"{rel_or_abs} is outside the repository")
    cur = repo
    for part in rel.parts:
        cur = cur / part
        if cur.is_symlink():
            raise UnsafePath(f"{cur.relative_to(repo)} is a symlink")
    try:
        cur.resolve(strict=False).relative_to(repo)
    except ValueError:
        raise UnsafePath(f"{rel_or_abs} resolves outside the repository") from None
    return cur
