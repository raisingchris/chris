"""gitops: minimal env, hook-free flags, and the pre-push gate (canaries, vows) with a fake git."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from agent import gitops


class ScriptedGit:
    """Records every call; answers `diff` / `push` from the scripted values."""

    def __init__(self, diff_text="", changed_invariants="", push_rc=0, diff_rc=0):
        self.calls = []
        self.diff_text = diff_text
        self.changed_invariants = changed_invariants
        self.push_rc = push_rc
        self.diff_rc = diff_rc

    def __call__(self, repo_dir, *args, check=True, **kw):
        self.calls.append(args)
        if args[:2] == ("diff", "--name-only"):
            return SimpleNamespace(stdout=self.changed_invariants, stderr="", returncode=0)
        if args[:1] == ("diff",):
            return SimpleNamespace(stdout=self.diff_text, stderr="", returncode=self.diff_rc)
        if args[:1] == ("push",):
            return SimpleNamespace(stdout="", stderr="remote said no" if self.push_rc else "", returncode=self.push_rc)
        if args[:1] == ("status",):
            return SimpleNamespace(stdout=" M x\n", stderr="", returncode=0)
        if args[:1] == ("rev-parse",):
            return SimpleNamespace(stdout="abc123\n", stderr="", returncode=0)
        return SimpleNamespace(stdout="", stderr="", returncode=0)


@pytest.fixture
def gate(tmp_path):
    entries = []
    g = gitops.PushGate(canaries=["Alice Realname", "Example Holdings"],
                        archive_append=lambda k, p: entries.append((k, p)) or "archive:2026-09-06#1",
                        state_dir=tmp_path / "state")
    g.entries = entries
    return g


# --- environment --------------------------------------------------------------------


def test_git_env_is_built_from_scratch(monkeypatch):
    monkeypatch.setenv("HOME", "/home/someone")
    monkeypatch.setenv("GIT_HOME", "/home/brain")
    monkeypatch.setenv("GIT_SSH_COMMAND", "ssh -i /home/brain/.ssh/id_ed25519")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-secret")
    monkeypatch.setenv("GIT_DIR", "/evil")
    env = gitops.git_env()
    assert env["HOME"] == "/home/brain" and env["TZ"] == "UTC"
    assert env["GIT_CONFIG_NOSYSTEM"] == "1"
    assert env["GIT_SSH_COMMAND"].startswith("ssh -i")
    assert env["GIT_AUTHOR_NAME"] == "Chris" and env["GIT_COMMITTER_EMAIL"] == "chris@raisingchris.com"
    assert "ANTHROPIC_API_KEY" not in env and "GIT_DIR" not in env
    assert set(env) <= {"PATH", "HOME", "TZ", "GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME",
                        "GIT_COMMITTER_EMAIL", "GIT_CONFIG_NOSYSTEM", "GIT_TERMINAL_PROMPT", "GIT_SSH_COMMAND"}


def test_git_env_home_falls_back_and_ssh_optional(monkeypatch):
    monkeypatch.delenv("GIT_HOME", raising=False)
    monkeypatch.delenv("GIT_SSH_COMMAND", raising=False)
    monkeypatch.setenv("HOME", "/home/x")
    env = gitops.git_env(gitops.PARENT)
    assert env["HOME"] == "/home/x" and "GIT_SSH_COMMAND" not in env
    assert env["GIT_AUTHOR_NAME"] == "Parent" and env["GIT_AUTHOR_EMAIL"] == "parent@raisingchris.com"


def test_git_passes_hookless_flags_and_minimal_env(monkeypatch, tmp_path):
    seen = {}

    def fake_run(argv, cwd, env, capture_output, text, check):
        seen.update(argv=argv, cwd=cwd, env=env)
        return SimpleNamespace(stdout="", stderr="", returncode=0)

    monkeypatch.setattr(gitops.subprocess, "run", fake_run)
    monkeypatch.setenv("SECRET_THING", "x")
    gitops.git(tmp_path, "status", "--porcelain")
    assert seen["argv"][:5] == ["git", "-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false"]
    assert seen["argv"][5:] == ["status", "--porcelain"]
    assert "SECRET_THING" not in seen["env"] and seen["env"]["TZ"] == "UTC"
    gitops.git_as_parent(tmp_path, "commit", "-m", "x")
    assert seen["env"]["GIT_AUTHOR_NAME"] == "Parent"


def test_source_never_spreads_os_environ():
    src = Path(gitops.__file__).read_text()
    assert "**os.environ" not in src


# --- push gate ------------------------------------------------------------------------


def test_clean_diff_is_pushed(gate):
    git = ScriptedGit(diff_text="+Met a stranger at the market.\n")
    ok, err = gitops.push_repo("/repo", git, gate)
    assert ok and err == ""
    assert ("push",) in git.calls
    assert gate.entries == []
    assert gitops.push_blocked_reason(gate.state_dir) == ""


def test_canary_in_outgoing_diff_blocks_push(gate):
    git = ScriptedGit(diff_text="+Talked to alice realname today\n+about Example Holdings\n")
    ok, err = gitops.push_repo("/repo", git, gate)
    assert not ok and err == "push blocked: identity hit"
    assert ("push",) not in git.calls
    kinds = [k for k, _ in gate.entries]
    assert kinds == ["push_blocked_canary"]
    payload = gate.entries[0][1]
    assert payload["report"] == [{"kind": "canary", "count": 2}]
    assert "alice" not in repr(gate.entries).lower()  # counts only, never the text
    assert gitops.push_blocked_reason(gate.state_dir) == "identity hit"

    # a later clean push clears the marker
    ok, _ = gitops.push_repo("/repo", ScriptedGit(), gate)
    assert ok and gitops.push_blocked_reason(gate.state_dir) == ""


def test_foreign_email_or_phone_alone_does_not_block(gate):
    git = ScriptedGit(diff_text="+wrote to someone@else.org, call +1 415 555 0100\n")
    ok, _ = gitops.push_repo("/repo", git, gate)
    assert ok and ("push",) in git.calls


def test_unreadable_diff_fails_closed(gate):
    git = ScriptedGit(diff_rc=128)
    ok, err = gitops.push_repo("/repo", git, gate)
    assert not ok and ("push",) not in git.calls
    assert gate.entries[0][1]["report"] == [{"kind": "diff_unavailable", "count": 1}]


def test_vows_edit_is_reverted_and_archived_before_push(gate):
    git = ScriptedGit(changed_invariants="soul/vows.md\n")
    ok, _ = gitops.push_repo("/repo", git, gate)
    assert ok
    assert ("diff", "--name-only", "origin/main", "HEAD", "--", "soul/vows.md", "soul/constitution.md") in git.calls
    assert ("checkout", "origin/main", "--", "soul/vows.md") in git.calls
    assert ("commit", "-m", "revert: vows are not editable", "--", "soul/vows.md") in git.calls
    assert git.calls.index(("push",)) > git.calls.index(("checkout", "origin/main", "--", "soul/vows.md"))
    assert [k for k, _ in gate.entries] == ["invariant_violation"]
    assert gate.entries[0][1]["files"] == ["soul/vows.md"]


def test_push_failure_reported_without_gate_marker(gate):
    git = ScriptedGit(push_rc=1)
    ok, err = gitops.push_repo("/repo", git, gate)
    assert not ok and err == "remote said no"
    assert gitops.push_blocked_reason(gate.state_dir) == ""


def test_commit_all_routes_push_through_gate(gate):
    git = ScriptedGit(diff_text="+alice realname\n")
    failures = []
    sha = gitops.commit_all("/repo", "m", push=True, run=git, on_push_failed=failures.append, gate=gate)
    assert sha == "abc123" and failures == ["push blocked: identity hit"]
    assert ("push",) not in git.calls


def test_meters_line_shows_push_blocked(services, monkeypatch):
    monkeypatch.setattr(gitops, "unpushed_count", lambda repo_dir, run=None: 1)
    Path(services.cfg.state_dir).mkdir(parents=True, exist_ok=True)
    (Path(services.cfg.state_dir) / gitops.BLOCKED_MARKER).write_text("identity hit")
    assert services.meters_line().endswith("· 1 commits unpushed · push blocked: identity hit")
