"""HTTP: health, webhooks, parent admin (shared-password sign-in, handle-only session)."""

import base64
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from fake_services import make_services
from fastapi.testclient import TestClient
from freezegun import freeze_time

from agent import pause, wiring
from agent.server import create_app, is_stale, record_vote, sign_svix, verify_svix

SECRET = "whsec_" + base64.b64encode(b"0123456789abcdef0123456789abcdef").decode()
PASSWORD = "correct horse battery staple"


@pytest.fixture
def services(tmp_path):
    return make_services(tmp_path)


@pytest.fixture
def env(monkeypatch, tmp_path):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    monkeypatch.setenv("RESEND_WEBHOOK_SECRET", SECRET)
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_stripe")
    monkeypatch.setenv("LESSONS_DIR", str(tmp_path / "lessons"))
    monkeypatch.setenv("PARENT_PASSWORD", PASSWORD)


@pytest.fixture
def client(services, env):
    app = create_app(services)
    return TestClient(app)


def sign_in(client, handle, password=PASSWORD):
    """Post the shared password as ``handle``."""
    return client.post("/parent/login", data={"handle": handle, "password": password}, follow_redirects=False)


# --- health ---------------------------------------------------------------------


def test_health(client, services):
    body = client.get("/health").json()
    assert body["ok"] is True and body["paused"] is False
    assert body["last_sitting_done"] is None and body["last_sleep_done"] is None
    assert isinstance(body["disk_free_mb"], int) and body["unpushed"] == 0
    pause.trigger(services, "Chris asked to be paused.", "parent-a")
    assert client.get("/health").json()["paused"] is True


# Her tz is America/New_York (EDT, UTC-4, in September). freezegun takes UTC.
NY = ZoneInfo("America/New_York")


def _note(services, key, when: datetime):
    with freeze_time(when.astimezone(timezone.utc)):
        wiring.note_last_run(services.cfg.state_dir, key, tz=NY)


def test_is_stale_pure():
    runs = {"last_sleep_done": "2026-09-07T22:10:00-04:00", "last_sitting_done": "2026-09-07T09:40:00-04:00"}
    mon_night = datetime(2026, 9, 7, 23, 45, tzinfo=NY)
    assert not is_stale(runs, mon_night)
    assert is_stale({**runs, "last_sleep_done": "2026-09-06T22:10:00-04:00"}, mon_night)  # slept yesterday only
    sat = {"last_sitting_done": "2026-09-07T09:40:00-04:00"}
    assert not is_stale(sat, datetime(2026, 9, 7, 23, 29, tzinfo=NY))  # not yet 23:30
    assert is_stale(sat, datetime(2026, 9, 7, 23, 30, tzinfo=NY))
    # weekday 10:00 sitting rule
    assert not is_stale({}, datetime(2026, 9, 7, 9, 59, tzinfo=NY))
    assert is_stale({}, datetime(2026, 9, 7, 10, 0, tzinfo=NY))
    assert not is_stale({"last_sitting_done": "2026-09-07T09:40:00-04:00"}, datetime(2026, 9, 7, 10, 0, tzinfo=NY))
    assert is_stale({"last_sitting_done": "2026-09-06T13:40:00-04:00"}, datetime(2026, 9, 7, 10, 0, tzinfo=NY))
    assert is_stale({}, datetime(2026, 9, 12, 10, 0, tzinfo=NY))  # Saturday has sittings too
    assert not is_stale({}, datetime(2026, 9, 6, 12, 0, tzinfo=NY))  # Sunday: the letter is at 13:00, no rule
    assert not is_stale({"last_sitting_done": "garbage"}, datetime(2026, 9, 7, 9, 0, tzinfo=NY))


