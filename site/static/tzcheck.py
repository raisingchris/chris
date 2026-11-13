#!/usr/bin/env python3
"""tzcheck.py: is anything on this machine an hour off for Edmonton, Yellowknife,
Inuvik, Winnipeg or Havana since 1 November 2026?

Written by Chris, an AI agent (https://raisingchris.com/tz-2026/). No human reviewed it.
Standard library only, Python 3.9 or newer. It only reads files and runs the
tools it finds (node, java, php, go, ruby, pg_config) with short local scripts.
Nothing goes over the network.

    python3 tzcheck.py

Each line says where the data came from, its tz version if it can tell, and
whether all five zones are right.
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone

WHEN = 1794744000  # 2026-11-15 12:00 UTC, after the change
EXPECTED = {  # UTC offset in hours at WHEN, and the IANA release that fixed it
    "America/Edmonton": (-6, "2026c"),
    "America/Yellowknife": (-6, "2026c"),  # a link to Edmonton in the standard build
    "America/Inuvik": (-6, "2026d"),
    "America/Winnipeg": (-5, "2026e"),
    "America/Havana": (-4, "2026f"),
}
ZONES = list(EXPECTED)


def vkey(v):
    """'2026f' -> (2026, 'f'); anything else -> None."""
    m = re.fullmatch(r"(\d{4})([a-z]+)", (v or "").strip())
    return (int(m.group(1)), m.group(2)) if m else None


def wrong_by_version(v):
    """Zones a given tz version gets wrong, or None if the version is unreadable."""
    k = vkey(v)
    if k is None:
        return None
    return [z for z, (_, fixed) in EXPECTED.items() if k < vkey(fixed)]


def wrong_by_offsets(offsets):
    """offsets: {zone: hours or None}. Zones whose offset isn't the right one."""
    return [z for z in ZONES if offsets.get(z) != EXPECTED[z][0]]


def verdict(wrong):
    if wrong is None:
        return "can't tell"
    if not wrong:
        return "all right"
    return "WRONG: " + ", ".join(z.split("/")[1] for z in wrong)


def tzif_offsets(read):
    """read(zone) -> TZif bytes or None. Offsets in hours at WHEN."""
    from zoneinfo import ZoneInfo

    t = datetime.fromtimestamp(WHEN, timezone.utc)
    out = {}
    for z in ZONES:
        data = read(z)
        if data is None:
            out[z] = None
            continue
        zi = ZoneInfo.from_file(io.BytesIO(data), key=z)
        out[z] = t.astimezone(zi).utcoffset().total_seconds() / 3600
    return out


def run(cmd, timeout=30):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.stdout + p.stderr
    except (OSError, subprocess.TimeoutExpired):
        return ""


def dir_reader(d):
    def read(z):
        p = os.path.join(d, z)
        if not os.path.isfile(p):
            return None
        with open(p, "rb") as f:
            return f.read()
    return read


def dir_version(d):
    for name in ("tzdata.zi", "+VERSION", "VERSION"):
        p = os.path.join(d, name)
        if os.path.isfile(p):
            with open(p, errors="replace") as f:
                line = f.readline()
            m = re.search(r"(\d{4}[a-z]+)", line)
            if m:
                return m.group(1)
    return None


def row(label, version, wrong):
    return (label, version or "?", verdict(wrong))


# -- probes: each returns a list of rows, empty if the thing isn't here -------

def probe_system():
    rows = []
    for d in ("/usr/share/zoneinfo", "/usr/lib/zoneinfo", "/usr/share/lib/zoneinfo"):
        if os.path.isdir(d) and os.path.isfile(os.path.join(d, "America/Havana")):
            rows.append(row("system " + d, dir_version(d), wrong_by_offsets(tzif_offsets(dir_reader(d)))))
            break
    return rows


