"""Chris's clock: APScheduler 3.x, AsyncIO, in her timezone.

Mon–Sat: wake, each sitting, sleep. Sunday: one 13:00 "sunday" sitting (the
letter home) and sleep. Every job checks the pause flag first and does nothing
while paused. Two housekeeping jobs: ``git pull --rebase`` at 06:55 so parent
commits land before she wakes, and ``council.unseal_due()`` at 07:05.
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Awaitable, Callable
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from agent import pause

log = logging.getLogger("chris.scheduler")

JOB_DEFAULTS = {"misfire_grace_time": 600, "coalesce": True, "max_instances": 1}
WEEKDAYS = "mon-sat"
SUNDAY_SITTING = "13:00"
PULL_AT = "06:55"
UNSEAL_AT = "07:05"


def _hm(s: str) -> tuple[int, int]:
    h, m = s.strip().split(":")
    return int(h), int(m)


def guarded(services, fn: Callable[..., Awaitable], *args, name: str = "") -> Callable[[], Awaitable[None]]:
    """Wrap a coroutine function so it is skipped while paused."""

    async def run() -> None:
        if pause.is_paused(services.cfg.state_dir):
            log.info("paused; skipping %s", name or getattr(fn, "__name__", "job"))
            return
        await fn(*args)

    run.__name__ = name or getattr(fn, "__name__", "job")
    return run


def git_pull(repo_dir: str | Path) -> bool:
    repo = Path(repo_dir)
    if not (repo / ".git").exists():
        return False
    r = subprocess.run(["git", "pull", "--rebase", "--quiet"], cwd=repo, capture_output=True)
    if r.returncode != 0:
        log.warning("git pull failed: %s", r.stderr.decode(errors="replace").strip())
        return False
    return True


def make_scheduler(services, run_sitting, run_sleep) -> AsyncIOScheduler:
    cfg = services.cfg
    sched = AsyncIOScheduler(timezone=cfg.tz, job_defaults=JOB_DEFAULTS)

    def cron(hhmm: str, dow: str = "*") -> CronTrigger:
        h, m = _hm(hhmm)
        return CronTrigger(day_of_week=dow, hour=h, minute=m, timezone=cfg.tz)

    def add(fn, trigger: CronTrigger, id: str, name: str) -> None:
        sched.add_job(fn, trigger, id=id, name=name, **JOB_DEFAULTS)

    add(guarded(services, run_sitting, services, "wake", name="wake"), cron(cfg.wake, WEEKDAYS), "wake", "wake")
    for t in cfg.sittings:
        add(guarded(services, run_sitting, services, "sitting", name=f"sitting {t}"),
            cron(t, WEEKDAYS), f"sitting-{t}", f"sitting {t}")
    add(guarded(services, run_sitting, services, "sunday", name="sunday"),
        cron(SUNDAY_SITTING, "sun"), "sunday", "sunday letter")
    add(guarded(services, run_sleep, services, name="sleep"), cron(cfg.sleep), "sleep", "sleep")

    async def pull() -> None:
        await asyncio.to_thread(git_pull, cfg.repo_dir)

    async def unseal() -> None:
        copied = await asyncio.to_thread(services.council.unseal_due)
        if copied:
            log.info("unsealed %d council minute(s)", len(copied))

    add(pull, cron(PULL_AT), "git-pull", "git pull")
    add(unseal, cron(UNSEAL_AT), "unseal", "council unseal")
    return sched


def next_runs(sched: AsyncIOScheduler, limit: int = 8) -> list[tuple[str, datetime]]:
    """(job name, next fire time) soonest first — works before the scheduler starts too."""
    now = datetime.now(sched.timezone)
    out = []
    for job in sched.get_jobs():
        t = getattr(job, "next_run_time", None) or job.trigger.get_next_fire_time(None, now)
        if t:
            out.append((job.name, t))
    out.sort(key=lambda x: x[1])
    return out[:limit]


def due_on(sched: AsyncIOScheduler, day: date) -> list[str]:
    """Job ids that fire on a given calendar day, in time order."""
    tz = ZoneInfo(str(sched.timezone))
    start = datetime.combine(day, time.min, tzinfo=tz)
    end = start + timedelta(days=1)
    hits = []
    for job in sched.get_jobs():
        t = job.trigger.get_next_fire_time(None, start)
        if t and t < end:
            hits.append((t, job.id))
    return [jid for _, jid in sorted(hits)]
