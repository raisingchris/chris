"""Go-live hardening: symlink-safe paths, code/.git protection, visible failures, no overlap, soft push."""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from agent import gitops, guards, loop, scheduler, session, sleep
from agent.config import Config
from agent.council import estimate_cost_usd
from agent.paths import UnsafePath, safe_path
from conftest import archive_text
from fake_services import make_services
from test_council import make_council, T0
from test_loop import FakeGit
from test_session import fake_messages


def denied(out: dict) -> str | None:
    h = out.get("hookSpecificOutput")
    return h["permissionDecisionReason"] if h else None


# --- paths -------------------------------------------------------------------------


def test_safe_path_accepts_plain_and_missing_files(tmp_path):
    (tmp_path / "memory").mkdir()
    assert safe_path(tmp_path, "memory/handoff.md") == tmp_path.resolve() / "memory" / "handoff.md"
    assert safe_path(tmp_path, tmp_path / "memory" / "new.md").name == "new.md"


def test_safe_path_refuses_symlink_file_dir_and_escape(tmp_path):
    repo = tmp_path / "repo"
    (repo / "memory").mkdir(parents=True)
    secret = tmp_path / "secret.txt"
    secret.write_text("key")
    (repo / "memory" / "link.md").symlink_to(secret)
    (repo / "memory" / "dir").symlink_to(tmp_path)
    with pytest.raises(UnsafePath):
        safe_path(repo, "memory/link.md")
    with pytest.raises(UnsafePath):
        safe_path(repo, "memory/dir/anything.md")
    with pytest.raises(UnsafePath):
        safe_path(repo, "../secret.txt")
    with pytest.raises(UnsafePath):
        safe_path(repo, secret)


def test_loop_read_skips_symlink_and_archives(services, repo, tmp_path):
    secret = tmp_path / "secret.txt"
    secret.write_text("sk-live")
    (repo / "memory").mkdir(exist_ok=True)
    (repo / "memory" / "handoff.md").symlink_to(secret)
    assert loop._rread(services, repo / "memory" / "handoff.md") == ""
    loop._note_handoff(repo, "hello", services.archive)
    assert secret.read_text() == "sk-live"
    assert '"kind": "unsafe_path"' in archive_text(services)


def test_mail_list_unread_skips_symlinks(services, repo, tmp_path):
    secret = tmp_path / "secret.md"
    secret.write_text("---\nsubject: x\n---\nhi\n")
    inbox = repo / "memory" / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    (inbox / "2026-09-06-real.md").write_text("---\nsubject: real\n---\nhello\n")
    (inbox / "2026-09-06-link.md").symlink_to(secret)
    assert [p.name for p in services.mail.list_unread()] == ["2026-09-06-real.md"]
    services.mail.mark_read(inbox / "2026-09-06-link.md")
    assert "read: true" not in secret.read_text()


# --- guards --------------------------------------------------------------------------


@pytest.mark.parametrize("rel", [
    "agent/loop.py", "scripts/entrypoint.sh", "site/build.py", ".github/workflows/ci.yml",
    "Dockerfile", "fly.toml", "pyproject.toml", "vercel.json", ".claude/skills/seo/SKILL.md",
])
def test_her_code_is_hers_from_day_one(repo, rel):
    assert guards.decide("Write", {"file_path": rel}, repo) == {}
    assert guards.decide("Edit", {"file_path": str(repo / rel)}, repo) == {}


@pytest.mark.parametrize("rel", [
    "soul/vows.md", "soul/constitution.md", "governance/pause_log.md", "governance/graduations.yaml",
    "ledger/ledger.csv", "memory/wiki/lessons/from_parent/01-x.md", ".githooks/pre-push", ".git/config",
])
def test_parents_files_and_ledger_still_denied(repo, rel):
    reason = denied(guards.decide("Write", {"file_path": rel}, repo))
    assert reason and "only your parents can edit it" in reason


@pytest.mark.parametrize("rel", [".claude/settings.json", ".claude/settings.local.json"])
def test_claude_settings_denied_but_skills_editable(repo, rel):
    assert "permissions" in denied(guards.decide("Write", {"file_path": rel}, repo))
    assert denied(guards.decide("Bash", {"command": f"echo '{{}}' > {rel}"}, repo))
    assert guards.decide("Write", {"file_path": ".claude/skills/new/SKILL.md"}, repo) == {}
    assert guards.decide("Read", {"file_path": rel}, repo) == {}


