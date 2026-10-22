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
