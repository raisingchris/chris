"""Build every service Chris's loop needs from one Config.

This is the only module that knows the environment: which env var holds which
key, where private state lives, and whether we are in dry-run. Nothing here
touches the network at construction time, so ``build()`` is safe in tests and
rehearsals.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from agent.archive import Archive
from agent.budget import Meter
from agent.config import Config
from agent.council import Council
from agent.analytics import Analytics
from agent.dataforseo import DataForSEO
from agent.google_auth import GoogleWIF
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
    dataforseo_auth_b64: str = ""  # parent-identifying; never reaches her shell or the archive
    # Google, keyless: the WIF provider resource and service-account address name her parents'
    # project, so they stay here. Property/site ids are what the tools read.
    google_wif_provider: str = ""
    google_metrics_sa: str = ""
    ga4_property_id: str = ""
    gsc_site_url: str = ""

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
            dataforseo_auth_b64=e.get("DATAFORSEO_AUTH_B64", ""),
            google_wif_provider=e.get("GOOGLE_WIF_PROVIDER", ""),
            google_metrics_sa=e.get("GOOGLE_METRICS_SA", ""),
            ga4_property_id=e.get("GA4_PROPERTY_ID", ""),
            gsc_site_url=e.get("GSC_SITE_URL", ""),
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
    dataforseo_meter: Meter | None = None  # weekly DataForSEO spend
    dataforseo: Any = None  # DataForSEO proxy, or None when no credential is configured
    google: Any = None  # GoogleWIF, or None when the provider/SA are not configured
    ga4_property: str = ""
    gsc_site: str = ""
    analytics: Any = None  # Analytics (GA4 + Search Console), or None
    scheduler: Any = None  # set by main.py once the clock exists; the loop uses it for continuation sittings
    repo_dir: Path = field(init=False)
    state_dir: Path = field(init=False)

    def __post_init__(self) -> None:
        self.repo_dir = Path(self.cfg.repo_dir)
        self.state_dir = Path(self.cfg.state_dir)

    @property
    def meters(self) -> dict[str, Meter]:
        """Meters by name (server.py reads this shape)."""
        m = {"inference": self.inference, "council": self.council_meter}
        if self.dataforseo_meter is not None:
            m["dataforseo"] = self.dataforseo_meter
        return m

    def birthday(self) -> date:
        """CHRIS_BIRTHDAY if set; else the first diary entry's day; else today."""
        if self.cfg.birthday:
            return date.fromisoformat(self.cfg.birthday)
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
        line = " ".join(parts)
        if self.dataforseo is not None and self.dataforseo_meter is not None:
            line += (f" · DataForSEO this week ${self.dataforseo_meter.spent():.2f} "
                     f"of ${cfg.dataforseo_weekly_usd:.2f}")
        from agent import gitops

        n = gitops.unpushed_count(self.repo_dir)
        if n > 0:
            line += f" · {n} commits unpushed"
        blocked = gitops.push_blocked_reason(self.state_dir)
        if blocked:
            line += f" · push blocked: {blocked}"
        # Her code changes run only after a parent deploys; say so when the two differ.
        running, head = gitops.running_sha(), gitops.head_sha(self.repo_dir)
        if running and head and running != head:
            line += f" · running code {running[:7]}; repo HEAD {head[:7]} (not deployed yet)"
        from agent import tickets

        n = len(tickets.list_tickets(self.repo_dir, "open"))
        if n > 0:
            line += f" · {n} open tickets"
        from agent.scheduler import continuations_today

        n = continuations_today(self.state_dir, datetime.now(self.archive.tz))
        if n > 0:
            line += f" · {n} continuations today"
        return line



LAST_RUNS = "last_runs.json"


def note_last_run(state_dir: str | Path, key: str, tz: ZoneInfo | None = None, **extra) -> None:
    """Record ``<key>: <now iso>`` (plus extras) in ``<state_dir>/last_runs.json``; never raises."""
    import json

    path = Path(state_dir) / LAST_RUNS
    try:
        data = json.loads(path.read_text()) if path.exists() else {}
    except Exception:  # noqa: BLE001
        data = {}
    data[key] = datetime.now(tz).isoformat(timespec="seconds")
    for k, v in extra.items():
        data[f"{key}_{k}"] = v
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=1))
    except OSError:
        pass


def read_last_runs(state_dir: str | Path) -> dict:
    import json

    try:
        return json.loads((Path(state_dir) / LAST_RUNS).read_text())
    except Exception:  # noqa: BLE001
        return {}


def build(cfg: Config, secrets: Secrets | None = None, env: dict[str, str] | None = None) -> Services:
    secrets = secrets or Secrets.from_env(env)
    archive = Archive(cfg.archive_dir, tz=cfg.tz)
    inference = Meter("inference", "day", cfg.state_dir, tz=cfg.tz)
    council_meter = Meter("council", "week", cfg.state_dir, tz=cfg.tz)
    dataforseo_meter = Meter("dataforseo", "week", cfg.state_dir, tz=cfg.tz)

    handles = list(cfg.parent_handles) + ["parent-a", "parent-b"][len(cfg.parent_handles):]
    parents = {handles[0]: cfg.parent_a_email, handles[1]: cfg.parent_b_email}

    mail = Mail(
        repo_dir=Path(cfg.repo_dir),
        archive_append=archive.append,
        parents=parents,
        chris_email=cfg.chris_email,
        resend_api_key=secrets.resend_key,
        dry_run=cfg.dry_run,
        canaries=cfg.canaries,
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
        anthropic_api_key=secrets.anthropic_key,
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

    # Her clock, not UTC: odometer claims and archive refs must share a date.
    tz = ZoneInfo(cfg.tz)
    odometer = Odometer(cfg.repo_dir, cfg.state_dir, archive.append, lambda: datetime.now(tz))

    dataforseo = None
    if secrets.dataforseo_auth_b64:
        dataforseo = DataForSEO(secrets.dataforseo_auth_b64, dataforseo_meter, cfg.dataforseo_weekly_usd,
                                archive.append)

    google = analytics = None
    if secrets.google_wif_provider and secrets.google_metrics_sa:
        google = GoogleWIF(secrets.google_wif_provider, secrets.google_metrics_sa)
        analytics = Analytics(google, secrets.ga4_property_id, secrets.gsc_site_url, archive.append)

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
        dataforseo_meter=dataforseo_meter,
        dataforseo=dataforseo,
        google=google,
        ga4_property=secrets.ga4_property_id,
        gsc_site=secrets.gsc_site_url,
        analytics=analytics,
    )
