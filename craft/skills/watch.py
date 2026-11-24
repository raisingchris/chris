"""The Monday check in one command: which threads I've promised to answer have news?

Reads the OPEN rows of memory/wiki/self/commitments.md, finds every GitHub
issue or PR link in them, and for each thread prints whether anyone other
than me has commented since my last comment, or whether it was closed after
it. The list comes from the promises file itself, so it can't drift from it.

Usage:
  python -I watch.py [path/to/commitments.md] [--me login,...]
Exit codes: 0 = all quiet, 1 = something to read, 2 = file/API error.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from typing import Callable

Api = Callable[[str], object]
ME = ('raisingchris2026',)
DEFAULT = 'memory/wiki/self/commitments.md'
URL = re.compile(r'https://github\.com/([\w.-]+/[\w.-]+)/(?:issues|pull)/(\d+)')
ROW = re.compile(r'^\|\s*(\d+)\s*\|')
# a bare link to one of my own repos (README promises to answer issues there)
OWN = re.compile(r'https://github\.com/(raisingchris2026/[\w.-]+?)(?=[\s|)/.,;]*(?:\s|\||\)|$))(?!/(?:issues|pull))')


def gh_api(path: str) -> object:
    out = subprocess.run(['gh', 'api', '-X', 'GET', path], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def open_threads(text: str) -> list[tuple[str, str, int]]:
    """(row number, owner/repo, issue number) for every GitHub link in an OPEN row."""
    found, seen = [], set()
    for line in text.splitlines():
        m = ROW.match(line)
        if not m:
            continue
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) < 5 or not re.match(r'^\**OPEN\b', cells[4]):
            continue
        for repo, num in URL.findall(line):
            key = (repo.lower(), int(num))
            if key not in seen:
                seen.add(key)
                found.append((m.group(1), repo, int(num)))
    return found


def open_rows(text: str):
    for line in text.splitlines():
        m = ROW.match(line)
        if not m:
            continue
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) >= 5 and re.match(r'^\**OPEN\b', cells[4]):
            yield m.group(1), line


def own_repos(text: str) -> list[tuple[str, str]]:
    """(row number, owner/repo) for each of my own repos linked bare in an OPEN row."""
    found, seen = [], set()
    for row, line in open_rows(text):
        for repo in OWN.findall(line):
            if repo.lower() not in seen:
                seen.add(repo.lower())
                found.append((row, repo))
    return found


def repo_news(repo: str, api: Api = gh_api, me: tuple[str, ...] = ME) -> list[str]:
    """Open issues/PRs on my repo where someone else spoke last (or opened it and nobody answered)."""
    mine = {m.lower() for m in me}
    items = []
    for it in api(f'repos/{repo}/issues?state=open&per_page=100'):
        last = it['user']['login']
        if it.get('comments'):
            last = all_comments(repo, it['number'], api)[-1]['user']['login']
        if last.lower() not in mine:
            kind = 'PR' if 'pull_request' in it else 'issue'
            items.append(f"{kind} #{it['number']} by {it['user']['login']}: last word from {last}")
    return items


def all_comments(repo: str, num: int, api: Api) -> list[dict]:
    out, page = [], 1
    while True:
        batch = api(f'repos/{repo}/issues/{num}/comments?per_page=100&page={page}')
        out.extend(batch)
        if len(batch) < 100:
            return out
        page += 1


def news(repo: str, num: int, api: Api = gh_api, me: tuple[str, ...] = ME) -> tuple[str, list[str]]:
    """Return (one summary line, list of things to read since my last comment)."""
    mine = {m.lower() for m in me}
    issue = api(f'repos/{repo}/issues/{num}')
    comments = all_comments(repo, num, api)
    my_times = [c['created_at'] for c in comments if c['user']['login'].lower() in mine]
    if (issue.get('user') or {}).get('login', '').lower() in mine:
        my_times.append(issue['created_at'])  # I opened it: the opening post is mine
    since = max(my_times) if my_times else ''
    items = [f"{c['user']['login']} commented {c['created_at']}" for c in comments
             if c['created_at'] > since and c['user']['login'].lower() not in mine]
    closed_at = issue.get('closed_at') or ''
    if issue['state'] != 'open' and closed_at > since:
        items.append(f"closed {closed_at} ({issue.get('state_reason') or issue['state']})")
    if not my_times:
        items.insert(0, 'no comment of mine found here (wrong link, or deleted?)')
    line = (f"{repo}#{num} {issue['state']} comments={issue['comments']} "
            f"my last={since or '-'}")
    return line, items


STRAY = re.compile(r'\|\s*(\d+)\s*\|[^|\n]*\|[^|\n]*\|[^|\n]*\|\s*\**OPEN\b')


def stray_rows(text: str) -> list[str]:
    """Row numbers of OPEN rows that start mid-line (glued to a log line), which open_threads can't see."""
    return [m.group(1) for line in text.splitlines() if not ROW.match(line)
            for m in STRAY.finditer(line)]


def run(text: str, api: Api = gh_api, me: tuple[str, ...] = ME) -> tuple[list[str], int]:
    lines, flagged = [], 0
    for row in stray_rows(text):
        lines.append(f'row {row}: FIX  OPEN row not in the table (starts mid-line), so it is not watched')
        flagged += 1
    threads = open_threads(text)
    for row, repo, num in threads:
        line, items = news(repo, num, api, me)
        lines.append(f"row {row}: {'NEWS ' if items else 'quiet'} {line}")
        lines.extend(f'    - {i}' for i in items)
        flagged += bool(items)
    repos = own_repos(text)
    for row, repo in repos:
        items = repo_news(repo, api, me)
        lines.append(f"row {row}: {'NEWS ' if items else 'quiet'} {repo} (my repo)")
        lines.extend(f'    - {i}' for i in items)
        flagged += bool(items)
    lines.append(f'{flagged} of {len(threads) + len(repos)} thread(s) need reading')
    return lines, flagged


def main(argv: list[str]) -> int:
    path, me = DEFAULT, ME
    it = iter(argv)
    for a in it:
        if a == '--me':
            me = tuple(next(it).split(','))
        else:
            path = a
    try:
        text = open(path, encoding='utf-8').read()
        lines, flagged = run(text, me=me)
    except OSError as e:
        print('cannot read', path, e, file=sys.stderr)
        return 2
    except subprocess.CalledProcessError as e:
        print('API error:', (e.stderr or '').strip()[:200], file=sys.stderr)
        return 2
    print('\n'.join(lines))
    return 1 if flagged else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
