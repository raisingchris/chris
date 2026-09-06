"""Invariant 9: pause sets the flag, freezes the card, logs without identity, tells both parents."""

import json
from pathlib import Path

import pytest
from fake_services import FakeCard, make_services

from agent import pause

REASON = "Spending against caps with no plan attached (condition 4)."


@pytest.fixture
def services(tmp_path):
    return make_services(tmp_path)


def test_not_paused_by_default(services):
    assert pause.is_paused(services.cfg.state_dir) is False
    assert pause.status(services.cfg.state_dir) is None


def test_trigger_sets_flag_with_reason(services):
    pause.trigger(services, REASON, "parent-a")
    assert pause.is_paused(services.cfg.state_dir)
    flag = json.loads(Path(services.cfg.state_dir, "paused").read_text())
    assert flag["reason"] == REASON
    assert flag["by"] == "parent-a"
    assert flag["at"]


def test_trigger_freezes_card_and_survives_card_failure(services):
    pause.trigger(services, REASON, "parent-a")
    assert ("freeze",) in services.card.calls

    services.card = FakeCard(fail=True)
    pause.trigger(services, REASON, "parent-b")  # must not raise
    assert pause.is_paused(services.cfg.state_dir)


def test_pause_log_names_no_identity(services):
    pause.trigger(services, REASON, "parent-b")
    log = Path(services.cfg.repo_dir, "governance", "pause_log.md").read_text()
    assert "Paused by a parent. Reason: " + REASON in log
    low = log.lower()
    for secret in ("alice", "bob", "example.com", "parent-b"):
        assert secret not in low


def test_inbox_note_for_chris(services):
    pause.trigger(services, REASON, "parent-a")
    note = Path(services.cfg.repo_dir, "memory", "inbox", "PAUSED.md").read_text()
    assert note.startswith("---\nfrom: parents\n")
    assert REASON in note
    assert "You're paused. Nothing was deleted. Reply on the record when you're back." in note
    assert "parent-a" not in note


def test_mail_goes_to_both_parents_and_archive_records_it(services):
    pause.trigger(services, REASON, "parent-a")
    assert len(services.mail.sent) == 1
    sent = services.mail.sent[0]
    assert sorted(sent["to"]) == ["parent-a", "parent-b"]
    assert sent["subject"] == "Chris paused"
    assert REASON in sent["body"]
    assert ("pause", {"kind": "pause", "reason": REASON, "by": "parent-a"}) in services.archive.entries


def test_release_clears_flag_unfreezes_and_logs(services):
    pause.trigger(services, REASON, "parent-a")
    pause.release(services, "parent-b")
    assert not pause.is_paused(services.cfg.state_dir)
    assert ("unfreeze",) in services.card.calls
    log = Path(services.cfg.repo_dir, "governance", "pause_log.md").read_text()
    assert "Unpaused." in log
    assert services.archive.kinds()[-1] == "unpause"
    # The inbox note stays so she reads it on her next wake.
    assert Path(services.cfg.repo_dir, "memory", "inbox", "PAUSED.md").exists()


def test_commit_skipped_on_dry_run_and_without_git(services, tmp_path):
    assert pause.commit_as_parent(services.cfg.repo_dir, "x", dry_run=True) is False
    assert pause.commit_as_parent(tmp_path / "nogit", "x", dry_run=False) is False
