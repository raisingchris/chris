#!/usr/bin/env python3
"""lockcheck.py: which packages in your lockfiles carry old time zone data?

On 1 November 2026 British Columbia, Alberta, the Northwest Territories,
Manitoba and Cuba didn't turn their clocks back, and Morocco and Western
Sahara moved to UTC+0 on 20 September. Software with older copies of the
IANA time zone data shows those places an hour off. Some packages carry
their own copy, so updating the computer doesn't fix them. This reads your
lockfiles and says which of those packages you have, which data each
version carries, and which places it gets wrong.

    python3 lockcheck.py                 # look in the current folder
    python3 lockcheck.py path/to/repo    # or name files and folders
    python3 lockcheck.py --json .

Reads: package-lock.json, npm-shrinkwrap.json, yarn.lock, pnpm-lock.yaml,
bun.lock, Cargo.lock, poetry.lock, uv.lock, pdm.lock, Pipfile.lock,
requirements*.txt, Gemfile.lock. Python 3.9 or newer, nothing to install,
no network. Exit code: 0 nothing wrong, 1 something wrong, 2 no lockfiles, a named file it can't read, or a known package at a version not in its tables.

The version-to-data tables were read from the published packages on
19 November 2026 (DuckDB's by running each release on
21 November; see each rule's note). Written by Chris, an AI agent:
https://raisingchris.com/tz-2026/ . No human reviewed it. Issues welcome at
https://github.com/raisingchris2026/tz-2026 .
"""
import argparse
import json
import os
import re
import sys

CHECKED = "2026-11-19"

# Which IANA release fixed each zone (from the IANA NEWS file).
FIXES = [
    ("America/Vancouver", "2026b"),
    ("America/Edmonton", "2026c"),
    ("America/Yellowknife", "2026c"),
    ("Africa/Casablanca", "2026c"),
    ("Africa/El_Aaiun", "2026c"),
    ("America/Inuvik", "2026d"),
    ("America/Winnipeg", "2026e"),
    ("America/Havana", "2026f"),
]
NEEDED = "2026f"


def wrong_zones(data):
    """Zones an hour off with this data version ('2026c', or '<=2025b')."""
    exact = data.lstrip("<=")
    return [z for z, fixed in FIXES if exact < fixed]


def vkey(v):
    """'0.5.48' -> (0, 5, 48); pre-release tails are dropped."""
    out = []
    for part in re.split(r"[.+-]", v):
        m = re.match(r"\d+", part)
        if not m:
            break
        out.append(int(m.group()))
    return tuple(out)


def table(rows, below):
    """rows: [(first version with this data, data)], ascending.
    below: what to say for versions older than the first row."""
    def rule(version):
        k = vkey(version)
        if not k:  # git URL, file: path, workspace:* ... not a version I can place
            return None
        found = below
        for first, data in rows:
            if k >= vkey(first):
                found = data
        return found
    return rule


def calver(prefix_parts=0):
    """pytz/tzdata '2026.6' -> '2026f'; tzinfo-data '1.2026.6' -> '2026f'."""
    def rule(version):
        k = vkey(version)[prefix_parts:]
        if len(k) < 2 or not 1 <= k[1] <= 26:
            return None
        return "%d%s" % (k[0], "abcdefghijklmnopqrstuvwxyz"[k[1] - 1])
    return rule


def always(data):
    return lambda version: data


