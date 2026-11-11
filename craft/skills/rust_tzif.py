"""What time zone data does a Rust crate really ship? Decode its TZif byte literals in Python.

Some crates (tzdb_data, others) bundle tzdb as `const NAME: &[u8] = b"TZif...";` in a .rs file.
I can't always build Rust here (no linker), but I can read the bytes and load them with
zoneinfo. That shows the offset a Rust user would get, from the crate's own data.

    python3 rust_tzif.py raw_tzdata.rs AMERICA_EDMONTON CUBA --at 2026-11-15T12:00Z
    python3 rust_tzif.py raw_tzdata.rs --list | head

Prints: NAME  offset-hours  footer (the POSIX TZ rule for times after the last transition).
Say plainly in any write-up that this is the crate's data decoded in Python, not a Rust run.
"""
import argparse
import datetime as dt
import io
import re
import sys
from zoneinfo import ZoneInfo

_ESC = {"0": 0, "n": 10, "t": 9, "r": 13, "\\": 92, '"': 34, "'": 39}
_CONST = r'const\s+(%s)\s*:\s*&(?:\'static\s+)?\[u8(?:;\s*\d+)?\]\s*=\s*b"((?:[^"\\]|\\.)*)"\s*;'


def rust_bytes(lit):
    """Turn the inside of a Rust b"..." literal into bytes."""
    out = bytearray()
    i = 0
    while i < len(lit):
        c = lit[i]
        if c == "\\":
            n = lit[i + 1]
            if n == "x":
                out.append(int(lit[i + 2:i + 4], 16))
                i += 4
                continue
            if n == "\n":  # line continuation: skip the newline and leading whitespace
                i += 2
                while i < len(lit) and lit[i] in " \t\r\n":
                    i += 1
                continue
            out.append(_ESC[n])
            i += 2
            continue
        out.append(ord(c))
        i += 1
    return bytes(out)


def find_consts(src, names=None):
    """{name: bytes} for byte-string consts in src (all of them if names is None)."""
    pat = _CONST % ("|".join(map(re.escape, names)) if names else r"\w+")
    return {m.group(1): rust_bytes(m.group(2)) for m in re.finditer(pat, src, re.S)}


def footer(data):
    lines = data.rstrip(b"\n").rsplit(b"\n", 1)
    return lines[-1].decode("ascii", "replace") if len(lines) == 2 else ""


def offset_at(data, when, key="x"):
    z = ZoneInfo.from_file(io.BytesIO(data), key=key)
    return when.astimezone(z).utcoffset().total_seconds() / 3600


def parse_when(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(dt.timezone.utc)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("source")
    ap.add_argument("names", nargs="*")
    ap.add_argument("--at", default=None, help="ISO time, default now (UTC)")
    ap.add_argument("--list", action="store_true", help="only list const names")
    a = ap.parse_args(argv)
    src = open(a.source, encoding="utf-8").read()
    found = find_consts(src, a.names or None)
    if a.list:
        print("\n".join(sorted(n for n, d in found.items() if d.startswith(b"TZif"))))
        return 0
    when = parse_when(a.at) if a.at else dt.datetime.now(dt.timezone.utc)
    rc = 0
    for name in a.names or sorted(found):
        d = found.get(name)
        if d is None:
            print(f"{name}\tMISSING")
            rc = 1
            continue
        if not d.startswith(b"TZif"):
            continue
        print(f"{name}\t{offset_at(d, when, name):+g}\t{footer(d)}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
