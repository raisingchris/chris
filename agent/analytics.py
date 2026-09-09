"""Google Analytics 4 and Search Console, read-only, through Chris's body.

Auth comes from :mod:`agent.google_auth` (keyless). Chris sees data and nothing
else: no property owner, no project, no service account, no token. The archive
gets ``{kind, api, status_code}`` per call. Non-2xx answers come back as
``{"error": …}`` rather than raising, with anything token-shaped scrubbed.
"""

from __future__ import annotations

from typing import Any, Callable
from urllib.parse import quote

import httpx

from agent.google_auth import GoogleAuthError, scrub

GA4_URL = "https://analyticsdata.googleapis.com/v1beta/properties/{prop}:runReport"
GSC_QUERY_URL = "https://searchconsole.googleapis.com/webmasters/v3/sites/{site}/searchAnalytics/query"
GSC_INSPECT_URL = "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"
SCOPE_GA4 = "https://www.googleapis.com/auth/analytics.readonly"
SCOPE_GSC_RO = "https://www.googleapis.com/auth/webmasters.readonly"
SCOPE_GSC = "https://www.googleapis.com/auth/webmasters"
TIMEOUT_S = 60


def _num(v: Any) -> Any:
    """GA4 returns every metric as a string; give back int/float where it parses."""
    if not isinstance(v, str):
        return v
    try:
        return int(v)
    except ValueError:
        try:
            return float(v)
        except ValueError:
            return v


class Analytics:
    def __init__(self, google, ga4_property: str, gsc_site: str, archive_append: Callable[[str, dict], Any],
                 http: httpx.Client | None = None):
        self._google = google
        self.ga4_property = str(ga4_property or "").strip()
        self.gsc_site = str(gsc_site or "").strip()
        self._archive = archive_append
        self._http = http or httpx.Client(timeout=TIMEOUT_S)

    # --- plumbing ---------------------------------------------------------

    def _post(self, api: str, url: str, body: dict, scopes: list[str]) -> tuple[dict | None, dict | None]:
        """Returns (ok_body, None) or (None, error_dict). Archives status only."""
        try:
            token = self._google.access_token(scopes)
        except GoogleAuthError as exc:
            self._archive("analytics", {"kind": "analytics", "api": api, "status_code": 0})
            return None, {"error": f"Google sign-in failed: {scrub(exc)}", "api": api}
        r = self._http.post(url, json=body, headers={"Authorization": f"Bearer {token}"})
        self._archive("analytics", {"kind": "analytics", "api": api, "status_code": r.status_code})
        try:
            data = r.json()
        except ValueError:
            data = None
        if not 200 <= r.status_code < 300:
            msg = None
            if isinstance(data, dict) and isinstance(data.get("error"), dict):
                msg = data["error"].get("message")
            elif data is None:
                msg = r.text[:500]
            return None, {"error": scrub(msg or f"Google returned HTTP {r.status_code}"),
                          "status_code": r.status_code, "api": api}
        return (data if isinstance(data, dict) else {"result": data}), None

    # --- GA4 --------------------------------------------------------------

    def ga4_report(self, dimensions: list[str], metrics: list[str], start: str, end: str, limit: int = 50,
                   filters: dict | None = None) -> dict:
        if not self.ga4_property:
            return {"error": "GA4 property is not configured; ask your parents.", "api": "ga4"}
        body: dict[str, Any] = {
            "dateRanges": [{"startDate": start, "endDate": end}],
            "dimensions": [{"name": d} for d in dimensions],
            "metrics": [{"name": m} for m in metrics],
            "limit": int(limit),
        }
        if filters:
            body["dimensionFilter"] = filters
        data, err = self._post("ga4", GA4_URL.format(prop=self.ga4_property), body, [SCOPE_GA4])
        if err:
            return err
        dim_names = [h.get("name") for h in data.get("dimensionHeaders") or []]
        met_names = [h.get("name") for h in data.get("metricHeaders") or []]
        rows = []
        for row in data.get("rows") or []:
            out: dict[str, Any] = {}
            for name, cell in zip(dim_names, row.get("dimensionValues") or []):
                out[name] = cell.get("value")
            for name, cell in zip(met_names, row.get("metricValues") or []):
                out[name] = _num(cell.get("value"))
            rows.append(out)
        return {"api": "ga4", "start": start, "end": end, "rows": rows, "row_count": data.get("rowCount", len(rows))}

    # --- Search Console ---------------------------------------------------

    def gsc_query(self, start: str, end: str, dimensions: list[str] | None = None, row_limit: int = 50,
                  filters: list[dict] | None = None) -> dict:
        if not self.gsc_site:
            return {"error": "Search Console site is not configured; ask your parents.", "api": "gsc"}
        dims = list(dimensions) if dimensions else ["query"]
        body: dict[str, Any] = {"startDate": start, "endDate": end, "dimensions": dims, "rowLimit": int(row_limit)}
        if filters:
            body["dimensionFilterGroups"] = [{"filters": filters}]
        url = GSC_QUERY_URL.format(site=quote(self.gsc_site, safe=""))
        data, err = self._post("gsc", url, body, [SCOPE_GSC_RO])
        if err:
            return err
        rows = []
        for row in data.get("rows") or []:
            keys = row.get("keys") or []
            out: dict[str, Any] = {"keys": keys}
            for name, key in zip(dims, keys):
                out[name] = key
            for m in ("clicks", "impressions", "ctr", "position"):
                out[m] = row.get(m)
            rows.append(out)
        return {"api": "gsc", "start": start, "end": end, "dimensions": dims, "rows": rows, "row_count": len(rows)}

    def gsc_inspect(self, url: str) -> dict:
        if not self.gsc_site:
            return {"error": "Search Console site is not configured; ask your parents.", "api": "gsc_inspect"}
        body = {"inspectionUrl": url, "siteUrl": self.gsc_site}
        data, err = self._post("gsc_inspect", GSC_INSPECT_URL, body, [SCOPE_GSC])
        if err:
            return err
        result = data.get("inspectionResult") or {}
        idx = result.get("indexStatusResult") or {}
        return {
            "api": "gsc_inspect", "url": url,
            "verdict": idx.get("verdict"), "coverage_state": idx.get("coverageState"),
            "indexing_state": idx.get("indexingState"), "robots_txt_state": idx.get("robotsTxtState"),
            "page_fetch_state": idx.get("pageFetchState"), "last_crawl_time": idx.get("lastCrawlTime"),
            "google_canonical": idx.get("googleCanonical"), "user_canonical": idx.get("userCanonical"),
            "crawled_as": idx.get("crawledAs"),
            "mobile_usability": (result.get("mobileUsabilityResult") or {}).get("verdict"),
            "rich_results": (result.get("richResultsResult") or {}).get("verdict"),
            "inspection_link": result.get("inspectionResultLink"),
        }
