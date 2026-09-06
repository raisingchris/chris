"""Build every service Chris's loop needs from one Config.

This is the only module that knows the environment: which env var holds which
key, where private state lives, and whether we are in dry-run. Nothing here
touches the network at construction time, so ``build()`` is safe in tests and
rehearsals.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable

from agent.archive import Archive
from agent.budget import Meter
from agent.config import Config
from agent.council import Council
from agent.mail import Mail


@dataclass
class Secrets:
    """API keys, read from the environment; never from any file in the repo."""

    anthropic_key: str = ""
    resend_key: str = ""
    openai_key: str = ""
    qwen_key: str = ""
    qwen_base_url: str = ""
    airwallex_client_id: str = ""
    airwallex_api_key: str = ""
    airwallex_base_url: str = "https://api.airwallex.com"
    airwallex_cardholder_id: str = ""
    card_id: str = ""
    stripe_key: str = ""

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "Secrets":
        e = os.environ if env is None else env
        return cls(
            anthropic_key=e.get("ANTHROPIC_API_KEY", ""),
            resend_key=e.get("RESEND_API_KEY", ""),
            openai_key=e.get("OPENAI_API_KEY", ""),
            qwen_key=e.get("QWEN_API_KEY", ""),
            qwen_base_url=e.get("QWEN_BASE_URL", ""),
            airwallex_client_id=e.get("AIRWALLEX_CLIENT_ID", ""),
            airwallex_api_key=e.get("AIRWALLEX_API_KEY", ""),
            airwallex_base_url=e.get("AIRWALLEX_BASE_URL", "https://api.airwallex.com"),
            airwallex_cardholder_id=e.get("AIRWALLEX_CARDHOLDER_ID", ""),
            card_id=e.get("CHRIS_CARD_ID", ""),
            stripe_key=e.get("STRIPE_CHRIS_SECRET_KEY", ""),
        )


@dataclass
class Services:
    cfg: Config
    secrets: Secrets
    archive: Archive
    inference: Meter  # daily food bill
    council_meter: Meter  # weekly council spend
    mail: Mail
    council: Council
    ledger: Any
    card: Any
    payments: Any
    odometer: Any
    repo_dir: Path = field(init=False)
    state_dir: Path = field(init=False)

    def __post_init__(self) -> None:
        self.repo_dir = Path(self.cfg.repo_dir)
        self.state_dir = Path(self.cfg.state_dir)

    @property
    def meters(self) -> dict[str, Meter]:
        """Both meters by name (server.py reads this shape)."""
        return {"inference": self.inference, "council": self.council_meter}

    def birthday(self) -> date:
        """Day of the first diary entry; today if she has not been born yet."""
        diaries = sorted((self.repo_dir / "memory" / "diary").glob("????-??-??.md"))
        if diaries:
            return date.fromisoformat(diaries[0].stem)
        return datetime.now(self.archive.tz).date()

    def meters_line(self) -> str:
        cfg = self.cfg
        parts = [
            f"Food bill today: ${self.inference.spent():.2f} of ${cfg.soft_usd:.0f} soft / ${cfg.hard_usd:.0f} hard.",
            f"Council this week: ${self.council_meter.spent():.2f} of ${cfg.council_weekly_usd:.0f}.",
        ]
        try:
            parts.append(f"Ledger balance: ${self.ledger.balance():.2f} USD.")
        except Exception as exc:  # money modules may be unconfigured in dry-run
            parts.append(f"Ledger balance: unavailable ({type(exc).__name__}).")
        try:
            parts.append(self.odometer.render_line(self.birthday()))
        except Exception as exc:
            parts.append(f"Odometer: unavailable ({type(exc).__name__}).")
        return " ".join(parts)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def build(cfg: Config, secrets: Secrets | None = None, env: dict[str, str] | None = None) -> Services:
    secrets = secrets or Secrets.from_env(env)
    archive = Archive(cfg.archive_dir, tz=cfg.tz)
    inference = Meter("inference", "day", cfg.state_dir, tz=cfg.tz)
    council_meter = Meter("council", "week", cfg.state_dir, tz=cfg.tz)

    handles = list(cfg.parent_handles) + ["parent-a", "parent-b"][len(cfg.parent_handles):]
    parents = {handles[0]: cfg.parent_a_email, handles[1]: cfg.parent_b_email}

    mail = Mail(
        repo_dir=Path(cfg.repo_dir),
        archive_append=archive.append,
        parents=parents,
        chris_email=cfg.chris_email,
        resend_api_key=secrets.resend_key,
        dry_run=cfg.dry_run,
    )
    # Private minutes sit next to the other private state, never in the repo.
    minutes_dir = Path(os.environ.get("COUNCIL_MINUTES_DIR") or Path(cfg.state_dir).parent / "council_minutes")
    council = Council(
        repo_dir=Path(cfg.repo_dir),
        minutes_dir=minutes_dir,
        archive_append=archive.append,
        meter=council_meter,
        weekly_cap_usd=cfg.council_weekly_usd,
        openai_api_key=secrets.openai_key,
        qwen_api_key=secrets.qwen_key,
        qwen_base_url=secrets.qwen_base_url,
    )

    # Money modules are imported lazily so the loop still builds if one is
    # missing or mid-rewrite; each one is optional in dry-run.
    from agent.ledger import Ledger

    ledger = Ledger(cfg.repo_dir)

    from agent.card import Card

    card = Card(
        client_id=secrets.airwallex_client_id,
        api_key=secrets.airwallex_api_key,
        base_url=secrets.airwallex_base_url,
        card_id=secrets.card_id or None,
        cardholder_id=secrets.airwallex_cardholder_id,
        archive_append=archive.append,
    )

    from agent.payments import Payments

    payments = Payments(secrets.stripe_key, archive.append, ledger)

    from agent.odometer import Odometer

    odometer = Odometer(cfg.repo_dir, cfg.state_dir, archive.append, _now_utc)

    return Services(
        cfg=cfg,
        secrets=secrets,
        archive=archive,
        inference=inference,
        council_meter=council_meter,
        mail=mail,
        council=council,
        ledger=ledger,
        card=card,
        payments=payments,
        odometer=odometer,
    )
