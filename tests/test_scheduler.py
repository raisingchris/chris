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
        "git-pull", "wake", "unseal", "sitting-09:00", "sitting-12:00", "sitting-15:00", "sitting-18:00",
        "sleep", "backup",
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
        return {"kind": "backup_done", "changed": False, "commit": None, "files": 0}

    monkeypatch.setattr(backup_mod, "run_backup", fake_run)
    pause.trigger(services, "Runaway loop, condition 4.", "parent-a")
    await job.func()
    assert seen == [1]
    runs = wiring.read_last_runs(services.cfg.state_dir)
    assert runs["last_backup_done"] and runs["last_backup_done_ok"] is True
    assert runs["last_backup_done_kind"] == "backup_done"


async def test_backup_job_skip_path_noted(sched, services, monkeypatch):
    from agent import wiring

    monkeypatch.delenv("BACKUP_GIT_URL", raising=False)
    monkeypatch.delenv("BACKUP_DEPLOY_KEY", raising=False)
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
    for jid, expect in (("wake", "wake"), ("sunday", "sunday"), ("sitting-12:00", "sitting")):
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


# --- wake on mail --------------------------------------------------------------------


def _mon(h, m=0):
    """Monday 2026-09-07 at h:m, her time."""
    from zoneinfo import ZoneInfo

    return datetime(2026, 9, 7, h, m, tzinfo=ZoneInfo("America/New_York"))


def test_mail_wake_decision(services):
    from agent.scheduler import mail_wake_decision as d

    cfg = services.cfg
    assert d(_mon(10, 30), {}, cfg, born=True, paused=False) == (True, "ok")
    assert d(_mon(10, 30), {}, cfg, born=False, paused=False) == (False, "unborn")
    assert d(_mon(10, 30), {}, cfg, born=True, paused=True) == (False, "paused")
    # sleep hours 22:00–07:00
    assert d(_mon(22, 0), {}, cfg, born=True, paused=False) == (False, "sleep_hours")
    assert d(_mon(3, 0), {}, cfg, born=True, paused=False) == (False, "sleep_hours")
    assert d(_mon(6, 59), {}, cfg, born=True, paused=False) == (False, "sleep_hours")
    assert d(_mon(7, 0), {}, cfg, born=True, paused=False)[0] is True
    # within 20 minutes before a scheduled sitting or sleep it would just overlap
    assert d(_mon(11, 41), {}, cfg, born=True, paused=False) == (False, "near_scheduled")  # 12:00 sitting
    assert d(_mon(11, 39), {}, cfg, born=True, paused=False)[0] is True
    assert d(_mon(12, 0), {}, cfg, born=True, paused=False) == (False, "near_scheduled")
    assert d(_mon(12, 1), {}, cfg, born=True, paused=False)[0] is True
    assert d(_mon(21, 45), {}, cfg, born=True, paused=False) == (False, "near_scheduled")  # 22:00 sleep
    # debounce: one per 30 minutes
    state = {"last": _mon(10, 10).isoformat(), "day": "2026-09-07", "count": 1}
    assert d(_mon(10, 30), state, cfg, born=True, paused=False) == (False, "debounce")
    assert d(_mon(10, 40), state, cfg, born=True, paused=False) == (True, "ok")
    # daily cap of six, reset the next day
    state = {"last": _mon(8, 0).isoformat(), "day": "2026-09-07", "count": 6}
    assert d(_mon(10, 30), state, cfg, born=True, paused=False) == (False, "daily_cap")
    assert d(_mon(10, 30) + __import__("datetime").timedelta(days=1), {**state, "day": "2026-09-07"},
             cfg, born=True, paused=False) == (True, "ok")
    assert d(_mon(10, 30), {**state, "count": 5}, cfg, born=True, paused=False) == (True, "ok")


class FakeSched:
    def __init__(self):
        self.jobs = []

    def add_job(self, fn, trigger, **kw):
        self.jobs.append((fn, trigger, kw))


async def test_request_mail_wake_adds_one_off_job_and_counts(services, calls):
    from agent.scheduler import mail_wakes_today, read_mail_wake_state, request_mail_wake

    fs = FakeSched()
    ok, reason = request_mail_wake(services, fs, run_sitting=calls.run_sitting, now=_mon(10, 30))
    assert (ok, reason) == (True, "ok")
    fn, trigger, kw = fs.jobs[-1]
    assert kw["id"] == "mail-wake" and kw["replace_existing"] is True and kw["misfire_grace_time"] == 600
    assert trigger.run_date == _mon(10, 31)
    await fn()
    assert calls.sittings == ["mail"]
    st = read_mail_wake_state(services.cfg.state_dir)
    assert st["count"] == 1 and st["day"] == "2026-09-07"
    assert mail_wakes_today(services.cfg.state_dir, _mon(10, 32)) == 1
    assert mail_wakes_today(services.cfg.state_dir, _mon(10, 32).replace(day=8)) == 0
    assert services.archive.entries[-1][1]["kind"] == "mail_wake"

    # a second mail ten minutes later is debounced and archived as skipped
    assert request_mail_wake(services, fs, run_sitting=calls.run_sitting, now=_mon(10, 40)) == (False, "debounce")
    assert len(fs.jobs) == 1
    assert services.archive.entries[-1][1] == {"kind": "mail_wake_skipped", "reason": "debounce"}

    # paused → skipped
    pause.trigger(services, "Runaway loop, condition 4.", "parent-a")
    assert request_mail_wake(services, fs, run_sitting=calls.run_sitting, now=_mon(11, 20)) == (False, "paused")


