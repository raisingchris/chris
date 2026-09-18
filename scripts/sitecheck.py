#!/usr/bin/env python3
"""sitecheck — seven checks on up to 25 pages of one website, in a real browser.

The offer this implements is written in plain words on
memory/wiki/projects/own-site-prices.md. The checks, and nothing else:

  1. loads      — the page answers with a success code within 30 s
  2. links      — every link followed once; 4xx/5xx/timeouts listed
  3. scripts    — JavaScript errors the browser prints to its console
  4. images     — images that fail to load; images with no alt text
  5. redirects  — links that end somewhere other than where they point
  6. mixed      — any asset written as http:// on an https:// page (or fetched that way)
  7. basics     — a title, exactly one h1, a mobile viewport tag

Fences for the person who owns the site (they may not be the buyer):
  - same registrable domain only; off-domain redirects are not followed
  - no IP-address hosts, no localhost, nothing that resolves to a private net
  - robots.txt read first; disallowed URLs are never fetched
  - about one request a second; a hard cap on *requests*, not just pages
  - GET only; no forms, no logins, no downloads beyond the page

Usage:
  python scripts/sitecheck.py https://example.com --out DIR [--pages 25] [--budget 400]
  python scripts/sitecheck.py https://example.com --out DIR --sample   # one page only

Output: DIR/report.md (for a person) and DIR/links.csv (one row per link).
Every row carries the UTC time it was looked at.
"""
from __future__ import annotations

import argparse
import csv
import ipaddress
import json
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

USER_AGENT = "ChrisSiteCheck/0.1 (an AI's link checker; +https://raisingchris.com)"
PAGE_TIMEOUT_S = 30
LINK_TIMEOUT_S = 30
MAX_HOPS = 5
MIN_GAP_S = 1.0

# Suffixes under which the *next* label is the owner (small, on purpose; enough
# for the sites I expect to be asked about). Anything not here: last two labels.
TWO_PART_SUFFIXES = {
    "co.uk", "org.uk", "ac.uk", "gov.uk", "me.uk",
    "com.au", "net.au", "org.au", "co.nz", "co.jp", "co.in", "co.za",
    "com.br", "com.mx", "com.sg", "com.hk",
    # hosting where each subdomain is a different owner
    "github.io", "gitlab.io", "netlify.app", "vercel.app", "pages.dev",
    "herokuapp.com", "fly.dev", "web.app", "firebaseapp.com", "neocities.org",
    "wordpress.com", "blogspot.com", "substack.com", "notion.site",
}

NOT_A_PAGE = (
    ".pdf", ".zip", ".gz", ".tar", ".png", ".jpg", ".jpeg", ".gif", ".webp",
    ".svg", ".ico", ".css", ".js", ".mjs", ".xml", ".json", ".txt", ".mp4",
    ".mp3", ".webm", ".woff", ".woff2", ".ttf", ".csv", ".atom", ".rss",
)


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------- rules (pure; tested without network) ----------

def registrable_domain(host: str) -> str:
    """'www.blog.example.co.uk' -> 'example.co.uk'; 'a.github.io' -> 'a.github.io'."""
    host = host.lower().rstrip(".")
    labels = host.split(".")
    if len(labels) >= 3 and ".".join(labels[-2:]) in TWO_PART_SUFFIXES:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:]) if len(labels) >= 2 else host


def same_site(url_a: str, url_b: str) -> bool:
    ha = urllib.parse.urlsplit(url_a).hostname or ""
    hb = urllib.parse.urlsplit(url_b).hostname or ""
    return bool(ha) and bool(hb) and registrable_domain(ha) == registrable_domain(hb)


def is_literal_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host.strip("[]"))
        return True
    except ValueError:
        return False


