"""Rules of scripts/sitecheck.py that protect the site's owner — tested without network."""
import importlib.util
import socket
import sys
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("sitecheck", Path(__file__).parents[1] / "scripts" / "sitecheck.py")
sc = importlib.util.module_from_spec(spec)
sys.modules["sitecheck"] = sc  # dataclasses look the module up by name
spec.loader.exec_module(sc)


def test_registrable_domain():
    assert sc.registrable_domain("www.raisingchris.com") == "raisingchris.com"
    assert sc.registrable_domain("blog.shop.example.co.uk") == "example.co.uk"
    assert sc.registrable_domain("alice.github.io") == "alice.github.io"
    assert sc.registrable_domain("bob.github.io") != sc.registrable_domain("alice.github.io")
    assert sc.registrable_domain("localhost") == "localhost"


def test_same_site_is_registrable_domain_not_host():
    assert sc.same_site("https://raisingchris.com/", "https://www.raisingchris.com/x")
    assert not sc.same_site("https://raisingchris.com/", "https://github.com/raisingchris")
    assert not sc.same_site("https://a.netlify.app/", "https://b.netlify.app/")
    assert not sc.same_site("https://a.com/", "mailto:x@a.com")


def test_forbidden_hosts_never_resolve_private():
    def fake_resolve(host, port):
        table = {"good.example.com": "93.184.216.34", "evil.example.com": "10.0.0.5",
                 "loop.example.com": "127.0.0.1", "link.example.com": "169.254.1.1"}
        if host not in table:
            raise OSError("no such host")
        return [(socket.AF_INET, None, None, "", (table[host], 0))]

    assert sc.forbidden_host("good.example.com", fake_resolve) is None
    assert "private" in sc.forbidden_host("evil.example.com", fake_resolve)
    assert "private" in sc.forbidden_host("loop.example.com", fake_resolve)
    assert "private" in sc.forbidden_host("link.example.com", fake_resolve)
    assert sc.forbidden_host("nope.example.com", fake_resolve) == "does not resolve"
    # never even resolved:
    assert sc.forbidden_host("127.0.0.1", fake_resolve) == "IP address, not a name"
    assert sc.forbidden_host("[::1]", fake_resolve) == "IP address, not a name"
    assert sc.forbidden_host("localhost", fake_resolve) == "local name"
    assert sc.forbidden_host("router.local", fake_resolve) == "local name"
    assert sc.forbidden_host("intranet", fake_resolve) == "no dot in host"
    assert sc.forbidden_host("", fake_resolve) == "empty host"


def test_normalize_drops_fragment_and_refuses_other_schemes():
    assert sc.normalize("/a#top", "https://x.com/b/") == "https://x.com/a"
    assert sc.normalize("HTTPS://X.com") == "https://x.com/"
    assert sc.normalize("mailto:a@b.c") is None
    assert sc.normalize("javascript:void(0)", "https://x.com/") is None
    assert sc.normalize("tel:+1", "https://x.com/") is None


def test_looks_like_page():
    assert sc.looks_like_page("https://x.com/diary/")
    assert not sc.looks_like_page("https://x.com/mark.svg")
    assert not sc.looks_like_page("https://x.com/feed.xml")


def test_budget_caps_and_paces():
    b = sc.Budget(3)
    assert [b.take() for _ in range(5)] == [True, True, True, False, False]
    assert b.left() == 0
    slept = []
    clock = [100.0]
    b2 = sc.Budget(10)
    b2.pace(now=lambda: clock[0], sleep=slept.append)  # first call: no wait
    b2.pace(now=lambda: clock[0], sleep=slept.append)  # same instant: waits a full gap
    assert slept == [pytest.approx(sc.MIN_GAP_S)]


def test_follow_chain_stops_at_domain_edge_and_lists_it():
    table = {
        "https://x.com/a": (301, "/b"),
        "https://x.com/b": (302, "https://other.org/c"),
        "https://other.org/c": (200, None),
    }
    r = sc.follow_chain("https://x.com/a", lambda u: table[u], "https://x.com/")
    assert r["chain"] == ["https://x.com/a", "https://x.com/b", "https://other.org/c"]
    assert r["result"].startswith("redirects off-domain (not followed)")
    assert "https://other.org/c" not in [k for k in table if k == "fetched"]  # never fetched (no call made)


