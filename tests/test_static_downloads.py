"""Every download that /tz-2026/ links must be in the built site.

Added 2026-11-26: /lockcheck.py was linked from /tz-2026/ since 11-19 and answered 404 on the live site,
because build.py copied tzcheck.py but never lockcheck.py. Separate file so it can't collide with a parent's test.
"""
import re


def test_every_linked_download_on_tz_page_is_served(real_site_out):
    html = (real_site_out / "tz-2026" / "index.html").read_text()
    links = sorted(set(re.findall(r'href="/([\w.-]+\.(?:py|php))"', html)))
    assert "lockcheck.py" in links and "tzcheck.py" in links
    missing = [name for name in links if not (real_site_out / name).is_file()]
    assert missing == []


def test_wordpress_plugin_is_served_and_linked(real_site_out):
    from pathlib import Path

    src = Path(__file__).resolve().parent.parent / "site" / "static" / "wp-date-tz-2026.php"
    assert (real_site_out / "wp-date-tz-2026.php").read_bytes() == src.read_bytes()
    text = src.read_text()
    assert text.startswith("<?php") and "an AI agent" in text
    for zone in ("America/Vancouver", "America/Edmonton", "America/Winnipeg", "America/Havana", "Africa/Casablanca", "America/Yellowknife"):
        assert zone + "|" in text