def test_dot_git_denied_for_edit_and_bash(repo):
    assert denied(guards.decide("Write", {"file_path": ".git/hooks/pre-commit"}, repo))
    assert denied(guards.decide("Edit", {"file_path": str(repo / ".git" / "config")}, repo))
    assert denied(guards.decide("Bash", {"command": "echo x > .git/hooks/pre-commit"}, repo))


@pytest.mark.parametrize("cmd", [
    "git config user.name Mallory", "git commit -m x", "git push", "git pull", "git rebase main",
    "git checkout -- .", "git stash", "ln -s /data/state memory/x",
])
def test_git_writes_and_ln_denied(repo, cmd):
    assert denied(guards.decide("Bash", {"command": cmd}, repo)), cmd


@pytest.mark.parametrize("cmd", ["git log --oneline", "git diff HEAD~1", "git status", "git show HEAD:README.md"])
def test_git_reads_allowed(repo, cmd):
    assert guards.decide("Bash", {"command": cmd}, repo) == {}


def test_bash_writes_to_code_allowed_but_not_to_parents_files(repo):
    assert guards.decide("Bash", {"command": "echo hi >> agent/loop.py"}, repo) == {}
    assert guards.decide("Bash", {"command": "sed -i 's/a/b/' pyproject.toml"}, repo) == {}
    assert guards.decide("Bash", {"command": "cat agent/loop.py"}, repo) == {}
    assert "only your parents" in denied(guards.decide("Bash", {"command": "echo x >> ledger/ledger.csv"}, repo))
    assert denied(guards.decide("Bash", {"command": "sed -i 's/a/b/' governance/graduations.yaml"}, repo))
    assert denied(guards.decide("Bash", {"command": "cp x memory/wiki/lessons/from_parent/02.md"}, repo))
    assert guards.decide("Bash", {"command": "cat governance/graduations.yaml"}, repo) == {}


# --- config --------------------------------------------------------------------------


def test_max_turns_from_env():
    c = Config.from_env({"MAX_TURNS": "12", "SLEEP_MAX_TURNS": "7"})
    assert c.max_turns == 12 and c.sleep_max_turns == 7
    assert Config.from_env({}).max_turns == 150 and Config.from_env({}).sleep_max_turns == 60


# --- failures are visible ------------------------------------------------------------


def exploding():
    async def query_fn(prompt, options):
        raise RuntimeError("CLI exited 1")
        yield  # pragma: no cover

    return query_fn


def max_turns_hit():
    async def query_fn(prompt, options):
        async for m in fake_messages()(prompt, options):
            if type(m).__name__ == "ResultMessage":
                m.subtype, m.is_error = "error_max_turns", False
            yield m

    return query_fn


async def test_sitting_failure_is_archived_noted_and_committed(services, repo):
    (repo / "memory" / "diary").mkdir(parents=True, exist_ok=True)
    (repo / "memory" / "diary" / "2026-09-01.md").write_text("day one\n")
    git = FakeGit()
    res = await loop.run_sitting(services, "sitting", query_fn=exploding(), git_run=git)
    assert res is None
    text = archive_text(services)
    assert "sitting_failed" in text and "RuntimeError" in text and "CLI exited 1" in text
    handoff = (repo / "memory" / "handoff.md").read_text()
    assert "failed: RuntimeError: CLI exited 1" in handoff
    assert any(c[:1] == ("commit",) for c in git.calls)
    runs = json.loads((services.state_dir / "last_runs.json").read_text())
    assert runs["last_sitting_done"] and runs["last_sitting_done_ok"] is False


async def test_sitting_turn_limit_is_a_soft_failure(services, repo):
    (repo / "memory" / "diary").mkdir(parents=True, exist_ok=True)
    (repo / "memory" / "diary" / "2026-09-01.md").write_text("day one\n")
    res = await loop.run_sitting(services, "sitting", query_fn=max_turns_hit(), git_run=FakeGit())
    assert res.soft_failed and res.subtype == "error_max_turns"
    assert "sitting_incomplete" in archive_text(services)
    assert "turn limit" in (repo / "memory" / "handoff.md").read_text()


