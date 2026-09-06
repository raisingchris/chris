"""Invariant 6: every change to `memory/wiki/self/character.md` cites the archive.

Diff lines live under a `## Diffs` heading, one per line:

    - 2026-09-07 — I answer mail before I start work — evidence: archive:2026-09-07#12

`validate` lists problems in a page; `enforce` takes the page as it was and as
sleep left it, and returns the accepted text: new diff lines that are malformed
or cite a record the archive does not have are dropped, everything else stays.

Public API: ``validate``, ``enforce``, ``diff_lines``, ``DIFF_RE``.
"""

from __future__ import annotations

import re
from typing import Callable

from agent.archive import is_valid_ref

DIFFS_HEADING = "## Diffs"
DIFF_RE = re.compile(
    r"^- (?P<date>\d{4}-\d{2}-\d{2}) — (?P<text>.+?) — evidence: (?P<ref>archive:\d{4}-\d{2}-\d{2}#\d+)\s*$"
)

ArchiveGet = Callable[[str], dict]


def _split(text: str) -> tuple[list[str], list[str], list[str]]:
    """(lines before the heading, heading line, lines of the Diffs section)."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.strip() == DIFFS_HEADING:
            for j in range(i + 1, len(lines)):
                if lines[j].startswith("## "):
                    return lines[: i + 1], lines[i + 1 : j], lines[j:]
            return lines[: i + 1], lines[i + 1 :], []
    return lines, [], []


def diff_lines(text: str) -> list[str]:
    """Non-blank lines in the Diffs section, as written."""
    _, body, _ = _split(text)
    return [ln for ln in body if ln.strip()]


def _ref_exists(ref: str, archive_get: ArchiveGet | None) -> bool:
    if not is_valid_ref(ref):
        return False
    if archive_get is None:
        return True
    try:
        archive_get(ref)
        return True
    except (KeyError, ValueError, FileNotFoundError):
        return False


def _check(lines: list[str], today_refs: set[str] | None, archive_get: ArchiveGet | None) -> list[tuple[str, str]]:
    """(line, problem) for every diff line that fails."""
    out = []
    for ln in lines:
        m = DIFF_RE.match(ln)
        if not m:
            out.append((ln, "malformed diff line (need `- <date> — <text> — evidence: archive:YYYY-MM-DD#N`)"))
            continue
        ref = m.group("ref")
        if not _ref_exists(ref, archive_get):
            out.append((ln, f"evidence {ref} is not in the archive"))
        elif today_refs is not None and ref not in today_refs:
            out.append((ln, f"evidence {ref} is not from today"))
    return out


def validate(character_md: str, today_refs: set[str] | None = None,
             archive_get: ArchiveGet | None = None) -> list[str]:
    """Problems with the page's diff lines, as plain sentences.

    `archive_get` (e.g. Archive.get) must raise KeyError for a missing ref.
    `today_refs`, when given, additionally requires each cited ref to be one of today's.
    """
    return [f"{problem}: {ln}" for ln, problem in _check(diff_lines(character_md), today_refs, archive_get)]


def enforce(before: str, after: str, archive_get: ArchiveGet | None = None,
            today_refs: set[str] | None = None) -> str:
    """Accept `after` minus any newly added diff line that fails validation."""
    old = set(diff_lines(before))
    new = {ln for ln in diff_lines(after) if ln not in old}
    if not new:
        return after
    bad = {ln for ln, _ in _check(sorted(new), today_refs, archive_get)}
    if not bad:
        return after
    head, body, tail = _split(after)
    kept = [ln for ln in body if ln not in bad]
    out = "\n".join(head + kept + tail)
    return out + ("\n" if after.endswith("\n") else "")
