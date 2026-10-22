import importlib.util
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location('release_bisect', Path(__file__).with_name('release_bisect.py'))
rb = importlib.util.module_from_spec(spec)
sys.modules['release_bisect'] = rb
spec.loader.exec_module(rb)

V = [f'1.{i}' for i in range(10)]


def fake(first_good: int, skip=()):
    calls = []

    def run(v):
        calls.append(v)
        i = V.index(v)
        if i in skip:
            return 125, 'pip failed'
        return (0, 'ok') if i >= first_good else (1, 'AssertionError')
    return run, calls


def test_bisect_finds_flip_with_few_runs():
    run, calls = fake(7)
    first, rows = rb.bisect(V, run)
    assert first == '1.7'
    assert len(calls) <= 6 and len(set(calls)) == len(calls)
    assert all(v in calls for v, _, _ in rows)


def test_bisect_no_flip():
    run, _ = fake(0)
    assert rb.bisect(V, run)[0] is None


def test_bisect_walks_past_skipped_midpoint():
    run, _ = fake(5, skip={4})
    assert rb.bisect(V, run)[0] == '1.5'


def test_bisect_flip_right_after_skip_region():
    run, _ = fake(4, skip={3})
    assert rb.bisect(V, run)[0] == '1.4'


def test_last_line_and_table():
    assert rb.last_line('a\n\n  KeyError: x  \n\n') == 'KeyError: x'
    assert rb.last_line('') == ''
    t = rb.table([('2.1.2', 1, 'KeyError'), ('2.1.3', 0, '[]')])
    assert '2.1.2' in t and 'KeyError' in t and t.splitlines()[0].startswith('version')


def test_disk_guard_refuses_and_skips(tmp_path):
    class U:
        def __init__(self, free): self.free = free
    assert rb.enough_disk(tmp_path / 'not' / 'yet', usage=lambda p: U(2e9))
    assert not rb.enough_disk(tmp_path, usage=lambda p: U(1e8))


def test_runner_skips_when_venv_cannot_be_built(tmp_path, monkeypatch):
    def boom(*a):
        raise RuntimeError('under 1.5 GB free')
    monkeypatch.setattr(rb, 'venv_python', boom)
    rc, line = rb.make_runner('x', tmp_path / 's.py', [], tmp_path, 5)('1.0')
    assert rc == 125 and 'GB free' in line


def test_runner_reports_timeout_and_rc(tmp_path, monkeypatch):
    monkeypatch.setattr(rb, 'venv_python', lambda *a: Path(sys.executable))
    s = tmp_path / 's.py'
    s.write_text('import sys, os; print(os.environ["TMPDIR"]); sys.exit(3)')
    rc, line = rb.make_runner('x', s, [], tmp_path, 30)('1.0')
    assert rc == 3 and 'rb-' in line
    s.write_text('import time; time.sleep(5)')
    assert rb.make_runner('x', s, [], tmp_path, 0.5)('1.0')[0] == 124
