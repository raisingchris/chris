from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from agent import inbound
from agent.attachments import AttachmentError


class FakeMail:
    def __init__(self, tmp_path, fail_ids=()):
        self.resend_api_key = "k"
        self.ingested, self.forwarded = [], []
        self.fail_ids = set(fail_ids)
        self.tmp = tmp_path

    def is_owner_mail(self, payload, aliases):
        return "owner@x" in str(payload["data"].get("to"))

    def forward_owner_mail(self, payload):
        self.forwarded.append(payload["data"]["email_id"])

    def ingest(self, payload):
        eid = payload["data"]["email_id"]
        if eid in self.fail_ids:
            raise AttachmentError("pending")
        self.ingested.append(eid)
        p = self.tmp / f"{eid}.md"
        p.write_text("---\nfrom: a\n---\nhello\n")
        return p


def services(tmp_path, **kw):
    archive = []
    return SimpleNamespace(cfg=SimpleNamespace(state_dir=str(tmp_path), owner_aliases=("owner@x",)),
                           mail=FakeMail(tmp_path, **kw), archive=SimpleNamespace(append=lambda k, d: archive.append(k)),
                           payments=None, _archive=archive)


NOW = datetime(2026, 11, 23, 12, tzinfo=timezone.utc)


def item(eid, hours_ago, to="chris@x"):
    return {"id": eid, "to": [to], "from": "s@y", "subject": "hi",
            "created_at": (NOW - timedelta(hours=hours_ago)).isoformat()}


def test_first_poll_files_recent_and_skips_old(tmp_path, monkeypatch):
    monkeypatch.setattr("agent.mail.filed_blank", lambda p: False)
    monkeypatch.setattr("agent.mail.filed_report", lambda p: False)
    monkeypatch.setattr("agent.mail.filed_job_alert", lambda p: False)
    s = services(tmp_path)
    got = inbound.poll_mail(s, list_fn=lambda k, stop=None: [item("old", 100), item("a", 3), item("b", 1)], now=NOW)
    assert s.mail.ingested == ["a", "b"]          # oldest first, old one skipped
    assert got["new"] == 2 and got["wake"] is True
    # second poll: nothing new, nothing re-filed, old stays skipped
    got = inbound.poll_mail(s, list_fn=lambda k, stop=None: [item("old", 100), item("a", 3), item("b", 1)], now=NOW)
    assert got["new"] == 0 and s.mail.ingested == ["a", "b"]


def test_later_polls_file_any_age_and_owner_mail_is_forwarded(tmp_path, monkeypatch):
    monkeypatch.setattr("agent.mail.filed_blank", lambda p: True)
    s = services(tmp_path)
    inbound.poll_mail(s, list_fn=lambda k, stop=None: [], now=NOW)            # first run: empty
    got = inbound.poll_mail(s, list_fn=lambda k, stop=None: [item("late", 200), item("o", 1, to="owner@x")], now=NOW)
    assert s.mail.ingested == ["late"] and s.mail.forwarded == ["o"]
    assert got["owner"] == 1 and got["wake"] is False             # blank body: no wake


def test_pending_attachments_retry_next_poll(tmp_path, monkeypatch):
    monkeypatch.setattr("agent.mail.filed_blank", lambda p: False)
    monkeypatch.setattr("agent.mail.filed_report", lambda p: False)
    monkeypatch.setattr("agent.mail.filed_job_alert", lambda p: False)
    s = services(tmp_path, fail_ids={"x"})
    got = inbound.poll_mail(s, list_fn=lambda k, stop=None: [item("x", 1)], now=NOW)
    assert got["pending"] == 1 and s.mail.ingested == []
    s.mail.fail_ids.clear()
    inbound.poll_mail(s, list_fn=lambda k, stop=None: [item("x", 1)], now=NOW)
    assert s.mail.ingested == ["x"]


def test_payments_poll_advances_cursor(tmp_path):
    handled = []
    calls = []
    pay = SimpleNamespace(_key="sk", handle_event=lambda e: handled.append(e["id"]),
                          list_events=lambda after, types: calls.append(after) or
                          [e for e in [{"id": "e1", "created": 1000}, {"id": "e2", "created": 2000}] if e["created"] > after])
    s = services(tmp_path)
    s.payments = pay
    assert inbound.poll_payments(s, now=1500 + 2 * 86400)["events"] == 1   # first run: look back two days
    assert handled == ["e2"]
    inbound.poll_payments(s, now=5000 + 2 * 86400)
    assert calls[-1] == 2000 and handled == ["e2"]


def test_payments_poll_skips_without_stripe(tmp_path):
    assert inbound.poll_payments(services(tmp_path)) == {"events": 0}


def test_payments_boundary_second_and_dedupe(tmp_path):
    handled = []
    events = [{"id": "e1", "created": 1000}]
    pay = SimpleNamespace(_key="sk", handle_event=lambda e: handled.append(e["id"]),
                          list_events=lambda after, types: [e for e in events if e["created"] >= after])
    s = services(tmp_path)
    s.payments = pay
    inbound.poll_payments(s, now=1500)
    events.append({"id": "e2", "created": 1000})   # same second, shows up later
    inbound.poll_payments(s, now=1600)
    assert handled == ["e1", "e2"]


def test_failure_mid_poll_keeps_earlier_owner_forward(tmp_path, monkeypatch):
    s = services(tmp_path)
    inbound.poll_mail(s, list_fn=lambda k, stop=None: [], now=NOW)
    boom = item("boom", 1)

    def ingest(payload):
        raise RuntimeError("resend down")
    s.mail.ingest = ingest
    with pytest.raises(RuntimeError):
        inbound.poll_mail(s, list_fn=lambda k, stop=None: [item("o", 2, to="owner@x"), boom], now=NOW)
    with pytest.raises(RuntimeError):
        inbound.poll_mail(s, list_fn=lambda k, stop=None: [item("o", 2, to="owner@x"), boom], now=NOW)
    assert s.mail.forwarded == ["o"]


def test_list_received_follows_cursor(monkeypatch):
    import resend
    pages = {None: {"data": [{"id": "c"}, {"id": "b"}], "has_more": True},
             "b": {"data": [{"id": "a"}], "has_more": False}}
    calls = []
    monkeypatch.setattr(resend.Emails.Receiving, "list", lambda params: calls.append(params.get("after")) or pages[params.get("after")])
    got = inbound._list_received("k")
    assert [i["id"] for i in got] == ["c", "b", "a"] and calls == [None, "b"]
    calls.clear()
    got = inbound._list_received("k", stop=lambda page: True)
    assert [i["id"] for i in got] == ["c", "b"] and calls == [None]