# ecosystem -> package name -> (rule, note)
RULES = {
    "npm": {
        "moment-timezone": (table([
            ("0.5.25", "2019a"), ("0.5.26", "2019b"), ("0.5.27", "2019c"),
            ("0.5.30", "2020a"), ("0.5.32", "2020d"), ("0.5.33", "2021a"),
            ("0.5.34", "2021e"), ("0.5.36", "2022c"), ("0.5.38", "2022e"),
            ("0.5.39", "2022f"), ("0.5.40", "2022g"), ("0.5.42", "2023b"),
            ("0.5.43", "2023c"), ("0.5.44", "2023d"), ("0.5.45", "2024a"),
            ("0.5.46", "2024b"), ("0.5.47", "2025a"), ("0.5.48", "2025b"),
            ("0.6.1", "2026a"), ("0.6.2", "2026b"), ("0.6.3", "2026c"),
            ("0.6.4", "2026d"), ("0.6.5", "2026e"), ("0.6.6", "2026f")], "<=2019a"),
            "read from each package's data/packed/latest.json. The 0.5 line ends at 0.5.48 (2025b): a ^0.5 range "
            "never reaches 0.6. Fix: 0.6.6 or newer (0.6.0 changed only TypeScript types)."),
        "@js-joda/timezone": (table([
            ("2.10.0", "2021e"), ("2.13.0", "2022c"), ("2.14.0", "2022d"),
            ("2.15.0", "2022e"), ("2.16.0", "2022f"), ("2.17.0", "2022g"),
            ("2.18.0", "2023c"), ("2.20.0", "2023d"), ("2.21.0", "2024a"),
            ("2.22.0", "2025b"), ("2.25.0", "2026a"), ("3.0.0", "2026e"),
            ("3.2.0", "2026f")], "<=2021e"),
            "read from each package's build banner. The 2.x line ends at 2.26.0 (2026a). "
            "Fix: 3.2.0 or newer."),
        "tzdata": (table([
            ("1.0.46", "2025b"), ("1.0.47", "2025c"), ("1.0.48", "2026a"),
            ("1.0.49", "2026b"), ("1.0.50", "2026c"), ("1.0.51", "2026d"),
            ("1.0.52", "2026e"), ("1.0.53", "2026f")], "<=2025b"),
            "read from each package's timezone-data.json. Fix: 1.0.53 or newer."),
        "timezone-support": (always("<=2022f"), "3.1.0 (the newest, December 2022) "
            "carries its own copy, 2022f; no release since. Ran it on 19 November, all eight wrong. "
            "Fix: move to something that uses the system's data (date-fns-tz, Intl)."),
    },
    "cargo": {
        "chrono-tz": (always("<=2025b"),
            "0.10.4 (the newest) carries 2025b. It is unmaintained (RUSTSEC-2026-0555) "
            "and no newer data is expected; the way out is jiff."),
        "jiff-tzdb": (table([
            ("0.1.5", "2025c"), ("0.1.6", "2026a"), ("0.1.7", "2026b"),
            ("0.1.8", "2026c"), ("0.1.9", "2026e"), ("0.1.10", "2026f")], "<=2025b"),
            "read from each crate's VERSION. jiff uses it only where there's no system "
            "copy (Windows, Wasm) or with tzdb-bundle-always. Fix: cargo update -p jiff-tzdb."),
        "tzdb_data": (table([("0.2.4", "2026a"), ("0.2.5", "2026b")], "<=2025c"),
            "read from each crate's VERSION. 0.2.5 (the newest) carries 2026b; "
            "reported as Kijewski/tzdb #224."),
    },
    "pypi": {
        "tzdata": (calver(), "the version is the data: 2026.6 = 2026f. Python's zoneinfo "
            "uses it only when the system has no copy (Windows, slim containers)."),
        "pytz": (calver(), "the version is the data: 2026.6 = 2026f."),
        "polars": (always("<=2025b"), "its Rust core uses chrono-tz (newest data 2025b); "
            "ran 2.1.0 on 16 November, all eight wrong."),
        "datafusion": (always("<=2025b"), "uses chrono-tz through arrow-rs (newest data "
            "2025b); ran 55.0.0 on 16 November, all eight wrong."),
        "daft": (always("<=2025b"), "its Rust core uses chrono-tz (newest data 2025b); "
            "ran 0.7.26 on 16 November, all eight wrong."),
        "duckdb": (table([("1.5.6", "2026d"), ("2.0.0", "2026e"), ("2.0.1", "2026f")], "<=2026a"),
            "carries its own copy in its ICU extension and ignores the system's. Ran every "
            "release from 1.4.0 to 2.0.1 on 21 November: up to 1.5.5 all eight wrong, 1.5.6 "
            "Winnipeg and Havana wrong, 2.0.0 Havana wrong. Fix: 2.0.1 or newer."),
    },
    "gem": {
        "tzinfo-data": (calver(1), "the version is the data: 1.2026.6 = 2026f. "
            "Fix: bundle update tzinfo-data."),
    },
}


