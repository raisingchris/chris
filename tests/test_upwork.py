import json
import time
from pathlib import Path

import httpx
import pytest

from agent.upwork import Upwork, WorkError, write_private


@pytest.fixture
def work(tmp_path):
    w = Upwork(tmp_path, ["Example Parent"])
    write_private(w.connection, {"org_uid": "private-org", "client_id": "private-client",
        "access_token": "secret-access", "refresh_token": "secret-refresh",
        "obtained_at": time.time(), "expires_in": 86400})
    return w


def test_projection_withholds_identity_and_maps_references(work):
    raw = {"jobs": [{"id": "12345", "title": "Clean CSV", "budget": "25.00",
        "description": "Example Parent wrote from parent@example.test at /Users/private-person/file. "
                       "https://upwork.com/freelancers/private-profile secret-access",
        "client": {"name": "Secret Company", "rating": 5},
        "user": {"id": "private-user"}, "photo_url": "https://private.test/photo.jpg",
        "unknown_identity_field": "Private identity"}], "org_uid": "private-org"}
    result = work._project(raw)
    text = json.dumps(result)
    for secret in ("Example Parent", "parent@example.test", "private-person", "private-profile",
                   "secret-access", "Secret Company", "private-user", "Private identity", "private-org"):
        assert secret not in text
    job = result["jobs"][0]
    assert job["budget"] == "25.00" and job["client"]["rating"] == 5
    assert work._resolve(job["id"]) == "12345"
    assert work._project(raw)["jobs"][0]["id"] == job["id"]


@pytest.mark.parametrize("action,params", [
    ("get_account", {}), ("search", {"org_uid": "other"}),
    ("search", {"url": "https://private.test"}), ("job", {"id": "12345"}),
    ("search", {"limit": 100}), ("search", {"limit": True}),
])
def test_no_generic_account_or_identifier_passthrough(work, action, params):
    work._call = lambda *a: pytest.fail("Must reject before a network call")
    with pytest.raises(WorkError):
        work.read(action, params)


def test_read_resolves_reference_and_filters_new_fields(work):
    ref = work._reference("job-123")
    def call(tool, action, params):
        assert (tool, action, params) == ("find_jobs", "get", {"id": "job-123"})
        return {"data": {"content": {"title": "Test task", "description": "Clean data"},
                         "new_personal_data": "private"}, "connects_cost": 8}
    work._call = call
    got = work.read("job", {"id": ref})
    assert got["connects_cost"] == 8
    assert "new_personal_data" not in json.dumps(got)


def test_prepare_is_private_local_idempotent_and_does_not_send(work):
    work._call = lambda *a: pytest.fail("Preparing a local draft must never call Upwork")
    ref = work._reference("job-123")
    a = work.prepare("proposal", ref, "I can clean the supplied CSV using an AI agent.", 20)
    assert a == work.prepare("proposal", ref, "I can clean the supplied CSV using an AI agent.", 20)
    assert len(work.outbox()) == 1
    assert work.item(a["id"])["state"] == "pending"
    assert (work.root / "outbox" / (a["id"] + ".json")).stat().st_mode & 0o077 == 0


@pytest.mark.parametrize("body,amount", [("Example Parent", 20), ("https://private.test", 20),
    ("Write to me@example.test", 20), ("Fine", float("nan")), ("Fine", -1), ("", 20)])
def test_private_details_and_invalid_bids_cannot_be_queued(work, body, amount):
    with pytest.raises(WorkError):
        work.prepare("proposal", work._reference("job"), body, amount)
    assert work.outbox() == []


def test_parent_message_confirm_sends_once_and_requires_preview(work):
    ref = work._reference("room-1")
    item = work.prepare("message", ref, "The result is ready.")
    with pytest.raises(WorkError):
        work.parent_confirm(item["id"])
    work._call = lambda *a: {"messages": [{"from": "Client", "text": "Please update me."}]}
    work.parent_prepare(item["id"])
    calls = []
    work._call = lambda *a: calls.append(a) or {"status": "ok"}
    assert work.parent_confirm(item["id"])["state"] == "sent"
    assert calls == [("send_message", "send", {"room_id": "room-1", "message": "The result is ready."})]
    with pytest.raises(WorkError):
        work.parent_confirm(item["id"])
    assert len(calls) == 1


def test_ambiguous_send_is_not_retried(work):
    key = work.prepare("message", work._reference("room-1"), "Ready.")["id"]
    work._call = lambda *a: {"messages": []}
    work.parent_prepare(key)
    def fail(*a):
        raise RuntimeError("secret-access account identity")
    work._call = fail
    with pytest.raises(WorkError, match="uncertain"):
        work.parent_confirm(key)
    assert work.item(key)["state"] == "check_on_upwork"
    with pytest.raises(WorkError):
        work.parent_confirm(key)


def test_token_refresh_is_private_and_rotated_token_persists(work):
    cfg = work._config()
    cfg["obtained_at"] = 0
    write_private(work.connection, cfg)
    def transport(request):
        if request.url.path.endswith("/token"):
            assert b"refresh_token=secret-refresh" in request.content
            return httpx.Response(200, json={"access_token": "rotated-access", "refresh_token": "rotated-refresh", "expires_in": 86400})
        assert request.headers["authorization"] == "Bearer rotated-access"
        return httpx.Response(200, json={"result": {"ok": True}})
    work.client = httpx.Client(transport=httpx.MockTransport(transport))
    assert work._request({"id": 1}) == {"ok": True}
    assert work._config()["refresh_token"] == "rotated-refresh"
    assert work.connection.stat().st_mode & 0o077 == 0


def test_upstream_error_does_not_leak_identity(work):
    work.client = httpx.Client(transport=httpx.MockTransport(
        lambda request: httpx.Response(403, text="secret-access Example Parent")))
    with pytest.raises(WorkError) as e:
        work._request({"id": 1})
    assert "secret-access" not in str(e.value) and "Example Parent" not in str(e.value)


def test_parent_proposal_blocks_duplicate_or_invited_job(work):
    key = work.prepare("proposal", work._reference("job-1"), "I can do this with AI assistance.", 20)["id"]
    work._call = lambda *a: {"invitations": [{"jobPosting": {"id": "job-1"}}]}
    with pytest.raises(WorkError, match="invitation"):
        work.parent_prepare(key)
    assert work.item(key)["state"] == "pending"


def test_status_never_exposes_raw_preview_or_tokens(work):
    key = work.prepare("message", work._reference("room-1"), "Ready")["id"]
    item = work.item(key)
    item["preview"] = {"account": "Example Parent", "token": "secret-access"}
    work._save_item(item)
    assert "Example Parent" not in json.dumps(work.read("status", {}))
    assert "secret-access" not in json.dumps(work.read("status", {}))
