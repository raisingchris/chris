import pathlib
import subprocess
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import api_pr  # noqa: E402

BASE = 'a' * 40


class FakeGH:
    def __init__(self, compare_files=None, ahead_by=1, existing_tree=None):
        self.calls = []
        self.compare_files = compare_files
        self.ahead_by = ahead_by
        self.existing_tree = existing_tree  # None = branch not on the fork yet

    def __call__(self, args, payload):
        self.calls.append((args, payload))
        path = args[-1]
        if path.endswith('/git/ref/heads/fix-1'):
            if self.existing_tree is None:
                raise subprocess.CalledProcessError(1, 'gh')
            return {'object': {'sha': 'oldchange'}}
        if path.endswith('/git/commits/oldchange'):
            return {'tree': {'sha': self.existing_tree}}
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
            return {'sha': f'change{len(self.calls)}'}
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
    k = dict(clone=extra.get('clone') or make_clone(tmp_path), upstream='up/proj', me='me', branch='fix-1',
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


def test_first_files_get_their_own_earlier_change(tmp_path):
    clone = make_clone(tmp_path)
    (clone / 'tests').mkdir()
    (clone / 'tests/test_a.py').write_text('def test(): pass\n')
    fake = FakeGH(compare_files=['pkg/a.py', 'tests/test_a.py'], ahead_by=2)
    api_pr.open_pr(**kwargs(tmp_path, fake, clone=clone, files=['pkg/a.py', 'tests/test_a.py'],
                            first=['tests/test_a.py'], first_message='test first', draft=True))
    trees = [p for a, p in fake.calls if a[-1] == 'repos/me/proj/git/trees']
    assert [[i['path'] for i in t['tree']] for t in trees] == [['tests/test_a.py'], ['pkg/a.py']]
    assert trees[1]['base_tree'] == 'newtree'
    changes = [p for a, p in fake.calls if a[-1] == 'repos/me/proj/git/commits']
    assert changes[0]['message'] == 'test first' and changes[0]['parents'] == [BASE]
    assert changes[1]['message'] == 'm' and changes[1]['parents'][0].startswith('change')
    ref = next(p for a, p in fake.calls if a[-1] == 'repos/me/proj/git/refs')
    assert ref['sha'].startswith('change') and ref['sha'] != changes[1]['parents'][0]
    pr = next(p for a, p in fake.calls if a[-1] == 'repos/up/proj/pulls')
    assert pr['draft'] is True


def test_first_needs_ahead_by_two(tmp_path):
    clone = make_clone(tmp_path)
    (clone / 't.py').write_text('')
    fake = FakeGH(compare_files=['pkg/a.py', 't.py'], ahead_by=1)
    with pytest.raises(SystemExit, match='compare looks wrong'):
        api_pr.open_pr(**kwargs(tmp_path, fake, clone=clone, files=['pkg/a.py', 't.py'],
                                first=['t.py'], first_message='x'))


def test_reuses_branch_left_by_dry_run(tmp_path):
    # 2026-11-02: the dry run for jupyter_client #1150 made the branch, then the real
    # run died creating it again.
    fake = FakeGH(compare_files=['pkg/a.py'], existing_tree='newtree')
    url = api_pr.open_pr(**kwargs(tmp_path, fake))
    assert url.endswith('/pull/7')
    assert not any(c[0][-1] == 'repos/me/proj/git/refs' for c in fake.calls)


def test_refuses_existing_branch_with_other_content(tmp_path):
    fake = FakeGH(compare_files=['pkg/a.py'], existing_tree='othertree')
    with pytest.raises(SystemExit, match='already exists'):
        api_pr.open_pr(**kwargs(tmp_path, fake))
    assert not any(c[0][-1].endswith('/pulls') for c in fake.calls)
