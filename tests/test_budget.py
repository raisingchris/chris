import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from agent.budget import Meter

NY = ZoneInfo("America/New_York")


def at(s):
    return datetime.fromisoformat(s).replace(tzinfo=NY)


class Clock:
    def __init__(self, s):
        self.t = at(s)

    def __call__(self, tz=None):
        return self.t


def test_add_spent_remaining_exceeded(tmp_path):
    clock = Clock("2026-09-06 10:00")
    m = Meter("inference", "day", tmp_path, "America/New_York", now=clock)
    assert m.spent() == 0
    m.add_usd(3.0, "sitting")
    m.add_usd(1.5)
    assert m.spent() == pytest.approx(4.5)
    assert m.remaining(10) == pytest.approx(5.5)
    assert not m.exceeded(10)
    assert m.exceeded(4.5)
    assert m.remaining(2) == 0
    assert m.exceeded(2)


def test_persists_and_shares_file(tmp_path):
    clock = Clock("2026-09-06 10:00")
    Meter("inference", "day", tmp_path, "America/New_York", now=clock).add_usd(2, "x")
    Meter("council", "week", tmp_path, "America/New_York", now=clock).add_usd(5)
    data = json.loads((tmp_path / "budget.json").read_text())
    assert set(data) == {"inference", "council"}
    assert data["inference"]["entries"][0]["note"] == "x"
    m = Meter("inference", "day", tmp_path, "America/New_York", now=clock)
    assert m.spent() == 2
    assert Meter("council", "week", tmp_path, "America/New_York", now=clock).spent() == 5


def test_day_period_key_uses_tz(tmp_path):
    # 23:30 NY on Sep 6 is Sep 7 in UTC; key must be NY date
    now = lambda tz=None: datetime(2026, 9, 7, 3, 30, tzinfo=ZoneInfo("UTC"))
    m = Meter("inference", "day", tmp_path, "America/New_York", now=now)
    assert m.period_key() == "2026-09-06"


def test_week_period_key_monday_start(tmp_path):
    clock = Clock("2026-09-06 10:00")  # Sunday
    m = Meter("council", "week", tmp_path, "America/New_York", now=clock)
    assert m.period_key() == "2026-W36"
    clock.t = at("2026-09-07 00:01")  # Monday
    assert m.period_key() == "2026-W37"
    clock.t = at("2026-09-13 23:59")  # Sunday
    assert m.period_key() == "2026-W37"


def test_day_rollover_resets(tmp_path):
    clock = Clock("2026-09-06 10:00")
    m = Meter("inference", "day", tmp_path, "America/New_York", now=clock)
    m.add_usd(20)
    assert m.exceeded(15)
    clock.t = at("2026-09-07 00:00")
    assert m.spent() == 0
    assert not m.exceeded(15)
    m.add_usd(1)
    assert m.spent() == 1
    # reopened meter sees the new period only
    assert Meter("inference", "day", tmp_path, "America/New_York", now=clock).spent() == 1


def test_week_rollover_resets(tmp_path):
    clock = Clock("2026-09-06 10:00")  # Sunday
    m = Meter("council", "week", tmp_path, "America/New_York", now=clock)
    m.add_usd(9)
    clock.t = at("2026-09-06 23:59")
    assert m.spent() == 9
    clock.t = at("2026-09-07 00:00")  # Monday
    assert m.spent() == 0


def test_state_dir_created(tmp_path):
    d = tmp_path / "nested" / "state"
    Meter("inference", "day", d, "America/New_York", now=Clock("2026-09-06 10:00")).add_usd(1)
    assert (d / "budget.json").exists()


def test_bad_window(tmp_path):
    with pytest.raises(ValueError):
        Meter("x", "month", tmp_path, "America/New_York")
