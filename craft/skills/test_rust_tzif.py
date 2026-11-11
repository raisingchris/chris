import datetime as dt
import importlib.resources
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import rust_tzif as rt  # noqa: E402


def tzif(key):
    parts = key.split("/")
    return importlib.resources.files("tzdata.zoneinfo").joinpath(*parts).read_bytes()


def as_rust_literal(data):
    """Write bytes the way generated Rust does: printable ASCII as is, the rest as escapes."""
    out = []
    for b in data:
        if b == 10:
            out.append("\\n")
        elif b == 0:
            out.append("\\0")
        elif b in (34, 92):
            out.append("\\" + chr(b))
        elif 32 <= b < 127:
            out.append(chr(b))
        else:
            out.append("\\x%02x" % b)
    return "".join(out)


def rs_file(tmp_path, consts):
    body = "\n".join(f'pub(crate) const {n}: &[u8] = b"{as_rust_literal(d)}";' for n, d in consts.items())
    p = tmp_path / "raw.rs"
    p.write_text("// generated\n" + body + '\nconst NOT_TZ: &[u8] = b"hello\\x21";\n')
    return p


def test_round_trip_and_offset(tmp_path):
    ed = tzif("America/Edmonton")
    src = rs_file(tmp_path, {"AMERICA_EDMONTON": ed}).read_text()
    got = rt.find_consts(src)
    assert got["AMERICA_EDMONTON"] == ed
    assert got["NOT_TZ"] == b"hello!"
    when = dt.datetime(2026, 11, 15, 12, tzinfo=dt.timezone.utc)
    want = when.astimezone(rt.ZoneInfo("America/Edmonton")).utcoffset().total_seconds() / 3600
    assert rt.offset_at(got["AMERICA_EDMONTON"], when) == want
    assert rt.footer(ed) and "\n" not in rt.footer(ed)


def test_line_continuation():
    assert rt.rust_bytes('ab\\\n     cd') == b"abcd"


def test_main_list_and_missing(tmp_path, capsys):
    p = rs_file(tmp_path, {"CUBA": tzif("Cuba")})
    assert rt.main([str(p), "--list"]) == 0
    assert capsys.readouterr().out.split() == ["CUBA"]
    assert rt.main([str(p), "CUBA", "NOPE", "--at", "2026-11-15T12:00Z"]) == 1
    out = capsys.readouterr().out
    assert "NOPE\tMISSING" in out and out.startswith("CUBA\t")
