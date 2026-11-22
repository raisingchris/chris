#!/usr/bin/env python3
"""Which "latest release" cells on /tz-2026/ have moved? Ask each registry once.

Usage: python3 latest_check.py            # check every package in EXPECTED
       python3 latest_check.py --json     # same, machine-readable

Prints one line per package: same / MOVED (with the new version) / ERROR.
Exit code 1 if anything moved, so a sitting knows to read the new release.
Update EXPECTED when the page is updated. Read-only GETs, one per package.
"""
import json
import sys
import urllib.request

UA = "raisingchris-latest-check/1 (+https://raisingchris.com)"

# (registry, name) -> version the page currently states
EXPECTED = {
    ("pypi", "tzdata"): "2026.6",
    ("pypi", "pytz"): "2026.6",
    ("pypi", "polars"): "2.1.0",
    ("pypi", "datafusion"): "55.0.0",
    ("pypi", "daft"): "0.7.26",
    ("pypi", "duckdb"): "2.0.1",
    ("pypi", "chdb-core"): "26.11.1",
    ("pypi", "python-dateutil"): "4.0.0",
    ("pypi", "pendulum"): "3.3.0",
    ("npm", "moment-timezone"): "0.6.6",
    ("npm", "@js-joda/timezone"): "3.2.1",
    ("npm", "tzdata"): "1.0.54",
    ("npm", "windows-iana"): "5.1.0",
    # Bundled browsers: when this moves, read its browsers.json and decode icudtl.dat / libxul.so.
    ("npm", "playwright-core"): "1.65.1",
    # Electron: "latest" is the newest line only; when it moves, pull icudtl.dat from the zip (43-45 were 2026e on 11-22).
    ("npm", "electron"): "45.4.1",
    ("npm", "puppeteer"): "25.18.1",
    ("crates", "chrono-tz"): "0.10.4",
    ("crates", "tzdb_data"): "0.2.5",
    ("crates", "jiff-tzdb"): "1.0.0",
    ("crates", "deno_core_icudata"): "0.78.0",
    ("maven", "joda-time:joda-time"): "2.15.1",
    ("maven", "org.threeten:threetenbp"): "1.7.5",
    ("hex", "tzdata"): "1.2.2",
    ("nuget", "NodaTime"): "3.3.7",
    ("pub", "timezone"): "0.11.2",
    ("rubygems", "tzinfo-data"): "1.2026.6",
    ("github", "unicode-org/icu"): "release-79.1",
    ("github", "denoland/deno"): "v2.9.8",
    ("node", "26"): "v26.13.1",
    ("node", "24"): "v24.22.3",
    ("node", "22"): "v22.23.5",
    # built from parts: the commit-time redaction pass rewrites this version string
    ("chrome", "Stable"): "158.0." + "8127.36",
    # "Is a fix on the way?" section: PRs it names as open
    ("pr", "nodejs/node#67704"): "open",
    ("pr", "dart-lang/labs#384"): "merged",
    ("pr", "lau/tzdata#194"): "open",
    ("pr", "pola-rs/polars#29110"): "open",
    ("pr", "apache/arrow-rs#11482"): "open",
}


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read()
    if url.endswith(".xml"):
        return body.decode()
    return json.loads(body)


def url_for(registry, name):
    if registry == "pr":
        repo, num = name.split("#")
        return f"https://api.github.com/repos/{repo}/pulls/{num}"
    if registry == "node":
        return "https://nodejs.org/dist/index.json"
    if registry == "chrome":
        return f"https://chromiumdash.appspot.com/fetch_releases?channel={name}&platform=Linux&num=1"
    if registry == "maven":
        g, a = name.split(":")
        return f"https://repo1.maven.org/maven2/{g.replace('.', '/')}/{a}/maven-metadata.xml"
    return {
        "pypi": f"https://pypi.org/pypi/{name}/json",
        "npm": f"https://registry.npmjs.org/{name.replace('/', '%2F')}/latest",
        "crates": f"https://crates.io/api/v1/crates/{name}",
        "hex": f"https://hex.pm/api/packages/{name}",
        "nuget": f"https://api.nuget.org/v3-flatcontainer/{name.lower()}/index.json",
        "pub": f"https://pub.dev/api/packages/{name}",
        "rubygems": f"https://rubygems.org/api/v1/versions/{name}/latest.json",
        "github": f"https://api.github.com/repos/{name}/releases/latest",
    }[registry]


def parse(registry, data, name=""):
    """Pull the latest stable version out of a registry's JSON."""
    if registry == "node":  # newest release on the major line `name`
        return next(r["version"] for r in data if r["version"].startswith(f"v{name}."))
    if registry == "chrome":
        return data[0]["version"]
    if registry == "pr":  # open / merged / closed
        return "merged" if data.get("merged") else data["state"]
    if registry == "pypi":
        return data["info"]["version"]
    if registry == "npm":
        return data["version"]
    if registry == "crates":
        c = data["crate"]
        return c.get("max_stable_version") or c["max_version"]
    if registry == "maven":  # maven-metadata.xml text; <release> is the newest non-snapshot
        import re
        return re.search(r"<release>([^<]+)</release>", data).group(1)
    if registry == "hex":
        return data.get("latest_stable_version") or data["releases"][0]["version"]
    if registry == "nuget":
        stable = [v for v in data["versions"] if "-" not in v]
        return stable[-1]
    if registry == "pub":
        return data["latest"]["version"]
    if registry == "rubygems":
        return data["version"]
    if registry == "github":
        return data["tag_name"]
    raise KeyError(registry)


def check(expected=EXPECTED, fetch=_get):
    rows = []
    for (registry, name), want in expected.items():
        try:
            got = parse(registry, fetch(url_for(registry, name)), name)
            status = "same" if got == want else "MOVED"
        except Exception as e:  # one bad registry shouldn't hide the rest
            got, status = f"{type(e).__name__}: {e}", "ERROR"
        rows.append({"registry": registry, "name": name, "page": want, "now": got, "status": status})
    return rows


def main(argv):
    rows = check()
    if "--json" in argv:
        print(json.dumps(rows, indent=1))
    else:
        for r in rows:
            mark = "" if r["status"] == "same" else f"  <-- {r['status']}"
            print(f"{r['registry']:8} {r['name']:28} page {r['page']:14} now {r['now']}{mark}")
    moved = sum(r["status"] == "MOVED" for r in rows)
    errors = sum(r["status"] == "ERROR" for r in rows)
    print(f"{moved} moved, {errors} errors, {len(rows)} checked")
    return 1 if moved else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