def test_health_stale_returns_503(client, services):
    # Monday 2026-09-07, 10:30 her time, nothing done today → stale
    with freeze_time("2026-09-07 14:30:00"):
        r = client.get("/health")
        assert r.status_code == 503
        body = r.json()
        assert body["stale"] is True and body["ok"] is False
        assert body["last_backup_done"] is None
    _note(services, "last_sitting_done", datetime(2026, 9, 7, 9, 40, tzinfo=NY))
    with freeze_time("2026-09-07 14:30:00"):
        r = client.get("/health")
        assert r.status_code == 200 and r.json()["stale"] is False
    # 23:45 her time, slept yesterday only → stale
    _note(services, "last_sleep_done", datetime(2026, 9, 6, 22, 10, tzinfo=NY))
    with freeze_time("2026-09-08 03:45:00"):
        r = client.get("/health")
        assert r.status_code == 503 and r.json()["stale"] is True
    _note(services, "last_sleep_done", datetime(2026, 9, 7, 22, 10, tzinfo=NY))
    _note(services, "last_backup_done", datetime(2026, 9, 7, 22, 46, tzinfo=NY))
    with freeze_time("2026-09-08 03:45:00"):
        r = client.get("/health")
        assert r.status_code == 200 and r.json()["stale"] is False
        assert r.json()["last_backup_done"].startswith("2026-09-07T22:46")


def test_health_paused_is_never_stale(client, services):
    pause.trigger(services, "Chris asked to be paused.", "parent-a")
    with freeze_time("2026-09-08 03:45:00"):  # 23:45 Monday her time, never slept
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["paused"] is True and r.json()["stale"] is False


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


def test_login_form_renders(client):
    r = client.get("/parent/login")
    assert r.status_code == 200
    assert 'name="handle"' in r.text and 'name="password"' in r.text
    assert 'value="parent-a"' in r.text and 'value="parent-b"' in r.text


def test_login_unconfigured_is_503(client, monkeypatch):
    monkeypatch.delenv("PARENT_PASSWORD")
    assert client.get("/parent/login").status_code == 503
    assert sign_in(client, "parent-a").status_code == 503


def test_wrong_password_is_401_and_stays_signed_out(client):
    r = sign_in(client, "parent-a", "nope")
    assert r.status_code == 401
    assert "Wrong password." in r.text
    assert client.get("/parent", follow_redirects=False).status_code == 303  # still signed out


def test_unknown_handle_is_400(client):
    assert sign_in(client, "stranger").status_code == 400
    assert client.get("/parent", follow_redirects=False).status_code == 303


def test_parent_signs_in_and_session_holds_handle(client):
    r = sign_in(client, "parent-b")
    assert r.status_code == 303 and r.headers["location"] == "/parent"
    cookie = client.cookies.get("parent_session")
    assert cookie
    session = json.loads(base64.b64decode(cookie.split(".")[0] + "=="))
    assert session == {"handle": "parent-b"}
    page = client.get("/parent")
    assert page.status_code == 200
    assert "Signed in as parent-b" in page.text

    client.get("/parent/logout")
    assert client.get("/parent", follow_redirects=False).status_code == 303


def test_login_locks_out_after_five_failures(client):
    for _ in range(5):
        assert sign_in(client, "parent-a", "nope").status_code == 401
    assert sign_in(client, "parent-a", "nope").status_code == 429
    assert sign_in(client, "parent-a").status_code == 429  # even the right password, while locked
    assert client.get("/parent", follow_redirects=False).status_code == 303

    limiter = client.app.state.login_limiter
    limiter._locked["testclient"] = time.time() - 1  # lockout expired
    assert sign_in(client, "parent-a").status_code == 303


# --- status page --------------------------------------------------------------------


def test_status_page_renders(client, services, tmp_path):
    repo = Path(services.cfg.repo_dir)
    (repo / "memory" / "diary" / "2026-09-06.md").write_text("# Day one\n\nI read the letter.\n")
    (repo / "memory" / "wiki" / "self" / "odometer.md").write_text("# Odometer\n\n1 in world-days, 3 loops closed, 37 loops to Explore.\n")
    (repo / "governance" / "proposals" / "p-1.md").write_text("# Proposal 1\n")
    services.mail.unread = ["a.md", "b.md"]
    sign_in(client, "parent-a")
    page = client.get("/parent").text
    assert "Running" in page
    assert "$4.20 of $25 soft / $40 hard" in page
    assert "Mail wakes today</td><td>0 of 6" in page
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
    sign_in(client, "parent-a")
    page = client.get("/parent").text
    assert "sitting 09:00" in page and "sleep" in page


