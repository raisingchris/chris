import json

import httpx
import pytest

from agent.card import Card

BASE = "https://api-demo.airwallex.com"
CARD_ID = "7f687fe6-dcf4-4462-92fa-80335301d9d2"
PAN = "4111111111111111"


class Fake:
    """Records requests and answers like Airwallex Issuing."""

    def __init__(self):
        self.requests: list[httpx.Request] = []
        self.logins = 0

    def __call__(self, req: httpx.Request) -> httpx.Response:
        self.requests.append(req)
        p = req.url.path
        if p == "/api/v1/authentication/login":
            self.logins += 1
            assert req.headers["x-client-id"] == "cid"
            assert req.headers["x-api-key"] == "key"
            return httpx.Response(201, json={"token": "tok", "expires_at": "2099-01-01T00:00:00+0000"})
        assert req.headers["authorization"] == "Bearer tok"
        if p == "/api/v1/issuing/cards/create":
            return httpx.Response(201, json={"card_id": CARD_ID, "card_status": "ACTIVE"})
        if p == f"/api/v1/issuing/cards/{CARD_ID}/details":
            return httpx.Response(200, json={
                "card_number": PAN, "cvv": "123", "expiry_month": 1,
                "expiry_year": 2030, "name_on_card": "Some Human",
            })
        if p == f"/api/v1/issuing/cards/{CARD_ID}/update":
            return httpx.Response(200, json={"card_id": CARD_ID, **json.loads(req.content)})
        if p == "/api/v1/issuing/transactions":
            return httpx.Response(200, json={"has_more": False, "items": [{
                "transaction_id": "t1", "transaction_date": "2026-09-06T10:00:00.000Z",
                "billing_amount": -12.5, "billing_currency": "USD",
                "merchant": {"name": "Merchant A"}, "status": "APPROVED",
                "transaction_type": "CLEARING",
            }]})
        return httpx.Response(404, json={"path": p})


@pytest.fixture
def fake():
    return Fake()


@pytest.fixture
def archived():
    return []


@pytest.fixture
def card(fake, archived):
    def archive_append(kind, payload):
        archived.append((kind, payload))
        return "archive:2026-09-06#1"

    return Card("cid", "key", BASE, CARD_ID, "ch_1", archive_append,
                transport=httpx.MockTransport(fake))


def test_login_once_and_cached(card, fake):
    card.freeze()
    card.unfreeze()
    assert fake.logins == 1


def test_details_strips_name_and_never_archives_number(card, archived):
    d = card.details()
    assert d == {"number": PAN, "expiry_month": 1, "expiry_year": 2030, "cvc": "123"}
    assert not any("name" in k for k in d)
    assert archived == []  # the tool archives the request (with its memo); the client never does
    assert PAN not in json.dumps(archived) and "123" not in json.dumps(archived)


def test_freeze_posts_inactive(card, fake):
    card.freeze()
    body = json.loads(fake.requests[-1].content)
    assert fake.requests[-1].url.path == f"/api/v1/issuing/cards/{CARD_ID}/update"
    assert body == {"card_status": "INACTIVE"}
    card.unfreeze()
    assert json.loads(fake.requests[-1].content) == {"card_status": "ACTIVE"}


def test_set_limits(card, fake):
    card.set_limits(80, 30)
    body = json.loads(fake.requests[-1].content)
    limits = body["authorization_controls"]["transaction_limits"]
    assert limits["currency"] == "USD"
    assert {"amount": 80, "interval": "WEEKLY"} in limits["limits"]
    assert {"amount": 30, "interval": "PER_TRANSACTION"} in limits["limits"]


def test_create(fake, archived):
    def archive_append(kind, payload):
        archived.append((kind, payload))
        return "archive:2026-09-06#1"

    c = Card("cid", "key", BASE, None, "ch_1", archive_append, transport=httpx.MockTransport(fake))
    out = c.create()
    assert out["card_id"] == CARD_ID
    assert c.card_id == CARD_ID
    body = json.loads(fake.requests[-1].content)
    assert body["form_factor"] == "VIRTUAL"
    assert body["cardholder_id"] == "ch_1"
    assert body["authorization_controls"]["transaction_limits"]["limits"] == [
        {"amount": 100, "interval": "WEEKLY"}, {"amount": 50, "interval": "PER_TRANSACTION"}]


def test_transactions_normalized(card, fake):
    txs = card.transactions("2026-09-01T00:00:00Z")
    assert txs == [{"ts": "2026-09-06T10:00:00.000Z", "amount": -12.5, "ccy": "USD",
                    "merchant": "Merchant A", "ref": "t1"}]
    q = dict(fake.requests[-1].url.params)
    assert q["card_id"] == CARD_ID and q["from_created_at"] == "2026-09-01T00:00:00Z"
