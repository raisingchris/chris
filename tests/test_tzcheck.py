"""tzcheck.py, the download on /tz-2026/: each probe on fake tools and fake data."""
import importlib.resources
import importlib.util
import os
import pathlib
import stat
import struct
import zipfile

import pytest

SRC = pathlib.Path(__file__).resolve().parent.parent / "site" / "static" / "tzcheck.py"
spec = importlib.util.spec_from_file_location("tzcheck", SRC)
tc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tc)

TZDATA = importlib.resources.files("tzdata.zoneinfo")  # 2026f in this env (test checks)


def tzif(zone):
    return TZDATA.joinpath(*zone.split("/")).read_bytes()


def write_zones(d, zones=tc.ZONES, swap_havana_for=None):
    for z in zones:
        p = d / z
        p.parent.mkdir(parents=True, exist_ok=True)
        data = tzif(swap_havana_for) if (z == "America/Havana" and swap_havana_for) else tzif(z)
        p.write_bytes(data)


def shim(bindir, name, body):
    p = bindir / name
    p.write_text("#!/bin/sh\n" + body + "\n")
    p.chmod(p.stat().st_mode | stat.S_IEXEC)


@pytest.fixture
def path_only(tmp_path, monkeypatch):
    b = tmp_path / "bin"
    b.mkdir()
    monkeypatch.setenv("PATH", str(b))
    return b


def test_bundled_tzdata_is_2026f():
    first = TZDATA.joinpath("tzdata.zi").read_text().split("\n", 1)[0]
    assert "2026f" in first or "2026g" in first or "2027" in first


@pytest.mark.parametrize("v,wrong", [
    ("2026b", tc.ZONES), ("2026c", ["America/Inuvik", "America/Winnipeg", "America/Havana"]), ("2026d", ["America/Winnipeg", "America/Havana"]), ("2026e", ["America/Havana"]),
    ("2026f", []), ("2027a", []), ("junk", None), (None, None),
])
def test_wrong_by_version(v, wrong):
    assert tc.wrong_by_version(v) == wrong


def test_verdict_words():
    assert tc.verdict([]) == "all right"
    assert tc.verdict(None) == "can't tell"
    assert tc.verdict(["America/Havana"]) == "WRONG: Havana"


def test_offsets_right_on_good_data_and_wrong_on_old(tmp_path):
    good = tmp_path / "good"
    write_zones(good)
    assert tc.wrong_by_offsets(tc.tzif_offsets(tc.dir_reader(str(good)))) == []
    old = tmp_path / "old"  # Havana replaced by a zone that's UTC-5 in November
    write_zones(old, swap_havana_for="America/New_York")
    assert tc.wrong_by_offsets(tc.tzif_offsets(tc.dir_reader(str(old)))) == ["America/Havana"]


def test_missing_zone_counts_as_wrong(tmp_path):
    write_zones(tmp_path, zones=tc.ZONES[:-1])
    assert tc.wrong_by_offsets(tc.tzif_offsets(tc.dir_reader(str(tmp_path)))) == ["America/Havana"]


def test_dir_version(tmp_path):
    (tmp_path / "tzdata.zi").write_text("# version 2026e\n# redo\n")
    assert tc.dir_version(str(tmp_path)) == "2026e"


def test_java_tzdb_version(tmp_path):
    def utf(s):
        return struct.pack(">H", len(s)) + s.encode()
    p = tmp_path / "tzdb.dat"
    p.write_bytes(b"\x01" + utf("TZDB") + struct.pack(">H", 1) + utf("2026e") + b"\x00" * 20)
    assert tc.java_tzdb_version(str(p)) == "2026e"
    p.write_bytes(b"\x02junk")
    assert tc.java_tzdb_version(str(p)) is None


def test_probe_java_on_fake_jdk(tmp_path, path_only):
    home = tmp_path / "jdk"
    (home / "lib").mkdir(parents=True)
    utf = lambda s: struct.pack(">H", len(s)) + s.encode()  # noqa: E731
    (home / "lib" / "tzdb.dat").write_bytes(b"\x01" + utf("TZDB") + struct.pack(">H", 1) + utf("2026e"))
    shim(path_only, "java", f'echo "    java.home = {home}" >&2; echo \'openjdk version "21.0.13"\' >&2')
    [(label, v, verd)] = tc.probe_java()
    assert "21.0.13" in label and v == "2026e" and verd == "WRONG: Havana"


@pytest.mark.parametrize("raw,name", [("2026.6", "2026f"), ("2026.5", "2026e"), ("0.system", "system")])
def test_php_tz_name(raw, name):
    assert tc.php_tz_name(raw) == name


def test_probe_php_on_fake_php(path_only):
    out = '{"v":"8.4.27","tz":"2026.5","out":{"America/Edmonton":-6,"America/Yellowknife":-6,"America/Inuvik":-6,"America/Winnipeg":-5,"America/Havana":-5}}'
    shim(path_only, "php", f"echo '{out}'")
    assert tc.probe_php() == [("php 8.4.27", "2026e", "WRONG: Havana")]


