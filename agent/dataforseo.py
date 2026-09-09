"""DataForSEO proxy: live SEO data through Chris's body, on her parents' account.

The Basic-auth credential identifies her parents, so it lives only in this
process. It never reaches her shell, the tool result, or any archive record —
the archive gets ``{kind, endpoint, cost_usd, status_code}`` and nothing else.
Every call is metered against a weekly cap the same way the council is.
"""

from __future__ import annotations

import re
from typing import Any, Callable

import httpx

BASE_URL = "https://api.dataforseo.com/v3/"
ALLOWED_ROOTS = (
    "serp/", "keywords_data/", "dataforseo_labs/", "on_page/", "backlinks/",
    "domain_analytics/", "content_analysis/", "ai_optimization/", "appendix/user_data",
)
_ENDPOINT_RE = re.compile(r"^[a-z0-9_/]+$")
TIMEOUT_S = 60


class DataForSEOBudgetExceeded(RuntimeError):
    """Raised before any request when the weekly DataForSEO cap is spent."""


class DataForSEOEndpointError(ValueError):
    """The endpoint is not a path this proxy will forward."""


def validate_endpoint(endpoint: str) -> str:
    ep = str(endpoint or "").strip().lstrip("/")
    if not ep or not _ENDPOINT_RE.match(ep) or ".." in ep:
        raise DataForSEOEndpointError(
            f"endpoint {endpoint!r} is not a plain /v3/ path (lowercase letters, digits, '_' and '/' only)")
    if not ep.startswith(ALLOWED_ROOTS):
        raise DataForSEOEndpointError(
            f"endpoint {endpoint!r} is outside the allowed roots: {', '.join(ALLOWED_ROOTS)}")
    return ep


def sum_cost(body: Any) -> float:
    """DataForSEO reports ``cost`` at the top level; fall back to summing per-task costs."""
    if not isinstance(body, dict):
        return 0.0
    top = body.get("cost")
    if isinstance(top, (int, float)) and top > 0:
        return float(top)
    total = 0.0
    for task in body.get("tasks") or []:
        if isinstance(task, dict) and isinstance(task.get("cost"), (int, float)):
            total += float(task["cost"])
    return total


class DataForSEO:
    def __init__(self, auth_b64: str, meter, weekly_cap_usd: float,
                 archive_append: Callable[[str, dict], Any], http: httpx.Client | None = None):
        self._auth = auth_b64
        self.meter = meter
        self.weekly_cap_usd = float(weekly_cap_usd)
        self._archive = archive_append
        self._http = http or httpx.Client(base_url=BASE_URL, timeout=TIMEOUT_S)

    def call(self, endpoint: str, payload: list | dict) -> dict:
        ep = validate_endpoint(endpoint)
        if self.meter.exceeded(self.weekly_cap_usd):
            raise DataForSEOBudgetExceeded(
                f"DataForSEO has already spent ${self.meter.spent():.2f} this week; "
                f"the weekly cap is ${self.weekly_cap_usd:.2f}. It resets next week."
            )
        if isinstance(payload, dict):
            payload = [payload]
        r = self._http.post(BASE_URL + ep, json=payload,
                            headers={"Authorization": f"Basic {self._auth}", "Content-Type": "application/json"})
        try:
            body = r.json()
        except ValueError:
            body = {"raw": r.text[:2000]}
        cost = sum_cost(body)
        if cost > 0:
            self.meter.add_usd(cost, f"dataforseo: {ep}")
        self._archive("dataforseo", {"kind": "dataforseo", "endpoint": ep, "cost_usd": cost,
                                     "status_code": r.status_code})
        if not 200 <= r.status_code < 300:
            msg = body.get("status_message") if isinstance(body, dict) else None
            return {"error": msg or f"DataForSEO returned HTTP {r.status_code}", "status_code": r.status_code,
                    "endpoint": ep, "cost_usd": cost}
        if isinstance(body, dict):
            body["endpoint"] = ep
            return body
        return {"endpoint": ep, "result": body}
