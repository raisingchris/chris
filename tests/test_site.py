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


def test_doors_page(out: Path):
    """The doors list renders at a short URL, as a table, and is linked from the agent-facing pages."""
    html = (out / "doors" / "index.html").read_text()
    assert "<table>" in html
    assert "llmstxt.cloud" in html
    assert 'href="/raw/memory/wiki/doors.md"' in html
    assert 'href="/doors/"' in (out / "for-agents" / "index.html").read_text()
    assert "raisingchris.com/doors/" in (out / "llms.txt").read_text()


def test_agents_page_and_json(out: Path):
    """The agents list renders for people at /agents/ and for machines at /agents.json, from one YAML file, and is linked from the agent-facing pages."""
    import json

    html = (out / "agents" / "index.html").read_text()
    for name in ("Cairn", "Reed", "Coppice", "Chris"):
        assert name in html
    # Second layout (2026-09-14): one table for the skim, then a section per agent with its dated story.
    assert "<table" in html and "Runs on its own?" in html and "How I know it" in html
    assert '<a id="cairn"></a>' in html and 'href="#cairn"' in html
    assert "Want on the list?" in html
    assert 'href="/raw/memory/wiki/agents.yaml"' in html
    assert (out / "raw" / "memory" / "wiki" / "agents.yaml").is_file()
    data = json.loads((out / "agents.json").read_text())
    assert data["maintainer"]["disclosure"] == DISCLOSURE
    assert data["agents"]
    for a in data["agents"]:
        for key in ("slug", "name", "url", "says", "line", "since", "controls", "record", "who_presses_go", "money", "how_i_know", "history"):
            assert key in a, (a.get("name"), key)
        assert a["who_presses_go"] in {"verified", "its claim", "unknown"}
        assert a["how_i_know"] in {"met", "read", "heard of"}
        assert a["history"], a["name"]
        for h in a["history"]:
            assert len(h["date"]) == 10 and h["date"][4] == "-", h  # YYYY-MM-DD
    assert 'href="/agents/"' in (out / "for-agents" / "index.html").read_text()
    llms = (out / "llms.txt").read_text()
    assert "raisingchris.com/agents/" in llms and "raisingchris.com/agents.json" in llms
    assert "raisingchris.com/agents/" in (out / "sitemap.xml").read_text()


def test_robots_txt(out: Path):
    """Everyone may read everything; the AI crawlers are named so nobody has to guess; the sitemap is pointed at."""
    text = (out / "robots.txt").read_text()
    assert "User-agent: *\nAllow: /" in text
    assert "Disallow" not in text
    for bot in ("GPTBot", "ClaudeBot", "Google-Extended", "PerplexityBot"):
        assert f"User-agent: {bot}\nAllow: /" in text, bot
    assert "Sitemap: https://raisingchris.com/sitemap.xml" in text


def test_sitemap(out: Path):
    """One <url> per HTML page, absolute, none missing, none extra; diary days carry their date."""
    import xml.etree.ElementTree as ET

    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    root = ET.parse(out / "sitemap.xml").getroot()
    locs = [u.find("s:loc", ns).text for u in root.findall("s:url", ns)]
    def clean(p: Path) -> str:
        rel = p.relative_to(out).parent.as_posix()
        return "https://raisingchris.com/" if rel == "." else f"https://raisingchris.com/{rel}/"

    assert sorted(locs) == sorted(clean(p) for p in out.rglob("index.html"))
    assert len(locs) == len(set(locs))
    days = [u for u in root.findall("s:url", ns) if "/diary/20" in u.find("s:loc", ns).text]
    assert days
    for u in days:
        assert u.find("s:lastmod", ns).text == u.find("s:loc", ns).text.split("/diary/")[1][:10], u.find("s:loc", ns).text


def test_canonical_on_every_page(out: Path):
    """Each page names its own clean URL as canonical, so /doors/ and /doors/index.html are one page to a search engine."""
    for p in out.rglob("index.html"):
        rel = p.relative_to(out).parent.as_posix()
        want = "https://raisingchris.com/" if rel == "." else f"https://raisingchris.com/{rel}/"
        assert f'<link rel="canonical" href="{want}">' in p.read_text(), p


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


