"""The self-time clock: counts loops closed with the real world (PRD §6.1).

Only the nine list-matched loop types count (eight from PRD §6.1, plus
`changed_by_reply`, approved in ticket 20260911T0708); each claim needs at least one
`archive:YYYY-MM-DD#N` evidence ref. Private log at <state_dir>/odometer.jsonl,
public table at governance/odometer.md, one-line summary in memory/wiki/self/odometer.md.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Callable
from threading import Lock

from agent.archive import is_valid_ref

import yaml

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
                 archive_append: Callable[[str, dict], str], now: Callable[[], datetime],
                 archive_get: Callable[[str], dict]):
        self.repo = Path(repo_dir)
        self.log = Path(state_dir) / "odometer.jsonl"
        self.public = self.repo / "governance" / "odometer.md"
        self._archive = archive_append
        self._now = now
        self._get = archive_get
        self._claim_lock = Lock()

    def _entries(self) -> list[dict]:
        if not self.log.exists():
            return []
        return [json.loads(l) for l in self.log.read_text().splitlines() if l.strip()]

    def claim(self, loop_type: str, evidence_refs: list[str], note: str) -> dict:
        with self._claim_lock:
            return self._claim(loop_type, evidence_refs, note)

    def _claim(self, loop_type: str, evidence_refs: list[str], note: str) -> dict:
        try:
            lt = LoopType(loop_type)
        except ValueError:
            raise ValueError(f"unknown loop type {loop_type!r}; allowed: {[t.value for t in LoopType]}")
        if not isinstance(evidence_refs, list) or not evidence_refs or not all(is_valid_ref(r) for r in evidence_refs):
            raise ValueError("every evidence ref must be an archive:YYYY-MM-DD#N reference")
        refs = list(evidence_refs)
        if len(set(refs)) != len(refs):
            raise ValueError("evidence refs must be distinct")
        if not isinstance(note, str) or not note.strip():
            raise ValueError("explain the completed loop in a non-empty note")
        records, times = [], []
        for ref in refs:
            try:
                record = self._get(ref)
                stamp = datetime.fromisoformat(record["ts"])
                if record.get("ref") != ref or stamp.tzinfo is None:
                    raise ValueError("invalid record")
            except (KeyError, ValueError, TypeError):
                raise ValueError(f"evidence is missing or invalid: {ref}") from None
            if stamp > self._now():
                raise ValueError(f"evidence is in the future: {ref}")
            records.append(record)
            times.append(stamp)
        # Evidence is single-use across types, including old claims without new metadata.
        used = {r for entry in self._entries() for r in entry.get("evidence", [])}
        if used.intersection(refs):
            raise ValueError("evidence already belongs to a claimed loop")
        if lt == LoopType.changed_by_reply:
            if len(refs) != 3:
                raise ValueError("changed_by_reply needs three refs in order: outside message, change, follow-up")
            payload = records[0].get("payload") or {}
            sender = str(payload.get("data", payload).get("from", "")).lower()
            if records[0].get("kind") != "mail_in" or not sender or "parent-" in sender:
                raise ValueError("the first ref must be an incoming message from outside the family")
            if not times[0] <= times[1] <= times[2] or times[2] - times[1] < timedelta(days=7):
                raise ValueError("follow-up evidence must be at least seven days after the change")
            # This establishes a traceable citation, not a semantic judgment of growth.
            if refs[0] not in json.dumps(records[1].get("payload", {}), ensure_ascii=False):
                raise ValueError("the change record must cite the outside message ref")
            if refs[1] not in json.dumps(records[2].get("payload", {}), ensure_ascii=False):
                raise ValueError("the follow-up record must cite the change ref")
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
