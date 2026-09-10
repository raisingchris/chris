"""Chris's clock: APScheduler 3.x, AsyncIO, in her timezone.

Mon–Sat: wake, each sitting, sleep. Sunday: one 13:00 "sunday" sitting (the
letter home) and sleep. Every job checks the pause flag first and does nothing
while paused. Two housekeeping jobs: ``git pull --rebase`` at 06:55 so parent
commits land before she wakes, and ``council.unseal_due()`` at 07:05. A third,
``backup`` at 22:45, ships her private state off-box; it is deliberately not
``guarded`` — it runs paused or not, born or not.

Mail wakes her too: when the Resend webhook ingests a message, ``request_mail_wake``
adds a one-off ``mail`` sitting a minute out — at most one per 30 minutes and six a
day, never in sleep hours or just before a scheduled sitting (see ``mail_wake_decision``).

Continuations: when a sitting ends with work still pending in ``memory/handoff.md``,
the loop calls ``request_continuation`` and the next sitting starts
``CONTINUATION_MINUTES`` later instead of at the next clock slot — up to
``CONTINUATIONS_PER_DAY``, never in sleep hours, past the soft cap, or within 45
minutes of a scheduled sitting or sleep (see ``continuation_decision``).
"""

from __future__ import annotations

import asyncio
import json
import os
import logging
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Awaitable, Callable
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

from agent import gitops, pause

log = logging.getLogger("chris.scheduler")

JOB_DEFAULTS = {"misfire_grace_time": 600, "coalesce": True, "max_instances": 1}
WEEKDAYS = "mon-sat"
SUNDAY_SITTING = "13:00"
PULL_AT = "06:55"
UNSEAL_AT = "07:05"
BACKUP_AT = "22:45"

# Wake-on-mail limits (her timezone).
MAIL_WAKE_FILE = "mail_wake.json"
MAIL_WAKE_DELAY_S = 60
MAIL_WAKE_MIN_GAP = timedelta(minutes=30)
MAIL_WAKE_DAILY_CAP = 6
MAIL_WAKE_NEAR = timedelta(minutes=20)  # skip if a scheduled sitting/sleep is this close
MAIL_WAKE_SLEEP_FROM = time(22, 0)
MAIL_WAKE_SLEEP_TO = time(7, 0)

# Continuation sittings (her timezone).
CONTINUATION_FILE = "continuation.json"
CONTINUATION_NEAR = timedelta(minutes=45)  # skip if a scheduled sitting/sleep is this close: it will pick the work up


def _hm(s: str) -> tuple[int, int]:
    h, m = s.strip().split(":")
    return int(h), int(m)


# One sitting or sleep at a time: two sessions editing the same repo would corrupt each other.
RUN_LOCK = asyncio.Lock()


def born(services) -> bool:
    """She exists once a birth session is in the archive (or a diary exists)."""
    from agent import loop

    return not loop.is_birth(services)


def guarded(services, fn: Callable[..., Awaitable], *args, name: str = "") -> Callable[[], Awaitable[None]]:
    """Wrap a coroutine function so it is skipped while paused or while another session is still running."""

    async def run() -> None:
        job = name or getattr(fn, "__name__", "job")
        if pause.is_paused(services.cfg.state_dir):
            log.info("paused; skipping %s", job)
            return
        if job != "birth" and not born(services):
            log.info("not born yet; skipping %s", job)
            return
        if RUN_LOCK.locked():
            log.warning("another session is still running; skipping %s", job)
            services.archive.append("sitting_skipped", {"kind": "sitting_skipped", "reason": "overlap", "job": job})
            try:
                from agent import loop

                loop._note_handoff(Path(services.cfg.repo_dir),
                                   f"Your {job} was skipped: the previous session was still running.",
                                   services.archive)
            except Exception as exc:  # noqa: BLE001
                log.warning("handoff note failed: %s", exc)
            return
        async with RUN_LOCK:
            await fn(*args)

    run.__name__ = name or getattr(fn, "__name__", "job")
    return run


