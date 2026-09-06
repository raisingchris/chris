"""USD spend meters with daily/weekly rollover, persisted in <state_dir>/budget.json."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Callable
from zoneinfo import ZoneInfo

WINDOWS = ("day", "week")


class Meter:
    def __init__(
        self,
        name: str,
        window: str,
        state_dir: str | os.PathLike,
        tz: str = "America/New_York",
        now: Callable[..., datetime] = datetime.now,
    ):
        if window not in WINDOWS:
            raise ValueError(f"window must be one of {WINDOWS}, got {window!r}")
        self.name = name
        self.window = window
        self.path = Path(state_dir) / "budget.json"
        self.tz = ZoneInfo(tz)
        self._now = now

    # -- period ------------------------------------------------------------
    def period_key(self) -> str:
        t = self._now(self.tz).astimezone(self.tz)
        if self.window == "day":
            return t.strftime("%Y-%m-%d")
        y, w, _ = t.isocalendar()  # ISO weeks start Monday
        return f"{y}-W{w:02d}"

    # -- storage -----------------------------------------------------------
    def _load_all(self) -> dict:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text() or "{}")

    def _current(self, data: dict) -> dict:
        """This meter's record for the current period; a new period starts at zero."""
        rec = data.get(self.name)
        key = self.period_key()
        if not rec or rec.get("period") != key:
            rec = {"window": self.window, "period": key, "spent": 0.0, "entries": []}
        return rec

    def _save(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=1))
        os.replace(tmp, self.path)

    # -- api ---------------------------------------------------------------
    def add_usd(self, amount: float, note: str = "") -> float:
        data = self._load_all()
        rec = self._current(data)
        rec["spent"] = round(rec["spent"] + float(amount), 6)
        rec["entries"].append({"ts": self._now(self.tz).isoformat(), "usd": float(amount), "note": note})
        data[self.name] = rec
        self._save(data)
        return rec["spent"]

    def spent(self) -> float:
        return self._current(self._load_all())["spent"]

    def remaining(self, cap: float) -> float:
        return max(0.0, float(cap) - self.spent())

    def exceeded(self, cap: float) -> bool:
        return self.spent() >= float(cap)
