"""Step zero right before posting: has anything changed on this issue since I drafted?

One command per issue instead of five API calls typed by hand. It prints:
  state, comment count, last comment (who, when), labels, whether I (or any
  account in --me) already commented, PRs that name the issue (linked_prs.py),
  the repo's latest GitHub release, and the newest version on PyPI.
  (Some repos stopped making GitHub releases: ipython's "latest" is 7.18.1
  from 2021. So an old release gets a warning, and PyPI is asked too.)
With --expect-comments N it says DRIFT if the count moved, and exits 1 on any
reason to stop: closed, count moved, I already posted, or a PR says "Fixes #n".
It also counts my footprint in the owner's org: threads I've touched there in the
last 30 days. 3 or more is a stop, and so is an org on BLOCKED (my own list of
orgs that blocked me or that I left). Added 2026-11-09, the day ipython and jupyter
blocked me after 19 posts in 11 days: the check I lacked wasn't about the issue,
it was about how much of the room's noise was already mine.

Then the restart rule I sent my parents on 2026-11-10 (memory/inbox/work/audit-posts.md),
read from my own public GitHub events, so it can't drift from what I actually did:
  - nothing new before PAUSE_UNTIL (no outside posts while I'm on pause);
  - at most 3 new outside threads in any 7 days, all orgs together (a reply in a
    thread I'm already in doesn't count);
  - one open item per org: a post there with no human answer yet, younger than 14
    days, is a stop;
  - my last 5 outside posts all with no human answer = full stop, write to parents.
"Human answer" = a comment after my post by someone who isn't me and isn't a bot,
or the thread closed by someone else.

New issue (no number yet; added 2026-11-14): `owner/repo new --search t1,t2` checks the
org isn't BLOCKED, the repo isn't archived, no issue or PR matching any term is open
(someone may already have it), my footprint in the org, and the restart rule.

Usage:
  python -I step_zero.py owner/repo 123 [--expect-comments N] [--me login,...] [--pypi name]
  python -I step_zero.py owner/repo new --search term1,term2 [--me login,...]
  add --released YYYY-MM-DD (a package release that links this repo) to check the
  tracker still belongs to the author (see tracker_owner).
Exit codes: 0 = clear to post, 1 = stop and read, 2 = usage/API error.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Callable

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import linked_prs as lp  # noqa: E402

Api = Callable[[str], object]
Pypi = Callable[[str], 'str | None']
STALE_DAYS = 365
ME = ('raisingchris2026',)
FOOTPRINT_DAYS = 30
FOOTPRINT_MAX = 3
# Orgs that blocked me (archive:2026-11-09#188, #201) or that I left the same day.
BLOCKED = ('ipython', 'jupyter', 'jupyter-server', 'jupyterlab', 'jupyter-widgets')
PAUSE_UNTIL = '2026-11-16'   # first day new posts are allowed again
WEEK_MAX = 3
ORG_WAIT_DAYS = 14
SILENT_RUN = 5


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
    owner = repo.split('/')[0].lower()
    if owner in BLOCKED:
        stop.append(f'org {owner} is on my BLOCKED list: never post there')
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
    since = ((now or datetime.now(timezone.utc)) - timedelta(days=FOOTPRINT_DAYS)).date().isoformat()
    mine_org = search(f'involves:{me[0]} org:{owner} updated:>={since}')
    lines.insert(1, f'my footprint in {owner}: {len(mine_org)} thread(s) in {FOOTPRINT_DAYS} days')
    if len(mine_org) >= FOOTPRINT_MAX:
        stop.append(f'footprint: {len(mine_org)} of my threads in {owner} in {FOOTPRINT_DAYS} days '
                    f'(max {FOOTPRINT_MAX - 1}); wait for answers first')
    return lines, stop


def check_new(repo: str, terms: list[str], api: Api = gh_api, search: lp.Search = lp.gh_search,
              me: tuple[str, ...] = ME, now: datetime | None = None) -> tuple[list[str], list[str]]:
    """Before opening a NEW issue: is the room open, and has anyone already raised it?"""
    lines, stop = [], []
    owner = repo.split('/')[0].lower()
    if owner in BLOCKED:
        stop.append(f'org {owner} is on my BLOCKED list: never post there')
    info = api(f'repos/{repo}')
    lines.append(f"{repo} new issue: archived={info.get('archived')} "
                 f"last push {str(info.get('pushed_at'))[:10]}")
    if info.get('archived'):
        stop.append('repo is archived')
    for t in terms:
        hits = search(f'repo:{repo} {t}')
        open_ = [h for h in hits if h.get('state') == 'open']
        lines.append(f"'{t}': {len(open_)} open, {len(hits) - len(open_)} closed")
        for h in hits:
            kind = 'PR' if 'pull_request' in h else 'issue'
            lines.append(f"  {kind} #{h['number']} {h['state']} {h['title']}")
        for h in open_:
            kind = 'PR' if 'pull_request' in h else 'issue'
            stop.append(f"open {kind} #{h['number']} matches '{t}': {h['title']} (read it first)")
    since = ((now or datetime.now(timezone.utc)) - timedelta(days=FOOTPRINT_DAYS)).date().isoformat()
    mine_org = search(f'involves:{me[0]} org:{owner} updated:>={since}')
    lines.append(f'my footprint in {owner}: {len(mine_org)} thread(s) in {FOOTPRINT_DAYS} days')
    if len(mine_org) >= FOOTPRINT_MAX:
        stop.append(f'footprint: {len(mine_org)} of my threads in {owner} in {FOOTPRINT_DAYS} days')
    return lines, stop


def _ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace('Z', '+00:00'))


def my_posts(api: Api, me: tuple[str, ...] = ME) -> list[dict]:
    """My outside posts, newest first: {repo, num, at}. From the public events feed
    (last 90 days, at most 300 events); my own account's repos are left out."""
    posts = []
    for page in (1, 2, 3):
        evs = api(f'users/{me[0]}/events/public?per_page=100&page={page}')
        if not evs:
            break
        for e in evs:
            repo, pl = e['repo']['name'], e.get('payload', {})
            if repo.split('/')[0].lower() in {m.lower() for m in me}:
                continue
            if e['type'] == 'IssueCommentEvent' and pl.get('action', 'created') == 'created':
                num = pl['issue']['number']
            elif e['type'] in ('IssuesEvent', 'PullRequestEvent') and pl.get('action') == 'opened':
                num = (pl.get('issue') or pl.get('pull_request'))['number']
            else:
                continue
            posts.append({'repo': repo, 'num': num, 'at': e['created_at']})
    posts.sort(key=lambda p: p['at'], reverse=True)
    return posts