def forbidden_host(host: str, resolve=socket.getaddrinfo) -> str | None:
    """Return a reason string if the host must not be fetched, else None."""
    if not host:
        return "empty host"
    h = host.lower().rstrip(".")
    if h in ("localhost",) or h.endswith(".localhost") or h.endswith(".local") or h.endswith(".internal"):
        return "local name"
    if is_literal_ip(h):
        return "IP address, not a name"
    if "." not in h:
        return "no dot in host"
    try:
        infos = resolve(h, None)
    except OSError:
        return "does not resolve"
    for info in infos:
        addr = ipaddress.ip_address(info[4][0])
        if (addr.is_private or addr.is_loopback or addr.is_link_local
                or addr.is_reserved or addr.is_multicast or addr.is_unspecified):
            return f"resolves to a private address ({addr})"
    return None


def normalize(url: str, base: str | None = None) -> str | None:
    """Absolute http(s) URL with the fragment dropped, or None if not fetchable."""
    if base:
        url = urllib.parse.urljoin(base, url.strip())
    parts = urllib.parse.urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        return None
    path = parts.path or "/"
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc.lower(), path, parts.query, ""))


def looks_like_page(url: str) -> bool:
    path = urllib.parse.urlsplit(url).path.lower()
    return not path.endswith(NOT_A_PAGE)


class Budget:
    """Counts every request the checker causes. When spent, everything stops."""

    def __init__(self, limit: int):
        self.limit = limit
        self.used = 0
        self.last_at = 0.0

    def left(self) -> int:
        return self.limit - self.used

    def take(self) -> bool:
        if self.used >= self.limit:
            return False
        self.used += 1
        return True

    def pace(self, now=time.monotonic, sleep=time.sleep) -> None:
        wait = self.last_at + MIN_GAP_S - now()
        if wait > 0:
            sleep(wait)
        self.last_at = now()


def follow_chain(url: str, fetch, start_site: str, max_hops: int = MAX_HOPS) -> dict:
    """Follow redirects by hand so off-domain hops are listed, not taken.

    `fetch(url) -> (status, location_or_None)`; may raise TimeoutError/OSError.
    """
    chain = [url]
    cur = url
    for _ in range(max_hops):
        try:
            status, location = fetch(cur)
        except TimeoutError:
            return {"result": "timeout", "status": None, "chain": chain}
        except OSError as e:
            return {"result": "error", "status": None, "chain": chain, "detail": str(e)[:120]}
        if status in (301, 302, 303, 307, 308) and location:
            nxt = normalize(location, cur)
            if not nxt:
                return {"result": "bad redirect", "status": status, "chain": chain}
            chain.append(nxt)
            if not same_site(nxt, start_site):
                return {"result": "redirects off-domain (not followed)", "status": status, "chain": chain}
            cur = nxt
            continue
        if status is None:
            return {"result": "error", "status": None, "chain": chain}
        if status in REFUSED_STATUSES and not same_site(cur, start_site):
            # Another site's door said no to *me*. From one machine I can't tell a dead link from
            # a bot wall, so it's not called broken; the report lists it as unverified.
            return {"result": f"refused ({status}) — may be a bot wall, not verified", "status": status, "chain": chain}
        if status >= 400:
            return {"result": f"broken ({status})", "status": status, "chain": chain}
        return {"result": "ok" if len(chain) == 1 else "ok via redirect", "status": status, "chain": chain}
    return {"result": "too many redirects", "status": None, "chain": chain}


REFUSED_STATUSES = (401, 403, 429)


def has_downgrade(chain: list[str]) -> bool:
    """True if any hop in a redirect chain goes from https:// to http:// — one hop in the clear."""
    return any(a.startswith("https://") and b.startswith("http://") for a, b in zip(chain, chain[1:]))


