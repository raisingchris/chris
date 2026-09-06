"""No identifying fragment anywhere in the tracked tree.

The repo goes public and must never name the parents, their company or their
city. The forbidden list itself must not live in the repo, so it comes from the
environment: run locally as

    IDENTITY_FORBIDDEN="Real Name,Holdco,City,+CC" .venv/bin/pytest tests/test_no_identity_strings.py

Skipped when the variable is unset. Matching is case-insensitive over every
text file ``git ls-files`` reports; failures name the file and the fragment's
*index* in the list, never the fragment.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def _forbidden() -> list[str]:
    return [s.strip() for s in os.environ.get("IDENTITY_FORBIDDEN", "").split(",") if s.strip()]


def tracked_text_files(repo: Path) -> list[Path]:
    try:
        out = subprocess.run(["git", "ls-files", "-z"], cwd=repo, capture_output=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("not a git checkout")
    files = []
    for rel in out.decode("utf-8", errors="replace").split("\0"):
        if not rel:
            continue
        p = repo / rel
        if not p.is_file() or p.is_symlink():
            continue
        try:
            head = p.read_bytes()[:8192]
        except OSError:
            continue
        if b"\x00" in head:
            continue
        files.append(p)
    return files


def test_no_forbidden_fragment_in_tracked_files():
    forbidden = _forbidden()
    if not forbidden:
        pytest.skip("IDENTITY_FORBIDDEN not set")
    hits = []
    for p in tracked_text_files(REPO):
        try:
            text = p.read_text(encoding="utf-8", errors="replace").lower()
        except OSError:
            continue
        for i, frag in enumerate(forbidden):
            if frag.lower() in text:
                hits.append(f"{p.relative_to(REPO)}: fragment #{i}")
    assert not hits, "identifying fragments found:\n  " + "\n  ".join(hits)


def test_helper_finds_a_planted_fragment(tmp_path, monkeypatch):
    """Sanity check of the scan itself, with a throwaway git repo and a made-up fragment."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / "a.md").write_text("Nothing here about Zenda.\n")
    (tmp_path / "b.bin").write_bytes(b"Zenda\x00binary")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    files = tracked_text_files(tmp_path)
    assert [p.name for p in files] == ["a.md"]
    assert any("zenda" in p.read_text().lower() for p in files)
