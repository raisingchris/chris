import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import api_pr  # noqa: E402

BASE = 'a' * 40


class FakeGH:
    def __init__(self, compare_files=None, ahead_by=1):
        self.calls = []
        self.compare_files = compare_files
        self.ahead_by = ahead_by

    def __call__(self, args, payload):
        self.calls.append((args, payload))
        path = args[-1]
        if path == 'repos/up/proj':
            return {'default_branch': 'master'}
        if path.endswith('/git/ref/heads/master'):
            return {'object': {'sha': BASE}}
        if path.endswith(f'/git/commits/{BASE}'):
            return {'tree': {'sha': 'basetree'}}
        if path.endswith('/forks'):
            return {}
        if path.endswith('/git/blobs'):
            return {'sha': f'blob{len(self.calls)}'}
        if path.endswith('/git/trees'):
            return {'sha': 'newtree'}
        if path.endswith('/git/commits'):
            return {'sha': 'newchange'}
        if path.endswith('/git/refs'):
            return {}
        if '/compare/' in path:
            return {'ahead_by': self.ahead_by,
                    'files': [{'filename': f} for f in self.compare_files]}
        if path.endswith('/pulls'):
            return {'html_url': 'https://github.com/up/proj/pull/7'}
        raise AssertionError(path)


def make_clone(tmp_path):
    (tmp_path / 'pkg').mkdir()
    (tmp_path / 'pkg/a.py').write_text('x = 1\n')
    return tmp_path


def kwargs(tmp_path, fake, **extra):
    k = dict(clone=make_clone(tmp_path), upstream='up/proj', me='me', branch='fix-1',
             message='m', title='(AI) t', body='b', files=['pkg/a.py'], run=fake,
             head_sha=BASE, sleep=lambda s: None)
    k.update(extra)
    return k


def test_opens_pr_with_tree_on_upstream_head(tmp_path):
    fake = FakeGH(compare_files=['pkg/a.py'])
    url = api_pr.open_pr(**kwargs(tmp_path, fake))
    assert url == 'https://github.com/up/proj/pull/7'
    paths = [c[0][-1] for c in fake.calls]
    assert paths.index('repos/up/proj/forks') < paths.index('repos/me/proj/git/blobs')
    change = next(p for a, p in fake.calls if a[-1] == 'repos/me/proj/git/commits')
    assert change['parents'] == [BASE] and change['tree'] == 'newtree'
    pr = next(p for a, p in fake.calls if a[-1] == 'repos/up/proj/pulls')
    assert pr['head'] == 'me:fix-1' and pr['base'] == 'master'


def test_dry_run_stops_before_pull(tmp_path):
    fake = FakeGH(compare_files=['pkg/a.py'])
    out = api_pr.open_pr(**kwargs(tmp_path, fake, dry_run=True))
    assert 'not opened' in out
    assert not any(c[0][-1].endswith('/pulls') for c in fake.calls)


def test_refuses_stale_clone(tmp_path):
    fake = FakeGH(compare_files=['pkg/a.py'])
    with pytest.raises(SystemExit, match='re-clone'):
        api_pr.open_pr(**kwargs(tmp_path, fake, head_sha='b' * 40))
    assert not any(c[0][-1].endswith('/forks') for c in fake.calls)


def test_refuses_when_compare_shows_extra_files(tmp_path):
    fake = FakeGH(compare_files=['pkg/a.py', 'stray.py'])
    with pytest.raises(SystemExit, match='compare looks wrong'):
        api_pr.open_pr(**kwargs(tmp_path, fake))
    assert not any(c[0][-1].endswith('/pulls') for c in fake.calls)
