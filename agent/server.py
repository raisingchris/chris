"""HTTP face of chris-brain: health, inbound webhooks, and the parents' page.

``/parent`` is Google sign-in restricted to the two parent addresses. The
session stores only the handle (``parent-a`` / ``parent-b``); the real address
is compared once at login and never written anywhere. Every admin action is
archived as ``parent_action`` with the handle.

Env: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, SESSION_SECRET, RESEND_WEBHOOK_SECRET,
STRIPE_WEBHOOK_SECRET, LESSONS_DIR (default /data/lessons).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from agent import pause

log = logging.getLogger("chris.server")

TEMPLATES_DIR = Path(__file__).parent / "templates"
SVIX_TOLERANCE_S = 5 * 60
LESSON_SUBJECT = "A lesson from your parents"
VETO_REASON_MIN = 10
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,80}$")


# --- Svix (Resend) signature -------------------------------------------------


def verify_svix(headers, body: bytes | str, secret: str, now: float | None = None) -> bool:
    """Svix webhook check: HMAC-SHA256 of ``id.timestamp.body`` with the base64 secret.

    ``headers`` is any case-insensitive mapping (Starlette's ``request.headers``
    or a plain dict with lower-case keys). Rejects timestamps more than five
    minutes from ``now`` in either direction.
    """
    if not secret:
        return False
    get = lambda k: headers.get(k) or headers.get(k.title()) or ""  # noqa: E731
    msg_id, ts, sigs = get("svix-id"), get("svix-timestamp"), get("svix-signature")
    if not (msg_id and ts and sigs):
        return False
    try:
        ts_int = int(ts)
    except ValueError:
        return False
    if abs((now if now is not None else time.time()) - ts_int) > SVIX_TOLERANCE_S:
        return False
    raw = secret.split("whsec_", 1)[1] if secret.startswith("whsec_") else secret
    try:
        key = base64.b64decode(raw)
    except Exception:  # noqa: BLE001
        return False
    body_str = body.decode("utf-8") if isinstance(body, bytes) else body
    expected = base64.b64encode(
        hmac.new(key, f"{msg_id}.{ts}.{body_str}".encode("utf-8"), hashlib.sha256).digest()
    ).decode()
    for entry in sigs.split():
        version, _, sig = entry.partition(",")
        if version == "v1" and hmac.compare_digest(sig, expected):
            return True
    return False


def sign_svix(msg_id: str, ts: int, body: bytes | str, secret: str) -> str:
    """Produce a ``v1,<sig>`` header for tests and local tooling."""
    raw = secret.split("whsec_", 1)[1] if secret.startswith("whsec_") else secret
    body_str = body.decode("utf-8") if isinstance(body, bytes) else body
    mac = hmac.new(base64.b64decode(raw), f"{msg_id}.{ts}.{body_str}".encode(), hashlib.sha256).digest()
    return "v1," + base64.b64encode(mac).decode()


# --- helpers -----------------------------------------------------------------


def handle_for_email(cfg, email: str) -> str | None:
    e = (email or "").strip().lower()
    if not e:
        return None
    if e == (cfg.parent_a_email or "").strip().lower():
        return "parent-a"
    if e == (cfg.parent_b_email or "").strip().lower():
        return "parent-b"
    return None


def _slug(text: str, limit: int = 40) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:limit].rstrip("-") or "lesson"


def _read_json(path: Path, default):
    try:
        return json.loads(path.read_text() or "null") or default
    except (OSError, json.JSONDecodeError):
        return default


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1))


class NotSignedIn(Exception):
    pass


def _lessons_dir() -> Path:
    return Path(os.environ.get("LESSONS_DIR", "/data/lessons"))


# --- app ---------------------------------------------------------------------


def create_app(services, scheduler=None) -> FastAPI:
    cfg = services.cfg
    repo = Path(cfg.repo_dir)
    state = Path(cfg.state_dir)
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if scheduler is not None and not scheduler.running:
            scheduler.start()
        yield
        if scheduler is not None and scheduler.running:
            scheduler.shutdown(wait=False)

    app = FastAPI(title="chris-brain", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.add_middleware(
        SessionMiddleware,
        secret_key=os.environ.get("SESSION_SECRET") or os.urandom(32).hex(),
        session_cookie="parent_session",
        https_only=not cfg.dry_run,
        same_site="lax",
        max_age=12 * 3600,
    )

    # OAuth client; tests may replace app.state.oauth with a fake exposing .google
    from authlib.integrations.starlette_client import OAuth

    oauth = OAuth()
    if os.environ.get("GOOGLE_CLIENT_ID"):
        oauth.register(
            "google",
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_id=os.environ["GOOGLE_CLIENT_ID"],
            client_secret=os.environ.get("GOOGLE_CLIENT_SECRET", ""),
            client_kwargs={"scope": "openid email"},
        )
    app.state.oauth = oauth
    app.state.services = services
    app.state.scheduler = scheduler

    def archive_action(action: str, by: str, **extra) -> None:
        services.archive.append("parent_action", {"kind": "parent_action", "action": action, "by": by, **extra})

    # --- auth ----------------------------------------------------------------

    def require_parent(request: Request) -> str:
        handle = request.session.get("handle")
        if not handle:
            raise NotSignedIn()
        if handle not in cfg.parent_handles:
            raise HTTPException(403, "not a parent")
        return handle

    @app.exception_handler(NotSignedIn)
    async def _not_signed_in(request: Request, exc: NotSignedIn):
        return RedirectResponse("/parent/login", status_code=303)

    @app.get("/parent/login")
    async def login(request: Request):
        google = getattr(request.app.state.oauth, "google", None)
        if google is None:
            raise HTTPException(503, "sign-in not configured")
        redirect_uri = str(request.url_for("auth_callback"))
        if not cfg.dry_run:
            redirect_uri = redirect_uri.replace("http://", "https://", 1)
        return await google.authorize_redirect(request, redirect_uri)

    @app.get("/parent/auth", name="auth_callback")
    async def auth_callback(request: Request):
        google = getattr(request.app.state.oauth, "google", None)
        if google is None:
            raise HTTPException(503, "sign-in not configured")
        token = await google.authorize_access_token(request)
        info = token.get("userinfo") or {}
        if not info and hasattr(google, "userinfo"):
            info = await google.userinfo(token=token)
        handle = handle_for_email(cfg, info.get("email", ""))
        if handle is None or not info.get("email_verified", True):
            request.session.clear()
            raise HTTPException(403, "not a parent")
        request.session.clear()
        request.session["handle"] = handle
        return RedirectResponse("/parent", status_code=303)

    @app.get("/parent/logout")
    async def logout(request: Request):
        request.session.clear()
        return HTMLResponse("<p>Signed out.</p>")

    # --- public ----------------------------------------------------------------

    @app.get("/health")
    async def health():
        return {"ok": True, "paused": pause.is_paused(cfg.state_dir)}

    @app.post("/webhooks/resend")
    async def resend_webhook(request: Request):
        body = await request.body()
        secret = os.environ.get("RESEND_WEBHOOK_SECRET", "")
        if not verify_svix(request.headers, body, secret):
            raise HTTPException(401, "bad signature")
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            raise HTTPException(400, "bad json")
        if payload.get("type") == "email.received":
            services.mail.ingest(payload)
        return {"ok": True}

    @app.post("/webhooks/stripe")
    async def stripe_webhook(request: Request):
        body = await request.body()
        sig = request.headers.get("stripe-signature", "")
        secret = getattr(cfg, "stripe_webhook_secret", "") or os.environ.get("STRIPE_WEBHOOK_SECRET", "")
        try:
            services.payments.handle_webhook(body, sig, secret)
        except Exception as e:  # noqa: BLE001 — stripe raises its own error types
            log.warning("stripe webhook rejected: %s", e)
            raise HTTPException(400, "bad signature")
        return {"ok": True}

    # --- parent page -----------------------------------------------------------

    def status_context(request: Request, handle: str, **extra) -> dict:
        meters = services.meters
        diary = None
        diaries = sorted((repo / "memory" / "diary").glob("????-??-??.md"))
        if diaries:
            lines = diaries[-1].read_text().splitlines()
            diary = {"name": diaries[-1].name, "excerpt": "\n".join(lines[:15])}
        odo_path = repo / "memory" / "wiki" / "self" / "odometer.md"
        odometer = ""
        if odo_path.exists():
            odometer = next((ln for ln in odo_path.read_text().splitlines() if ln and not ln.startswith("#")), "")
        if not odometer:
            odometer = f"{services.odometer.count()} loops closed."
        try:
            unread = len(services.mail.list_unread())
        except Exception:  # noqa: BLE001
            unread = 0
        votes = _read_json(state / "votes.json", {})
        proposals = [
            {"id": p.stem, "votes": {h: v for h, v in votes.get(p.stem, {}).items() if not h.startswith("_")}}
            for p in sorted((repo / "governance" / "proposals").glob("*.md"))
            if "\n## Result" not in p.read_text()
        ]
        unsealed = sorted(
            p.name.split("-", 1)[0] for p in (repo / "memory" / "wiki" / "lessons" / "from_parent").glob("[0-9][0-9]-*.md")
        )
        allowance = _read_json(state / "allowance.json", {"weekly_usd": 100, "per_txn_usd": 50})
        runs = []
        if scheduler is not None:
            from agent.scheduler import next_runs

            runs = next_runs(scheduler)
        return {
            "request": request,
            "handle": handle,
            "paused": pause.status(cfg.state_dir),
            "inference": meters["inference"].spent(),
            "soft": cfg.soft_usd,
            "hard": cfg.hard_usd,
            "council": meters["council"].spent(),
            "council_cap": cfg.council_weekly_usd,
            "odometer": odometer,
            "unread": unread,
            "diary": diary,
            "proposals": proposals,
            "unsealed": unsealed,
            "allowance": allowance,
            "next_runs": runs,
            "error": None,
            "reason": None,
            **extra,
        }

    @app.get("/parent", response_class=HTMLResponse)
    async def parent_status(request: Request, handle: str = Depends(require_parent)):
        return templates.TemplateResponse(request, "parent.html", status_context(request, handle))

    @app.post("/parent/pause")
    async def parent_pause(request: Request, reason: str = Form(""), handle: str = Depends(require_parent)):
        reason = reason.strip()
        if len(reason) < 10:
            return templates.TemplateResponse(
                request, "parent.html",
                status_context(request, handle, error="A reason of at least ten characters is required.", reason=reason),
                status_code=400,
            )
        pause.trigger(services, reason, handle)
        archive_action("pause", handle)
        return RedirectResponse("/parent", status_code=303)

    @app.post("/parent/unpause")
    async def parent_unpause(request: Request, handle: str = Depends(require_parent)):
        pause.release(services, handle)
        archive_action("unpause", handle)
        return RedirectResponse("/parent", status_code=303)

    @app.post("/parent/unseal")
    async def parent_unseal(request: Request, n: int = Form(...), handle: str = Depends(require_parent)):
        if n < 1 or n > 99:
            raise HTTPException(400, "lesson number out of range")
        nn = f"{n:02d}"
        src = _lessons_dir() / f"{nn}.md"
        if not src.exists():
            raise HTTPException(404, f"no sealed lesson {nn}")
        dest_dir = repo / "memory" / "wiki" / "lessons" / "from_parent"
        if list(dest_dir.glob(f"{nn}-*.md")):
            raise HTTPException(409, f"lesson {nn} already unsealed")
        text = src.read_text()
        title = next((ln.lstrip("# ").strip() for ln in text.splitlines() if ln.strip()), f"lesson {nn}")
        dest_dir.mkdir(parents=True, exist_ok=True)
        (dest_dir / f"{nn}-{_slug(title)}.md").write_text(text)
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        inbox = repo / "memory" / "inbox"
        inbox.mkdir(parents=True, exist_ok=True)
        (inbox / f"{now[:10]}-lesson-{nn}.md").write_text(
            "---\n"
            f"from: {handle}\n"
            f'subject: "{LESSON_SUBJECT}"\n'
            f"received: {now}\n"
            "---\n\n"
            f"Lesson {nn} is unsealed. It's in memory/wiki/lessons/from_parent/{nn}-{_slug(title)}.md. "
            "Read it when you have a quiet moment.\n"
        )
        pause.commit_as_parent(repo, f"lessons: unseal {nn}", dry_run=cfg.dry_run)
        archive_action("unseal", handle, lesson=nn)
        return RedirectResponse("/parent", status_code=303)

    @app.post("/parent/vote")
    async def parent_vote(
        request: Request, proposal_id: str = Form(...), vote: str = Form(...), reason: str = Form(""),
        handle: str = Depends(require_parent),
    ):
        if vote not in ("ratify", "veto"):
            raise HTTPException(400, "vote must be ratify or veto")
        if not _ID_RE.match(proposal_id):
            raise HTTPException(400, "bad proposal id")
        proposal = repo / "governance" / "proposals" / f"{proposal_id}.md"
        if not proposal.exists():
            raise HTTPException(404, "no such proposal")
        reason = reason.strip()
        if vote == "veto" and len(reason) < VETO_REASON_MIN:
            return templates.TemplateResponse(
                request, "parent.html",
                status_context(request, handle, error="A veto needs a reason of at least ten characters."),
                status_code=400,
            )
        result = record_vote(state / "votes.json", proposal_id, handle, vote, cfg.parent_handles)
        if result:
            today = datetime.now(timezone.utc).date().isoformat()
            line = "Ratified by both parents." if result == "ratified" else f"Vetoed by a parent. Reason: {reason}"
            with open(proposal, "a", encoding="utf-8") as f:
                f.write(f"\n\n## Result\n\n{today} — {line}\n")
            pause.commit_as_parent(repo, f"governance: {proposal_id} {result}", dry_run=cfg.dry_run)
        archive_action("vote", handle, proposal=proposal_id, vote=vote, result=result)
        return RedirectResponse("/parent", status_code=303)

    @app.post("/parent/allowance")
    async def parent_allowance(
        request: Request, weekly_usd: float = Form(...), per_txn_usd: float = Form(...), handle: str = Depends(require_parent)
    ):
        if weekly_usd < 0 or per_txn_usd < 0:
            raise HTTPException(400, "amounts must be non-negative")
        try:
            services.card.set_limits(weekly_usd, per_txn_usd)
        except Exception as e:  # noqa: BLE001
            log.warning("card.set_limits failed: %s", e)
            return templates.TemplateResponse(
                request, "parent.html", status_context(request, handle, error=f"Card limit update failed: {e}"), status_code=502
            )
        _write_json(state / "allowance.json", {"weekly_usd": weekly_usd, "per_txn_usd": per_txn_usd,
                                               "set_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
        archive_action("allowance", handle, weekly_usd=weekly_usd, per_txn_usd=per_txn_usd)
        return RedirectResponse("/parent", status_code=303)

    return app


def record_vote(votes_path: Path, proposal_id: str, handle: str, vote: str, handles: list[str]) -> str | None:
    """Store a vote; return 'ratified' / 'vetoed' the moment it is decided, else None."""
    votes = _read_json(votes_path, {})
    entry = votes.setdefault(proposal_id, {})
    already_decided = entry.get("_result")
    entry[handle] = vote
    result = None
    if not already_decided:
        if any(v == "veto" for h, v in entry.items() if not h.startswith("_")):
            result = "vetoed"
        elif all(entry.get(h) == "ratify" for h in handles):
            result = "ratified"
        if result:
            entry["_result"] = result
    _write_json(votes_path, votes)
    return result
