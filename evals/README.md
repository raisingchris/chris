# evals/

Chris's eval: real bugs from SWE-bench Verified, used as bug-reproduction tasks (see `agent/evals.py`).

- `dev.json`: the dev split. Hers to read and practise on. Results come back in full in `craft/eval-report.md`.
- The held-out split lives only in the brain's state. She sees its pass count, never its tasks.

Each task was validated on 2026-10-21: the project's own failing tests fail at `base_commit` and pass with the fix, and a reference `repro.py` written from the issue text alone fails before the fix and passes after it, offline.

Contract: given the repo at `base_commit` in a ready venv and the issue text, write `repro.py` in the repo root. It exits non-zero while the bug is present and 0 once it's fixed, with no network and no files outside the repo.

This folder, `agent/evals.py` and `agent/craft.py` are deploy-protected: changing the grader needs a parent.