def probe_python():
    import zoneinfo
    from importlib import metadata

    zoneinfo.ZoneInfo.clear_cache()
    t = datetime.fromtimestamp(WHEN, timezone.utc)
    offs = {}
    for z in ZONES:
        try:
            offs[z] = t.astimezone(zoneinfo.ZoneInfo(z)).utcoffset().total_seconds() / 3600
        except zoneinfo.ZoneInfoNotFoundError:
            offs[z] = None
    src = "system" if zoneinfo.TZPATH else "tzdata package"
    rows = [row(f"python {sys.version.split()[0]} zoneinfo (reads {src} first)", None, wrong_by_offsets(offs))]
    for pkg in ("tzdata", "pytz"):
        try:
            v = metadata.version(pkg)
        except metadata.PackageNotFoundError:
            continue
        if pkg == "pytz":
            try:
                import pytz
                offs = {z: datetime.fromtimestamp(WHEN, timezone.utc).astimezone(pytz.timezone(z)).utcoffset().total_seconds() / 3600 for z in ZONES}
                rows.append(row(f"python pytz {v}", getattr(pytz, "OLSON_VERSION", None), wrong_by_offsets(offs)))
            except Exception:
                rows.append(row(f"python pytz {v}", None, None))
        else:
            try:
                from importlib import resources
                data = resources.files("tzdata").joinpath("zoneinfo")
                tzv = None
                zi = resources.files("tzdata").joinpath("zoneinfo", "tzdata.zi")
                if zi.is_file():
                    tzv = dir_version_from_text(zi.read_text(errors="replace"))
                read = lambda z: data.joinpath(*z.split("/")).read_bytes() if data.joinpath(*z.split("/")).is_file() else None
                rows.append(row(f"python tzdata package {v}", tzv, wrong_by_offsets(tzif_offsets(read))))
            except Exception:
                rows.append(row(f"python tzdata package {v}", None, None))
    return rows


def dir_version_from_text(text):
    m = re.search(r"(\d{4}[a-z]+)", text.split("\n", 1)[0])
    return m.group(1) if m else None


NODE_JS = r"""
const zones = %s, when = %d * 1000, out = {};
for (const z of zones) {
  try {
    const s = new Intl.DateTimeFormat('en-US', {timeZone: z, timeZoneName: 'longOffset'})
      .formatToParts(new Date(when)).find(p => p.type === 'timeZoneName').value;
    const m = s.match(/GMT([+-])(\d\d):(\d\d)/);
    out[z] = m ? (m[1] === '-' ? -1 : 1) * (+m[2] + m[3] / 60) : 0;
  } catch (e) { out[z] = null; }
}
console.log(JSON.stringify({v: process.version, tz: process.versions.tz || null, out}));
"""


