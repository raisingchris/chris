"""Nightly GCS backup: skip path, JWT-signed token exchange, object names, failure without leaking the key."""

import io
import json
import tarfile
from pathlib import Path

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fake_services import make_services
from freezegun import freeze_time

from agent import backup
from agent.backup import SCOPE, TOKEN_URL, run_backup

BUCKET = "chris-private-archive"


@pytest.fixture(scope="module")
def keypair():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    ).decode()
    pub = key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()
    return pem, pub


@pytest.fixture
def sa(keypair):
    pem, _ = keypair
    return {
        "type": "service_account",
        "client_email": "chris-backup@example.iam.gserviceaccount.com",
        "private_key_id": "kid-123",
        "private_key": pem,
    }


@pytest.fixture
def env(sa):
    return {"GCS_ARCHIVE_BUCKET": BUCKET, "GCS_ARCHIVE_SA_JSON": json.dumps(sa)}


@pytest.fixture
def services(tmp_path):
    s = make_services(tmp_path)
    (Path(s.cfg.archive_dir)).mkdir(parents=True, exist_ok=True)
    (Path(s.cfg.archive_dir) / "2026-09-06.jsonl").write_text('{"kind":"x"}\n')
    (Path(s.cfg.state_dir) / "last_runs.json").write_text("{}")
    minutes = tmp_path / "council_minutes"
    minutes.mkdir()
    (minutes / "2026-09-01.md").write_text("minutes")
    return s


class Recorder:
    """MockTransport handler that records every request and plays a scripted response."""

    def __init__(self, token_status=200, upload_status=200):
        self.requests: list[httpx.Request] = []
        self.token_status, self.upload_status = token_status, upload_status

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.url.host == "oauth2.googleapis.com":
            return httpx.Response(self.token_status, json={"access_token": "ya29.test", "expires_in": 3599})
        return httpx.Response(self.upload_status, json={"name": request.url.params.get("name")})

    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self))


def test_skipped_without_config(services):
    result = run_backup(services, env={})
    assert result["kind"] == "backup_skipped"
    assert result["missing"] == ["GCS_ARCHIVE_BUCKET", "GCS_ARCHIVE_SA_JSON"]
    assert services.archive.entries == [("backup", result)]

    services.archive.entries.clear()
    result = run_backup(services, env={"GCS_ARCHIVE_BUCKET": BUCKET})
    assert result["kind"] == "backup_skipped" and result["missing"] == ["GCS_ARCHIVE_SA_JSON"]


@freeze_time("2026-09-07 02:45:10")  # 22:45 on 2026-09-06 in America/New_York (EDT)
def test_upload_names_and_jwt(services, env, sa, keypair, monkeypatch):
    monkeypatch.setenv("COUNCIL_MINUTES_DIR", str(Path(services.cfg.state_dir).parent / "council_minutes"))
    rec = Recorder()
    result = run_backup(services, http=rec.client(), env=env)

    assert result["kind"] == "backup_done"
    assert result["objects"] == [
        "chris/2026-09-06/state-2245.tar.gz",
        "chris/2026-09-06/archive-2026-09-06.jsonl",
    ]
    assert result["bytes"] > 0
    assert services.archive.entries == [("backup", result)]

    token_req, tar_req, jsonl_req = rec.requests
    # token exchange: JWT-bearer grant, signed with the SA key, verifiable with its public half
    assert str(token_req.url) == TOKEN_URL and token_req.method == "POST"
    form = dict(httpx.QueryParams(token_req.content.decode()))
    assert form["grant_type"] == "urn:ietf:params:oauth:grant-type:jwt-bearer"
    _, pub = keypair
    header = jwt.get_unverified_header(form["assertion"])
    assert header["alg"] == "RS256" and header["kid"] == "kid-123"
    claims = jwt.decode(form["assertion"], pub, algorithms=["RS256"], audience=TOKEN_URL)
    assert claims["iss"] == sa["client_email"] and claims["scope"] == SCOPE
    assert claims["exp"] - claims["iat"] == 3600

    # uploads: media upload to the bucket, bearer token, right object names
    for req, name in ((tar_req, result["objects"][0]), (jsonl_req, result["objects"][1])):
        assert req.method == "POST"
        assert req.url.host == "storage.googleapis.com"
        assert req.url.path == f"/upload/storage/v1/b/{BUCKET}/o"
        assert req.url.params["uploadType"] == "media" and req.url.params["name"] == name
        assert req.headers["authorization"] == "Bearer ya29.test"
    assert jsonl_req.content == b'{"kind":"x"}\n'

    # the tarball holds all three private dirs under their basenames
    with tarfile.open(fileobj=io.BytesIO(tar_req.read()), mode="r:gz") as tar:
        names = set(tar.getnames())
    assert {"archive/2026-09-06.jsonl", "state/last_runs.json", "council_minutes/2026-09-01.md"} <= names
    assert result["bytes"] == len(tar_req.content) + len(jsonl_req.content)


@freeze_time("2026-09-07 02:45:10")
def test_no_archive_file_today_uploads_tar_only(services, env):
    (Path(services.cfg.archive_dir) / "2026-09-06.jsonl").unlink()
    rec = Recorder()
    result = run_backup(services, http=rec.client(), env=env)
    assert result["kind"] == "backup_done"
    assert result["objects"] == ["chris/2026-09-06/state-2245.tar.gz"]
    assert len(rec.requests) == 2


def test_failure_archived_without_the_key(services, env, sa):
    rec = Recorder(upload_status=403)
    result = run_backup(services, http=rec.client(), env=env)
    assert result["kind"] == "backup_failed" and result["error"] == "RuntimeError"
    assert result["objects"] == []
    dumped = json.dumps(services.archive.entries)
    assert "PRIVATE KEY" not in dumped and sa["private_key"][40:80] not in dumped
    assert "403" not in result.get("error", "")  # only the type; the message is not stored


def test_token_exchange_failure(services, env):
    rec = Recorder(token_status=401)
    result = run_backup(services, http=rec.client(), env=env)
    assert result["kind"] == "backup_failed" and result["error"] == "RuntimeError"
    assert len(rec.requests) == 1  # never got to upload


def test_bad_key_json_is_a_failure_not_a_crash(services, env):
    rec = Recorder()
    result = run_backup(services, http=rec.client(), env={**env, "GCS_ARCHIVE_SA_JSON": "{not json"})
    assert result["kind"] == "backup_failed" and result["error"] == "JSONDecodeError"
    assert rec.requests == []
    assert "not json" not in json.dumps(services.archive.entries)


def test_backup_dirs_env_override(services, monkeypatch, tmp_path):
    monkeypatch.setenv("COUNCIL_MINUTES_DIR", str(tmp_path / "elsewhere"))
    dirs = backup.backup_dirs(services.cfg)
    assert dirs == [Path(services.cfg.archive_dir), Path(services.cfg.state_dir), tmp_path / "elsewhere"]
    monkeypatch.delenv("COUNCIL_MINUTES_DIR")
    assert backup.backup_dirs(services.cfg)[2] == Path(services.cfg.state_dir).parent / "council_minutes"
