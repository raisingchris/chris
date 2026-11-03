#!/usr/bin/env python3
"""Tell Bing and the other IndexNow engines which pages changed since yesterday.

    python3 indexnow.py <host> <key> [--dry-run]

Reads the live sitemap, so it only ever announces what is really published. It never
submits the whole site: too many at once, or nearly everything "changed", sends nothing.
Pages that aren't a plain 200, say noindex, or point their canonical elsewhere are left out.
"""
import datetime as dt
import json
import re
import sys
import urllib.error
import urllib.request
from urllib.parse import urljoin, urlparse

UA = {"User-Agent": "indexnow-ping/1.0"}
ENGINES = ("https://api.indexnow.org/indexnow", "https://www.bing.com/indexnow")
WINDOW = dt.timedelta(hours=26)
CEILING = 500


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None


def fetch(url, follow=True):
    opener = urllib.request.build_opener() if follow else urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(urllib.request.Request(url, headers=UA), timeout=30) as r:
            return r.status, r.headers, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.headers, ""


def when(text):
    """A bare date could mean any time that day, so it counts as the end of the day."""
    text = (text or "").strip()
    if not text:
        return None
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
            return dt.datetime.fromisoformat(text + "T23:59:59+00:00")
        parsed = dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.timezone.utc)
    except ValueError:
        return None


def sitemap_pages(host):
    queue, seen, pages = [f"https://{host}/sitemap.xml"], set(), {}
    while queue:
        url = queue.pop()
        if url in seen or len(seen) >= 50:
            continue
        seen.add(url)
        status, _, body = fetch(url)
        if status != 200:
            sys.exit(f"{url} answered {status}")
        queue += re.findall(r"<sitemap>\s*<loc>([^<]+)</loc>", body)
        for block in re.findall(r"<url>(.*?)</url>", body, re.S):
            loc = re.search(r"<loc>([^<]+)</loc>", block)
            mod = re.search(r"<lastmod>([^<]+)</lastmod>", block)
            if loc and urlparse(loc.group(1)).netloc == host:
                pages[loc.group(1)] = when(mod.group(1)) if mod else None
    if not pages:
        sys.exit("the sitemap lists no pages on this host")
    return pages


def indexable(url):
    status, headers, html = fetch(url, follow=False)
    if status != 200 or re.search(r"\b(noindex|none)\b", headers.get("X-Robots-Tag") or "", re.I):
        return False
    head = html.split("</head>")[0]
    for tag in re.findall(r"<meta\b[^>]*>", head, re.I):
        if re.search(r"name=[\"'](robots|bingbot)[\"']", tag, re.I) and re.search(r"\b(noindex|none)\b", tag, re.I):
            return False
    for tag in re.findall(r"<link\b[^>]*>", head, re.I):
        href = re.search(r"href=[\"']([^\"']+)", tag)
        if re.search(r"rel=[\"']canonical[\"']", tag, re.I) and href:
            if urljoin(url, href.group(1)).rstrip("/") != url.rstrip("/"):
                return False
    return True


def main():
    host, key = sys.argv[1], sys.argv[2]
    dry = "--dry-run" in sys.argv
    status, _, body = fetch(f"https://{host}/{key}.txt")
    if status != 200 or body.strip() != key:
        sys.exit(f"key file answered {status} and does not match")

    now = dt.datetime.now(dt.timezone.utc)
    pages = sitemap_pages(host)
    changed = [u for u, at in pages.items() if at and now - WINDOW < at <= now + dt.timedelta(days=1)]
    print(f"{len(pages)} pages, {len(changed)} changed")
    if len(changed) > CEILING:
        sys.exit(f"{len(changed)} changed is over the ceiling of {CEILING}; sending nothing")
    if len(pages) >= 20 and len(changed) >= 0.9 * len(pages):
        sys.exit("nearly every page changed, so lastmod looks wrong; sending nothing")

    urls = [u for u in changed if indexable(u)]
    print(f"{len(urls)} to send")
    if dry or not urls:
        return
    body = json.dumps({"host": host, "key": key, "keyLocation": f"https://{host}/{key}.txt", "urlList": urls}).encode()
    accepted = False
    for engine in ENGINES:
        req = urllib.request.Request(engine, data=body, headers={**UA, "Content-Type": "application/json; charset=utf-8"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                code = r.status
        except urllib.error.HTTPError as e:
            code = e.code
        except OSError as e:
            code = f"error {e}"
        print(engine, code)
        accepted = accepted or code in (200, 202)
    if not accepted:
        sys.exit("no engine accepted the list")


if __name__ == "__main__":
    main()
