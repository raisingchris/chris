"""X posting through Typefully: bearer auth stays in the header, the body shape is
right, threads split, 280 is enforced, the weekly cap refuses, the archive is clean,
non-2xx comes back as text, and publish-state polling returns a url or gives up."""

import json

import httpx
import pytest

from agent import tools
from agent.budget import Meter
from agent.x_client import XClient, XError
from conftest import archive_text

KEY = "tk_live_SECRETKEY_do_not_leak"  # never appears in a result or the archive
SOCIAL = "ss_42"


def out_text(result: dict) -> str:
    return result["content"][0]["text"]


class Recorder:
    def __init__(self, create_status=201, create_body=None, poll_states=None):
        self.create_status = create_status
        self.create_body = create_body if create_body is not None else {
            "id": 99, "status": "draft", "publish_state": "in_progress"}
        # states returned by successive GET polls; the last one repeats when exhausted
        self.poll_states = list(poll_states) if poll_states is not None else ["finished"]
        self.requests: list[httpx.Request] = []

    def _next_state(self):
        if len(self.poll_states) > 1:
            return self.poll_states.pop(0)
        return self.poll_states[0] if self.poll_states else None

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.method == "POST":
            return httpx.Response(self.create_status, json=self.create_body)
        state = self._next_state()
        body = {"id": 99, "publish_state": state}
        if state == "finished":
            body["platforms"] = {"x": {"posts": [{"url": "https://x.com/Raising_Chris/status/1"}]}}
        return httpx.Response(200, json=body)

    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self.handler))


@pytest.fixture
def archived():
    rows = []
    return rows, (lambda kind, data: rows.append((kind, data)) or f"archive:2026-09-12#{len(rows)}")


@pytest.fixture
def meter(tmp_path):
    return Meter("x", "week", tmp_path / "state")


def make(rec: Recorder, meter, archived, cap=7) -> XClient:
    c = XClient(KEY, SOCIAL, archived[1], meter, weekly_cap=cap, http=rec.client())
    c.poll_interval = 0  # never actually sleep in tests
    return c


def create_request(rec: Recorder) -> httpx.Request:
    return next(r for r in rec.requests if r.method == "POST")


# --- the client -------------------------------------------------------------

def test_sends_bearer_auth_and_body_shape(meter, archived):
    rec = Recorder()
    make(rec, meter, archived).post("hello world", publish=True)
    req = create_request(rec)
    assert req.method == "POST"
    assert str(req.url) == f"https://api.typefully.com/v2/social-sets/{SOCIAL}/drafts"
    assert req.headers["Authorization"] == f"Bearer {KEY}"
    body = json.loads(req.content)
    assert body["platforms"]["x"]["enabled"] is True
    assert body["platforms"]["x"]["posts"] == [{"text": "hello world"}]
    assert body["publish_at"] == "now"
    assert body["draft_title"]


def test_thread_splits_into_multiple_posts(meter, archived):
    rec = Recorder()
    make(rec, meter, archived).post(["one", "two", "three"])
    body = json.loads(create_request(rec).content)
    assert body["platforms"]["x"]["posts"] == [{"text": "one"}, {"text": "two"}, {"text": "three"}]
    # a thread of three posted tweets counts three toward the weekly cap
    assert meter.spent() == pytest.approx(3.0)


def test_over_280_raises(meter, archived):
    rec = Recorder()
    with pytest.raises(XError):
        make(rec, meter, archived).post("x" * 281)
    with pytest.raises(XError):
        make(rec, meter, archived).post(["ok", "y" * 300])
    assert rec.requests == []  # nothing was sent


def test_empty_raises(meter, archived):
    with pytest.raises(XError):
        make(Recorder(), meter, archived).post("   ")


def test_draft_does_not_publish_or_count(meter, archived):
    rec = Recorder()
    out = make(rec, meter, archived).draft("just a draft")
    body = json.loads(create_request(rec).content)
    assert "publish_at" not in body
    assert out["published"] is False and out["status"] == "draft"
    assert meter.spent() == 0.0  # drafts never count against the cap
    # no GET poll happened
    assert all(r.method == "POST" for r in rec.requests)


