"""Which time zone data does a shipped ICU build really use? Load its own .so files and ask it.

Some packages ship ICU as three shared libraries (libicudata, libicuuc, libicui18n), e.g. .NET's
app-local ICU NuGet package `Microsoft.ICU.ICU4C.Runtime.linux-x64`. Unlike icu_dat.py (data run
through this machine's ICU), this runs the package's own code and data: it dlopens the three files
by path, in order, with RTLD_GLOBAL, and calls the versioned C API (`ucal_getTZDataVersion_72`...).

    python3 icu_so.py DIR VERSION [--at 2026-11-15T12:00Z] [ZONE ...]

VERSION is the file suffix, e.g. 72.1.0.3 for libicuuc.so.72.1.0.3; the symbol suffix is its first
part. Only for Linux builds of the same CPU as this machine. Downloaded libraries are untrusted
code: run this from a scratch directory with `python3 -I`, and only on packages from a real
publisher's feed (here NuGet, signed by Microsoft).
"""
import argparse
import calendar
import ctypes
import datetime as dt

DEFAULT_ZONES = ["America/Vancouver", "America/Edmonton", "America/Yellowknife", "America/Inuvik",
                 "America/Winnipeg", "America/Havana", "Africa/Casablanca", "Africa/El_Aaiun",
                 "America/New_York"]
UCAL_GREGORIAN, UCAL_ZONE_OFFSET, UCAL_DST_OFFSET = 1, 15, 16


def symbol_suffix(version):
    return version.split(".")[0]


def utf16z(s):
    return (s + "\0").encode("utf-16-le")


def epoch_ms(at):
    t = dt.datetime.strptime(at, "%Y-%m-%dT%H:%MZ")
    return calendar.timegm(t.timetuple()) * 1000.0


def load(d, version):
    for lib in ("data", "uc", "i18n"):
        ctypes.CDLL(f"{d}/libicu{lib}.so.{version}", mode=ctypes.RTLD_GLOBAL)
    return ctypes.CDLL(f"{d}/libicui18n.so.{version}")


def offsets(i18n, version, zones, ms):
    s = symbol_suffix(version)
    err = ctypes.c_int(0)
    ver = getattr(i18n, f"ucal_getTZDataVersion_{s}")
    ver.restype = ctypes.c_char_p
    tzver = ver(ctypes.byref(err)).decode()
    uo = getattr(i18n, f"ucal_open_{s}")
    uo.restype = ctypes.c_void_p
    uo.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int,
                   ctypes.POINTER(ctypes.c_int)]
    st = getattr(i18n, f"ucal_setMillis_{s}")
    st.argtypes = [ctypes.c_void_p, ctypes.c_double, ctypes.POINTER(ctypes.c_int)]
    gt = getattr(i18n, f"ucal_get_{s}")
    gt.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
    cl = getattr(i18n, f"ucal_close_{s}")
    cl.argtypes = [ctypes.c_void_p]
    out = {}
    for z in zones:
        e = ctypes.c_int(0)
        buf = ctypes.create_string_buffer(utf16z(z))
        c = uo(buf.raw, -1, b"en_US", UCAL_GREGORIAN, ctypes.byref(e))
        st(c, ms, ctypes.byref(e))
        off = gt(c, UCAL_ZONE_OFFSET, ctypes.byref(e)) + gt(c, UCAL_DST_OFFSET, ctypes.byref(e))
        cl(c)
        out[z] = (off / 3600000, e.value)
    return tzver, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("version")
    ap.add_argument("--at", default="2026-11-15T12:00Z")
    ap.add_argument("zones", nargs="*")
    a = ap.parse_args()
    tzver, out = offsets(load(a.dir, a.version), a.version, a.zones or DEFAULT_ZONES, epoch_ms(a.at))
    print(f"tz data version (from the package's own ICU): {tzver}   at {a.at}")
    for z, (h, e) in out.items():
        print(f"  {z:22} UTC{h:+.1f}" + (f"  (ICU error {e})" if e > 0 else ""))


if __name__ == "__main__":
    main()