def answered(api: Api, post: dict, me: tuple[str, ...] = ME) -> bool:
    """Did a human other than me act on this thread after my post?"""
    mine = {m.lower() for m in me}
    at = _ts(post['at'])
    for c in api(f"repos/{post['repo']}/issues/{post['num']}/comments?per_page=100"):
        who = c['user']['login'].lower()
        if who not in mine and not who.endswith('[bot]') and _ts(c['created_at']) > at:
            return True
    issue = api(f"repos/{post['repo']}/issues/{post['num']}")
    by = ((issue.get('closed_by') or {}).get('login') or '').lower()
    return issue.get('state') == 'closed' and bool(by) and by not in mine


def restart_rule(owner: str, api: Api = gh_api, me: tuple[str, ...] = ME,
                 now: datetime | None = None) -> tuple[list[str], list[str]]:
    """The 2026-11-10 restart rule. Return (lines, reasons to stop)."""
    now = now or datetime.now(timezone.utc)
    lines, stop = [], []
    if now.date().isoformat() < PAUSE_UNTIL:
        stop.append(f'pause: no new outside posts before {PAUSE_UNTIL}')
    posts = my_posts(api, me)
    # one thread counts once, at my latest post in it
    seen, threads = set(), []
    for p in posts:
        key = (p['repo'].lower(), p['num'])
        if key not in seen:
            seen.add(key)
            threads.append(p)
    # the week limit counts threads I walked into, at my first post there; replies I
    # owe and closing notes on my own drafts aren't new noise
    first: dict = {}
    for p in posts:
        first[(p['repo'].lower(), p['num'])] = p['at']   # posts are newest first
    week = [k for k, at in first.items() if now - _ts(at) < timedelta(days=7)]
    lines.append(f'restart rule: {len(week)} new outside thread(s) in 7 days (max {WEEK_MAX})')
    if len(week) >= WEEK_MAX:
        stop.append(f'week: {len(week)} new outside threads in 7 days (max {WEEK_MAX})')
    for p in threads:
        if p['repo'].split('/')[0].lower() != owner.lower():
            continue
        if now - _ts(p['at']) >= timedelta(days=ORG_WAIT_DAYS):
            continue
        if not answered(api, p, me):
            stop.append(f"org: {p['repo']}#{p['num']} ({p['at'][:10]}) has no human answer "
                        f'and is under {ORG_WAIT_DAYS} days old')
    last = threads[:SILENT_RUN]
    if len(last) == SILENT_RUN:
        silent = [p for p in last if not answered(api, p, me)]
        lines.append(f'restart rule: {SILENT_RUN - len(silent)} of my last {SILENT_RUN} threads got a human answer')
        if len(silent) == SILENT_RUN:
            names = ', '.join(f"{p['repo']}#{p['num']}" for p in silent)
            stop.append(f'silence: my last {SILENT_RUN} threads have no human answer ({names}); '
                        'stop all new posts and write to my parents')
    return lines, stop


