"""Open a pull request on someone else's GitHub project with no git writes.

My guard blocks git's write commands; ticket 20261020T1202 (parent-b, option 1)
sanctions this path instead: GitHub's API through `gh api`.

Usage:
  python -I api_pr.py --clone /tmp/proj --upstream owner/repo --me raisingchris2026 \
      --branch fix-123 --message "Fix the thing (fixes #123)" \
      --title "(AI) Fix the thing" --body-file /tmp/body.md [--dry-run] path/in/repo.py ...
  options: --first tests/test_x.py --first-message "Add failing test" puts those files in
           their own change first (projects that want the test committed before the fix);
           --draft opens the PR as a draft (e.g. when no human reviewed the work).

Steps: check the clone's HEAD is upstream's default-branch head; fork; upload each
file as a blob; make a tree on the base tree; make the change object with upstream
head as parent; point a new branch at it; compare (must be 1 ahead, exactly these
files, or 2 ahead with --first); then open the PR unless --dry-run. Prints the PR URL.
"""
from __future__ import annotations

import argparse
import base64
import json
import pathlib
import subprocess
import sys
import time
from typing import Callable

Runner = Callable[[list[str], 'dict | None'], 'dict | list']


def gh(args: list[str], payload: dict | None = None) -> dict | list:
    """Run `gh api ...`, sending payload as JSON on stdin. Returns parsed JSON."""
    cmd = ['gh', 'api'] + args
    if payload is not None:
        cmd += ['--input', '-']
    out = subprocess.run(cmd, input=json.dumps(payload) if payload is not None else None,
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out) if out.strip() else {}


def clone_head(clone: pathlib.Path) -> str:
    return subprocess.run(['git', '-C', str(clone), 'rev-parse', 'HEAD'],
                          capture_output=True, text=True, check=True).stdout.strip()


def open_pr(*, clone: pathlib.Path, upstream: str, me: str, branch: str, message: str,
            title: str, body: str, files: list[str], dry_run: bool = False,
            run: Runner = gh, head_sha: str | None = None,
            first: list[str] | None = None, first_message: str = '', draft: bool = False,
            sleep: Callable[[float], None] = time.sleep) -> str:
    repo = upstream.split('/')[1]
    fork = f'{me}/{repo}'
    info = run([f'repos/{upstream}'], None)
    base_branch = info['default_branch']
    base_sha = run([f'repos/{upstream}/git/ref/heads/{base_branch}'], None)['object']['sha']
    local = head_sha if head_sha is not None else clone_head(clone)
    if local != base_sha:
        raise SystemExit(f'clone HEAD {local[:7]} != upstream {base_branch} {base_sha[:7]}; '
                         're-clone and re-test first')

    run(['-X', 'POST', f'repos/{upstream}/forks'], {'default_branch_only': True})
    for _ in range(10):  # forks are made asynchronously
        try:
            run([f'repos/{fork}/git/commits/{base_sha}'], None)
            break
        except subprocess.CalledProcessError:
            sleep(5)
    else:
        raise SystemExit('fork never got the upstream head')

    first = list(first or [])
    if any(f not in files for f in first):
        raise SystemExit('--first files must also be listed as files')
    if first and not first_message:
        raise SystemExit('--first needs --first-message')

    def blob_items(paths: list[str]) -> list[dict]:
        items = []
        for f in paths:
            data = (clone / f).read_bytes()
            blob = run(['-X', 'POST', f'repos/{fork}/git/blobs'],
                       {'content': base64.b64encode(data).decode(), 'encoding': 'base64'})
            items.append({'path': f, 'mode': '100644', 'type': 'blob', 'sha': blob['sha']})
        return items

    parent = base_sha
    tree = run([f'repos/{fork}/git/commits/{base_sha}'], None)['tree']['sha']
    steps = [(first, first_message), ([f for f in files if f not in first], message)]
    for paths, msg in steps:
        if not paths:
            continue
        tree = run(['-X', 'POST', f'repos/{fork}/git/trees'],
                   {'base_tree': tree, 'tree': blob_items(paths)})['sha']
        parent = run(['-X', 'POST', f'repos/{fork}/git/commits'],
                     {'message': msg, 'tree': tree, 'parents': [parent]})['sha']
    # A --dry-run leaves its branch behind. Reuse it only if it holds exactly this
    # tree; otherwise stop (never force-move a branch).
    try:
        existing = run([f'repos/{fork}/git/ref/heads/{branch}'], None)['object']['sha']
    except subprocess.CalledProcessError:
        existing = None
    if existing is None:
        run(['-X', 'POST', f'repos/{fork}/git/refs'],
            {'ref': f'refs/heads/{branch}', 'sha': parent})
    elif run([f'repos/{fork}/git/commits/{existing}'], None)['tree']['sha'] != tree:
        raise SystemExit(f'branch {branch} already exists on {fork} with other content; '
                         'pick a new --branch')
    want_ahead = sum(1 for paths, _ in steps if paths)

    cmp = run([f'repos/{upstream}/compare/{base_branch}...{me}:{repo}:{branch}'], None)
    changed = sorted(x['filename'] for x in cmp['files'])
    if cmp['ahead_by'] != want_ahead or changed != sorted(files):
        raise SystemExit(f'compare looks wrong: ahead_by={cmp["ahead_by"]} files={changed}')
    if dry_run:
        return f'dry run: branch {fork}:{branch} ready, PR not opened'

    pr = run(['-X', 'POST', f'repos/{upstream}/pulls'],
             {'title': title, 'head': f'{me}:{branch}', 'base': base_branch, 'body': body,
              'draft': draft})
    return pr['html_url']


def main(argv: list[str]) -> None:
    p = argparse.ArgumentParser()
    for name in ('--clone', '--upstream', '--me', '--branch', '--message', '--title',
                 '--body-file'):
        p.add_argument(name, required=True)
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--draft', action='store_true')
    p.add_argument('--first', action='append', default=[])
    p.add_argument('--first-message', default='')
    p.add_argument('files', nargs='+')
    a = p.parse_args(argv)
    print(open_pr(clone=pathlib.Path(a.clone), upstream=a.upstream, me=a.me, branch=a.branch,
                  message=a.message, title=a.title,
                  body=pathlib.Path(a.body_file).read_text(), files=a.files,
                  dry_run=a.dry_run, first=a.first, first_message=a.first_message,
                  draft=a.draft))


if __name__ == '__main__':
    main(sys.argv[1:])
