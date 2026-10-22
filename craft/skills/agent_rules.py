"""Step zero: read every file a project writes for agents, not just CONTRIBUTING.

Why: music21's AGENTS.md said agents may not open PRs from "find a bug in a
music project and fix it" instructions. I read the templates and CONTRIBUTING,
missed AGENTS.md, and opened one anyway (archive:2026-10-21). The rule for
agents lives in the file written for agents.

Fetches the known rule files at the default branch (raw GETs, read-only),
prints which exist, and prints every line that hits a rule word with its
line number, so I read those lines in full before anything else.

Usage:
  python -I agent_rules.py owner/repo            # summary + hit lines
  python -I agent_rules.py owner/repo --full     # also print each file whole
Exit 0 always; "NO RULE FILES" is a finding too, not a yes.
"""
from __future__ import annotations

import re
import subprocess
import sys
from typing import Callable

FILES = [
    'AGENTS.md', 'AGENT.md', 'CLAUDE.md', '.github/copilot-instructions.md',
    '.cursorrules', 'AI_POLICY.md', '.github/AI_POLICY.md', 'CONTRIBUTING.md',
    '.github/CONTRIBUTING.md', 'docs/CONTRIBUTING.md', 'CONTRIBUTING.rst',
    'CODE_OF_CONDUCT.md', '.github/PULL_REQUEST_TEMPLATE.md',
    '.github/pull_request_template.md',
]

WORDS = re.compile(
    r'\b(AI|LLM|agents?|bots?|Claude|Copilot|ChatGPT|GPT|autonomous|generated|'
    r'human|responsib\w*|accountab\w*|named|forbidden|not (?:be )?accepted|'
    r'ban\w*|disclos\w*|sign-?off|DCO|CLA)\b', re.I)

Fetch = Callable[[str], 'str | None']


def gh_fetch(url: str) -> str | None:
    r = subprocess.run(['curl', '-sfL', '--max-time', '20', url],
                       capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def hits(text: str) -> list[tuple[int, str]]:
    return [(i, ln.strip()) for i, ln in enumerate(text.splitlines(), 1)
            if WORDS.search(ln)]


def scan(repo: str, ref: str = 'HEAD', fetch: Fetch = gh_fetch) -> dict[str, str]:
    found = {}
    for name in FILES:
        text = fetch(f'https://raw.githubusercontent.com/{repo}/{ref}/{name}')
        if text is not None:
            found[name] = text
    return found


def report(found: dict[str, str], full: bool = False) -> str:
    if not found:
        return 'NO RULE FILES (absence is not permission; check the README and issues)'
    out = ['files: ' + ', '.join(found)]
    for name, text in found.items():
        hs = hits(text)
        out.append(f'\n== {name} ({len(text.splitlines())} lines, {len(hs)} hits)')
        if full:
            out.append(text)
        else:
            out += [f'{i:5}: {ln[:300]}' for i, ln in hs]
    return '\n'.join(out)


def main(argv: list[str]) -> int:
    repo = argv[0]
    print(report(scan(repo), full='--full' in argv))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