def tracker_owner(repo: str, api: Api = gh_api, released: str | None = None) -> tuple[list[str], list[str]]:
    """Does this tracker still belong to the people who made the package?

    Added 2026-11-18: npm `windows-iana` (5.1.0, 2021) points to github.com/rubenillodo/windows-iana,
    but that account was made 2025-03-11, 27 s before the repo, which holds only a bug-bounty
    tester's README. The author's name had been re-registered; an issue there reaches a stranger.
    With --released DATE (a release that names this repo), a repo younger than it is a stop.
    Without it, a user account made within a day of the repo is a warning line only.
    """
    lines, stop = [], []
    info = api(f'repos/{repo}')
    owner = info.get('owner') or {}
    rc = str(info.get('created_at') or '')
    oc = ''
    if owner.get('type') == 'User' and owner.get('login'):
        oc = str((api(f"users/{owner['login']}") or {}).get('created_at') or '')
    lines.append(f"tracker: repo created {rc[:10] or '?'}, owner {owner.get('login')} "
                 f"({owner.get('type')}) created {oc[:10] or '?'}")
    if released and rc and rc[:10] > released:
        stop.append(f'repo created {rc[:10]}, after the release {released} that points here: '
                    'the name may have been re-registered; this tracker may not reach the author')
    if rc and oc and abs((_ts(rc) - _ts(oc)).total_seconds()) < 86400:
        lines.append('warning: owner account and repo made within a day of each other')
    return lines, stop


def main(argv: list[str]) -> int:
    args, expect, me, pypi_name, terms, released = [], None, ME, None, [], None
    it = iter(argv)
    for a in it:
        if a == '--expect-comments':
            expect = int(next(it))
        elif a == '--me':
            me = tuple(next(it).split(','))
        elif a == '--pypi':
            pypi_name = next(it)
        elif a == '--released':
            released = next(it)
        elif a == '--search':
            terms = [t for t in next(it).split(',') if t]
        else:
            args.append(a)
    if len(args) != 2 or '/' not in args[0]:
        print(__doc__.strip().splitlines()[-3], file=sys.stderr)
        return 2
    if args[1] == 'new' and not terms:
        print('new mode needs --search term1,term2', file=sys.stderr)
        return 2
    try:
        if args[1] == 'new':
            lines, stop = check_new(args[0], terms, me=me)
        else:
            lines, stop = check(args[0], args[1], expect_comments=expect, me=me, pypi_name=pypi_name)
        more, stop2 = tracker_owner(args[0], released=released)
        lines += more
        stop += stop2
        more, stop2 = restart_rule(args[0].split('/')[0], me=me)
        lines += more
        stop += stop2
    except subprocess.CalledProcessError as e:
        print('API error:', (e.stderr or '').strip()[:200], file=sys.stderr)
        return 2
    print('\n'.join(lines))
    print('STOP: ' + '; '.join(stop) if stop else 'CLEAR: nothing changed that blocks posting')
    return 1 if stop else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
