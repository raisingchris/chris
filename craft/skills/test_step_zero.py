import pathlib
import subprocess
import sys

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


def test_clear_when_nothing_changed():
    lines, stop = sz.check('o/r', 5, make_api(), no_prs, expect_comments=2)
    assert stop == []
    assert lines[0] == 'o/r#5 open comments=2 labels=bug'
    assert 'last comment: bob 2020-01-02T00:00:00Z' in lines
    assert '0 PR(s) name #5' in lines
    assert lines[-1].startswith('latest release: v7.4.0')


def test_stops_on_drift_closed_and_my_own_comment():
    api = make_api(state='closed', n=3, logins=('alice', 'RaisingChris2026', 'bob'))
    _, stop = sz.check('o/r', 5, api, no_prs, expect_comments=2)
    assert any('closed' in s for s in stop)
    assert any('DRIFT' in s for s in stop)
    assert any('already commented' in s for s in stop)


def test_stops_on_open_fixing_pr_but_not_on_a_mention():
    pr = {'number': 9, 'title': 'x', 'body': 'Fixes #5', 'state': 'open', 'user': {'login': 'c'}}
    _, stop = sz.check('o/r', 5, make_api(), lambda q: [pr])
    assert stop == ['an open PR says it fixes this']
    mention = dict(pr, body='related to #5')
    _, stop = sz.check('o/r', 5, make_api(), lambda q: [mention])
    assert stop == []


def test_no_release_is_not_an_error():
    lines, _ = sz.check('o/r', 5, make_api(release=False), no_prs)
    assert lines[-1].startswith('latest release: none')


def test_usage():
    assert sz.main(['nonsense']) == 2
