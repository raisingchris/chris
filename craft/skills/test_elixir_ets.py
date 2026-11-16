import datetime as dt
import struct

import elixir_ets as e


def atom(s):
    b = s.encode()
    return bytes([119, len(b)]) + b


def binary(s):
    b = s.encode()
    return b"m" + struct.pack(">I", len(b)) + b


def big(n):
    sign = 1 if n < 0 else 0
    n = abs(n)
    raw = n.to_bytes((n.bit_length() + 7) // 8 or 1, "little")
    return bytes([110, len(raw), sign]) + raw


def small(n):
    return b"b" + struct.pack(">i", n)


def tup(*items):
    return bytes([104, len(items)]) + b"".join(items)


def lst(*items):
    return b"l" + struct.pack(">I", len(items)) + b"".join(items) + b"j"


def record(term, pad=0):
    body = b"\x83" + term
    md5 = b"\0" * 16 if len(body) >= 65528 else b""
    return struct.pack(">I", len(body)) + b"bWLA" + md5 + body


G = e.GREG_1970
SPLIT = G + int(dt.datetime(2026, 11, 1, 6, tzinfo=dt.timezone.utc).timestamp())


def period(name, lo, hi, off):
    return tup(atom(name), lo, lo, lo, hi, hi, hi, small(off), small(0), binary("X"))


def sample(extra_rows=()):
    rows = lst(
        period("Zone/A", atom("min"), big(SPLIT), -21600),
        period("Zone/A", big(SPLIT), atom("max"), -18000),
        *extra_rows,
    )
    return b"\x01\x02\x03\x04cXM\x0b" + record(tup(atom("header"))) + record(rows)


def test_offsets_on_each_side_of_a_change():
    rs = e.rows(sample())
    zp = e.zone_periods(rs)
    assert list(zp) == ["Zone/A"]
    assert e.offset_at(zp["Zone/A"], dt.datetime(2026, 10, 1, 12)) == -21600
    assert e.offset_at(zp["Zone/A"], dt.datetime(2026, 11, 20, 12)) == -18000


def test_big_chunk_skips_md5():
    pad = tup(atom("pad"), binary("x" * 70000))
    rs = e.rows(sample([pad]))
    assert len(e.zone_periods(rs)["Zone/A"]) == 2
    assert any(isinstance(r, tuple) and r[0] == "pad" for r in rs)