def test_probe_go_on_fake_goroot(tmp_path, path_only):
    root = tmp_path / "go"
    (root / "lib" / "time").mkdir(parents=True)
    (root / "lib" / "time" / "update.bash").write_text("CODE=2026c\nDATA=2026c\n")
    with zipfile.ZipFile(root / "lib" / "time" / "zoneinfo.zip", "w") as z:
        for zone in tc.ZONES:
            z.writestr(zone, tzif(zone))
    shim(path_only, "go", f'case "$2" in GOROOT) echo {root};; GOVERSION) echo go1.27.4;; esac')
    [(label, v, verd)] = tc.probe_go()
    assert label.startswith("go1.27.4") and v == "2026c" and verd == "all right"


def test_probe_ruby(path_only):
    shim(path_only, "ruby", "echo 2026b")
    assert tc.probe_ruby()[0][1:] == ("2026b", "WRONG: Edmonton, Yellowknife, Inuvik, Winnipeg, Havana")
    shim(path_only, "ruby", "echo none")
    assert tc.probe_ruby()[0][2] == "can't tell"


def test_probe_postgres_own_dir(tmp_path, path_only):
    write_zones(tmp_path / "share" / "timezone", swap_havana_for="America/New_York")
    shim(path_only, "pg_config", f"echo {tmp_path / 'share'}")
    [(label, v, verd)] = tc.probe_postgres()
    assert verd == "WRONG: Havana"


def test_absent_tools_give_no_rows(path_only):
    for p in (tc.probe_node, tc.probe_java, tc.probe_php, tc.probe_go, tc.probe_ruby, tc.probe_postgres):
        assert p() == []


def test_main_runs_and_exit_code_matches(capsys):
    rc = tc.main()
    out = capsys.readouterr().out
    assert "Havana -4" in out and "Inuvik" in out
    assert rc == (1 if "WRONG" in out else 0)


def test_no_network_imports():
    text = SRC.read_text()
    for bad in ("urllib", "socket", "http.client", "requests"):
        assert bad not in text


def test_go_2026c_zip_gets_yellowknife_right(tmp_path):
    """2026-11-12: Yellowknife is a link to Edmonton, so 2026c data already has it right; 2026d fixed Inuvik.
    Real 2026c data (PyPI tzdata 2026.3, Go 1.27.4's zip) gave Yellowknife -6, Inuvik -7."""
    assert tc.wrong_by_version("2026c") == ["America/Inuvik", "America/Winnipeg", "America/Havana"]


def test_tzcheck_script_is_served_and_linked(tmp_path):
    """2026-11-12: /tz-2026/ links a runnable checker; the built site must serve the same file it links.
    Lives here, not at the end of test_site.py, so it can't collide with a parent's test appended there."""
    repo = SRC.resolve().parents[2]
    spec_b = importlib.util.spec_from_file_location("chris_site_build_tz", repo / "site" / "build.py")
    sb = importlib.util.module_from_spec(spec_b)
    spec_b.loader.exec_module(sb)
    out = sb.build(repo, tmp_path / "out")
    assert (out / "tzcheck.py").read_bytes() == SRC.read_bytes()
    assert 'href="/tzcheck.py"' in (out / "tz-2026" / "index.html").read_text()


# 2026-11-13: DuckDB carries its own copy in its ICU extension (1.4.5 all wrong, 1.5.6 2026d, 2.0.0 2026e, ran each).
DUCK_200 = "America/Edmonton,-360\nAmerica/Yellowknife,-360\nAmerica/Inuvik,-360\nAmerica/Winnipeg,-300\nAmerica/Havana,-300\n"


def test_duckdb_offsets_parses_csv_and_quotes():
    offs = tc.duckdb_offsets('V=2.0.0\n"America/Havana,-240"\nAmerica/Winnipeg,-300\njunk,1\n')
    assert offs["America/Havana"] == -4 and offs["America/Winnipeg"] == -5
    assert offs["America/Edmonton"] is None  # missing counts as wrong, not right
    assert tc.wrong_by_offsets(tc.duckdb_offsets(DUCK_200)) == ["America/Havana"]


def test_duckdb_sql_names_all_five_zones():
    for z in tc.ZONES:
        assert f"('{z}')" in tc.DUCKDB_SQL


def test_probe_duckdb_python_and_cli(path_only, monkeypatch):
    body = "printf '" + DUCK_200.replace("\n", "\\n") + "'"
    shim(path_only, "fakepy", "echo V=2.0.0; " + body)
    monkeypatch.setattr(tc.sys, "executable", str(path_only / "fakepy"))
    shim(path_only, "duckdb", "printf 'America/Edmonton,-420\\nAmerica/Yellowknife,-420\\nAmerica/Inuvik,-420\\nAmerica/Winnipeg,-360\\nAmerica/Havana,-300\\n'")
    rows = tc.probe_duckdb()
    assert rows[0] == ("duckdb (python package 2.0.0)", "?", "WRONG: Havana")
    assert rows[1][2] == "WRONG: Edmonton, Yellowknife, Inuvik, Winnipeg, Havana"


def test_probe_duckdb_absent(path_only, monkeypatch):
    shim(path_only, "fakepy", "echo 'ModuleNotFoundError: duckdb'")
    monkeypatch.setattr(tc.sys, "executable", str(path_only / "fakepy"))
    assert tc.probe_duckdb() == []