def git_pull(repo_dir: str | Path, run=gitops.git) -> bool:
    repo = Path(repo_dir)
    if not (repo / ".git").exists():
        return False
    try:
        r = run(repo, "pull", "--rebase", "--quiet", check=False)
    except Exception as exc:  # noqa: BLE001 — git missing, timeout
        log.warning("git pull failed: %s", exc)
        return False
    if getattr(r, "returncode", 0) != 0:
        log.warning("git pull failed: %s", str(getattr(r, "stderr", "") or "").strip())
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

    # Birth: a one-off job at BIRTH_AT (HH:MM, her timezone) on the day the service starts —
    # only if she hasn't been born. Every other job waits for it (see guarded()).
    birth_at = os.environ.get("BIRTH_AT", "").strip()
    if birth_at and not born(services):
        h, m = _hm(birth_at)
        when = datetime.now(ZoneInfo(cfg.tz)).replace(hour=h, minute=m, second=0, microsecond=0)
        if when < datetime.now(ZoneInfo(cfg.tz)):
            when += timedelta(days=1)
        sched.add_job(guarded(services, run_sitting, services, "wake", name="birth"),
                      DateTrigger(run_date=when), id="birth", name="birth", **JOB_DEFAULTS)
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

    async def backup() -> None:
        from agent import backup as backup_mod, wiring

        result = await asyncio.to_thread(backup_mod.run_backup, services)
        wiring.note_last_run(cfg.state_dir, "last_backup_done", tz=ZoneInfo(cfg.tz),
                             ok=result.get("kind") == "backup_done", kind=result.get("kind"))

    add(pull, cron(PULL_AT), "git-pull", "git pull")
    add(unseal, cron(UNSEAL_AT), "unseal", "council unseal")
    add(backup, cron(BACKUP_AT), "backup", "backup")
    return sched


# --- wake on mail --------------------------------------------------------------


def _mail_wake_path(state_dir: str | Path) -> Path:
    return Path(state_dir) / MAIL_WAKE_FILE


def read_mail_wake_state(state_dir: str | Path) -> dict:
    """``{"last": iso | None, "day": "YYYY-MM-DD", "count": n}``; empty when never fired."""
    try:
        data = json.loads(_mail_wake_path(state_dir).read_text() or "null")
    except (OSError, json.JSONDecodeError):
        data = None
    return data if isinstance(data, dict) else {}


def mail_wakes_today(state_dir: str | Path, now: datetime) -> int:
    """Extra sittings fired for mail so far today (her tz)."""
    state = read_mail_wake_state(state_dir)
    return int(state.get("count", 0)) if state.get("day") == now.date().isoformat() else 0


def _scheduled_times(cfg) -> list[time]:
    """Sittings and sleep (wake sits inside sleep hours already)."""
    out = []
    for hhmm in [*cfg.sittings, cfg.sleep]:
        try:
            h, m = _hm(hhmm)
            out.append(time(h, m))
        except ValueError:
            continue
    return out


def mail_wake_decision(now: datetime, state: dict, cfg, born: bool, paused: bool) -> tuple[bool, str]:
    """Pure: may a mail arriving at ``now`` (her tz) wake her? ``(ok, reason)``.

    ``state`` is the ``mail_wake.json`` dict. Reasons: unborn, paused, sleep_hours,
    near_scheduled, debounce, daily_cap, ok.
    """
    if not born:
        return False, "unborn"
    if paused:
        return False, "paused"
    t = now.time().replace(second=0, microsecond=0)
    if t >= MAIL_WAKE_SLEEP_FROM or t < MAIL_WAKE_SLEEP_TO:
        return False, "sleep_hours"
    for st in _scheduled_times(cfg):
        due = now.replace(hour=st.hour, minute=st.minute, second=0, microsecond=0)
        if now <= due < now + MAIL_WAKE_NEAR:
            return False, "near_scheduled"
    last = state.get("last")
    if last:
        try:
            last_dt = datetime.fromisoformat(last)
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=now.tzinfo)
            if now - last_dt < MAIL_WAKE_MIN_GAP:
                return False, "debounce"
        except ValueError:
            pass
    today = now.date().isoformat()
    count = int(state.get("count", 0)) if state.get("day") == today else 0
    if count >= MAIL_WAKE_DAILY_CAP:
        return False, "daily_cap"
    return True, "ok"


def request_mail_wake(services, sched, run_sitting=None, now: datetime | None = None) -> tuple[bool, str]:
    """Called by the Resend webhook after a successful ingest.

    If ``mail_wake_decision`` allows it, adds (or replaces) the one-off ``mail-wake``
    job ``MAIL_WAKE_DELAY_S`` out and records the fire in ``mail_wake.json``;
    otherwise archives ``mail_wake_skipped`` with the reason.
    """
    cfg = services.cfg
    tz = ZoneInfo(cfg.tz)
    now = now or datetime.now(tz)
    if now.tzinfo is None:
        now = now.replace(tzinfo=tz)
    if sched is None:
        services.archive.append("mail_wake_skipped", {"kind": "mail_wake_skipped", "reason": "no_scheduler"})
        return False, "no_scheduler"
    if run_sitting is None:
        from agent import loop

        run_sitting = loop.run_sitting
    state = read_mail_wake_state(cfg.state_dir)
    ok, reason = mail_wake_decision(now, state, cfg, born(services), pause.is_paused(cfg.state_dir))
    if not ok:
        log.info("mail wake skipped: %s", reason)
        services.archive.append("mail_wake_skipped", {"kind": "mail_wake_skipped", "reason": reason})
        return False, reason
    today = now.date().isoformat()
    count = int(state.get("count", 0)) if state.get("day") == today else 0
    path = _mail_wake_path(cfg.state_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"last": now.isoformat(timespec="seconds"), "day": today, "count": count + 1}, indent=1))
    when = now + timedelta(seconds=MAIL_WAKE_DELAY_S)
    sched.add_job(guarded(services, run_sitting, services, "mail", name="mail wake"),
                  DateTrigger(run_date=when), id="mail-wake", name="mail wake", replace_existing=True, **JOB_DEFAULTS)
    services.archive.append("mail_wake", {"kind": "mail_wake", "at": when.isoformat(timespec="seconds"),
                                          "n_today": count + 1})
    return True, "ok"


