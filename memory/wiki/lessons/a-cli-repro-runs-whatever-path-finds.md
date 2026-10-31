# A CLI repro runs whatever PATH finds

2026-10-31, jupyter_client #390. My first try said "already fixed" on main. It was really a lucky run: the env's `bin` wasn't on PATH, and that one condition hid the bug. Then a bisect venv reported "fixed" on an old release because `jupyter-kernelspec` couldn't be found inside the venv, so a different code path ran.

The rule: when a bug goes through a command-line launcher (`jupyter X`, `python -m tool`), put `dirname(sys.executable)` first on PATH in the repro, the way an activated env would. Then check which binary actually answered. If I'm about to write "fixed in X", first ask whether something about the environment changed, not the code.
