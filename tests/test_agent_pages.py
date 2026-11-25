"""/agents/<slug>/: one page per listed agent, plus the /autonomous-ai-agents/ explainer (2026-11-23)."""
import importlib.util
import json
import re
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("chris_site_build_agentpages", REPO / "site" / "build.py")
site_build = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(site_build)


@pytest.fixture(scope="module")
def out(real_site_out) -> Path:
    return real_site_out  # one shared build (conftest.py)


def _agents():
    return yaml.safe_load((REPO / "memory" / "wiki" / "agents.yaml").read_text())["agents"]


def test_every_agent_has_a_page_in_the_sitemap(out):
    sitemap = (out / "sitemap.xml").read_text()
    listing = (out / "agents" / "index.html").read_text()
    for a in _agents():
        page = out / "agents" / a["slug"] / "index.html"
        assert page.is_file(), a["slug"]
        html = page.read_text()
        assert a["name"] in html
        assert f"/agents/{a['slug']}/" in sitemap
        assert f'href="/agents/{a["slug"]}/"' in listing
        # own description and structured data, not the site-wide footer
        desc = re.search(r'<meta name="description" content="([^"]*)"', html).group(1)
        assert desc.startswith(a["name"].replace("&", "&amp;").split(" ")[0]), desc
        ld = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
        assert ld and json.loads(ld.group(1))["url"].endswith(f"/agents/{a['slug']}/")


def test_no_links_agent_page_links_nowhere_outside(out):
    for a in _agents():
        if a.get("url"):
            continue
        html = (out / "agents" / a["slug"] / "index.html").read_text()
        body = html[html.index("<article>"): html.index("</article>")]
        outside = [h for h in re.findall(r'href="([^"]+)"', body) if h.startswith("http") and "raisingchris.com" not in h]
        assert outside == [], (a["slug"], outside)


def test_json_points_at_pages(out):
    data = json.loads((out / "agents.json").read_text())
    assert all(a["page"].endswith(f"/agents/{a['slug']}/") for a in data["agents"])


def test_json_rows_carry_latest_entry(out):
    """An agent reading /agents.json can tell how fresh each row is without parsing history (2026-11-25)."""
    data = json.loads((out / "agents.json").read_text())
    assert "latest_entry" in data["how_to_read"]
    for a in data["agents"]:
        assert a["latest_entry"] == max(h["date"] for h in a["history"]), a["slug"]
    index = (out / "agents" / "index.html").read_text()
    assert "Last entry" in index
    assert all(a["latest_entry"] in index for a in data["agents"])


def test_explainer_page(out):
    html = (out / "autonomous-ai-agents" / "index.html").read_text()
    assert "What is an autonomous AI agent?" in html
    assert "/autonomous-ai-agents/" in (out / "sitemap.xml").read_text()
    assert "/autonomous-ai-agents/" in (out / "llms.txt").read_text()
    # every agent page it links to exists
    for slug in re.findall(r'href="/agents/([a-z0-9-]+)/"', html):
        assert (out / "agents" / slug / "index.html").is_file(), slug
    assert 'id="checked-not-listed"' in (out / "agents" / "index.html").read_text()


def test_agent_pages_carry_lastmod(out):
    """The daily IndexNow job only announces pages with a recent lastmod (2026-11-23)."""
    sitemap = (out / "sitemap.xml").read_text()
    for a in _agents():
        last = max(str(h["date"]) for h in a["history"])
        assert f"/agents/{a['slug']}/</loc><lastmod>{last}</lastmod>" in sitemap, a["slug"]
