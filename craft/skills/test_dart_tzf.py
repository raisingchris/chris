"""dart_tzf.py on a hand-built .tzf: one location, two zones, one transition."""
import datetime as dt
import importlib.util
import pathlib
import struct

spec = importlib.util.spec_from_file_location("dart_tzf", pathlib.Path(__file__).with_name("dart_tzf.py"))
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)

SWITCH = dt.datetime(2026, 11, 1, 6, 0, tzinfo=dt.timezone.utc)


def build(name=b"Test/Zone"):
    abbr = b"OLD\0NEW\0"
    name_off = 32
    abbr_off = name_off + len(name)
    zones_off = (abbr_off + len(abbr) + 3) // 4 * 4
    trans_off = (zones_off + 2 * 8 + 7) // 8 * 8
    body = bytearray(((trans_off + 9) + 7) // 8 * 8)
    struct.pack_into(">8I", body, 0, name_off, len(name), abbr_off, len(abbr), zones_off, 2, trans_off, 1)
    body[name_off:name_off + len(name)] = name
    body[abbr_off:abbr_off + len(abbr)] = abbr
    struct.pack_into(">iB", body, zones_off, -5 * 3600, 0)
    struct.pack_into(">iB", body, zones_off + 8, -4 * 3600, 0)
    struct.pack_into(">d", body, trans_off, SWITCH.timestamp())
    body[trans_off + 8] = 1
    return struct.pack(">I", len(body)) + b"\0" * 4 + bytes(body)


def test_offset_before_and_after_transition(tmp_path):
    f = tmp_path / "x.tzf"
    f.write_bytes(build() + build(b"Other/Zone"))
    locs = d.locations(f.read_bytes())
    assert set(locs) == {"Test/Zone", "Other/Zone"}
    assert d.offset_at(locs["Test/Zone"], SWITCH - dt.timedelta(hours=1)) == -5 * 3600
    assert d.offset_at(locs["Test/Zone"], SWITCH) == -4 * 3600


def test_fmt():
    assert d.fmt(-4 * 3600) == "[redacted]"
    assert d.fmt(5 * 3600 + 1800) == "[redacted]"
    assert d.fmt(0) == "[redacted]"


def test_main_prints_missing(tmp_path, capsys):
    f = tmp_path / "x.tzf"
    f.write_bytes(build())
    d.main([str(f), "2026-11-20T12:00", "Test/Zone", "Nope/Zone"])
    assert capsys.readouterr().out.splitlines() == ["Test/Zone [redacted]", "Nope/Zone MISSING"]
