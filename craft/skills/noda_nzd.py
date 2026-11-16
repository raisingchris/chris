"""What time zone data does NodaTime really ship? Decode its .nzd (or the one inside NodaTime.dll) in Python.

NodaTime carries its own tz data: `Tzdb.nzd`, embedded in NodaTime.dll (and downloadable from
nodatime.org/tzdb/). The file names a version, but a label isn't a run. This reads the bytes the
way NodaTime's `TzdbStreamData` / `DateTimeZoneReader` / `PrecalculatedDateTimeZone.Read` do
(3.x format) and prints each zone's UTC offset at a moment.

    python3 -I noda_nzd.py NodaTime.dll America/Havana America/Edmonton --at 2026-11-20T12:00Z
    python3 -I noda_nzd.py tzdb2026f.nzd --version

Put downloads in their own empty folder. Use controls (America/New_York, Europe/London).
Say plainly in any write-up that this is NodaTime's data decoded in Python, not NodaTime run.
"""
import argparse
import calendar
import datetime as dt
import io
import struct
import sys

DAY_MS = 86400000
EPOCH = dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)
EPOCH_1800_MS = (dt.datetime(1800, 1, 1, tzinfo=dt.timezone.utc) - EPOCH) // dt.timedelta(milliseconds=1)
MIN, MAX = float("-inf"), float("inf")


class Reader:
    def __init__(self, data, pool=None):
        self.f = io.BytesIO(data) if isinstance(data, (bytes, bytearray)) else data
        self.pool = pool

    def byte(self):
        b = self.f.read(1)
        if not b:
            raise EOFError
        return b[0]

    def varint(self):
        ret, shift = 0, 0
        while True:
            b = self.byte()
            ret += (b & 0x7F) << shift
            shift += 7
            if b < 0x80:
                return ret

    count = varint

    def signed_count(self):
        v = self.varint()
        return (v >> 1) ^ -(v & 1)

    def int16(self):
        return struct.unpack(">h", self.f.read(2))[0]

    def int64(self):
        return struct.unpack(">q", self.f.read(8))[0]

    def millis(self):
        b = self.byte()
        if not b & 0x80:
            m = b * 30 * 60000
        else:
            flag, data = b & 0xE0, b & 0x1F
            if flag == 0x80:
                m = ((data << 8) + self.byte()) * 60000
            elif flag == 0xA0:
                m = ((data << 16) + (self.int16() & 0xFFFF)) * 1000
            elif flag == 0xC0:
                m = (data << 24) + (self.byte() << 16) + (self.int16() & 0xFFFF)
            else:
                raise ValueError(f"bad offset flag {flag:#x}")
        return m - DAY_MS

    def string(self):
        if self.pool is None:
            return self.f.read(self.count()).decode("utf-8")
        return self.pool[self.count()]

    def transition(self, previous):
        v = self.count()
        if v < 128:
            if v == 0:
                return MIN
            if v == 1:
                return MAX
            if v == 2:
                return self.int64() // 10000  # ticks -> ms
            raise ValueError(f"bad marker {v}")
        if v < (1 << 21):
            return previous + v * 3600000
        return EPOCH_1800_MS + v * 60000


def read_fields(data):
    """Container: int32 LE version, then (id byte, varint length, bytes) fields."""
    (version,) = struct.unpack("<i", data[:4])
    f = io.BytesIO(data[4:])
    fields = []
    while True:
        b = f.read(1)
        if not b:
            break
        length = Reader(f).count()
        body = f.read(length)
        if len(body) != length:
            raise ValueError("truncated field")
        fields.append((b[0], body))
    return version, fields


def parse(data):
    version, fields = read_fields(data)
    pool, zones, tzver, idmap = None, {}, None, {}
    for fid, body in fields:
        if fid == 0:
            r = Reader(body)
            pool = [r.string() for _ in range(r.count())]
        elif fid == 1:
            zid = Reader(body, pool).string()
            zones[zid] = body
        elif fid == 2:
            tzver = Reader(body).string()
        elif fid == 3:
            r = Reader(body, pool)
            idmap = {r.string(): r.string() for _ in range(r.count())}
    return dict(format=version, version=tzver, pool=pool, zones=zones, idmap=idmap)


def read_year_offset(r):
    flags = r.byte()
    return dict(mode=flags >> 5, dow=(flags >> 2) & 7, advance=bool(flags & 2), add_day=bool(flags & 1),
                month=r.count(), dom=r.signed_count(), tod=r.millis() + DAY_MS)


