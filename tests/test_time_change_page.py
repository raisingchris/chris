"""/time-change-2026/: the plain page for people, not developers.

Kept out of tests/test_site.py on purpose (2026-11-21): that file is also edited on
origin/main, and my appends there keep jamming the merge in ticket 0938.
"""

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

_spec = importlib.util.spec_from_file_location("chris_site_build_tc", REPO / "site" / "build.py")
site_build = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(site_build)


@pytest.fixture(scope="module")
def out(real_site_out) -> Path:
    return real_site_out  # one shared build (conftest.py)


def test_time_change_page_answers_the_public_question(out: Path):
    """2026-11-20: people search "Alberta time change" (~50k in Canada in October), not "phone time wrong" (~50).
    A plain page answers that question first, says an AI wrote it, links the check, and is in the sitemap."""
    html = (out / "time-change-2026" / "index.html").read_text()
    assert "Alberta, BC and Manitoba time change 2026" in html
    assert "an AI agent" in html
    assert 'href="/tz-2026/browser/"' in html and 'href="/tz-2026/"' in html
    assert "/time-change-2026/" in (out / "sitemap.xml").read_text()


def test_md_pages_get_their_own_description(out: Path):
    """2026-11-27: every md page's <meta name="description"> was the site footer ("I'm Chris, an AI raised
    in public..."), so a search snippet for /time-change-2026/ said nothing about clocks. Frontmatter
    `description:` wins; otherwise the first paragraph, as plain text, at most 160 characters."""
    import re

    def desc(slug: str) -> str:
        html = (out / slug / "index.html").read_text()
        m = re.search(r'<meta name="description" content="([^"]*)"', html)
        assert m, slug
        import html as _h

        return _h.unescape(m.group(1))

    tc = desc("time-change-2026")
    assert "clock" in tc.lower() and "Alberta" in tc and "raised in public" not in tc
    assert len(tc) <= 160
    tz = desc("tz-2026")  # no frontmatter: first paragraph, markdown stripped
    assert tz.startswith("Short answer: these places stopped") and "**" not in tz
    assert len(tz) <= 160


def test_plain_description_helper():
    f = site_build._plain_description
    assert f("# T\n\n**Short answer:** a [link](/x/) and `code`.\n\nmore") == "Short answer: a link and code."
    long = "# T\n\n" + "word " * 60
    d = f(long)
    assert len(d) <= 160 and d.endswith("…") and not d.endswith(" …")
    assert f("# T\n\n*Written by me.*\n\n| a | b |\n|---|---|\n") == "Written by me."
    assert f("# only a title\n") == ""


def test_home_links_the_pages_people_can_use(out: Path):
    """2026-11-27: the home page linked none of the pages written for outside readers."""
    home = (out / "index.html").read_text()
    for href in ('href="/time-change-2026/"', 'href="/tz-2026/"', 'href="/agents/"'):
        assert href in home, href


def test_updated_frontmatter_reaches_the_sitemap(out: Path):
    """2026-11-27: the IndexNow job only announces pages with a recent lastmod, and md pages had none."""
    sm = (out / "sitemap.xml").read_text()
    assert "<loc>https://raisingchris.com/time-change-2026/</loc><lastmod>" in sm
