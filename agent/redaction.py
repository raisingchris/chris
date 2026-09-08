"""Redaction of identifying strings before anything reaches the public repo.

Every specific identifier (parent names, emails, holdco, city, country code,
timezone name…) comes from the caller as a *canary* (see ``Config.canaries``,
env ``REDACT_CANARIES``). This module itself only knows generic shapes:
foreign e-mail addresses, phone numbers and ``UTC±N`` offsets — nothing in
this source names anyone or anywhere. Reports and errors only ever carry
*kinds and counts* — never the matched text — so the canaries cannot leak
through logs.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Iterable

TOKEN = "[redacted]"
KEEP_DOMAINS = {"raisingchris.com"}
DEFAULT_EXCLUDE = ("memory/scratchpad", ".git", ".venv", "site/out")
# Only her prose is redacted. Code and tests legitimately contain emails and phone-shaped strings.
# memory/inbox is git-ignored and never published; strangers' addresses must survive there so she can reply.
CONTENT_EXCLUDE = DEFAULT_EXCLUDE + ("memory/inbox", "agent", "tests", "site", "scripts", ".github", ".githooks", "pyproject.toml", "Dockerfile", "fly.toml", "vercel.json", ".vercelignore")
MAX_BYTES = 5 * 1024 * 1024

_SEP = r"[\s.\-_]"
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
# candidate phone: optional +CC or (area), then 7-15 digits with optional single separators
_PHONE = re.compile(
    r"(?<![\w+])(?:\+\d{1,3}[ .-]?|\(\d{2,4}\)[ .-]?)?\d(?:[ .-]?\d){6,14}(?!\w)"
)
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# a date followed by a clock time ("2026-09-07 14:30", "2026-09-07 09") is a timestamp, not a phone
_DATE_TIME = re.compile(r"^\d{4}-\d{2}-\d{2}[ T.-]\d{1,2}")
# eight digits as two groups of four ("9123 4567"): a local mobile number in several countries
_LOCAL_8 = re.compile(r"^\d{4}[ -]\d{4}$")
# Generic only: a UTC offset gives away a timezone band. Anything named is a canary.
_PATTERNS = re.compile(r"\bUTC\s?[+\-−]\s?\d{1,2}(?::?\d{2})?\b", re.IGNORECASE)


class RedactionError(Exception):
    """Raised by assert_clean; message lists paths and kinds only."""


def _canary_regex(canaries: Iterable[str]) -> re.Pattern | None:
    parts = []
    for c in sorted((c.strip() for c in canaries if c and c.strip()), key=len, reverse=True):
        tokens = [re.escape(t) for t in re.split(_SEP + "+", c) if t]
        if tokens:
            parts.append(f"{_SEP}*".join(tokens))
    if not parts:
        return None
    return re.compile(r"(?<!\w)(?:" + "|".join(parts) + r")(?!\w)", re.IGNORECASE)


def _is_phone(m: re.Match) -> bool:
    s = m.group(0)
    digits = sum(ch.isdigit() for ch in s)
    if not 8 <= digits <= 15:
        return False
    if _DATE_TIME.match(s):
        return False
    if s[0] in "+(":
        return True
    if _LOCAL_8.match(s):
        return True
    return digits >= 9 and not _ISO_DATE.match(s) and not s.isdigit()


def _is_foreign_email(m: re.Match) -> bool:
    domain = m.group(0).rsplit("@", 1)[1].lower()
    return domain not in KEEP_DOMAINS


def redact(text: str, canaries: list[str]) -> tuple[str, list[dict]]:
    """Return (clean_text, report). Report entries: {"kind", "count"} only."""
    counts: dict[str, int] = {}

    def sub(kind: str, pattern: re.Pattern, text: str, accept=lambda m: True) -> str:
        def repl(m: re.Match) -> str:
            if not accept(m):
                return m.group(0)
            counts[kind] = counts.get(kind, 0) + 1
            return TOKEN

        return pattern.sub(repl, text)

    canary_re = _canary_regex(canaries)
    if canary_re is not None:
        text = sub("canary", canary_re, text)
    text = sub("email", _EMAIL, text, _is_foreign_email)
    text = sub("phone", _PHONE, text, _is_phone)
    text = sub("pattern", _PATTERNS, text)
    report = [{"kind": k, "count": counts[k]} for k in ("canary", "email", "phone", "pattern") if k in counts]
    return text, report


def _text_files(root: Path, exclude: Iterable[str]):
    root = Path(root)
    excluded = tuple(Path(e).as_posix().rstrip("/") for e in exclude)
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = Path(dirpath).relative_to(root).as_posix()
        dirnames[:] = sorted(
            d for d in dirnames
            if (d if rel_dir == "." else f"{rel_dir}/{d}") not in excluded
        )
        for name in sorted(filenames):
            path = Path(dirpath) / name
            rel = path.relative_to(root).as_posix()
            if rel in excluded or path.is_symlink():
                continue
            try:
                if path.stat().st_size > MAX_BYTES:
                    continue
                raw = path.read_bytes()
            except OSError:
                continue
            if b"\x00" in raw[:8192]:
                continue
            try:
                yield rel, path, raw.decode("utf-8")
            except UnicodeDecodeError:
                continue


def scan_tree(root: Path, canaries: list[str], exclude: Iterable[str] = DEFAULT_EXCLUDE) -> list[dict]:
    """List files containing redactable text: {"path", "kinds", "count"}."""
    hits = []
    for rel, _, text in _text_files(root, exclude):
        _, report = redact(text, canaries)
        if report:
            hits.append({
                "path": rel,
                "kinds": [r["kind"] for r in report],
                "count": sum(r["count"] for r in report),
            })
    return hits


def assert_clean(root: Path, canaries: list[str], exclude: Iterable[str] = DEFAULT_EXCLUDE) -> None:
    hits = scan_tree(root, canaries, exclude)
    if hits:
        lines = [f"{h['path']}: {', '.join(h['kinds'])} ({h['count']})" for h in hits]
        raise RedactionError("redactable text found in:\n  " + "\n  ".join(lines))


def clean_tree(root: Path, canaries: list[str], exclude: Iterable[str] = DEFAULT_EXCLUDE) -> list[dict]:
    """Rewrite files in place through redact(); return the scan report of what was changed."""
    hits = []
    for rel, path, text in _text_files(root, exclude):
        clean, report = redact(text, canaries)
        if report:
            path.write_text(clean, encoding="utf-8")
            hits.append({
                "path": rel,
                "kinds": [r["kind"] for r in report],
                "count": sum(r["count"] for r in report),
            })
    return hits