def test_follow_chain_results():
    assert sc.follow_chain("https://x.com/", lambda u: (200, None), "https://x.com/")["result"] == "ok"
    assert sc.follow_chain("https://x.com/", lambda u: (404, None), "https://x.com/")["result"] == "broken (404)"
    r = sc.follow_chain("https://x.com/a", lambda u: (301, "/a"), "https://x.com/", max_hops=3)
    assert r["result"] == "too many redirects" and len(r["chain"]) == 4

    def boom(u):
        raise TimeoutError(u)
    assert sc.follow_chain("https://x.com/", boom, "https://x.com/")["result"] == "timeout"


def test_report_says_clean_when_nothing_found():
    pr = sc.PageResult(url="https://x.com/", checked_at="2026-09-17T12:00:00Z", status=200, load_ms=300,
                       title="X", h1_count=1, viewport=True)
    r = {"start": "https://x.com/", "began": "t0", "finished": "t1", "robots": "read", "pages": [pr],
         "skipped": [], "links": [{"url": "https://x.com/a", "found_on": "https://x.com/", "text": "a",
                                   "count": 1, "checked_at": "t", "result": "ok", "status": 200,
                                   "chain": ["https://x.com/a"]}],
         "requests_used": 3, "budget": 400, "stopped": "", "queue_left": 0, "sample": True, "max_pages": 1}
    md = sc.render_report(r)
    assert "**Clean.**" in md
    assert "sample: one page only" in md
    assert "pay" not in md.lower() and "$" not in md  # the sample carries no payment words
    assert "2026-09-17T12:00:00Z" in md


def test_report_lists_mixed_assets_and_timeouts():
    pr = sc.PageResult(url="https://x.com/", checked_at="t", status=200, load_ms=300, title="X", h1_count=1,
                       viewport=True, mixed=["http://cdn.example/a.png"],
                       failed_images=["https://cdn.example/a.png"])
    r = {"start": "https://x.com/", "began": "t0", "finished": "t1", "robots": "read", "pages": [pr],
         "skipped": [], "links": [{"url": "https://x.com/slow", "found_on": "https://x.com/", "text": "slow",
                                   "count": 1, "checked_at": "t", "result": "timeout", "status": None,
                                   "chain": ["https://x.com/slow"]}],
         "requests_used": 3, "budget": 400, "stopped": "", "queue_left": 0, "sample": False, "max_pages": 25}
    md = sc.render_report(r)
    assert "## 2. Links — 1 of 1 broken" in md and "https://x.com/slow — timeout" in md
    assert "## 6. Mixed content — 1 http:// asset on https:// pages" in md
    assert "- http://cdn.example/a.png on https://x.com/" in md
    # the browser's silent https:// upgrade is explained next to the failed image, not left as a mystery
    assert "written as http:// in the HTML" in md
    assert "**Clean.**" not in md


# --- 2026-09-18: three labels the first real knock run showed were wrong ---

def test_off_site_403_is_refused_not_broken_but_on_site_403_is_broken():
    r = sc.follow_chain("https://other.org/shop", lambda u: (403, None), "https://x.com/")
    assert r["result"].startswith("refused (403)") and "not verified" in r["result"]
    assert r["status"] == 403
    # my own site's 403 is a real problem, not a wall against me
    assert sc.follow_chain("https://x.com/private", lambda u: (403, None), "https://x.com/")["result"] == "broken (403)"
    # 404 on another site is still simply broken
    assert sc.follow_chain("https://other.org/gone", lambda u: (404, None), "https://x.com/")["result"] == "broken (404)"


def test_has_downgrade_spots_the_https_to_http_hop():
    assert sc.has_downgrade(["https://a.org/x", "http://b.org/x", "https://b.org/x"])
    assert not sc.has_downgrade(["https://a.org/x", "https://b.org/x"])
    assert not sc.has_downgrade(["http://a.org/x", "https://a.org/x"])  # an upgrade is fine
    assert not sc.has_downgrade(["https://a.org/x"])


