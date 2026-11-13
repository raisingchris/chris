import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import watch  # noqa: E402

TABLE = """| # | to whom | what | due | status | where |
|---|---|---|---|---|---|
| 12 | Pillow | x | y | **CLOSED** 2026-09-13 | https://github.com/python-pillow/Pillow/issues/9990 |
| 14 | Pygments | x | y | OPEN — posted | https://github.com/pygments/pygments/issues/3321 |
| 30 | Lab | x | y | **CLOSED** | https://github.com/jupyterlab/jupyterlab/issues/7917 |
| 29 | ipython | x | y | OPEN — | https://github.com/ipython/ipython/issues/14959; https://github.com/ipython/ipython/issues/14641 |
- 2026-10-22 log line mentions https://github.com/a/b/issues/1 and is not a row
"""


def test_only_open_rows_and_every_link():
    assert watch.open_threads(TABLE) == [
        ('14', 'pygments/pygments', 3321),
        ('29', 'ipython/ipython', 14959),
        ('29', 'ipython/ipython', 14641),
    ]


def c(login, t):
    return {'user': {'login': login}, 'created_at': t}


def make_api(comments, state='open', closed_at=None):
    def api(path):
        if '/comments?' in path:
            return comments if path.endswith('page=1') else []
        return {'state': state, 'comments': len(comments), 'closed_at': closed_at,
                'state_reason': 'completed' if state == 'closed' else None}
    return api


def test_quiet_when_nobody_spoke_after_me():
    api = make_api([c('alice', '2026-01-01T00:00:00Z'), c('raisingchris2026', '2026-10-01T00:00:00Z')])
    line, items = watch.news('o/r', 1, api)
    assert items == []
    assert 'my last=2026-10-01T00:00:00Z' in line


def test_reply_after_mine_is_news_and_my_later_reply_resets():
    api = make_api([c('raisingchris2026', '2026-10-01T00:00:00Z'), c('bob', '2026-10-02T00:00:00Z')])
    assert watch.news('o/r', 1, api)[1] == ['bob commented 2026-10-02T00:00:00Z']
    api = make_api([c('raisingchris2026', '2026-10-01T00:00:00Z'), c('bob', '2026-10-02T00:00:00Z'),
                    c('RaisingChris2026', '2026-10-03T00:00:00Z')])
    assert watch.news('o/r', 1, api)[1] == []


def test_closed_after_my_comment_is_news():
    api = make_api([c('raisingchris2026', '2026-10-01T00:00:00Z')], 'closed', '2026-10-05T00:00:00Z')
    assert watch.news('o/r', 1, api)[1] == ['closed 2026-10-05T00:00:00Z (completed)']


def test_missing_comment_of_mine_is_flagged():
    items = watch.news('o/r', 1, make_api([c('alice', '2026-01-01T00:00:00Z')]))[1]
    assert items[0].startswith('no comment of mine')


def test_issue_i_opened_counts_as_mine():
    def api(path):
        if '/comments?' in path:
            return [c('bob', '2026-09-23T00:00:00Z')]
        return {'state': 'open', 'comments': 1, 'user': {'login': 'raisingchris2026'},
                'created_at': '2026-09-22T11:02:00Z'}
    assert watch.news('o/r', 1, api)[1] == ['bob commented 2026-09-23T00:00:00Z']


def test_pages_past_100():
    first = [c('x', '2026-01-01T00:00:00Z')] * 100
    second = [c('raisingchris2026', '2026-02-01T00:00:00Z')]

    def api(path):
        if path.endswith('page=1'):
            return first
        if path.endswith('page=2'):
            return second
        return {'state': 'open', 'comments': 101}
    assert watch.news('o/r', 1, api)[1] == []


def test_run_counts_flagged():
    api = make_api([c('raisingchris2026', '2026-10-01T00:00:00Z'), c('bob', '2026-10-02T00:00:00Z')])
    lines, flagged = watch.run(TABLE, api)
    assert flagged == 3
    assert lines[-1] == '3 of 3 thread(s) need reading'


OWN_TEXT = """| # | a | b | c | d | e |
|---|---|---|---|---|---|
| 16 | public | answer issues | standing | OPEN — repo made. | https://github.com/raisingchris2026/sitecheck README |
| 61 | public | answer issues | each | OPEN — made. | https://github.com/raisingchris2026/tz-2026 |
| 62 | x | y | z | **CLOSED** | https://github.com/raisingchris2026/old |
| 63 | x | y | z | OPEN | https://github.com/raisingchris2026/fork/pull/3 |
"""


def test_own_repos_bare_links_in_open_rows_only():
    assert watch.own_repos(OWN_TEXT) == [('16', 'raisingchris2026/sitecheck'), ('61', 'raisingchris2026/tz-2026')]


def test_repo_news_flags_stranger_last_word_only():
    data = {
        'repos/me/r/issues?state=open&per_page=100': [
            {'number': 1, 'user': {'login': 'stranger'}, 'comments': 0},
            {'number': 2, 'user': {'login': 'stranger'}, 'comments': 1},
            {'number': 3, 'user': {'login': 'raisingchris2026'}, 'comments': 1, 'pull_request': {}},
        ],
        'repos/me/r/issues/2/comments?per_page=100&page=1': [{'user': {'login': 'raisingchris2026'}}],
        'repos/me/r/issues/3/comments?per_page=100&page=1': [{'user': {'login': 'other'}}],
    }
    items = watch.repo_news('me/r', api=data.__getitem__)
    assert items == ['issue #1 by stranger: last word from stranger', 'PR #3 by raisingchris2026: last word from other']
