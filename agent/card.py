"""Chris's one virtual card (Airwallex Issuing).

Endpoint paths and field names below were taken from the Airwallex API reference
(https://www.airwallex.com/docs/api/, fetched via context7 on 2026-09-06):

  POST /api/v1/authentication/login           headers x-client-id / x-api-key -> {"token", "expires_at"}
  POST /api/v1/issuing/cards/create           body: cardholder_id, form_factor "VIRTUAL", nick_name,
                                              authorization_controls.transaction_limits
                                              {currency, limits:[{amount, interval}]}, request_id
                                              interval in PER_TRANSACTION|DAILY|WEEKLY|MONTHLY|ALL_TIME
  GET  /api/v1/issuing/cards/{id}/details     -> {card_number, cvv, expiry_month, expiry_year, name_on_card}
  POST /api/v1/issuing/cards/{id}/update      body: card_status "ACTIVE"|"INACTIVE", authorization_controls...
  GET  /api/v1/issuing/transactions           ?card_id&from_created_at&page_num&page_size
                                              -> {has_more, items:[{transaction_id, transaction_date,
                                                  billing_amount, billing_currency, merchant.name, ...}]}

Invariant: card numbers are never written to the archive. `details()` archives only
the fixed marker {"kind": "card_details_requested"}.
"""
from __future__ import annotations

import time
import uuid
from typing import Callable

import httpx

ArchiveAppend = Callable[[str, dict], str]

TOKEN_TTL_S = 25 * 60  # Airwallex tokens last 30 min; refresh a little early.


class Card:
    def __init__(self, client_id: str, api_key: str, base_url: str, card_id: str | None,
                 cardholder_id: str, archive_append: ArchiveAppend,
                 transport: httpx.BaseTransport | None = None):
        self.client_id = client_id
        self.api_key = api_key
        self.card_id = card_id
        self.cardholder_id = cardholder_id
        self._archive = archive_append
        self._http = httpx.Client(base_url=base_url.rstrip("/"), transport=transport, timeout=30)
        self._tok: str | None = None
        self._tok_at = 0.0

    # -- auth -------------------------------------------------------------
    def _token(self) -> str:
        if self._tok and time.monotonic() - self._tok_at < TOKEN_TTL_S:
            return self._tok
        r = self._http.post("/api/v1/authentication/login",
                            headers={"x-client-id": self.client_id, "x-api-key": self.api_key})
        r.raise_for_status()
        self._tok = r.json()["token"]
        self._tok_at = time.monotonic()
        return self._tok

    def _call(self, method: str, path: str, **kw) -> dict:
        r = self._http.request(method, path, headers={"Authorization": f"Bearer {self._token()}"}, **kw)
        r.raise_for_status()
        return r.json()

    def _card_path(self, suffix: str = "") -> str:
        if not self.card_id:
            raise RuntimeError("no card_id: a parent must run create() first")
        return f"/api/v1/issuing/cards/{self.card_id}{suffix}"

    @staticmethod
    def _limits(weekly_usd: float, per_txn_usd: float) -> dict:
        return {"transaction_limits": {"currency": "USD", "limits": [
            {"amount": weekly_usd, "interval": "WEEKLY"},
            {"amount": per_txn_usd, "interval": "PER_TRANSACTION"}]}}

    # -- lifecycle (create is a one-time parent action) -------------------
    def create(self, weekly_usd: float = 100, per_txn_usd: float = 50,
               nickname: str = "Chris allowance") -> dict:
        body = {
            "request_id": str(uuid.uuid4()),
            "cardholder_id": self.cardholder_id,
            "form_factor": "VIRTUAL",
            "nick_name": nickname,
            "authorization_controls": self._limits(weekly_usd, per_txn_usd),
        }
        out = self._call("POST", "/api/v1/issuing/cards/create", json=body)
        self.card_id = out["card_id"]
        self._archive("card_created", {"card_id": self.card_id, "weekly_usd": weekly_usd,
                                       "per_txn_usd": per_txn_usd})
        return {"card_id": self.card_id, "card_status": out.get("card_status")}

    def details(self) -> dict:
        """Sensitive card data for Chris to pay with. Name stripped; numbers never archived."""
        self._archive("card_details_requested", {"kind": "card_details_requested"})
        d = self._call("GET", self._card_path("/details"))
        return {"number": d["card_number"], "expiry_month": d["expiry_month"],
                "expiry_year": d["expiry_year"], "cvc": d["cvv"]}

    def _update(self, body: dict) -> dict:
        return self._call("POST", self._card_path("/update"), json=body)

    def freeze(self) -> dict:
        out = self._update({"card_status": "INACTIVE"})
        self._archive("card_frozen", {"card_id": self.card_id})
        return out

    def unfreeze(self) -> dict:
        out = self._update({"card_status": "ACTIVE"})
        self._archive("card_unfrozen", {"card_id": self.card_id})
        return out

    def set_limits(self, weekly_usd: float, per_txn_usd: float) -> dict:
        out = self._update({"authorization_controls": self._limits(weekly_usd, per_txn_usd)})
        self._archive("card_limits_set", {"card_id": self.card_id, "weekly_usd": weekly_usd,
                                          "per_txn_usd": per_txn_usd})
        return out

    # -- history ----------------------------------------------------------
    def transactions(self, since_iso: str) -> list[dict]:
        """All transactions on this card since `since_iso`, normalized to
        {ts, amount, ccy, merchant, ref}. amount is the billed amount as Airwallex reports it."""
        out, page = [], 0
        while True:
            data = self._call("GET", "/api/v1/issuing/transactions", params={
                "card_id": self.card_id, "from_created_at": since_iso,
                "page_num": page, "page_size": 100})
            for t in data.get("items", []):
                out.append({"ts": t.get("transaction_date"), "amount": t.get("billing_amount"),
                            "ccy": t.get("billing_currency"),
                            "merchant": (t.get("merchant") or {}).get("name", ""),
                            "ref": t.get("transaction_id")})
            if not data.get("has_more"):
                return out
            page += 1
