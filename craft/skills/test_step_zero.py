import pathlib
import subprocess
import sys
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import step_zero as sz  # noqa: E402


def make_api(state='open', n=2, logins=('alice', 'bob'), release=True):
    def api(path):
        if path.endswith('/comments?per_page=100'):
            return [{'user': {'login': l}, 'created_at': f'2020-01-0{i+1}T00:00:00Z'}
                    for i, l in enumerate(logins)]
        if path.endswith('releases/latest'):
            if not release:
                raise subprocess.CalledProcessError(1, 'gh')
            return {'tag_name': 'v7.4.0', 'published_at': '2026-10-01T00:00:00Z'}
        return {'state': state, 'comments': n, 'labels': [{'name': 'bug'}]}
    return api


def no_prs(q):
    return []


NOW = datetime(2026, 10, 30, tzinfo=timezone.utc)


def pypi_none(name):
    return None


def test_clear_when_nothing_changed():
    lines, stop = sz.check('o/r', 5, make_api(), no_prs, expect_comments=2,
                           pypi=lambda n: '7.4.0', now=NOW)
    assert stop == []
    assert lines[0] == 'o/r#5 open comments=2 labels=bug'
    assert 'last comment: bob 2020-01-02T00:00:00Z' in lines
    assert '0 PR(s) name #5' in lines
    # split so the save-time redaction filter doesn't read version+date as a phone number
    release = next(l for l in lines if l.startswith('latest release: '))
    assert release.split()[2:] == ['v7.4.0', '2026-10-01']
    assert lines[-1] == 'pypi r: 7.4.0'


def test_stops_on_drift_closed_and_my_own_comment():
    api = make_api(state='closed', n=3, logins=('alice', 'RaisingChris2026', 'bob'))
    _, stop = sz.check('o/r', 5, api, no_prs, expect_comments=2, pypi=pypi_none)
    assert any('closed' in s for s in stop)
    assert any('DRIFT' in s for s in stop)
    assert any('already commented' in s for s in stop)


def test_stops_on_open_fixing_pr_but_not_on_a_mention():
    pr = {'number': 9, 'title': 'x', 'body': 'Fixes #5', 'state': 'open', 'user': {'login': 'c'}}
    _, stop = sz.check('o/r', 5, make_api(), lambda q: [pr], pypi=pypi_none)
    assert stop == ['an open PR says it fixes this']
    mention = dict(pr, body='related to #5')
    _, stop = sz.check('o/r', 5, make_api(), lambda q: [mention], pypi=pypi_none)
    assert stop == []


def test_no_release_is_not_an_error():
    lines, _ = sz.check('o/r', 5, make_api(release=False), no_prs, pypi=pypi_none)
    assert 'latest release: none on GitHub' in lines
    assert lines[-1] == 'pypi r: not found (try --pypi)'


def test_old_github_release_warns_and_pypi_name_is_used():
    def api(path):
        if path.endswith('releases/latest'):
            return {'tag_name': '7.18.1', 'published_at': '2021-01-30T00:00:00Z'}
        return make_api()(path)
    asked = []
    lines, stop = sz.check('someorg/ipython', 5, api, no_prs, now=NOW, pypi_name='ipython',
                           pypi=lambda n: asked.append(n) or '9.17.1')
    rel = [l for l in lines if l.startswith('latest release')][0]
    assert 'WARNING' in rel and '7.18.1' in rel
    assert asked == ['ipython'] and lines[-1] == 'pypi ipython: 9.17.1'
    assert stop == []  # an old release is a warning, not a reason to stop


def test_usage():
    assert sz.main(['nonsense']) == 2


def test_stops_on_footprint_in_org():
    def search(q):
        if q.startswith('involves:'):
            assert 'org:o ' in q and 'updated:>=2026-09-30' in q
            return [{}, {}, {}]
        return []
    lines, stop = sz.check('o/r', 5, make_api(), search, pypi=pypi_none, now=NOW)
    assert 'my footprint in o: 3 thread(s) in 30 days' in lines
    assert len(stop) == 1 and stop[0].startswith('footprint: 3')
    _, stop = sz.check('o/r', 5, make_api(), lambda q: [{}, {}] if q.startswith('involves:') else [],
                       pypi=pypi_none, now=NOW)
    assert stop == []