def test_request_mail_wake_without_scheduler(services):
    from agent.scheduler import request_mail_wake

    assert request_mail_wake(services, None, now=_mon(10, 30)) == (False, "no_scheduler")
    assert services.archive.entries[-1][1]["reason"] == "no_scheduler"


# --- continuation sittings ------------------------------------------------------


def test_continuation_decision(services):
    from agent.scheduler import continuation_decision as d

    cfg = services.cfg
    ok = dict(born=True, paused=False, spent_today=5.0, soft_usd=25.0)
    assert d(_mon(10, 30), {}, cfg, **ok) == (True, "ok")
    assert d(_mon(10, 30), {}, cfg, **{**ok, "born": False}) == (False, "unborn")
    assert d(_mon(10, 30), {}, cfg, **{**ok, "paused": True}) == (False, "paused")
    # sleep hours 22:00–07:00
    assert d(_mon(22, 0), {}, cfg, **ok) == (False, "sleep_hours")
    assert d(_mon(3, 0), {}, cfg, **ok) == (False, "sleep_hours")
    assert d(_mon(7, 0), {}, cfg, **ok)[0] is True
    # at or past the soft cap the chain stops
    assert d(_mon(10, 30), {}, cfg, **{**ok, "spent_today": 25.0}) == (False, "soft_cap")
    assert d(_mon(10, 30), {}, cfg, **{**ok, "spent_today": 24.99})[0] is True
    # within 45 minutes of a scheduled sitting or sleep, the clock one picks the work up
    assert d(_mon(11, 16), {}, cfg, **ok) == (False, "near_scheduled")  # 12:00 sitting
    assert d(_mon(11, 14), {}, cfg, **ok)[0] is True
    assert d(_mon(12, 0), {}, cfg, **ok) == (False, "near_scheduled")
    assert d(_mon(12, 1), {}, cfg, **ok)[0] is True
    assert d(_mon(21, 20), {}, cfg, **ok) == (False, "near_scheduled")  # 22:00 sleep
    # daily cap of twelve, reset the next day
    state = {"day": "2026-09-07", "count": 12}
    assert d(_mon(10, 30), state, cfg, **ok) == (False, "daily_cap")
    assert d(_mon(10, 30), {**state, "count": 11}, cfg, **ok) == (True, "ok")
    assert d(_mon(10, 30) + __import__("datetime").timedelta(days=1), state, cfg, **ok) == (True, "ok")
    small = make_services(Path(services.cfg.state_dir).parent / "small", continuations_per_day=2).cfg
    assert d(_mon(10, 30), {"day": "2026-09-07", "count": 2}, small, **ok) == (False, "daily_cap")


async def test_request_continuation_adds_one_off_job_and_counts(services, calls):
    from agent.scheduler import continuations_today, read_continuation_state, request_continuation

    fs = FakeSched()
    assert request_continuation(services, fs, run_sitting=calls.run_sitting, now=_mon(10, 30)) == (True, "ok")
    fn, trigger, kw = fs.jobs[-1]
    assert kw["id"] == "continuation" and kw["replace_existing"] is True and kw["misfire_grace_time"] == 600
    assert trigger.run_date == _mon(11, 0)
    await fn()
    assert calls.sittings == ["continue"]
    assert read_continuation_state(services.cfg.state_dir) == {"day": "2026-09-07", "count": 1}
    assert continuations_today(services.cfg.state_dir, _mon(11, 5)) == 1
    assert continuations_today(services.cfg.state_dir, _mon(11, 5).replace(day=8)) == 0
    assert services.archive.entries[-1][1] == {"kind": "continuation", "at": "2026-09-07T11:00:00-04:00", "n_today": 1}

    # over the soft cap → skipped and archived
    services.meters["inference"]._spent = 30.0
    assert request_continuation(services, fs, run_sitting=calls.run_sitting, now=_mon(11, 5)) == (False, "soft_cap")
    assert len(fs.jobs) == 1
    assert services.archive.entries[-1][1] == {"kind": "continuation_skipped", "reason": "soft_cap"}
    services.meters["inference"]._spent = 4.2

    # paused → skipped
    pause.trigger(services, "Runaway loop, condition 4.", "parent-a")
    assert request_continuation(services, fs, run_sitting=calls.run_sitting, now=_mon(11, 5)) == (False, "paused")


def test_request_continuation_without_scheduler(services):
    from agent.scheduler import request_continuation

    assert request_continuation(services, None, now=_mon(10, 30)) == (False, "no_scheduler")
    assert services.archive.entries[-1][1]["reason"] == "no_scheduler"
