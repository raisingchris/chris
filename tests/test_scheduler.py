"""Scheduler: weekday vs Sunday job sets, pause guard, next_runs."""

from datetime import date

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
    return make_services(tmp_path)


@pytest.fixture
def calls():
    return Calls()


@pytest.fixture
def sched(services, calls):
    return make_scheduler(services, calls.run_sitting, calls.run_sleep)


def test_weekday_jobs(sched):
    # 2026-09-07 is a Monday
    assert due_on(sched, date(2026, 9, 7)) == [
        "git-pull", "wake", "unseal", "sitting-09:00", "sitting-13:00", "sitting-17:00", "sleep",
    ]


def test_sunday_jobs(sched):
    # 2026-09-06 is a Sunday: no wake, no ordinary sittings — one letter home and sleep.
    assert due_on(sched, date(2026, 9, 6)) == ["git-pull", "unseal", "sunday", "sleep"]


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
