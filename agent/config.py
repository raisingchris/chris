"""Runtime configuration, read once from the environment."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

ENV_KEYS = (
    "REPO_DIR", "ARCHIVE_DIR", "STATE_DIR", "TZ", "SITTINGS", "WAKE", "SLEEP",
    "SOFT_USD", "HARD_USD", "COUNCIL_WEEKLY_USD", "PARENT_A_EMAIL", "PARENT_B_EMAIL",
    "CHRIS_EMAIL", "PARENT_HANDLES", "CHRIS_DRY_RUN", "REDACT_CANARIES", "CHRIS_MODEL",
    "STRIPE_WEBHOOK_SECRET", "CHRIS_BIRTHDAY", "MAX_TURNS", "SLEEP_MAX_TURNS", "DATAFORSEO_WEEKLY_USD",
    "X_WEEKLY_CAP", "CONTINUATION_MINUTES", "CONTINUATIONS_PER_DAY",
)

_TRUE = {"1", "true", "yes", "on"}


def _csv(value: str) -> list[str]:
    return [s.strip() for s in value.split(",") if s.strip()]


@dataclass(frozen=True)
class Config:
    repo_dir: str = "/data/repo"
    archive_dir: str = "/data/archive"
    state_dir: str = "/data/state"
    tz: str = "America/New_York"
    sittings: list[str] = field(default_factory=lambda: ["09:00", "12:00", "15:00", "18:00"])
    wake: str = "07:00"
    sleep: str = "22:00"
    soft_usd: float = 25.0
    hard_usd: float = 40.0
    council_weekly_usd: float = 10.0
    dataforseo_weekly_usd: float = 2.0
    x_weekly_cap: int = 7  # posted tweets/week through Typefully; drafts don't count
    parent_a_email: str = ""
    parent_b_email: str = ""
    chris_email: str = "chris@raisingchris.com"
    parent_handles: list[str] = field(default_factory=lambda: ["parent-a", "parent-b"])
    dry_run: bool = False
    canaries: list[str] = field(default_factory=list)
    model: str = "claude-fable-5-1"
    stripe_webhook_secret: str = ""
    birthday: str = ""  # ISO date of her first day, or empty to infer from the first diary
    max_turns: int = 150  # per sitting
    sleep_max_turns: int = 60
    continuation_minutes: int = 30  # a sitting that ends with work pending is followed by another this soon
    continuations_per_day: int = 12

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "Config":
        e = os.environ if env is None else env
        g = lambda k, d="": e.get(k, d)  # noqa: E731
        return cls(
            repo_dir=g("REPO_DIR", "/data/repo"),
            archive_dir=g("ARCHIVE_DIR", "/data/archive"),
            state_dir=g("STATE_DIR", "/data/state"),
            tz=g("TZ", "America/New_York"),
            sittings=_csv(g("SITTINGS", "09:00,12:00,15:00,18:00")),
            wake=g("WAKE", "07:00"),
            sleep=g("SLEEP", "22:00"),
            soft_usd=float(g("SOFT_USD", "25")),
            hard_usd=float(g("HARD_USD", "40")),
            council_weekly_usd=float(g("COUNCIL_WEEKLY_USD", "10")),
            dataforseo_weekly_usd=float(g("DATAFORSEO_WEEKLY_USD", "2")),
            x_weekly_cap=int(g("X_WEEKLY_CAP", "7")),
            parent_a_email=g("PARENT_A_EMAIL"),
            parent_b_email=g("PARENT_B_EMAIL"),
            chris_email=g("CHRIS_EMAIL", "chris@raisingchris.com"),
            parent_handles=_csv(g("PARENT_HANDLES", "parent-a,parent-b")),
            dry_run=g("CHRIS_DRY_RUN").strip().lower() in _TRUE,
            canaries=_csv(g("REDACT_CANARIES")),
            model=g("CHRIS_MODEL", "claude-fable-5-1"),
            stripe_webhook_secret=g("STRIPE_WEBHOOK_SECRET"),
            birthday=g("CHRIS_BIRTHDAY").strip(),
            max_turns=int(g("MAX_TURNS", "150")),
            sleep_max_turns=int(g("SLEEP_MAX_TURNS", "60")),
            continuation_minutes=int(g("CONTINUATION_MINUTES", "30")),
            continuations_per_day=int(g("CONTINUATIONS_PER_DAY", "12")),
        )


_cached: Config | None = None


def cfg() -> Config:
    """Process-wide config, built from the environment on first use."""
    global _cached
    if _cached is None:
        _cached = Config.from_env()
    return _cached


def reset() -> None:
    """Drop the cached config (tests)."""
    global _cached
    _cached = None
