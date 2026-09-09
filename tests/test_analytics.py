"""GA4 + Search Console: request shapes, row flattening, archive shape, scrubbed errors, and the tools."""

import json

import httpx
import pytest

from agent import tools
from agent.analytics import Analytics
from agent.google_auth import GoogleAuthError
from conftest import archive_text

TOKEN = "ya29.super-secret-sa-token"
SITE = "sc-domain:raisingchris.com"


def out_text(result: dict) -> str:
    return result["content"][0]["text"]


class FakeGoogle:
    def __init__(self, exc=None):
        self.scopes: list[list[str]] = []
        self.exc = exc

    def access_token(self, scopes):
        self.scopes.append(list(scopes))
        if self.exc:
            raise self.exc
        return TOKEN


class Recorder:
    def __init__(self, status=200, body=None, text=None):
        self.status, self.body, self.text = status, body, text
        self.requests: list[httpx.Request] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.text is not None:
            return httpx.Response(self.status, text=self.text)
        return httpx.Response(self.status, json=self.body)

    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self.handler))


@pytest.fixture
def archived():
    rows = []
    return rows, (lambda kind, data: rows.append((kind, data)) or f"archive:2026-09-09#{len(rows)}")


def make(rec: Recorder, archived, google=None, prop="553409810", site=SITE) -> Analytics:
    return Analytics(google or FakeGoogle(), prop, site, archived[1], http=rec.client())


GA4_BODY = {
    "dimensionHeaders": [{"name": "date"}, {"name": "pagePath"}],
    "metricHeaders": [{"name": "activeUsers", "type": "TYPE_INTEGER"},
                      {"name": "averageSessionDuration", "type": "TYPE_SECONDS"}],
    "rows": [
        {"dimensionValues": [{"value": "20260908"}, {"value": "/"}],
         "metricValues": [{"value": "12"}, {"value": "41.5"}]},
        {"dimensionValues": [{"value": "20260908"}, {"value": "/diary/"}],
         "metricValues": [{"value": "3"}, {"value": "7"}]},
    ],
    "rowCount": 2,
}


def test_ga4_request_shape_and_row_flattening(archived):
    rec = Recorder(body=GA4_BODY)
    g = FakeGoogle()
    out = make(rec, archived, g).ga4_report(["date", "pagePath"], ["activeUsers", "averageSessionDuration"],
                                            "7daysAgo", "today", limit=25)
    req = rec.requests[0]
    assert str(req.url) == "https://analyticsdata.googleapis.com/v1beta/properties/553409810:runReport"
    assert req.headers["Authorization"] == f"Bearer {TOKEN}"
    assert json.loads(req.content) == {
        "dateRanges": [{"startDate": "7daysAgo", "endDate": "today"}],
        "dimensions": [{"name": "date"}, {"name": "pagePath"}],
        "metrics": [{"name": "activeUsers"}, {"name": "averageSessionDuration"}],
        "limit": 25,
    }
    assert g.scopes == [["https://www.googleapis.com/auth/analytics.readonly"]]
    assert out["rows"] == [
        {"date": "20260908", "pagePath": "/", "activeUsers": 12, "averageSessionDuration": 41.5},
        {"date": "20260908", "pagePath": "/diary/", "activeUsers": 3, "averageSessionDuration": 7},
    ]
    assert out["row_count"] == 2 and out["api"] == "ga4"
    rows, _ = archived
    assert rows == [("analytics", {"kind": "analytics", "api": "ga4", "status_code": 200})]


def test_ga4_filters_passed_through(archived):
    rec = Recorder(body={"rows": []})
    flt = {"filter": {"fieldName": "pagePath", "stringFilter": {"value": "/diary/"}}}
    out = make(rec, archived).ga4_report(["date"], ["activeUsers"], "2026-09-01", "2026-09-08", filters=flt)
    assert json.loads(rec.requests[0].content)["dimensionFilter"] == flt
    assert out["rows"] == [] and out["row_count"] == 0


