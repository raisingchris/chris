"""Which time zone data is inside an ICU data package? Unpack it and run it through real ICU.

Many programs embed ICU's data as one `.dat` package (`icudt76l.dat`, or C arrays of hex bytes
like swift-foundation-icu's `icu_packaged_main_data.N.inc.h`). The zone rules live in
`zoneinfo64.res` inside it. This pulls the four zone `.res` files out, then loads them into this
machine's own libicu through `ICU_TIMEZONE_FILES_DIR` and prints the data version and offsets.

    python3 icu_dat.py PKG.dat [--hex] --out DIR [--at 2026-11-15T12:00Z] [ZONE ...]

--hex: the input files are C sources full of 0xNN bytes (several files are concatenated in order).
Say plainly in any write-up that this is the package's data run through the system's ICU code,
not a run of the program that ships it. Lesson (2026-11-15): check which package is actually
compiled in. swift-foundation-icu keeps a dead 2023c timezone package next to the live 2025b one.
A package baked into an executable (Deno): find `b"CmnD"`, step back 12 bytes, check bytes 2-3 are
0xda 0x27, and pass the slice from there to the end as PKG.dat; the TOC tells it where to stop.
"""
import argparse
import calendar
import ctypes
import ctypes.util
import datetime as dt
import glob
import os
import re
import struct
import subprocess
import sys

ZONE_FILES = ("zoneinfo64.res", "metaZones.res", "timezoneTypes.res", "windowsZones.res")
DEFAULT_ZONES = ["America/Vancouver", "America/Edmonton", "America/Yellowknife", "America/Inuvik",
                 "America/Winnipeg", "America/Havana", "Africa/Casablanca", "Africa/El_Aaiun"]
HEX = re.compile(rb"0x([0-9A-Fa-f]{2})")


def hex_to_bytes(paths):
    out = bytearray()
    for p in paths:
        with open(p, "rb") as f:
            out += bytes(int(h, 16) for h in HEX.findall(f.read()))
    return bytes(out)


def list_dat(b):
    """Return {entry name: bytes} for an ICU common-data package (little-endian)."""
    hs = struct.unpack_from("<H", b, 0)[0]
    if b[2:4] != b"\xda\x27":
        raise ValueError("not an ICU data package (no 0xda27 magic)")
    n = struct.unpack_from("<I", b, hs)[0]
    ents = [struct.unpack_from("<II", b, hs + 4 + 8 * i) for i in range(n)]
    out = {}
    for i, (no, do) in enumerate(ents):
        name = b[hs + no:b.index(b"\0", hs + no)].decode()
        end = hs + ents[i + 1][1] if i + 1 < n else len(b)
        out[name] = b[hs + do:end]
    return out


def extract_zone_files(b, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    got = []
    for name, data in list_dat(b).items():
        base = name.split("/")[-1]
        if base in ZONE_FILES:
            with open(os.path.join(out_dir, base), "wb") as f:
                f.write(data)
            got.append(name)
    return got


def find_icu_version():
    for p in glob.glob("/usr/lib/*/libicui18n.so.*") + glob.glob("/usr/lib/libicui18n.so.*"):
        m = re.search(r"\.so\.(\d+)$", p)
        if m:
            return m.group(1)
    return None


def icu_offsets(zones, when, version):
    """Run in-process; ICU_TIMEZONE_FILES_DIR must be set before this process loads ICU."""
    lib = ctypes.CDLL("libicui18n.so." + version)
    fn = lambda n: getattr(lib, n + "_" + version)
    err = ctypes.c_int(0)
    fn("ucal_getTZDataVersion").restype = ctypes.c_char_p
    ver = fn("ucal_getTZDataVersion")(ctypes.byref(err)).decode()
    fn("ucal_open").restype = ctypes.c_void_p
    ms = calendar.timegm(when.utctimetuple()) * 1000.0
    rows = []
    for z in zones:
        err = ctypes.c_int(0)
        cal = fn("ucal_open")(z.encode("utf-16le") + b"\0\0", len(z), b"en_US", 0, ctypes.byref(err))
        fn("ucal_setMillis")(ctypes.c_void_p(cal), ctypes.c_double(ms), ctypes.byref(err))
        off = sum(fn("ucal_get")(ctypes.c_void_p(cal), f, ctypes.byref(err)) for f in (15, 16))
        fn("ucal_close")(ctypes.c_void_p(cal))
        rows.append((z, off // 60000, err.value))
    return ver, rows


def run_child(res_dir, zones, at):
    env = dict(os.environ, ICU_TIMEZONE_FILES_DIR=os.path.abspath(res_dir))
    cmd = [sys.executable, "-I", os.path.abspath(__file__), "--child", "--at", at] + zones
    return subprocess.run(cmd, env=env, capture_output=True, text=True, check=True).stdout


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="*")
    ap.add_argument("--hex", action="store_true")
    ap.add_argument("--out")
    ap.add_argument("--at", default="2026-11-15T12:00Z")
    ap.add_argument("--zone", action="append")
    ap.add_argument("--child", action="store_true")
    a = ap.parse_args(argv)
    when = dt.datetime.fromisoformat(a.at.replace("Z", "+00:00"))
    if a.child:
        version = find_icu_version()
        ver, rows = icu_offsets(a.inputs or DEFAULT_ZONES, when, version)
        print(f"ICU {version}, TZ data version: {ver}")
        for z, mins, e in rows:
            print(f"{z:22s} {mins / 60:+g}" + (f"  err={e}" if e > 0 else ""))
        return 0
    b = hex_to_bytes(a.inputs) if a.hex else open(a.inputs[0], "rb").read()
    print("extracted:", ", ".join(extract_zone_files(b, a.out)) or "nothing")
    if find_icu_version() is None:
        print("no system libicu found; files are in", a.out)
        return 0
    print(run_child(a.out, a.zone or DEFAULT_ZONES, a.at), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
