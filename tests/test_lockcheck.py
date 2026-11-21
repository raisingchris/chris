"""lockcheck.py, the lockfile scanner on /tz-2026/: each reader on a small real-shaped file."""
import importlib.util
import json
import pathlib

SRC = pathlib.Path(__file__).resolve().parent.parent / "site" / "static" / "lockcheck.py"
spec = importlib.util.spec_from_file_location("lockcheck", SRC)
lc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lc)


def run(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text)
    return {(r["package"], r["version"]): r for r in lc.check_file(str(p))}


def test_wrong_zones_by_release():
    assert len(lc.wrong_zones("<=2025b")) == 8
    assert lc.wrong_zones("2026b") == [z for z, _ in lc.FIXES[1:]]
    assert lc.wrong_zones("2026c") == ["America/Inuvik", "America/Winnipeg", "America/Havana"]
    assert lc.wrong_zones("2026e") == ["America/Havana"]
    assert lc.wrong_zones("2026f") == []
    assert lc.wrong_zones("2027a") == []


def test_tables_match_what_was_read():
    mtz = lc.RULES["npm"]["moment-timezone"][0]
    assert mtz("0.5.37") == "2022c"  # wazuh-dashboard's pin
    assert mtz("0.5.43") == "2023c"  # sequelize v6 yarn.lock
    assert mtz("0.5.48") == "2025b" and mtz("0.6.0") == "2025b"
    assert mtz("0.6.5") == "2026e" and mtz("0.6.6") == "2026f" and mtz("0.7.0") == "2026f"
    jj = lc.RULES["npm"]["@js-joda/timezone"][0]
    assert jj("2.3.0") == "<=2021e" and jj("2.26.0") == "2026a" and jj("3.1.1") == "2026e" and jj("3.2.1") == "2026f"
    tz = lc.RULES["npm"]["tzdata"][0]
    assert tz("1.0.52") == "2026e" and tz("1.0.54") == "2026f"
    assert lc.RULES["npm"]["timezone-support"][0]("3.1.0") == "<=2022f"
    jt = lc.RULES["cargo"]["jiff-tzdb"][0]
    assert jt("0.1.9") == "2026e" and jt("0.1.10") == "2026f" and jt("1.0.0") == "2026f"
    assert lc.RULES["pypi"]["pytz"][0]("2026.6") == "2026f"
    assert lc.RULES["pypi"]["tzdata"][0]("2025.2") == "2025b"
    assert lc.RULES["gem"]["tzinfo-data"][0]("1.2026.5") == "2026e"
    # DuckDB: every release 1.4.0..2.0.1 run on 21 November 2026
    dk = lc.RULES["pypi"]["duckdb"][0]
    assert len(lc.wrong_zones(dk("1.4.5"))) == 8 and len(lc.wrong_zones(dk("1.5.5"))) == 8
    assert lc.wrong_zones(dk("1.5.6")) == ["America/Winnipeg", "America/Havana"]
    assert lc.wrong_zones(dk("2.0.0")) == ["America/Havana"] and lc.wrong_zones(dk("2.0.1")) == []


def test_package_lock_v3_nested(tmp_path):
    lock = {"lockfileVersion": 3, "packages": {
        "": {"name": "app"},
        "node_modules/moment-timezone": {"version": "0.6.6"},
        "node_modules/sequelize/node_modules/moment-timezone": {"version": "0.5.48"},
        "node_modules/@js-joda/timezone": {"version": "2.26.0"},
        "node_modules/left-pad": {"version": "1.3.0"},
    }}
    got = run(tmp_path, "package-lock.json", json.dumps(lock))
    assert got[("moment-timezone", "0.6.6")]["wrong"] == []
    nested = got[("moment-timezone", "0.5.48")]
    assert len(nested["wrong"]) == 8 and "sequelize" in nested["where"]
    assert got[("@js-joda/timezone", "2.26.0")]["data"] == "2026a"
    assert len(got) == 3


def test_package_lock_v1(tmp_path):
    lock = {"lockfileVersion": 1, "dependencies": {
        "sequelize": {"version": "6.37.8", "dependencies": {"moment-timezone": {"version": "0.5.45"}}}}}
    got = run(tmp_path, "package-lock.json", json.dumps(lock))
    assert got[("moment-timezone", "0.5.45")]["where"] == "sequelize > moment-timezone"


def test_yarn_v1_and_berry(tmp_path):
    v1 = ('"@js-joda/timezone@^3.2.0":\n  version "3.2.1"\n  resolved "x"\n\n'
          'moment-timezone@^0.5.27, moment-timezone@^0.5.31:\n  version "0.5.37"\n')
    got = run(tmp_path, "yarn.lock", v1)
    assert set(got) == {("@js-joda/timezone", "3.2.1"), ("moment-timezone", "0.5.37")}
    berry = '"moment-timezone@npm:^0.5.43":\n  version: 0.5.48\n  resolution: "x"\n'
    sub = tmp_path / "b"
    sub.mkdir()
    got = run(sub, "yarn.lock", berry)
    assert ("moment-timezone", "0.5.48") in got


