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


async def test_sitting_prompt_carries_commitments_when_present(services, repo):
    (repo / "memory/diary/2026-09-01.md").write_text("diary\n")
    prompt = loop.compose_user_prompt(services, "sitting")
    assert "commitments.md" not in prompt  # no file, no section
    self_dir = repo / "memory/wiki/self"
    self_dir.mkdir(parents=True, exist_ok=True)
    (self_dir / "commitments.md").write_text("| 1 | Cairn | add the row | reply | OPEN |\n")
    prompt = loop.compose_user_prompt(services, "sitting")
    assert "## memory/wiki/self/commitments.md" in prompt
    assert "| 1 | Cairn | add the row | reply | OPEN |" in prompt


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


# --- continuation sittings ------------------------------------------------------


def test_handoff_has_pending():
    h = loop.handoff_has_pending
    assert h("") is False
    assert h("Wrote the diary. All good.\n") is False
    assert h("Next: reply to Cairn.\n") is True
    assert h("NEXT: reply to Cairn.\n") is True
    assert h("- [ ] finish the sitemap\n") is True
    assert h("- [x] finish the sitemap\n") is False
    assert h("TODO: check the ledger\n") is True
    assert h("Pending: the letter home\n") is True
    assert h("  todo: indented still counts\n") is True
    assert h("The next: thing mid-line does not count\n") is False
    # a closing line stops the chain, wherever it sits
    assert h("Next: reply to Cairn.\nnothing pending\n") is False
    assert h("Next: reply to Cairn.\nNothing pending.\n") is False
    assert h("- [ ] x\nDone for now\n") is False
    assert h("todo: y\nNo work pending\n") is False
    assert h("nothing pending\n") is False


async def test_continue_kind_uses_sitting_prompt_with_header(services, repo):
    (repo / "memory/diary/2026-09-04.md").write_text("diary\n")
    prompt = loop.compose_user_prompt(services, "continue")
    assert prompt.startswith(loop.KIND_HEADER["continue"] + "\n\n")
    assert "You are continuing: your last sitting ended with work pending." in prompt
    assert "This is a sitting" in prompt
    assert "You are continuing" not in loop.compose_user_prompt(services, "sitting")

    seen = {}

    async def query_fn(prompt, options):
        seen["prompt"] = prompt
        async for m in fake_messages()(prompt, options):
            yield m

    git = FakeGit()
    await loop.run_sitting(services, "continue", query_fn=query_fn, git_run=git)
    assert seen["prompt"].startswith("You are continuing")
    assert ("commit", "-m", loop.datetime.now(services.archive.tz).strftime("continue: %Y-%m-%d sitting 1")) in git.calls


class FakeScheduler:
    def __init__(self):
        self.jobs = []

    def add_job(self, fn, trigger, **kw):
        self.jobs.append((fn, trigger, kw))


async def test_sitting_end_requests_continuation_when_pending(services, repo, monkeypatch):
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from agent import scheduler as scheduler_module

    (repo / "memory/diary/2026-09-04.md").write_text("diary\n")
    fs = FakeScheduler()
    services.scheduler = fs
    seen = []
    real = scheduler_module.request_continuation

    def spy(svc, sched, run_sitting=None, now=None):
        seen.append(sched)
        return real(svc, sched, run_sitting=run_sitting,
                    now=datetime(2026, 9, 7, 10, 30, tzinfo=ZoneInfo(services.cfg.tz)))

    monkeypatch.setattr(scheduler_module, "request_continuation", spy)

    # no pending work → archived as not pending, scheduler untouched
    (repo / "memory/handoff.md").write_text("All done. nothing pending\n")
    await loop.run_sitting(services, "sitting", query_fn=fake_messages(), git_run=FakeGit())
    assert '"pending": false' in archive_text(services)
    assert seen == [] and fs.jobs == []

    # pending work → the loop asks the scheduler for a continuation 30 minutes out
    (repo / "memory/handoff.md").write_text("Next: finish the sitemap.\n")
    await loop.run_sitting(services, "sitting", query_fn=fake_messages(), git_run=FakeGit())
    assert seen == [fs]
    fn, trigger, kw = fs.jobs[-1]
    assert kw["id"] == "continuation"
    assert trigger.run_date == datetime(2026, 9, 7, 11, 0, tzinfo=ZoneInfo(services.cfg.tz))
    assert '"pending": true' in archive_text(services) and '"kind": "continuation"' in archive_text(services)


async def test_sitting_end_without_scheduler_is_noop(services, repo):
    (repo / "memory/diary/2026-09-04.md").write_text("diary\n")
    (repo / "memory/handoff.md").write_text("Next: finish the sitemap.\n")
    assert getattr(services, "scheduler", None) is None
    res = await loop.run_sitting(services, "sitting", query_fn=fake_messages(), git_run=FakeGit())
    assert res is not None
    assert "sitting_pending" in archive_text(services)
    assert "continuation_skipped" not in archive_text(services)


def test_meters_line_counts_continuations(services):
    import json
    from datetime import datetime

    assert "continuations today" not in services.meters_line()
    services.state_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now(services.archive.tz).date().isoformat()
    (services.state_dir / "continuation.json").write_text(json.dumps({"day": today, "count": 3}))
    assert services.meters_line().endswith(" · 3 continuations today")