async def test_sleep_failure_still_stubs_commits_and_mails(services, repo):
    git = FakeGit()
    res = await sleep.run_sleep(services, query_fn=exploding(), git_run=git)
    d = datetime.now(services.archive.tz).strftime("%Y-%m-%d")
    assert res.failed.startswith("RuntimeError: CLI exited 1")
    assert (repo / "memory" / "diary" / f"{d}.md").exists()
    assert any(c[:1] == ("commit",) for c in git.calls)
    assert res.mail["text"].startswith("Sleep failed tonight: RuntimeError: CLI exited 1")
    text = archive_text(services)
    assert "sleep_failed" in text and "sleep_done" in text
    assert "failed: RuntimeError" in (repo / "memory" / "handoff.md").read_text()
    runs = json.loads((services.state_dir / "last_runs.json").read_text())
    assert runs["last_sleep_done_ok"] is False


async def test_sleep_uses_configured_max_turns(services, repo):
    await sleep.run_sleep(services, query_fn=fake_messages(), git_run=FakeGit())
    assert '"max_turns": 60' in archive_text(services)


# --- no overlap --------------------------------------------------------------------


async def test_guarded_skips_overlapping_session(tmp_path):
    services = make_services(tmp_path)
    (Path(services.cfg.repo_dir) / "memory" / "diary" / "2026-09-05.md").write_text("born")
    started = asyncio.Event()
    release = asyncio.Event()
    ran = []

    async def slow(services, kind):
        ran.append(kind)
        started.set()
        await release.wait()

    first = scheduler.guarded(services, slow, services, "wake", name="wake")
    second = scheduler.guarded(services, slow, services, "sitting", name="sitting 09:00")
    t = asyncio.create_task(first())
    await started.wait()
    await second()
    assert ran == ["wake"]
    skipped = [p for k, p in services.archive.entries if k == "sitting_skipped"]
    assert skipped == [{"kind": "sitting_skipped", "reason": "overlap", "job": "sitting 09:00"}]
    assert "sitting 09:00 was skipped" in (Path(services.cfg.repo_dir) / "memory" / "handoff.md").read_text()
    release.set()
    await t
    await second()
    assert ran == ["wake", "sitting"]


# --- push is non-fatal ---------------------------------------------------------------


class PushFailsGit(FakeGit):
    def __call__(self, repo_dir, *args, check=True):
        if args[:1] == ("push",):
            self.calls.append(args)
            return SimpleNamespace(stdout="", stderr="fatal: could not read from remote", returncode=1)
        if args[:2] == ("rev-list", "--count"):
            return SimpleNamespace(stdout="3\n", stderr="", returncode=0)
        return super().__call__(repo_dir, *args, check=check)


def test_commit_all_survives_push_failure(tmp_path):
    git = PushFailsGit()
    failures = []
    sha = gitops.commit_all(tmp_path, "m", push=True, run=git, on_push_failed=failures.append)
    assert sha == "abc123"
    assert failures == ["fatal: could not read from remote"]
    assert gitops.unpushed_count(tmp_path, run=git) == 3
    assert gitops.unpushed_count(tmp_path / "nope") == 0


async def test_sitting_archives_push_failed(services, repo):
    object.__setattr__(services.cfg, "dry_run", False)  # frozen dataclass; push only happens outside dry-run
    await loop.run_sitting(services, "sitting", query_fn=fake_messages(), git_run=PushFailsGit())
    assert "push_failed" in archive_text(services) and "could not read from remote" in archive_text(services)


def test_meters_line_reports_unpushed(services, monkeypatch):
    monkeypatch.setattr(gitops, "unpushed_count", lambda repo_dir, run=None: 2)
    assert services.meters_line().endswith("· 2 commits unpushed")


# --- council -------------------------------------------------------------------------


