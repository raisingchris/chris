"""Step zero in bulk: which issues already have a pull request that names them?

A bug with 0 comments is not a bug nobody is on. Fix PRs link an issue
("Fixes #123") without commenting on it, so the issue page looks quiet.
This asks GitHub's search for PRs in the same repo that mention the number,
and keeps only those whose title or body really says `#<number>`.

Usage:
  python -I linked_prs.py owner/repo 123          # one issue: prints each PR
  python -I linked_prs.py --tsv in.tsv out.tsv    # rows "repo<TAB>number<TAB>..."
                                                  # -> "repo number count states ..."
Search API limit is 30 a minute, so the TSV mode sleeps 2.2 s between calls.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from typing import Callable

Search = Callable[[str], list]


def gh_search(query: str) -> list:
    out = subprocess.run(['gh', 'api', '-X', 'GET', 'search/issues', '-f', f'q={query}',
                          '-f', 'per_page=50'], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)['items']


def mentions(item: dict, num: int | str) -> bool:
    text = (item.get('title') or '') + ' ' + (item.get('body') or '')
    return re.search(rf'#{num}(?!\d)', text) is not None


def linked_prs(repo: str, num: int | str, search: Search = gh_search) -> list[dict]:
    items = search(f'repo:{repo} is:pr {num}')
    return [i for i in items if mentions(i, num)]


def tsv(src: str, dst: str, search: Search = gh_search, pause: float = 2.2) -> None:
    with open(src) as f, open(dst, 'w') as o:
        for line in f:
            cols = line.rstrip('\n').split('\t')
            try:
                prs = linked_prs(cols[0], cols[1], search)
                n, states = str(len(prs)), ','.join(p['state'] for p in prs)
            except subprocess.CalledProcessError:
                n, states = 'ERR', ''
            o.write('\t'.join([cols[0], cols[1], n, states] + cols[2:]) + '\n')
            o.flush()
            time.sleep(pause)


def main(argv: list[str]) -> int:
    if argv[:1] == ['--tsv']:
        tsv(argv[1], argv[2])
        return 0
    repo, num = argv
    for p in linked_prs(repo, num):
        print(p['number'], p['state'], p['user']['login'], p['created_at'][:10], p['title'])
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
