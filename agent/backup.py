"""Nightly off-box backup of Chris's private state to a write-only GCS bucket.

Tars ``archive_dir``, ``state_dir`` and the council minutes into one gzip and
uploads it, plus today's archive JSONL on its own, to an append-only bucket.
Objects carry the time of day so nothing is ever overwritten.

Env (brain-only): ``GCS_ARCHIVE_BUCKET`` and ``GCS_ARCHIVE_SA_JSON`` — the
service-account key as JSON. Without both the backup is skipped and archived
as such. No Google SDK: a self-signed RS256 JWT is exchanged for a bearer
token over plain HTTPS, then the bytes are posted to the JSON upload API.
The key never appears in logs or the archive — only error *types* do.
"""

from __future__ import annotations

import io
import json
import logging
import os
import tarfile
import tempfile
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
import jwt

log = logging.getLogger("chris.backup")

TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = "https://storage.googleapis.com/upload/storage/v1/b/{bucket}/o"
SCOPE = "https://www.googleapis.com/auth/devstorage.write_only"
PREFIX = "chris"
JWT_TTL_S = 3600
HTTP_TIMEOUT_S = 120


def backup_dirs(cfg) -> list[Path]:
    """The three private directories, in a stable order: archive, state, council minutes."""
    state = Path(cfg.state_dir)
    minutes = Path(os.environ.get("COUNCIL_MINUTES_DIR") or state.parent / "council_minutes")
    return [Path(cfg.archive_dir), state, minutes]


def make_tarball(dirs: list[Path], out: Path) -> int:
    """Write a gzip tar of every existing directory in ``dirs`` (each under its own basename); return its size."""
    with tarfile.open(out, "w:gz") as tar:
        for d in dirs:
            if d.is_dir():
                tar.add(d, arcname=d.name)
    return out.stat().st_size


def build_jwt(sa: dict, now: float | None = None, scope: str = SCOPE) -> str:
    """Self-signed RS256 assertion for the OAuth2 JWT-bearer grant."""
    iat = int(now if now is not None else time.time())
    claims = {
        "iss": sa["client_email"],
        "scope": scope,
        "aud": TOKEN_URL,
        "iat": iat,
        "exp": iat + JWT_TTL_S,
    }
    headers = {"kid": sa["private_key_id"]} if sa.get("private_key_id") else None
    return jwt.encode(claims, sa["private_key"], algorithm="RS256", headers=headers)


def fetch_access_token(http: httpx.Client, sa: dict) -> str:
    r = http.post(
        TOKEN_URL,
        data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": build_jwt(sa)},
        timeout=HTTP_TIMEOUT_S,
    )
    if r.status_code != 200:
        raise RuntimeError(f"token exchange returned {r.status_code}")
    token = r.json().get("access_token")
    if not token:
        raise RuntimeError("token exchange returned no access_token")
    return token


def upload_object(http: httpx.Client, token: str, bucket: str, name: str, data: bytes | io.IOBase,
                  content_type: str = "application/octet-stream") -> None:
    """Media upload of one object. Raises on any non-2xx (409 = already exists, i.e. append-only violated)."""
    r = http.post(
        UPLOAD_URL.format(bucket=bucket),
        params={"uploadType": "media", "name": name},
        headers={"Authorization": f"Bearer {token}", "Content-Type": content_type},
        content=data,
        timeout=HTTP_TIMEOUT_S,
    )
    if not (200 <= r.status_code < 300):
        raise RuntimeError(f"upload of {name} returned {r.status_code}")


def run_backup(services, http: httpx.Client | None = None, env: dict[str, str] | None = None) -> dict:
    """Tar + upload; archives ``backup_skipped`` / ``backup_done`` / ``backup_failed``. Never raises."""
    e = os.environ if env is None else env
    cfg = services.cfg
    bucket = e.get("GCS_ARCHIVE_BUCKET", "").strip()
    sa_json = e.get("GCS_ARCHIVE_SA_JSON", "")
    if not bucket or not sa_json:
        missing = [k for k, v in (("GCS_ARCHIVE_BUCKET", bucket), ("GCS_ARCHIVE_SA_JSON", sa_json)) if not v]
        log.info("backup skipped: %s not set", ", ".join(missing))
        payload = {"kind": "backup_skipped", "missing": missing}
        services.archive.append("backup", payload)
        return payload

    now = datetime.now(ZoneInfo(cfg.tz))
    day, hhmm = now.strftime("%Y-%m-%d"), now.strftime("%H%M")
    tar_name = f"{PREFIX}/{day}/state-{hhmm}.tar.gz"
    jsonl_name = f"{PREFIX}/{day}/archive-{day}.jsonl"
    objects: list[str] = []
    total = 0
    own_client = http is None
    tmp = None
    try:
        sa = json.loads(sa_json)
        if http is None:
            http = httpx.Client()
        with tempfile.NamedTemporaryFile(prefix="chris-backup-", suffix=".tar.gz", delete=False) as f:
            tmp = Path(f.name)
        size = make_tarball(backup_dirs(cfg), tmp)
        token = fetch_access_token(http, sa)
        with open(tmp, "rb") as f:
            upload_object(http, token, bucket, tar_name, f, "application/gzip")
        objects.append(tar_name)
        total += size
        jsonl = Path(cfg.archive_dir) / f"{day}.jsonl"
        if jsonl.is_file():
            data = jsonl.read_bytes()
            upload_object(http, token, bucket, jsonl_name, data, "application/x-ndjson")
            objects.append(jsonl_name)
            total += len(data)
    except Exception as exc:  # noqa: BLE001 — never let the key or its errors escape
        err = type(exc).__name__
        log.warning("backup failed: %s", err)
        payload = {"kind": "backup_failed", "error": err, "objects": objects, "bytes": total}
        services.archive.append("backup", payload)
        return payload
    finally:
        if tmp is not None:
            try:
                tmp.unlink()
            except OSError:
                pass
        if own_client and http is not None:
            http.close()
    log.info("backup done: %d object(s), %d bytes", len(objects), total)
    payload = {"kind": "backup_done", "bucket": bucket, "objects": objects, "bytes": total}
    services.archive.append("backup", payload)
    return payload
