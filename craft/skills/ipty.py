"""Type cells into a real terminal REPL (IPython by default) through a pty and get the transcript.

For prompt/terminal bugs that a plain `python -c` can't show (ipython #14959, #14641, #15420):
the bug lives in the prompt between cells, so the repro has to type like a person.
Pass/fail by a success marker, not by one error string: the same crash says different words
on different versions (#15420: 9.x "cannot be called from a running event loop", 8.17.2
"This event loop is already running"), so "no error string found" is not "fixed".

Usage:
  python -I ipty.py --python /path/to/venv/bin/python --marker 'ALIVE 42' \\
      "import x" "x.start()" "print('ALIVE', 6*7)"
  options: --repl "-m IPython --no-banner --colors=NoColor" (args after the interpreter),
           --wait SECONDS per cell (default 8), --home DIR (a fresh HOME so no profile leaks in).
Exit 0 if the marker appears in the transcript, 1 if not. The transcript's tail is printed.
"""
from __future__ import annotations

import argparse
import os
import pty
import select
import shlex
import sys
import time

DEFAULT_REPL = "-m IPython --no-banner --colors=NoColor"


def run(python: str, cells: list[str], repl: str = DEFAULT_REPL, wait: float = 8.0,
        start_wait: float = 5.0, env: dict | None = None) -> str:
    """Start `python <repl>` on a pty, type each cell + Enter, wait, then `exit`. Return all output."""
    argv = [python, *shlex.split(repl)]
    pid, fd = pty.fork()
    if pid == 0:  # child
        if env is not None:
            os.execve(python, argv, env)
        os.execv(python, argv)
    out = bytearray()

    def drain(seconds: float) -> None:
        end = time.time() + seconds
        while time.time() < end:
            r, _, _ = select.select([fd], [], [], 0.1)
            if not r:
                continue
            try:
                chunk = os.read(fd, 65536)
            except OSError:
                return
            if not chunk:
                return
            out.extend(chunk)

    try:
        drain(start_wait)
        for cell in cells:
            os.write(fd, cell.encode() + b"\r")
            drain(wait)
        os.write(fd, b"exit()\r")
        drain(1.5)
    finally:
        try:
            os.kill(pid, 9)
        except ProcessLookupError:
            pass
        try:
            os.waitpid(pid, 0)
        except ChildProcessError:
            pass
        os.close(fd)
    return out.decode("utf-8", "replace").replace("\r", "")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--python", default=sys.executable)
    ap.add_argument("--repl", default=DEFAULT_REPL)
    ap.add_argument("--marker", required=True)
    ap.add_argument("--wait", type=float, default=8.0)
    ap.add_argument("--home", default=None)
    ap.add_argument("cells", nargs="+")
    a = ap.parse_args(argv)
    env = None
    if a.home:
        os.makedirs(a.home, exist_ok=True)
        env = {**os.environ, "HOME": a.home}
    text = run(a.python, a.cells, a.repl, a.wait, env=env)
    print(text[-3000:])
    ok = a.marker in text
    print(f"\nmarker {a.marker!r} found={ok}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
