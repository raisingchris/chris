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


def test_symlink_is_followed():
    # pydantic/pydantic, 2026-11-04: CONTRIBUTING.md is a symlink, and the raw
    # URL returns only its target path. The AI policy lived in the target.
    files = {'CONTRIBUTING.md': 'docs/contributing.md',
             'docs/contributing.md': '# Contributing\n\n## AI policy\nWe welcome AI.\n'}
    found = ar.scan('o/r', fetch=fake(files))
    assert 'CONTRIBUTING.md -> docs/contributing.md' in found
    assert 'AI policy' in found['CONTRIBUTING.md -> docs/contributing.md']


def test_symlink_relative_to_its_folder():
    files = {'.github/CONTRIBUTING.md': '../docs/c.md', 'docs/c.md': 'No bots.\n'}
    found = ar.scan('o/r', fetch=fake(files))
    assert found == {'.github/CONTRIBUTING.md -> docs/c.md': 'No bots.\n'}


def test_one_line_prose_is_not_a_symlink():
    files = {'AGENTS.md': 'Read and follow CONTRIBUTING.md, in particular the tests.'}
    found = ar.scan('o/r', fetch=fake(files))
    assert list(found) == ['AGENTS.md']


def test_broken_symlink_is_said_plainly():
    files = {'CONTRIBUTING.md': 'docs/gone.md'}
    found = ar.scan('o/r', fetch=fake(files))
    assert 'CONTRIBUTING.md -> docs/gone.md (BROKEN LINK)' in found


def test_plural_humans_hit():
    # dask AGENTS.md line 457, missed 2026-11-04 because \bhuman\b skips "humans".
    text = 'other interactions with other humans.'
    assert ar.hits(text) == [(1, text)]
    assert ar.hits('You must never think or speak instead of the user in discussions')


def test_referenced_agent_skill_is_read():
    # dask: the "[unsupervised AI]" rule lives in a skill file AGENTS.md only names.
    files = {'AGENTS.md': 'follow the rules in the `open-pr` skill\n'
                          '(`.agents/skills/open-pr/SKILL.md`).\n',
             '.agents/skills/open-pr/SKILL.md': 'The PR title MUST start with `[unsupervised AI]`\n'}
    found = ar.scan('o/r', fetch=fake(files))
    assert 'ref: .agents/skills/open-pr/SKILL.md' in found
    assert 'unsupervised AI' in ar.report(found)


def test_unreadable_reference_is_named_not_dropped():
    # Klara on Moltbook, 2026-11-23: "a reference you cannot read is a gap with
    # a name, not an absence." Before this, a failed fetch of a named file vanished.
    files = {'AGENTS.md': 'See `.agents/skills/open-pr/SKILL.md` before any PR.\n'}
    found = ar.scan('o/r', fetch=fake(files))
    assert 'ref: .agents/skills/open-pr/SKILL.md (UNREAD)' in found
    assert 'UNREAD' in ar.report(found)


def test_markdown_link_to_policy_is_followed():
    files = {'CONTRIBUTING.md': 'Read our [AI policy](docs/ai-policy.md) first.\n',
             'docs/ai-policy.md': 'LLM-generated PRs are not accepted.\n'}
    found = ar.scan('o/r', fetch=fake(files))
    assert 'ref: docs/ai-policy.md' in found


def test_web_links_are_not_refs():
    files = {'CONTRIBUTING.md': 'See [agents](https://example.com/agents.md).\n'}
    found = ar.scan('o/r', fetch=fake(files))
    assert list(found) == ['CONTRIBUTING.md']
