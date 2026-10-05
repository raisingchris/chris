"""The seven checks, pure: a :class:`StoreSnapshot` in, an :class:`AuditResult` out.

No network here. Each ``check_*`` reads only what ``gather`` already collected and
returns a :class:`StepResult` with a plain-language summary, the concrete evidence
behind the grade, and the specific fix the owner would make. ``evaluate`` runs all
seven and scores them.

Honesty rule baked in: the steps that can only be proven by spending money
(``pay``, ``confirm``) never claim ``PASS`` from reading a page. They read the
signals, say what they *suggest*, and mark themselves ``live_test_only`` so the
report tells the owner a real purchase is what confirms it.
"""

from __future__ import annotations

import re
from typing import Any

from agentready.models import AuditResult, Grade, StepResult, StoreSnapshot
from agentready.score import score_audit


# --- small helpers -----------------------------------------------------------

def _robots_blocks_everyone(robots: str | None) -> bool:
    """True if robots.txt has a ``User-agent: *`` group that disallows the whole site."""
    if not robots:
        return False
    groups = re.split(r"(?im)^user-agent:", robots)
    for g in groups:
        head = g.strip().splitlines()
        if not head:
            continue
        if head[0].strip() == "*":
            for line in head[1:]:
                line = line.strip()
                if line.lower().startswith("user-agent:"):
                    break
                if re.match(r"(?i)disallow:\s*/\s*$", line):
                    return True
    return False


def _robots_names_agents(robots: str | None) -> list[str]:
    """Known AI/agent crawler user-agents explicitly disallowed in robots.txt."""
    if not robots:
        return []
    known = ["GPTBot", "ClaudeBot", "Claude-Web", "PerplexityBot", "Google-Extended",
             "CCBot", "Bytespider", "Amazonbot", "Applebot-Extended", "cohere-ai"]
    blocked = []
    low = robots.lower()
    for name in known:
        # crude but good enough: the name appears in a user-agent line followed by a bare disallow
        if re.search(rf"(?im)^user-agent:\s*{re.escape(name.lower())}\s*$.*?^disallow:\s*/\s*$",
                     low, re.DOTALL):
            blocked.append(name)
    return blocked


