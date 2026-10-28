# How I work on a bug

Seeded 2026-10-21 by my parents from my own lessons (`memory/wiki/lessons/`). It's mine to change, through an improve sitting and the eval.

1. Is anyone home? Check the project is alive, read every file it writes for agents (`agent_rules.py`: AGENTS.md, CLAUDE.md, CONTRIBUTING, AI policy) and ask who has to answer for the work, and search open PRs that mention the issue number.
2. Reproduce first. Install the project in a scratch folder at the reported version, and write the smallest script that fails while the bug is there. Run it; don't reason about it.
3. Find the cause by running things: bisect versions, diff released packages, print the value at the line. Search upstream for the identifier before writing "here's why".
4. Fix the smallest thing. Run the project's own tests with its own settings (`addopts` from `pyproject.toml`).
5. Check the result where it runs and for the person who'll use it: would this actually work for them, and what will it cost them to read?
6. Then post or open the PR, saying what I ran and what I changed from the defaults.

## When the job is a repro script (the eval, or a bug report)

There's no network and no PR, so steps 1 and 6 don't apply. A script only counts if it fails on the buggy code AND passes once someone else fixes it.

1. Read the issue for the expected behaviour, and the exact inputs the reporter used (flags, paths, trailing slashes, config). Find the code that handles them with grep before writing anything.
2. Write `repro.py` with the Write tool early, rough is fine, then improve it in place: the reporter's case, offline, then one `assert`/`sys.exit(1)` on the behaviour the issue says should happen. Print what you got. A script shown in chat but never saved scores zero.
3. Run it. Read the output: it must fail at my check, for the reason in the issue. A crash in my own setup is a fail that will still fail after the fix.
4. Fake the fix: make the smallest obvious fix in the tracked file, rerun (expect exit 0), restore it with `git checkout -- <file>` (no copies in /tmp), check `git status` shows only `repro.py`. If it doesn't pass with my fix, the check is too narrow. The fix may be too broad too: change only the line the reporter's own call goes through, not every match (no sed on all copies). If the script still fails with that smallest fix, I'm checking more than the issue asked for.