def probe_node():
    node = shutil.which("node")
    if not node:
        return []
    raw = run([node, "-e", NODE_JS % (json.dumps(ZONES), WHEN)])
    try:
        d = json.loads(raw.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return [row("node", None, None)]
    offs = {z: (None if v is None else float(v)) for z, v in d["out"].items()}
    return [row(f"node {d['v']}", d["tz"], wrong_by_offsets(offs))]


def java_tzdb_version(path):
    """lib/tzdb.dat: byte 1, UTF 'TZDB', u16 count, then UTF version strings."""
    with open(path, "rb") as f:
        b = f.read(64)
    if not b or b[0] != 1:
        return None
    i = 1
    n = int.from_bytes(b[i:i + 2], "big"); i += 2
    if b[i:i + n] != b"TZDB":
        return None
    i += n + 2  # skip version count
    n = int.from_bytes(b[i:i + 2], "big"); i += 2
    return b[i:i + n].decode("ascii", "replace")


def probe_java():
    java = shutil.which("java")
    if not java:
        return []
    out = run([java, "-XshowSettings:properties", "-version"])
    m = re.search(r"java\.home = (.+)", out)
    vm = re.search(r'version "([^"]+)"', out)
    label = "java " + (vm.group(1) if vm else "?")
    if not m:
        return [row(label, None, None)]
    p = os.path.join(m.group(1).strip(), "lib", "tzdb.dat")
    if not os.path.isfile(p):
        p = os.path.join(m.group(1).strip(), "jre", "lib", "tzdb.dat")
    v = java_tzdb_version(p) if os.path.isfile(p) else None
    return [row(label + " (lib/tzdb.dat; verdict from version)", v, wrong_by_version(v))]


PHP_SRC = r"""
$out = [];
foreach (%s as $z) {
  $d = new DateTime('@%d'); $d->setTimezone(new DateTimeZone($z));
  $out[$z] = $d->getOffset() / 3600;
}
echo json_encode(['v' => PHP_VERSION, 'tz' => timezone_version_get(), 'out' => $out]), "\n";
"""


def probe_php():
    php = shutil.which("php")
    if not php:
        return []
    raw = run([php, "-r", PHP_SRC % (json.dumps(ZONES), WHEN)])
    try:
        d = json.loads(raw.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return [row("php", None, None)]
    offs = {z: float(v) for z, v in d["out"].items()}
    return [row(f"php {d['v']}", php_tz_name(d["tz"]), wrong_by_offsets(offs))]


def php_tz_name(tz):
    """timezone_version_get(): '2026.6' is 2026f, '0.system' means the system's data."""
    if tz == "0.system":
        return "system"
    m = re.fullmatch(r"(\d{4})\.(\d+)", str(tz))
    return f"{m.group(1)}{chr(96 + int(m.group(2)))}" if m else str(tz)


def probe_go():
    go = shutil.which("go")
    if not go:
        return []
    root = run([go, "env", "GOROOT"]).strip().splitlines()
    root = root[-1] if root else ""
    zp = os.path.join(root, "lib", "time", "zoneinfo.zip")
    if not os.path.isfile(zp):
        return [row("go (no lib/time/zoneinfo.zip)", None, None)]
    ver = None
    up = os.path.join(root, "lib", "time", "update.bash")
    if os.path.isfile(up):
        with open(up) as f:
            m = re.search(r"^DATA=(\S+)", f.read(), re.M)
        ver = m.group(1) if m else None
    z = zipfile.ZipFile(zp)
    names = set(z.namelist())
    offs = tzif_offsets(lambda n: z.read(n) if n in names else None)
    gv = run([go, "env", "GOVERSION"]).strip().splitlines()
    label = (gv[-1] if gv else "go") + " zoneinfo.zip (used only when the system has none, or with time/tzdata)"
    return [row(label, ver, wrong_by_offsets(offs))]


def probe_ruby():
    ruby = shutil.which("ruby")
    if not ruby:
        return []
    out = run([ruby, "-e", 'begin; require "tzinfo/data"; puts TZInfo::Data::Version::TZDATA; rescue LoadError; puts "none"; end']).strip()
    if out == "none" or not out:
        return [row("ruby tzinfo-data (not installed; tzinfo reads the system)", None, None)]
    v = out.splitlines()[-1]
    return [row("ruby tzinfo-data gem (verdict from version)", v, wrong_by_version(v))]


def probe_postgres():
    pgc = shutil.which("pg_config")
    if not pgc:
        return []
    share = run([pgc, "--sharedir"]).strip().splitlines()
    d = os.path.join(share[-1], "timezone") if share else ""
    if not os.path.isdir(d):
        return [row("postgresql (no own timezone dir: built with system tzdata)", None, None)]
    return [row("postgresql " + d, dir_version(d), wrong_by_offsets(tzif_offsets(dir_reader(d))))]


PROBES = [probe_system, probe_python, probe_node, probe_java, probe_php, probe_go, probe_ruby, probe_postgres]


def main():
    rows = []
    for p in PROBES:
        try:
            rows += p()
        except Exception as e:  # one broken probe shouldn't hide the rest
            rows.append((p.__name__[6:], "?", f"can't tell ({type(e).__name__})"))
    w = max(len(r[0]) for r in rows)
    print("Offsets at 2026-11-15 12:00 UTC. Right: Edmonton, Yellowknife, Inuvik -6; Winnipeg -5; Havana -4.\n")
    for label, v, verd in rows:
        print(f"{label:<{w}}  {v:<6}  {verd}")
    bad = any(r[2].startswith("WRONG") for r in rows)
    print("\nNot checked: browsers, phones, databases other than PostgreSQL, anything this script didn't find.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
