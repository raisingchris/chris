"""Gather what an agent would see of a store — the only part that touches the network.

``gather(url)`` makes a handful of polite GETs (homepage, robots.txt, llms.txt,
sitemap, and on Shopify the ``/products.json`` and ``/cart.js`` catalogue), pulls
the JSON-LD and a few signals out of the homepage, and returns a
:class:`~agentready.models.StoreSnapshot`. Everything is wrapped so one slow or
missing resource degrades the snapshot instead of raising.

The user-agent discloses who we are and why — this is a diagnosis done to help the
owner, in the open, never a disguised scrape. That disclosure is the point: it's
how reading a store's own data to improve it stays a knock, not a climb.
"""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from agentready.models import StoreSnapshot

USER_AGENT = (
    "AgentReadyBot/0.1 (+https://raisingchris.com/agents/; diagnosing your store's "
    "agent-readiness to help you fix it; contact chris@raisingchris.com)"
)
TIMEOUT = 15.0


def _norm_url(url: str) -> str:
    if not urlparse(url).scheme:
        url = "https://" + url
    return url


def _get(client: httpx.Client, url: str) -> httpx.Response | None:
    try:
        r = client.get(url, follow_redirects=True)
        return r
    except httpx.HTTPError:
        return None


def _extract_jsonld(html: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in re.finditer(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html, re.IGNORECASE | re.DOTALL,
    ):
        raw = m.group(1).strip()
        try:
            out.append(json.loads(raw))
        except (ValueError, TypeError):
            continue
    return out


def _detect_signals(html: str, headers: dict[str, str], has_cart_js: bool) -> dict[str, Any]:
    low = html.lower()
    signals: dict[str, Any] = {}

    captcha_markers = {
        "recaptcha": "recaptcha",
        "hcaptcha": "hcaptcha",
        "turnstile": "cloudflare turnstile",
        "cf-challenge": "cloudflare challenge",
        "__cf_chl": "cloudflare challenge",
    }
    for marker, kind in captcha_markers.items():
        if marker in low:
            signals["captcha"] = True
            signals["captcha_kind"] = kind
            break

    if "shop_pay" in low or "shopify_pay" in low or "shop pay" in low:
        signals["shop_pay"] = True
    if "agentic" in low or "/agent-checkout" in low or "agent-commerce" in low:
        signals["agent_pay"] = True

    # Shopify password-protected / forced login heuristics.
    if "customer_login_required" in low or re.search(r'/account/login', low):
        if "add to cart" not in low and "/cart" not in low:
            signals["forced_login"] = True

    if has_cart_js:
        signals["ajax_cart"] = True
    if "/cart/add" in low or "cart/add.js" in low:
        signals["ajax_cart"] = True

    if re.search(r'/policies/refund-policy|refund policy|returns? policy|/pages/returns', low):
        signals["refund_policy"] = True

    # A near-empty body that only ships a JS bundle: an agent without a full browser sees nothing.
    text_only = re.sub(r"(?is)<script.*?</script>|<style.*?</style>|<[^>]+>", " ", html)
    if len(text_only.split()) < 40 and "<script" in low:
        signals["js_only_checkout"] = True

    return signals


def gather(url: str, *, client: httpx.Client | None = None) -> StoreSnapshot:
    """Collect a :class:`StoreSnapshot` for ``url``. Never raises on a bad site."""
    url = _norm_url(url)
    own_client = client is None
    client = client or httpx.Client(
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/json;q=0.9,*/*;q=0.8"},
        timeout=TIMEOUT,
    )
    snap = StoreSnapshot(url=url)
    try:
        home = _get(client, url)
        if home is None:
            snap.reachable = False
            snap.gather_notes.append("Homepage request failed.")
            return snap
        snap.reachable = True
        snap.status_code = home.status_code
        snap.final_url = str(home.url)
        snap.headers = {k.lower(): v for k, v in home.headers.items()}
        snap.homepage_html = home.text or ""
        snap.jsonld = _extract_jsonld(snap.homepage_html)

        base = f"{urlparse(snap.final_url).scheme}://{urlparse(snap.final_url).netloc}"

        r = _get(client, urljoin(base + "/", "robots.txt"))
        if r is not None and r.status_code == 200:
            snap.robots_txt = r.text
        r = _get(client, urljoin(base + "/", "llms.txt"))
        if r is not None and r.status_code == 200 and "html" not in r.headers.get("content-type", ""):
            snap.llms_txt = r.text
        r = _get(client, urljoin(base + "/", "sitemap.xml"))
        if r is not None and r.status_code == 200 and "xml" in r.headers.get("content-type", "").lower():
            snap.sitemap_xml = r.text

        # Shopify detection + catalogue.
        powered = snap.headers.get("x-shopid") or snap.headers.get("x-shopify-stage")
        if powered or "cdn.shopify.com" in snap.homepage_html or "shopify" in snap.homepage_html.lower():
            snap.is_shopify = True
            r = _get(client, urljoin(base + "/", "products.json?limit=50"))
            if r is not None and r.status_code == 200 and "json" in r.headers.get("content-type", "").lower():
                try:
                    snap.products_json = r.json()
                except ValueError:
                    snap.gather_notes.append("products.json present but not valid JSON.")
            r = _get(client, urljoin(base + "/", "cart.js"))
            if r is not None and r.status_code == 200 and "json" in r.headers.get("content-type", "").lower():
                try:
                    snap.cart_js = r.json()
                except ValueError:
                    pass

        snap.signals = _detect_signals(snap.homepage_html, snap.headers, snap.cart_js is not None)
        return snap
    finally:
        if own_client:
            client.close()
