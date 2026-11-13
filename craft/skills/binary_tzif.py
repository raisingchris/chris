"""Which time zone data is baked into a binary? Find its TZif blobs and match them by history.

Many programs embed tzdb zone files straight into a .so or executable (ClickHouse/chDB, others),
with no names next to them. This finds every TZif blob, cuts it to its exact length, loads it
with zoneinfo, and matches it to a zone by comparing offsets at ~200 past instants ([redacted])
against this machine's own tzdata. Then it prints what that blob says for a date you choose.

    python3 binary_tzif.py libchdb.so --at 2026-11-15T12:00Z
    python3 binary_tzif.py --wheel-url URL --member-suffix .so --at 2026-11-15T12:00Z

--wheel-url reads a wheel (zip) into memory and scans the member without writing it to disk
(useful when the disk is tight and nothing can be deleted). Default zones: the five that
changed in 2026 (Edmonton, Yellowknife, Inuvik, Winnipeg, Havana).
Say plainly in any write-up: this is the binary's data decoded in Python, not the program run.
"""
import argparse
import datetime as dt
import io
import struct
import sys
import zipfile
from zoneinfo import ZoneInfo

ZONES = ["America/Edmonton", "America/Yellowknife", "America/Inuvik", "America/Winnipeg", "America/Havana"]


def _block_len(buf, start, v1):
    """Length of one TZif data block (header + body) starting at start."""
    if buf[start:start + 4] != b"TZif":
        raise ValueError("no TZif magic")
    isut, isstd, leap, timecnt, typecnt, charcnt = struct.unpack(">6l", buf[start + 20:start + 44])
    tsize = 4 if v1 else 8
    body = timecnt * tsize + timecnt + typecnt * 6 + charcnt + leap * (tsize + 4) + isstd + isut
    return 44 + body


def tzif_blobs(buf):
    """Yield (offset, bytes) for every complete TZif file found in buf."""
    i = buf.find(b"TZif")
    while i != -1:
        try:
            ver = buf[i + 4:i + 5]
            n = _block_len(buf, i, True)
            if ver in (b"2", b"3", b"4"):
                n += _block_len(buf, i + n, False)
                nl = buf.find(b"\n", i + n + 1)  # footer: \n rule \n
                if buf[i + n:i + n + 1] != b"\n" or nl == -1 or nl - (i + n) > 200:
                    raise ValueError("bad footer")
                n = nl + 1 - i
            elif ver != b"\x00":
                raise ValueError("bad version")
            blob = bytes(buf[i:i + n])
            ZoneInfo.from_file(io.BytesIO(blob))
            yield i, blob
            i = buf.find(b"TZif", i + n)
        except Exception:
            i = buf.find(b"TZif", i + 4)


def footer(blob):
    parts = blob.rstrip(b"\n").rsplit(b"\n", 1)
    return parts[-1].decode("ascii", "replace") if len(parts) == 2 and blob.endswith(b"\n") else ""


def _probe_times():
    t = dt.datetime(1970, 1, 15, 12, tzinfo=dt.timezone.utc)
    out = []
    while t.year < 2026:
        out.append(t)
        t += dt.timedelta(days=97)
    return out


def signature(zi, times):
    return tuple(t.astimezone(zi).utcoffset() for t in times)


def match(blobs, zones, at):
    """{zone: [(offset_in_file, offset_hours_at, footer), ...]} for blobs whose past matches the zone."""
    times = _probe_times()
    want = {z: signature(ZoneInfo(z), times) for z in zones}
    found = {z: [] for z in zones}
    for off, blob in blobs:
        zi = ZoneInfo.from_file(io.BytesIO(blob))
        sig = signature(zi, times)
        for z, s in want.items():
            if sig == s:
                h = at.astimezone(zi).utcoffset().total_seconds() / 3600
                found[z].append((off, h, footer(blob)))
    return found


def stream_blobs(f, chunk=8 << 20, keep=1 << 20):
    """tzif_blobs over a file object read in chunks; memory stays ~chunk+keep.

    A blob longer than `keep` that straddles a chunk edge would be missed; zone files are
    far smaller than 1 MB. Blobs are de-duplicated by absolute offset."""
    seen, base, tail = set(), 0, b""
    while True:
        data = f.read(chunk)
        buf = tail + data
        for off, blob in tzif_blobs(buf):
            if base + off not in seen:
                seen.add(base + off)
                yield base + off, blob
        if not data:
            return
        cut = max(0, len(buf) - keep)
        base += cut
        tail = buf[cut:]


def open_wheel_member(url, suffix):
    """(name, size, file object) for the largest member ending in suffix; the wheel stays in memory."""
    import urllib.request
    data = urllib.request.urlopen(url).read()
    zf = zipfile.ZipFile(io.BytesIO(data))
    names = [n for n in zf.namelist() if n.endswith(suffix)]
    big = max(names, key=lambda n: zf.getinfo(n).file_size)
    return big, zf.getinfo(big).file_size, zf.open(big)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("path", nargs="?")
    ap.add_argument("--wheel-url")
    ap.add_argument("--member-suffix", default=".so")
    ap.add_argument("--at", default="2026-11-15T12:00Z")
    ap.add_argument("--zone", action="append")
    a = ap.parse_args(argv)
    at = dt.datetime.fromisoformat(a.at.replace("Z", "+00:00"))
    if a.wheel_url:
        name, size, f = open_wheel_member(a.wheel_url, a.member_suffix)
        print(f"member: {name} ({size} bytes, streamed, not written to disk)")
    else:
        f = open(a.path, "rb")
    blobs = list(stream_blobs(f))
    print(f"TZif blobs found: {len(blobs)}")
    found = match(blobs, a.zone or ZONES, at)
    for z, rows in found.items():
        if not rows:
            print(f"{z}\tno blob matches its [redacted] history")
        for off, h, f in rows:
            print(f"{z}\tUTC{h:+g} at {a.at}\tfooter {f!r}\t@{off}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
