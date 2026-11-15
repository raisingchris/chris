import os
import struct
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
import icu_dat  # noqa: E402


def make_dat(entries):
    """Build a tiny ICU common-data package: 32-byte header, TOC, names, then data."""
    hs = 32
    header = struct.pack("<H", hs) + b"\xda\x27" + b"\0" * (hs - 4)
    n = len(entries)
    toc_len = 4 + 8 * n
    names = b""
    name_offs = []
    for name, _ in entries:
        name_offs.append(toc_len + len(names))
        names += name.encode() + b"\0"
    data = b""
    data_offs = []
    for _, d in entries:
        data_offs.append(toc_len + len(names) + len(data))
        data += d
    toc = struct.pack("<I", n) + b"".join(struct.pack("<II", a, b) for a, b in zip(name_offs, data_offs))
    return header + toc + names + data


def test_list_and_extract(tmp_path):
    b = make_dat([("icudt76l/a.res", b"AAA"), ("icudt76l/zoneinfo64.res", b"ZZZZ"),
                  ("icudt76l/metaZones.res", b"MM")])
    assert icu_dat.list_dat(b)["icudt76l/a.res"] == b"AAA"
    got = icu_dat.extract_zone_files(b, str(tmp_path))
    assert sorted(got) == ["icudt76l/metaZones.res", "icudt76l/zoneinfo64.res"]
    assert (tmp_path / "zoneinfo64.res").read_bytes() == b"ZZZZ"
    assert not (tmp_path / "a.res").exists()


def test_hex_input(tmp_path):
    raw = make_dat([("x/zoneinfo64.res", b"\x01\x02")])
    half = len(raw) // 2
    for i, part in enumerate((raw[:half], raw[half:])):
        (tmp_path / f"d{i}.h").write_text("#define X \\\n" + ", ".join(f"0x{c:02X}" for c in part))
    assert icu_dat.hex_to_bytes([str(tmp_path / "d0.h"), str(tmp_path / "d1.h")]) == raw


def test_rejects_non_icu():
    with pytest.raises(ValueError):
        icu_dat.list_dat(b"\x20\x00\x00\x00" + b"\0" * 40)
