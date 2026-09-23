"""Tests for scripts/shopify_snapshot.py — the niche daily saver.

Every fetch is faked; nothing here touches the network.
"""
import importlib.util
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location("shopify_snapshot", Path(__file__).resolve().parents[1] / "scripts" / "shopify_snapshot.py")
ss = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ss)


def product(handle, price="10.00", vid=1, compare=None, available=True, variants=None):
    return {
        "id": hash(handle) % 10**6, "handle": handle, "title": handle.title(), "product_type": "Serum", "vendor": "Brand",
        "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-02T00:00:00Z", "published_at": "2026-01-01T00:00:00Z",
        "tags": ["face"], "body_html": "<p>lots of text that must not be saved</p>",
        "images": [{"src": "a.jpg"}, {"src": "b.jpg"}],
        "variants": variants or [{"id": vid, "title": "30ml", "sku": "S1", "price": price, "compare_at_price": compare,
                                  "available": available, "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-02T00:00:00Z"}],
    }


class FakeFetch:
    def __init__(self, robots="User-agent: *\nDisallow: /cart\n", pages=None, robots_status=200, fail=None, product_status=200):
        self.robots, self.pages, self.robots_status, self.fail, self.product_status = robots, pages or [[]], robots_status, fail, product_status
        self.urls = []

    def __call__(self, url):
        self.urls.append(url)
        if self.fail and self.fail in url:
            raise OSError("boom")
        if url.endswith("/robots.txt"):
            return self.robots_status, self.robots.encode()
        if "/products.json" in url:
            page = int(url.split("page=")[1])
            items = self.pages[page - 1] if page <= len(self.pages) else []
            return self.product_status, json.dumps({"products": items}).encode()
        raise AssertionError(url)


def nopace():
    return ss.Pacer(now=lambda: 0.0, sleep=lambda s: None)


BRAND = {"slug": "acme", "domain": "acme.example"}


def test_compact_drops_body_and_images_keeps_prices():
    row = ss.compact(product("glow", price="12.50", compare="15.00"))
    assert "body_html" not in row and "images" not in row
    assert row["image_count"] == 2
    assert row["variants"][0]["price"] == "12.50" and row["variants"][0]["compare_at_price"] == "15.00"


def test_robots_disallow_means_nothing_read():
    f = FakeFetch(robots="User-agent: *\nDisallow: /products.json\n", pages=[[product("a")]])
    rec = ss.snapshot_brand(BRAND, fetch=f, pacer=nopace())
    assert rec["status"] == "gap" and "disallows" in rec["reason"]
    assert all("/products.json" not in u for u in f.urls), "must not fetch what robots forbids"


def test_robots_404_means_allowed():
    f = FakeFetch(robots_status=404, pages=[[product("a")]])
    rec = ss.snapshot_brand(BRAND, fetch=f, pacer=nopace())
    assert rec["status"] == "ok" and len(rec["products"]) == 1


def test_robots_unreadable_is_a_gap_not_a_go():
    f = FakeFetch(fail="robots.txt", pages=[[product("a")]])
    rec = ss.snapshot_brand(BRAND, fetch=f, pacer=nopace())
    assert rec["status"] == "gap" and "robots unreadable" in rec["reason"]
    assert len(f.urls) == 1


def test_network_failure_is_a_gap_with_zero_products_not_a_zero_count():
    f = FakeFetch(fail="products.json")
    rec = ss.snapshot_brand(BRAND, fetch=f, pacer=nopace())
    assert rec["status"] == "gap" and rec["products"] == []


def test_non_shopify_body_is_a_gap():
    class F(FakeFetch):
        def __call__(self, url):
            if "/products.json" in url:
                self.urls.append(url)
                return 200, b"<html>not a store</html>"
            return super().__call__(url)
    rec = ss.snapshot_brand(BRAND, fetch=F(), pacer=nopace())
    assert rec["status"] == "gap" and "not JSON" in rec["reason"]


def test_paging_stops_on_short_page_and_paces_every_request():
    full = [product(f"p{i}", vid=i) for i in range(ss.PAGE_SIZE)]
    f = FakeFetch(pages=[full, [product("last", vid=9999)]])
    sleeps = []
    pacer = ss.Pacer(now=lambda: 0.0, sleep=sleeps.append)
    rec = ss.snapshot_brand(BRAND, fetch=f, pacer=pacer)
    assert rec["status"] == "ok" and len(rec["products"]) == ss.PAGE_SIZE + 1
    assert [u for u in f.urls if "page=" in u] == [
        f"https://acme.example/products.json?limit={ss.PAGE_SIZE}&page=1",
        f"https://acme.example/products.json?limit={ss.PAGE_SIZE}&page=2",
    ]
    # robots + 2 pages = 3 requests; the pacer waited before each one after the first
    assert len(sleeps) == 2 and all(s == pytest.approx(ss.MIN_GAP_S) for s in sleeps)


def test_run_writes_one_file_per_brand_and_a_summary(tmp_path):
    brands = tmp_path / "brands.json"
    brands.write_text(json.dumps([BRAND, {"slug": "off", "domain": "off.example", "active": False}]))
    f = FakeFetch(pages=[[product("a")]])
    out = tmp_path / "snaps"
    ss.run(brands, out, fetch=f, pacer=nopace(), date="2026-09-23")
    assert (out / "2026-09-23" / "acme.json").exists()
    assert not (out / "2026-09-23" / "off.json").exists()
    summary = json.loads((out / "2026-09-23" / "_summary.json").read_text())
    assert summary == [{"slug": "acme", "status": "ok", "reason": "1 products", "count": 1, "fetched_at": summary[0]["fetched_at"]}]


def rec(products, status="ok", at="2026-09-23T07:00:00Z"):
    return {"status": status, "fetched_at": at, "products": [ss.compact(p) for p in products]}


def test_diff_finds_new_removed_price_and_availability():
    a = rec([product("keep", price="10.00"), product("gone"), product("flip", vid=5, available=True)])
    b = rec([product("keep", price="8.50", compare="10.00"), product("new"), product("flip", vid=5, available=False)], at="2026-09-24T07:00:00Z")
    d = ss.diff(a, b)
    assert d["comparable"]
    assert d["new_products"] == ["new"] and d["removed_products"] == ["gone"]
    assert d["price_changes"] == [{"handle": "keep", "variant": "30ml", "from": "10.00", "to": "8.50", "compare_from": None, "compare_to": "10.00"}]
    assert d["availability_changes"] == [{"handle": "flip", "variant": "30ml", "available": False}]


def test_diff_finds_new_variant():
    a = rec([product("p", vid=1)])
    b = rec([product("p", variants=[product("p", vid=1)["variants"][0], {**product("p", vid=2)["variants"][0], "title": "50ml"}])])
    assert ss.diff(a, b)["new_variants"] == [{"handle": "p", "variant": "50ml"}]


def test_diff_refuses_across_a_gap():
    d = ss.diff(rec([product("a")]), rec([], status="gap"))
    assert d["comparable"] is False and "gap is not zero" in d["why"]


def test_diff_holds_a_suspicious_jump():
    d = ss.diff(rec([product(f"p{i}", vid=i) for i in range(10)]), rec([product("p0")]))
    assert d["comparable"] is False and "held" in d["why"]


def test_diff_missing_day():
    assert ss.diff(None, rec([])) == {"comparable": False, "why": "missing day"}


def test_user_agent_names_me_and_says_ai():
    assert "raisingchris.com" in ss.USER_AGENT and "AI" in ss.USER_AGENT
