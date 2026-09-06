"""Nightly git backup: skip path, first-run clone, copy+commit+push, nothing-changed, failure without the key."""

import json
import os
import stat
import subprocess
from pathlib import Path

import pytest
from fake_services import make_services
from freezegun import freeze_time

from agent import backup
from agent.backup import run_backup

URL = "git@github.com:raisingchris/chris-private.git"
KEY = "-----BEGIN OPENSSH PRIVATE KEY-----\nb3BlbnNzaC1rZXktdjEAAAAAsecretsecretsecret\n-----END OPENSSH PRIVATE KEY-----\n"
SHA = "0123456789abcdef0123456789abcdef01234567"


@pytest.fixture
def env():
    return {"BACKUP_GIT_URL": URL, "BACKUP_DEPLOY_KEY": KEY}


@pytest.fixture
def services(tmp_path, monkeypatch):
    s = make_services(tmp_path)
    Path(s.cfg.archive_dir).mkdir(parents=True, exist_ok=True)
    (Path(s.cfg.archive_dir) / "2026-09-06.jsonl").write_text('{"kind":"x"}\n')
    (Path(s.cfg.state_dir) / "last_runs.json").write_text("{}")
    minutes = Path(s.cfg.state_dir).parent / "council_minutes"
    minutes.mkdir()
    (minutes / "2026-09-01.md").write_text("minutes")
    monkeypatch.setenv("COUNCIL_MINUTES_DIR", str(minutes))
    return s


class FakeGit:
    """Records every git command; plays scripted results. ``clone``/``init`` create the ``.git`` marker."""

    def __init__(self, *, clone_stderr=None, pull_rc=0, dirty=True, fail=None):
        self.calls: list[tuple[str, tuple[str, ...]]] = []
        self.clone_stderr, self.pull_rc, self.dirty, self.fail = clone_stderr, pull_rc, dirty, fail

    def __call__(self, repo_dir, *args, check=True):
        self.calls.append((str(repo_dir), args))
        cmd = args[0]
        rc, out, err = 0, "", ""
        if cmd == "clone":
            if self.clone_stderr is not None:
                rc, err = 128, self.clone_stderr
            else:
                (Path(args[2]) / ".git").mkdir(parents=True)
        elif cmd == "init":
            (Path(repo_dir) / ".git").mkdir(parents=True)
        elif cmd == "pull":
            rc = self.pull_rc
        elif cmd == "status":
            out = " M state/last_runs.json\n" if self.dirty else ""
        elif cmd == "rev-parse":
            out = SHA + "\n"
        if self.fail and cmd == self.fail[0]:
            rc, err = 1, self.fail[1]
        if rc and check:
            raise subprocess.CalledProcessError(rc, ["git", *args], out, err)
        return subprocess.CompletedProcess(["git", *args], rc, out, err)

    def commands(self) -> list[str]:
        return [a[0] for _, a in self.calls]

    def lines(self) -> str:
        return "\n".join(" ".join(a) for _, a in self.calls)


def test_skipped_without_config(services):
    result = run_backup(services, env={})
    assert result["kind"] == "backup_skipped"
    assert result["missing"] == ["BACKUP_GIT_URL", "BACKUP_DEPLOY_KEY"]
    assert services.archive.entries == [("backup", result)]

    services.archive.entries.clear()
    result = run_backup(services, env={"BACKUP_GIT_URL": URL, "BACKUP_DEPLOY_KEY": "  "})
    assert result["kind"] == "backup_skipped" and result["missing"] == ["BACKUP_DEPLOY_KEY"]
    key_path, repo = backup.backup_paths(services.cfg)
    assert not key_path.exists() and not repo.exists()


