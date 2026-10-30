import pathlib
import sys
import zipfile

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import wheel_grep as wg  # noqa: E402


def make_wheel(path, files):
    with zipfile.ZipFile(path, 'w') as z:
        for name, text in files.items():
            z.writestr(name, text)
    return str(path)


def test_pattern_counts_and_missing_is_loud(tmp_path):
    old = make_wheel(tmp_path / 'a.whl', {'pk/x.py': 'from IPython.utils.warn import warn', 'pk/y.py': 'pass'})
    new = make_wheel(tmp_path / 'b.whl', {'pk/x.py': 'import warnings'})
    wheels = {'1.0': old, '2.0': new}
    rows = wg.run('pk', ['1.0', '2.0', '9.9'], pattern='utils.warn',
                  fetcher=lambda p, v, d: wheels.get(v))
    assert rows == [('1.0', '1 pk/x.py'), ('2.0', '0 '), ('9.9', 'MISSING')]


def test_file_presence(tmp_path):
    w = make_wheel(tmp_path / 'a.whl', {'pk/serialize.py': ''})
    assert wg.run('pk', ['1'], file='pk/serialize.py', fetcher=lambda *a: w) == [('1', 'True')]
    assert wg.run('pk', ['1'], file='pk/gone.py', fetcher=lambda *a: w) == [('1', 'False')]


def test_main_exit_code_flags_missing(monkeypatch, capsys):
    monkeypatch.setattr(wg, 'fetch', lambda *a: None)
    monkeypatch.setattr(wg.run, '__defaults__', (None, None, '.', wg.fetch))
    assert wg.main(['--pkg', 'pk', '--versions', '1', '--file', 'x']) == 1
    assert 'MISSING' in capsys.readouterr().out
