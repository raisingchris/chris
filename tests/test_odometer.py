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

    records = {f"archive:2026-09-09#{i}": {
        "ref": f"archive:2026-09-09#{i}", "ts": "2026-09-09T12:00:00+00:00",
        "kind": "tool", "payload": {}} for i in range(1, 7)}
    o = Odometer(repo, state, archive_append,
                 lambda: datetime(2026, 9, 10, 12, tzinfo=timezone.utc), records.__getitem__)
    o._records = records
    o._archived = archived
    return o


def test_loop_types_are_prd_6_1_plus_changed_by_reply():
    # Eight from PRD §6.1, plus the ninth Chris proposed and a parent approved (ticket 20260911T0708).
    assert [t.value for t in LoopType] == [
        "promise_kept", "shipped_used", "mistake_written_up", "conflict_resolved",
        "prediction_scored", "relationship_30d", "dollar_earned", "disagreement_defended",
        "changed_by_reply"]
    assert LOOP_TYPES is LoopType


def changed_evidence(odo):
    refs = ["archive:2026-09-01#1", "archive:2026-09-02#1", "archive:2026-09-09#10"]
    for ref, stamp, kind, payload in zip(refs,
            ["2026-09-01T12:00:00+00:00", "2026-09-02T12:00:00+00:00", "2026-09-09T12:00:00+00:00"],
            ["mail_in", "tool", "tool"],
            [{"data": {"from": "cairn@example.test"}}, {"citation": refs[0]}, {"checked": "commitments.md", "change": refs[1]}]):
        odo._records[ref] = {"ref": ref, "ts": stamp, "kind": kind, "payload": payload}
    return refs


def test_changed_by_reply_is_claimable(odo):
    out = odo.claim("changed_by_reply", changed_evidence(odo), "commitments.md still read seven days on")
    assert out["loop"] == "changed_by_reply" and out["n"] == 1


@pytest.mark.parametrize("bad_ref", ["archive:2026-09-09#999", "archive:2026-02-30#1", "archive:2026-09-09#0"])
def test_nonexistent_evidence_rejected(odo, bad_ref):
    with pytest.raises(ValueError):
        odo.claim("promise_kept", [bad_ref], "done")
    assert odo.count() == 0 and not odo._archived


def test_future_evidence_rejected(odo):
    odo._records["archive:2026-09-09#1"]["ts"] = "2026-09-11T00:00:00+00:00"
    with pytest.raises(ValueError, match="future"):
        odo.claim("promise_kept", ["archive:2026-09-09#1"], "done")
    assert odo.count() == 0


@pytest.mark.parametrize("loop_type", ["promise_kept", "shipped_used"])
def test_reused_evidence_rejected_even_with_extra_refs(odo, loop_type):
    odo.claim("promise_kept", ["archive:2026-09-09#1"], "done")
    with pytest.raises(ValueError, match="already"):
        odo.claim(loop_type, ["archive:2026-09-09#2", "archive:2026-09-09#1"], "reworded")
    assert odo.count() == 1


@pytest.mark.parametrize("fault", ["too_soon", "parent", "council", "no_citation", "missing_ref", "reordered", "unlinked_followup"])
def test_changed_by_reply_guards(odo, fault):
    refs = changed_evidence(odo)
    if fault == "too_soon":
        odo._records[refs[2]]["ts"] = "2026-09-09T11:59:59+00:00"
    elif fault == "parent":
        odo._records[refs[0]]["payload"]["data"]["from"] = "parent-a"
    elif fault == "council":
        odo._records[refs[0]]["kind"] = "council"
    elif fault == "no_citation":
        odo._records[refs[1]]["payload"] = {}
    elif fault == "unlinked_followup":
        odo._records[refs[2]]["payload"] = {}
    elif fault == "missing_ref":
        refs.pop()
    else:
        refs[1], refs[2] = refs[2], refs[1]
    with pytest.raises(ValueError):
        odo.claim("changed_by_reply", refs, "commitments.md still read")
    assert odo.count() == 0 and not odo._archived


@pytest.mark.parametrize("refs,note", [(["archive:2026-09-09#1"] * 2, "done"),
    (["archive:2026-09-09#1", "bad"], "done"), (["archive:2026-09-09#1"], " ")])
def test_invalid_claim_rejected_without_side_effects(odo, refs, note):
    with pytest.raises(ValueError):
        odo.claim("promise_kept", refs, note)
    assert odo.count() == 0 and not odo._archived


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


def test_concurrent_duplicate_claim_counts_once(odo):
    from concurrent.futures import ThreadPoolExecutor
    def attempt(_):
        try:
            odo.claim("promise_kept", ["archive:2026-09-09#1"], "done")
            return True
        except ValueError:
            return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sum(pool.map(attempt, range(2))) == 1
    assert odo.count() == 1
