"""What time zone data does a Joda-Time jar really ship? Decode its compiled zone files in Python.

Joda-Time never reads the system's or Java's zone data: it carries its own, compiled by its
ZoneInfoCompiler into `org/joda/time/tz/data/<Zone>` inside the jar. The manifest names a version
(`Time-Zone-Database-Version`), but a label isn't a run. This reads those bytes the way
`DateTimeZoneBuilder.readFrom` does (precalculated transitions, then an optional recurring
DST tail) and prints each zone's UTC offset at a moment.

    python3 -I joda_tz.py JAR America/Havana America/Edmonton --at 2026-11-20T12:00Z
    python3 -I joda_tz.py JAR --version

Put the downloaded jar in its own empty folder. Use controls (America/New_York, Europe/London).
Say plainly in any write-up that this is the jar's data decoded in Python, not Joda-Time run.
"""
import argparse
import calendar
import datetime as dt
import io
import struct
import sys
import zipfile

PREFIX = "org/joda/time/tz/data/"
EPOCH = dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)


class R:
    def __init__(self, data):
        self.f = io.BytesIO(data)

    def u8(self):
        b = self.f.read(1)
        if not b:
            raise EOFError
        return b[0]

    def i8(self):
        return struct.unpack(">b", self.f.read(1))[0]

    def u16(self):
        return struct.unpack(">H", self.f.read(2))[0]

    def i32(self):
        return struct.unpack(">i", self.f.read(4))[0]

    def i64(self):
        return struct.unpack(">q", self.f.read(8))[0]

    def utf(self):
        return self.f.read(self.u16()).decode("utf-8")

    def boolean(self):
        return self.u8() != 0

    def millis(self):
        """DateTimeZoneBuilder.readMillis: a two-bit form tag, then a signed value."""
        v = self.u8()
        form, low = v >> 6, v & 0x3F
        s = low - 64 if low & 0x20 else low  # 6-bit signed head
        if form == 0:
            return s * 30 * 60000
        if form == 1:
            return ((s << 24) | (self.u8() << 16) | (self.u8() << 8) | self.u8()) * 60000
        if form == 2:
            w = s << 32
            for shift in (24, 16, 8, 0):
                w |= self.u8() << shift
            return w * 1000
        return self.i64()


def read_ofyear(r):
    return dict(mode=chr(r.u8()), month=r.u8(), dom=r.i8(), dow=r.u8(), advance=r.boolean(), mod=r.millis())


def read_recurrence(r):
    oy = read_ofyear(r)
    return dict(oy, name=r.utf(), save=r.millis())


def read_dst(r):
    return dict(std=r.millis(), start=read_recurrence(r), end=read_recurrence(r))


def read_precalc(r):
    pool = [r.utf() for _ in range(r.u16())]
    size = r.i32()
    trans = []
    for _ in range(size):
        t, wall, std = r.millis(), r.millis(), r.millis()
        idx = r.u8() if len(pool) < 256 else r.u16()
        trans.append((t, wall, std, pool[idx]))
    tail = read_dst(r) if r.boolean() else None
    return dict(kind="P", trans=trans, tail=tail)


def parse(data):
    r = R(data)
    tag = chr(r.u8())
    if tag == "F":
        name = r.utf()
        wall, std = r.millis(), r.millis()
        return dict(kind="F", trans=[], tail=None, fixed=wall, name=name)
    if tag in ("C", "P"):
        return read_precalc(r)
    raise ValueError(f"unknown zone tag {tag!r}")


def _rule_instant(rec, year, std, prev_save):
    """OfYear.setInstant for one year, as UTC millis."""
    month = rec["month"]
    if rec["dom"] > 0:
        d = dt.date(year, month, min(rec["dom"], calendar.monthrange(year, month)[1]))
    else:
        d = dt.date(year, month, calendar.monthrange(year, month)[1]) + dt.timedelta(days=rec["dom"] + 1)
    if rec["dow"]:
        diff = rec["dow"] - (d.weekday() + 1)
        if rec["advance"]:
            diff %= 7
        elif diff > 0:
            diff -= 7
        d += dt.timedelta(days=diff)
    local = (dt.datetime(d.year, d.month, d.day, tzinfo=dt.timezone.utc) - EPOCH) // dt.timedelta(milliseconds=1) + rec["mod"]
    offset = {"u": 0, "s": std}.get(rec["mode"], std + prev_save)
    return local - offset


def offset_at(zone, t_ms):
    """Wall offset in ms at UTC millis t_ms, and the name key."""
    if zone["kind"] == "F":
        return zone["fixed"], zone["name"]
    trans = zone["trans"]
    best = None
    for t, wall, std, name in trans:
        if t <= t_ms:
            best = (wall, name)
        else:
            break
    tail = zone["tail"]
    if tail is None or (trans and t_ms < trans[-1][0]):
        return best
    std, a, b = tail["std"], tail["start"], tail["end"]
    year = (EPOCH + dt.timedelta(milliseconds=t_ms)).year
    events = []
    for y in (year - 1, year, year + 1):
        events.append((_rule_instant(a, y, std, b["save"]), a))
        events.append((_rule_instant(b, y, std, a["save"]), b))
    events.sort(key=lambda e: e[0])
    cur = None
    for when, rec in events:
        if when <= t_ms:
            cur = rec
    if trans and cur is not None:
        last_t = trans[-1][0]
        if all(when <= last_t for when, _ in events if when <= t_ms):
            return best
    return std + cur["save"], cur["name"]


def version(jar):
    z = zipfile.ZipFile(jar)
    for line in z.read("META-INF/MANIFEST.MF").decode("utf-8", "replace").splitlines():
        if line.lower().startswith("time-zone-database-version"):
            return line.split(":", 1)[1].strip()
    return None


def load(jar, key):
    z = zipfile.ZipFile(jar)
    return parse(z.read(PREFIX + key))


def fmt(ms):
    sign = "-" if ms < 0 else "+"
    m = abs(ms) // 60000
    return f"{sign}{m // 60:02d}:{m % 60:02d}"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("jar")
    ap.add_argument("zones", nargs="*")
    ap.add_argument("--at", default="2026-11-20T12:00Z")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args(argv)
    if a.version:
        print(f"manifest Time-Zone-Database-Version: {version(a.jar)}")
    when = dt.datetime.fromisoformat(a.at.replace("Z", "+00:00"))
    t_ms = (when - EPOCH) // dt.timedelta(milliseconds=1)
    for key in a.zones:
        off, name = offset_at(load(a.jar, key), t_ms)
        print(f"{key:24s} {fmt(off)} {name}  (at {a.at})")


if __name__ == "__main__":
    sys.exit(main())
