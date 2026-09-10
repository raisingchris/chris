"""Append-only event archive: one JSONL file per day, one JSON object per line.

Invariant: this module only ever appends. No code path here may delete or
shorten an archive file; tests/test_archive.py greps this source to enforce it.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

REF_RE = re.compile(r"^archive:(\d{4}-\d{2}-\d{2})#([1-9]\d*)$")


def is_valid_ref(s: str) -> bool:
    return isinstance(s, str) and REF_RE.match(s) is not None


def _parse_ref(ref: str) -> tuple[str, int]:
    m = REF_RE.match(ref)
    if not m:
        raise ValueError(f"not an archive ref: {ref!r}")
    return m.group(1), int(m.group(2))


class Archive:
    def __init__(self, dir: str | os.PathLike, tz: str = "America/New_York"):
        self.dir = Path(dir)
        self.tz = ZoneInfo(tz)

    def _path(self, date: str) -> Path:
        return self.dir / f"{date}.jsonl"

    def _count_lines(self, path: Path) -> int:
        if not path.exists():
            return 0
        with open(path, "rb") as f:
            return sum(1 for _ in f)

    def append(self, kind: str, payload: dict) -> str:
        now = datetime.now(self.tz)
        date = now.strftime("%Y-%m-%d")
        self.dir.mkdir(parents=True, exist_ok=True)
        path = self._path(date)
        n = self._count_lines(path) + 1
        ref = f"archive:{date}#{n}"
        record = {"ts": now.isoformat(), "kind": kind, "ref": ref, "payload": payload}
        line = json.dumps(record, ensure_ascii=False) + "\n"  # raises TypeError on bad payload
        fd = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o644)
        try:
            os.write(fd, line.encode("utf-8"))
        finally:
            os.close(fd)
        return ref

    def read_day(self, date: str) -> list[dict]:
        path = self._path(date)
        if not path.exists():
            return []
        with open(path, "r", encoding="utf-8") as f:
            return [json.loads(ln) for ln in f if ln.strip()]

    def get(self, ref: str) -> dict:
        date, n = _parse_ref(ref)
        day = self.read_day(date)
        if n > len(day):
            raise KeyError(ref)
        return day[n - 1]

    def any(self, kind: str, payload_kind: str | None = None) -> bool:
        """True if any record of ``kind`` exists (optionally with ``payload["kind"] == payload_kind``), any day."""
        for path in sorted(self.dir.glob("????-??-??.jsonl"), reverse=True):
            with open(path, "r", encoding="utf-8") as f:
                for ln in f:
                    if not ln.strip():
                        continue
                    try:
                        rec = json.loads(ln)
                    except json.JSONDecodeError:
                        continue
                    if rec.get("kind") != kind:
                        continue
                    if payload_kind is None or (rec.get("payload") or {}).get("kind") == payload_kind:
                        return True
        return False

    # Records that quote large slices of other records; matching them returns the whole day, not a memory.
    NOISY_KINDS = ("session_start", "session_result", "assistant", "redaction", "tool")

    def search(self, query: str, limit: int = 20, max_chars: int = 2000) -> list[dict]:
        """Case-insensitive substring match over serialized lines, newest first.

        Prompt/transcript records (session_start, assistant text, tool echoes) are skipped: they
        contain the day's other records verbatim, so every query would match them first. Each hit's
        payload is cut to ``max_chars`` in the *result only* (the file is untouched), so a recall stays a memory.
        """
        q = query.lower()
        hits: list[dict] = []
        for path in sorted(self.dir.glob("????-??-??.jsonl"), reverse=True):
            with open(path, "r", encoding="utf-8") as f:
                lines = [ln for ln in f if ln.strip()]
            for ln in reversed(lines):
                if q in ln.lower():
                    rec = json.loads(ln)
                    if rec.get("kind") in self.NOISY_KINDS:
                        continue
                    if max_chars:
                        raw = json.dumps(rec.get("payload", ""), ensure_ascii=False)
                        if len(raw) > max_chars:
                            rec["payload"] = raw[:max_chars] + f"… [{len(raw) - max_chars} more chars; use the ref to read it whole]"
                    hits.append(rec)
                    if len(hits) >= limit:
                        return hits
        return hits
