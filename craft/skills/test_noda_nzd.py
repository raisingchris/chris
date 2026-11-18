import datetime as dt
import pathlib
import struct
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import noda_nzd as n  # noqa: E402

H = 3600000


def varint(v):
    out = b""
    while True:
        b = v & 0x7F
        v >>= 7
        if v:
            out += bytes([b | 0x80])
        else:
            return out + bytes([b])


def zigzag(v):
    return varint((v << 1) ^ (v >> 31))


def millis(ms):
    v = ms + n.DAY_MS
    if v % (30 * 60000) == 0 and v // (30 * 60000) < 128:
        return bytes([v // (30 * 60000)])
    m = v // 60000
    assert v % 60000 == 0 and m < (1 << 13)
    return bytes([0x80 | (m >> 8), m & 0xFF])


def s_inline(s):
    b = s.encode()
    return varint(len(b)) + b


def year_offset(mode, month, dom, dow, advance, tod_ms):
    return bytes([(mode << 5) | (dow << 2) | (int(advance) << 1)]) + varint(month) + zigzag(dom) + millis(tod_ms - n.DAY_MS)


def field(fid, body):
    return bytes([fid]) + varint(len(body)) + body


def ms(s):
    return (dt.datetime.fromisoformat(s) - n.EPOCH) // dt.timedelta(milliseconds=1)


def build():
    pool = ["Test/Zone", "EST", "EDT", "Alias/Zone"]
    P = {s: i for i, s in enumerate(pool)}
    t1 = ms("2007-03-11T07:00+00:00")
    t2 = ms("2007-11-04T06:00+00:00")
    z = varint(P["Test/Zone"]) + b"\x02" + varint(2)
    z += varint(0)  # starts at BeforeMinValue
    z += varint(P["EST"]) + millis(-5 * H) + millis(0)
    z += varint(2) + struct.pack(">q", t1 * 10000)  # raw ticks
    z += varint(P["EDT"]) + millis(-4 * H) + millis(H)
    z += varint((t2 - t1) // H)  # hours since previous
    z += b"\x01" + millis(-5 * H) + varint(P["EST"]) + year_offset(1, 11, 1, 7, True, 2 * H)
    z += varint(P["EDT"]) + year_offset(1, 3, 8, 7, True, 2 * H) + millis(H)
    data = struct.pack("<i", 0)
    data += field(0, varint(len(pool)) + b"".join(s_inline(s) for s in pool))
    data += field(2, s_inline("2026f"))
    data += field(1, z)
    data += field(3, varint(1) + varint(P["Alias/Zone"]) + varint(P["Test/Zone"]))
    return data


def test_decode_periods_and_tail():
    nzd = n.parse(build())
    assert nzd["version"] == "2026f"
    z = n.zone(nzd, "Test/Zone")
    assert n.offset_at(z, ms("2000-01-01T00:00+00:00")) == (-5 * H, "EST")
    assert n.offset_at(z, ms("2007-07-01T00:00+00:00")) == (-4 * H, "EDT")
    assert n.offset_at(z, ms("2026-07-01T12:00+00:00")) == (-4 * H, "EDT")
    assert n.offset_at(z, ms("2026-11-20T12:00+00:00")) == (-5 * H, "EST")
    assert n.offset_at(z, ms("2027-03-14T06:59+00:00"))[0] == -5 * H
    assert n.offset_at(z, ms("2027-03-14T07:00+00:00"))[0] == -4 * H
    # aliases go through the id map
    assert n.offset_at(n.zone(nzd, "Alias/Zone"), ms("2026-11-20T12:00+00:00"))[0] == -5 * H


def test_finds_nzd_embedded_in_a_dll(tmp_path, capsys):
    blob = b"MZ" + b"\x90" * 300 + struct.pack("<I", len(build())) + build() + b"\x00" * 50
    p = tmp_path / "Fake.dll"
    p.write_bytes(blob)
    n.main([str(p), "--version", "Test/Zone", "--at", "2026-11-20T12:00Z"])
    out = capsys.readouterr().out
    assert "tzdb version: 2026f" in out and "-" + "05:00 EST" in out


def test_reads_cldr_windows_mapping(capsys, tmp_path):
    pool = ["49", "2021a", "7e11800", "British Columbia Standard Time", "001", "CA",
            "America/Vancouver", "Pacific Standard Time", "America/Los_Angeles", "US"]
    P = {s: i for i, s in enumerate(pool)}
    w = varint(P["49"]) + varint(P["2021a"]) + varint(P["7e11800"]) + varint(2)
    w += varint(P["British Columbia Standard Time"]) + varint(P["CA"]) + varint(1) + varint(P["America/Vancouver"])
    w += varint(P["Pacific Standard Time"]) + varint(P["US"]) + varint(1) + varint(P["America/Los_Angeles"])
    data = struct.pack("<i", 0)
    data += field(0, varint(len(pool)) + b"".join(s_inline(s) for s in pool))
    data += field(2, s_inline("2026f"))
    data += field(4, w)
    nzd = n.parse(data)
    assert nzd["windows"]["version"] == "49"
    assert n.windows_ids(nzd, "America/Vancouver") == [("British Columbia Standard Time", "CA")]
    p = tmp_path / "t.nzd"
    p.write_bytes(data)
    n.main([str(p), "America/Vancouver", "--windows"])
    assert "British Columbia Standard Time" in capsys.readouterr().out
