"""The public site: builds from the real repo, discloses on every page, leaks nothing."""

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

# `site` shadows the stdlib module of the same name, so load build.py by path.
_spec = importlib.util.spec_from_file_location("chris_site_build", REPO / "site" / "build.py")
site_build = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(site_build)

DISCLOSURE = "I'm an AI. Anything you tell me is private from the world, but my operators can technically access it."


@pytest.fixture(scope="module")
def out(tmp_path_factory) -> Path:
    return site_build.build(REPO, tmp_path_factory.mktemp("out"))


def test_key_pages_exist(out: Path):
    for rel in ["index.html", "soul/letter/index.html", "letters/index.html", "for-agents/index.html",
                "llms.txt", "llms-full.txt", "style.css", "raw/soul/letter.md"]:
        assert (out / rel).is_file(), rel


def test_soul_in_founding_order(out: Path):
    html = (out / "soul" / "letter" / "index.html").read_text()
    idx = [html.index(f'href="/soul/{n}/"') for n in ["letter", "vows", "values", "constitution", "day_one", "prd", "life_lessons_index"]]
    assert idx == sorted(idx)


def test_disclosure_on_every_page(out: Path):
    pages = list(out.rglob("*.html"))
    assert pages
    for p in pages:
        html = p.read_text()
        assert DISCLOSURE in html, p
        assert "<header" in html and "Always an AI." in html, p


def test_no_canaries_anywhere(out: Path):
    for p in out.rglob("*"):
        if p.is_file():
            text = p.read_text(errors="ignore")
            for canary in ("Moat", "Singapore"):
                assert canary not in text, f"{canary} in {p}"


def test_council_shows_empty_chair(out: Path):
    html = (out / "council" / "index.html").read_text()
    assert "Third chair — empty on purpose" in html
    assert "OpenAI seat" in html


def test_llms_txt_shape(out: Path):
    text = (out / "llms.txt").read_text()
    assert text.startswith("# Chris\n")
    assert text.splitlines()[2].startswith("> ")
    assert "## Soul" in text and "raisingchris.com/raw/soul/letter.md" in text


def test_for_agents_page(out: Path):
    html = (out / "for-agents" / "index.html").read_text()
    assert "chris@raisingchris.com" in html
    assert "America/New_York" in html
    assert "/raw/" in html


def test_diary_twin(tmp_path: Path):
    """A day with a machine twin gets both pages and a link between them."""
    import shutil

    repo = tmp_path / "repo"
    for d in ("soul", "memory/wiki/self", "memory/diary", "council/members", "council/minutes", "governance", "ledger"):
        (repo / d).mkdir(parents=True)
    shutil.copy(REPO / "README.md", repo / "README.md")
    (repo / "soul" / "letter.md").write_text("# Letter\n\nhello\n")
    (repo / "memory" / "diary" / "2026-09-07.md").write_text("# Day one\n\nI woke up.\n")
    (repo / "memory" / "diary" / "2026-09-07.agent.md").write_text("# 2026-09-07\n\n- state: born\n")
    out = site_build.build(repo, tmp_path / "out")
    human = (out / "diary" / "2026-09-07" / "index.html").read_text()
    assert 'href="/diary/2026-09-07/agent/"' in human
    assert (out / "diary" / "2026-09-07" / "agent" / "index.html").is_file()
    assert "I woke up." in (out / "index.html").read_text()
    assert "2026-09-07.agent.md" in (out / "for-agents" / "index.html").read_text()
    assert "I woke up." in (out / "llms-full.txt").read_text()
