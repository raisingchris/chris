"""HTTP: health, webhooks, parent admin (sign-in restricted to parents, handle-only session)."""

import base64
import json
import time
from pathlib import Path

import pytest
from fake_services import make_services
from fastapi.testclient import TestClient

from agent import pause
from agent.server import create_app, record_vote, sign_svix, verify_svix

SECRET = "whsec_" + base64.b64encode(b"0123456789abcdef0123456789abcdef").decode()


class FakeGoogle:
    def __init__(self, email):
        self.email = email

    async def authorize_redirect(self, request, redirect_uri):
        from fastapi.responses import RedirectResponse

        return RedirectResponse("https://accounts.google.com/o/oauth2/auth?fake=1")

    async def authorize_access_token(self, request):
        return {"userinfo": {"email": self.email, "email_verified": True}}


class FakeOAuth:
    def __init__(self, email):
        self.google = FakeGoogle(email)


@pytest.fixture
def services(tmp_path):
    return make_services(tmp_path)


@pytest.fixture
def env(monkeypatch, tmp_path):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    monkeypatch.setenv("RESEND_WEBHOOK_SECRET", SECRET)
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_stripe")
    monkeypatch.setenv("LESSONS_DIR", str(tmp_path / "lessons"))
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)


@pytest.fixture
def client(services, env):
    app = create_app(services)
    return TestClient(app)


def sign_in(client, email):
    """Drive the OAuth callback with a fake Google that returns ``email``."""
    client.app.state.oauth = FakeOAuth(email)
    return client.get("/parent/auth", follow_redirects=False)


# --- health ---------------------------------------------------------------------


def test_health(client, services):
    assert client.get("/health").json() == {"ok": True, "paused": False}
    pause.trigger(services, "Chris asked to be paused.", "parent-a")
    assert client.get("/health").json()["paused"] is True


# --- resend webhook ---------------------------------------------------------------


def test_verify_svix_pure():
    body = b'{"type":"email.received"}'
    ts = 1_800_000_000
    sig = sign_svix("msg_1", ts, body, SECRET)
    headers = {"svix-id": "msg_1", "svix-timestamp": str(ts), "svix-signature": f"v1,bogus {sig}"}
    assert verify_svix(headers, body, SECRET, now=ts + 10)
    assert not verify_svix(headers, body, SECRET, now=ts + 600)  # too old
    assert not verify_svix(headers, body + b" ", SECRET, now=ts)  # body changed
    assert not verify_svix(headers, body, "whsec_" + base64.b64encode(b"x" * 32).decode(), now=ts)
    assert not verify_svix({}, body, SECRET, now=ts)


def test_resend_webhook_rejects_bad_signature(client, services):
    body = json.dumps({"type": "email.received", "data": {"email_id": "e1"}}).encode()
    r = client.post("/webhooks/resend", content=body, headers={
        "svix-id": "m", "svix-timestamp": str(int(time.time())), "svix-signature": "v1,nope",
    })
    assert r.status_code == 401
    assert services.mail.ingested == []


def test_resend_webhook_ingests_on_valid_signature(client, services):
    payload = {"type": "email.received", "data": {"email_id": "e1", "from": "x@y.z"}}
    body = json.dumps(payload).encode()
    ts = int(time.time())
    r = client.post("/webhooks/resend", content=body, headers={
        "svix-id": "msg_2", "svix-timestamp": str(ts), "svix-signature": sign_svix("msg_2", ts, body, SECRET),
        "content-type": "application/json",
    })
    assert r.status_code == 200
    assert services.mail.ingested == [payload]

    other = json.dumps({"type": "email.sent", "data": {}}).encode()
    client.post("/webhooks/resend", content=other, headers={
        "svix-id": "msg_3", "svix-timestamp": str(ts), "svix-signature": sign_svix("msg_3", ts, other, SECRET),
    })
    assert len(services.mail.ingested) == 1  # only email.received is ingested


# --- stripe webhook ---------------------------------------------------------------


def test_stripe_webhook_passes_raw_body_and_secret(client, services):
    r = client.post("/webhooks/stripe", content=b"{}", headers={"stripe-signature": "good"})
    assert r.status_code == 200
    assert services.payments.calls == [(b"{}", "good", "whsec_stripe")]
    assert client.post("/webhooks/stripe", content=b"{}", headers={"stripe-signature": "bad"}).status_code == 400


