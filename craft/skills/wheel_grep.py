"""Which published releases of a pip package contain a file, or a text pattern?

The "when did this go away / arrive?" check, without installing anything:
download each version's wheel (no deps) and look inside the zip.

Usage:
  python -I wheel_grep.py --pkg ipykernel --versions 4.3.1,4.4.0 --pattern utils.warn
  python -I wheel_grep.py --pkg ipykernel --versions 6.31.0,7.0.0 --file ipykernel/serialize.py
  python -I wheel_grep.py --pkg tornado --versions 6.5 --regex 'EventLoopPolicy|iscoroutinefunction'
  options: --dir DIR (download cache; default ~/.cache/wheel_grep)

--pattern is plain text: 'A|B' looks for the three characters A, |, B.
For alternatives use --regex (2026-11-05: an 'A|B|C' --pattern sweep printed
0 for fifteen packages, including one known to match).

Each row says the version and either the matching .py files / True|False for
--file, or MISSING if no wheel could be fetched. A missing wheel is never shown
as "0 matches" (2026-10-30: a loop over wrong tag names printed 0 for every
tag and looked like a clean answer).
"""
from __future__ import annotations

import argparse
import re
import glob
import os
import subprocess
import sys
import zipfile
from typing import Callable, Optional

Fetch = Callable[[str, str, str], Optional[str]]  # (pkg, version, dir) -> wheel path or None


def fetch(pkg: str, version: str, root: str) -> Optional[str]:
    d = os.path.join(root, pkg, version)
    os.makedirs(d, exist_ok=True)
    found = glob.glob(os.path.join(d, '*.whl'))
    if not found:
        subprocess.run([sys.executable, '-m', 'pip', 'download', '-q', '--no-deps',
                        '--only-binary', ':all:', f'{pkg}=={version}', '-d', d],
                       capture_output=True, text=True)
        found = glob.glob(os.path.join(d, '*.whl'))
    return found[0] if found else None


def look(whl: str, file: Optional[str], pattern: Optional[str],
         regex: bool = False) -> str:
    z = zipfile.ZipFile(whl)
    names = z.namelist()
    if file:
        return str(file in names)
    if regex:
        rx = re.compile(pattern.encode())
        hits = [n for n in names if n.endswith('.py') and rx.search(z.read(n))]
    else:
        pat = pattern.encode()
        hits = [n for n in names if n.endswith('.py') and pat in z.read(n)]
    return f'{len(hits)} ' + ' '.join(hits)


def run(pkg, versions, file=None, pattern=None, root='.', fetcher: Fetch = fetch,
        regex=False):
    rows = []
    for v in versions:
        whl = fetcher(pkg, v, root)
        rows.append((v, look(whl, file, pattern, regex) if whl else 'MISSING'))
    return rows


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--pkg', required=True)
    p.add_argument('--versions', required=True)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--file')
    g.add_argument('--pattern', help='plain text, not a regex')
    g.add_argument('--regex', help='a Python regular expression')
    p.add_argument('--dir', default=os.path.expanduser('~/.cache/wheel_grep'))
    a = p.parse_args(argv)
    rows = run(a.pkg, [v.strip() for v in a.versions.split(',') if v.strip()],
               a.file, a.pattern or a.regex, a.dir, regex=bool(a.regex))
    for v, r in rows:
        print(f'{v}\t{r}')
    return 1 if any(r == 'MISSING' for _, r in rows) else 0


if __name__ == '__main__':
    sys.exit(main())
