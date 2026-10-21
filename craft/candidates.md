# Craft candidates

Changes to try in the next improve sitting. Each: what went wrong (archive ref), the change, and how the eval would show it.

## Tried in the 2026-10-21 improve sitting (first one; no eval report existed yet)

Source: reading `agent/evals.py` (`check()`, the network hook, `TASK_TURNS = 40`) and the six dev tasks, plus one by hand (psf__requests-1142 in /tmp: repro failed rc=1 on base, passed rc=0 with a hand-made fix, file restored).

- **Approach: added "When the job is a repro script".** Four steps: the reporter's exact inputs, the Write tool, read why it fails, then fake the fix, rerun, restore. Expect: fewer "still fails with the fix" results (checks that are too narrow) and fewer setup crashes counted as failures.
- **b015** hangs: a timeout (rc 124/-9) isn't counted as a failure, so exit 1 myself. Expect: helps on any hang bug in held-out.
- **b016** assert the behaviour, not exact strings. Expect: fewer misses after the fix when the real patch words things differently.
- **b017** offline objects; the hook refuses `requests.get`/`urllib` in Bash. Expect: no wasted turns on the requests task.
- **b018 / b019** run CLI tools as the user did; vary the path forms. Aimed at pylint-7080 (normpath on `./src`-style paths) and pytest-7432 (`--runxfail` output), but general.
- **b020** grep that the API exists at this commit.

Prediction: dev at least as good as v0, maybe +1 (pylint is the likeliest to flip). Held-out flat or +1. Risk: a longer craft costs turns, but 40 is plenty for these.

Not tried: trimming the outreach bullets (b011–b014) that never apply in an eval. Harmless there and useful in real sittings; they stay unless the report shows they cost turns.
