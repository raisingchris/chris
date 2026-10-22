"""Run one repro script against several published releases of a pip package.

The "already fixed?" check: one venv per version (cached), the script run with
`python -I`, a fresh TMPDIR and a timeout, and a table of rc + last output line.
With --bisect the versions are taken as ordered oldest->newest and searched for
the first one whose exit code differs from the first version's (assumes one flip).

Usage:
  python -I release_bisect.py --pkg jupyterlab --versions 2.1.0,2.2.0,4.6.4 repro.py
  python -I release_bisect.py --pkg ipython --versions 9.14.0,9.15.0,9.16.0,9.17.0 --bisect repro.py
  options: --extra setuptools (more pip specs, comma-separated; old releases on 3.12
           need it for distutils), --cache DIR (default ~/.cache/release_bisect),
           --timeout SECONDS (default 120; a timeout counts as rc 124, b015),
           --python PATH (base interpreter; old releases may need 3.11 for `imp`).
The script should exit non-zero while the bug is there. Exit 0 = fixed.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable

Runner = Callable[[str], tuple[int, str]]  # version -> (rc, last line)


def last_line(text: str) -> str:
    lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
    return lines[-1][:160] if lines else ''


MIN_FREE = 1.5e9  # bytes. 2026-10-22: plain pip venvs filled the 7.8G root disk
                  # (I can't delete), so: uv with hardlinks, and refuse below this.


def enough_disk(path: Path, need: float = MIN_FREE, usage=shutil.disk_usage) -> bool:
    p = path
    while not p.exists():
        p = p.parent
    return usage(p).free >= need


def venv_python(cache: Path, pkg: str, version: str, extra: list[str], base: str = sys.executable) -> Path:
    tag = Path(base).name if base != sys.executable else 'default'
    d = cache / f'{pkg}-{version}' / f"{tag}-{'+'.join(extra) or 'plain'}"
    py = d / 'bin' / 'python'
    if not py.exists():
        if not enough_disk(cache):
            raise RuntimeError(f'under {MIN_FREE / 1e9:.1f} GB free near {cache}; not building a venv')
        uv = shutil.which('uv')
        if uv:  # hardlinks from uv's cache: a venv costs megabytes, not hundreds
            mk = [uv, 'venv', '-q', '--python', base, str(d)]
            inst = [uv, 'pip', 'install', '-q', '--link-mode', 'hardlink', '--python', str(py)]
        else:
            mk = [base, '-m', 'venv', str(d)]
            inst = [str(py), '-m', 'pip', 'install', '-q', '--no-cache-dir']
        r = subprocess.run(mk, capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(f'venv failed: {last_line(r.stderr)}')
        r = subprocess.run(inst + [f'{pkg}=={version}', *extra], capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(f'install {pkg}=={version} failed: {last_line(r.stderr)}')
    return py


def make_runner(pkg: str, script: Path, extra: list[str], cache: Path, timeout: float,
                base: str = sys.executable) -> Runner:
    def run(version: str) -> tuple[int, str]:
        try:
            py = venv_python(cache, pkg, version, extra, base)
        except RuntimeError as e:
            return 125, str(e)  # 125 = couldn't test (git bisect's "skip")
        env = dict(os.environ, TMPDIR=tempfile.mkdtemp(prefix='rb-'))
        try:
            r = subprocess.run([str(py), '-I', str(script)], capture_output=True, text=True,
                               timeout=timeout, env=env, cwd=env['TMPDIR'])
        except subprocess.TimeoutExpired:
            return 124, f'timeout after {timeout}s'
        return r.returncode, last_line(r.stdout + '\n' + r.stderr)
    return run


def run_all(versions: list[str], run: Runner) -> list[tuple[str, int, str]]:
    return [(v, *run(v)) for v in versions]


def bisect(versions: list[str], run: Runner) -> tuple[str | None, list[tuple[str, int, str]]]:
    """First version whose rc class (0 vs non-zero) differs from versions[0].
    Returns (version or None, every row actually run). Skips (125) are not used."""
    seen: dict[str, tuple[int, str]] = {}

    def ok(i: int) -> bool | None:
        v = versions[i]
        if v not in seen:
            seen[v] = run(v)
        rc = seen[v][0]
        return None if rc == 125 else rc == 0

    base = ok(0)
    if base is None or ok(len(versions) - 1) in (None, base):
        return None, [(v, *seen[v]) for v in versions if v in seen]
    lo, hi = 0, len(versions) - 1  # versions[lo] same as base, versions[hi] flipped
    while hi - lo > 1:
        mid = (lo + hi) // 2
        r = ok(mid)
        if r is None:  # can't test mid: fall back to a linear walk inside (lo, hi)
            for j in range(lo + 1, hi):
                rj = ok(j)
                if rj is not None and rj != base:
                    hi = j
                    break
                if rj == base:
                    lo = j
            break
        if r == base:
            lo = mid
        else:
            hi = mid
    return versions[hi], [(v, *seen[v]) for v in versions if v in seen]


def table(rows: list[tuple[str, int, str]]) -> str:
    w = max([len(v) for v, _, _ in rows] + [7])
    out = [f'{"version":<{w}}  rc   last line']
    for v, rc, line in rows:
        out.append(f'{v:<{w}}  {rc:<3}  {line}')
    return '\n'.join(out)


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--pkg', required=True)
    p.add_argument('--versions', required=True)
    p.add_argument('--extra', default='')
    p.add_argument('--cache', default=str(Path.home() / '.cache' / 'release_bisect'))
    p.add_argument('--timeout', type=float, default=120)
    p.add_argument('--bisect', action='store_true')
    p.add_argument('--python', default=sys.executable, help='base interpreter for the venvs')
    p.add_argument('script')
    a = p.parse_args(argv)
    versions = [v.strip() for v in a.versions.split(',') if v.strip()]
    extra = [e.strip() for e in a.extra.split(',') if e.strip()]
    run = make_runner(a.pkg, Path(a.script).resolve(), extra, Path(a.cache), a.timeout, a.python)
    if a.bisect:
        first, rows = bisect(versions, run)
        print(table(rows))
        print(f'first flip: {first}' if first else 'no flip found between first and last')
    else:
        print(table(run_all(versions, run)))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
