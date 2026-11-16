"""What time zone data does a Java runtime (or threetenbp/threetenabp) really ship? Decode tzdb.dat in Python.

java.time reads `lib/tzdb.dat` (JDK 8+); ThreeTen backports ship the same format as `TZDB.dat`
inside their jar/aar. The file names a version, but a label isn't a run. This reads the bytes the
way `TzdbZoneRulesProvider.load` and `ZoneRules.readExternal` do and prints each zone's UTC offset
at a moment, using `ZoneRules.getOffset(Instant)`'s logic (wall transitions, then the last rules).

    python3 -I java_tzdb.py tzdb.dat America/Havana America/Edmonton --at 2026-11-20T12:00Z
    python3 -I java_tzdb.py some.jar --version     # finds */TZDB.dat or */tzdb.dat inside a zip

Put downloads in their own empty folder. Use controls (America/New_York, Europe/London).
Say plainly in any write-up that this is the file's data decoded in Python, not Java run.
"""
import argparse
import calendar
import datetime as dt
import io
import struct
import sys
import zipfile

EPOCH = dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)


class R:
    def __init__(self, data):
        self.f = io.BytesIO(data)

    def read(self, fmt):
        n = struct.calcsize(fmt)
        b = self.f.read(n)
        if len(b) != n:
            raise EOFError
        return struct.unpack(">" + fmt, b)[0]

    def utf(self):
        return self.f.read(self.read("H")).decode("utf-8")

    def epoch_sec(self):
        hi = self.read("B")
        if hi == 255:
            return self.read("q")
        tot = (hi << 16) + (self.read("B") << 8) + self.read("B")
        return tot * 900 - 4575744000

    def offset(self):
        b = self.read("b")
        return self.read("i") if b == 127 else b * 900


def read_rule(r):
    data = r.read("I")
    month = data >> 28
    dom = ((data >> 22) & 63) - 32
    dow = (data >> 19) & 7
    time_byte = (data >> 14) & 31
    defn = (data >> 12) & 3  # 0 UTC, 1 WALL, 2 STANDARD
    std_byte = (data >> 4) & 255
    before_b = (data >> 2) & 3
    after_b = data & 3
    secs = r.read("i") if time_byte == 31 else (time_byte % 24) * 3600
    std = r.read("i") if std_byte == 255 else (std_byte - 128) * 900
    before = r.read("i") if before_b == 3 else std + before_b * 1800
    after = r.read("i") if after_b == 3 else std + after_b * 1800
    return dict(month=month, dom=dom, dow=dow, secs=secs, end_of_day=time_byte == 24, defn=defn,
                std=std, before=before, after=after)


def read_rules(data):
    r = R(data)
    kind = r.read("B")
    if kind != 1:
        raise ValueError(f"not ZoneRules (type {kind})")
    n = r.read("i")
    std_trans = [r.epoch_sec() for _ in range(n)]
    std_offs = [r.offset() for _ in range(n + 1)]
    n = r.read("i")
    wall_trans = [r.epoch_sec() for _ in range(n)]
    wall_offs = [r.offset() for _ in range(n + 1)]
    last = [read_rule(r) for _ in range(r.read("b"))]
    return dict(std_trans=std_trans, std_offs=std_offs, wall_trans=wall_trans, wall_offs=wall_offs, last=last)


def parse(data):
    r = R(data)
    if r.read("B") != 1:
        raise ValueError("not a tzdb.dat (format byte)")
    group = r.utf()
    versions = [r.utf() for _ in range(r.read("h"))]
    regions = [r.utf() for _ in range(r.read("h"))]
    rules = []
    for _ in range(r.read("h")):
        rules.append(r.f.read(r.read("h")))
    by_version = {}
    for v in versions:
        m = {}
        for _ in range(r.read("h")):
            reg = regions[r.read("h")]
            m[reg] = rules[r.read("H")]
        by_version[v] = m
    return dict(group=group, versions=versions, zones=by_version[versions[-1]] if versions else {})


def _transition(rule, year):
    if rule["dom"] < 0:
        d = dt.date(year, rule["month"], calendar.monthrange(year, rule["month"])[1] + 1 + rule["dom"])
        if rule["dow"]:
            d -= dt.timedelta(days=(d.weekday() + 1 - rule["dow"]) % 7)
    else:
        d = dt.date(year, rule["month"], rule["dom"])
        if rule["dow"]:
            d += dt.timedelta(days=(rule["dow"] - (d.weekday() + 1)) % 7)
    if rule["end_of_day"]:
        d += dt.timedelta(days=1)
    local = (dt.datetime(d.year, d.month, d.day, tzinfo=dt.timezone.utc) - EPOCH).total_seconds() + rule["secs"]
    # TimeDefinition.createDateTime turns the rule's time into wall time; the instant is wall - before
    if rule["defn"] == 0:
        local += rule["before"]
    elif rule["defn"] == 2:
        local += rule["before"] - rule["std"]
    return int(local) - rule["before"], rule["before"], rule["after"]


def offset_at(rules, epoch_sec):
    """ZoneRules.getOffset(Instant) in seconds."""
    wt, wo = rules["wall_trans"], rules["wall_offs"]
    if not wt:
        return wo[0]
    if rules["last"] and epoch_sec > wt[-1]:
        local = epoch_sec + wo[-1]
        year = (EPOCH + dt.timedelta(seconds=local)).year
        trans = [_transition(rule, year) for rule in rules["last"]]
        for when, before, after in trans:
            if epoch_sec < when:
                return before
        return trans[-1][2]
    lo = 0
    for i, t in enumerate(wt):
        if t <= epoch_sec:
            lo = i + 1
        else:
            break
    return wo[lo]


def read_file(path):
    if zipfile.is_zipfile(path):
        z = zipfile.ZipFile(path)
        names = [n for n in z.namelist() if n.lower().endswith("tzdb.dat")]
        if not names:
            raise SystemExit("no tzdb.dat inside")
        return z.read(names[0])
    return open(path, "rb").read()


def fmt(secs):
    sign = "-" if secs < 0 else "+"
    m = abs(secs) // 60
    return f"{sign}{m // 60:02d}:{m % 60:02d}"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("path")
    ap.add_argument("zones", nargs="*")
    ap.add_argument("--at", default="2026-11-20T12:00Z")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args(argv)
    db = parse(read_file(a.path))
    if a.version:
        print(f"group {db['group']}, versions {db['versions']}, {len(db['zones'])} zones")
    when = dt.datetime.fromisoformat(a.at.replace("Z", "+00:00"))
    t = int((when - EPOCH).total_seconds())
    for key in a.zones:
        print(f"{key:24s} {fmt(offset_at(read_rules(db['zones'][key]), t))}  (at {a.at})")


if __name__ == "__main__":
    sys.exit(main())