@freeze_time("2026-09-07 02:45:10")  # 22:45 on 2026-09-06 in America/New_York (EDT)
def test_first_run_clones_copies_commits_pushes(services, env):
    git = FakeGit()
    result = run_backup(services, env=env, run=git)
    key_path, repo = backup.backup_paths(services.cfg)

    assert result == {"kind": "backup_done", "changed": True, "commit": SHA[:7], "files": 3}
    assert services.archive.entries == [("backup", result)]

    # the key landed next to state/, mode 600, and only its *path* is ever handed to git
    assert key_path.read_text() == KEY
    assert stat.S_IMODE(key_path.stat().st_mode) == 0o600
    assert "BEGIN OPENSSH" not in git.lines() and "secretsecret" not in git.lines()
    assert "secretsecret" not in json.dumps(services.archive.entries)

    # the git sequence
    assert git.calls[0] == (str(repo.parent), ("clone", URL, str(repo)))
    assert git.commands() == ["clone", "add", "status", "commit", "rev-parse", "push"]
    assert all(cwd == str(repo) for cwd, _ in git.calls[1:])
    assert git.calls[1][1] == ("add", "-A")
    assert git.calls[3][1] == ("commit", "-m", "backup 2026-09-06T22:45:10-04:00")
    assert git.calls[5][1] == ("push", "-u", "origin", "HEAD")

    # the copy: every private dir under its own top-level name
    assert (repo / "archive" / "2026-09-06.jsonl").read_text() == '{"kind":"x"}\n'
    assert (repo / "state" / "last_runs.json").read_text() == "{}"
    assert (repo / "council_minutes" / "2026-09-01.md").read_text() == "minutes"


def test_default_runner_uses_key_by_path_and_minimal_env(services, monkeypatch):
    key_path, _ = backup.backup_paths(services.cfg)
    seen = {}

    def fake_run(argv, **kw):
        seen.update(argv=argv, **kw)
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(backup.subprocess, "run", fake_run)
    backup.make_runner(key_path)("/somewhere", "status", "--porcelain")
    assert seen["argv"] == ["git", "-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false",
                            "status", "--porcelain"]
    assert seen["cwd"] == "/somewhere" and seen["check"] is True
    env = seen["env"]
    assert env["GIT_SSH_COMMAND"] == (
        f"ssh -i {key_path} -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new")
    assert env["GIT_AUTHOR_NAME"] == "Chris" and env["GIT_COMMITTER_EMAIL"] == "chris@raisingchris.com"
    assert env["GIT_CONFIG_NOSYSTEM"] == "1" and env["GIT_TERMINAL_PROMPT"] == "0"
    assert set(env) <= {"PATH", "HOME", "TZ", "GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME",
                        "GIT_COMMITTER_EMAIL", "GIT_CONFIG_NOSYSTEM", "GIT_TERMINAL_PROMPT", "GIT_SSH_COMMAND"}


def test_empty_remote_is_initialised(services, env):
    git = FakeGit(clone_stderr="warning: You appear to have cloned an empty repository.\nfatal: ...")
    result = run_backup(services, env=env, run=git)
    _, repo = backup.backup_paths(services.cfg)
    assert result["kind"] == "backup_done" and result["changed"] is True
    assert git.commands()[:4] == ["clone", "init", "symbolic-ref", "remote"]
    assert git.calls[2][1] == ("symbolic-ref", "HEAD", "refs/heads/main")
    assert git.calls[3][1] == ("remote", "add", "origin", URL)
    assert git.commands()[-1] == "push" and (repo / ".git").is_dir()


def test_clone_failure_other_than_empty_is_a_failure(services, env):
    git = FakeGit(clone_stderr="fatal: Could not read from remote repository.")
    result = run_backup(services, env=env, run=git)
    assert result["kind"] == "backup_failed" and result["error"] == "CalledProcessError"
    assert "Could not read" in result["stderr"]
    assert git.commands() == ["clone"]


def test_second_run_pulls_and_keeps_existing_key(services, env):
    key_path, repo = backup.backup_paths(services.cfg)
    (repo / ".git").mkdir(parents=True)
    key_path.write_text("already-there\n")
    key_path.chmod(0o600)
    git = FakeGit()
    result = run_backup(services, env=env, run=git)
    assert result["kind"] == "backup_done" and result["changed"] is True
    assert git.commands() == ["pull", "add", "status", "commit", "rev-parse", "push"]
    assert git.calls[0] == (str(repo), ("pull", "--rebase"))
    assert key_path.read_text() == "already-there\n"