def test_gsc_query_encodes_site_and_flattens_rows(archived):
    rec = Recorder(body={"rows": [
        {"keys": ["raising chris", "https://raisingchris.com/"], "clicks": 4, "impressions": 90,
         "ctr": 0.0444, "position": 8.2},
    ]})
    g = FakeGoogle()
    out = make(rec, archived, g).gsc_query("2026-09-01", "2026-09-07", ["query", "page"], row_limit=10)
    req = rec.requests[0]
    assert str(req.url) == ("https://searchconsole.googleapis.com/webmasters/v3/sites/"
                            "sc-domain%3Araisingchris.com/searchAnalytics/query")
    assert req.headers["Authorization"] == f"Bearer {TOKEN}"
    assert json.loads(req.content) == {"startDate": "2026-09-01", "endDate": "2026-09-07",
                                       "dimensions": ["query", "page"], "rowLimit": 10}
    assert g.scopes == [["https://www.googleapis.com/auth/webmasters.readonly"]]
    assert out["rows"] == [{"keys": ["raising chris", "https://raisingchris.com/"], "query": "raising chris",
                            "page": "https://raisingchris.com/", "clicks": 4, "impressions": 90,
                            "ctr": 0.0444, "position": 8.2}]
    assert out["row_count"] == 1 and out["dimensions"] == ["query", "page"]
    assert archived[0] == [("analytics", {"kind": "analytics", "api": "gsc", "status_code": 200})]


def test_gsc_query_defaults_and_filters(archived):
    rec = Recorder(body={})
    flt = [{"dimension": "page", "operator": "contains", "expression": "/diary/"}]
    out = make(rec, archived).gsc_query("2026-09-01", "2026-09-07", filters=flt)
    body = json.loads(rec.requests[0].content)
    assert body["dimensions"] == ["query"] and body["rowLimit"] == 50
    assert body["dimensionFilterGroups"] == [{"filters": flt}]
    assert out["rows"] == []


def test_gsc_inspect_shape(archived):
    rec = Recorder(body={"inspectionResult": {
        "inspectionResultLink": "https://search.google.com/search-console/inspect?x",
        "indexStatusResult": {"verdict": "PASS", "coverageState": "Submitted and indexed",
                              "robotsTxtState": "ALLOWED", "indexingState": "INDEXING_ALLOWED",
                              "lastCrawlTime": "2026-09-08T03:00:00Z", "pageFetchState": "SUCCESSFUL",
                              "googleCanonical": "https://raisingchris.com/", "userCanonical": "https://raisingchris.com/",
                              "crawledAs": "MOBILE"},
        "mobileUsabilityResult": {"verdict": "PASS"},
    }})
    g = FakeGoogle()
    out = make(rec, archived, g).gsc_inspect("https://raisingchris.com/")
    req = rec.requests[0]
    assert str(req.url) == "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"
    assert json.loads(req.content) == {"inspectionUrl": "https://raisingchris.com/", "siteUrl": SITE}
    assert g.scopes == [["https://www.googleapis.com/auth/webmasters"]]
    assert out["verdict"] == "PASS" and out["coverage_state"] == "Submitted and indexed"
    assert out["last_crawl_time"] == "2026-09-08T03:00:00Z" and out["mobile_usability"] == "PASS"
    assert out["rich_results"] is None
    assert archived[0] == [("analytics", {"kind": "analytics", "api": "gsc_inspect", "status_code": 200})]


def test_non_2xx_returned_scrubbed_not_raised(archived):
    rec = Recorder(status=403, body={"error": {"code": 403, "status": "PERMISSION_DENIED",
                                                "message": f"Caller Bearer {TOKEN} lacks permission ya29.other"}})
    out = make(rec, archived).ga4_report(["date"], ["activeUsers"], "today", "today")
    assert out["status_code"] == 403 and out["api"] == "ga4"
    assert "lacks permission" in out["error"]
    assert TOKEN not in json.dumps(out) and "ya29." not in json.dumps(out) and "Bearer " not in out["error"]
    assert archived[0] == [("analytics", {"kind": "analytics", "api": "ga4", "status_code": 403})]


