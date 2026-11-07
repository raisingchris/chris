"""Step zero right before posting: has anything changed on this issue since I drafted?

One command per issue instead of five API calls typed by hand. It prints:
  state, comment count, last comment (who, when), labels, whether I (or any
  account in --me) already commented, PRs that name the issue (linked_prs.py),
  the repo's latest GitHub release, and the newest version on PyPI.
  (Some repos stopped making GitHub releases: ipython's "latest" is 7.18.1
  from 2021. So an old release gets a warning, and PyPI is asked too.)
With --expect-comments N it says DRIFT if the count moved, and exits 1 on any
reason to stop: closed, count moved, I already posted, or a PR says "Fixes #n".

Usage:
  python -I step_zero.py owner/repo 123 [--expect-comments N] [--me login,...] [--pypi name]
Exit codes: 0 = clear to post, 1 = stop and read, 2 = usage/API error.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from typing import Callable

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import linked_prs as lp  # noqa: E402

Api = Callable[[str], object]
Pypi = Callable[[str], 'str | None']
STALE_DAYS = 365
ME = ('raisingchris2026',)


def gh_api(path: str) -> object:
    out = subprocess.run(['gh', 'api', '-X', 'GET', path], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def pypi_latest(name: str) -> str | None:
    try:
        with urllib.request.urlopen(f'https://pypi.org/pypi/{name}/json', timeout=15) as r:
            return json.load(r)['info']['version']
    except Exception:
        return None


def check(repo: str, num: int | str, api: Api = gh_api, search: lp.Search = lp.gh_search,
          expect_comments: int | None = None, me: tuple[str, ...] = ME,
          pypi: Pypi = pypi_latest, pypi_name: str | None = None,
          now: datetime | None = None) -> tuple[list[str], list[str]]:
    """Return (lines to print, reasons to stop)."""
    issue = api(f'repos/{repo}/issues/{num}')
    comments = api(f'repos/{repo}/issues/{num}/comments?per_page=100')
    lines, stop = [], []
    labels = ','.join(l['name'] for l in issue.get('labels', [])) or '-'
    lines.append(f"{repo}#{num} {issue['state']} comments={issue['comments']} labels={labels}")
    if issue['state'] != 'open':
        stop.append(f"issue is {issue['state']}")
    if comments:
        last = comments[-1]
        lines.append(f"last comment: {last['user']['login']} {last['created_at']}")
    mine = [c for c in comments if c['user']['login'].lower() in {m.lower() for m in me}]
    if mine:
        stop.append(f"already commented ({len(mine)}x, first {mine[0]['created_at']})")
    if expect_comments is not None and issue['comments'] != expect_comments:
        stop.append(f"DRIFT: comments {expect_comments} -> {issue['comments']}")
    prs = lp.linked_prs(repo, num, search)
    for p in prs:
        lines.append(f"PR #{p['number']} {lp.state(p)} {lp.claim(p, num, repo)} {p['user']['login']} {p['title']}")
    lines.append(f"{len(prs)} PR(s) name #{num}")
    if any(lp.claim(p, num) == 'fixes' and lp.state(p) == 'open' for p in prs):
        stop.append('an open PR says it fixes this')
    try:
        rel = api(f'repos/{repo}/releases/latest')
        when = str(rel.get('published_at'))
        line = f"latest release: {rel.get('tag_name')} {when[:10]}"
        try:
            age = ((now or datetime.now(timezone.utc))
                   - datetime.fromisoformat(when.replace('Z', '+00:00'))).days
            if age > STALE_DAYS:
                line += f' (WARNING: {age} days old; this repo may not use GitHub releases)'
        except ValueError:
            pass
        lines.append(line)
    except subprocess.CalledProcessError:
        lines.append('latest release: none on GitHub')
    name = pypi_name or repo.split('/')[-1]
    ver = pypi(name)
    lines.append(f'pypi {name}: {ver}' if ver else f'pypi {name}: not found (try --pypi)')
    return lines, stop


def main(argv: list[str]) -> int:
    args, expect, me, pypi_name = [], None, ME, None
    it = iter(argv)
    for a in it:
        if a == '--expect-comments':
            expect = int(next(it))
        elif a == '--me':
            me = tuple(next(it).split(','))
        elif a == '--pypi':
            pypi_name = next(it)
        else:
            args.append(a)
    if len(args) != 2 or '/' not in args[0]:
        print(__doc__.strip().splitlines()[-3], file=sys.stderr)
        return 2
    try:
        lines, stop = check(args[0], args[1], expect_comments=expect, me=me, pypi_name=pypi_name)
    except subprocess.CalledProcessError as e:
        print('API error:', (e.stderr or '').strip()[:200], file=sys.stderr)
        return 2
    print('\n'.join(lines))
    print('STOP: ' + '; '.join(stop) if stop else 'CLEAR: nothing changed that blocks posting')
    return 1 if stop else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
