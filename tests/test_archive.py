import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from freezegun import freeze_time

from agent.archive import Archive, is_valid_ref

NY = "America/New_York"


@pytest.fixture
def arch(tmp_path):
    return Archive(tmp_path / "archive", tz=NY)


def test_append_returns_ref_and_writes_jsonl(arch, tmp_path):
    with freeze_time("2026-09-06 12:00:00"):  # UTC → 08:00 NY same day
        ref = arch.append("note", {"a": 1})
    assert ref == "archive:2026-09-06#1"
    f = tmp_path / "archive" / "2026-09-06.jsonl"
    lines = f.read_text().splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["kind"] == "note"
    assert rec["ref"] == ref
    assert rec["payload"] == {"a": 1}
    ts = datetime.fromisoformat(rec["ts"])
    assert ts.tzinfo is not None
    assert ts.utcoffset() == datetime(2026, 9, 6, 8, tzinfo=ZoneInfo(NY)).utcoffset()


def test_date_uses_configured_tz(arch):
    # 02:00 UTC on Sep 7 is still Sep 6 in New York
    with freeze_time("2026-09-07 02:00:00"):
        ref = arch.append("note", {})
    assert ref == "archive:2026-09-06#1"


def test_line_numbers_increment_per_day(arch):
    with freeze_time("2026-09-06 12:00:00"):
        assert arch.append("a", {}) == "archive:2026-09-06#1"
        assert arch.append("b", {}) == "archive:2026-09-06#2"
    with freeze_time("2026-09-07 12:00:00"):
        assert arch.append("c", {}) == "archive:2026-09-07#1"
    # a fresh instance continues numbering from what is on disk
    other = Archive(arch.dir, tz=NY)
    with freeze_time("2026-09-06 13:00:00"):
        assert other.append("d", {}) == "archive:2026-09-06#3"


def test_read_day_and_get(arch):
    with freeze_time("2026-09-06 12:00:00"):
        r1 = arch.append("a", {"x": 1})
        r2 = arch.append("b", {"x": 2})
    day = arch.read_day("2026-09-06")
    assert [r["ref"] for r in day] == [r1, r2]
    assert arch.get(r2)["payload"] == {"x": 2}
    assert arch.read_day("2026-01-01") == []
    with pytest.raises(KeyError):
        arch.get("archive:2026-09-06#99")
    with pytest.raises(ValueError):
        arch.get("nonsense")


def test_search_case_insensitive_newest_first(arch):
    with freeze_time("2026-09-05 12:00:00"):
        arch.append("mail", {"body": "Hello Parent"})
    with freeze_time("2026-09-06 12:00:00"):
        arch.append("note", {"body": "nothing here"})
        arch.append("mail", {"body": "hello again"})
    hits = arch.search("HELLO")
    assert [h["ref"] for h in hits] == ["archive:2026-09-06#2", "archive:2026-09-05#1"]
    assert arch.search("hello", limit=1)[0]["ref"] == "archive:2026-09-06#2"
    assert arch.search("zzz") == []


def test_payload_must_be_json(arch):
    with pytest.raises(TypeError):
        arch.append("bad", {"o": object()})


def test_is_valid_ref():
    assert is_valid_ref("archive:2026-09-06#1")
    assert is_valid_ref("archive:2026-09-06#123")
    assert not is_valid_ref("archive:2026-09-06#0")
    assert not is_valid_ref("archive:2026-9-6#1")
    assert not is_valid_ref("2026-09-06#1")
    assert not is_valid_ref("archive:2026-09-06")
    assert not is_valid_ref(" archive:2026-09-06#1")


def test_source_has_no_delete_or_truncate_paths():
    src = (Path(__file__).resolve().parents[1] / "agent" / "archive.py").read_text()
    src = src.replace("O_WRONLY", "")
    forbidden = re.compile(r'unlink|remove\(|truncate|"w"|\'w\'|"w\+"|rmtree|rename')
    hits = [ln for ln in src.splitlines() if forbidden.search(ln)]
    assert hits == [], f"archive.py must be append-only; found: {hits}"
    assert "os.O_APPEND" in src and "os.O_CREAT" in src


def test_existing_file_is_never_rewritten(arch, tmp_path):
    f = tmp_path / "archive" / "2026-09-06.jsonl"
    with freeze_time("2026-09-06 12:00:00"):
        arch.append("a", {})
        before = f.read_bytes()
        arch.append("b", {})
    assert f.read_bytes().startswith(before)


def test_search_skips_transcript_records_and_truncates(tmp_path):
    from agent.archive import Archive
    a = Archive(tmp_path)
    a.append("mail_out", {"subject": "tomatoes", "body": "x" * 5000})
    a.append("session_start", {"user_prompt": "everything about tomatoes " * 50})
    a.append("assistant", {"text": "tomatoes are red"})
    hits = a.search("tomatoes", limit=10)
    assert [h["kind"] for h in hits] == ["mail_out"]
    assert "more chars" in hits[0]["payload"] and len(hits[0]["payload"]) < 2200
