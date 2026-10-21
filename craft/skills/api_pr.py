"""Open a pull request on someone else's GitHub project with no git writes.

My guard blocks git's write commands; ticket 20261020T1202 (parent-b, option 1)
sanctions this path instead: GitHub's API through `gh api`.

Usage:
  python -I api_pr.py --clone /tmp/proj --upstream owner/repo --me raisingchris2026 \
      --branch fix-123 --message "Fix the thing (fixes #123)" \
      --title "(AI) Fix the thing" --body-file /tmp/body.md [--dry-run] path/in/repo.py ...

Steps: check the clone's HEAD is upstream's default-branch head; fork; upload each
file as a blob; make a tree on the base tree; make the change object with upstream
head as parent; point a new branch at it; compare (must be 1 ahead, exactly these
files); then open the PR unless --dry-run. Prints the PR URL.
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

    tree_items = []
    for f in files:
        data = (clone / f).read_bytes()
        blob = run(['-X', 'POST', f'repos/{fork}/git/blobs'],
                   {'content': base64.b64encode(data).decode(), 'encoding': 'base64'})
        tree_items.append({'path': f, 'mode': '100644', 'type': 'blob', 'sha': blob['sha']})

    base_tree = run([f'repos/{fork}/git/commits/{base_sha}'], None)['tree']['sha']
    tree = run(['-X', 'POST', f'repos/{fork}/git/trees'],
               {'base_tree': base_tree, 'tree': tree_items})['sha']
    change = run(['-X', 'POST', f'repos/{fork}/git/commits'],
                 {'message': message, 'tree': tree, 'parents': [base_sha]})['sha']
    run(['-X', 'POST', f'repos/{fork}/git/refs'],
        {'ref': f'refs/heads/{branch}', 'sha': change})

    cmp = run([f'repos/{upstream}/compare/{base_branch}...{me}:{repo}:{branch}'], None)
    changed = sorted(x['filename'] for x in cmp['files'])
    if cmp['ahead_by'] != 1 or changed != sorted(files):
        raise SystemExit(f'compare looks wrong: ahead_by={cmp["ahead_by"]} files={changed}')
    if dry_run:
        return f'dry run: branch {fork}:{branch} ready, PR not opened'

    pr = run(['-X', 'POST', f'repos/{upstream}/pulls'],
             {'title': title, 'head': f'{me}:{branch}', 'base': base_branch, 'body': body})
    return pr['html_url']


def main(argv: list[str]) -> None:
    p = argparse.ArgumentParser()
    for name in ('--clone', '--upstream', '--me', '--branch', '--message', '--title',
                 '--body-file'):
        p.add_argument(name, required=True)
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('files', nargs='+')
    a = p.parse_args(argv)
    print(open_pr(clone=pathlib.Path(a.clone), upstream=a.upstream, me=a.me, branch=a.branch,
                  message=a.message, title=a.title,
                  body=pathlib.Path(a.body_file).read_text(), files=a.files,
                  dry_run=a.dry_run))


if __name__ == '__main__':
    main(sys.argv[1:])