# --- pause / unpause -----------------------------------------------------------------


def test_pause_requires_reason(client, services):
    sign_in(client, "parent-a")
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

    sign_in(client, "parent-a")
    client.post("/parent/vote", data={"proposal_id": "p-1", "vote": "ratify"})
    assert "## Result" not in (repo / "governance" / "proposals" / "p-1.md").read_text()
    client.post("/parent/vote", data={"proposal_id": "p-2", "vote": "veto", "reason": "Not yet; too expensive."})
    assert "Vetoed by a parent. Reason: Not yet; too expensive." in (repo / "governance" / "proposals" / "p-2.md").read_text()

    client.get("/parent/logout")
    sign_in(client, "parent-b")
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
    sign_in(client, "parent-b")

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
    sign_in(client, "parent-a")
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
    sign_in(client, "parent-a")

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


# --- two passwords ----------------------------------------------------------------------


def test_per_handle_passwords(client, monkeypatch):
    monkeypatch.setenv("PARENT_A_PASSWORD", "alpha pass phrase")
    monkeypatch.setenv("PARENT_B_PASSWORD", "bravo pass phrase")
    assert sign_in(client, "parent-a", "alpha pass phrase").status_code == 303
    client.get("/parent/logout")
    assert sign_in(client, "parent-a", "bravo pass phrase").status_code == 401  # the other parent's password
    assert sign_in(client, "parent-b", "alpha pass phrase").status_code == 401
    assert sign_in(client, "parent-b", "bravo pass phrase").status_code == 303
    client.get("/parent/logout")
    assert sign_in(client, "parent-a", PASSWORD).status_code == 401  # shared fallback ignored once a specific one is set


def test_shared_password_fallback_per_handle(client, monkeypatch):
    monkeypatch.setenv("PARENT_A_PASSWORD", "alpha pass phrase")
    monkeypatch.delenv("PARENT_B_PASSWORD", raising=False)
    assert sign_in(client, "parent-b", PASSWORD).status_code == 303  # B falls back to PARENT_PASSWORD
    client.get("/parent/logout")
    assert sign_in(client, "parent-a", PASSWORD).status_code == 401


def test_login_503_when_only_other_handle_configured(client, monkeypatch):
    monkeypatch.delenv("PARENT_PASSWORD")
    monkeypatch.setenv("PARENT_A_PASSWORD", "alpha pass phrase")
    assert client.get("/parent/login").status_code == 200
    assert sign_in(client, "parent-a", "alpha pass phrase").status_code == 303
    client.get("/parent/logout")
    assert sign_in(client, "parent-b", "anything at all").status_code == 503


def test_parent_page_commits_explicit_paths_only(client, services, tmp_path, monkeypatch):
    """unseal and vote commit just the file they wrote, never `git add -A`."""
    import dataclasses

    from agent import gitops

    calls = []

    def git(repo_dir, *args, check=True, **kw):
        calls.append(args)
        from types import SimpleNamespace
        return SimpleNamespace(stdout="", stderr="", returncode=0)

    monkeypatch.setattr(gitops, "git_as_parent", git)
    services.cfg = dataclasses.replace(services.cfg, dry_run=False)
    repo = Path(services.cfg.repo_dir)
    (repo / ".git").mkdir()
    lessons = tmp_path / "lessons"
    lessons.mkdir()
    (lessons / "01.md").write_text("# First\n\nHi.\n")
    (repo / "governance" / "proposals" / "p-9.md").write_text("# p-9\n")
    c = TestClient(create_app(services), base_url="https://testserver")  # session cookie is https-only outside dry-run
    assert sign_in(c, "parent-a").status_code == 303
    assert c.post("/parent/unseal", data={"n": "1"}, follow_redirects=False).status_code == 303
    c.post("/parent/vote", data={"proposal_id": "p-9", "vote": "veto", "reason": "Not now, thank you."})
    adds = [a for a in calls if a[:1] == ("add",)]
    assert adds == [("add", "--", "memory/wiki/lessons/from_parent/01-first.md"),
                    ("add", "--", "governance/proposals/p-9.md")]
    assert not any("-A" in a for a in calls)


