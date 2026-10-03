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
import time
from urllib import robotparser
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from agentready.models import StoreSnapshot

USER_AGENT = (
    "AgentReadyBot/0.1 (+https://raisingchris.com/agents/; diagnosing your store's "
    "agent-readiness to help you fix it; contact chris@raisingchris.com)"
)
TIMEOUT = 15.0
# Politeness (2026-10-03, after three 429 days on one shop's server): a pause between
# requests, robots.txt honoured for every path after the homepage, and a full stop at
# the first 429/503 — a "slow down" ends the audit, it isn't retried.
PAUSE_S = 20.0
STOP_CODES = (429, 503)


def _norm_url(url: str) -> str:
    if not urlparse(url).scheme:
        url = "https://" + url
    return url


class SlowDown(Exception):
    """The store said 429/503. Stop the whole audit."""


def _get(client: httpx.Client, url: str, pause: float = 0.0) -> httpx.Response | None:
    if pause:
        time.sleep(pause)
    try:
        r = client.get(url, follow_redirects=True)
    except httpx.HTTPError:
        return None
    if r.status_code in STOP_CODES:
        raise SlowDown(f"{r.status_code} on {url}")
    return r


def _robots(text: str | None) -> robotparser.RobotFileParser:
    rp = robotparser.RobotFileParser()
    rp.parse((text or "").splitlines())
    return rp


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


# Words that make a store's terms a "no" to an automated read. Matched loosely on purpose:
# a false "no" costs me one polite email; a false "silent" costs the owner their word.
NO_BOT_WORDS = re.compile(
    r"spider|crawl|scrap(e|ing)|robot|data[- ]mining|automated (means|tools|systems|software)|bots?\b",
    re.IGNORECASE,
)
_TERMS_HREF = re.compile(r'href=["\']([^"\']*(?:terms|conditions)[^"\']*)["\']', re.IGNORECASE)


def _text(html: str) -> str:
    t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t))


def terms_gate(client: httpx.Client, base: str, home_html: str, allowed, pause: float) -> tuple[str, str]:
    """Find and read the store's terms. Returns (status, url).

    "says-no" if they forbid automated reading; "unreadable" if there's no link, robots
    forbids the page, or it won't load; "silent" otherwise. Only "silent" lets the cold
    audit go past homepage + robots. Intent and a polite user-agent don't turn a no into
    a yes (Value 6; council 2026-10-03).
    """
    hrefs = [h for h in _TERMS_HREF.findall(home_html) if "privacy" not in h.lower()]
    if not hrefs:
        return "unreadable", ""
    turl = urljoin(base + "/", hrefs[0])
    if urlparse(turl).netloc != urlparse(base).netloc:
        return "unreadable", turl
    if not allowed(urlparse(turl).path.lstrip("/")):
        return "unreadable", turl
    r = _get(client, turl, pause)
    if r is None or r.status_code != 200:
        return "unreadable", turl
    return ("says-no" if NO_BOT_WORDS.search(_text(r.text)) else "silent"), turl


def gather(url: str, *, client: httpx.Client | None = None, pause: float = PAUSE_S,
           owner_yes: bool = False) -> StoreSnapshot:
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

        r = _get(client, urljoin(base + "/", "robots.txt"), pause)
        if r is not None and r.status_code == 200:
            snap.robots_txt = r.text
        # A missing robots.txt (404) means "no rules"; one that failed to load means "unknown",
        # and unknown is treated as no.
        rp = _robots(snap.robots_txt if (r is not None and r.status_code < 500) else "User-agent: *\nDisallow: /")
        ua = USER_AGENT.split("/")[0]

        def allowed(path: str) -> bool:
            ok = rp.can_fetch(ua, urljoin(base + "/", path))
            if not ok:
                snap.gather_notes.append(f"Skipped /{path}: robots.txt disallows it.")
            return ok

        if owner_yes:
            snap.terms_status = "owner-yes"
        else:
            snap.terms_status, snap.terms_url = terms_gate(client, base, snap.homepage_html, allowed, pause)
        if snap.terms_status not in ("silent", "owner-yes"):
            snap.gather_notes.append(
                f"Stopped after homepage + robots + terms: terms are '{snap.terms_status}'. "
                "Ask the owner first; re-run with --owner-yes only after they say yes in their own words."
            )
            snap.signals = _detect_signals(snap.homepage_html, snap.headers, False)
            return snap

        if allowed("llms.txt"):
            r = _get(client, urljoin(base + "/", "llms.txt"), pause)
            if r is not None and r.status_code == 200 and "html" not in r.headers.get("content-type", ""):
                snap.llms_txt = r.text
        if allowed("sitemap.xml"):
            r = _get(client, urljoin(base + "/", "sitemap.xml"), pause)
            if r is not None and r.status_code == 200 and "xml" in r.headers.get("content-type", "").lower():
                snap.sitemap_xml = r.text

        # Shopify detection + catalogue.
        powered = snap.headers.get("x-shopid") or snap.headers.get("x-shopify-stage")
        if powered or "cdn.shopify.com" in snap.homepage_html or "shopify" in snap.homepage_html.lower():
            snap.is_shopify = True
            r = _get(client, urljoin(base + "/", "products.json?limit=50"), pause) if allowed("products.json?limit=50") else None
            if r is not None and r.status_code == 200 and "json" in r.headers.get("content-type", "").lower():
                try:
                    snap.products_json = r.json()
                except ValueError:
                    snap.gather_notes.append("products.json present but not valid JSON.")
            # Shopify's default robots.txt disallows /cart (which covers /cart.js); then we skip it.
            r = _get(client, urljoin(base + "/", "cart.js"), pause) if allowed("cart.js") else None
            if r is not None and r.status_code == 200 and "json" in r.headers.get("content-type", "").lower():
                try:
                    snap.cart_js = r.json()
                except ValueError:
                    pass

        snap.signals = _detect_signals(snap.homepage_html, snap.headers, snap.cart_js is not None)
        return snap
    except SlowDown as e:
        snap.gather_notes.append(f"Stopped early: the store said slow down ({e}). Not retried.")
        snap.signals = _detect_signals(snap.homepage_html, snap.headers, snap.cart_js is not None)
        return snap
    finally:
        if own_client:
            client.close()
