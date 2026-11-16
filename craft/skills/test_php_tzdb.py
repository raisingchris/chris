import importlib.resources
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import php_tzdb as pt  # noqa: E402


def php2_blob(key):
    """A PHP2-shaped blob: timelib header bytes, then the real TZif v2 section."""
    parts = key.split("/")
    raw = importlib.resources.files("tzdata.zoneinfo").joinpath(*parts).read_bytes()
    v2 = raw.find(b"TZif", 4)
    return b"PHP2" + b"\x01" + b"CA" + b"\0" * 44 + raw[v2:]


def header(zones, version="2099.9"):
    data, idx, off = b"", [], 0
    for z in zones:
        b = php2_blob(z)
        idx.append('\t{ (char*) "%s" , 0x%06X },' % (z, off))
        data += b
        off += len(b)
    hexes = ", ".join("0x%02X" % c for c in data)
    return (
        "const timelib_tzdb_index_entry timezonedb_idx_builtin[%d] = {\n%s\n};\n"
        "const unsigned char timelib_timezone_db_data_builtin[%d] = {\n%s\n};\n"
        'const timelib_tzdb timezonedb_builtin = { "%s", %d, timezonedb_idx_builtin, '
        "timelib_timezone_db_data_builtin };\n"
        % (len(zones), "\n".join(idx), len(data), hexes, version, len(zones))
    )


def test_decodes_offsets_and_version(tmp_path):
    f = tmp_path / "timezonedb.h"
    f.write_text(header(["Europe/London", "Asia/Tokyo"]))
    out = pt.main([str(f), "--zone", "Asia/Tokyo", "--zone", "Europe/London",
                   "--zone", "Nowhere/Else", "--at", "2026-07-01T12:00Z"])
    assert out[0] == "array 0: version 2099.9, 2 zones"
    assert "  Asia/Tokyo 21:00 +0900" in out
    assert "  Europe/London 13:00 +0100" in out
    assert "  Nowhere/Else missing" in out


def test_last_blob_runs_to_end_of_array(tmp_path):
    f = tmp_path / "timezonedb.h"
    f.write_text(header(["Asia/Tokyo", "Europe/London"]))
    (_, blobs), = list(pt.arrays(f.read_text()))
    assert blobs["Europe/London"].startswith(b"PHP2")
    assert pt.zone(blobs["Europe/London"], "Europe/London").key == "Europe/London"
