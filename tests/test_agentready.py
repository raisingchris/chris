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

def test_authorize_fails_on_captcha():
    r = evaluate(bad_store()).step("authorize")
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