def test_non_json_error_body(archived):
    rec = Recorder(status=502, text="<html>bad gateway</html>")
    out = make(rec, archived).gsc_query("2026-09-01", "2026-09-07")
    assert out["status_code"] == 502 and "bad gateway" in out["error"]


def test_auth_failure_returned_as_error(archived):
    rec = Recorder(body={})
    out = make(rec, archived, FakeGoogle(exc=GoogleAuthError("Google STS exchange failed: HTTP 400"))).gsc_inspect("u")
    assert rec.requests == []
    assert "sign-in failed" in out["error"] and "HTTP 400" in out["error"]
    assert archived[0] == [("analytics", {"kind": "analytics", "api": "gsc_inspect", "status_code": 0})]


def test_unconfigured_property_or_site(archived):
    rec = Recorder(body={})
    a = make(rec, archived, prop="", site="")
    assert "ask your parents" in a.ga4_report(["date"], ["activeUsers"], "today", "today")["error"]
    assert "ask your parents" in a.gsc_query("2026-09-01", "2026-09-07")["error"]
    assert "ask your parents" in a.gsc_inspect("u")["error"]
    assert rec.requests == [] and archived[0] == []


def test_archive_never_holds_token_or_query(archived):
    rec = Recorder(body=GA4_BODY)
    make(rec, archived).ga4_report(["date"], ["activeUsers"], "today", "today")
    blob = json.dumps(archived[0])
    assert TOKEN not in blob and "553409810" not in blob and "activeUsers" not in blob


# --- the tools ---------------------------------------------------------------

class FakeAnalytics:
    def __init__(self, result=None, exc=None):
        self.result = result if result is not None else {"api": "x", "rows": [{"a": 1}], "row_count": 1}
        self.exc = exc
        self.calls = []

    def _rec(self, name, **kw):
        self.calls.append((name, kw))
        if self.exc:
            raise self.exc
        return self.result

    def ga4_report(self, **kw):
        return self._rec("ga4_report", **kw)

    def gsc_query(self, **kw):
        return self._rec("gsc_query", **kw)

    def gsc_inspect(self, **kw):
        return self._rec("gsc_inspect", **kw)


def configure(services, fake=None):
    services.google = FakeGoogle()
    services.analytics = fake or FakeAnalytics()
    return services.analytics


@pytest.mark.parametrize("name,args", [
    ("site_analytics", {"start": "today", "end": "today"}),
    ("search_console", {"start": "2026-09-01", "end": "2026-09-07"}),
    ("search_console_inspect", {"url": "https://raisingchris.com/"}),
])
async def test_tools_not_configured(services, name, args):
    h = tools.make_handlers(services)
    assert "ask your parents" in out_text(await h[name](args))


async def test_site_analytics_happy_path(services):
    fake = configure(services)
    h = tools.make_handlers(services)
    got = out_text(await h["site_analytics"]({"dimensions_json": '["date","pagePath"]',
                                              "metrics_json": '["activeUsers"]', "start": "7daysAgo",
                                              "end": "today", "limit": 10}))
    assert fake.calls == [("ga4_report", {"dimensions": ["date", "pagePath"], "metrics": ["activeUsers"],
                                          "start": "7daysAgo", "end": "today", "limit": 10})]
    assert json.loads(got)["rows"] == [{"a": 1}]


async def test_site_analytics_defaults(services):
    fake = configure(services)
    h = tools.make_handlers(services)
    await h["site_analytics"]({})
    assert fake.calls[0][1] == {"dimensions": ["date"], "metrics": ["activeUsers", "screenPageViews"],
                                "start": "7daysAgo", "end": "today", "limit": 50}


