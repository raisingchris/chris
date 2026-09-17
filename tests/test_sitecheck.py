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