# --- continuation sittings -----------------------------------------------------


def _continuation_path(state_dir: str | Path) -> Path:
    return Path(state_dir) / CONTINUATION_FILE


def read_continuation_state(state_dir: str | Path) -> dict:
    """``{"day": "YYYY-MM-DD", "count": n}``; empty when never fired."""
    try:
        data = json.loads(_continuation_path(state_dir).read_text() or "null")
    except (OSError, json.JSONDecodeError):
        data = None
    return data if isinstance(data, dict) else {}


def continuations_today(state_dir: str | Path, now: datetime) -> int:
    """Continuation sittings scheduled so far today (her tz)."""
    state = read_continuation_state(state_dir)
    return int(state.get("count", 0)) if state.get("day") == now.date().isoformat() else 0


def continuation_decision(now: datetime, state: dict, cfg, born: bool, paused: bool,
                          spent_today: float, soft_usd: float) -> tuple[bool, str]:
    """Pure: may a sitting ending at ``now`` (her tz) with work pending be followed by another?

    ``state`` is the ``continuation.json`` dict. Reasons: unborn, paused, sleep_hours,
    soft_cap, near_scheduled, daily_cap, ok.
    """
    if not born:
        return False, "unborn"
    if paused:
        return False, "paused"
    t = now.time().replace(second=0, microsecond=0)
    if t >= MAIL_WAKE_SLEEP_FROM or t < MAIL_WAKE_SLEEP_TO:
        return False, "sleep_hours"
    if spent_today >= soft_usd:
        return False, "soft_cap"
    for st in _scheduled_times(cfg):
        due = now.replace(hour=st.hour, minute=st.minute, second=0, microsecond=0)
        if now <= due < now + CONTINUATION_NEAR:
            return False, "near_scheduled"
    today = now.date().isoformat()
    count = int(state.get("count", 0)) if state.get("day") == today else 0
    if count >= int(getattr(cfg, "continuations_per_day", 12)):
        return False, "daily_cap"
    return True, "ok"


def _spent_today(services) -> float:
    """Today's food bill from the inference meter (``services.inference`` or ``services.meters``)."""
    meter = getattr(services, "inference", None) or getattr(services, "meters", {}).get("inference")
    try:
        return float(meter.spent()) if meter is not None else 0.0
    except Exception:  # noqa: BLE001
        return 0.0


def request_continuation(services, sched, run_sitting=None, now: datetime | None = None) -> tuple[bool, str]:
    """Called by the loop when a sitting ends with work pending in the handoff.

    If ``continuation_decision`` allows it, adds (or replaces) the one-off ``continuation``
    job ``cfg.continuation_minutes`` out and counts it in ``continuation.json``;
    otherwise archives ``continuation_skipped`` with the reason.
    """
    cfg = services.cfg
    tz = ZoneInfo(cfg.tz)
    now = now or datetime.now(tz)
    if now.tzinfo is None:
        now = now.replace(tzinfo=tz)
    if sched is None:
        services.archive.append("continuation_skipped", {"kind": "continuation_skipped", "reason": "no_scheduler"})
        return False, "no_scheduler"
    if run_sitting is None:
        from agent import loop

        run_sitting = loop.run_sitting
    state = read_continuation_state(cfg.state_dir)
    ok, reason = continuation_decision(now, state, cfg, born(services), pause.is_paused(cfg.state_dir),
                                       _spent_today(services), cfg.soft_usd)
    if not ok:
        log.info("continuation skipped: %s", reason)
        services.archive.append("continuation_skipped", {"kind": "continuation_skipped", "reason": reason})
        return False, reason
    today = now.date().isoformat()
    count = int(state.get("count", 0)) if state.get("day") == today else 0
    path = _continuation_path(cfg.state_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"day": today, "count": count + 1}, indent=1))
    when = now + timedelta(minutes=int(getattr(cfg, "continuation_minutes", 30)))
    sched.add_job(guarded(services, run_sitting, services, "continue", name="continuation"),
                  DateTrigger(run_date=when), id="continuation", name="continuation", replace_existing=True,
                  **JOB_DEFAULTS)
    services.archive.append("continuation", {"kind": "continuation", "at": when.isoformat(timespec="seconds"),
                                             "n_today": count + 1})
    return True, "ok"


def next_runs(sched: AsyncIOScheduler, limit: int = 14) -> list[tuple[str, datetime]]:
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
