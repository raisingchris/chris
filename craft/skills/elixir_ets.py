"""What time zone data does Elixir's `tzdata` package really ship? Decode its .ets file in Python.

No Erlang needed. The file in priv/release_ets/ is written by ets:tab2file, which is a
disk_log: an 8-byte header, then records of [u32 big-endian size, 4-byte magic "bWLA",
term_to_binary bytes]; chunks of 65528 bytes or more carry a 16-byte MD5 after the
magic. The first record is the table header; the rest are lists of the
table's rows. This file has a small External Term Format decoder (enough tags for
tzdata) and, for tzdata 1.x, finds each zone's periods and prints its UTC offset.

Usage: python -I elixir_ets.py path/to/2026d.v2.ets 2026-11-20T12:00 America/Havana ...
       python -I elixir_ets.py path/to/2026d.v2.ets --keys   (show what the rows look like)
"""
import datetime as dt
import struct
import sys

GREG_1970 = 62167219200  # :calendar gregorian seconds at 1970-01-01T00:00:00Z


class Atom(str):
    pass


def decode_term(b: bytes, i: int):
    tag = b[i]
    i += 1
    if tag == 97:
        return b[i], i + 1
    if tag == 98:
        return struct.unpack_from(">i", b, i)[0], i + 4
    if tag in (119, 115):
        n = b[i]
        return Atom(b[i + 1 : i + 1 + n].decode()), i + 1 + n
    if tag in (118, 100):
        (n,) = struct.unpack_from(">H", b, i)
        return Atom(b[i + 2 : i + 2 + n].decode()), i + 2 + n
    if tag in (104, 105):
        if tag == 104:
            n, i = b[i], i + 1
        else:
            (n,), i = struct.unpack_from(">I", b, i), i + 4
        out = []
        for _ in range(n):
            v, i = decode_term(b, i)
            out.append(v)
        return tuple(out), i
    if tag == 106:
        return [], i
    if tag == 107:
        (n,) = struct.unpack_from(">H", b, i)
        return list(b[i + 2 : i + 2 + n]), i + 2 + n
    if tag == 108:
        (n,) = struct.unpack_from(">I", b, i)
        i += 4
        out = []
        for _ in range(n):
            v, i = decode_term(b, i)
            out.append(v)
        _tail, i = decode_term(b, i)
        return out, i
    if tag == 109:
        (n,) = struct.unpack_from(">I", b, i)
        return bytes(b[i + 4 : i + 4 + n]), i + 4 + n
    if tag in (110, 111):
        if tag == 110:
            n, i = b[i], i + 1
        else:
            (n,), i = struct.unpack_from(">I", b, i), i + 4
        sign = b[i]
        v = int.from_bytes(b[i + 1 : i + 1 + n], "little")
        return (-v if sign else v), i + 1 + n
    if tag == 70:
        return struct.unpack_from(">d", b, i)[0], i + 8
    if tag == 116:
        (n,) = struct.unpack_from(">I", b, i)
        i += 4
        out = {}
        for _ in range(n):
            k, i = decode_term(b, i)
            v, i = decode_term(b, i)
            out[k if not isinstance(k, list) else tuple(k)] = v
        return out, i
    if tag == 88:  # NEW_PID_EXT: node atom, id u32, serial u32, creation u32
        _node, i = decode_term(b, i)
        return ("pid",), i + 12
    if tag == 90:  # NEWER_REFERENCE_EXT
        (n,) = struct.unpack_from(">H", b, i)
        _node, i = decode_term(b, i + 2)
        return ("ref",), i + 4 + 4 * n
    raise ValueError(f"unsupported term tag {tag} at {i - 1}")


def records(data: bytes):
    """Yield each disk_log record's decoded term."""
    i = 8
    while i + 8 <= len(data):
        (size,) = struct.unpack_from(">I", data, i)
        md5 = 16 if size >= 65528 else 0  # disk_log adds an MD5 to big chunks
        body = data[i + 8 + md5 : i + 8 + md5 + size]
        i += 8 + md5 + size
        if body[:1] != b"\x83":
            raise ValueError("record without term version byte")
        term, _ = decode_term(body, 1)
        yield term


def rows(data: bytes) -> list:
    recs = list(records(data))
    out = []
    for r in recs[1:]:
        out.extend(r if isinstance(r, list) else [r])
    return out


def zone_periods(rows_: list) -> dict:
    """tzdata 1.x stores {zone_name, from_utc, from_std, from_wall, until_utc, until_std,
    until_wall, utc_off, std_off, zone_abbr} rows in the main table (as of 1.1.x).
    Times are gregorian seconds or the atoms :min/:max."""
    out = {}
    for r in rows_:
        if isinstance(r, tuple) and len(r) == 10 and isinstance(r[0], (bytes, str)):
            name = r[0].decode() if isinstance(r[0], bytes) else r[0]
            out.setdefault(name, []).append(r)
    return out


def offset_at(periods: list, when_utc: dt.datetime) -> int:
    g = int(when_utc.replace(tzinfo=dt.timezone.utc).timestamp()) + GREG_1970
    for p in periods:
        lo, hi = p[1], p[4]
        if (lo == "min" or lo <= g) and (hi == "max" or g < hi):
            return p[7] + p[8]
    raise LookupError("no period covers that time")


def main(argv):
    data = open(argv[1], "rb").read()
    rs = rows(data)
    if argv[2] == "--keys":
        seen = {}
        for r in rs:
            k = (type(r).__name__, len(r) if isinstance(r, tuple) else 0, type(r[0]).__name__ if isinstance(r, tuple) and r else "")
            seen.setdefault(k, r)
        for k, r in seen.items():
            print(k, repr(r)[:300])
        return 0
    when = dt.datetime.fromisoformat(argv[2])
    zp = zone_periods(rs)
    for z in argv[3:]:
        if z not in zp:
            print(f"{z}\tMISSING")
            continue
        off = offset_at(zp[z], when)
        sign = "+" if off >= 0 else "-"
        print(f"{z}\tUTC{sign}{abs(off) // 3600:02d}:{abs(off) % 3600 // 60:02d}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
