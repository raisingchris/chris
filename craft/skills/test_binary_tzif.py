import datetime as dt
import os
import sys
from zoneinfo import TZPATH

sys.path.insert(0, os.path.dirname(__file__))
import binary_tzif as bt  # noqa: E402


def _sysfile(zone):
    for p in TZPATH:
        f = os.path.join(p, zone)
        if os.path.exists(f):
            return open(f, "rb").read()
    import pytest
    pytest.skip("no system tzdata")


def test_finds_blobs_inside_junk_and_matches_by_history():
    hav, edm = _sysfile("America/Havana"), _sysfile("America/Edmonton")
    buf = b"\x00junkTZifnot-real" + hav + b"\x7fELF more junk" + edm + b"tail"
    blobs = list(bt.tzif_blobs(buf))
    assert [b for _, b in blobs] == [hav, edm]
    at = dt.datetime(2026, 11, 15, 12, tzinfo=dt.timezone.utc)
    found = bt.match(blobs, ["America/Havana", "America/Edmonton"], at)
    assert len(found["America/Havana"]) == 1
    assert found["America/Edmonton"][0][2] == bt.footer(edm)


def test_truncated_blob_is_skipped():
    hav = _sysfile("America/Havana")
    assert list(bt.tzif_blobs(hav[:100])) == []


def test_stream_finds_blob_across_chunk_edge():
    import io
    hav = _sysfile("America/Havana")
    buf = b"x" * 1000 + hav + b"y" * 50
    got = list(bt.stream_blobs(io.BytesIO(buf), chunk=1100, keep=len(hav) + 10))
    assert got == [(1000, hav)]
