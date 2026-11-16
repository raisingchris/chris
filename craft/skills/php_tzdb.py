"""What time zone data does PHP really ship? Decode timelib's `timezonedb.h` in Python.

PHP's built-in copy (php-src `ext/date/lib/timezonedb.h`) and PECL `timezonedb` store each
zone as a "PHP2" blob in a C hex array. Inside each blob is a normal TZif v2 section, so I
wrap it with an empty v1 header and hand it to zoneinfo. That gives the offset PHP users get
from that build's own data, without running PHP. The file can hold two arrays (slim and fat
builds); both are decoded.

    python3 php_tzdb.py timezonedb.h --zone America/Havana --zone America/Winnipeg
    python3 php_tzdb.py timezonedb.h --at 2026-11-16T12:00Z

Say plainly in any write-up that this is the data decoded in Python, not a PHP run.
"""
import argparse
import datetime as dt
import io
import re
from zoneinfo import ZoneInfo

DEFAULT_ZONES = ["America/Vancouver", "America/Edmonton", "America/Inuvik", "America/Winnipeg",
                 "America/Havana", "Africa/Casablanca", "Europe/London"]


def arrays(text):
    """Yield (version, {zone: blob}) for each data array in a timezonedb.h text."""
    version = re.search(r'timelib_tzdb timezonedb_builtin = \{ "([^"]*)"', text)
    version = version.group(1) if version else None
    starts = [m.end() for m in re.finditer(r'timelib_timezone_db_data_builtin\[\d+\] = \{', text)]
    idxs = re.findall(r'timezonedb_idx_builtin\[\d+\] = \{(.*?)\};', text, re.S)
    for start, idx in zip(starts, idxs):
        body = text[start:text.index("};", start)]
        data = bytes(int(x, 16) for x in re.findall(r'0x([0-9A-Fa-f]{2})', body))
        ent = [(n, int(o, 16)) for n, o in re.findall(r'"([^"]+)"\s*,\s*0x([0-9A-Fa-f]+)', idx)]
        ends = sorted({o for _, o in ent} | {len(data)})
        blobs = {}
        for name, off in ent:
            end = next(e for e in ends if e > off)
            blobs[name] = data[off:end]
        yield version, blobs


def zone(blob, key):
    """Turn one PHP2 blob into a ZoneInfo by wrapping its TZif v2 section."""
    k = blob.find(b"TZif")
    if k < 0:
        raise ValueError("no TZif section in blob")
    fake = b"TZif2" + b"\0" * 15 + b"\0" * 24 + blob[k:]
    return ZoneInfo.from_file(io.BytesIO(fake), key=key)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("path")
    ap.add_argument("--zone", action="append")
    ap.add_argument("--at", default="2026-11-16T12:00Z")
    a = ap.parse_args(argv)
    at = dt.datetime.fromisoformat(a.at.replace("Z", "+00:00"))
    text = open(a.path, encoding="latin-1").read()
    out = []
    for i, (version, blobs) in enumerate(arrays(text)):
        out.append(f"array {i}: version {version}, {len(blobs)} zones")
        for z in a.zone or DEFAULT_ZONES:
            if z not in blobs:
                out.append(f"  {z} missing")
                continue
            out.append(f"  {z} {at.astimezone(zone(blobs[z], z)).strftime('%H:%M %z')}")
    print("\n".join(out))
    return out


if __name__ == "__main__":
    main()
