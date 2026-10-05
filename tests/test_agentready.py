"""AgentReady: pure-evaluation tests (no network), scoring, report, and the
publish-only-on-opt-in rule on the leaderboard."""

from __future__ import annotations

from datetime import date

from agentready.checks import evaluate
from agentready.leaderboard import Entry, aggregate_stats, record, render_index_md
from agentready.models import AuditResult, Grade, StoreSnapshot
from agentready.report import owner_report_md, to_json


# --- snapshots ---------------------------------------------------------------

def good_shopify() -> StoreSnapshot:
    return StoreSnapshot(
        url="https://good.example",
        final_url="https://good.example",
        reachable=True,
        status_code=200,
        homepage_html="<html>shop pay cdn.shopify.com add to cart /cart/add.js refund policy</html>",
        robots_txt="User-agent: *\nAllow: /\nSitemap: https://good.example/sitemap.xml\n",
        llms_txt="# good store\nProducts: /products.json\n",
        sitemap_xml="<urlset></urlset>",
        is_shopify=True,
        products_json={"products": [{"title": "Mug", "variants": [{"id": 1, "price": "9.00"}]}]},
        cart_js={"item_count": 0},
        signals={"shop_pay": True, "ajax_cart": True, "refund_policy": True},
    )


def bad_store() -> StoreSnapshot:
    return StoreSnapshot(
        url="https://bad.example",
        final_url="https://bad.example",
        reachable=True,
        status_code=200,
        homepage_html="<html><script>app()</script></html>",
        robots_txt="User-agent: *\nDisallow: /\n",
        signals={"captcha": True, "captcha_kind": "recaptcha", "forced_login": True},
    )


# --- discover ----------------------------------------------------------------

def test_discover_fails_when_robots_blocks_everyone():
    r = evaluate(bad_store()).step("discover")
    assert r.grade is Grade.FAIL
    assert "robots.txt" in " ".join(r.evidence).lower()


def test_discover_passes_for_a_crawlable_store_with_sitemap():
    r = evaluate(good_shopify()).step("discover")
    assert r.grade is Grade.PASS


def test_discover_fails_when_unreachable():
    snap = StoreSnapshot(url="https://x", reachable=False)
    r = evaluate(snap).step("discover")
    assert r.grade is Grade.FAIL


def test_discover_fails_on_http_error():
    snap = StoreSnapshot(url="https://x", reachable=True, status_code=403)
    assert evaluate(snap).step("discover").grade is Grade.FAIL


# --- understand --------------------------------------------------------------

def test_understand_passes_with_products_json():
    assert evaluate(good_shopify()).step("understand").grade is Grade.PASS


def test_understand_passes_with_priced_available_jsonld():
    snap = StoreSnapshot(url="https://j", jsonld=[{
        "@type": "Product", "name": "T",
        "offers": {"@type": "Offer", "price": "10", "availability": "InStock"},
    }])
    assert evaluate(snap).step("understand").grade is Grade.PASS


def test_understand_partial_when_price_missing():
    snap = StoreSnapshot(url="https://j", jsonld=[{"@type": "Product", "name": "T",
                                                   "offers": {"@type": "Offer"}}])
    assert evaluate(snap).step("understand").grade is Grade.PARTIAL


def test_understand_fails_with_no_structured_catalogue():
    snap = StoreSnapshot(url="https://plain", homepage_html="<html>just words</html>")
    r = evaluate(snap).step("understand")
    assert r.grade is Grade.FAIL
    assert r.fixes


# --- authenticate / act ------------------------------------------------------

def test_authenticate_fails_on_forced_login():
    assert evaluate(bad_store()).step("authenticate").grade is Grade.FAIL


def test_authenticate_passes_with_guest_cart():
    assert evaluate(good_shopify()).step("authenticate").grade is Grade.PASS


def test_act_passes_with_ajax_cart_and_variants():
    assert evaluate(good_shopify()).step("act").grade is Grade.PASS


# --- authorize / pay / confirm ----------------------------------------------

def test_homepage_recaptcha_is_not_claimed_as_a_checkout_wall():
    # 2026-10-03: a captcha script on the homepage is usually a form; checkout wasn't visited.
    r = evaluate(bad_store()).step("authorize")
    assert r.grade is Grade.UNKNOWN
    assert r.live_test_only is True
    assert "checkout" in r.summary and "needs a live check" in r.summary