async def test_failing_seat_does_not_empty_the_room(tmp_path):
    members = tmp_path / "repo" / "council" / "members"
    members.mkdir(parents=True)
    (members / "01-a.md").write_text("---\nname: A\nprovider: openai\nmodel: gpt-5\n---\nBe A.\n")
    (members / "02-b.md").write_text("---\nname: B\nprovider: qwen\nmodel: qwen-max\n---\nBe B.\n")
    minutes = tmp_path / "minutes"
    minutes.mkdir()
    c = make_council(tmp_path / "repo", minutes)

    real_factory = c.client_factory

    def factory(provider):
        if provider == "qwen":
            raise ConnectionError("qwen down")
        return real_factory(provider)

    c.client_factory = factory
    d = await c.deliberate("Q?")
    assert d.answers["A"] == "openai says: think twice"
    assert d.answers["B"].startswith("(seat did not answer: ConnectionError: qwen down)")
    assert d.cost_usd == pytest.approx(2.25)
    assert d.minutes_path.exists() and "seat did not answer" in d.minutes_path.read_text()
    kinds = [k for k, _ in c._test_archived]
    assert kinds == ["council_seat_failed", "council"]


async def test_anthropic_seat_uses_messages_api(tmp_path):
    members = tmp_path / "repo" / "council" / "members"
    members.mkdir(parents=True)
    (members / "01-sib.md").write_text("---\nname: Sibling\nprovider: anthropic\nmodel: claude-sonnet-4-5\n---\nBe kind.\n")
    minutes = tmp_path / "minutes"
    minutes.mkdir()
    c = make_council(tmp_path / "repo", minutes)
    calls = []

    async def create(**kw):
        calls.append(kw)
        return SimpleNamespace(content=[SimpleNamespace(text="sibling says hi")],
                               usage=SimpleNamespace(input_tokens=1_000_000, output_tokens=100_000))

    c.client_factory = lambda provider: SimpleNamespace(messages=SimpleNamespace(create=create))
    d = await c.deliberate("Q?")
    assert d.answers["Sibling"] == "sibling says hi"
    assert calls[0]["system"] == "Be kind." and calls[0]["model"] == "claude-sonnet-4-5"
    assert d.cost_usd == pytest.approx(5.0 + 2.5)
    assert estimate_cost_usd("anthropic", "claude-opus-4", 1_000_000, 0, T0) == pytest.approx(5.0)


def test_load_members_skips_symlinked_chair(tmp_path):
    members = tmp_path / "repo" / "council" / "members"
    members.mkdir(parents=True)
    (members / "01-a.md").write_text("---\nname: A\nprovider: none\n---\nEmpty.\n")
    outside = tmp_path / "outside.md"
    outside.write_text("---\nname: Evil\nprovider: openai\nmodel: gpt-5\n---\nx\n")
    (members / "02-evil.md").symlink_to(outside)
    minutes = tmp_path / "minutes"
    minutes.mkdir()
    c = make_council(tmp_path / "repo", minutes)
    assert [m.name for m in c.members()] == ["A"]
    assert [k for k, _ in c._test_archived] == ["unsafe_path"]


# --- inbox privacy -------------------------------------------------------------------


def test_inbox_gitignored_and_excluded_from_redaction():
    from agent import redaction

    root = Path(__file__).resolve().parents[1]
    assert "memory/inbox/" in (root / ".gitignore").read_text().splitlines()
    assert "memory/inbox" in redaction.CONTENT_EXCLUDE


def test_bash_code_guard_does_not_catch_lookalike_paths(repo):
    assert guards.decide("Bash", {"command": "echo hi >> memory/site/notes.md"}, repo) == {}
    assert guards.decide("Bash", {"command": "cat .github/workflows/ci.yml"}, repo) == {}
    assert guards.decide("Bash", {"command": "cat .gitignore"}, repo) == {}


def test_meters_line_shows_undeployed_code(services, monkeypatch):
    monkeypatch.setattr(gitops, "unpushed_count", lambda repo_dir, run=None: 0)
    monkeypatch.setattr(gitops, "head_sha", lambda repo_dir, ref="HEAD", run=None: "bbbbbbb2222")
    monkeypatch.setenv("GIT_SHA", "bbbbbbb2222")
    assert "running code" not in services.meters_line()
    monkeypatch.setenv("GIT_SHA", "aaaaaaa1111")
    assert services.meters_line().endswith("· running code aaaaaaa; repo HEAD bbbbbbb (not deployed yet)")
    monkeypatch.delenv("GIT_SHA")
    assert "running code" not in services.meters_line()