def test_pull_failure_reclones_fresh(services, env):
    _, repo = backup.backup_paths(services.cfg)
    (repo / ".git").mkdir(parents=True)
    (repo / "stale.txt").write_text("stale")
    git = FakeGit(pull_rc=1)
    result = run_backup(services, env=env, run=git)
    assert result["kind"] == "backup_done"
    assert git.commands() == ["pull", "clone", "add", "status", "commit", "rev-parse", "push"]
    assert not (repo / "stale.txt").exists() and (repo / "state" / "last_runs.json").exists()


def test_nothing_changed_still_done(services, env):
    _, repo = backup.backup_paths(services.cfg)
    (repo / ".git").mkdir(parents=True)
    git = FakeGit(dirty=False)
    result = run_backup(services, env=env, run=git)
    assert result == {"kind": "backup_done", "changed": False, "commit": None, "files": 3}
    assert git.commands() == ["pull", "add", "status"]

    # a second pass over unchanged sources copies nothing
    git2 = FakeGit(dirty=False)
    assert run_backup(services, env=env, run=git2)["files"] == 0


def test_sync_never_deletes_and_only_copies_changes(tmp_path):
    src, dst = tmp_path / "src", tmp_path / "dst"
    (src / "sub").mkdir(parents=True)
    (src / "a.txt").write_text("a")
    (src / "sub" / "b.txt").write_text("b")
    dst.mkdir()
    (dst / "old.txt").write_text("keep me")
    assert backup.sync_dir(src, dst) == 2
    assert (dst / "old.txt").read_text() == "keep me"
    assert (dst / "sub" / "b.txt").read_text() == "b"
    assert backup.sync_dir(src, dst) == 0
    (src / "a.txt").write_text("changed!")
    assert backup.sync_dir(src, dst) == 1 and (dst / "a.txt").read_text() == "changed!"
    assert backup.sync_dir(tmp_path / "missing", dst) == 0


def test_failure_archived_without_the_key(services, env):
    key_path, _ = backup.backup_paths(services.cfg)
    # a hostile stderr: echoes the key path and the key text back at us
    stderr = f"Permission denied (publickey) using {key_path}\n{KEY}\n" + "x" * 500
    git = FakeGit(fail=("push", stderr))
    result = run_backup(services, env=env, run=git)
    assert result["kind"] == "backup_failed" and result["error"] == "CalledProcessError"
    assert result["stderr"].startswith("Permission denied (publickey) using <key-path>")
    assert len(result["stderr"]) <= 300
    dumped = json.dumps(services.archive.entries)
    assert "PRIVATE KEY" not in dumped and "secretsecret" not in dumped and str(key_path) not in dumped
    assert services.archive.entries == [("backup", result)]


def test_non_git_exception_is_a_failure_not_a_crash(services, env):
    def boom(repo_dir, *args, check=True):
        raise OSError(f"cannot run git with {KEY}")

    result = run_backup(services, env=env, run=boom)
    assert result["kind"] == "backup_failed" and result["error"] == "OSError"
    assert "secretsecret" not in result["stderr"] and "<key>" in result["stderr"]


def test_backup_dirs_env_override(services, monkeypatch, tmp_path):
    monkeypatch.setenv("COUNCIL_MINUTES_DIR", str(tmp_path / "elsewhere"))
    dirs = backup.backup_dirs(services.cfg)
    assert dirs == [Path(services.cfg.archive_dir), Path(services.cfg.state_dir), tmp_path / "elsewhere"]
    monkeypatch.delenv("COUNCIL_MINUTES_DIR")
    assert backup.backup_dirs(services.cfg)[2] == Path(services.cfg.state_dir).parent / "council_minutes"
    key_path, repo = backup.backup_paths(services.cfg)
    assert key_path == Path(services.cfg.state_dir).parent / "backup_key"
    assert repo == Path(services.cfg.state_dir).parent / "backup-repo"
    assert os.path.basename(key_path) == "backup_key"
