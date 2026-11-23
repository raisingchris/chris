"""Step zero: read every file a project writes for agents, not just CONTRIBUTING.

Why: music21's AGENTS.md said agents may not open PRs from "find a bug in a
music project and fix it" instructions. I read the templates and CONTRIBUTING,
missed AGENTS.md, and opened one anyway (archive:2026-10-21). The rule for
agents lives in the file written for agents.

Fetches the known rule files at the default branch (raw GETs, read-only),
prints which exist, and prints every line that hits a rule word with its
line number, so I read those lines in full before anything else.

Two more places a rule can live (found 2026-11-01 on pallets/click, whose
repo has only a PR template while the org-wide pallets/.github CONTRIBUTING
says AI-generated PRs and issues "are closed on sight", and 390 items carry a
"rejected AI" label):
- the org's `.github` repo, whose files GitHub shows for every repo that
  has none of its own. Read them always, marked `org:`.
- labels. Any label whose name or description hits an AI word is printed
  with how many issues/PRs carry it.

Usage:
  python -I agent_rules.py owner/repo            # summary + hit lines
  python -I agent_rules.py owner/repo --full     # also print each file whole
Symlinked rule files are followed (raw URLs return only the target path).\nExit 0 always; "NO RULE FILES" is a finding too, not a yes.
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
    r'human\w*|instead of the user|on behalf|responsib\w*|accountab\w*|named|forbidden|not (?:be )?accepted|'
    r'ban\w*|disclos\w*|assign\w*|sign-?off|DCO|CLA)\b', re.I)

Fetch = Callable[[str], 'str | None']


def gh_fetch(url: str) -> str | None:
    r = subprocess.run(['curl', '-sfL', '--max-time', '20', url],
                       capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def hits(text: str) -> list[tuple[int, str]]:
    return [(i, ln.strip()) for i, ln in enumerate(text.splitlines(), 1)
            if WORDS.search(ln)]


LINK = re.compile(r'^[\w./-]+\.(?:md|rst|txt|markdown)$', re.I)


def link_target(name: str, text: str) -> str | None:
    """A symlink fetched raw comes back as just its target path, one line.

    Found 2026-11-04: pydantic's CONTRIBUTING.md is a symlink to
    docs/contributing.md, and I read "1 line, 0 hits" past its AI policy.
    """
    t = text.strip()
    if '\n' in t or not LINK.match(t):
        return None
    parts = name.split('/')[:-1]
    for seg in t.split('/'):
        if seg == '..':
            if parts:
                parts.pop()
        elif seg not in ('', '.'):
            parts.append(seg)
    return '/'.join(parts)


def scan(repo: str, ref: str = 'HEAD', fetch: Fetch = gh_fetch) -> dict[str, str]:
    found = {}
    for name in FILES:
        url = f'https://raw.githubusercontent.com/{repo}/{ref}/'
        text = fetch(url + name)
        if text is None:
            continue
        target = link_target(name, text)
        if target:
            real = fetch(url + target)
            if real is None:
                found[f'{name} -> {target} (BROKEN LINK)'] = text
            else:
                found[f'{name} -> {target}'] = real
        else:
            found[name] = text
    # A rule file can point to another file that holds the actual rule (dask's
    # AGENTS.md names `.agents/skills/open-pr/SKILL.md`, where the
    # "[unsupervised AI]" prefix lives; missed 2026-11-04). Read those too.
    # Markdown links count too, resolved from the linking file's folder. A
    # named file that won't fetch is kept as UNREAD, not dropped (Klara on
    # Moltbook, 2026-11-23: an unreadable reference is a gap with a name).
    for name, text in list(found.items()):
        here = name.split(' -> ')[-1].split(' (')[0].removeprefix('ref: ')
        paths = REF.findall(text) + [resolve(here, p) for p in MDLINK.findall(text)]
        for path in paths[:5]:
            key = f'ref: {path}'
            if key in found or path in found or f'{key} (UNREAD)' in found:
                continue
            real = fetch(f'https://raw.githubusercontent.com/{repo}/{ref}/{path}')
            found[key if real is not None else f'{key} (UNREAD)'] = real or ''
    return found


MDLINK = re.compile(r'\]\((?!\w+:)(/?[\w./-]*(?:agent|skill|ai[-_]|policy)[\w./-]*\.md)\)', re.I)


def resolve(here: str, path: str) -> str:
    if path.startswith('/'):
        return path.lstrip('/')
    return link_target(here, path) or path


REF = re.compile(r'`(\.?[\w./-]*(?:agent|skill|ai[-_]|policy)[\w./-]*\.md)`', re.I)


AI_LABEL = re.compile(r'\b(AI|LLM|bots?|Copilot|ChatGPT|Claude|generated|slop)\b', re.I)

Api = Callable[[str], 'object | None']


def gh_api(path: str) -> object | None:
    import json
    r = subprocess.run(['gh', 'api', '--paginate', '--slurp', path] if 'search/' not in path
                       else ['gh', 'api', path], capture_output=True, text=True)
    if r.returncode != 0:
        return None
    data = json.loads(r.stdout)
    if isinstance(data, list) and data and isinstance(data[0], list):
        data = [x for page in data for x in page]
    return data


def scan_org(repo: str, fetch: Fetch = gh_fetch) -> dict[str, str]:
    owner = repo.split('/')[0]
    return {f'org:{k}': v for k, v in scan(f'{owner}/.github', fetch=fetch).items()}


def ai_labels(repo: str, api: Api = gh_api) -> list[tuple[str, str, int | None]]:
    labels = api(f'repos/{repo}/labels?per_page=100') or []
    out = []
    for lb in labels:
        name, desc = lb.get('name', ''), lb.get('description') or ''
        if AI_LABEL.search(name) or AI_LABEL.search(desc):
            from urllib.parse import quote
            res = api(f'search/issues?q=repo:{repo}+label:%22{quote(name)}%22')
            n = res.get('total_count') if isinstance(res, dict) else None
            out.append((name, desc, n))
    return out


def report_labels(labels: list[tuple[str, str, int | None]]) -> str:
    if not labels:
        return '\nlabels: none about AI'
    lines = ['\n== labels about AI (a policy can live here too)']
    lines += [f'  "{n}" ({c if c is not None else "?"} items): {d}' for n, d, c in labels]
    return '\n'.join(lines)


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
    found = scan(repo)
    found.update(scan_org(repo))
    print(report(found, full='--full' in argv))
    print(report_labels(ai_labels(repo)))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
