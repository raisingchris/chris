"""Self-deploy: the protected boundary, the guarded path, the tool, wiring and config.

Nothing here dispatches to GitHub or runs the real suite — git, tests and the
dispatch are all injected.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from agent import config, deploy, pause, sleep, tools, wiring
from agent.config import Config
from conftest import archive_text


def out_text(result: dict) -> str:
    return result["content"][0]["text"]


class FakeGit:
    """A git runner that answers rev-parse (HEAD) and diff --name-only."""

    def __init__(self, head: str = "", diff_names=None):
        self.head = head
        self.diff_names = list(diff_names or [])

    def __call__(self, repo_dir, *args, check=True, **kw):
        if args and args[0] == "rev-parse":
            return SimpleNamespace(returncode=0, stdout=self.head + "\n")
        if args and args[0] == "diff":
            return SimpleNamespace(returncode=0, stdout="\n".join(self.diff_names) + "\n")
        return SimpleNamespace(returncode=0, stdout="")


def _now(y=2026, m=9, d=22):
    return lambda: datetime(y, m, d, 12, 0, tzinfo=ZoneInfo("America/New_York"))


# --- changed_protected -------------------------------------------------------


def test_changed_protected_detects_locks_and_ignores_ordinary_files():
    git = FakeGit(diff_names=[
        "soul/vows.md", ".github/workflows/deploy.yml", "agent/guards.py", "agent/redaction.py",
        "tests/test_invariants.py", "agent/deploy.py",
        "agent/loop.py", "agent/tools.py", "site/index.html",
    ])
    got = deploy.changed_protected("/repo", "base", run=git)
    assert got == ["soul/vows.md", ".github/workflows/deploy.yml", "agent/guards.py",
                   "agent/redaction.py", "tests/test_invariants.py", "agent/deploy.py"]
    assert "agent/loop.py" not in got and "agent/tools.py" not in got and "site/index.html" not in got


def test_is_protected_dir_prefix_and_exact():
    assert deploy.is_protected(".github/workflows/anything.yml")  # dir prefix
    assert deploy.is_protected("soul/constitution.md")  # exact
    assert not deploy.is_protected("soul/vows.md.bak")  # not exact, not a dir entry
    assert not deploy.is_protected("agent/loop.py")


# --- self_deploy refusals ----------------------------------------------------


def test_self_deploy_refuses_when_paused(services, monkeypatch):
    monkeypatch.setenv("GIT_SHA", "old000")
    pause.flag_path(services.cfg.state_dir).parent.mkdir(parents=True, exist_ok=True)
    pause.flag_path(services.cfg.state_dir).write_text("{}")
    r = deploy.self_deploy(services, dispatch=lambda t: None, run_tests_fn=lambda repo: (True, "ok"),
                           git_run=FakeGit(head="new111"), now=_now())
    assert r["ok"] is False and r["reason"] == "paused"


def test_self_deploy_nothing_to_deploy(services, monkeypatch):
    monkeypatch.setenv("GIT_SHA", "abc1234567")
    r = deploy.self_deploy(services, dispatch=lambda t: None, run_tests_fn=lambda repo: (True, "ok"),
                           git_run=FakeGit(head="abc1234567"), now=_now())
    assert r["ok"] is False and r["reason"] == "nothing_to_deploy"


def test_self_deploy_refuses_protected_files(services, monkeypatch):
    monkeypatch.setenv("GIT_SHA", "old000")
    git = FakeGit(head="new111", diff_names=["soul/vows.md", "agent/loop.py"])
    called = []
    r = deploy.self_deploy(services, dispatch=lambda t: called.append(t),
                           run_tests_fn=lambda repo: (True, "ok"), git_run=git, now=_now())
    assert r["ok"] is False and r["reason"] == "protected_files"
    assert "soul/vows.md" in r["detail"] and "need a parent" in r["detail"]
    assert called == []  # never dispatched


def test_self_deploy_refuses_on_failed_tests(services, monkeypatch):
    monkeypatch.setenv("GIT_SHA", "old000")
    git = FakeGit(head="new111", diff_names=["agent/loop.py"])
    called = []
    r = deploy.self_deploy(services, dispatch=lambda t: called.append(t),
                           run_tests_fn=lambda repo: (False, "1 failed, 592 passed"), git_run=git, now=_now())
    assert r["ok"] is False and r["reason"] == "tests_failed" and r["detail"] == "1 failed, 592 passed"
    assert called == []


def test_self_deploy_daily_cap(services, monkeypatch):
    monkeypatch.setenv("GIT_SHA", "old000")
    state = Path(services.cfg.state_dir)
    state.mkdir(parents=True, exist_ok=True)
    (state / "self_deploy.json").write_text(json.dumps({"day": "2026-09-22", "count": 4}))
    r = deploy.self_deploy(services, dispatch=lambda t: None, run_tests_fn=lambda repo: (True, "ok"),
                           git_run=FakeGit(head="new111", diff_names=["agent/loop.py"]), now=_now())
    assert r["ok"] is False and r["reason"] == "daily_cap"


def test_self_deploy_not_configured_without_token(services, monkeypatch):
    monkeypatch.setenv("GIT_SHA", "old000")
    monkeypatch.delenv("GITHUB_DEPLOY_TOKEN", raising=False)
    r = deploy.self_deploy(services, run_tests_fn=lambda repo: (True, "ok"),
                           git_run=FakeGit(head="new111", diff_names=["agent/loop.py"]), now=_now())
    assert r["ok"] is False and r["reason"] == "not_configured"


# --- self_deploy happy path --------------------------------------------------


def test_self_deploy_happy_path(services, monkeypatch):
    monkeypatch.setenv("GIT_SHA", "old0000000")
    git = FakeGit(head="new1111222", diff_names=["agent/loop.py", "site/index.html"])
    called = []
    r = deploy.self_deploy(services, dispatch=lambda t: called.append(t),
                           run_tests_fn=lambda repo: (True, "593 passed, 2 skipped"),
                           git_run=git, now=_now())
    assert r["ok"] is True and r["sha"] == "new1111" and "deploying" in r["note"]
    assert len(called) == 1  # dispatched exactly once

    # changelog line written (an agent/loop.py edit deploys)
    changelog = (Path(services.cfg.repo_dir) / "governance" / "changelog.md").read_text()
    assert "Chris deployed herself: new1111 (2 files: agent/loop.py, site/index.html)" in changelog

    # counter incremented, archived, last_deploy recorded
    rec = json.loads((Path(services.cfg.state_dir) / "self_deploy.json").read_text())
    assert rec == {"day": "2026-09-22", "count": 1}
    assert "self_deploy" in archive_text(services)
    runs = wiring.read_last_runs(services.cfg.state_dir)
    assert "last_deploy" in runs


def test_self_deploy_cap_resets_next_day(services, monkeypatch):
    monkeypatch.setenv("GIT_SHA", "old000")
    state = Path(services.cfg.state_dir)
    state.mkdir(parents=True, exist_ok=True)
    (state / "self_deploy.json").write_text(json.dumps({"day": "2026-09-21", "count": 4}))
    git = FakeGit(head="new111", diff_names=["agent/loop.py"])
    # Yesterday's cap is spent, but today is a fresh day → allowed.
    r = deploy.self_deploy(services, dispatch=lambda t: None, run_tests_fn=lambda repo: (True, "ok"),
                           git_run=git, now=_now(d=22))
    assert r["ok"] is True
    rec = json.loads((state / "self_deploy.json").read_text())
    assert rec == {"day": "2026-09-22", "count": 1}


def test_self_deploys_today_counts_only_today(tmp_path):
    state = tmp_path / "state"
    state.mkdir()
    (state / "self_deploy.json").write_text(json.dumps({"day": "2026-09-22", "count": 3}))
    now = datetime(2026, 9, 22, 8, 0, tzinfo=ZoneInfo("America/New_York"))
    assert deploy.self_deploys_today(state, now) == 3
    later = datetime(2026, 9, 23, 8, 0, tzinfo=ZoneInfo("America/New_York"))
    assert deploy.self_deploys_today(state, later) == 0
    assert deploy.self_deploys_today(tmp_path / "missing", now) == 0


# --- the deploy tool ---------------------------------------------------------


async def test_deploy_tool_returns_success_note(services, monkeypatch):
    monkeypatch.setattr(deploy, "self_deploy",
                        lambda s: {"ok": True, "sha": "abc1234", "note": "deploying; ~2 min."})
    got = out_text(await tools.make_handlers(services)["deploy"]({}))
    assert "deploying" in got
    assert "abc1234" in archive_text(services)


async def test_deploy_tool_returns_protected_refusal(services, monkeypatch):
    monkeypatch.setattr(deploy, "self_deploy", lambda s: {
        "ok": False, "reason": "protected_files",
        "detail": "You changed protected safety files: soul/vows.md. These need a parent."})
    got = out_text(await tools.make_handlers(services)["deploy"]({}))
    assert "soul/vows.md" in got and "need a parent" in got
    assert "protected_files" in archive_text(services)


def test_deploy_is_a_tool_and_excluded_from_sleep():
    assert "deploy" in tools.TOOL_NAMES
    assert "deploy" in tools.SCHEMAS
    assert "mcp__chris__deploy" in tools.mcp_names()
    # She must not deploy during sleep consolidation.
    assert "deploy" in sleep.SLEEP_EXCLUDED
    assert "mcp__chris__deploy" not in tools.mcp_names(exclude=sleep.SLEEP_EXCLUDED)


# --- config ------------------------------------------------------------------


def test_config_self_deploy_per_day(monkeypatch):
    config.reset()
    assert "SELF_DEPLOY_PER_DAY" in config.ENV_KEYS
    monkeypatch.delenv("SELF_DEPLOY_PER_DAY", raising=False)
    assert Config.from_env().self_deploy_per_day == 4
    monkeypatch.setenv("SELF_DEPLOY_PER_DAY", "9")
    assert Config.from_env().self_deploy_per_day == 9
    config.reset()


# --- wiring meters_line ------------------------------------------------------


def test_meters_line_shows_self_deploys_when_any(tmp_path):
    cfg = Config(repo_dir=str(tmp_path / "repo"), archive_dir=str(tmp_path / "archive"),
                 state_dir=str(tmp_path / "state"), tz="Europe/Lisbon", dry_run=True)
    s = wiring.build(cfg, secrets=wiring.Secrets())
    Path(s.cfg.state_dir).mkdir(parents=True, exist_ok=True)
    # No self-deploys today → the segment is absent.
    assert "self-deploys today" not in s.meters_line()
    day = datetime.now(ZoneInfo("Europe/Lisbon")).strftime("%Y-%m-%d")
    (Path(s.cfg.state_dir) / "self_deploy.json").write_text(json.dumps({"day": day, "count": 2}))
    assert "self-deploys today 2/4" in s.meters_line()