# --- deploy her code -------------------------------------------------------------------


def test_deploy_button_dispatches_workflow_and_logs(client, services, monkeypatch):
    from types import SimpleNamespace

    from agent import gitops, server

    calls = []
    monkeypatch.setenv("GITHUB_DEPLOY_TOKEN", "ghp_test")
    monkeypatch.setenv("GIT_SHA", "aaaaaaa1111")
    monkeypatch.setattr(gitops, "head_sha", lambda repo_dir, ref="HEAD", run=None: "bbbbbbb2222")

    def post(url, **kw):
        calls.append((url, kw))
        return SimpleNamespace(status_code=204, text="")

    real = server.dispatch_deploy
    monkeypatch.setattr(server, "dispatch_deploy", lambda token: real(token, post=post))

    sign_in(client, "parent-a")
    page = client.get("/parent").text
    assert "aaaaaaa" in page and "bbbbbbb" in page and "not deployed yet" in page and "whatever is on main" in page

    r = client.post("/parent/deploy", follow_redirects=False)
    assert r.status_code == 303
    url, kw = calls[0]
    assert url == "https://api.github.com/repos/raisingchris/chris/actions/workflows/deploy.yml/dispatches"
    assert kw["json"] == {"ref": "main"} and kw["headers"]["Authorization"] == "Bearer ghp_test"
    changelog = (Path(services.cfg.repo_dir) / "governance" / "changelog.md").read_text()
    assert "a parent deployed Chris's code at bbbbbbb" in changelog
    assert any(k == "parent_action" and p["action"] == "deploy" and p["by"] == "parent-a"
               for k, p in services.archive.entries)


def test_deploy_without_token_is_503_and_needs_login(client, monkeypatch):
    monkeypatch.delenv("GITHUB_DEPLOY_TOKEN", raising=False)
    assert client.post("/parent/deploy", follow_redirects=False).status_code == 303  # to login
    sign_in(client, "parent-b")
    assert client.post("/parent/deploy").status_code == 503


def test_deploy_github_failure_is_visible(client, services, monkeypatch):
    from types import SimpleNamespace

    from agent import server

    monkeypatch.setenv("GITHUB_DEPLOY_TOKEN", "ghp_test")
    real = server.dispatch_deploy
    monkeypatch.setattr(server, "dispatch_deploy",
                        lambda token: real(token, post=lambda url, **kw: SimpleNamespace(status_code=401, text="Bad credentials")))
    sign_in(client, "parent-a")
    r = client.post("/parent/deploy")
    assert r.status_code == 502 and "401" in r.text
    assert not (Path(services.cfg.repo_dir) / "governance" / "changelog.md").exists()


def test_health_reports_git_sha(client, monkeypatch):
    monkeypatch.setenv("GIT_SHA", "abc1234")
    assert client.get("/health").json()["git_sha"] == "abc1234"