def test_authorize_fails_when_we_were_actually_challenged():
    from dataclasses import replace
    snap = bad_store()
    snap.signals = {**snap.signals, "captcha_kind": "cloudflare challenge"}
    r = evaluate(snap).step("authorize")
    assert r.grade is Grade.FAIL
    assert r.live_test_only is False


def test_authorize_unknown_is_live_test_only_when_clean():
    r = evaluate(good_shopify()).step("authorize")
    assert r.grade is Grade.UNKNOWN
    assert r.live_test_only is True


def test_pay_and_confirm_are_always_live_test_only():
    a = evaluate(good_shopify())
    assert a.step("pay").live_test_only is True
    assert a.step("confirm").live_test_only is True
    # Never claims PASS from reading a page.
    assert a.step("pay").grade is not Grade.PASS
    assert a.step("confirm").grade is not Grade.PASS


# --- scoring -----------------------------------------------------------------

def test_good_store_scores_higher_than_bad():
    good = evaluate(good_shopify())
    bad = evaluate(bad_store())
    assert good.score > bad.score
    assert 0 <= bad.score <= 100 and 0 <= good.score <= 100


def test_bad_store_is_failing_grade():
    assert evaluate(bad_store()).grade_letter in {"D", "F"}


def test_all_seven_steps_present():
    assert len(evaluate(good_shopify()).steps) == 7


# --- report ------------------------------------------------------------------

def test_owner_report_has_score_disclosure_and_fixes():
    a = evaluate(bad_store())
    a.audited_at = date.today().isoformat()
    md = owner_report_md(a)
    assert f"{a.score}/100" in md
    assert "Always an AI." in md
    assert "How to fix it" in md


def test_json_roundtrips_shape():
    import json
    a = evaluate(good_shopify())
    d = json.loads(to_json(a))
    assert d["score"] == a.score
    assert len(d["steps"]) == 7


# --- leaderboard: the opt-in rule -------------------------------------------

def _audit_for(url: str, score: int) -> AuditResult:
    a = AuditResult(url=url, snapshot=StoreSnapshot(url=url), steps=[])
    a.score, a.grade_letter, a.audited_at = score, "C", "2026-10-03"
    return a


def test_cold_audit_is_private_and_not_rendered(tmp_path):
    data = tmp_path / "lb.json"
    record(data, _audit_for("https://cold.example", 40), name="Cold Store")
    md = render_index_md(data)
    assert "Cold Store" not in md          # never named without opt-in
    assert "cold.example" not in md
    assert "Audited so far:** 1" in md      # but it counts toward the stat


def test_published_store_is_rendered(tmp_path):
    data = tmp_path / "lb.json"
    record(data, _audit_for("https://warm.example", 88), name="Warm Store", published=True)
    md = render_index_md(data)
    assert "Warm Store" in md
    assert "88/100" in md


def test_reaudit_keeps_published_flag_and_appends_history(tmp_path):
    data = tmp_path / "lb.json"
    record(data, _audit_for("https://s.example", 50), name="S", published=True)
    e = record(data, _audit_for("https://s.example", 70))  # no publish arg
    assert e.published is True               # sticky
    assert e.score == 70
    assert len(e.history) == 1 and e.history[0]["score"] == 50


def test_aggregate_stats_counts_unbuyable():
    entries = {
        "a": Entry("a", "A", 30, "F", "d"),
        "b": Entry("b", "B", 80, "B", "d"),
        "c": Entry("c", "C", 55, "D", "d"),
    }
    stats = aggregate_stats(entries)
    assert stats["total"] == 3
    assert stats["unbuyable_pct"] == 67      # 30 and 55 are < 60


# --- 2026-10-03: manners (robots honoured, stop at first 429/503) and private output ---

def _mock_client(routes):
    import httpx
    seen = []

    def handler(req):
        seen.append(req.url.path)
        code, body, ctype = routes.get(req.url.path, (404, "", "text/plain"))
        return httpx.Response(code, text=body, headers={"content-type": ctype})

    return httpx.Client(transport=httpx.MockTransport(handler)), seen


