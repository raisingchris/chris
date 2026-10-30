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
    assert 'latest release: v7.[redacted]' in lines
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
    lines, stop = sz.check('ipython/ipython', 5, api, no_prs, now=NOW, pypi_name='ipython',
                           pypi=lambda n: asked.append(n) or '9.17.1')
    rel = [l for l in lines if l.startswith('latest release')][0]
    assert 'WARNING' in rel and '7.18.1' in rel
    assert asked == ['ipython'] and lines[-1] == 'pypi ipython: 9.17.1'
    assert stop == []  # an old release is a warning, not a reason to stop


def test_usage():
    assert sz.main(['nonsense']) == 2
