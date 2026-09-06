from pathlib import Path

import pytest

from agent.ledger import HEADER, Ledger


@pytest.fixture
def ledger(tmp_path: Path) -> Ledger:
    return Ledger(tmp_path)


def test_creates_file_with_header(ledger: Ledger, tmp_path: Path):
    ledger.add("allowance", 100, "USD", "parents", "week 1")
    text = (tmp_path / "ledger" / "ledger.csv").read_text()
    assert text.splitlines()[0] == HEADER
    assert len(text.splitlines()) == 2


def test_rows_and_balance(ledger: Ledger):
    ledger.add("allowance", 100, "USD", "parents", "week 1")
    ledger.add("spend", 12.5, "USD", "some-saas", "trial")
    ledger.add("fee", 0.5, "USD", "airwallex", "fx")
    ledger.add("revenue", 20, "USD", "stranger", "first dollar", ref="cs_1")
    ledger.add("refund", 2.5, "USD", "some-saas", "partial")
    ledger.add("revenue", 999, "EUR", "stranger", "other ccy")
    assert len(ledger.rows()) == 6
    assert ledger.balance() == pytest.approx(100 - 12.5 - 0.5 + 20 + 2.5)
    assert ledger.balance("EUR") == pytest.approx(999)


def test_dedupes_on_ref(ledger: Ledger):
    a = ledger.add("revenue", 20, "USD", "stranger", "x", ref="cs_1")
    b = ledger.add("revenue", 20, "USD", "stranger", "x", ref="cs_1")
    assert a == b
    assert len(ledger.rows()) == 1
    # empty ref never dedupes
    ledger.add("spend", 1, "USD", "a", "m")
    ledger.add("spend", 1, "USD", "a", "m")
    assert len(ledger.rows()) == 3


def test_rejects_bad_type(ledger: Ledger):
    with pytest.raises(ValueError):
        ledger.add("bribe", 1, "USD", "x", "y")


def test_appends_to_existing_file_with_header(tmp_path: Path):
    p = tmp_path / "ledger" / "ledger.csv"
    p.parent.mkdir()
    p.write_text(HEADER + "\n")
    Ledger(tmp_path).add("spend", 1, "USD", "x", "y")
    assert len(p.read_text().splitlines()) == 2
