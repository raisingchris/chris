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