# --- admin auth -------------------------------------------------------------------


def test_admin_redirects_to_login_when_signed_out(client):
    r = client.get("/parent", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/parent/login"
    assert client.post("/parent/pause", data={"reason": "x" * 20}, follow_redirects=False).status_code == 303


def test_login_unconfigured_is_503(client):
    assert client.get("/parent/login", follow_redirects=False).status_code == 503


def test_admin_403_for_non_parent_email(client):
    assert sign_in(client, "stranger@example.com").status_code == 403
    assert client.get("/parent", follow_redirects=False).status_code == 303  # still signed out


def test_parent_signs_in_and_session_holds_handle_not_email(client):
    r = sign_in(client, "BOB.real@example.com")  # case-insensitive match against parent-b
    assert r.status_code == 303 and r.headers["location"] == "/parent"
    cookie = client.cookies.get("parent_session")
    assert cookie
    session = json.loads(base64.b64decode(cookie.split(".")[0] + "=="))
    assert session == {"handle": "parent-b"}
    page = client.get("/parent")
    assert page.status_code == 200
    assert "Signed in as parent-b" in page.text
    assert "example.com" not in page.text


# --- status page --------------------------------------------------------------------


def test_status_page_renders(client, services, tmp_path):
    repo = Path(services.cfg.repo_dir)
    (repo / "memory" / "diary" / "2026-09-06.md").write_text("# Day one\n\nI read the letter.\n")
    (repo / "memory" / "wiki" / "self" / "odometer.md").write_text("# Odometer\n\n1 in world-days, 3 loops closed, 37 loops to Explore.\n")
    (repo / "governance" / "proposals" / "p-1.md").write_text("# Proposal 1\n")
    services.mail.unread = ["a.md", "b.md"]
    sign_in(client, "alice.real@example.com")
    page = client.get("/parent").text
    assert "Running" in page
    assert "$4.20 of $15 soft / $25 hard" in page
    assert "$1.50 of $10" in page
    assert "3 loops closed" in page
    assert "I read the letter." in page
    assert "<td>2</td>" in page
    assert "p-1" in page
    assert "No scheduler attached" in page


def test_status_page_shows_next_runs_with_scheduler(services, env):
    from agent.scheduler import make_scheduler

    async def noop(*a):
        pass

    client = TestClient(create_app(services, make_scheduler(services, noop, noop)))
    sign_in(client, "alice.real@example.com")
    page = client.get("/parent").text
    assert "sitting 09:00" in page and "sleep" in page


# --- pause / unpause -----------------------------------------------------------------


def test_pause_requires_reason(client, services):
    sign_in(client, "alice.real@example.com")
    r = client.post("/parent/pause", data={"reason": "short"})
    assert r.status_code == 400
    assert "at least ten characters" in r.text
    assert not pause.is_paused(services.cfg.state_dir)

    r = client.post("/parent/pause", data={"reason": "Condition 7: she asked to be paused."}, follow_redirects=False)
    assert r.status_code == 303
    assert pause.is_paused(services.cfg.state_dir)
    assert pause.status(services.cfg.state_dir)["by"] == "parent-a"
    assert ("parent_action", {"kind": "parent_action", "action": "pause", "by": "parent-a"}) in services.archive.entries
    assert "Paused" in client.get("/parent").text

    client.post("/parent/unpause")
    assert not pause.is_paused(services.cfg.state_dir)


# --- votes -------------------------------------------------------------------------


def test_record_vote_logic(tmp_path):
    p = tmp_path / "votes.json"
    handles = ["parent-a", "parent-b"]
    assert record_vote(p, "x", "parent-a", "ratify", handles) is None
    assert record_vote(p, "x", "parent-b", "ratify", handles) == "ratified"
    assert record_vote(p, "y", "parent-b", "veto", handles) == "vetoed"
    assert record_vote(p, "y", "parent-a", "ratify", handles) is None  # already decided
    assert json.loads(p.read_text())["x"]["parent-a"] == "ratify"


def test_vote_endpoint_both_needed_and_either_vetoes(client, services):
    repo = Path(services.cfg.repo_dir)
    for pid in ("p-1", "p-2"):
        (repo / "governance" / "proposals" / f"{pid}.md").write_text(f"# {pid}\n")

    sign_in(client, "alice.real@example.com")
    client.post("/parent/vote", data={"proposal_id": "p-1", "vote": "ratify"})
    assert "## Result" not in (repo / "governance" / "proposals" / "p-1.md").read_text()
    client.post("/parent/vote", data={"proposal_id": "p-2", "vote": "veto", "reason": "Not yet; too expensive."})
    assert "Vetoed by a parent. Reason: Not yet; too expensive." in (repo / "governance" / "proposals" / "p-2.md").read_text()

    client.get("/parent/logout")
    sign_in(client, "bob.real@example.com")
    client.post("/parent/vote", data={"proposal_id": "p-1", "vote": "ratify"})
    assert "Ratified by both parents." in (repo / "governance" / "proposals" / "p-1.md").read_text()
    assert client.post("/parent/vote", data={"proposal_id": "nope", "vote": "ratify"}).status_code == 404
    assert client.post("/parent/vote", data={"proposal_id": "../x", "vote": "ratify"}).status_code == 400
    assert "p-1" not in client.get("/parent").text.split("<h2>Proposals</h2>")[1].split("<h2>")[0]


# --- unseal / allowance ----------------------------------------------------------------


def test_unseal_lesson(client, services, tmp_path):
    lessons = tmp_path / "lessons"
    lessons.mkdir()
    (lessons / "03.md").write_text("# On being wrong in public\n\nSay so.\n")
    repo = Path(services.cfg.repo_dir)
    sign_in(client, "bob.real@example.com")

    assert client.post("/parent/unseal", data={"n": "4"}).status_code == 404
    r = client.post("/parent/unseal", data={"n": "3"}, follow_redirects=False)
    assert r.status_code == 303
    dest = repo / "memory" / "wiki" / "lessons" / "from_parent" / "03-on-being-wrong-in-public.md"
    assert dest.read_text() == (lessons / "03.md").read_text()
    inbox = list((repo / "memory" / "inbox").glob("*-lesson-03.md"))
    assert len(inbox) == 1
    note = inbox[0].read_text()
    assert "from: parent-b" in note and 'subject: "A lesson from your parents"' in note
    assert client.post("/parent/unseal", data={"n": "3"}).status_code == 409
    assert ("parent_action", {"kind": "parent_action", "action": "unseal", "by": "parent-b", "lesson": "03"}) in services.archive.entries


def test_allowance(client, services):
    sign_in(client, "alice.real@example.com")
    r = client.post("/parent/allowance", data={"weekly_usd": "80", "per_txn_usd": "25"}, follow_redirects=False)
    assert r.status_code == 303
    assert ("set_limits", 80.0, 25.0) in services.card.calls
    saved = json.loads(Path(services.cfg.state_dir, "allowance.json").read_text())
    assert saved["weekly_usd"] == 80.0 and saved["per_txn_usd"] == 25.0
    assert any(k == "parent_action" and p["action"] == "allowance" for k, p in services.archive.entries)
    assert 'value="80.0"' in client.get("/parent").text


def test_veto_requires_reason_ratify_does_not(client, services):
    repo = Path(services.cfg.repo_dir)
    for pid in ("v-1", "v-2"):
        (repo / "governance" / "proposals" / f"{pid}.md").write_text(f"# {pid}\n")
    sign_in(client, "alice.real@example.com")

    r = client.post("/parent/vote", data={"proposal_id": "v-1", "vote": "veto"})
    assert r.status_code == 400 and "reason" in r.text
    r = client.post("/parent/vote", data={"proposal_id": "v-1", "vote": "veto", "reason": "short"})
    assert r.status_code == 400
    assert "## Result" not in (repo / "governance" / "proposals" / "v-1.md").read_text()

    r = client.post("/parent/vote", data={"proposal_id": "v-1", "vote": "veto", "reason": "Too early; wait a month."},
                    follow_redirects=False)
    assert r.status_code == 303
    assert "Vetoed by a parent. Reason: Too early; wait a month." in (repo / "governance" / "proposals" / "v-1.md").read_text()

    assert client.post("/parent/vote", data={"proposal_id": "v-2", "vote": "ratify"}, follow_redirects=False).status_code == 303
    assert 'name="reason"' in client.get("/parent").text
