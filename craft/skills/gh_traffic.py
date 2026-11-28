#!/usr/bin/env python3
"""Does anyone read my GitHub repos? Views, unique visitors, clones and referrers.

A reader count that still works while Google Analytics is off. GitHub keeps
14 days and only shows it to people with push access.

Usage: python3 gh_traffic.py                    # every non-fork repo of raisingchris2026
       python3 gh_traffic.py tz-2026 sitecheck  # just these

One line per repo: views/uniques, clones/uniques, top referrers.
"Clones with 0 views" is flagged: that's almost always bots and mirrors, not people.
Needs `gh` logged in. Read-only.
"""
import json
import subprocess
import sys

OWNER = "raisingchris2026"


def gh(path):
    out = subprocess.run(["gh", "api", path], capture_output=True, text=True)
    if out.returncode != 0:
        return None
    return json.loads(out.stdout)


def summarize(name, views, clones, referrers):
    """Return one plain line for a repo from the three API answers."""
    v = views or {}
    c = clones or {}
    line = (f"{name}: views {v.get('count', 0)}/{v.get('uniques', 0)} uniq, "
            f"clones {c.get('count', 0)}/{c.get('uniques', 0)} uniq")
    refs = ", ".join(f"{r['referrer']} {r['count']}" for r in (referrers or [])[:3])
    if refs:
        line += f", from {refs}"
    if v.get("count", 0) == 0 and c.get("count", 0) > 0:
        line += "  <- clones but no views: bots, not people"
    if views is None:
        line += "  (views unreadable)"
    return line


def main(argv):
    names = argv
    if not names:
        repos = gh(f"users/{OWNER}/repos?per_page=100") or []
        names = [r["name"] for r in repos if not r.get("fork")]
    for n in names:
        base = f"repos/{OWNER}/{n}/traffic"
        print(summarize(n, gh(base + "/views"), gh(base + "/clones"),
                        gh(base + "/popular/referrers")))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
