import json
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI, HTTPException

from agent.budget import Meter
from agent.config import Config
from agent.creative import CreativeRelay, MODEL, worker_request, usage_usd, image_request, image_usage_usd


@pytest.mark.parametrize("extra", [
    {"model": "another-model"}, {"previous_response_id": "private-response"},
    {"conversation": "private-conversation"}, {"background": True},
    {"tools": [{"type": "file_search", "vector_store_ids": ["private-store"]}]},
    {"tools": [{"type": "mcp", "server_url": "https://example.test"}]},
    {"tools": [{"type": "namespace", "tools": [{"type": "web_search"}]}]},
])
def test_worker_cannot_use_parent_storage_or_other_models(extra):
    with pytest.raises(HTTPException):
        worker_request({"model": MODEL, "input": "draw", **extra})


def test_request_enforces_standard_billing_and_stateless_output_cap():
    body, reserve = worker_request({"model": MODEL, "input": "draw", "max_output_tokens": 100_000,
                                    "service_tier": "priority", "store": True})
    assert body["max_output_tokens"] == 8192
    assert body["store"] is False and body["service_tier"] == "default"
    assert reserve >= .4096
    assert usage_usd({"input_tokens": 1000, "input_tokens_details": {"cached_tokens": 500},
                      "output_tokens": 100}) == .0105


@pytest.fixture
def relay_setup(tmp_path):
    cfg = Config(repo_dir=str(tmp_path / "repo"), state_dir=str(tmp_path / "state"))
    entries = []
    services = SimpleNamespace(cfg=cfg, inference=Meter("food", "day", cfg.state_dir),
                               archive=SimpleNamespace(append=lambda *a: entries.append(a)))
    return services, entries


async def run_request(services, handler, body=None, token="worker-token"):
    calls = []

    def upstream(request):
        calls.append(request)
        return handler(request)

    relay = CreativeRelay(services, "parent-secret", "worker-token",
        client_factory=lambda **kw: httpx.AsyncClient(transport=httpx.MockTransport(upstream), **kw))
    app = FastAPI()
    app.add_api_route("/responses", relay.responses, methods=["POST"])
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        response = await c.post("/responses", json=body or {"model": MODEL, "input": "draw"},
                                headers={"Authorization": "Bearer " + token})
    return response, relay, calls


async def test_relay_requires_separate_token_before_spending(relay_setup):
    services, entries = relay_setup
    r, relay, calls = await run_request(services, lambda r: pytest.fail("No network"), token="wrong")
    assert r.status_code == 401 and calls == [] and entries == []
    assert services.inference.spent() == 0


async def test_relay_settles_actual_usage_and_never_forwards_parent_headers(relay_setup):
    services, entries = relay_setup
    def upstream(req):
        assert req.headers["authorization"] == "Bearer parent-secret"
        body = json.loads(req.content)
        assert body["model"] == MODEL and body["store"] is False
        return httpx.Response(200, json={"output": [], "usage": {"input_tokens": 100, "output_tokens": 10}},
                              headers={"openai-organization": "parent-identity"})
    r, relay, calls = await run_request(services, upstream)
    assert r.status_code == 200
    assert "parent-identity" not in str(r.headers) and "parent-secret" not in r.text
    assert relay.meter.spent() == services.inference.spent() == .0015
    assert entries[-1][1]["estimated"] is False and not relay.lock.locked()


async def test_streamed_usage_is_counted(relay_setup):
    services, entries = relay_setup
    event = {"type": "response.completed", "response": {"usage": {"input_tokens": 200, "output_tokens": 20}}}
    r, relay, calls = await run_request(services, lambda req: httpx.Response(200,
        text="data: " + json.dumps(event) + "\n\n", headers={"content-type": "text/event-stream"}),
        body={"model": MODEL, "input": "draw", "stream": True})
    assert "response.completed" in r.text
    assert relay.meter.spent() == .003 and not relay.lock.locked()


async def test_failed_stream_keeps_reservation_and_hides_upstream_error(relay_setup):
    services, entries = relay_setup
    r, relay, calls = await run_request(services, lambda req: httpx.Response(200,
        text='data: {"type":"error","message":"parent-identity"}\n\n'),
        body={"model": MODEL, "input": "draw", "stream": True})
    assert "parent-identity" not in r.text
    assert relay.meter.spent() >= .4096 and entries[-1][1]["estimated"] is True


async def test_upstream_rejection_is_generic_and_releases_reservation(relay_setup):
    services, entries = relay_setup
    r, relay, calls = await run_request(services, lambda req: httpx.Response(403,
        json={"error": "parent-secret private-project owner@example.test"}))
    assert r.status_code == 502 and "private-project" not in r.text
    assert relay.meter.spent() == services.inference.spent() == 0 and not relay.lock.locked()


async def test_exhausted_food_budget_prevents_network_call(relay_setup):
    services, entries = relay_setup
    services.inference.add_usd(services.cfg.hard_usd)
    r, relay, calls = await run_request(services, lambda r: pytest.fail("No network"))
    assert r.status_code == 429 and calls == [] and not relay.lock.locked()


def test_images_are_bounded_and_priced_separately():
    body, reserve = image_request({"prompt": "A sample illustration", "quality": "max", "stream": True})
    assert body["quality"] == "medium" and body["n"] == 1 and "stream" not in body
    assert reserve == 1
    assert image_usage_usd({"input_tokens": 100, "input_tokens_details": {"text_tokens": 100},
                            "output_tokens": 1000}) == .0305
    for extra in ({"size": "8192x8192"}, {"n": 20}, {"model": "another-model"}):
        with pytest.raises(HTTPException):
            image_request({"prompt": "sample", **extra})


async def test_image_route_uses_image_endpoint_and_records_image_usage(relay_setup):
    services, entries = relay_setup
    def upstream(req):
        assert req.url.path == "/v1/images/generations"
        assert json.loads(req.content)["n"] == 1
        return httpx.Response(200, json={"data": [{"b64_json": "sample"}],
            "usage": {"input_tokens": 100, "input_tokens_details": {"text_tokens": 100}, "output_tokens": 1000}})
    relay = CreativeRelay(services, "parent-secret", "worker-token",
        client_factory=lambda **kw: httpx.AsyncClient(transport=httpx.MockTransport(upstream), **kw))
    app = FastAPI()
    app.add_api_route("/images", relay.images, methods=["POST"])
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/images", json={"prompt": "sample"}, headers={"Authorization": "Bearer worker-token"})
    assert r.status_code == 200 and relay.meter.spent() == .0305
    assert entries[-1][1]["model"] == "gpt-image-2.5-flare"


def test_api_relay_disabled_without_explicit_opt_in(monkeypatch):
    from agent.creative import register_creative
    monkeypatch.delenv("CREATIVE_API_ENABLED", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "present-but-not-authorized")
    # Disabled registration must not touch services, credentials or routes.
    register_creative(None, None)
