"""tzcheck.html, the in-browser check linked from /tz-2026/ (2026-11-13).

The verdict logic runs in Node with a fake Intl, so the test doesn't depend on the machine's own tz data."""
import importlib.util
import json
import pathlib
import re
import shutil
import subprocess

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
SRC = REPO / "site" / "static" / "tzcheck-browser.html"

# Hours at 2026-11-15 12:00 UTC: right (2026f) and with each older data version.
RIGHT = {"America/Vancouver": "05:00", "America/Edmonton": "06:00", "America/Yellowknife": "06:00", "America/Inuvik": "06:00",
         "America/Winnipeg": "07:00", "America/Havana": "08:00"}
D2026D = dict(RIGHT, **{"America/Winnipeg": "06:00", "America/Havana": "07:00"})  # Chromium 156.0.8078.4
OLD = {"America/Vancouver": "04:00", "America/Edmonton": "05:00", "America/Yellowknife": "05:00", "America/Inuvik": "05:00",
       "America/Winnipeg": "06:00", "America/Havana": "07:00"}  # Node 20, 2024b


def _verdict(hours):
    js = re.search(r"<script>(.*)</script>", SRC.read_text(), re.S).group(1)
    harness = (
        "var HOURS=" + json.dumps(hours) + ";\n"
        "var Intl={DateTimeFormat:function(l,o){return {format:function(d){"
        "if(d.getTime()!==Date.UTC(2026,10,15,12)) throw new Error('moment');"
        "if(!(o.timeZone in HOURS)) throw new RangeError('zone'); return HOURS[o.timeZone];}};}};\n"
        + js + "\nvar r=check(); console.log(JSON.stringify(r.bad.map(function(z){return z[0]})));"
    )
    res = subprocess.run(["node", "-e", harness], capture_output=True, text=True, timeout=30)
    assert res.returncode == 0, res.stderr
    return json.loads(res.stdout)


needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="no node")


@needs_node
def test_all_right_with_2026f():
    assert _verdict(RIGHT) == []


@needs_node
def test_2026d_flags_winnipeg_and_havana():
    assert _verdict(D2026D) == ["America/Winnipeg", "America/Havana"]


@needs_node
def test_old_data_flags_all_six():
    assert len(_verdict(OLD)) == 6


@needs_node
def test_2026b_gets_vancouver_right():
    # 2026b (April) moved British Columbia to permanent -07; the other five came later.
    assert len(_verdict(dict(OLD, **{"America/Vancouver": "05:00"}))) == 5
    assert "America/Vancouver" not in _verdict(dict(OLD, **{"America/Vancouver": "05:00"}))


@needs_node
def test_unknown_zone_counts_as_wrong():
    hours = dict(RIGHT)
    del hours["America/Inuvik"]
    assert _verdict(hours) == ["America/Inuvik"]


def test_fragment_sends_nothing():
    text = SRC.read_text()
    for word in ("fetch(", "XMLHttpRequest", "sendBeacon", "googletagmanager", "<img", "src=\"http"):
        assert word not in text


def test_served_and_linked(tmp_path):
    spec = importlib.util.spec_from_file_location("chris_site_build_tzhtml", REPO / "site" / "build.py")
    sb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sb)
    out = sb.build(REPO, tmp_path / "out")
    page = (out / "tz-2026" / "browser" / "index.html").read_text()
    assert "function check()" in page and "<header" in page
    assert "I'm an AI. Anything you tell me is private from the world, but my operators can technically access it." in page
    assert 'href="/tz-2026/browser/"' in (out / "tz-2026" / "index.html").read_text()
