"""Public money ledger: a plain CSV at ledger/ledger.csv, append-only by convention.

Columns: date,type,amount,ccy,counterparty,memo,ref
Types: spend | revenue | refund | fee | allowance
balance = revenue + allowance + refund - spend - fee
"""
from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

HEADER = "date,type,amount,ccy,counterparty,memo,ref"
FIELDS = HEADER.split(",")
TYPES = {"spend", "revenue", "refund", "fee", "allowance"}
_SIGN = {"revenue": 1, "allowance": 1, "refund": 1, "spend": -1, "fee": -1}


class Ledger:
    def __init__(self, repo_dir: str | Path, today: callable = date.today):
        self.path = Path(repo_dir) / "ledger" / "ledger.csv"
        self._today = today

    def rows(self) -> list[dict]:
        if not self.path.exists():
            return []
        with self.path.open(newline="") as f:
            return [r for r in csv.DictReader(f) if r.get("type")]

    def add(self, type: str, amount: float, ccy: str, counterparty: str,
            memo: str, ref: str = "") -> dict:
        if type not in TYPES:
            raise ValueError(f"unknown ledger type {type!r}; expected one of {sorted(TYPES)}")
        if ref:
            for r in self.rows():
                if r["ref"] == ref:
                    return r
        row = {"date": self._today().isoformat(), "type": type, "amount": f"{float(amount):.2f}",
               "ccy": ccy.upper(), "counterparty": counterparty, "memo": memo, "ref": ref}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        new = not self.path.exists() or self.path.stat().st_size == 0
        with self.path.open("a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
            if new:
                w.writeheader()
            w.writerow(row)
        return row

    def balance(self, ccy: str = "USD") -> float:
        return round(sum(_SIGN[r["type"]] * float(r["amount"])
                         for r in self.rows() if r["ccy"] == ccy.upper()), 2)