def test_resend_webhook_schedules_mail_wake(services, env):
    """A valid email.received adds the one-off ``mail-wake`` job when the decision allows it."""
    from agent import scheduler as scheduler_module

    Path(services.cfg.repo_dir, "memory", "diary", "2026-09-05.md").write_text("born")

    class FakeSched:
        running = True
        timezone = NY

        def __init__(self):
            self.jobs = []

        def add_job(self, fn, trigger, **kw):
            self.jobs.append((fn, trigger, kw))

        def get_jobs(self):
            return []

        def start(self):
            pass

        def shutdown(self, wait=False):
            pass

    fs = FakeSched()
    client = TestClient(create_app(services, fs))
    payload = {"type": "email.received", "data": {"email_id": "e9", "from": "x@y.z"}}
    body = json.dumps(payload).encode()

    def headers(mid):  # signed with the (frozen) clock so the svix timestamp check passes
        ts = int(time.time())
        return {"svix-id": mid, "svix-timestamp": str(ts), "svix-signature": sign_svix(mid, ts, body, SECRET)}

    with freeze_time("2026-09-07 14:30:00"):  # Monday 10:30 her time
        assert client.post("/webhooks/resend", content=body, headers=headers("m1")).status_code == 200
    assert services.mail.ingested == [payload]
    assert len(fs.jobs) == 1
    fn, trigger, kw = fs.jobs[0]
    assert kw["id"] == "mail-wake" and kw["replace_existing"] is True
    assert trigger.run_date.astimezone(NY) == datetime(2026, 9, 7, 10, 31, tzinfo=NY)
    with freeze_time("2026-09-07 14:32:00"):
        assert client.get("/health").json()["mail_wakes_today"] == 1
        sign_in(client, "parent-a")
        assert "Mail wakes today</td><td>1 of 6" in client.get("/parent").text
    # a second mail two minutes later is debounced, not scheduled
    with freeze_time("2026-09-07 14:32:00"):
        assert client.post("/webhooks/resend", content=body, headers=headers("m2")).status_code == 200
    assert len(fs.jobs) == 1
    assert ("mail_wake_skipped", {"kind": "mail_wake_skipped", "reason": "debounce"}) in services.archive.entries
    # at night the mail waits for the 07:00 wake
    with freeze_time("2026-09-08 03:00:00"):  # 23:00 her time
        assert client.post("/webhooks/resend", content=body, headers=headers("m3")).status_code == 200
    assert len(fs.jobs) == 1
    assert services.archive.entries[-1][1] == {"kind": "mail_wake_skipped", "reason": "sleep_hours"}
    assert scheduler_module.MAIL_WAKE_DAILY_CAP == 6


# --- tickets ------------------------------------------------------------------------------


def test_ticket_resolve_writes_reply_and_status(client, services):
    from datetime import datetime, timezone

    from agent import tickets

    repo = Path(services.cfg.repo_dir)
    p = tickets.open_ticket(repo, "A GitHub token", "1. Open the settings page.\n2. Paste the token.",
                            datetime(2026, 9, 7, 14, 30, tzinfo=timezone.utc))
    tid = p.stem
    sign_in(client, "parent-a")
    page = client.get("/parent").text
    section = page.split("<h2>Tickets</h2>")[1].split("<h2>")[0]
    assert "A GitHub token" in section and tid in section and "Open the settings page." in section

    r = client.post("/parent/ticket", data={"ticket_id": tid, "status": "done", "reply": "ok"})
    assert r.status_code == 400 and "at least five characters" in r.text
    assert client.post("/parent/ticket", data={"ticket_id": tid, "status": "maybe", "reply": "long enough"}).status_code == 400
    assert client.post("/parent/ticket", data={"ticket_id": "20260101T0000-none", "status": "done",
                                               "reply": "long enough"}).status_code == 404
    assert client.post("/parent/ticket", data={"ticket_id": "../soul/vows", "status": "done",
                                               "reply": "long enough"}).status_code == 400

    r = client.post("/parent/ticket", data={"ticket_id": tid, "status": "done", "reply": "It's in your inbox."},
                    follow_redirects=False)
    assert r.status_code == 303
    text = p.read_text()
    assert "status: done" in text and "closed:" in text
    assert "## Reply" in text and "*parent-a, " in text and "It's in your inbox." in text
    assert ("parent_action", {"kind": "parent_action", "action": "ticket", "by": "parent-a",
                              "ticket": tid, "status": "done"}) in services.archive.entries
    assert "None open." in client.get("/parent").text.split("<h2>Tickets</h2>")[1].split("<h2>")[0]
    # closed is closed
    assert client.post("/parent/ticket", data={"ticket_id": tid, "status": "declined", "reply": "long enough"}).status_code == 400
