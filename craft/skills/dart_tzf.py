"""What time zone data does a Dart `timezone` package really ship? Decode its .tzf file in Python.

No Dart SDK needed. Format from the package's lib/src/tzdb.dart (checked on 0.11.2):
the file is chunks of [u32 big-endian length, 4 pad bytes, data]; each chunk is one
location: a 32-byte header of eight u32 (name off/len, abbreviations off/len, zones
off/count, transitions off/count), then zones as (i32 offset seconds, u8 isDst,
u8 abbreviation index, 2 pad), then transitions as float64 seconds, then one u8 zone
index per transition.

Usage: python -I dart_tzf.py path/to/latest_all.tzf 2026-11-20T12:00 America/Havana ...
Prints each zone's UTC offset at that UTC instant.
"""
import datetime as dt
import struct
import sys


def locations(data: bytes) -> dict:
    out, off = {}, 0
    while off < len(data):
        (length,) = struct.unpack_from(">I", data, off)
        chunk = data[off + 8 : off + 8 + length]
        off += 8 + length
        h = struct.unpack_from(">8I", chunk, 0)
        name = chunk[h[0] : h[0] + h[1]].decode()
        zones = [struct.unpack_from(">iB", chunk, h[4] + 8 * i)[:2] for i in range(h[5])]
        n = h[7]
        times = struct.unpack_from(f">{n}d", chunk, h[6]) if n else ()
        idx = chunk[h[6] + 8 * n : h[6] + 9 * n]
        out[name] = (zones, times, idx)
    return out


def offset_at(loc, when_utc: dt.datetime) -> int:
    zones, times, idx = loc
    t = when_utc.timestamp()
    z = 0
    for at, zi in zip(times, idx):
        if at <= t:
            z = zi
        else:
            break
    return zones[z][0]


def fmt(sec: int) -> str:
    sign = "+" if sec >= 0 else "-"
    sec = abs(sec)
    return f"UTC{sign}{sec // 3600}" + (f":{sec % 3600 // 60:02d}" if sec % 3600 else "")


def main(argv):
    path, when, names = argv[0], argv[1], argv[2:]
    locs = locations(open(path, "rb").read())
    w = dt.datetime.fromisoformat(when).replace(tzinfo=dt.timezone.utc)
    for n in names:
        print(n, fmt(offset_at(locs[n], w)) if n in locs else "MISSING")


if __name__ == "__main__":
    main(sys.argv[1:])
