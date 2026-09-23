#!/usr/bin/env python3
"""Daily saver for a small list of brand storefronts (skincare niche).

An AI (Chris, https://raisingchris.com) wrote and runs this. It reads only
what a store publishes to everyone: robots.txt first, then the public
`/products.json` that every Shopify storefront serves. GET only, one request
a second, User-Agent names me. It never logs in, never posts, never touches
a cart or a checkout.

Rules for the numbers (parent-b, 2026-09-23, adopted as mine):
  * a fetch that fails is a GAP, not zero — never compare across a gap
  * a day whose product count is far off the day before is HELD, not compared
  * a guess never sits beside a checked number without a label

Usage:
  scripts/shopify_snapshot.py run   --brands brands.json --out snapshots/
  scripts/shopify_snapshot.py diff  --out snapshots/ --brand SLUG A_DATE B_DATE
  scripts/shopify_snapshot.py diff  --out snapshots/ --brand SLUG   (latest two)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from datetime import datetime, timezone
from pathlib import Path

USER_AGENT = "ChrisNicheWatch/0.1 (an AI's daily reader of public product pages; +https://raisingchris.com)"
UA_TOKEN = USER_AGENT.split("/")[0]
MIN_GAP_S = 1.0
TIMEOUT_S = 20
PAGE_SIZE = 250
MAX_PAGES = 8  # 2,000 products; a small brand has far fewer
HOLD_RATIO = 2.0  # count doubled or halved between days -> hold, don't compare


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ---------- fetching ----------

class Pacer:
    def __init__(self, now=time.monotonic, sleep=time.sleep):
        self.now, self.sleep = now, sleep
        self.last: float | None = None

    def wait(self) -> None:
        if self.last is not None:
            gap = self.last + MIN_GAP_S - self.now()
            if gap > 0:
                self.sleep(gap)
        self.last = self.now()


def http_get(url: str) -> tuple[int, bytes]:
    """One GET. Returns (status, body). Raises OSError on network failure."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json,text/plain,*/*"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except urllib.error.URLError as e:
        raise OSError(str(e.reason))


def robots_allows(domain: str, path: str, fetch=http_get) -> tuple[bool | None, str]:
    """(allowed, note). None means robots.txt could not be read -> treat as a gap."""
    url = f"https://{domain}/robots.txt"
    try:
        status, body = fetch(url)
    except OSError as e:
        return None, f"robots unreadable: {e}"
    if status == 404:
        return True, "robots: none (404)"
    if status != 200:
        return None, f"robots: HTTP {status}"
    rp = urllib.robotparser.RobotFileParser()
    rp.parse(body.decode("utf-8", "replace").splitlines())
    ok = rp.can_fetch(UA_TOKEN, f"https://{domain}{path}") and rp.can_fetch("*", f"https://{domain}{path}")
    return bool(ok), "robots: allows" if ok else "robots: disallows"


# ---------- shaping ----------

VARIANT_KEYS = ("id", "title", "sku", "price", "compare_at_price", "available", "created_at", "updated_at")
PRODUCT_KEYS = ("id", "handle", "title", "product_type", "vendor", "created_at", "updated_at", "published_at", "tags")


def compact(product: dict) -> dict:
    row = {k: product.get(k) for k in PRODUCT_KEYS}
    row["variants"] = [{k: v.get(k) for k in VARIANT_KEYS} for v in product.get("variants", [])]
    row["image_count"] = len(product.get("images", []) or [])
    return row


def fetch_products(domain: str, fetch=http_get, pacer: Pacer | None = None) -> tuple[list[dict] | None, str]:
    """All products via paged /products.json. (None, reason) on any failure: a gap."""
    pacer = pacer or Pacer()
    out: list[dict] = []
    for page in range(1, MAX_PAGES + 1):
        url = f"https://{domain}/products.json?limit={PAGE_SIZE}&page={page}"
        pacer.wait()
        try:
            status, body = fetch(url)
        except OSError as e:
            return None, f"page {page}: {e}"
        if status != 200:
            return None, f"page {page}: HTTP {status}"
        try:
            data = json.loads(body.decode("utf-8", "replace"))
        except ValueError:
            return None, f"page {page}: not JSON"
        products = data.get("products")
        if not isinstance(products, list):
            return None, f"page {page}: no 'products' key (not a Shopify storefront?)"
        out.extend(compact(p) for p in products)
        if len(products) < PAGE_SIZE:
            break
    else:
        return None, f"more than {MAX_PAGES * PAGE_SIZE} products; refusing (is this a small brand?)"
    return out, f"{len(out)} products"


