from types import SimpleNamespace

import pytest

import agent.payments as payments
from agent.ledger import Ledger


class FakeStripe:
    """Stands in for the `stripe` module: records calls, returns canned objects."""

    def __init__(self, event=None):
        self.calls = []
        self.api_key = None
        self.event = event
        fs = self

        class Price:
            @staticmethod
            def create(**kw):
                fs.calls.append(("Price.create", kw))
                return SimpleNamespace(id="price_1")

        class PaymentLink:
            @staticmethod
            def create(**kw):
                fs.calls.append(("PaymentLink.create", kw))
                return SimpleNamespace(id="plink_1", url="https://buy.stripe.com/test_x")

        class Webhook:
            @staticmethod
            def construct_event(payload, sig, secret):
                fs.calls.append(("construct_event", payload, sig, secret))
                if fs.event is None:
                    raise ValueError("bad signature")
                return fs.event

        self.Price, self.PaymentLink, self.Webhook = Price, PaymentLink, Webhook


@pytest.fixture
def archived():
    return []


@pytest.fixture
def make(tmp_path, archived, monkeypatch):
    def _make(event=None):
        fake = FakeStripe(event)
        monkeypatch.setattr(payments, "stripe", fake)
        ledger = Ledger(tmp_path)

        def archive_append(kind, payload):
            archived.append((kind, payload))
            return "archive:2026-09-06#1"

        return payments.Payments("sk_test_x", archive_append, ledger), fake, ledger

    return _make


def test_create_link(make, archived):
    p, fake, _ = make()
    url = p.create_link(500, "usd", "Tip jar", "a coffee for Chris")
    assert url == "https://buy.stripe.com/test_x"
    assert fake.api_key == "sk_test_x"
    price_kw = dict(fake.calls[0][1])
    assert price_kw["unit_amount"] == 500 and price_kw["currency"] == "usd"
    assert price_kw["product_data"]["name"] == "Tip jar"
    link_kw = dict(fake.calls[1][1])
    assert link_kw["line_items"] == [{"price": "price_1", "quantity": 1}]
    assert link_kw["payment_method_types"] == ["card"]
    # card charges only accept the suffix form (statement_descriptor errors for cards)
    assert link_kw["payment_intent_data"]["statement_descriptor_suffix"] == "CHRIS"
    assert archived[-1][0] == "payment_link_created"
    assert archived[-1][1]["url"] == url


def test_webhook_adds_revenue_row(make, archived):
    event = {"type": "checkout.session.completed", "data": {"object": {
        "id": "cs_1", "amount_total": 2500, "currency": "usd",
        "customer_details": {"email": "someone@example.org"}}}}
    p, fake, ledger = make(event)
    out = p.handle_webhook(b"{}", "sig", "whsec")
    assert out["amount"] == 25.0 and out["ccy"] == "USD"
    assert out["counterparty"] == "example.org"
    rows = ledger.rows()
    assert len(rows) == 1 and rows[0]["type"] == "revenue" and rows[0]["ref"] == "cs_1"
    assert ledger.balance() == 25.0
    assert archived[-1][0] == "payment_received"
    assert "someone@" not in str(archived) and "someone@" not in str(rows)
    # replay is idempotent
    p.handle_webhook(b"{}", "sig", "whsec")
    assert len(ledger.rows()) == 1


def test_webhook_stranger_without_email(make):
    event = {"type": "checkout.session.completed", "data": {"object": {
        "id": "cs_2", "amount_total": 100, "currency": "usd", "customer_details": None}}}
    p, _, ledger = make(event)
    assert p.handle_webhook(b"{}", "sig", "whsec")["counterparty"] == "stranger"


def test_webhook_ignores_other_events(make):
    p, _, ledger = make({"type": "payment_intent.created", "data": {"object": {}}})
    assert p.handle_webhook(b"{}", "sig", "whsec") is None
    assert ledger.rows() == []


def test_webhook_bad_signature_raises(make):
    p, _, _ = make(None)
    with pytest.raises(ValueError):
        p.handle_webhook(b"{}", "sig", "whsec")
