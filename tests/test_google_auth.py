"""Keyless Google auth: Fly OIDC → STS → SA impersonation, cached, no token or identity in errors."""

import json
from urllib.parse import parse_qs

import httpx
import pytest

from agent import google_auth
from agent.google_auth import GoogleAuthError, GoogleWIF, scrub

PROVIDER = "projects/961991115893/locations/global/workloadIdentityPools/flyio/providers/chris-brain"
SA = "chris-metrics@example-project.iam.gserviceaccount.com"
OIDC = "eyJhbGciOiJSUzI1NiJ9.eyJhdWQiOiJ4In0.sigsigsigsig"
FEDERATED = "ya29.federated-token-abc"
SA_TOKEN = "ya29.sa-token-xyz"


class Google:
    """MockTransport for sts.googleapis.com + iamcredentials.googleapis.com."""

    def __init__(self, sts_status=200, iam_status=200, sa_token=SA_TOKEN):
        self.sts_status, self.iam_status, self.sa_token = sts_status, iam_status, sa_token
        self.requests: list[httpx.Request] = []
        self.mints = 0

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.url.host == "sts.googleapis.com":
            if self.sts_status != 200:
                return httpx.Response(self.sts_status, json={"error": "invalid_grant",
                                                             "error_description": f"bad token {OIDC}"})
            return httpx.Response(200, json={"access_token": FEDERATED, "token_type": "Bearer", "expires_in": 3599})
        if request.url.host == "iamcredentials.googleapis.com":
            if self.iam_status != 200:
                return httpx.Response(self.iam_status, json={"error": {"code": 403, "message": f"denied for {SA}"}})
            self.mints += 1
            return httpx.Response(200, json={"accessToken": f"{self.sa_token}-{self.mints}",
                                             "expireTime": "2030-01-01T00:00:00Z"})
        return httpx.Response(404)

    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self.handler))


@pytest.fixture
def fly():
    calls = []

    def fn(aud: str) -> str:
        calls.append(aud)
        return OIDC

    fn.calls = calls
    return fn


def make(g: Google, fly) -> GoogleWIF:
    return GoogleWIF(PROVIDER, SA, http=g.client(), fly_token_fn=fly)


def test_full_exchange_shapes(fly):
    g = Google()
    tok = make(g, fly).access_token(["https://www.googleapis.com/auth/analytics.readonly"])
    assert tok == f"{SA_TOKEN}-1"
    assert fly.calls == [f"https://iam.googleapis.com/{PROVIDER}"]
    sts, iam = g.requests
    assert sts.method == "POST" and str(sts.url) == "https://sts.googleapis.com/v1/token"
    form = {k: v[0] for k, v in parse_qs(sts.content.decode()).items()}
    assert form == {
        "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
        "audience": f"//iam.googleapis.com/{PROVIDER}",
        "scope": "https://www.googleapis.com/auth/cloud-platform",
        "requested_token_type": "urn:ietf:params:oauth:token-type:access_token",
        "subject_token_type": "urn:ietf:params:oauth:token-type:jwt",
        "subject_token": OIDC,
    }
    assert str(iam.url) == (f"https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/{SA}"
                            ":generateAccessToken")
    assert iam.headers["Authorization"] == f"Bearer {FEDERATED}"
    assert json.loads(iam.content) == {"scope": ["https://www.googleapis.com/auth/analytics.readonly"],
                                       "lifetime": "3600s"}


def test_cached_until_near_expiry(fly, monkeypatch):
    g = Google()
    w = make(g, fly)
    scopes = ["https://www.googleapis.com/auth/webmasters.readonly"]
    t0 = 1_000_000.0
    monkeypatch.setattr(google_auth.time, "time", lambda: t0)
    assert w.access_token(scopes) == f"{SA_TOKEN}-1"
    assert w.access_token(list(reversed(scopes))) == f"{SA_TOKEN}-1"  # same scopes, any order
    assert g.mints == 1 and len(fly.calls) == 1
    monkeypatch.setattr(google_auth.time, "time", lambda: t0 + 3600 - 299)  # inside the 5-minute margin
    assert w.access_token(scopes) == f"{SA_TOKEN}-2"
    assert g.mints == 2
    # A different scope set is its own cache entry.
    assert w.access_token(["https://www.googleapis.com/auth/analytics.readonly"]) == f"{SA_TOKEN}-3"


@pytest.mark.parametrize("kw,needle", [({"sts_status": 400}, "STS"), ({"iam_status": 403}, "impersonation")])
def test_failures_raise_without_tokens_or_identity(fly, kw, needle):
    w = make(Google(**kw), fly)
    with pytest.raises(GoogleAuthError) as ei:
        w.access_token(["s"])
    msg = str(ei.value)
    assert needle in msg
    for secret in (OIDC, FEDERATED, SA_TOKEN, SA, PROVIDER, "961991115893"):
        assert secret not in msg


def test_fly_failure_propagates(fly):
    def bad(aud):
        raise GoogleAuthError("Fly OIDC token request failed: HTTP 500")

    w = GoogleWIF(PROVIDER, SA, http=Google().client(), fly_token_fn=bad)
    with pytest.raises(GoogleAuthError, match="Fly OIDC"):
        w.access_token(["s"])


def test_fly_oidc_token_posts_aud_over_socket_client():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, text=OIDC)

    tok = google_auth.fly_oidc_token("https://iam.googleapis.com/x", http=httpx.Client(transport=httpx.MockTransport(handler)))
    assert tok == OIDC
    assert str(seen[0].url) == "http://localhost/v1/tokens/oidc"
    assert json.loads(seen[0].content) == {"aud": "https://iam.googleapis.com/x"}


def test_fly_oidc_token_error_status():
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(503, text="no")))
    with pytest.raises(GoogleAuthError, match="HTTP 503"):
        google_auth.fly_oidc_token("aud", http=client)


def test_scrub_removes_token_shapes():
    s = scrub(f"Authorization: Bearer {SA_TOKEN} and {FEDERATED} and jwt {OIDC} end")
    assert SA_TOKEN not in s and FEDERATED not in s and OIDC not in s
    assert s.endswith("end")
    assert scrub("plain text") == "plain text"