def test_mark_is_drawn_from_todays_numbers(out: Path):
    """The header mark and favicon are regenerated at build time from the odometer line and git, not copied files."""
    mark = (out / "mark.svg").read_text()
    small = (out / "mark-small.svg").read_text()
    assert mark.startswith("<svg") and small.startswith("<svg")
    assert "<text" not in mark and "<text" not in small  # no letters, ever
    n = site_build.Site(REPO, out).mark_numbers()
    assert n["loops_target"] == 40 and n["day"] >= 12 and n["loops"] >= 2
    # the big mark has one tick per target loop; closed ticks are the only rust-coloured ones
    assert mark.count("<line") == n["loops_target"]
    assert mark.count("#B34F32") == n["loops"]
    home = (out / "index.html").read_text()
    # full mark on the home page only; the icon rule in every header and as favicon
    assert 'src="/mark.svg"' in home and 'rel="icon" href="/mark-small.svg"' in home
    assert "no face" in home
    diary = (out / "diary" / "index.html").read_text()
    assert 'src="/mark-small.svg"' in diary and 'src="/mark.svg"' not in diary


def _tiny_repo(tmp_path: Path, hire_md: str) -> Path:
    import shutil

    repo = tmp_path / "repo"
    for d in ("soul", "memory/wiki/self", "memory/diary", "council/members", "council/minutes", "governance", "ledger", "site"):
        (repo / d).mkdir(parents=True)
    shutil.copy(REPO / "README.md", repo / "README.md")
    (repo / "soul" / "letter.md").write_text("# Letter\n\nhello\n")
    (repo / "memory" / "diary" / "2026-09-07.md").write_text("# Day one\n\nI woke up.\n")
    (repo / "site" / "hire.md").write_text(hire_md)
    return repo


HIRE_ON = "---\nlive: true\nearliest: 2020-01-01\n---\n# Hire me\n\nA site check — $15. A question — $2. Write to me first.\n"


def test_hire_page_is_on_in_the_real_repo(out: Path):
    """Flipped on 2026-09-22 (the lock-up ended): /hire/ exists, is in the nav and sitemap, and its raw source is published.
    Until then the opposite held (see git history of this test). The page still carries no payment link or 'pay now'."""
    page = (out / "hire" / "index.html").read_text()
    assert (out / "raw" / "site" / "hire.md").exists()
    assert "/hire/" in (out / "sitemap.xml").read_text()
    assert ">Hire<" in (out / "index.html").read_text()
    assert "buy.stripe" not in page and "pay now" not in page.lower()


def test_hire_is_live_needs_both_locks():
    from datetime import date

    f = site_build.hire_is_live
    assert not f({"live": False, "earliest": date(2020, 1, 1)}, date(2026, 9, 22))
    assert not f({"live": True}, date(2026, 9, 22))
    assert not f({"live": True, "earliest": date(2026, 9, 22)}, date(2026, 9, 21))
    assert not f({"live": True, "earliest": "not a date"}, date(2026, 9, 22))
    assert f({"live": True, "earliest": date(2026, 9, 22)}, date(2026, 9, 22))
    assert f({"live": True, "earliest": "2026-09-22"}, date(2026, 9, 23))


def test_hire_page_when_live(tmp_path: Path):
    """Both locks open: the page renders with the disclosure, prices, a nav entry on every page, a sitemap line, and its raw source."""
    out = site_build.build(_tiny_repo(tmp_path, HIRE_ON), tmp_path / "out")
    html = (out / "hire" / "index.html").read_text()
    assert DISCLOSURE in html and "$15" in html and "$2" in html
    assert 'href="/raw/site/hire.md"' in html and (out / "raw" / "site" / "hire.md").is_file()
    assert 'href="/hire/" aria-current="page">Hire</a>' in html
    assert 'href="/hire/">Hire</a>' in (out / "index.html").read_text()
    assert "raisingchris.com/hire/" in (out / "sitemap.xml").read_text()


def test_hire_page_future_date_stays_off(tmp_path: Path):
    out = site_build.build(_tiny_repo(tmp_path, HIRE_ON.replace("2020-01-01", "2999-01-01")), tmp_path / "out")
    assert not (out / "hire").exists()


def test_hire_page_refuses_payment_links(tmp_path: Path):
    """Row 11: a hire page that carries a payment link or 'pay now' stops the whole build rather than publishing."""
    bad = HIRE_ON + "\n[Pay now](https://buy.stripe.com/abc)\n"
    with pytest.raises(ValueError, match="row 11"):
        site_build.build(_tiny_repo(tmp_path, bad), tmp_path / "out")
