import datetime as dt
import pathlib
import struct
import sys
import zipfile

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import java_tzdb as J  # noqa: E402

H = 3600


def utf(s):
    b = s.encode()
    return struct.pack(">H", len(b)) + b


def epoch_sec(t):
    if -4575744000 <= t < 10413792000 and t % 900 == 0:
        s = (t + 4575744000) // 900
        return bytes([(s >> 16) & 255, (s >> 8) & 255, s & 255])
    return b"\xff" + struct.pack(">q", t)


def offset(o):
    return struct.pack(">b", o // 900) if o % 900 == 0 and abs(o // 900) < 127 else b"\x7f" + struct.pack(">i", o)


def rule(month, dom, dow, hour, defn, std, before, after):
    data = (month << 28) | ((dom + 32) << 22) | (dow << 19) | (hour << 14) | (defn << 12)
    data |= ((std // 900 + 128) << 4) | (((before - std) // 1800) << 2) | ((after - std) // 1800)
    return struct.pack(">I", data)


def ts(s):
    return int(dt.datetime.fromisoformat(s).timestamp())


def ny_rules():
    t1, t2 = ts("2007-03-11T07:00+00:00"), ts("2007-11-04T06:00+00:00")
    b = b"\x01" + struct.pack(">i", 0) + offset(-5 * H)
    b += struct.pack(">i", 2) + epoch_sec(t1) + epoch_sec(t2) + offset(-5 * H) + offset(-4 * H) + offset(-5 * H)
    b += struct.pack(">b", 2)
    b += rule(3, 8, 7, 2, 1, -5 * H, -5 * H, -4 * H)  # second Sunday March, 02:00 wall
    b += rule(11, 1, 7, 2, 1, -5 * H, -4 * H, -5 * H)  # first Sunday Nov, 02:00 wall
    return b


def fixed_rules(o):
    return b"\x01" + struct.pack(">i", 0) + offset(o) + struct.pack(">i", 0) + offset(o) + struct.pack(">b", 0)


def build():
    rules = [ny_rules(), fixed_rules(-4 * H)]
    out = b"\x01" + utf("TZDB") + struct.pack(">h", 1) + utf("2026f")
    regions = ["Test/NY", "Test/Fixed"]
    out += struct.pack(">h", len(regions)) + b"".join(utf(r) for r in regions)
    out += struct.pack(">h", len(rules)) + b"".join(struct.pack(">h", len(r)) + r for r in rules)
    out += struct.pack(">h", 2) + struct.pack(">hH", 0, 0) + struct.pack(">hH", 1, 1)
    return out


def test_last_rules_and_fixed():
    db = J.parse(build())
    assert db["versions"] == ["2026f"]
    ny = J.read_rules(db["zones"]["Test/NY"])
    assert J.offset_at(ny, ts("2000-01-01T00:00+00:00")) == -5 * H
    assert J.offset_at(ny, ts("2007-07-01T00:00+00:00")) == -4 * H
    assert J.offset_at(ny, ts("2026-07-01T12:00+00:00")) == -4 * H
    assert J.offset_at(ny, ts("2026-11-20T12:00+00:00")) == -5 * H
    assert J.offset_at(ny, ts("2027-03-14T06:59+00:00")) == -5 * H
    assert J.offset_at(ny, ts("2027-03-14T07:00+00:00")) == -4 * H
    assert J.offset_at(ny, ts("2027-11-07T05:59+00:00")) == -4 * H
    assert J.offset_at(ny, ts("2027-11-07T06:00+00:00")) == -5 * H
    assert J.offset_at(J.read_rules(db["zones"]["Test/Fixed"]), ts("2026-11-20T12:00+00:00")) == -4 * H


def test_reads_tzdb_inside_a_jar(tmp_path, capsys):
    p = tmp_path / "x.jar"
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("org/threeten/bp/TZDB.dat", build())
    J.main([str(p), "--version", "Test/NY", "--at", "2026-11-20T12:00Z"])
    out = capsys.readouterr().out
    assert "2026f" in out and "-" + "05:00" in out
