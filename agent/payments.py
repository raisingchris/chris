"""Receiving money: Stripe payment links (card only) + webhook -> ledger revenue row.

Stripe API notes (docs.stripe.com, fetched via context7 on 2026-09-06):
  POST /v1/prices          product_data{name}, unit_amount, currency
  POST /v1/payment_links   line_items[{price, quantity}], payment_method_types, payment_intent_data
  payment_intent_data.statement_descriptor is for NON-card charges and errors on card charges;
  card charges take payment_intent_data.statement_descriptor_suffix, which Stripe appends to the
  account-level descriptor. The "Chris" Stripe account's own descriptor must therefore be set
  to CHRIS in the dashboard (Settings > Public details) so the statement reads "CHRIS* CHRIS"
  or "CHRIS" — never the holdco name.

`stripe` is a module attribute so tests can monkeypatch it.
"""
from __future__ import annotations

from typing import Callable

import stripe

from agent.ledger import Ledger

ArchiveAppend = Callable[[str, dict], str]
STATEMENT_DESCRIPTOR = "CHRIS"


class Payments:
    def __init__(self, stripe_secret_key: str, archive_append: ArchiveAppend, ledger: Ledger):
        self._key = stripe_secret_key
        self._archive = archive_append
        self._ledger = ledger

    def create_link(self, amount_cents: int, ccy: str, name: str, description: str = "") -> str:
        stripe.api_key = self._key
        product_data = {"name": name}
        if description:
            product_data["description"] = description
        price = stripe.Price.create(unit_amount=int(amount_cents), currency=ccy.lower(),
                                    product_data=product_data)
        link = stripe.PaymentLink.create(
            line_items=[{"price": price.id, "quantity": 1}],
            payment_method_types=["card"],
            payment_intent_data={"statement_descriptor_suffix": STATEMENT_DESCRIPTOR},
        )
        self._archive("payment_link_created", {"url": link.url, "link_id": link.id,
                                               "amount_cents": int(amount_cents),
                                               "ccy": ccy.upper(), "name": name})
        return link.url

    def handle_webhook(self, payload_bytes: bytes, sig_header: str, webhook_secret: str) -> dict | None:
        """Verify signature; on checkout.session.completed record revenue. Raises on bad signature."""
        event = stripe.Webhook.construct_event(payload_bytes, sig_header, webhook_secret)
        if event["type"] != "checkout.session.completed":
            return None
        obj = event["data"]["object"]
        # stripe-python objects aren't plain dicts (no .get); normalise once.
        s = obj.to_dict() if hasattr(obj, "to_dict") else dict(obj)
        amount = (s.get("amount_total") or 0) / 100
        ccy = (s.get("currency") or "usd").upper()
        # Never the payer's address or even their domain: the ledger is public.
        counterparty = "stranger"
        row = self._ledger.add("revenue", amount, ccy, counterparty,
                               "stripe payment link", ref=s["id"])
        self._archive("payment_received", {"session_id": s["id"], "amount": amount,
                                           "ccy": ccy, "counterparty": counterparty})
        return {"amount": amount, "ccy": ccy, "counterparty": counterparty, "ref": s["id"], "row": row}
