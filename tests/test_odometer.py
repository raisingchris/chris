import json
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from agent.odometer import LOOP_TYPES, LoopType, Odometer

GRADS = """phases:
  - {n: 1, name: Explore,       loops: 3}
  - {n: 2, name: Build skills,  loops: 5}
"""


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "governance").mkdir()
    (tmp_path / "governance" / "graduations.yaml").write_text(GRADS)
    (tmp_path / "memory" / "wiki" / "self").mkdir(parents=True)
    return tmp_path


@pytest.fixture
def odo(repo, tmp_path):
    state = tmp_path / "state"
    state.mkdir()
    archived = []

    def archive_append(kind, payload):
        archived.append((kind, payload))
        return f"archive:2026-09-10#{len(archived)}"

    o = Odometer(repo, state, archive_append, lambda: datetime(2026, 9, 10, 12, tzinfo=timezone.utc))
    o._archived = archived
    return o


def test_loop_types_are_exactly_prd_6_1():
    assert [t.value for t in LoopType] == [
        "promise_kept", "shipped_used", "mistake_written_up", "conflict_resolved",
        "prediction_scored", "relationship_30d", "dollar_earned", "disagreement_defended"]
    assert LOOP_TYPES is LoopType


def test_unknown_type_rejected(odo):
    with pytest.raises(ValueError):
        odo.claim("thought_hard", ["archive:2026-09-09#3"], "no")
    assert odo.count() == 0


def test_missing_or_bad_ref_rejected(odo):
    with pytest.raises(ValueError):
        odo.claim("promise_kept", [], "kept it")
    with pytest.raises(ValueError):
        odo.claim("promise_kept", ["diary:2026-09-09"], "kept it")
    with pytest.raises(ValueError):
        odo.claim("promise_kept", ["archive:2026-9-9#3"], "kept it")
    assert odo.count() == 0


def test_claim_writes_jsonl_and_public_table(odo, repo, tmp_path):
    out = odo.claim("promise_kept", ["archive:2026-09-09#3"], "replied to X on time")
    assert out["loop"] == "promise_kept" and out["n"] == 1
    lines = (tmp_path / "state" / "odometer.jsonl").read_text().splitlines()
    assert json.loads(lines[0])["evidence"] == ["archive:2026-09-09#3"]
    md = (repo / "governance" / "odometer.md").read_text()
    assert "| 2026-09-10 | promise_kept | replied to X on time | archive:2026-09-09#3 |" in md
    assert odo._archived[-1][0] == "odometer_claim"
    assert odo.count() == 1


def test_count_and_to_next(odo, repo):
    for i in range(4):
        odo.claim("dollar_earned", [f"archive:2026-09-09#{i+1}"], f"d{i}")
    assert odo.count() == 4
    assert odo.to_next(repo / "governance" / "graduations.yaml") == ("Build skills", 1)


def test_to_next_at_zero_and_past_all(odo, repo, tmp_path):
    assert odo.to_next(repo / "governance" / "graduations.yaml") == ("Explore", 3)
    for i in range(6):
        odo.claim("dollar_earned", [f"archive:2026-09-09#{i+1}"], "d")
    assert odo.to_next(repo / "governance" / "graduations.yaml") == ("Build skills", 0)
    # missing yaml -> default 40 to "next graduation"
    assert odo.to_next(tmp_path / "nope.yaml") == ("next graduation", 34)


def test_world_days_and_render_line(odo, repo):
    assert odo.world_days(date(2026, 9, 1)) == 9
    odo.claim("shipped_used", ["archive:2026-09-09#1"], "someone used it")
    line = odo.render_line(date(2026, 9, 1))
    assert line == "9 in world-days, 1 loops closed, 2 loops to Explore."
    assert line in (repo / "memory" / "wiki" / "self" / "odometer.md").read_text()