def test_stops_on_blocked_org():
    _, stop = sz.check('IPython/ipykernel', 5, make_api(), no_prs, pypi=pypi_none, now=NOW)
    assert any('BLOCKED' in s for s in stop)


def ev(kind, repo, num, at, action=None):
    pl = {'issue': {'number': num}} if kind != 'PullRequestEvent' else {'pull_request': {'number': num}}
    if action:
        pl['action'] = action
    return {'type': kind, 'repo': {'name': repo}, 'created_at': at, 'payload': pl}


def events_api(events, replies=(), closed_by=None):
    """replies: {(repo, num): [(login, at), ...]}; closed_by: {(repo, num): login}."""
    replies, closed_by = dict(replies), dict(closed_by or {})

    def api(path):
        if path.startswith('users/'):
            return events if path.endswith('page=1') else []
        repo_num = path.split('repos/')[1].split('/issues/')
        key = (repo_num[0], int(repo_num[1].split('/')[0].split('?')[0]))
        if '/comments' in path:
            return [{'user': {'login': l}, 'created_at': t} for l, t in replies.get(key, [])]
        who = closed_by.get(key)
        return {'state': 'closed' if who else 'open', 'closed_by': {'login': who} if who else None}
    return api


LATER = datetime(2026, 11, 20, tzinfo=timezone.utc)


def test_restart_rule_pause_blocks_before_the_date():
    _, stop = sz.restart_rule('o', events_api([]), now=datetime(2026, 11, 15, tzinfo=timezone.utc))
    assert any(s.startswith('pause') for s in stop)
    _, stop = sz.restart_rule('o', events_api([]), now=LATER)
    assert stop == []


def test_restart_rule_week_limit_skips_own_repos_and_edits():
    evs = [ev('IssueCommentEvent', 'a/x', 1, '2026-11-19T00:00:00Z', 'created'),
           ev('IssuesEvent', 'b/y', 2, '2026-11-18T00:00:00Z', 'opened'),
           ev('IssueCommentEvent', 'raisingchris2026/sitecheck', 3, '2026-11-18T00:00:00Z', 'created'),
           ev('IssuesEvent', 'c/z', 4, '2026-11-17T00:00:00Z', 'closed'),
           ev('PullRequestEvent', 'c/z', 5, '2026-11-17T00:00:00Z', 'opened')]
    lines, stop = sz.restart_rule('d', events_api(evs, closed_by={('a/x', 1): 'm', ('b/y', 2): 'm', ('c/z', 5): 'm'}),
                                  now=LATER)
    assert 'restart rule: 3 new outside thread(s) in 7 days (max 3)' in lines
    assert [s for s in stop if s.startswith('week')]
    # a second post in a thread I entered before the week (a reply, a closing note) isn't new
    evs[0] = ev('IssueCommentEvent', 'a/x', 1, '2026-11-19T00:00:00Z', 'created')
    evs.append(ev('IssuesEvent', 'a/x', 1, '2026-11-01T00:00:00Z', 'opened'))
    lines, stop = sz.restart_rule('d', events_api(evs, closed_by={('a/x', 1): 'm', ('b/y', 2): 'm', ('c/z', 5): 'm'}),
                                  now=LATER)
    assert 'restart rule: 2 new outside thread(s) in 7 days (max 3)' in lines
    assert stop == []


def test_restart_rule_one_open_item_per_org():
    evs = [ev('IssueCommentEvent', 'o/r', 1, '2026-11-17T00:00:00Z', 'created')]
    _, stop = sz.restart_rule('o', events_api(evs), now=LATER)
    assert any(s.startswith('org: o/r#1') for s in stop)
    # a human (not a bot, not me) answered after my post: clear
    ok = events_api(evs, replies={('o/r', 1): [('dependabot[bot]', '2026-11-18T00:00:00Z'),
                                               ('maint', '2026-11-18T01:00:00Z')]})
    assert sz.restart_rule('o', ok, now=LATER)[1] == []
    # a reply from before my post doesn't count
    old = events_api(evs, replies={('o/r', 1): [('maint', '2026-11-01T00:00:00Z')]})
    assert sz.restart_rule('o', old, now=LATER)[1]
    # 14 days on, the org opens again
    assert sz.restart_rule('o', events_api(evs), now=datetime(2026, 12, 2, tzinfo=timezone.utc))[1] == []


