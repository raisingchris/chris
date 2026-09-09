"""DataForSEO proxy: auth stays in the body, cost is metered, the cap refuses, endpoints are fenced."""

import json

import httpx
import pytest

from agent import tools
from agent.budget import Meter
from agent.dataforseo import DataForSEO, DataForSEOBudgetExceeded, DataForSEOEndpointError, validate_endpoint
from conftest import archive_text

AUTH = "bG9naW46cGFzc3dvcmQ="  # base64("login:password"); never appears in results or the archive


def out_text(result: dict) -> str:
    return result["content"][0]["text"]


class Recorder:
    def __init__(self, status=200, body=None):
        self.status = status
        self.body = body if body is not None else {
            "status_code": 20000, "cost": 0.0, "tasks": [{"cost": 0.002, "result": [{"keyword": "x"}]},
                                                          {"cost": 0.003, "result": []}]}
        self.requests: list[httpx.Request] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return httpx.Response(self.status, json=self.body)

    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self.handler))


@pytest.fixture
def archived():
    rows = []
    return rows, (lambda kind, data: rows.append((kind, data)) or f"archive:2026-09-09#{len(rows)}")


@pytest.fixture
def meter(tmp_path):
    return Meter("dataforseo", "week", tmp_path / "state")


def make(rec: Recorder, meter, archived, cap=5.0) -> DataForSEO:
    return DataForSEO(AUTH, meter, cap, archived[1], http=rec.client())


def test_sends_basic_auth_and_json_payload(meter, archived):
    rec = Recorder()
    d = make(rec, meter, archived)
    out = d.call("serp/google/organic/live/regular", [{"keyword": "chris", "location_code": 2840}])
    req = rec.requests[0]
    assert req.method == "POST"
    assert str(req.url) == "https://api.dataforseo.com/v3/serp/google/organic/live/regular"
    assert req.headers["Authorization"] == f"Basic {AUTH}"
    assert json.loads(req.content) == [{"keyword": "chris", "location_code": 2840}]
    assert out["endpoint"] == "serp/google/organic/live/regular"
    assert out["tasks"][0]["result"] == [{"keyword": "x"}]
    assert AUTH not in json.dumps(out)


def test_cost_summed_per_task_and_metered(meter, archived):
    d = make(Recorder(), meter, archived)
    d.call("keywords_data/google_ads/search_volume/live", {"keywords": ["a"]})
    assert meter.spent() == pytest.approx(0.005)
    rows, _ = archived
    assert rows == [("dataforseo", {"kind": "dataforseo", "endpoint": "keywords_data/google_ads/search_volume/live",
                                    "cost_usd": pytest.approx(0.005), "status_code": 200})]


def test_top_level_cost_wins_when_present(meter, archived):
    rec = Recorder(body={"cost": 0.01, "tasks": [{"cost": 0.01}]})
    make(rec, meter, archived).call("backlinks/summary/live", {"target": "x.com"})
    assert meter.spent() == pytest.approx(0.01)


def test_cap_refuses_before_any_request(meter, archived):
    rec = Recorder()
    meter.add_usd(5.0, "earlier")
    with pytest.raises(DataForSEOBudgetExceeded) as ei:
        make(rec, meter, archived).call("serp/google/organic/live/regular", [{"keyword": "q"}])
    assert "$5.00" in str(ei.value) and "cap" in str(ei.value)
    assert rec.requests == []


@pytest.mark.parametrize("bad", [
    "../appendix/user_data", "serp/../../etc", "merchant/google/products", "/etc/passwd", "",
    "serp/google/organic/live/regular?x=1", "SERP/google", "appendix/errors", "https://evil/serp/",
])
def test_endpoint_validation_rejects(bad, meter, archived):
    rec = Recorder()
    with pytest.raises(DataForSEOEndpointError):
        make(rec, meter, archived).call(bad, [])
    assert rec.requests == []


def test_endpoint_validation_accepts_allowlist():
    assert validate_endpoint("/on_page/instant_pages") == "on_page/instant_pages"
    assert validate_endpoint("appendix/user_data") == "appendix/user_data"
    assert validate_endpoint("ai_optimization/chat_gpt/llm_responses/live") == "ai_optimization/chat_gpt/llm_responses/live"


def test_archive_record_has_no_auth_or_payload(meter, archived):
    make(Recorder(), meter, archived).call("serp/google/organic/live/regular", [{"keyword": "SECRETQ"}])
    rows, _ = archived
    dumped = json.dumps(rows)
    assert AUTH not in dumped and "Authorization" not in dumped and "SECRETQ" not in dumped
    assert set(rows[0][1]) == {"kind", "endpoint", "cost_usd", "status_code"}


def test_non_2xx_returned_not_raised(meter, archived):
    rec = Recorder(status=401, body={"status_code": 40100, "status_message": "You are not authorized"})
    out = make(rec, meter, archived).call("serp/google/organic/live/regular", [{"keyword": "q"}])
    assert out["status_code"] == 401 and "not authorized" in out["error"]
    assert meter.spent() == 0.0
    rows, _ = archived
    assert rows[0][1]["status_code"] == 401