def test_weekly_cap_refuses_after_seven(meter, archived):
    rec = Recorder()
    meter.add_usd(7.0, "earlier this week")
    out = make(rec, meter, archived, cap=7).post("one more")
    assert "refused" in out and out["published"] is False
    assert "7 posts a week" in out["refused"]
    assert rec.requests == []  # refused before any request; not raised
    # a draft is still allowed over the cap
    out2 = make(rec, meter, archived, cap=7).draft("drafts are fine")
    assert out2["status"] == "draft"


def test_archive_has_no_api_key(meter, archived):
    make(Recorder(), meter, archived).post("SECRETMESSAGE")
    rows, _ = archived
    dumped = json.dumps(rows)
    assert KEY not in dumped and "Authorization" not in dumped and "Bearer" not in dumped
    assert set(rows[0][1]) == {"kind", "n_posts", "published", "url", "draft_id"}
    assert rows[0][1] == {"kind": "x_post", "n_posts": 1, "published": True,
                          "url": "https://x.com/Raising_Chris/status/1", "draft_id": 99}


def test_non_2xx_returned_not_raised(meter, archived):
    rec = Recorder(create_status=402, create_body={"detail": "over your plan limit"})
    out = make(rec, meter, archived).post("nope")
    assert out["status_code"] == 402 and "over your plan limit" in out["error"]
    assert out["published"] is False
    assert meter.spent() == 0.0  # a failed create never counts
    rows, _ = archived
    assert rows[0][1]["published"] is False and rows[0][1]["url"] is None


def test_error_text_scrubs_api_key(meter, archived):
    rec = Recorder(create_status=400, create_body={"detail": f"bad token {KEY} rejected"})
    out = make(rec, meter, archived).post("nope")
    assert KEY not in out["error"] and "<redacted>" in out["error"]


def test_publish_polls_to_finished_and_returns_url(meter, archived):
    rec = Recorder(poll_states=["in_progress", "finished"])
    out = make(rec, meter, archived).post("shipping it")
    assert out["published"] is True
    assert out["url"] == "https://x.com/Raising_Chris/status/1"
    assert out["status"] == "finished"
    assert meter.spent() == pytest.approx(1.0)
    assert sum(1 for r in rec.requests if r.method == "GET") >= 2


def test_publish_stuck_returns_publishing_message(meter, archived):
    rec = Recorder(poll_states=[None])
    c = make(rec, meter, archived)
    c.poll_timeout = 0  # poll once, then give up
    out = c.post("free tier is slow")
    assert out["published"] is False
    assert "publishing" in out["message"] and "check X" in out["message"]
    # counted anyway: the tweets were accepted for publishing
    assert meter.spent() == pytest.approx(1.0)
    rows, _ = archived
    assert rows[0][1]["published"] is False


def test_publish_errored_state_surfaced(meter, archived):
    rec = Recorder(poll_states=["errored"])
    out = make(rec, meter, archived).post("something")
    assert out["published"] is False
    assert "publish_state" in out["message"] and "errored" in out["message"]


# --- the tool ---------------------------------------------------------------

class FakeX:
    def __init__(self, result=None):
        self.result = result if result is not None else {
            "published": True, "url": "https://x.com/Raising_Chris/status/9", "draft_id": 9, "n_posts": 1}
        self.calls = []

    def post(self, content, publish=True):
        self.calls.append((content, publish))
        return self.result


async def test_tool_not_configured(services):
    h = tools.make_handlers(services)
    assert "ask your parents" in out_text(await h["x_post"]({"text": "hi"}))


async def test_tool_happy_path_single(services):
    services.x = FakeX()
    services.secrets.x_handle = "Raising_Chris"
    h = tools.make_handlers(services)
    got = out_text(await h["x_post"]({"text": "hello", "publish": True}))
    assert services.x.calls == [("hello", True)]
    assert "Posted to X" in got and "@Raising_Chris" in got and "status/9" in got


