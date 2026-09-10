"""Fake ``Services`` for pause / server / scheduler tests. Nothing here touches the network."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from agent.config import Config


class FakeArchive:
    def any(self, kind, payload_kind=None):
        return any(r[0] == kind and (payload_kind is None or r[1].get('kind') == payload_kind) for r in self.entries)

    def __init__(self):
        self.entries: list[tuple[str, dict]] = []
        self.days: dict[str, list[dict]] = {}  # date → full records, for read_day

    def read_day(self, date):
        return list(self.days.get(date, []))

    def append(self, kind, payload):
        self.entries.append((kind, payload))
        return f"archive:2026-09-06#{len(self.entries)}"

    def kinds(self):
        return [k for k, _ in self.entries]


class FakeCard:
    def __init__(self, fail=False):
        self.calls: list[tuple] = []
        self.fail = fail

    def _rec(self, *call):
        self.calls.append(call)
        if self.fail:
            raise RuntimeError("airwallex down")

    def freeze(self):
        self._rec("freeze")

    def unfreeze(self):
        self._rec("unfreeze")

    def set_limits(self, weekly_usd, per_txn_usd):
        self._rec("set_limits", weekly_usd, per_txn_usd)


class FakeMail:
    def __init__(self):
        self.sent: list[dict] = []
        self.ingested: list[dict] = []
        self.unread: list[str] = []

    def send(self, to, subject, body, **kw):
        self.sent.append({"to": to, "subject": subject, "body": body})
        return {"dry_run": True}

    def ingest(self, payload):
        self.ingested.append(payload)
        return Path("inbox.md")

    def list_unread(self):
        return list(self.unread)


class FakeMeter:
    def __init__(self, spent=0.0):
        self._spent = spent

    def spent(self):
        return self._spent

    def exceeded(self, cap):
        return self._spent >= cap


class FakePayments:
    def __init__(self):
        self.calls: list[tuple] = []

    def handle_webhook(self, body, sig, secret):
        self.calls.append((body, sig, secret))
        if sig != "good":
            raise ValueError("bad stripe signature")
        return {"amount": 1.0}


class FakeCouncil:
    def __init__(self):
        self.unsealed = 0

    def unseal_due(self):
        self.unsealed += 1
        return []


class FakeOdometer:
    def count(self):
        return 3


def make_services(tmp_path: Path, **cfg_overrides) -> SimpleNamespace:
    repo = tmp_path / "repo"
    state = tmp_path / "state"
    for d in ("governance/proposals", "memory/inbox", "memory/diary", "memory/wiki/self",
              "memory/wiki/lessons/from_parent"):
        (repo / d).mkdir(parents=True, exist_ok=True)
    state.mkdir(exist_ok=True)
    cfg = Config(
        repo_dir=str(repo),
        state_dir=str(state),
        archive_dir=str(tmp_path / "archive"),
        parent_a_email="alice.real@example.com",
        parent_b_email="Bob.Real@example.com",
        dry_run=True,
        **cfg_overrides,
    )
    return SimpleNamespace(
        cfg=cfg,
        repo_dir=repo,
        state_dir=state,
        archive=FakeArchive(),
        card=FakeCard(),
        mail=FakeMail(),
        meters={"inference": FakeMeter(4.2), "council": FakeMeter(1.5)},
        payments=FakePayments(),
        council=FakeCouncil(),
        odometer=FakeOdometer(),
        ledger=None,
    )