# --- the tool ---------------------------------------------------------------

class FakeDataForSEO:
    def __init__(self, result=None, exc=None):
        self.result = result if result is not None else {"endpoint": "serp/x", "tasks": [{"result": ["ok"]}]}
        self.exc = exc
        self.calls = []

    def call(self, endpoint, payload):
        self.calls.append((endpoint, payload))
        if self.exc:
            raise self.exc
        return self.result


async def test_tool_not_configured(services):
    h = tools.make_handlers(services)
    assert "ask your parents" in out_text(await h["seo_data"]({"endpoint": "serp/x", "payload_json": "[]"}))


async def test_tool_passes_parsed_payload_and_returns_json(services):
    services.dataforseo = FakeDataForSEO()
    h = tools.make_handlers(services)
    got = out_text(await h["seo_data"]({"endpoint": "serp/google/organic/live/regular",
                                        "payload_json": '[{"keyword": "chris"}]'}))
    assert services.dataforseo.calls == [("serp/google/organic/live/regular", [{"keyword": "chris"}])]
    assert json.loads(got)["tasks"][0]["result"] == ["ok"]


async def test_tool_rejects_bad_json(services):
    services.dataforseo = FakeDataForSEO()
    h = tools.make_handlers(services)
    assert "not valid JSON" in out_text(await h["seo_data"]({"endpoint": "serp/x", "payload_json": "{nope"}))
    assert services.dataforseo.calls == []


async def test_tool_budget_and_endpoint_refusals_are_text(services):
    services.dataforseo = FakeDataForSEO(exc=DataForSEOBudgetExceeded("DataForSEO has already spent $5.00 this week; the weekly cap is $5.00."))
    h = tools.make_handlers(services)
    assert "weekly cap" in out_text(await h["seo_data"]({"endpoint": "serp/x", "payload_json": "[]"}))
    services.dataforseo = FakeDataForSEO(exc=DataForSEOEndpointError("outside the allowed roots"))
    assert "refused" in out_text(await h["seo_data"]({"endpoint": "merchant/x", "payload_json": "[]"}))
    assert "refused" in archive_text(services)


async def test_tool_truncates_large_responses(services):
    services.dataforseo = FakeDataForSEO(result={"endpoint": "serp/x", "blob": "x" * 70_000})
    h = tools.make_handlers(services)
    got = out_text(await h["seo_data"]({"endpoint": "serp/x", "payload_json": "[]"}))
    assert len(got) < 61_000 and "[truncated" in got


def test_seo_data_registered_and_excluded_from_sleep():
    from agent.sleep import SLEEP_EXCLUDED

    assert "seo_data" in tools.TOOL_NAMES and "seo_data" in tools.SCHEMAS
    assert "seo_data" in SLEEP_EXCLUDED


# --- wiring -----------------------------------------------------------------

def test_meters_line_mentions_dataforseo_only_when_configured(services, tmp_path):
    assert "DataForSEO" not in services.meters_line()
    services.dataforseo_meter = Meter("dataforseo", "week", services.cfg.state_dir, tz=services.cfg.tz)
    services.dataforseo_meter.add_usd(0.25, "test")
    services.dataforseo = FakeDataForSEO()
    assert "· DataForSEO this week $0.25 of $2.00" in services.meters_line()
    assert "dataforseo" in services.meters


async def test_meters_tool_reports_dataforseo(services):
    services.dataforseo_meter = Meter("dataforseo", "week", services.cfg.state_dir, tz=services.cfg.tz)
    services.dataforseo = FakeDataForSEO()
    h = tools.make_handlers(services)
    assert "DataForSEO this week" in out_text(await h["meters"]({}))


def test_build_wires_dataforseo_from_env(tmp_path, repo):
    from agent import wiring
    from agent.config import Config

    cfg = Config(repo_dir=str(repo), archive_dir=str(tmp_path / "a"), state_dir=str(tmp_path / "s"), dry_run=True,
                 dataforseo_weekly_usd=2.5)
    s = wiring.build(cfg, env={})
    assert s.dataforseo is None and s.dataforseo_meter is not None
    s = wiring.build(cfg, env={"DATAFORSEO_AUTH_B64": AUTH})
    assert isinstance(s.dataforseo, DataForSEO) and s.dataforseo.weekly_cap_usd == 2.5
    assert s.secrets.dataforseo_auth_b64 == AUTH


def test_config_reads_weekly_cap():
    from agent.config import ENV_KEYS, Config

    assert "DATAFORSEO_WEEKLY_USD" in ENV_KEYS
    assert Config.from_env({}).dataforseo_weekly_usd == 2.0
    assert Config.from_env({"DATAFORSEO_WEEKLY_USD": "1.5"}).dataforseo_weekly_usd == 1.5