async def test_search_console_happy_path_and_missing_dates(services):
    fake = configure(services)
    h = tools.make_handlers(services)
    got = out_text(await h["search_console"]({"start": "2026-09-01", "end": "2026-09-07",
                                              "dimensions_json": '["query","page"]', "row_limit": 5}))
    assert fake.calls == [("gsc_query", {"start": "2026-09-01", "end": "2026-09-07",
                                         "dimensions": ["query", "page"], "row_limit": 5})]
    assert json.loads(got)["row_count"] == 1
    assert "needs start and end" in out_text(await h["search_console"]({"dimensions_json": '["query"]'}))
    assert len(fake.calls) == 1


async def test_search_console_inspect_happy_path_and_missing_url(services):
    fake = configure(services)
    h = tools.make_handlers(services)
    await h["search_console_inspect"]({"url": "https://raisingchris.com/diary/"})
    assert fake.calls == [("gsc_inspect", {"url": "https://raisingchris.com/diary/"})]
    assert "needs a url" in out_text(await h["search_console_inspect"]({}))


async def test_json_arg_errors_are_text(services):
    fake = configure(services)
    h = tools.make_handlers(services)
    assert "not valid JSON" in out_text(await h["site_analytics"]({"dimensions_json": "[date"}))
    assert "array of strings" in out_text(await h["site_analytics"]({"metrics_json": '{"a": 1}'}))
    assert "not valid JSON" in out_text(await h["search_console"]({"start": "a", "end": "b",
                                                                   "dimensions_json": "nope"}))
    assert fake.calls == []


async def test_tool_exception_is_text_and_scrubbed(services):
    configure(services, FakeAnalytics(exc=RuntimeError(f"boom Bearer {TOKEN}")))
    h = tools.make_handlers(services)
    got = out_text(await h["search_console_inspect"]({"url": "u"}))
    assert "failed" in got and TOKEN not in got
    assert "RuntimeError" in archive_text(services) and TOKEN not in archive_text(services)


async def test_tool_truncates_large_responses(services):
    configure(services, FakeAnalytics(result={"rows": "x" * 70_000}))
    h = tools.make_handlers(services)
    got = out_text(await h["site_analytics"]({}))
    assert len(got) < 61_000 and "[truncated" in got


def test_tools_registered_and_excluded_from_sleep():
    from agent.sleep import SLEEP_EXCLUDED

    for n in ("site_analytics", "search_console", "search_console_inspect"):
        assert n in tools.TOOL_NAMES and n in tools.SCHEMAS and n in SLEEP_EXCLUDED


# --- wiring ------------------------------------------------------------------

def test_build_wires_google_from_env(tmp_path, repo):
    from agent import wiring
    from agent.config import Config
    from agent.google_auth import GoogleWIF

    cfg = Config(repo_dir=str(repo), archive_dir=str(tmp_path / "a"), state_dir=str(tmp_path / "s"), dry_run=True)
    s = wiring.build(cfg, env={})
    assert s.google is None and s.analytics is None and s.ga4_property == "" and s.gsc_site == ""
    s = wiring.build(cfg, env={"GOOGLE_WIF_PROVIDER": "projects/1/locations/global/workloadIdentityPools/p/providers/x",
                               "GOOGLE_METRICS_SA": "sa@x.iam.gserviceaccount.com",
                               "GA4_PROPERTY_ID": "553409810", "GSC_SITE_URL": SITE})
    assert isinstance(s.google, GoogleWIF) and isinstance(s.analytics, Analytics)
    assert s.ga4_property == "553409810" and s.gsc_site == SITE
    assert s.analytics.ga4_property == "553409810" and s.analytics.gsc_site == SITE
    # Provider only, no SA: not configured.
    s = wiring.build(cfg, env={"GOOGLE_WIF_PROVIDER": "projects/1/x"})
    assert s.google is None