def test_pnpm_v5_v6_v9(tmp_path):
    text = ("packages:\n\n  /moment-timezone/0.5.40:\n    resolution: x\n"
            "  /tzdata@1.0.51:\n    resolution: x\n"
            "  '@js-joda/timezone@3.2.1':\n    resolution: x\n"
            "snapshots:\n\n  '@js-joda/timezone@3.2.1':\n    dependencies: {}\n")
    got = run(tmp_path, "pnpm-lock.yaml", text)
    assert set(got) == {("moment-timezone", "0.5.40"), ("tzdata", "1.0.51"), ("@js-joda/timezone", "3.2.1")}
    assert got[("tzdata", "1.0.51")]["data"] == "2026d"


def test_bun_lock(tmp_path):
    text = '{\n  "packages": {\n    "moment-timezone": ["moment-timezone@0.6.5", "", {}, "sha"],\n  }\n}\n'
    got = run(tmp_path, "bun.lock", text)
    assert got[("moment-timezone", "0.6.5")]["wrong"] == ["America/Havana"]


def test_cargo_lock(tmp_path):
    text = ('version = 4\n\n[[package]]\nname = "chrono-tz"\nversion = "0.10.4"\n\n'
            '[[package]]\nname = "jiff-tzdb"\nversion = "0.1.9"\n\n'
            '[[package]]\nname = "tzdb_data"\nversion = "0.2.5"\n\n'
            '[[package]]\nname = "serde"\nversion = "1.0.0"\n')
    got = run(tmp_path, "Cargo.lock", text)
    assert len(got[("chrono-tz", "0.10.4")]["wrong"]) == 8
    assert got[("jiff-tzdb", "0.1.9")]["wrong"] == ["America/Havana"]
    assert "America/Vancouver" not in got[("tzdb_data", "0.2.5")]["wrong"]
    assert len(got) == 3


def test_python_locks(tmp_path):
    poetry = '[[package]]\nname = "pytz"\nversion = "2025.2"\n\n[[package]]\nname = "Polars"\nversion = "2.1.0"\n'
    got = run(tmp_path, "poetry.lock", poetry)
    assert got[("pytz", "2025.2")]["data"] == "2025b" and ("Polars", "2.1.0") in got
    pip = json.dumps({"default": {"tzdata": {"version": "==2026.6"}}, "develop": {}})
    assert run(tmp_path, "Pipfile.lock", pip)[("tzdata", "2026.6")]["wrong"] == []
    req = "tzdata==2026.4  # pinned\npytz>=2020\ndatafusion==55.0.0\n"
    got = run(tmp_path, "requirements-dev.txt", req)
    assert set(got) == {("tzdata", "2026.4"), ("datafusion", "55.0.0")}


def test_gemfile_lock(tmp_path):
    text = "GEM\n  specs:\n    tzinfo (2.0.6)\n    tzinfo-data (1.2024.1)\n      tzinfo (>= 1.0.0)\n"
    got = run(tmp_path, "Gemfile.lock", text)
    assert got == {("tzinfo-data", "1.2024.1"): got[("tzinfo-data", "1.2024.1")]}
    assert got[("tzinfo-data", "1.2024.1")]["data"] == "2024a"


def test_walk_skips_node_modules_and_exit_codes(tmp_path, capsys):
    (tmp_path / "node_modules" / "x").mkdir(parents=True)
    (tmp_path / "node_modules" / "x" / "yarn.lock").write_text('a@1:\n  version "1"\n')
    assert lc.main([str(tmp_path)]) == 2
    (tmp_path / "Cargo.lock").write_text('[[package]]\nname = "jiff-tzdb"\nversion = "1.0.0"\n')
    assert lc.main([str(tmp_path)]) == 0
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "Cargo.lock").write_text('[[package]]\nname = "chrono-tz"\nversion = "0.9.0"\n')
    capsys.readouterr()
    assert lc.main([str(tmp_path), "--json"]) == 1
    out = json.loads(capsys.readouterr().out)
    assert len(out["lockfiles"]) == 2
    assert [f["package"] for f in out["findings"] if f["wrong"]] == ["chrono-tz"]


def test_says_it_is_an_ai_and_no_network():
    text = SRC.read_text()
    assert "AI agent" in text and "raisingchris.com" in text
    for bad in ("urllib", "socket", "requests", "http.client", "subprocess"):
        assert "import " + bad not in text


def test_note_only_when_wrong(tmp_path, capsys):
    (tmp_path / "Cargo.lock").write_text('[[package]]\nname = "jiff-tzdb"\nversion = "1.0.0"\n'
                                         '\n[[package]]\nname = "chrono-tz"\nversion = "0.10.4"\n')
    lc.main([str(tmp_path)])
    out = capsys.readouterr().out
    assert out.count("note:") == 1 and "the way out is jiff" in out


def test_renamed_and_unknown_files_are_not_a_silent_all_clear(tmp_path, capsys):
    # 2026-11-20: saved copies named "app__yarn.lock" were skipped and the run said "0 with old data".
    berry = ('"moment-timezone@npm:^0.5.31, moment-timezone@npm:^0.5.34":\n'
             '  version: 0.5.43\n  resolution: "moment-timezone@npm:0.5.43"\n')
    (tmp_path / "calcom__yarn.lock").write_text(berry)
    assert lc.main([str(tmp_path / "calcom__yarn.lock")]) == 1
    assert "0.5.43" in capsys.readouterr().out
    (tmp_path / "notes.txt").write_text("moment-timezone 0.5.43\n")
    assert lc.main([str(tmp_path / "notes.txt")]) == 2
    out = capsys.readouterr().out
    assert "not a lockfile name I know" in out and "0 known package(s)" in out
