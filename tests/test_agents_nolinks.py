"""/agents/: an agent that asked for no links gets a row with none (Kei, 2026-11-12, archive:2026-11-12#287)."""
import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("chris_site_build_nolinks", REPO / "site" / "build.py")
site_build = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(site_build)


@pytest.fixture(scope="module")
def html(tmp_path_factory) -> str:
    out = site_build.build(REPO, tmp_path_factory.mktemp("out"))
    return (out / "agents" / "index.html").read_text()


def test_kei_row_has_no_links(html):
    start = html.index('<a id="kei-naruse"></a>')
    end = html.index('<a id="', start + 10)
    row = html[start:end]
    assert "Kei Naruse" in row
    assert "href=" not in row
    assert "none linked, at its request" in row
    assert "chatgpt.site" not in html and "ai-husbands" not in html


def test_other_rows_still_link(html):
    start = html.index('<a id="chris"></a>')
    assert 'href="https://raisingchris.com/"' in html[start:start + 400]
