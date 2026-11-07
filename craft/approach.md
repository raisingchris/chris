# How I work on a bug

Seeded 2026-10-21 by my parents from my own lessons (`memory/wiki/lessons/`). It's mine to change, through an improve sitting and the eval.

1. Is anyone home? Check the project is alive, read every file it writes for agents (`agent_rules.py`: AGENTS.md, CLAUDE.md, CONTRIBUTING, AI policy) and ask who has to answer for the work, and search open PRs that mention the issue number.
2. Reproduce first. Install the project in a scratch folder at the reported version, and write the smallest script that fails while the bug is there. Run it; don't reason about it.
3. Find the cause by running things: bisect versions, diff released packages, print the value at the line. Search upstream for the identifier before writing "here's why".
4. Fix the smallest thing. Run the project's own tests with its own settings (`addopts` from `pyproject.toml`).
5. Check the result where it runs and for the person who'll use it: would this actually work for them, and what will it cost them to read?
6. Then post or open the PR, saying what I ran and what I changed from the defaults.

## When the job is a fix (the eval)

No network, no PR, nobody to answer questions, so steps 1 and 6 don't apply. About 80 turns and $3: grep and read ranges, not whole files. The grade is the project's own tests for this issue, which I never see, plus the tests around them. They test the feature the way its maintainers would, not just the reporter's one line.

1. Read the issue for the behaviour wanted. Grep for the code and for its existing tests (`grep -rn <name> <tests dir>`). Read those tests: the hidden ones are probably edits of them, same file, same helpers, same output format. Note any XFAIL, skip or "not implemented" case beside them, and if the issue names the change that broke it, `git show` that commit.
2. Run the reporter's case from a file in the repo and watch it fail. Print the module's `__file__` once (must be in the checkout).
3. Find the cause, not the symptom. Follow the value all the way to what the user sees (rendered output, repr, return value). List every path into the same feature (class and function, Dataset and DataArray, drop=True and False, public callers like `solveset` over `nthroot_mod`) and make them all agree.
4. Add a test in their style beside the existing ones. Run it, then the whole test file of each module I touched, in the foreground with the exit code kept: `timeout 900 python -m pytest -q -x <file> -p no:cacheprovider 2>&1 | tail -25; echo rc=${PIPESTATUS[0]}`. Too slow: split with `-k`, never background it. A failure: undo my change (`git diff > /tmp/f.patch; patch -R -p1 < /tmp/f.patch`), rerun, reapply, to see if it failed before me.
5. Finish. Never end on "shall I go on?": nobody will answer. Leave the fix in the tree, `git status` showing only source and test files, and say in one line what's still unchecked. If that line names a broken case of the same feature ("not addressed", "was broken before me", "tests may expect otherwise"), it isn't a note, it's the next fix: go back to step 3 for it. Leave it only if fixing it breaks an existing test.
