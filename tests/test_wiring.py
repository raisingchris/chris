"""wiring.build: her clock runs in cfg.tz, and CHRIS_BIRTHDAY wins over the first diary."""

from datetime import date

from agent import wiring
from agent.config import Config


def _cfg(tmp_path, **kw):
    return Config(repo_dir=str(tmp_path / "repo"), archive_dir=str(tmp_path / "archive"),
                  state_dir=str(tmp_path / "state"), tz="Europe/Lisbon", dry_run=True, **kw)


def test_odometer_clock_in_her_timezone(tmp_path):
    s = wiring.build(_cfg(tmp_path), secrets=wiring.Secrets())
    now = s.odometer._now()
    assert str(now.tzinfo) == "Europe/Lisbon"
    # an odometer claim dated today lands on the same archive day as its evidence ref
    assert s.archive.append("x", {}).startswith(f"archive:{now.strftime('%Y-%m-%d')}#")


def test_birthday_prefers_config_then_first_diary(tmp_path):
    s = wiring.build(_cfg(tmp_path), secrets=wiring.Secrets())
    (s.repo_dir / "memory" / "diary").mkdir(parents=True)
    (s.repo_dir / "memory" / "diary" / "2026-09-02.md").write_text("x\n")
    assert s.birthday() == date(2026, 9, 2)
    s2 = wiring.build(_cfg(tmp_path, birthday="2026-08-30"), secrets=wiring.Secrets())
    assert s2.birthday() == date(2026, 8, 30)