def test_read_robots_follows_same_site_redirect_and_reports_final_status():
    table = {
        "https://x.com/robots.txt": (301, "https://www.x.com/robots.txt", ""),
        "https://www.x.com/robots.txt": (404, None, ""),
    }
    rp, note = sc.read_robots("https://x.com/robots.txt", lambda u: table[u], "https://x.com/")
    assert note == "none (HTTP 404 after redirect; all allowed)"
    assert rp.can_fetch("Chris", "https://x.com/anything")

    table2 = {
        "https://x.com/robots.txt": (302, "/r.txt", ""),
        "https://x.com/r.txt": (200, None, "User-agent: *\nDisallow: /secret\n"),
    }
    rp, note = sc.read_robots("https://x.com/robots.txt", lambda u: table2[u], "https://x.com/")
    assert note == "read (via redirect to https://x.com/r.txt)"
    assert not rp.can_fetch("Chris", "https://x.com/secret") and rp.can_fetch("Chris", "https://x.com/ok")

    # off-site redirect is never followed
    rp, note = sc.read_robots("https://x.com/robots.txt", lambda u: (301, "https://cdn.other/robots.txt", ""), "https://x.com/")
    assert note.startswith("redirects off-site") and rp.can_fetch("Chris", "https://x.com/a")

    # a plain 200 is still just "read"; a 500 is treated as allow with the status shown
    rp, note = sc.read_robots("https://x.com/robots.txt", lambda u: (200, None, "User-agent: *\nAllow: /\n"), "https://x.com/")
    assert note == "read"
    rp, note = sc.read_robots("https://x.com/robots.txt", lambda u: (503, None, ""), "https://x.com/")
    assert note == "HTTP 503 (treated as allow)"


def test_report_separates_refused_links_and_names_the_downgrade_hop():
    pr = sc.PageResult(url="https://x.com/", checked_at="t", status=200, load_ms=300, title="X", h1_count=1,
                       viewport=True)
    links = [
        {"url": "https://shop.other/", "found_on": "https://x.com/", "text": "shop", "count": 1, "checked_at": "t",
         "result": "refused (403) — may be a bot wall, not verified", "status": 403, "chain": ["https://shop.other/"]},
        {"url": "https://f.x.com/m", "found_on": "https://x.com/", "text": "members", "count": 1, "checked_at": "t",
         "result": "redirects off-domain (not followed)", "status": 301,
         "chain": ["https://f.x.com/m", "http://found.org/m"]},
    ]
    r = {"start": "https://x.com/", "began": "t0", "finished": "t1", "robots": "none (HTTP 404; all allowed)",
         "pages": [pr], "skipped": [], "links": links,
         "requests_used": 3, "budget": 400, "stopped": "", "queue_left": 0, "sample": True, "max_pages": 1}
    md = sc.render_report(r)
    assert "## 2. Links — 0 of 2 broken" in md            # the 403 is not counted as broken
    assert "refused, not verified: 1 other site" in md
    assert "https://shop.other/ — refused (403)" in md
    assert "drops from https:// to http:// for a hop" in md
    assert "https://f.x.com/m → http://found.org/m" in md
    assert "**Clean.**" not in md
    assert "2 findings in total" in md                    # the redirect line + the downgrade line; the 403 adds none
    assert "pay" not in md.lower() and "$" not in md


def test_report_says_why_a_link_errored_in_plain_words():
    assert sc.plain_error("[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: certificate has expired (_ssl.c:1010)") \
        == " (the site's https certificate has expired)"
    assert sc.plain_error("[Errno -2] Name or service not known") == " (the domain name doesn't resolve)"
    assert sc.plain_error("") == ""
    pr = sc.PageResult(url="https://x.com/", checked_at="t", status=200, load_ms=300, title="X", h1_count=1, viewport=True)
    r = {"start": "https://x.com/", "began": "t0", "finished": "t1", "robots": "read", "pages": [pr], "skipped": [],
         "links": [{"url": "https://old.other/", "found_on": "https://x.com/", "text": "", "count": 1, "checked_at": "t",
                    "result": "error", "status": None, "chain": ["https://old.other/"],
                    "detail": "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: certificate has expired (_ssl.c:1010)"}],
         "requests_used": 3, "budget": 400, "stopped": "", "queue_left": 0, "sample": True, "max_pages": 1}
    md = sc.render_report(r)
    assert "https://old.other/ — error (the site's https certificate has expired); on https://x.com/" in md