def zone(nzd, key):
    key = nzd["idmap"].get(key, key)
    r = Reader(nzd["zones"][key], nzd["pool"])
    r.string()
    kind = r.byte()
    if kind == 1:
        off = r.millis()
        try:
            name = r.string()
        except (EOFError, IndexError):
            name = key
        return dict(periods=[(MIN, MAX, off, 0, name)], tail=None)
    if kind != 2:
        raise ValueError(f"unknown zone type {kind}")
    size = r.count()
    start = r.transition(None)
    periods = []
    for _ in range(size):
        name, off, sav = r.string(), r.millis(), r.millis()
        nxt = r.transition(start)
        periods.append((start, nxt, off, sav, name))
        start = nxt
    tail = None
    if r.byte() == 1:
        tail = dict(std=r.millis(), std_name=r.string(), std_yo=read_year_offset(r),
                    dst_name=r.string(), dst_yo=read_year_offset(r), savings=r.millis())
    return dict(periods=periods, tail=tail)


def _yo_instant(yo, year, std, prev_savings):
    month = yo["month"]
    last = calendar.monthrange(year, month)[1]
    d = dt.date(year, month, yo["dom"] if yo["dom"] > 0 else last + yo["dom"] + 1)
    if yo["dow"]:
        diff = yo["dow"] - (d.weekday() + 1)
        if yo["advance"]:
            diff %= 7
        elif diff > 0:
            diff -= 7
        d += dt.timedelta(days=diff)
    if yo["add_day"]:
        d += dt.timedelta(days=1)
    local = (dt.datetime(d.year, d.month, d.day, tzinfo=dt.timezone.utc) - EPOCH) // dt.timedelta(milliseconds=1) + yo["tod"]
    rule_off = {0: 0, 1: std + prev_savings, 2: std}[yo["mode"]]
    return local - rule_off


def offset_at(z, t_ms):
    """(wall offset ms, name) at UTC millis t_ms."""
    for s, e, off, sav, name in z["periods"]:
        if s <= t_ms < e:
            return off, name
    tail = z["tail"]
    if tail is None:
        raise ValueError("instant past the last period and no tail")
    std, sv = tail["std"], tail["savings"]
    year = (EPOCH + dt.timedelta(milliseconds=t_ms)).year
    events = []
    for y in (year - 1, year, year + 1):
        events.append((_yo_instant(tail["std_yo"], y, std, sv), std, tail["std_name"]))
        events.append((_yo_instant(tail["dst_yo"], y, std, 0), std + sv, tail["dst_name"]))
    events.sort()
    cur = None
    for when, off, name in events:
        if when <= t_ms:
            cur = (off, name)
    return cur


def find_embedded(blob):
    """Find a .nzd inside a .NET DLL: a uint32 LE length, then int32 0 and a string-pool field."""
    i = 0
    while True:
        i = blob.find(b"\x00\x00\x00\x00\x00", i + 1)
        if i < 4:
            return None
        (n,) = struct.unpack("<I", blob[i - 4:i])
        if 64 < n <= len(blob) - i:
            cand = blob[i:i + n]
            try:
                nzd = parse(cand)
                if nzd["version"] and nzd["zones"]:
                    return cand
            except Exception:
                pass


def load(path):
    data = open(path, "rb").read()
    if data[:2] == b"MZ":
        data = find_embedded(data)
        if data is None:
            raise SystemExit("no embedded .nzd found")
    return parse(data)


def fmt(ms):
    sign = "-" if ms < 0 else "+"
    m = abs(ms) // 60000
    return f"{sign}{m // 60:02d}:{m % 60:02d}"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("path")
    ap.add_argument("zones", nargs="*")
    ap.add_argument("--at", default="2026-11-20T12:00Z")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args(argv)
    nzd = load(a.path)
    if a.version:
        print(f"tzdb version: {nzd['version']} ({len(nzd['zones'])} zones, format {nzd['format']})")
    when = dt.datetime.fromisoformat(a.at.replace("Z", "+00:00"))
    t_ms = (when - EPOCH) // dt.timedelta(milliseconds=1)
    for key in a.zones:
        off, name = offset_at(zone(nzd, key), t_ms)
        print(f"{key:24s} {fmt(off)} {name}  (at {a.at})")


if __name__ == "__main__":
    sys.exit(main())