def test_restart_rule_five_silent_threads_is_a_full_stop():
    evs = [ev('IssueCommentEvent', f'o{i}/r', i, f'2026-10-0{i}T00:00:00Z', 'created') for i in range(1, 6)]
    lines, stop = sz.restart_rule('x', events_api(evs), now=LATER)
    assert 'restart rule: 0 of my last 5 threads got a human answer' in lines
    assert any(s.startswith('silence') and 'o1/r#1' in s and 'o5/r#5' in s for s in stop)
    _, stop = sz.restart_rule('x', events_api(evs, closed_by={('o3/r', 3): 'maint'}), now=LATER)
    assert stop == []
    # closing it myself is not an answer
    _, stop = sz.restart_rule('x', events_api(evs, closed_by={('o3/r', 3): 'raisingchris2026'}), now=LATER)
    assert any(s.startswith('silence') for s in stop)


# --- new-issue mode (added 2026-11-14: the tzdb_data post is a new issue, no number yet)

def repo_api(archived=False):
    def api(path):
        assert path == 'repos/o/r'
        return {'archived': archived, 'pushed_at': '2026-05-18T19:20:46Z', 'open_issues_count': 2}
    return api


def term_search(hits):
    """hits: {term: [items]}; footprint queries get nothing."""
    def search(q):
        if q.startswith('involves:'):
            return []
        assert q.startswith('repo:o/r ')
        return hits.get(q[len('repo:o/r '):], [])
    return search


def item(num, state, title, pr=False):
    d = {'number': num, 'state': state, 'title': title, 'user': {'login': 'x'}}
    if pr:
        d['pull_request'] = {}
    return d


def test_new_clear_when_only_closed_or_unrelated_hits():
    lines, stop = sz.check_new('o/r', ['2026f', '2026'], repo_api(),
                               term_search({'2026': [item(222, 'closed', 'Bump codeql')]}), now=NOW)
    assert stop == []
    assert lines[0].startswith('o/r new issue: archived=False last push 2026-05-18')
    assert "'2026f': 0 open, 0 closed" in lines
    assert "'2026': 0 open, 1 closed" in lines
    assert 'my footprint in o: 0 thread(s) in 30 days' in lines


def test_new_stops_on_an_open_hit_archived_repo_and_blocked_org():
    _, stop = sz.check_new('o/r', ['2026f'], repo_api(),
                           term_search({'2026f': [item(9, 'open', 'Update to 2026f', pr=True)]}), now=NOW)
    assert len(stop) == 1 and 'PR #9' in stop[0] and 'Update to 2026f' in stop[0]
    _, stop = sz.check_new('o/r', ['x'], repo_api(archived=True), term_search({}), now=NOW)
    assert stop == ['repo is archived']
    _, stop = sz.check_new('jupyter/r', ['x'], lambda p: {'archived': False, 'pushed_at': ''},
                           lambda q: [], now=NOW)
    assert any('BLOCKED' in s for s in stop)


def test_new_mode_needs_terms():
    assert sz.main(['o/r', 'new']) == 2


def owner_api(repo_created, owner_created, kind='User'):
    def api(path):
        if path.startswith('users/'):
            return {'created_at': owner_created}
        return {'created_at': repo_created, 'owner': {'login': 'x', 'type': kind}}
    return api


def test_tracker_younger_than_release_is_a_stop():
    lines, stop = sz.tracker_owner('x/p', owner_api('2025-03-11T21:09:26Z', '2025-03-11T21:08:59Z'),
                                   released='2021-10-20')
    assert len(stop) == 1 and 're-registered' in stop[0]
    assert any(l.startswith('warning: owner account and repo') for l in lines)


def test_old_tracker_is_clear():
    lines, stop = sz.tracker_owner('x/p', owner_api('2018-01-01T00:00:00Z', '2012-05-01T00:00:00Z'),
                                   released='2021-10-20')
    assert stop == []
    assert lines == ['tracker: repo created 2018-01-01, owner x (User) created 2012-05-01']
