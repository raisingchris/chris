import dataclasses

import pytest

from agent import config


@pytest.fixture(autouse=True)
def _reset():
    config.reset()
    yield
    config.reset()


def test_defaults(monkeypatch):
    for k in list(config.ENV_KEYS):
        monkeypatch.delenv(k, raising=False)
    c = config.Config.from_env()
    assert c.repo_dir == "/data/repo"
    assert c.archive_dir == "/data/archive"
    assert c.state_dir == "/data/state"
    assert c.tz == "America/New_York"
    assert c.sittings == ["09:00", "12:00", "15:00", "18:00"]
    assert c.wake == "07:00"
    assert c.sleep == "22:00"
    assert c.soft_usd == 25.0
    assert c.hard_usd == 40.0
    assert c.council_weekly_usd == 10.0
    assert c.chris_email == "chris@raisingchris.com"
    assert c.parent_handles == ["parent-a", "parent-b"]
    assert c.parent_a_email == ""
    assert c.parent_b_email == ""
    assert c.dry_run is False
    assert c.canaries == []
    assert c.model == "claude-fable-5-1"


def test_from_env_overrides(monkeypatch):
    monkeypatch.setenv("REPO_DIR", "/tmp/repo")
    monkeypatch.setenv("ARCHIVE_DIR", "/tmp/archive")
    monkeypatch.setenv("STATE_DIR", "/tmp/state")
    monkeypatch.setenv("TZ", "Europe/Lisbon")
    monkeypatch.setenv("SITTINGS", "10:00, 15:00")
    monkeypatch.setenv("SOFT_USD", "1.5")
    monkeypatch.setenv("HARD_USD", "2")
    monkeypatch.setenv("COUNCIL_WEEKLY_USD", "3")
    monkeypatch.setenv("PARENT_A_EMAIL", "a@example.com")
    monkeypatch.setenv("PARENT_B_EMAIL", "b@example.com")
    monkeypatch.setenv("CHRIS_DRY_RUN", "1")
    monkeypatch.setenv("REDACT_CANARIES", "Alice, Bob,, secret corp")
    monkeypatch.setenv("CHRIS_MODEL", "claude-x")
    c = config.Config.from_env()
    assert c.repo_dir == "/tmp/repo"
    assert c.archive_dir == "/tmp/archive"
    assert c.state_dir == "/tmp/state"
    assert c.tz == "Europe/Lisbon"
    assert c.sittings == ["10:00", "15:00"]
    assert c.soft_usd == 1.5 and c.hard_usd == 2.0 and c.council_weekly_usd == 3.0
    assert c.parent_a_email == "a@example.com"
    assert c.parent_b_email == "b@example.com"
    assert c.dry_run is True
    assert c.canaries == ["Alice", "Bob", "secret corp"]
    assert c.model == "claude-x"


@pytest.mark.parametrize("val,expected", [("0", False), ("false", False), ("", False), ("true", True), ("yes", True)])
def test_dry_run_parsing(monkeypatch, val, expected):
    monkeypatch.setenv("CHRIS_DRY_RUN", val)
    assert config.Config.from_env().dry_run is expected


def test_frozen(monkeypatch):
    c = config.Config.from_env()
    with pytest.raises(dataclasses.FrozenInstanceError):
        c.tz = "UTC"


def test_cfg_cached_and_reset(monkeypatch):
    monkeypatch.setenv("TZ", "UTC")
    a = config.cfg()
    assert a.tz == "UTC"
    monkeypatch.setenv("TZ", "Europe/London")
    assert config.cfg() is a  # cached
    config.reset()
    assert config.cfg().tz == "Europe/London"


def test_stripe_webhook_secret_and_birthday(monkeypatch):
    for k in ("STRIPE_WEBHOOK_SECRET", "CHRIS_BIRTHDAY"):
        assert k in config.ENV_KEYS
        monkeypatch.delenv(k, raising=False)
    c = config.Config.from_env()
    assert c.stripe_webhook_secret == "" and c.birthday == ""
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_x")
    monkeypatch.setenv("CHRIS_BIRTHDAY", " 2026-09-10 ")
    c = config.Config.from_env()
    assert c.stripe_webhook_secret == "whsec_x" and c.birthday == "2026-09-10"
