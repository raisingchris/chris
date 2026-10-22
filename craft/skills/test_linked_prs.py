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
    assert rows[0][:5] == ['o/r', '1', '1', 'open', '1']
    assert rows[1][:5] == ['o/r', '2', '0', '', '0']
    assert rows[1][-1] == 'title two'


def test_single_mode_says_zero(monkeypatch, capsys):
    monkeypatch.setattr(lp, 'gh_search', lambda q: [])
    monkeypatch.setattr(lp.linked_prs, '__defaults__', (lp.gh_search,))
    assert lp.main(['o/r', '42']) == 0
    assert capsys.readouterr().out.strip() == '0 PR(s) in o/r name #42'


def test_merged_is_not_just_closed():
    items = [{'title': 'fix #7', 'body': '', 'state': 'closed', 'pull_request': {'merged_at': '2026-08-05T07:53:08Z'}},
             {'title': 'try #7', 'body': '', 'state': 'closed', 'pull_request': {'merged_at': None}}]
    assert [lp.state(i) for i in lp.linked_prs('o/r', 7, fake(items))] == ['merged', 'closed']


def test_fixes_versus_mentions():
    # ipykernel #781: "possibly related to #775 and #319" fixed a different path.
    said = {
        'Fixes #319.': 'fixes',
        'closes: #319': 'fixes',
        'This RESOLVED #319': 'fixes',
        'This is designed to fix #780 and is possibly related to #775 and #319.': 'mentions',
        'Fix kernel restart (#319)': 'mentions',
        'fixes #3190': 'mentions',
        'fixes other/repo#319': 'mentions',
        'prefixes #319': 'mentions',
    }
    for body, want in said.items():
        assert lp.claim({'title': '', 'body': body}, 319) == want, body


def test_other_repo_refs_and_bots_do_not_count():
    items = [
        {'title': 'Bump actions', 'body': '<a href="https://github.com/actions/upload-artifact/pull/744">actions/upload-artifact#744</a>', 'state': 'closed'},
        {'title': 'Bump pip', 'body': '(<a href="https://github.com/jupyterlab/language-packs/issues/744">#744</a>)', 'state': 'closed'},
        {'title': 'Bump deps', 'body': 'Fixes #744', 'state': 'closed', 'user': {'login': 'dependabot[bot]', 'type': 'Bot'}},
        {'title': 'Copilot fix', 'body': 'Fixes #744', 'state': 'closed', 'user': {'login': 'Copilot', 'type': 'Bot'}},
        {'title': 'Fix kernel restart (#744)', 'body': '', 'state': 'closed', 'user': {'type': 'User'}},
    ]
    assert [i['title'] for i in lp.linked_prs('o/r', 744, fake(items))] == ['Copilot fix', 'Fix kernel restart (#744)']
