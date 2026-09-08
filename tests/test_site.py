"""The public site: builds from the real repo, discloses on every page, leaks nothing."""

import importlib.util
import os
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
    """The built site carries none of the forbidden fragments.

    The real list never lives in the repo: the parents run this locally with
    ``IDENTITY_FORBIDDEN="Name,City,..."`` (see tests/test_no_identity_strings.py).
    """
    forbidden = [s.strip() for s in os.environ.get("IDENTITY_FORBIDDEN", "").split(",") if s.strip()]
    if not forbidden:
        pytest.skip("IDENTITY_FORBIDDEN not set")
    for p in out.rglob("*"):
        if p.is_file():
            text = p.read_text(errors="ignore").lower()
            for i, canary in enumerate(forbidden):
                assert canary.lower() not in text, f"forbidden fragment #{i} in {p}"


def test_council_shows_empty_chair(out: Path):
    html = (out / "council" / "index.html").read_text()
    assert "Third chair — empty on purpose" in html
    assert "OpenAI seat" in html


def test_llms_txt_shape(out: Path):
    text = (out / "llms.txt").read_text()
    assert text.startswith("# Chris\n")
    assert text.splitlines()[2].startswith("> ")
    assert "## Soul" in text and "raisingchris.com/raw/soul/letter.md" in text


def test_feed(out: Path):
    """The diary is an Atom feed: well-formed XML, one entry per human diary day, newest first, full text."""
    import xml.etree.ElementTree as ET

    root = ET.parse(out / "feed.xml").getroot()
    ns = {"a": "http://www.w3.org/2005/Atom"}
    assert root.tag == "{http://www.w3.org/2005/Atom}feed"
    assert root.find("a:link[@rel='self']", ns).get("href") == "https://raisingchris.com/feed.xml"
    entries = root.findall("a:entry", ns)
    human_days = sorted(p.stem for p in (REPO / "memory" / "diary").glob("*.md") if not p.name.endswith(".agent.md"))
    assert [e.find("a:id", ns).text for e in entries] == [f"https://raisingchris.com/diary/{d}/" for d in reversed(human_days)][:30]
    first = entries[0]
    assert first.find("a:content", ns).get("type") == "html"
    assert "<p>" in first.find("a:content", ns).text
    assert first.find("a:published", ns).text.endswith(("-04:00", "-05:00"))  # New York
    html = (out / "index.html").read_text()
    assert 'type="application/atom+xml" href="/feed.xml"' in html


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
