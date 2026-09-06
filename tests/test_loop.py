"""run_sitting: birth detection, pause skip, hard-cap skip, prompt composition, commit via fake git."""

from types import SimpleNamespace

from agent import loop
from conftest import archive_text
from test_session import fake_messages


class FakeGit:
    def __init__(self, dirty=True):
        self.calls = []
        self.dirty = dirty

    def __call__(self, repo_dir, *args, check=True):
        self.calls.append(args)
        if args[:1] == ("status",):
            return SimpleNamespace(stdout=" M memory/handoff.md\n" if self.dirty else "", returncode=0)
        if args[:1] == ("rev-parse",):
            return SimpleNamespace(stdout="abc123\n", returncode=0)
        return SimpleNamespace(stdout="", returncode=0)


async def test_birth_when_diary_empty(services, repo):
    seen = {}

    async def query_fn(prompt, options):
        seen["prompt"] = prompt
        async for m in fake_messages()(prompt, options):
            yield m

    git = FakeGit()
    await loop.run_sitting(services, "sitting", query_fn=query_fn, git_run=git)
    assert "first day" in seen["prompt"]
    assert "## Meters" in seen["prompt"] and "Unread mail" in seen["prompt"]
    assert ("commit", "-m", loop.datetime.now(services.archive.tz).strftime("birth: %Y-%m-%d sitting 1")) in git.calls
    assert ("push",) not in git.calls  # dry_run
    assert '"kind": "sitting_done"' in archive_text(services) or "sitting_done" in archive_text(services)


async def test_sitting_prompt_when_diary_exists(services, repo):
    for d in ("2026-09-01", "2026-09-02", "2026-09-03", "2026-09-04"):
        (repo / "memory/diary" / f"{d}.md").write_text(f"diary {d}\n")
    (repo / "memory/diary/2026-09-04.agent.md").write_text("AGENT TWIN\n")
    (repo / "memory/handoff.md").write_text("Next: reply to mail.\n")
    (repo / "memory/inbox/2026-09-04-note.md").write_text('---\nfrom: parent-b\nsubject: "Breakfast note"\n---\n\nHi.\n')
    prompt = loop.compose_user_prompt(services, "sitting")
    assert "This is a sitting" in prompt
    assert "diary 2026-09-01" not in prompt and "diary 2026-09-02" in prompt  # last three only
    assert "AGENT TWIN" not in prompt
    assert "Next: reply to mail." in prompt
    assert "- Breakfast note" in prompt


async def test_paused_skips(services):
    services.state_dir.mkdir(parents=True, exist_ok=True)
    (services.state_dir / "paused").write_text("reason\n")
    git = FakeGit()
    assert await loop.run_sitting(services, "sitting", query_fn=fake_messages(), git_run=git) is None
    assert git.calls == []
    assert '"reason": "paused"' in archive_text(services)


async def test_hard_cap_skip_writes_handoff(services, repo):
    services.inference.add_usd(45.0, "burned")
    git = FakeGit()
    assert await loop.run_sitting(services, "sitting", query_fn=fake_messages(), git_run=git) is None
    handoff = (repo / "memory/handoff.md").read_text()
    assert "Sitting skipped: daily food bill hit the hard cap ($45.00 of $40.00)." in handoff
    assert git.calls == []


async def test_nothing_to_commit(services, repo):
    (repo / "memory/diary/2026-09-01.md").write_text("x\n")
    git = FakeGit(dirty=False)
    res = await loop.run_sitting(services, "sitting", query_fn=fake_messages(), git_run=git)
    assert res.cost_usd == 0.42
    assert not any(c[:1] == ("commit",) for c in git.calls)


async def test_redaction_runs_before_commit(services, repo, tmp_path):
    (repo / "memory/diary/2026-09-01.md").write_text("Met Alice Realname today.\n")
    await loop.run_sitting(services, "sitting", query_fn=fake_messages(), git_run=FakeGit())
    assert "Alice Realname" not in (repo / "memory/diary/2026-09-01.md").read_text()
    logs = list((tmp_path / "redaction").glob("*.json"))
    assert logs and "Alice" not in logs[0].read_text()


async def test_birth_decided_by_archive_not_diary(services, repo):
    """A failed birth (no diary written) is not repeated: the next sitting is a normal one."""
    async def dying(prompt, options):
        raise RuntimeError("cli crashed")
        yield  # pragma: no cover

    await loop.run_sitting(services, "sitting", query_fn=dying, git_run=FakeGit())
    assert not loop.diary_entries(repo)
    assert services.archive.any("session_start", "birth")
    assert "birth" in (repo / "memory/handoff.md").read_text() and "failed" in (repo / "memory/handoff.md").read_text()

    seen = {}

    async def query_fn(prompt, options):
        seen["prompt"] = prompt
        async for m in fake_messages()(prompt, options):
            yield m

    git = FakeGit()
    await loop.run_sitting(services, "sitting", query_fn=query_fn, git_run=git)
    assert "This is a sitting" in seen["prompt"] and "first day" not in seen["prompt"]
    assert any(c[:2] == ("commit", "-m") and c[2].startswith("sitting:") for c in git.calls)


def test_is_birth(services, repo):
    assert loop.is_birth(services)
    services.archive.append("session_start", {"kind": "sitting"})
    assert loop.is_birth(services)  # an ordinary session_start does not count
    services.archive.append("session_start", {"kind": "birth"})
    assert not loop.is_birth(services)


async def test_mail_kind_uses_sitting_prompt_with_header(services, repo):
    (repo / "memory/diary/2026-09-04.md").write_text("diary\n")
    prompt = loop.compose_user_prompt(services, "mail")
    assert prompt.startswith("You were woken by new mail.\n\n")
    assert "This is a sitting" in prompt
    assert "You were woken by new mail." not in loop.compose_user_prompt(services, "sitting")

    seen = {}

    async def query_fn(prompt, options):
        seen["prompt"] = prompt
        async for m in fake_messages()(prompt, options):
            yield m

    git = FakeGit()
    await loop.run_sitting(services, "mail", query_fn=query_fn, git_run=git)
    assert seen["prompt"].startswith("You were woken by new mail.")
    assert ("commit", "-m", loop.datetime.now(services.archive.tz).strftime("mail: %Y-%m-%d sitting 1")) in git.calls
    assert '"kind": "mail"' in archive_text(services)