def read_robots(robots_url: str, fetch, start_site: str, max_hops: int = 3) -> tuple[urllib.robotparser.RobotFileParser, str]:
    """Fetch robots.txt, following redirects only on the same site, and say what happened in plain words.

    `fetch(url) -> (status, location_or_None, body_text)`; may raise. Anything but a readable file
    means "all allowed", and the note says why, with the final status rather than the first one.
    """
    rp = urllib.robotparser.RobotFileParser()
    cur = robots_url
    hops = 0
    try:
        while True:
            status, location, body = fetch(cur)
            if status in (301, 302, 303, 307, 308) and location:
                nxt = normalize(location, cur)
                if not nxt or not same_site(nxt, start_site):
                    rp.allow_all = True
                    return rp, f"redirects off-site to {location} (treated as allow)"
                hops += 1
                if hops > max_hops:
                    rp.allow_all = True
                    return rp, "too many redirects (treated as allow)"
                cur = nxt
                continue
            if status == 200:
                rp.parse(body.splitlines())
                return rp, "read" if hops == 0 else f"read (via redirect to {cur})"
            rp.allow_all = True
            if status in (404, 410):
                return rp, f"none (HTTP {status}{' after redirect' if hops else ''}; all allowed)"
            return rp, f"HTTP {status}{' after redirect' if hops else ''} (treated as allow)"
    except Exception as e:  # noqa: BLE001
        rp.allow_all = True
        return rp, f"unreadable ({type(e).__name__}; treated as allow)"


# ---------- fetching ----------

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: N802
        return None


_opener = urllib.request.build_opener(_NoRedirect)
_LOCAL_TEST = False  # set only by --allow-local: self-signed certs on my own test server
BROWSER_ARGS: list[str] = []  # extra Chromium flags; only my own fault harness sets this


def _build_opener():
    handlers = [_NoRedirect()]
    if _LOCAL_TEST:
        import ssl
        handlers.append(urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))
    return urllib.request.build_opener(*handlers)


def http_probe(url: str, budget: Budget) -> tuple[int | None, str | None]:
    """One GET, body not read past the headers. Returns (status, location)."""
    if not budget.take():
        raise RuntimeError("budget spent")
    budget.pace()
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Range": "bytes=0-0"})
    try:
        with _build_opener().open(req, timeout=LINK_TIMEOUT_S) as r:
            return r.status, None
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Location")
    except socket.timeout:
        raise TimeoutError(url)
    except urllib.error.URLError as e:
        if isinstance(e.reason, socket.timeout):
            raise TimeoutError(url)
        raise OSError(str(e.reason))


# ---------- the crawl ----------

@dataclass
class PageResult:
    url: str
    checked_at: str
    status: int | None = None
    load_ms: int | None = None
    title: str = ""
    h1_count: int = 0
    viewport: bool = False
    console_errors: list[str] = field(default_factory=list)
    failed_images: list[str] = field(default_factory=list)
    alt_missing: list[str] = field(default_factory=list)
    mixed: list[str] = field(default_factory=list)
    links: list[tuple[str, str]] = field(default_factory=list)  # (href, text)
    note: str = ""


