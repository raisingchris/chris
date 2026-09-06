"""Entry point: ``python -m agent.main``.

Builds services, starts the scheduler inside the web server's event loop, and
serves on ``PORT`` (default 8080). With ``CHRIS_RUN_ONCE=<kind>`` it runs that
one job (birth | wake | sitting | sunday | sleep) and exits — used for rehearsal.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys

SITTING_KINDS = ("birth", "wake", "sitting", "sunday")


def _setup_logging() -> None:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        stream=sys.stdout,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


async def run_once(services, kind: str) -> None:
    from agent.loop import run_sitting
    from agent.sleep import run_sleep

    if kind in SITTING_KINDS:
        await run_sitting(services, kind)
    elif kind == "sleep":
        await run_sleep(services)
    else:
        raise SystemExit(f"CHRIS_RUN_ONCE must be one of {SITTING_KINDS + ('sleep',)}, got {kind!r}")


def main() -> None:
    _setup_logging()
    log = logging.getLogger("chris.main")

    from agent import wiring
    from agent.config import cfg as load_cfg

    cfg = load_cfg()
    services = wiring.build(cfg)

    once = os.environ.get("CHRIS_RUN_ONCE", "").strip().lower()
    if once:
        log.info("running once: %s", once)
        asyncio.run(run_once(services, once))
        return

    import uvicorn

    from agent.loop import run_sitting
    from agent.scheduler import make_scheduler
    from agent.server import create_app
    from agent.sleep import run_sleep

    scheduler = make_scheduler(services, run_sitting, run_sleep)
    app = create_app(services, scheduler)  # lifespan starts/stops the scheduler
    port = int(os.environ.get("PORT", "8080"))
    log.info("serving on :%d, tz %s", port, cfg.tz)
    uvicorn.run(app, host="0.0.0.0", port=port, log_config=None, proxy_headers=True, forwarded_allow_ips="*")


if __name__ == "__main__":
    main()
