"""Inbound mail and payments by polling, for a body with no public address.

On Fly, Resend and Stripe pushed events to /webhooks/*. A body behind a home router has no
public URL, so the brain asks instead: every couple of minutes it lists received mail at Resend
and checkout events at Stripe, and files each new one through exactly the same path a webhook
would. Both paths are idempotent (mail on ``email_id``, payments on the receipt ref), and a
small seen-set in brain's state keeps a mail from being handled twice.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

log = logging.getLogger(__name__)

STATE_FILE = "inbound.json"
SEEN_MAX = 1000
FIRST_RUN_DAYS = 2   # on the first poll, look back this far (covers a cutover gap)
PAGE = 100
STRIPE_TYPES = ("checkout.session.completed", "checkout.session.async_payment_succeeded")


def _state_path(state_dir) -> Path:
    return Path(state_dir) / STATE_FILE


def load_state(state_dir) -> dict:
    try:
        data = json.loads(_state_path(state_dir).read_text())
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_state(state_dir, state: dict) -> None:
    p = _state_path(state_dir)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(state))
    tmp.replace(p)


def handle_received(services, payload: dict) -> str:
    """File one ``email.received`` event (webhook or poll). Returns what happened:
    'owner', 'filed', or 'filed_wake'. Raises AttachmentError when attachments aren't ready."""
    cfg = services.cfg
    if services.mail.is_owner_mail(payload, getattr(cfg, "owner_aliases", ())):
        # A parent's account mail (a login or claim link): forwarded to them, never filed for her.
        services.mail.forward_owner_mail(payload)
        return "owner"
    path = services.mail.ingest(payload)
    from agent.mail import filed_blank, filed_job_alert, filed_report

    try:
        return _wake_kind(services, path, filed_blank, filed_job_alert, filed_report)
    except Exception as exc:  # noqa: BLE001 — the mail is already filed; a wake is a bonus
        log.warning("mail wake check failed: %s", exc)
        return "filed"


def _wake_kind(services, path, filed_blank, filed_job_alert, filed_report) -> str:
    if filed_blank(path):
        services.archive.append("mail_wake_skipped", {"kind": "mail_wake_skipped", "reason": "empty_body"})
    elif filed_report(path):
        services.archive.append("mail_wake_skipped", {"kind": "mail_wake_skipped", "reason": "dmarc_report"})
    elif filed_job_alert(path):
        services.archive.append("mail_wake_skipped", {"kind": "mail_wake_skipped", "reason": "job_alert_batched"})
    else:
        return "filed_wake"
    return "filed"


def _created(item: dict) -> datetime | None:
    raw = str(item.get("created_at") or "")
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00").replace(" ", "T", 1))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


MAX_PAGES = 10


def _list_received(api_key: str, stop=lambda page: False) -> list[dict]:
    """Received mail, newest first, following Resend's cursor until a page ``stop`` says is
    already known (or MAX_PAGES), so a backlog of more than one page isn't dropped."""
    import resend

    resend.api_key = api_key
    out: list[dict] = []
    after = None
    for _ in range(MAX_PAGES):
        params = {"limit": PAGE, **({"after": after} if after else {})}
        got = resend.Emails.Receiving.list(params)
        got = got if isinstance(got, dict) else dict(got)
        page = [dict(i) for i in (got.get("data") or [])]
        out.extend(page)
        if not page or not got.get("has_more") or stop(page):
            break
        after = str(page[-1].get("id") or "")
        if not after:
            break
    return out


def poll_mail(services, list_fn=None, now: datetime | None = None) -> dict:
    """List recent received mail; file every one not yet seen. Returns counts; 'wake' says
    whether a mail worth an extra sitting arrived."""
    from agent.attachments import AttachmentError

    now = now or datetime.now(timezone.utc)
    state_dir = services.cfg.state_dir
    state = load_state(state_dir)
    seen = list(state.get("mail_seen") or [])
    seen_set = set(seen)
    first = "mail_seen" not in state
    since = now - timedelta(days=FIRST_RUN_DAYS)
    key = getattr(services.mail, "resend_api_key", None) or ""

    def known(page: list[dict]) -> bool:
        # A page is "known" once it reaches mail we've seen (or, first run, mail older than the lookback).
        if first:
            return any((_created(i) or since) < since for i in page)
        return any(str(i.get("id") or "") in seen_set for i in page)

    items = (list_fn or _list_received)(key, known)
    out = {"new": 0, "owner": 0, "pending": 0, "wake": False}

    def remember(eid: str) -> None:
        # Saved after every item, so a later failure can't make a forwarded mail go out twice.
        seen.append(eid); seen_set.add(eid)
        state = load_state(state_dir)   # re-read: the stripe poll shares the file
        state["mail_seen"] = seen[-SEEN_MAX:]
        save_state(state_dir, state)

    # Oldest first, so her inbox fills in arrival order.
    for item in sorted(items, key=lambda i: str(i.get("created_at") or "")):
        eid = str(item.get("id") or "")
        if not eid or eid in seen_set:
            continue
        created = _created(item)
        if first and (created is None or created < since):
            remember(eid)
            continue
        payload = {"type": "email.received", "created_at": item.get("created_at"),
                   "data": {**item, "email_id": eid}}
        try:
            what = handle_received(services, payload)
        except AttachmentError:
            out["pending"] += 1   # not marked seen: the next poll tries again
            continue
        remember(eid)
        out["new"] += 1
        out["owner"] += what == "owner"
        out["wake"] = out["wake"] or what == "filed_wake"
    state = load_state(state_dir)
    if "mail_seen" not in state:   # first run with nothing to file still counts as the first run
        state["mail_seen"] = seen[-SEEN_MAX:]
        save_state(state_dir, state)
    return out


def poll_payments(services, list_fn=None, now: float | None = None) -> dict:
    """List Stripe checkout events since the last poll and record each, as the webhook would."""
    payments = getattr(services, "payments", None)
    if payments is None or not getattr(payments, "_key", ""):
        return {"events": 0}
    now = now or time.time()
    state_dir = services.cfg.state_dir
    state = load_state(state_dir)
    after = int(state.get("stripe_after") or (now - FIRST_RUN_DAYS * 86400))
    done = set(state.get("stripe_seen") or [])
    # Inclusive of the boundary second (a later event can share it); event ids dedupe.
    events = [e for e in (list_fn or payments.list_events)(after, STRIPE_TYPES) if e.get("id") not in done]
    newest = after
    seen_ids = list(state.get("stripe_seen") or [])
    for event in sorted(events, key=lambda e: int(e.get("created") or 0)):
        payments.handle_event(event)
        newest = max(newest, int(event.get("created") or 0))
        seen_ids.append(event.get("id"))
        state = load_state(state_dir)
        state["stripe_after"] = newest
        state["stripe_seen"] = seen_ids[-SEEN_MAX:]
        save_state(state_dir, state)
    state = load_state(state_dir)
    state.setdefault("stripe_after", newest)
    save_state(state_dir, state)
    return {"events": len(events)}
