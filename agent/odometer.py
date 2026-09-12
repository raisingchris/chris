"""The self-time clock: counts loops closed with the real world (PRD §6.1).

Only the nine list-matched loop types count (eight from PRD §6.1, plus
`changed_by_reply`, approved in ticket 20260911T0708); each claim needs at least one
`archive:YYYY-MM-DD#N` evidence ref. Private log at <state_dir>/odometer.jsonl,
public table at governance/odometer.md, one-line summary in memory/wiki/self/odometer.md.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Callable

import yaml

REF_RE = re.compile(r"^archive:\d{4}-\d{2}-\d{2}#\d+$")
DEFAULT_LOOPS = 40


class LoopType(str, Enum):
    promise_kept = "promise_kept"                  # promise made and kept, or broken and repaired
    shipped_used = "shipped_used"                  # something shipped and used by a stranger
    mistake_written_up = "mistake_written_up"      # con or mistake suffered and written up as a lesson
    conflict_resolved = "conflict_resolved"        # conflict had and resolved
    prediction_scored = "prediction_scored"        # prediction made and scored
    relationship_30d = "relationship_30d"          # relationship maintained for 30 days
    dollar_earned = "dollar_earned"                # a dollar earned honestly
    disagreement_defended = "disagreement_defended"  # public disagreement defended or conceded
    changed_by_reply = "changed_by_reply"          # an outside reply changed my code or a belief; still standing 7 days on (ticket 20260911T0708)


LOOP_TYPES = LoopType

PUBLIC_HEADER = "# Odometer\n\nLoops closed with the real world. One row per loop; evidence is an archive ref.\n\n| date | loop | note | evidence |\n|---|---|---|---|\n"


class Odometer:
    def __init__(self, repo_dir: str | Path, state_dir: str | Path,
                 archive_append: Callable[[str, dict], str], now: Callable[[], datetime]):
        self.repo = Path(repo_dir)
        self.log = Path(state_dir) / "odometer.jsonl"
        self.public = self.repo / "governance" / "odometer.md"
        self._archive = archive_append
        self._now = now

    def _entries(self) -> list[dict]:
        if not self.log.exists():
            return []
        return [json.loads(l) for l in self.log.read_text().splitlines() if l.strip()]

    def claim(self, loop_type: str, evidence_refs: list[str], note: str) -> dict:
        try:
            lt = LoopType(loop_type)
        except ValueError:
            raise ValueError(f"unknown loop type {loop_type!r}; allowed: {[t.value for t in LoopType]}")
        refs = [r for r in (evidence_refs or []) if isinstance(r, str) and REF_RE.match(r)]
        if not refs:
            raise ValueError("a loop claim needs at least one evidence ref like archive:YYYY-MM-DD#N")
        today = self._now().date().isoformat()
        entry = {"date": today, "loop": lt.value, "note": note, "evidence": refs,
                 "n": self.count() + 1}
        entry["ref"] = self._archive("odometer_claim", entry)
        self.log.parent.mkdir(parents=True, exist_ok=True)
        with self.log.open("a") as f:
            f.write(json.dumps(entry) + "\n")
        self.public.parent.mkdir(parents=True, exist_ok=True)
        if not self.public.exists() or "| date |" not in self.public.read_text():
            self.public.write_text(PUBLIC_HEADER)
        cell = lambda s: str(s).replace("|", "\\|").replace("\n", " ")
        with self.public.open("a") as f:
            f.write(f"| {today} | {lt.value} | {cell(note)} | {', '.join(refs)} |\n")
        return entry

    def count(self) -> int:
        return len(self._entries())

    def world_days(self, birthday: date) -> int:
        return (self._now().date() - birthday).days

    def to_next(self, graduations_yaml_path: str | Path) -> tuple[str, int]:
        """(phase name, loops remaining) for the first phase whose loop threshold is unmet."""
        n = self.count()
        p = Path(graduations_yaml_path)
        phases = []
        if p.exists():
            phases = sorted((yaml.safe_load(p.read_text()) or {}).get("phases", []),
                            key=lambda ph: ph.get("n", 0))
        if not phases:
            return ("next graduation", max(DEFAULT_LOOPS - n, 0))
        for ph in phases:
            if n < int(ph.get("loops", DEFAULT_LOOPS)):
                return (str(ph["name"]), int(ph["loops"]) - n)
        return (str(phases[-1]["name"]), 0)

    def render_line(self, birthday: date) -> str:
        phase, remaining = self.to_next(self.repo / "governance" / "graduations.yaml")
        line = f"{self.world_days(birthday)} in world-days, {self.count()} loops closed, {remaining} loops to {phase}."
        out = self.repo / "memory" / "wiki" / "self" / "odometer.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(f"# Odometer\n\n{line} (Maintained by the odometer; see `governance/odometer.md`.)\n")
        return line
