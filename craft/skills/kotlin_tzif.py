"""What time zone data does kotlinx-datetime's bundled zoneinfo really ship? Decode it in Python.

On Wasm/WASI, kotlinx-datetime reads zones from `kotlinx-datetime-zoneinfo`, a separate artifact.
Its sources jar is generated Kotlin: `tzData.kt` maps names to `tzDataN`, and each `tzDataN.kt`
holds `byteArrayOf(84, 90, 105, 102, ...)`, a TZif file. I can't build Kotlin here, but I can read
those bytes and load them with zoneinfo.

    python3 kotlin_tzif.py SRC_DIR America/Havana America/Edmonton --at 2026-11-15T12:00Z
    python3 kotlin_tzif.py SRC_DIR --version

SRC_DIR is the unpacked sources jar (the folder holding tzData.kt).
Say plainly in any write-up that this is the artifact's data decoded in Python, not a Kotlin run.
"""
import argparse
import datetime as dt
import io
import os
import re
import sys
from zoneinfo import ZoneInfo


def find_src(root):
    for d, _, files in os.walk(root):
        if "tzData.kt" in files:
            return d
    raise SystemExit(f"no tzData.kt under {root}")


def version(src):
    with open(os.path.join(src, "tzData.kt"), encoding="utf-8") as f:
        m = re.search(r"ZONE INFO DATABASE v\.(\S+?)\s*\*/", f.read(4000))
    return m.group(1) if m else None


def name_map(src):
    with open(os.path.join(src, "tzData.kt"), encoding="utf-8") as f:
        return dict(re.findall(r'"([^"]+)"\s*->\s*(tzData\d+)', f.read()))


def zone_bytes(src, val):
    with open(os.path.join(src, val + ".kt"), encoding="utf-8") as f:
        text = f.read()
    m = re.search(r"byteArrayOf\(([^)]*)\)", text)
    if not m:
        raise ValueError(f"no byteArrayOf in {val}.kt")
    nums = [int(x) for x in re.findall(r"-?\d+", m.group(1))]
    return bytes(n % 256 for n in nums)


def footer(data):
    return data.rstrip(b"\n").rsplit(b"\n", 1)[-1].decode("ascii", "replace")


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("root")
    p.add_argument("zones", nargs="*")
    p.add_argument("--at", default="2026-11-15T12:00Z")
    p.add_argument("--version", action="store_true")
    a = p.parse_args(argv)
    src = find_src(a.root)
    print("database:", version(src))
    if a.version:
        return 0
    when = dt.datetime.fromisoformat(a.at.replace("Z", "+00:00"))
    names = name_map(src)
    for z in a.zones:
        if z not in names:
            print(f"{z}\tnot in data")
            continue
        data = zone_bytes(src, names[z])
        try:
            off = when.astimezone(ZoneInfo.from_file(io.BytesIO(data), key=z)).utcoffset()
        except ValueError as e:  # e.g. a footer zoneinfo can't parse
            print(f"{z}\tunreadable ({e})\t{footer(data)}")
            continue
        print(f"{z}\t{off.total_seconds() / 3600:+g}\t{footer(data)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
