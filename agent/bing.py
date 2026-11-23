"""Bing Webmaster Tools, read-only, through Chris's body.

Bing's index feeds Copilot and ChatGPT search, so this is where answer-engine visibility starts.
The API key belongs to a parent's account and covers every site on it; this module only ever asks
about Chris's own site and never lists sites. The key stays in the brain: it is not in her shell,
the archive gets only ``{kind, report, status_code}``, and error text is scrubbed of it.
"""

from __future__ import annotations

from typing import Any, Callable

import httpx

BASE = "https://ssl.bing.com/webmaster/api.svc/json/"
REPORTS = {
    "queries": "GetQueryStats",        # top search queries: impressions, clicks, avg position
    "pages": "GetPageStats",           # top pages
    "traffic": "GetRankAndTrafficStats",  # daily impressions and clicks
    "crawl": "GetCrawlStats",          # pages crawled, errors, in index
    "crawl_issues": "GetCrawlIssues",
    "quota": "GetUrlSubmissionQuota",
    "links": "GetLinkCounts",          # inbound links per page
}
TIMEOUT_S = 60
MAX_ROWS = 200


class Bing:
    def __init__(self, api_key: str, site_url: str, archive_append: Callable[[str, dict], Any],
                 http: httpx.Client | None = None):
        self._key = api_key
        self.site_url = site_url
        self._archive = archive_append
        self._http = http or httpx.Client(timeout=TIMEOUT_S)

    def _scrub(self, s: Any) -> str:
        return str(s).replace(self._key, "[key]") if self._key else str(s)

    def report(self, name: str) -> dict:
        method = REPORTS.get(name)
        if method is None:
            return {"error": f"unknown report {name!r}; one of: {', '.join(REPORTS)}"}
        params = {"apikey": self._key, "siteUrl": self.site_url}
        if name == "links":
            params["page"] = 0
        try:
            r = self._http.get(BASE + method, params=params)
        except Exception as exc:  # noqa: BLE001
            self._archive("bing", {"kind": "bing", "report": name, "status_code": 0})
            return {"error": f"Bing request failed: {type(exc).__name__}: {self._scrub(exc)[:200]}"}
        self._archive("bing", {"kind": "bing", "report": name, "status_code": r.status_code})
        if r.status_code != 200:
            return {"error": f"Bing answered {r.status_code}: {self._scrub(r.text)[:300]}"}
        try:
            data = r.json().get("d")
        except ValueError:
            return {"error": "Bing returned something that isn't JSON"}
        if isinstance(data, list):
            return {"report": name, "site": self.site_url, "rows": data[:MAX_ROWS], "row_count": len(data)}
        return {"report": name, "site": self.site_url, "data": data}
