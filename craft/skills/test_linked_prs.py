import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import linked_prs as lp  # noqa: E402


def fake(items):
    return lambda q: items


def test_keeps_only_real_mentions():
    items = [
        {'title': 'Fix parser (#8705)', 'body': '', 'state': 'open'},
        {'title': 'Unrelated', 'body': 'see #87051', 'state': 'closed'},
        {'title': 'Other', 'body': 'Fixes #8705.', 'state': 'closed'},
        {'title': 'Mentions 8705 bare', 'body': None, 'state': 'open'},
    ]
    got = lp.linked_prs('o/r', 8705, fake(items))
    assert [i['title'] for i in got] == ['Fix parser (#8705)', 'Other']


def test_tsv_writes_count_and_states(tmp_path):
    src = tmp_path / 'in.tsv'
    dst = tmp_path / 'out.tsv'
    src.write_text('o/r\t1\t2026-10-01\ttitle one\no/r\t2\t2026-10-02\ttitle two\n')
    def search(q):
        return [{'title': 'fix #1', 'body': '', 'state': 'open'}] if q.endswith(' 1') else []
    lp.tsv(str(src), str(dst), search, pause=0)
    rows = [r.split('\t') for r in dst.read_text().splitlines()]
    assert rows[0][:4] == ['o/r', '1', '1', 'open']
    assert rows[1][:4] == ['o/r', '2', '0', '']
    assert rows[1][-1] == 'title two'


def test_single_mode_says_zero(monkeypatch, capsys):
    monkeypatch.setattr(lp, 'gh_search', lambda q: [])
    monkeypatch.setattr(lp.linked_prs, '__defaults__', (lp.gh_search,))
    assert lp.main(['o/r', '42']) == 0
    assert capsys.readouterr().out.strip() == '0 PR(s) in o/r name #42'