def test_gather_skips_paths_robots_disallows():
    from agentready.fetch import gather
    home = ('<html><script src="https://cdn.shopify.com/x.js"></script><a href="/pages/terms">Terms</a>'
            + "word " * 50 + "</html>")
    client, seen = _mock_client({
        "/": (200, home, "text/html"),
        "/pages/terms": (200, "<p>Be nice. Pay on time.</p>", "text/html"),
        "/robots.txt": (200, "User-agent: *\nDisallow: /cart\n", "text/plain"),
        "/products.json": (200, '{"products": []}', "application/json"),
        "/cart.js": (200, '{"items": []}', "application/json"),
    })
    snap = gather("https://shop.test", client=client, pause=0)
    assert "/cart.js" not in seen
    assert "/products.json" in seen
    assert any("robots.txt disallows" in n for n in snap.gather_notes)


def test_gather_stops_at_first_429():
    from agentready.fetch import gather
    home = '<html><script src="https://cdn.shopify.com/x.js"></script>' + "word " * 50 + "</html>"
    client, seen = _mock_client({
        "/": (200, home, "text/html"),
        "/robots.txt": (429, "", "text/plain"),
    })
    snap = gather("https://shop.test", client=client, pause=0)
    assert seen == ["/", "/robots.txt"]
    assert any("slow down" in n for n in snap.gather_notes)


def test_cold_audits_default_to_a_gitignored_folder():
    import subprocess
    from agentready.cli import DEFAULT_OUT
    r = subprocess.run(["git", "check-ignore", "-q", str(DEFAULT_OUT / "x.json")])
    assert r.returncode == 0, "audit output must not be committable to the public repo"


def _gate_routes(terms_body):
    home = ('<html><script src="https://cdn.shopify.com/x.js"></script><a href="/pages/terms-of-service">Terms</a>'
            + "word " * 50 + "</html>")
    return {
        "/": (200, home, "text/html"),
        "/robots.txt": (200, "User-agent: *\nDisallow: /cart\n", "text/plain"),
        "/pages/terms-of-service": (200, terms_body, "text/html"),
        "/products.json": (200, '{"products": []}', "application/json"),
    }


def test_terms_that_say_no_stop_the_cold_audit():
    from agentready.fetch import gather
    client, seen = _mock_client(_gate_routes("<p>You agree not to spider, crawl, or scrape the Site.</p>"))
    snap = gather("https://shop.test", client=client, pause=0)
    assert snap.terms_status == "says-no"
    assert "/products.json" not in seen and "/sitemap.xml" not in seen


def test_no_terms_link_means_unreadable_and_stop():
    from agentready.fetch import gather
    routes = _gate_routes("")
    routes["/"] = (200, "<html>" + "word " * 50 + "</html>", "text/html")
    client, seen = _mock_client(routes)
    snap = gather("https://shop.test", client=client, pause=0)
    assert snap.terms_status == "unreadable"
    assert seen == ["/", "/robots.txt"]


def test_terms_disallowed_by_robots_are_unreadable_not_silent():
    from agentready.fetch import gather
    routes = _gate_routes("<p>Be nice.</p>")
    routes["/robots.txt"] = (200, "User-agent: *\nDisallow: /pages/\n", "text/plain")
    client, seen = _mock_client(routes)
    snap = gather("https://shop.test", client=client, pause=0)
    assert snap.terms_status == "unreadable"
    assert "/pages/terms-of-service" not in seen


def test_owner_yes_skips_the_gate():
    from agentready.fetch import gather
    client, seen = _mock_client(_gate_routes("<p>no spider, crawl, or scrape</p>"))
    snap = gather("https://shop.test", client=client, pause=0, owner_yes=True)
    assert snap.terms_status == "owner-yes"
    assert "/products.json" in seen


def test_full_products_page_is_a_floor_not_a_count():
    # 2026-10-05: one read asks for PRODUCTS_LIMIT products; a full page means "at least".
    from agentready.checks import check_understand
    from agentready.fetch import PRODUCTS_LIMIT
    snap = good_shopify()
    snap.products_json = {"products": [{"title": f"P{i}", "variants": [{"id": i, "price": "1.00"}]}
                                       for i in range(PRODUCTS_LIMIT)]}
    text = " ".join(check_understand(snap).evidence)
    assert f"at least {PRODUCTS_LIMIT}" in text
    snap = good_shopify()
    text = " ".join(check_understand(snap).evidence)
    assert "lists 1 product" in text and "at least" not in text