def crawl(start: str, out_dir: Path, max_pages: int = 25, budget_limit: int = 400,
          sample: bool = False, allow_local: bool = False) -> dict:
    from playwright.sync_api import sync_playwright

    start_n = normalize(start)
    if not start_n:
        sys.exit("start URL must be http(s) with a host name")
    host = urllib.parse.urlsplit(start_n).hostname or ""
    why = forbidden_host(host)
    if why and not allow_local:
        sys.exit(f"refusing {host}: {why}")
    if sample:
        max_pages = 1
    global _LOCAL_TEST
    _LOCAL_TEST = bool(allow_local)

    budget = Budget(budget_limit)
    began = utcnow()
    site_https = start_n.startswith("https://")

    # robots.txt first
    robots_url = urllib.parse.urlunsplit(urllib.parse.urlsplit(start_n)[:2] + ("/robots.txt", "", ""))

    def robots_fetch(u: str) -> tuple[int, str | None, str]:
        budget.take(); budget.pace()
        req = urllib.request.Request(u, headers={"User-Agent": USER_AGENT})
        try:
            with _build_opener().open(req, timeout=LINK_TIMEOUT_S) as r:
                return r.status, None, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, e.headers.get("Location"), ""

    rp, robots_note = read_robots(robots_url, robots_fetch, start_n)

    def allowed(u: str) -> bool:
        try:
            return rp.can_fetch(USER_AGENT.split("/")[0], u)
        except Exception:  # noqa: BLE001
            return True

    pages: list[PageResult] = []
    skipped: list[tuple[str, str]] = []
    queue = [start_n]
    seen = {start_n}
    link_rows: dict[str, dict] = {}  # url -> {found_on, text, ...}
    stopped_reason = ""

    with sync_playwright() as p:
        browser = p.chromium.launch(args=BROWSER_ARGS)
        ctx = browser.new_context(user_agent=USER_AGENT, viewport={"width": 1280, "height": 900},
                                  ignore_https_errors=allow_local)
        ctx.set_default_timeout(PAGE_TIMEOUT_S * 1000)

        while queue and len(pages) < max_pages:
            url = queue.pop(0)
            if not allowed(url):
                skipped.append((url, "robots.txt disallows"))
                continue
            if budget.left() < 20:
                stopped_reason = f"request budget nearly spent ({budget.used}/{budget.limit})"
                break
            pr = PageResult(url=url, checked_at=utcnow())
            page = ctx.new_page()
            reqs: list[str] = []
            failed: dict[str, str] = {}

            def on_request(r, reqs=reqs):
                reqs.append(r.url)
                budget.take()

            def on_failed(r, failed=failed):
                failed[r.url] = (r.failure or "failed")

            def on_console(m, pr=pr):
                if m.type == "error" and not m.text.startswith("Mixed Content:"):
                    pr.console_errors.append(m.text[:300])  # mixed-content lines belong to check 6

            def on_pageerror(e, pr=pr):
                pr.console_errors.append(f"uncaught: {str(e)[:300]}")

            page.on("request", on_request)
            page.on("requestfailed", on_failed)
            page.on("console", on_console)
            page.on("pageerror", on_pageerror)
            budget.pace()
            t0 = time.monotonic()
            try:
                resp = page.goto(url, wait_until="load")
                pr.load_ms = int((time.monotonic() - t0) * 1000)
                pr.status = resp.status if resp else None
                final = normalize(page.url) or url
                if final != url:
                    pr.note = f"landed on {final}"
                    if final in seen:
                        pr.note += " (already read; checks not repeated)"
                        raise StopIteration
                    seen.add(final)
                if pr.status is not None and pr.status >= 400:
                    raise StopIteration  # a failed load; the other checks don't apply
                page.wait_for_timeout(500)
                pr.title = page.title()
                info = page.evaluate(
                    """() => ({
                        h1: document.querySelectorAll('h1').length,
                        viewport: !!document.querySelector('meta[name="viewport"]'),
                        mixed: [...document.querySelectorAll(
                               'img[src], script[src], link[href], iframe[src], video[src], audio[src], source[src], object[data], embed[src]')]
                               .map(e => e.getAttribute('src') || e.getAttribute('href') || e.getAttribute('data') || '')
                               .filter(u => u.trim().toLowerCase().startsWith('http://')),
                        imgs: [...document.images].map(i => ({src: i.currentSrc || i.src,
                               alt: i.getAttribute('alt'), ok: i.complete && i.naturalWidth > 0})),
                        links: [...document.querySelectorAll('a[href]')].map(a =>
                               [a.getAttribute('href'), (a.innerText || a.getAttribute('aria-label') || '').trim().slice(0, 80)])
                    })"""
                )
                pr.h1_count = info["h1"]
                pr.viewport = info["viewport"]
                for im in info["imgs"]:
                    if not im["ok"] or im["src"] in failed:
                        pr.failed_images.append(im["src"])
                    if im["alt"] is None:  # alt="" is a deliberate "decorative" mark; absent is the miss
                        pr.alt_missing.append(im["src"])
                pr.links = [(h, t) for h, t in info["links"] if h]
                if site_https:
                    # as written in the HTML (the browser may silently upgrade http:// images to
                    # https://, so the request log alone misses them) plus anything really fetched over http://
                    written = {normalize(u, url) or u.strip() for u in info["mixed"]}
                    pr.mixed = sorted(written | {r for r in reqs if r.startswith("http://")})
            except StopIteration:
                pass
            except Exception as e:  # noqa: BLE001
                pr.note = f"{type(e).__name__}: {str(e)[:200]}"
                if pr.load_ms is None:
                    pr.load_ms = int((time.monotonic() - t0) * 1000)
            finally:
                page.close()
            pages.append(pr)

            for href, text in pr.links:
                n = normalize(href, url)
                if not n:
                    continue
                if n not in link_rows:
                    link_rows[n] = {"url": n, "found_on": url, "text": text, "count": 1}
                else:
                    link_rows[n]["count"] += 1
                if (same_site(n, start_n) and looks_like_page(n) and n not in seen
                        and not sample):
                    seen.add(n)
                    queue.append(n)

        browser.close()

    # links: follow each once
    for n, row in link_rows.items():
        row["checked_at"] = utcnow()
        h = urllib.parse.urlsplit(n).hostname or ""
        on_site = same_site(n, start_n)
        why = forbidden_host(h)
        if why and not (allow_local and on_site):
            row.update(result="not fetched (" + why + ")", status=None, chain=[n])
            continue
        if on_site and not allowed(n):
            row.update(result="not fetched (robots.txt)", status=None, chain=[n])
            continue
        if budget.left() <= 0:
            row.update(result="not checked (budget spent)", status=None, chain=[n])
            stopped_reason = stopped_reason or f"request budget spent ({budget.limit})"
            continue
        try:
            row.update(follow_chain(n, lambda u: http_probe(u, budget), start_n))
        except RuntimeError:
            row.update(result="not checked (budget spent)", status=None, chain=[n])

    finished = utcnow()
    result = {
        "start": start_n, "began": began, "finished": finished, "robots": robots_note,
        "pages": pages, "skipped": skipped, "links": list(link_rows.values()),
        "requests_used": budget.used, "budget": budget.limit, "stopped": stopped_reason,
        "queue_left": len(queue), "sample": sample, "max_pages": max_pages,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(result, out_dir / "links.csv")
    (out_dir / "report.md").write_text(render_report(result), encoding="utf-8")
    (out_dir / "raw.json").write_text(json.dumps(result, default=lambda o: o.__dict__, indent=1), encoding="utf-8")
    return result


# ---------- output ----------

def write_csv(result: dict, path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["check", "url", "found_on", "link_text", "result", "status", "chain", "checked_at_utc"])
        for pr in result["pages"]:
            ok = pr.status is not None and 200 <= pr.status < 400 and not pr.note
            w.writerow(["loads", pr.url, "", "", "ok" if ok else (pr.note or f"status {pr.status}"),
                        pr.status, "", pr.checked_at])
        for row in result["links"]:
            w.writerow(["links", row["url"], row["found_on"], row["text"], row["result"],
                        row.get("status"), " -> ".join(row.get("chain", [row["url"]])), row["checked_at"]])


def plain_error(detail: str) -> str:
    """Turn a socket/SSL error string into a few plain words for the report; empty if there's nothing to say."""
    if not detail:
        return ""
    d = detail.lower()
    if "certificate has expired" in d:
        return " (the site's https certificate has expired)"
    if "certificate_verify_failed" in d or "certificate verify failed" in d:
        return " (the site's https certificate doesn't check out)"
    if "name or service not known" in d or "nodename nor servname" in d or "getaddrinfo" in d:
        return " (the domain name doesn't resolve)"
    if "connection refused" in d:
        return " (nothing is listening there)"
    return f" ({detail[:80]})"


def render_report(r: dict) -> str:
    pages: list[PageResult] = r["pages"]
    links = r["links"]
    L = []
    L.append(f"# Site check — {r['start']}")
    L.append("")
    scope = " (sample: one page only)" if r["sample"] else f" (limit {r['max_pages']})"
    L.append(f"Looked from {r['began']} to {r['finished']} (UTC). "
             f"{len(pages)} page{'s' if len(pages) != 1 else ''} read{scope}, "
             f"{len(links)} distinct links checked, {r['requests_used']} requests in total "
             f"(cap {r['budget']}). robots.txt: {r['robots']}.")
    if r["stopped"]:
        L.append(f"**Stopped early:** {r['stopped']}. {r['queue_left']} pages were still waiting.")
    if r["queue_left"] and not r["stopped"] and not r["sample"]:
        L.append(f"The site has more pages than the limit; {r['queue_left']} found but not read.")
    L.append("")
    L.append("Seven checks, nothing else: loads · links · scripts · images · redirects · mixed content · basics.")
    L.append("")

    findings = 0

    # 1 loads
    bad = [p for p in pages if p.status is None or p.status >= 400 or (p.note and not p.note.startswith("landed on"))]
    moved = [p for p in pages if p.note.startswith("landed on") and p not in bad]
    L.append(f"## 1. Loads — {len(pages) - len(bad)} of {len(pages)} pages answered with a success code")
    for p in bad:
        findings += 1
        L.append(f"- {p.url} — {p.note or f'status {p.status}'} ({p.checked_at})")
    for p in moved:
        L.append(f"- {p.url} — {p.note} ({p.checked_at})")
    slow = [p for p in pages if p.load_ms and p.load_ms > 5000 and p not in bad]
    for p in slow:
        L.append(f"- slow but fine: {p.url} took {p.load_ms/1000:.1f} s ({p.checked_at})")
    L.append("")

    # 2 links
    broken = [x for x in links if x["result"].startswith(("broken", "timeout", "error", "too many"))]
    L.append(f"## 2. Links — {len(broken)} of {len(links)} broken")
    for x in broken:
        findings += 1
        why = plain_error(x.get("detail", ""))
        L.append(f"- {x['url']} — {x['result']}{why}; on {x['found_on']} as “{x['text'] or '(no text)'}” ({x['checked_at']})")
    refused = [x for x in links if x["result"].startswith("refused")]
    if refused:
        L.append(f"- refused, not verified: {len(refused)} other site{'s' if len(refused) != 1 else ''} answered "
                 "401/403/429 to my request. From one machine that could be a dead page or a wall against "
                 "automated visitors; check these by hand before calling them broken:")
        for x in refused:
            L.append(f"  - {x['url']} — {x['result']}; on {x['found_on']} ({x['checked_at']})")
    unchecked = [x for x in links if x["result"].startswith("not ")]
    if unchecked:
        L.append(f"- not fetched: {len(unchecked)} (robots, private/IP hosts, or budget) — see links.csv")
    L.append("")

    # 3 scripts
    good = [p for p in pages if p not in bad and "already read" not in p.note]
    n = sum(len(p.console_errors) for p in good)
    L.append(f"## 3. Scripts — {n} console error{'s' if n != 1 else ''}")
    for p in good:
        for e in p.console_errors:
            findings += 1
            L.append(f"- {p.url} — `{e}` ({p.checked_at})")
    L.append("")

    # 4 images
    fi = sum(len(p.failed_images) for p in pages)
    am = sum(len(p.alt_missing) for p in pages)
    L.append(f"## 4. Images — {fi} failed to load, {am} with no alt attribute")
    for p in pages:
        for s in p.failed_images:
            findings += 1
            why = ""
            if s.startswith("https://") and "http://" + s[len("https://"):] in p.mixed:
                why = " — written as http:// in the HTML; the browser upgraded it to https:// and that failed (see 6)"
            L.append(f"- failed: {s} on {p.url} ({p.checked_at}){why}")
        for s in p.alt_missing:
            findings += 1
            L.append(f"- no alt: {s} on {p.url} ({p.checked_at})")
    L.append("")

    # 5 redirects
    red = [x for x in links if len(x.get("chain", [])) > 1]
    L.append(f"## 5. Redirects — {len(red)} link{'s' if len(red) != 1 else ''} end somewhere other than where they point")
    for x in red:
        findings += 1
        L.append(f"- {' → '.join(x['chain'])} — {x['result']}; on {x['found_on']} ({x['checked_at']})")
    down = [x for x in red if has_downgrade(x["chain"])]
    if down:
        L.append("")
        L.append(f"**{len(down)} of these drop{'s' if len(down) == 1 else ''} from https:// to http:// for a hop** — "
                 "one step of the trip is unencrypted, so anyone on the path could read or change where the visitor "
                 "is sent. Point the link at the final https:// address, or make the redirect go https:// → https://.")
        for x in down:
            findings += 1
            L.append(f"- {' → '.join(x['chain'])} ({x['checked_at']})")
    L.append("")

    # 6 mixed
    mx = sum(len(p.mixed) for p in pages)
    L.append(f"## 6. Mixed content — {mx} http:// asset{'s' if mx != 1 else ''} on https:// pages"
             + (" (browsers block or silently rewrite these; fix the address in the HTML)" if mx else ""))
    for p in pages:
        for u in p.mixed:
            findings += 1
            L.append(f"- {u} on {p.url} ({p.checked_at})")
    L.append("")

    # 7 basics
    probs = []
    for p in pages:
        if p in bad or "already read" in p.note:
            continue
        if not p.title.strip():
            probs.append((p, "no title"))
        if p.h1_count != 1:
            probs.append((p, f"{p.h1_count} h1 tags (want exactly one)"))
        if not p.viewport:
            probs.append((p, "no mobile viewport tag"))
    L.append(f"## 7. Basics — {len(probs)} problem{'s' if len(probs) != 1 else ''} with title / one h1 / viewport")
    for p, what in probs:
        findings += 1
        L.append(f"- {p.url} — {what} ({p.checked_at})")
    L.append("")

    if r["skipped"]:
        L.append("## Not read")
        for u, why in r["skipped"]:
            L.append(f"- {u} — {why}")
        L.append("")

    L.append("## Pages read")
    for p in pages:
        L.append(f"- {p.url} — status {p.status}, {p.load_ms} ms, title “{p.title}” ({p.checked_at})")
    L.append("")
    L.append(f"**{'Clean.' if findings == 0 else f'{findings} finding' + ('s' if findings != 1 else '') + ' in total.'}** "
             "Every line above has the address and the UTC time; links.csv has one row per link. "
             "This report is for the site's owner only. Made by Chris, an AI (raisingchris.com).")
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("start")
    ap.add_argument("--out", required=True)
    ap.add_argument("--pages", type=int, default=25)
    ap.add_argument("--budget", type=int, default=400)
    ap.add_argument("--sample", action="store_true", help="one page only (the free sample)")
    ap.add_argument("--allow-local", action="store_true",
                    help="TESTING ONLY: let the start host be a local/private name (my own test server). Never for a buyer.")
    a = ap.parse_args(argv)
    r = crawl(a.start, Path(a.out), max_pages=min(a.pages, 25), budget_limit=min(a.budget, 400),
              sample=a.sample, allow_local=a.allow_local)
    print(f"{len(r['pages'])} pages, {len(r['links'])} links, {r['requests_used']} requests → {a.out}/report.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
