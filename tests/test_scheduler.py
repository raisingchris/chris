from pathlib import Path
"""Scheduler: weekday vs Sunday job sets, pause guard, next_runs."""

from datetime import date, datetime

import pytest
from fake_services import make_services

from agent import pause
from agent.scheduler import due_on, guarded, make_scheduler, next_runs


class Calls:
    def __init__(self):
        self.sittings = []
        self.sleeps = 0

    async def run_sitting(self, services, kind):
        self.sittings.append(kind)

    async def run_sleep(self, services):
        self.sleeps += 1


@pytest.fixture
def services(tmp_path):
    s = make_services(tmp_path)
    # most tests concern a Chris who already exists
    (Path(s.cfg.repo_dir) / "memory" / "diary" / "2026-09-05.md").write_text("yesterday")
    return s


@pytest.fixture
def calls():
    return Calls()


@pytest.fixture
def sched(services, calls):
    return make_scheduler(services, calls.run_sitting, calls.run_sleep)


def test_weekday_jobs(sched):
    # 2026-09-07 is a Monday
    assert due_on(sched, date(2026, 9, 7)) == [
        "git-pull", "wake", "unseal", "sitting-09:00", "sitting-13:00", "sitting-17:00", "sleep", "backup",
    ]


def test_sunday_jobs(sched):
    # 2026-09-06 is a Sunday: no wake, no ordinary sittings — one letter home and sleep.
    assert due_on(sched, date(2026, 9, 6)) == ["git-pull", "unseal", "sunday", "sleep", "backup"]


async def test_backup_job_runs_unguarded_and_notes_last_run(sched, services, monkeypatch):
    """Backup fires even while paused (or unborn) and records last_backup_done."""
    from agent import backup as backup_mod, wiring

    job = sched.get_job("backup")
    assert job is not None
    t = job.trigger.get_next_fire_time(None, datetime(2026, 9, 7, tzinfo=sched.timezone))
    assert (t.hour, t.minute) == (22, 45)

    seen = []

    def fake_run(_services):
        seen.append(1)
        return {"kind": "backup_done", "objects": [], "bytes": 0}

    monkeypatch.setattr(backup_mod, "run_backup", fake_run)
    pause.trigger(services, "Runaway loop, condition 4.", "parent-a")
    await job.func()
    assert seen == [1]
    runs = wiring.read_last_runs(services.cfg.state_dir)
    assert runs["last_backup_done"] and runs["last_backup_done_ok"] is True
    assert runs["last_backup_done_kind"] == "backup_done"


async def test_backup_job_skip_path_noted(sched, services, monkeypatch):
    from agent import wiring

    monkeypatch.delenv("GCS_ARCHIVE_BUCKET", raising=False)
    monkeypatch.delenv("GCS_ARCHIVE_SA_JSON", raising=False)
    await sched.get_job("backup").func()
    assert services.archive.entries[-1][1]["kind"] == "backup_skipped"
    runs = wiring.read_last_runs(services.cfg.state_dir)
    assert runs["last_backup_done_ok"] is False and runs["last_backup_done_kind"] == "backup_skipped"


def test_job_defaults(sched):
    for job in sched.get_jobs():
        assert job.misfire_grace_time == 600
        assert job.coalesce is True
        assert job.max_instances == 1


def test_timezone(sched):
    assert str(sched.timezone) == "America/New_York"


async def test_guarded_skips_when_paused(services, calls):
    job = guarded(services, calls.run_sitting, services, "sitting", name="sitting")
    await job()
    assert calls.sittings == ["sitting"]

    pause.trigger(services, "Runaway loop, condition 4.", "parent-a")
    await job()
    assert calls.sittings == ["sitting"]  # not run again

    pause.release(services, "parent-a")
    await job()
    assert calls.sittings == ["sitting", "sitting"]


async def test_scheduled_jobs_run_the_real_functions(sched, calls, services):
    for jid, expect in (("wake", "wake"), ("sunday", "sunday"), ("sitting-13:00", "sitting")):
        await sched.get_job(jid).func()
        assert calls.sittings[-1] == expect
    await sched.get_job("sleep").func()
    assert calls.sleeps == 1
    await sched.get_job("unseal").func()
    assert services.council.unsealed == 1


def test_next_runs_before_start(sched):
    runs = next_runs(sched)
    assert runs and all(t is not None for _, t in runs)
    assert [t for _, t in runs] == sorted(t for _, t in runs)


def test_birth_at_one_off_and_not_born_gate(services, monkeypatch):
    from agent.scheduler import make_scheduler
    import asyncio
    calls = []

    async def fake_sitting(_services, kind):
        calls.append(kind)

    async def fake_sleep(_services):
        calls.append("sleep")

    (Path(services.cfg.repo_dir) / "memory" / "diary" / "2026-09-05.md").unlink()
    monkeypatch.setenv("BIRTH_AT", "21:30")
    sched = make_scheduler(services, fake_sitting, fake_sleep)
    assert sched.get_job("birth") is not None
    # before birth every other job is a no-op
    asyncio.run(sched.get_job("sleep").func())
    assert calls == []
    asyncio.run(sched.get_job("birth").func())
    assert calls == ["wake"]
    # once a diary exists she is born; the birth job is not added again and sleep runs
    (Path(services.cfg.repo_dir) / "memory" / "diary").mkdir(parents=True, exist_ok=True)
    (Path(services.cfg.repo_dir) / "memory" / "diary" / "2026-09-06.md").write_text("born")
    asyncio.run(sched.get_job("sleep").func())
    assert calls == ["wake", "sleep"]
    sched2 = make_scheduler(services, fake_sitting, fake_sleep)
    assert sched2.get_job("birth") is None
