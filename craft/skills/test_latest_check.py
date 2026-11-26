import latest_check as lc


def test_parsers_pick_latest():
    assert lc.parse("pypi", {"info": {"version": "2.1.0"}}) == "2.1.0"
    assert lc.parse("crates", {"crate": {"max_stable_version": "0.10.4", "max_version": "0.11.0-rc1"}}) == "0.10.4"
    assert lc.parse("nuget", {"versions": ["3.3.6", "3.3.7", "4.0.0-beta1"]}) == "3.3.7"
    assert lc.parse("maven", "<metadata><versioning><release>2.15.1</release></versioning></metadata>") == "2.15.1"
    node = [{"version": "v26.13.1"}, {"version": "v24.22.3"}, {"version": "v24.22.2"}]
    assert lc.parse("node", node, "24") == "v24.22.3"
    assert lc.parse("chrome", [{"version": "[redacted]"}]) == "[redacted]"
    assert lc.parse("pr", {"state": "closed", "merged": True}) == "merged"
    assert lc.parse("pr", {"state": "open", "merged": False}) == "open"
    assert lc.url_for("pr", "lau/tzdata#194") == "https://api.github.com/repos/lau/tzdata/pulls/194"


def test_url_for_builds_only_its_own_url():
    # regression: the URL table used to format every registry at once and crash
    assert lc.url_for("pypi", "tzdata") == "https://pypi.org/pypi/tzdata/json"
    assert "%2F" in lc.url_for("npm", "@js-joda/timezone")
    assert lc.url_for("maven", "org.threeten:threetenbp").endswith("org/threeten/threetenbp/maven-metadata.xml")


def test_check_reports_same_moved_error():
    exp = {("pypi", "a"): "1.0", ("pypi", "b"): "1.0", ("pypi", "c"): "1.0"}

    def fetch(url):
        if "/c/" in url:
            raise TimeoutError("slow")
        return {"info": {"version": "1.0" if "/a/" in url else "2.0"}}

    rows = {r["name"]: r for r in lc.check(exp, fetch)}
    assert rows["a"]["status"] == "same"
    assert rows["b"]["status"] == "MOVED" and rows["b"]["now"] == "2.0"
    assert rows["c"]["status"] == "ERROR"


def test_php_and_wordpress():
    # php.net: releases/index.php?json&version=8.4 -> {"version": "8.4.28", ...}
    assert lc.url_for("php", "8.4") == "https://www.php.net/releases/index.php?json&version=8.4"
    assert lc.parse("php", {"version": "8.4.28", "date": "19 Nov 2026"}, "8.4") == "8.4.28"
    # wordpress.org version-check API: first offer is the current release
    assert lc.url_for("wordpress", "core").startswith("https://api.wordpress.org/core/version-check/")
    assert lc.parse("wordpress", {"offers": [{"version": "7.1.5"}, {"version": "7.0.9"}]}) == "7.1.5"