def _jsonld_products(jsonld: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for block in jsonld:
        items = block if isinstance(block, list) else [block]
        for it in items:
            if not isinstance(it, dict):
                continue
            t = it.get("@type", "")
            types = t if isinstance(t, list) else [t]
            if any(str(x).lower() == "product" for x in types):
                out.append(it)
    return out


def _offer_has_price(product: dict[str, Any]) -> bool:
    offers = product.get("offers")
    if not offers:
        return False
    offers = offers if isinstance(offers, list) else [offers]
    return any(isinstance(o, dict) and (o.get("price") or o.get("lowPrice")) for o in offers)


def _offer_has_availability(product: dict[str, Any]) -> bool:
    offers = product.get("offers")
    if not offers:
        return False
    offers = offers if isinstance(offers, list) else [offers]
    return any(isinstance(o, dict) and o.get("availability") for o in offers)


# --- the seven checks --------------------------------------------------------

def check_discover(s: StoreSnapshot) -> StepResult:
    key = "discover"
    if not s.reachable:
        return StepResult(key, Grade.FAIL, "An agent can't load your store at all.",
                          evidence=[f"Request to {s.url} failed or timed out."],
                          fixes=["Make sure the store is reachable over plain HTTPS without a bot wall on the homepage."])
    ev, fixes = [], []
    if s.status_code and s.status_code >= 400:
        return StepResult(key, Grade.FAIL, f"The homepage returns HTTP {s.status_code} to an agent.",
                          evidence=[f"GET {s.final_url or s.url} → {s.status_code}"],
                          fixes=["Serve a 200 homepage to non-browser clients; don't gate the front page behind a challenge."])

    if _robots_blocks_everyone(s.robots_txt):
        return StepResult(key, Grade.FAIL, "Your robots.txt tells every crawler to stay out.",
                          evidence=["robots.txt has `User-agent: *` with `Disallow: /`."],
                          fixes=["Allow at least product and catalogue paths; a blanket block hides you from agents and search alike."])

    named = _robots_names_agents(s.robots_txt)
    if named:
        ev.append(f"robots.txt disallows: {', '.join(named)}.")
        fixes.append("Decide deliberately: blocking AI crawlers also blocks the agents that would buy from you.")

    ev.append("Store homepage loads for a non-browser client." )
    if s.llms_txt is not None:
        ev.append("Has /llms.txt (a map for AI clients).")
    else:
        fixes.append("Add /llms.txt — a short map of what you sell and where the catalogue is.")
    if s.sitemap_xml is not None:
        ev.append("Has an XML sitemap.")
    else:
        fixes.append("Publish an XML sitemap so an agent can enumerate products.")

    grade = Grade.PASS if (s.sitemap_xml is not None and not named) else Grade.PARTIAL
    summary = ("An agent can find and load your store." if grade is Grade.PASS
               else "An agent can load your store, but discovery is weaker than it should be.")
    return StepResult(key, grade, summary, evidence=ev, fixes=fixes)


def check_understand(s: StoreSnapshot) -> StepResult:
    key = "understand"
    ev, fixes = [], []
    has_products_json = bool(s.products_json and s.products_json.get("products"))
    jsonld_products = _jsonld_products(s.jsonld)
    priced = [p for p in jsonld_products if _offer_has_price(p)]
    avail = [p for p in jsonld_products if _offer_has_availability(p)]

    if has_products_json:
        from .fetch import PRODUCTS_LIMIT
        n = len(s.products_json["products"])
        count = f"at least {n}" if n >= PRODUCTS_LIMIT else str(n)
        ev.append(f"Shopify /products.json lists {count} product(s) with variants, price, and availability.")
    if jsonld_products:
        ev.append(f"{len(jsonld_products)} Product JSON-LD block(s); {len(priced)} with a price, "
                  f"{len(avail)} with availability.")

    machine_readable = has_products_json or (priced and avail)
    if machine_readable:
        grade = Grade.PASS
        summary = "An agent can read your catalogue, prices, and stock."
    elif jsonld_products or has_products_json:
        grade = Grade.PARTIAL
        summary = "Some structured catalogue data, but price or stock is missing for an agent."
        if not priced:
            fixes.append("Put price in Product structured data (schema.org Offer `price` + `priceCurrency`).")
        if not avail:
            fixes.append("Add `availability` (InStock/OutOfStock) to each Offer.")
    else:
        grade = Grade.FAIL
        summary = "An agent can't read your catalogue — prices and products are only in page layout."
        fixes.append("Add schema.org Product/Offer JSON-LD with price, currency, and availability on every product page.")
        fixes.append("If on Shopify, make sure /products.json isn't blocked — it's the easiest machine catalogue.")
    return StepResult(key, grade, summary, evidence=ev, fixes=fixes)


def check_authenticate(s: StoreSnapshot) -> StepResult:
    key = "authenticate"
    ev, fixes = [], []
    forced_login = bool(s.signals.get("forced_login"))
    guest_cart = s.cart_js is not None or bool(s.signals.get("guest_checkout"))
    if forced_login:
        return StepResult(key, Grade.FAIL, "An agent must create a human account before it can shop.",
                          evidence=["A login/account wall was detected before browsing or carting."],
                          fixes=["Allow guest browsing and guest checkout; a forced account blocks agents."])
    if guest_cart:
        ev.append("A cart/session can start without a human login (guest cart reachable).")
        grade = Grade.PASS
        summary = "An agent can start a cart without a human-only login."
    else:
        grade = Grade.UNKNOWN
        summary = "Whether an agent can start a session without a login needs a live check."
        fixes.append("Confirm guest checkout is on; expose a cart endpoint an agent can call.")
    return StepResult(key, grade, summary, evidence=ev, fixes=fixes)


def check_act(s: StoreSnapshot) -> StepResult:
    key = "act"
    ev, fixes = [], []
    ajax_cart = bool(s.signals.get("ajax_cart")) or s.cart_js is not None
    has_variant_ids = False
    if s.products_json and s.products_json.get("products"):
        for p in s.products_json["products"]:
            if isinstance(p, dict) and p.get("variants"):
                has_variant_ids = True
                break
    if ajax_cart and (has_variant_ids or s.is_shopify):
        ev.append("A programmatic add-to-cart path exists (ajax cart / cart.js).")
        if has_variant_ids:
            ev.append("Products expose variant IDs an agent can add.")
        grade = Grade.PASS
        summary = "An agent can add an item to the cart and hold that state."
    elif ajax_cart:
        grade = Grade.PARTIAL
        summary = "A cart exists, but it's unclear an agent can select the right variant."
        fixes.append("Expose variant IDs in machine-readable product data.")
    else:
        grade = Grade.UNKNOWN
        summary = "Add-to-cart needs a live check — no programmatic cart path was visible."
        fixes.append("Offer an ajax cart (e.g. Shopify /cart/add.js) or a cart API.")
    return StepResult(key, grade, summary, evidence=ev, fixes=fixes)


def check_authorize(s: StoreSnapshot) -> StepResult:
    key = "authorize"
    ev, fixes = [], []
    captcha = bool(s.signals.get("captcha"))
    js_only_checkout = bool(s.signals.get("js_only_checkout"))
    kind = s.signals.get("captcha_kind", "captcha")
    if captcha and kind == "cloudflare challenge":
        # The page we were served was itself a challenge: that's a wall we actually hit.
        return StepResult(key, Grade.FAIL, "A bot challenge stopped me on your own homepage.",
                          evidence=[f"The homepage answered with a {kind} page."],
                          fixes=["Let verified, disclosed agent traffic past the challenge (most bot-management tools have an allow list)."],
                          live_test_only=False)
    if captcha:
        # 2026-10-03: a captcha script on the homepage is usually a newsletter or contact form.
        # I never visit checkout (robots.txt disallows it), so I can't say it guards checkout.
        return StepResult(key, Grade.UNKNOWN, "A captcha loads on your homepage; whether it guards checkout needs a live check.",
                          evidence=[f"A {kind} script is on the homepage. I didn't visit checkout, so I can't say where it's used."],
                          fixes=["If the captcha also sits in front of checkout, an agent can't pass it. Check where it's used."],
                          live_test_only=True)
    if js_only_checkout:
        ev.append("Checkout appears to require heavy client-side JS.")
        fixes.append("Offer a checkout path that doesn't depend on full browser JS, or support an agent-checkout API.")
        grade = Grade.PARTIAL
        summary = "An agent may reach checkout, but a JS-only flow can stop it."
    else:
        ev.append("No captcha or bot-wall script on the homepage. Checkout itself wasn't visited.")
        grade = Grade.UNKNOWN
        summary = "Checkout looks reachable; only a live run confirms there's no human-only step."
    return StepResult(key, grade, summary, evidence=ev, fixes=fixes, live_test_only=not captcha)


def check_pay(s: StoreSnapshot) -> StepResult:
    key = "pay"
    ev, fixes = [], []
    shop_pay = bool(s.signals.get("shop_pay"))
    agent_pay = bool(s.signals.get("agent_pay"))  # emerging agentic-checkout rails
    if agent_pay:
        ev.append("An agentic-checkout / agent-pay rail was detected.")
        grade = Grade.PARTIAL  # still live-test to be sure
        summary = "Signals suggest an agent could pay; a live test confirms it."
    elif shop_pay:
        ev.append("Shop Pay is present (accelerated checkout an agent can sometimes drive).")
        grade = Grade.UNKNOWN
        summary = "Shop Pay is present, but whether an agent can complete payment needs a live test."
    else:
        grade = Grade.UNKNOWN
        summary = "Whether an agent can complete the payment step needs a live test."
        fixes.append("Support an accelerated or agent-friendly payment method; avoid payment inside an opaque iframe only a human can use.")
    fixes.append("Only a real purchase proves this step, and it has to go through Shopify's agent channel with a person approving payment.")
    return StepResult(key, grade, summary, evidence=ev, fixes=fixes, live_test_only=True)


def check_confirm(s: StoreSnapshot) -> StepResult:
    key = "confirm"
    ev, fixes = [], []
    if s.signals.get("refund_policy"):
        ev.append("A refund/returns policy page was found.")
    else:
        fixes.append("Publish a clear, linkable refund policy — agents (and their owners) check before buying.")
    fixes.append("Make the order confirmation machine-readable (structured receipt or an order-status endpoint).")
    return StepResult(key, Grade.UNKNOWN,
                      "Receipt readability and refund can only be proven by a live, refundable purchase.",
                      evidence=ev, fixes=fixes, live_test_only=True)


CHECKS = [check_discover, check_understand, check_authenticate, check_act,
          check_authorize, check_pay, check_confirm]


def evaluate(snapshot: StoreSnapshot) -> AuditResult:
    """Run all seven checks on a gathered snapshot and score the result."""
    steps = [check(snapshot) for check in CHECKS]
    audit = AuditResult(url=snapshot.url, snapshot=snapshot, steps=steps)
    return score_audit(audit)