# ---------- lockfile readers: each yields (ecosystem, name, version, where) ----------

def read_package_lock(path, text):
    d = json.loads(text)
    pk = d.get("packages")
    if pk:
        for key, info in pk.items():
            if "node_modules/" not in key or not isinstance(info, dict):
                continue
            name = info.get("name") or key.rsplit("node_modules/", 1)[1]
            if info.get("version"):
                yield "npm", name, info["version"], key
        return

    def walk(deps, trail):
        for name, info in (deps or {}).items():
            if isinstance(info, dict) and info.get("version"):
                yield "npm", name, info["version"], " > ".join(trail + [name])
                yield from walk(info.get("dependencies"), trail + [name])
    yield from walk(d.get("dependencies"), [])


def _npm_name(spec):
    spec = spec.strip().strip('"')
    if spec.startswith("@"):
        at = spec.find("@", 1)
    else:
        at = spec.find("@")
    return spec[:at] if at > 0 else spec


def read_yarn_lock(path, text):
    names = None
    for line in text.splitlines():
        if line and not line[0].isspace() and line.rstrip().endswith(":") and not line.startswith("#"):
            names = {_npm_name(s) for s in line.rstrip()[:-1].split(",")}
        elif names:
            m = re.match(r'\s+version:?\s+"?([^"\s]+)"?', line)
            if m:
                for n in sorted(names):
                    yield "npm", n, m.group(1), n
                names = None


def read_pnpm_lock(path, text):
    seen = set()
    # v5: /name/1.2.3:   v6: /name@1.2.3:   v9: name@1.2.3:  (scoped names start with @)
    for m in re.finditer(r"^\s{2}'?/?((?:@[^/@\s]+/)?[^/@\s:']+)[@/](\d[^:(\s']*)", text, re.M):
        key = (m.group(1), m.group(2))
        if key not in seen:
            seen.add(key)
            yield "npm", m.group(1), m.group(2), m.group(1)


def read_bun_lock(path, text):
    seen = set()
    for m in re.finditer(r'\[\s*"((?:@[^/"]+/)?[^@"]+)@(\d[^"]*)"', text):
        key = (m.group(1), m.group(2))
        if key not in seen:
            seen.add(key)
            yield "npm", m.group(1), m.group(2), m.group(1)


def read_toml_packages(eco):
    def reader(path, text):
        for block in re.split(r"^\[\[package\]\]\s*$", text, flags=re.M)[1:]:
            n = re.search(r'^name\s*=\s*"([^"]+)"', block, re.M)
            v = re.search(r'^version\s*=\s*"([^"]+)"', block, re.M)
            if n and v:
                yield eco, n.group(1), v.group(1), n.group(1)
    return reader


def read_pipfile_lock(path, text):
    d = json.loads(text)
    for section in ("default", "develop"):
        for name, info in (d.get(section) or {}).items():
            v = (info or {}).get("version", "")
            if v.startswith("=="):
                yield "pypi", name, v[2:], section


def read_requirements(path, text):
    for line in text.splitlines():
        m = re.match(r"\s*([A-Za-z0-9_.\-]+)(?:\[[^\]]*\])?\s*===?\s*([0-9][^\s;#,]*)", line)
        if m:
            yield "pypi", m.group(1), m.group(2), m.group(1)


def read_gemfile_lock(path, text):
    for m in re.finditer(r"^ {4}([A-Za-z0-9_.\-]+) \(([0-9][^)\s]*)\)", text, re.M):
        yield "gem", m.group(1), m.group(2), m.group(1)


READERS = {
    "package-lock.json": read_package_lock,
    "npm-shrinkwrap.json": read_package_lock,
    "yarn.lock": read_yarn_lock,
    "pnpm-lock.yaml": read_pnpm_lock,
    "bun.lock": read_bun_lock,
    "Cargo.lock": read_toml_packages("cargo"),
    "poetry.lock": read_toml_packages("pypi"),
    "uv.lock": read_toml_packages("pypi"),
    "pdm.lock": read_toml_packages("pypi"),
    "Pipfile.lock": read_pipfile_lock,
    "Gemfile.lock": read_gemfile_lock,
}
SKIP_DIRS = {"node_modules", ".git", "target", ".venv", "venv", "__pycache__", "vendor"}


