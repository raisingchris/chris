"""Shared fakes: a real Archive/Meter on tmp dirs, fake money modules, no network."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

from agent.archive import Archive
from agent.budget import Meter
from agent.config import Config
from agent.council import CouncilBudgetExceeded
from agent.mail import Mail
from agent.wiring import Secrets, Services

PARENT_A = "alice.realname@example.com"
PARENT_B = "bob.other@corp.example"


class FakeCard:
    def __init__(self):
        self.calls = 0

    def details(self):
        self.calls += 1
        return {"number": "4111111111111111", "expiry_month": 1, "expiry_year": 2030, "cvc": "123"}


class FakeLedger:
    def __init__(self):
        self.rows = []

    def add(self, type, amount, ccy, counterparty, memo, ref=""):
        row = {"type": type, "amount": f"{float(amount):.2f}", "ccy": ccy, "counterparty": counterparty,
               "memo": memo, "ref": ref}
        self.rows.append(row)
        return row

    def balance(self, ccy="USD"):
        return 0.0


class FakePayments:
    def create_link(self, amount_cents, ccy, name, description=""):
        return f"https://buy.stripe.com/test_{amount_cents}"


class FakeOdometer:
    def claim(self, loop_type, evidence_refs, note):
        if not evidence_refs:
            raise ValueError("a loop claim needs at least one evidence ref")
        return {"loop_type": loop_type, "refs": evidence_refs}

    def render_line(self, birthday: date) -> str:
        return "0 in world-days, 0 loops closed, 40 loops to next graduation."


class FakeCouncil:
    def __init__(self, exceeded=False):
        self.exceeded = exceeded
        self.asked = []

    def unseal_due(self):
        return []

    async def deliberate(self, question, context=""):
        self.asked.append(question)
        if self.exceeded:
            raise CouncilBudgetExceeded("The council has already spent $10.00 this week; the weekly cap is $10.00.")
        return SimpleNamespace(answers={"openai": "think twice", "qwen": "sleep on it"}, cost_usd=0.01,
                               minutes_path=Path("/private/20260906T0900-q.md"))


@pytest.fixture
def repo(tmp_path) -> Path:
    r = tmp_path / "repo"
    for d in ("memory/diary", "memory/inbox", "memory/wiki/self", "soul", "governance", "ledger"):
        (r / d).mkdir(parents=True)
    (r / "soul" / "vows.md").write_text("# Vows\n")
    (r / "memory" / "wiki" / "self" / "character.md").write_text("# Character\n\n## Diffs\n")
    return r


@pytest.fixture
def services(tmp_path, repo) -> Services:
    cfg = Config(
        repo_dir=str(repo), archive_dir=str(tmp_path / "archive"), state_dir=str(tmp_path / "state"),
        parent_a_email=PARENT_A, parent_b_email=PARENT_B, dry_run=True, canaries=["Alice Realname"],
    )
    archive = Archive(cfg.archive_dir, tz=cfg.tz)
    mail = Mail(repo, archive.append, {"parent-a": PARENT_A, "parent-b": PARENT_B}, cfg.chris_email, dry_run=True)
    return Services(
        cfg=cfg, secrets=Secrets(), archive=archive,
        inference=Meter("inference", "day", cfg.state_dir, tz=cfg.tz),
        council_meter=Meter("council", "week", cfg.state_dir, tz=cfg.tz),
        mail=mail, council=FakeCouncil(), ledger=FakeLedger(), card=FakeCard(),
        payments=FakePayments(), odometer=FakeOdometer(),
    )


def archive_text(services: Services) -> str:
    """Every byte ever archived, for 'never appears' assertions."""
    return "".join(p.read_text() for p in Path(services.cfg.archive_dir).glob("*.jsonl"))
