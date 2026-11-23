import json

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from agent.google_auth import GoogleAuthError, GoogleSAKey


def key_json():
    k = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                          serialization.NoEncryption()).decode()
    return json.dumps({"client_email": "sa@p.iam.gserviceaccount.com", "private_key": pem,
                       "private_key_id": "kid1"}), k.public_key()


def test_mints_and_caches_token():
    kj, pub = key_json()
    seen = []

    def handler(req):
        form = dict(x.split("=", 1) for x in req.content.decode().split("&"))
        claims = jwt.decode(form["assertion"], pub, algorithms=["RS256"], audience="https://oauth2.googleapis.com/token")
        seen.append(claims)
        return httpx.Response(200, json={"access_token": "ya29.t", "expires_in": 3600})

    g = GoogleSAKey(kj, http=httpx.Client(transport=httpx.MockTransport(handler)))
    assert g.access_token(["s2", "s1"]) == "ya29.t"
    assert g.access_token(["s1", "s2"]) == "ya29.t"
    assert len(seen) == 1 and seen[0]["scope"] == "s1 s2"


def test_error_never_echoes_body():
    kj, _ = key_json()
    g = GoogleSAKey(kj, http=httpx.Client(transport=httpx.MockTransport(
        lambda r: httpx.Response(400, json={"error": "sa@p.iam.gserviceaccount.com bad"}))))
    with pytest.raises(GoogleAuthError) as e:
        g.access_token(["s"])
    assert "sa@" not in str(e.value) and "400" in str(e.value)
