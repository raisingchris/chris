"""Keyless Google access for Chris's body: Fly OIDC → Workload Identity Federation → service account.

No Google key ever exists. The Fly machine mints a short-lived OIDC token over
its local socket; Google STS swaps it for a federated token; IAM Credentials
then impersonates the metrics service account. The provider resource and the
service-account address identify her parents' Google project, so they live only
in this process — never in a tool result, an exception message, or the archive.
"""

from __future__ import annotations

import re
import time
from typing import Callable

import httpx

FLY_SOCKET = "/.fly/api"
FLY_OIDC_URL = "http://localhost/v1/tokens/oidc"
STS_URL = "https://sts.googleapis.com/v1/token"
IAM_URL = "https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/{sa}:generateAccessToken"
CLOUD_SCOPE = "https://www.googleapis.com/auth/cloud-platform"
TIMEOUT_S = 30
LIFETIME_S = 3600
REFRESH_MARGIN_S = 300  # re-mint when less than ~5 minutes remain

_TOKEN_RE = re.compile(r"(ya29\.[A-Za-z0-9._-]+|Bearer\s+\S+|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9._-]+)")


def scrub(text: str) -> str:
    """Replace anything that looks like a bearer/JWT token with a placeholder."""
    return _TOKEN_RE.sub("[token]", str(text))


class GoogleAuthError(RuntimeError):
    """Token exchange failed. The message never carries a token or an identity."""


def fly_oidc_token(aud: str, http: httpx.Client | None = None) -> str:
    """Ask the Fly machine for an OIDC JWT with the given audience."""
    client = http or httpx.Client(transport=httpx.HTTPTransport(uds=FLY_SOCKET), timeout=TIMEOUT_S)
    r = client.post(FLY_OIDC_URL, json={"aud": aud})
    if not 200 <= r.status_code < 300:
        raise GoogleAuthError(f"Fly OIDC token request failed: HTTP {r.status_code}")
    tok = r.text.strip().strip('"')
    if not tok:
        raise GoogleAuthError("Fly OIDC token request returned nothing")
    return tok


class GoogleWIF:
    def __init__(self, provider_resource: str, sa_email: str, http: httpx.Client | None = None,
                 fly_token_fn: Callable[[str], str] | None = None):
        self._provider = provider_resource.strip().strip("/")
        self._sa = sa_email.strip()
        self._http = http or httpx.Client(timeout=TIMEOUT_S)
        self._fly = fly_token_fn or fly_oidc_token
        self._cache: dict[tuple[str, ...], tuple[str, float]] = {}

    @property
    def oidc_audience(self) -> str:
        return f"https://iam.googleapis.com/{self._provider}"

    @property
    def sts_audience(self) -> str:
        return f"//iam.googleapis.com/{self._provider}"

    def access_token(self, scopes: list[str]) -> str:
        key = tuple(sorted(scopes))
        hit = self._cache.get(key)
        if hit and hit[1] - time.time() > REFRESH_MARGIN_S:
            return hit[0]
        token, expires_at = self._mint(list(key))
        self._cache[key] = (token, expires_at)
        return token

    def _mint(self, scopes: list[str]) -> tuple[str, float]:
        oidc = self._fly(self.oidc_audience)
        r = self._http.post(STS_URL, data={
            "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
            "audience": self.sts_audience,
            "scope": CLOUD_SCOPE,
            "requested_token_type": "urn:ietf:params:oauth:token-type:access_token",
            "subject_token_type": "urn:ietf:params:oauth:token-type:jwt",
            "subject_token": oidc,
        })
        if not 200 <= r.status_code < 300:
            raise GoogleAuthError(f"Google STS exchange failed: HTTP {r.status_code}")
        federated = (self._json(r) or {}).get("access_token")
        if not federated:
            raise GoogleAuthError("Google STS exchange returned no access token")
        r = self._http.post(IAM_URL.format(sa=self._sa), json={"scope": scopes, "lifetime": f"{LIFETIME_S}s"},
                            headers={"Authorization": f"Bearer {federated}"})
        if not 200 <= r.status_code < 300:
            raise GoogleAuthError(f"Google service-account impersonation failed: HTTP {r.status_code}")
        body = self._json(r) or {}
        token = body.get("accessToken")
        if not token:
            raise GoogleAuthError("Google service-account impersonation returned no access token")
        return token, time.time() + LIFETIME_S

    @staticmethod
    def _json(r: httpx.Response):
        try:
            return r.json()
        except ValueError:
            return None
