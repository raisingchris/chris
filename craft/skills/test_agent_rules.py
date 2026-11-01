import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import agent_rules as ar  # noqa: E402

MUSIC21_LINE = ('- AI Agents not for core dev are forbidden to make any PRs whose user '
                'commands do not explicitly mention `music21`.')


def fake(files):
    def fetch(url):
        for name, text in files.items():
            if url == f'https://raw.githubusercontent.com/o/r/HEAD/{name}':
                return text
        return None
    return fetch


def test_finds_agents_md_not_just_contributing():
    files = {'AGENTS.md': '# Rules\n\n' + MUSIC21_LINE + '\n', 'CONTRIBUTING.md': 'Be nice.\n'}
    found = ar.scan('o/r', fetch=fake(files))
    assert list(found) == ['AGENTS.md', 'CONTRIBUTING.md']
    out = ar.report(found)
    assert '    3: - AI Agents not for core dev are forbidden' in out


def test_accountability_words_hit():
    text = 'Bot contributions need a named human who takes legal responsibility.'
    assert ar.hits(text) == [(1, text)]


def test_plain_lines_do_not_hit():
    assert ar.hits('Run the tests with pytest.\nUse four spaces.') == []


def test_absence_is_not_permission():
    assert 'not permission' in ar.report({})


PALLETS = ('## AI-Generated Contributions\n\n'
           'AI-generated PRs and issues are closed on sight, without review or discussion.\n')


def test_org_files_are_read_and_marked():
    def fetch(url):
        if url == 'https://raw.githubusercontent.com/o/.github/HEAD/CONTRIBUTING.md':
            return PALLETS
        return None
    found = ar.scan_org('o/r', fetch=fetch)
    assert list(found) == ['org:CONTRIBUTING.md']
    assert 'closed on sight' in ar.report(found)


def test_ai_label_found_with_count():
    def api(path):
        if path.startswith('repos/o/r/labels'):
            return [{'name': 'rejected AI', 'description': 'untrustworthy AI origin'},
                    {'name': 'bug', 'description': "Something isn't working"},
                    {'name': 'docs', 'description': None}]
        if path.startswith('search/issues') and 'rejected%20AI' in path:
            return {'total_count': 390}
        return None
    labels = ar.ai_labels('o/r', api=api)
    assert labels == [('rejected AI', 'untrustworthy AI origin', 390)]
    assert '"rejected AI" (390 items)' in ar.report_labels(labels)


def test_no_ai_labels_said_plainly():
    assert 'none about AI' in ar.report_labels(ar.ai_labels('o/r', api=lambda p: []))
