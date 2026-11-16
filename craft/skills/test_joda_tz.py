import pathlib
import struct
import sys
import zipfile

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import joda_tz as j  # noqa: E402

H = 3600000


def w_millis(ms):
    # Always use form 3 (raw long) except whole half-hours (form 0), to exercise both.
    if ms % (30 * 60000) == 0 and -32 <= ms // (30 * 60000) < 32:
        return bytes([(ms // (30 * 60000)) & 0x3F])
    if ms % 1000 == 0 and -(1 << 37) <= ms // 1000 < (1 << 37):
        s = ms // 1000
        return bytes([0x80 | ((s >> 32) & 0x3F)]) + struct.pack(">I", s & 0xFFFFFFFF)
    return b"\xc0" + struct.pack(">q", ms)


def w_utf(s):
    b = s.encode()
    return struct.pack(">H", len(b)) + b


def w_rec(mode, month, dom, dow, adv, mod, name, save):
    return bytes([ord(mode), month]) + struct.pack(">b", dom) + bytes([dow, int(adv)]) + w_millis(mod) + w_utf(name) + w_millis(save)


def ny_like(tail=True):
    pool = ["EST", "EDT"]
    out = b"C" + struct.pack(">H", len(pool)) + b"".join(w_utf(p) for p in pool)
    trans = [(1173596400000, -4 * H, -5 * H, 1), (1194152400000, -5 * H, -5 * H, 0)]  # 2007-03-11, 2007-11-04
    out += struct.pack(">i", len(trans))
    for t, wall, std, i in trans:
        out += w_millis(t) + w_millis(wall) + w_millis(std) + bytes([i])
    if tail:
        out += b"\x01" + w_millis(-5 * H)
        out += w_rec("w", 3, 8, 7, True, 2 * H, "EDT", H)
        out += w_rec("w", 11, 1, 7, True, 2 * H, "EST", 0)
    else:
        out += b"\x00"
    return out


def make_jar(tmp, zones):
    p = tmp / "fake.jar"
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\nTime-Zone-Database-Version: 2026fgtz\n")
        for k, data in zones.items():
            z.writestr(j.PREFIX + k, data)
    return p


def ms(s):
    import datetime as dt
    return (dt.datetime.fromisoformat(s) - j.EPOCH) // dt.timedelta(milliseconds=1)


def test_millis_forms_roundtrip():
    for v in (0, -5 * H, 2 * H, 1173596400000, -2208988800000, 1234567):
        assert j.R(w_millis(v)).millis() == v


def test_tail_rule_gives_summer_and_winter(tmp_path):
    jar = make_jar(tmp_path, {"America/New_York": ny_like()})
    z = j.load(jar, "America/New_York")
    assert j.offset_at(z, ms("2026-07-01T12:00+00:00")) == (-4 * H, "EDT")
    assert j.offset_at(z, ms("2026-11-20T12:00+00:00")) == (-5 * H, "EST")
    # second Sunday of March 2027 is 14 March; 2am EST = 07:00 UTC
    assert j.offset_at(z, ms("2027-03-14T06:59+00:00"))[0] == -5 * H
    assert j.offset_at(z, ms("2027-03-14T07:00+00:00"))[0] == -4 * H


def test_no_tail_holds_last_transition_and_version(tmp_path, capsys):
    jar = make_jar(tmp_path, {"X/Y": ny_like(tail=False)})
    z = j.load(jar, "X/Y")
    assert j.offset_at(z, ms("2030-07-01T00:00+00:00")) == (-5 * H, "EST")
    j.main([str(jar), "--version", "X/Y", "--at", "2030-07-01T00:00Z"])
    out = capsys.readouterr().out
    assert "2026fgtz" in out and "-" + "05:00 EST" in out