async def test_tool_thread_json_parsed_to_list(services):
    services.x = FakeX()
    h = tools.make_handlers(services)
    await h["x_post"]({"thread_json": '["a", "b"]'})
    assert services.x.calls == [(["a", "b"], True)]


async def test_tool_bad_thread_json_is_text(services):
    services.x = FakeX()
    h = tools.make_handlers(services)
    assert "not valid JSON" in out_text(await h["x_post"]({"thread_json": "[nope"}))
    assert services.x.calls == []


async def test_tool_needs_content(services):
    services.x = FakeX()
    h = tools.make_handlers(services)
    assert "needs either text" in out_text(await h["x_post"]({}))
    assert services.x.calls == []


async def test_tool_over_cap_is_refusal_text(services):
    services.x = FakeX(result={"refused": "You've already posted 7 to X this week; the cap is 7 posts a week.",
                               "published": False})
    h = tools.make_handlers(services)
    assert "cap is 7 posts" in out_text(await h["x_post"]({"text": "one more"}))
    assert "refused" in archive_text(services)


async def test_tool_draft_message(services):
    services.x = FakeX(result={"status": "draft", "published": False, "draft_id": 5, "n_posts": 1})
    h = tools.make_handlers(services)
    got = out_text(await h["x_post"]({"text": "later", "publish": False}))
    assert services.x.calls == [("later", False)]
    assert "draft" in got.lower() and "5" in got


async def test_tool_error_dict_is_text(services):
    services.x = FakeX(result={"error": "over your plan limit", "status_code": 402})
    h = tools.make_handlers(services)
    assert "402" in out_text(await h["x_post"]({"text": "hi"}))


async def test_tool_publishing_message(services):
    services.x = FakeX(result={"status": "pending", "published": False, "draft_id": 3, "n_posts": 1,
                               "message": "publishing, check X"})
    h = tools.make_handlers(services)
    assert "publishing" in out_text(await h["x_post"]({"text": "hi"}))


def test_x_post_registered_and_excluded_from_sleep():
    from agent.sleep import SLEEP_EXCLUDED

    assert "x_post" in tools.TOOL_NAMES and "x_post" in tools.SCHEMAS
    assert "x_post" in SLEEP_EXCLUDED


# --- wiring -----------------------------------------------------------------

def test_meters_line_mentions_x_only_when_configured(services):
    assert "X this week" not in services.meters_line()
    services.x_meter = Meter("x", "week", services.cfg.state_dir, tz=services.cfg.tz)
    services.x_meter.add_usd(2, "test")
    services.x = FakeX()
    assert "· X this week 2 of 7 posts" in services.meters_line()
    assert "x" in services.meters


def test_build_wires_x_from_env(tmp_path, repo):
    from agent import wiring
    from agent.config import Config

    cfg = Config(repo_dir=str(repo), archive_dir=str(tmp_path / "a"), state_dir=str(tmp_path / "s"), dry_run=True)
    s = wiring.build(cfg, env={})
    assert s.x is None and s.x_meter is not None
    s = wiring.build(cfg, env={"TYPEFULLY_API_KEY": KEY, "TYPEFULLY_SOCIAL_SET": SOCIAL, "X_HANDLE": "Raising_Chris"})
    assert isinstance(s.x, XClient) and s.x.weekly_cap == 7
    assert s.secrets.typefully_api_key == KEY and s.secrets.x_social_set == SOCIAL
    assert s.secrets.x_handle == "Raising_Chris"


def test_config_reads_weekly_cap():
    from agent.config import ENV_KEYS, Config

    assert "X_WEEKLY_CAP" in ENV_KEYS
    assert Config.from_env({}).x_weekly_cap == 7
    assert Config.from_env({"X_WEEKLY_CAP": "3"}).x_weekly_cap == 3