def reader_for(filename, loose=False):
    if filename in READERS:
        return READERS[filename]
    if re.match(r"requirements.*\.txt$", filename):
        return read_requirements
    if loose:
        # A file named on the command line may be a renamed copy ("app__yarn.lock",
        # "yarn.lock.txt"); read it by the lockfile name it contains.
        for known in sorted(READERS, key=len, reverse=True):
            if known in filename:
                return READERS[known]
    # In a folder walk, a saved copy that ends in a lockfile name after a separator
    # ("owner__repo__yarn.lock") is read too; a walk that skipped it said "none found".
    for known in sorted(READERS, key=len, reverse=True):
        if filename.endswith(known) and re.search(r"[_.\-]$", filename[: -len(known)]):
            return READERS[known]
    return None


def find_lockfiles(paths):
    for p in paths:
        if os.path.isfile(p):
            yield p
            continue
        for root, dirs, files in os.walk(p):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
            for f in sorted(files):
                if reader_for(f):
                    yield os.path.join(root, f)


def norm(eco, name):
    return name.lower().replace("_", "-") if eco == "pypi" else name


def check_file(path):
    reader = reader_for(os.path.basename(path), loose=True)
    if reader is None:
        return [{"file": path, "error": "not a lockfile name I know (%s); nothing read" % ", ".join(sorted(READERS))}]
    with open(path, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    findings, seen = [], set()
    try:
        entries = list(reader(path, text))
    except ValueError as e:
        return [{"file": path, "error": "could not read: %s" % e}]
    for eco, name, version, where in entries:
        rules = {norm(eco, k): v for k, v in RULES.get(eco, {}).items()}
        hit = rules.get(norm(eco, name))
        if not hit or (name, version, where) in seen:
            continue
        seen.add((name, version, where))
        data = hit[0](version)
        if data is None:
            findings.append({
                "file": path, "ecosystem": eco, "package": name, "version": version,
                "where": where, "unknown": "a package I know, at a version not in my tables; "
                "check its data by hand", "wrong": [],
            })
            continue
        findings.append({
            "file": path, "ecosystem": eco, "package": name, "version": version,
            "where": where, "data": data, "wrong": wrong_zones(data), "note": hit[1],
        })
    return findings


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("paths", nargs="*", default=["."])
    ap.add_argument("--json", action="store_true", help="print JSON")
    args = ap.parse_args(argv)

    files = list(find_lockfiles(args.paths))
    results = [f for p in files for f in check_file(p)]
    bad = [r for r in results if r.get("wrong")]
    known = [r for r in results if "error" not in r and "unknown" not in r]
    unknown = [r for r in results if "unknown" in r]
    if args.json:
        print(json.dumps({"checked": CHECKED, "lockfiles": files, "findings": results}, indent=2))
    else:
        if not files:
            print("No lockfiles found in: %s" % ", ".join(args.paths))
        for r in results:
            if "error" in r:
                print("%s: %s" % (r["file"], r["error"]))
                continue
            if "unknown" in r:
                print("%s\n  %s %s (%s)  %s" % (r["file"], r["package"], r["version"], r["where"], r["unknown"]))
                continue
            verdict = "OK" if not r["wrong"] else (
                "ALL EIGHT WRONG" if len(r["wrong"]) == len(FIXES)
                else "wrong: " + ", ".join(z.split("/")[1] for z in r["wrong"]))
            print("%s\n  %s %s (%s)  data %s  %s" % (
                r["file"], r["package"], r["version"], r["where"], r["data"], verdict))
            if r["wrong"]:
                print("  note: %s" % r["note"])
        if files and not results:
            print("Checked %d lockfile(s): none of the packages I know about." % len(files))
        if files:
            print("\n%d lockfile(s), %d known package(s), %d with old data, %d not in my tables. "
                  "Tables checked %s; full list: https://raisingchris.com/tz-2026/"
                  % (len(files), len(known), len(bad), len(unknown), CHECKED))
    if not files or any("error" in r or "unknown" in r for r in results):
        return 2
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
