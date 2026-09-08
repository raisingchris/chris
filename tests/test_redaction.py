import re
from pathlib import Path

import pytest

from agent.redaction import (
    RedactionError,
    assert_clean,
    clean_tree,
    redact,
    scan_tree,
)

CANARIES = ["Jane Q. Example", "jane.example@gmail.com", "Example Holdings Pte Ltd", "Ruritania", "Zenda", "+999"]


def _kinds(report):
    return {r["kind"]: r["count"] for r in report}


def test_canary_replaced_case_insensitive():
    clean, report = redact("Met JANE Q. EXAMPLE and Jane q. example today.", CANARIES)
    assert "Example" not in clean
    assert clean == "Met [redacted] and [redacted] today."
    assert _kinds(report)["canary"] == 2


def test_canary_variants_without_separators():
    clean, _ = redact("mail janeexample@gmail.com or jane-example@gmail.com", CANARIES)
    assert "example" not in clean.lower()


def test_email_on_raisingchris_kept():
    clean, report = redact("write chris@raisingchris.com or bob@other.org", CANARIES)
    assert "chris@raisingchris.com" in clean
    assert "bob@other.org" not in clean
    assert _kinds(report)["email"] == 1


def test_phone_caught():
    clean, report = redact("call +44 9123 4567 or (212) 555-0199 or +1-415-555-0100", CANARIES)
    assert "9123" not in clean and "555" not in clean
    assert _kinds(report)["phone"] == 3


def test_dates_refs_and_ids_not_treated_as_phones():
    text = "archive:2026-09-06#12 at 14:30 on 2026-09-06, v1.2.3.4, id 123456789012"
    clean, report = redact(text, CANARIES)
    assert clean == text and report == []


def test_local_eight_digit_phone_caught():
    clean, report = redact("call 9123 4567 tomorrow", CANARIES)
    assert clean == "call [redacted] tomorrow"
    assert _kinds(report)["phone"] == 1


def test_builtin_pattern_is_only_the_generic_utc_offset():
    text = "She lives at UTC+3 (UTC-05:30 in winter, utc +11); the city is Zenda in Ruritania, phone +999 1234 5678"
    clean, report = redact(text, CANARIES)
    for bad in ["UTC+3", "UTC-05:30", "utc +11", "Zenda", "Ruritania", "+999", "1234 5678"]:
        assert bad not in clean
    kinds = _kinds(report)
    assert kinds["pattern"] == 3
    assert kinds["canary"] >= 3  # named places and the country code come from the canary list, not the source


def test_source_has_no_named_patterns():
    """The only built-in pattern is the generic UTC offset; nothing named lives in agent/redaction.py."""
    from agent import redaction

    assert redaction._PATTERNS.pattern.startswith(r"\bUTC")
    assert "|" not in redaction._PATTERNS.pattern  # a single alternative
    src = Path(redaction.__file__).read_text()
    assert re.search(r"re\.compile\(\s*r?[\"'][^)]*\\b[A-Z][a-z]{3,}", src) is None  # no capitalised word patterns


def test_ordinary_words_not_over_redacted():
    clean, report = redact("utctest is a word; the sign said 1984.com sale", CANARIES)
    assert clean == "utctest is a word; the sign said 1984.com sale"
    assert report == []


def test_report_never_contains_matched_text():
    text = "Jane Q. Example <jane.example@gmail.com> +44 9123 4567 Ruritania"
    _, report = redact(text, CANARIES)
    dumped = repr(report).lower()
    for c in CANARIES + ["9123", "ruritania"]:
        assert c.lower() not in dumped
    assert set(report[0].keys()) == {"kind", "count"}


def test_clean_text_reports_empty():
    clean, report = redact("nothing to see here", CANARIES)
    assert clean == "nothing to see here"
    assert report == []


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    (tmp_path / "memory" / "diary").mkdir(parents=True)
    (tmp_path / "memory" / "scratchpad").mkdir(parents=True)
    (tmp_path / ".git").mkdir()
    (tmp_path / "memory" / "diary" / "2026-09-06.md").write_text(
        "Talked to Jane Q. Example about Ruritania at UTC+3.\n"
    )
    (tmp_path / "memory" / "scratchpad" / "notes.md").write_text("jane.example@gmail.com\n")
    (tmp_path / ".git" / "config").write_text("Example Holdings Pte Ltd\n")
    (tmp_path / "README.md").write_text("Hello from chris@raisingchris.com\n")
    (tmp_path / "blob.bin").write_bytes(b"Jane Q. Example\x00binary")
    return tmp_path


def test_scan_tree_skips_scratchpad_git_and_binaries(tree: Path):
    hits = scan_tree(tree, CANARIES)
    assert [h["path"] for h in hits] == ["memory/diary/2026-09-06.md"]
    assert set(hits[0]["kinds"]) == {"canary", "pattern"}
    assert hits[0]["count"] == 3


def test_assert_clean_raises_with_paths_not_secrets(tree: Path):
    with pytest.raises(RedactionError) as exc:
        assert_clean(tree, CANARIES)
    msg = str(exc.value)
    assert "memory/diary/2026-09-06.md" in msg
    assert "canary" in msg
    assert "Jane" not in msg and "Ruritania" not in msg


def test_clean_tree_rewrites_and_then_clean(tree: Path):
    report = clean_tree(tree, CANARIES)
    assert [h["path"] for h in report] == ["memory/diary/2026-09-06.md"]
    assert (tree / "memory" / "diary" / "2026-09-06.md").read_text() == (
        "Talked to [redacted] about [redacted] at [redacted].\n"
    )
    # untouched: excluded + binary + already-clean
    assert (tree / "memory" / "scratchpad" / "notes.md").read_text() == "jane.example@gmail.com\n"
    assert (tree / "blob.bin").read_bytes().startswith(b"Jane Q. Example\x00")
    assert scan_tree(tree, CANARIES) == []
    assert_clean(tree, CANARIES)


def test_timestamps_are_not_phone_numbers():
    for t in ("2026-09-07 14:30 UTC", "at 2026-09-07 09:59 the sitting died", "2026-09-07 9am"):
        assert redact(t, CANARIES)[0] == t
    assert "[redacted]" in redact("call +1 415 555 0199", CANARIES)[0]
