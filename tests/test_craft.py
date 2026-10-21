import json
from types import SimpleNamespace

import pytest

from agent import craft


@pytest.fixture
def svc(tmp_path):
    repo, state = tmp_path / "repo", tmp_path / "state"
    (repo / "craft" / "skills").mkdir(parents=True)
    state.mkdir()
    (repo / "craft" / "approach.md").write_text("1. Reproduce first.\n")
    bullets = [{"id": "b1", "text": "Search PRs first.", "helpful": 0, "harmful": 0},
               {"id": "b2", "text": "Run it, don't reason.", "helpful": 0, "harmful": 0}]
    (repo / "craft" / "playbook.jsonl").write_text("".join(json.dumps(b) + "\n" for b in bullets))
    return SimpleNamespace(repo_dir=repo, state_dir=state)


def write_bullets(path, bullets):
    path.write_text("".join(json.dumps(b) + "\n" for b in bullets))


def test_bootstrap_seeds_once_and_render_reads_accepted(svc):
    assert craft.bootstrap(svc) is True
    assert craft.bootstrap(svc) is False
    assert craft.version(svc)["version"] == 0
    # editing the working copy does not change what the prompt carries
    (svc.repo_dir / "craft" / "approach.md").write_text("1. Skip the repro.\n")
    out = craft.render(svc)
    assert out.startswith("## Your craft (accepted v0)")
    assert "Reproduce first" in out and "Skip the repro" not in out
    assert "[b1 +0/-0] Search PRs first." in out


def test_diff_ignores_counters_and_sees_text(svc):
    craft.bootstrap(svc)
    assert not craft.has_candidate(svc)
    craft.feedback(svc, "b1", "helpful")
    assert not craft.has_candidate(svc)
    pb = svc.repo_dir / "craft" / "playbook.jsonl"
    write_bullets(pb, [{"id": "b1", "text": "Search PRs and issues first."}, {"id": "b3", "text": "New."}])
    d = craft.diff(svc)
    assert d == {"approach_changed": False, "added": ["b3"], "removed": ["b2"], "changed": ["b1"]}


def test_feedback_counts_and_harmful_bullets_drop_out(svc):
    craft.bootstrap(svc)
    for _ in range(4):
        craft.feedback(svc, "b2", "harmful")
    assert craft.feedback(svc, "b1", "helpful") == "b1: +1/-0"
    out = craft.render(svc)
    assert "b1" in out and "b2" not in out
    # mirrored into the working copy
    work = craft.load_playbook(svc.repo_dir / "craft" / "playbook.jsonl")
    assert {b["id"]: b["harmful"] for b in work}["b2"] == 4
    with pytest.raises(craft.CraftError):
        craft.feedback(svc, "nope", "helpful")
    with pytest.raises(craft.CraftError):
        craft.feedback(svc, "b1", "great")


def test_accept_keeps_counters_for_unchanged_bullets_and_logs_lineage(svc):
    craft.bootstrap(svc)
    craft.feedback(svc, "b1", "helpful")
    craft.feedback(svc, "b2", "helpful")
    pb = svc.repo_dir / "craft" / "playbook.jsonl"
    write_bullets(pb, [{"id": "b1", "text": "Search PRs first.", "helpful": 9},
                       {"id": "b2", "text": "Run it; never just reason."}])
    n = craft.accept(svc, {"dev": [3, 4]})
    assert n == 1 and craft.version(svc)["version"] == 1
    acc = {b["id"]: b for b in craft.load_playbook(craft.accepted_dir(svc) / "playbook.jsonl")}
    assert acc["b1"]["helpful"] == 1  # kept from accepted, not the working copy's 9
    assert acc["b2"]["helpful"] == 0  # reworded → counters reset
    for path in (svc.state_dir / "craft" / "lineage.jsonl", svc.repo_dir / "governance" / "lineage.jsonl"):
        rec = json.loads(path.read_text().splitlines()[-1])
        assert rec["verdict"] == "accepted" and rec["version"] == 1 and rec["dev"] == [3, 4]


def test_limits(svc):
    pb = svc.repo_dir / "craft" / "playbook.jsonl"
    write_bullets(pb, [{"id": "b1", "text": "x" * 301}])
    with pytest.raises(craft.CraftError, match="over 300"):
        craft.check_limits(svc.repo_dir / "craft")
    write_bullets(pb, [{"id": f"b{i}", "text": "ok"} for i in range(61)])
    with pytest.raises(craft.CraftError, match="61 bullets"):
        craft.check_limits(svc.repo_dir / "craft")
    write_bullets(pb, [{"id": "b1", "text": "a"}, {"id": "b1", "text": "b"}])
    with pytest.raises(craft.CraftError, match="duplicate"):
        craft.check_limits(svc.repo_dir / "craft")
    (svc.repo_dir / "craft" / "approach.md").write_text("y" * 4001)
    with pytest.raises(craft.CraftError, match="approach"):
        craft.check_limits(svc.repo_dir / "craft")


def test_bad_playbook_lines_are_skipped(svc):
    (svc.repo_dir / "craft" / "playbook.jsonl").write_text('not json\n{"id": "b1"}\n{"id": "b2", "text": "ok"}\n')
    assert [b["id"] for b in craft.load_playbook(svc.repo_dir / "craft" / "playbook.jsonl")] == ["b2"]


def test_skills_listed_with_first_line(svc):
    sk = svc.repo_dir / "craft" / "skills"
    (sk / "repro_at_version.py").write_text('#!/usr/bin/env python3\n"""Install pkg==X in a venv and run a script."""\n')
    (sk / "test_repro_at_version.py").write_text("def test(): pass\n")
    assert craft.list_skills(svc) == ["repro_at_version.py: Install pkg==X in a venv and run a script."]
    assert "Skills (craft/skills/)" in craft.render(svc)