def snapshot_brand(brand: dict, fetch=http_get, pacer: Pacer | None = None) -> dict:
    domain = brand["domain"]
    rec = {"slug": brand["slug"], "domain": domain, "fetched_at": utcnow(), "status": "gap", "reason": "", "products": []}
    pacer = pacer or Pacer()
    pacer.wait()
    allowed, note = robots_allows(domain, "/products.json", fetch)
    rec["robots"] = note
    if allowed is None:
        rec["reason"] = note
        return rec
    if not allowed:
        rec["reason"] = "robots disallows /products.json; nothing read"
        return rec
    products, reason = fetch_products(domain, fetch, pacer)
    if products is None:
        rec["reason"] = reason
        return rec
    rec["status"], rec["reason"], rec["products"] = "ok", reason, products
    return rec


def run(brands_path: Path, out_dir: Path, fetch=http_get, pacer: Pacer | None = None, date: str | None = None) -> list[dict]:
    brands = json.loads(brands_path.read_text())
    day = date or today()
    day_dir = out_dir / day
    day_dir.mkdir(parents=True, exist_ok=True)
    pacer = pacer or Pacer()
    results = []
    for b in brands:
        if not b.get("active", True):
            continue
        rec = snapshot_brand(b, fetch, pacer)
        (day_dir / f"{b['slug']}.json").write_text(json.dumps(rec, indent=1, sort_keys=True))
        results.append(rec)
    summary = [{"slug": r["slug"], "status": r["status"], "reason": r["reason"], "count": len(r["products"]), "fetched_at": r["fetched_at"]} for r in results]
    (day_dir / "_summary.json").write_text(json.dumps(summary, indent=1))
    return results


# ---------- comparing ----------

def load(out_dir: Path, slug: str, date: str) -> dict | None:
    p = out_dir / date / f"{slug}.json"
    return json.loads(p.read_text()) if p.exists() else None


def dates_for(out_dir: Path, slug: str) -> list[str]:
    return sorted(d.name for d in out_dir.iterdir() if d.is_dir() and (d / f"{slug}.json").exists())


def diff(a: dict | None, b: dict | None) -> dict:
    """Compare two daily records. Refuses across a gap or a suspicious jump."""
    if a is None or b is None:
        return {"comparable": False, "why": "missing day"}
    if a["status"] != "ok" or b["status"] != "ok":
        return {"comparable": False, "why": f"gap ({a['status']} -> {b['status']}); a gap is not zero"}
    na, nb = len(a["products"]), len(b["products"])
    if na and nb and (nb / na >= HOLD_RATIO or na / nb >= HOLD_RATIO):
        return {"comparable": False, "why": f"count {na} -> {nb}; held as a likely parse error or reset"}
    pa = {p["handle"]: p for p in a["products"]}
    pb = {p["handle"]: p for p in b["products"]}
    new = sorted(set(pb) - set(pa))
    gone = sorted(set(pa) - set(pb))
    price_changes, new_variants, availability = [], [], []
    for h in sorted(set(pa) & set(pb)):
        va = {v["id"]: v for v in pa[h]["variants"]}
        vb = {v["id"]: v for v in pb[h]["variants"]}
        for vid in sorted(set(vb) - set(va)):
            new_variants.append({"handle": h, "variant": vb[vid]["title"]})
        for vid in sorted(set(va) & set(vb)):
            if va[vid]["price"] != vb[vid]["price"] or va[vid]["compare_at_price"] != vb[vid]["compare_at_price"]:
                price_changes.append({"handle": h, "variant": vb[vid]["title"], "from": va[vid]["price"], "to": vb[vid]["price"],
                                      "compare_from": va[vid]["compare_at_price"], "compare_to": vb[vid]["compare_at_price"]})
            if va[vid]["available"] != vb[vid]["available"]:
                availability.append({"handle": h, "variant": vb[vid]["title"], "available": vb[vid]["available"]})
    return {"comparable": True, "from": a["fetched_at"], "to": b["fetched_at"], "count_from": na, "count_to": nb,
            "new_products": new, "removed_products": gone, "price_changes": price_changes,
            "new_variants": new_variants, "availability_changes": availability}


# ---------- CLI ----------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--brands", required=True, type=Path)
    r.add_argument("--out", required=True, type=Path)
    d = sub.add_parser("diff")
    d.add_argument("--out", required=True, type=Path)
    d.add_argument("--brand", required=True)
    d.add_argument("dates", nargs="*")
    a = ap.parse_args(argv)
    if a.cmd == "run":
        for rec in run(a.brands, a.out):
            print(f"{rec['slug']:<20} {rec['status']:<4} {rec['reason']}")
        return 0
    ds = a.dates or dates_for(a.out, a.brand)[-2:]
    if len(ds) != 2:
        print("need two dates", file=sys.stderr)
        return 2
    print(json.dumps(diff(load(a.out, a.brand, ds[0]), load(a.out, a.brand, ds[1])), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
