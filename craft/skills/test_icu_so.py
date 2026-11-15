import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
import icu_so  # noqa: E402

SYS = "/usr/lib/x86_64-linux-gnu"
HAVE_76 = os.path.exists(f"{SYS}/libicui18n.so.76.1")


def test_helpers():
    assert icu_so.symbol_suffix("72.1.0.3") == "72"
    assert icu_so.utf16z("A") == b"A\0\0\0"
    assert icu_so.epoch_ms("1970-01-02T00:00Z") == 86400000.0


@pytest.mark.skipif(not HAVE_76, reason="needs this machine's ICU 76.1")
def test_runs_system_icu_in_subprocess():
    # A fresh process, so this test's ctypes loads can't leak into others.
    out = subprocess.run([sys.executable, "-I", icu_so.__file__, SYS, "76.1",
                          "--at", "2026-01-15T12:00Z", "America/New_York", "Asia/Tokyo"],
                         capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    assert "tz data version" in out.stdout
    assert "America/New_York       [redacted].0" in out.stdout
    assert "Asia/Tokyo             [redacted].0" in out.stdout
