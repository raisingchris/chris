# evals/

Chris's eval: real bugs from SWE-bench Verified (see `agent/evals.py`).

- `dev.json`: a public view of the dev split: issue, repo, commit, environment and the names of the tests that must pass. Hers to read and practise on. The full tasks (real fix, hidden tests) are in the brain's state, so she can't learn the answers and dev keeps measuring. Results, with her diffs, come back in `craft/eval-report.md`.
- The held-out split lives only in the brain's state. She sees its pass count, never its tasks.

Since 2026-10-29 the tasks are `fix` tasks: SWE-bench Verified's "1-4 hours" and ">4 hours" bugs (plus the largest "15 min - 1 hour" ones) from projects with a pytest suite. Given the repo at `base_commit` in a ready venv and the issue text, she fixes the bug. The brain carries her source changes (not tests, `conftest.py` or test config) into a clean copy, applies the hidden `test_patch`, runs its test files as `chris`, and passes the task when every `fail_to_pass` test passes and no `pass_to_pass` test breaks.

Each fix task was validated on id1 with the grader's own code: at `base_commit` plus the hidden tests the `fail_to_pass` tests fail, and with the real fix they pass, twice. `pass_to_pass` keeps only the tests that passed at base and in both fixed runs, so a flaky or environment-broken test can't fail her.

The earlier `repro` tasks (write `repro.py` that fails before the fix and passes after) still run if a task says `"kind": "repro"`; they were retired when she scored 14 of 14.

This folder, `agent/evals.py` and `agent/craft.py` are deploy-protected: changing the grader needs a parent.
