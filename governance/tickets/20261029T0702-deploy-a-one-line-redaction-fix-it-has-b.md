---
id: 20261029T0702-deploy-a-one-line-redaction-fix-it-has-b
title: 'Deploy a one-line redaction fix: it has been breaking evals/dev.json every
  sitting since 10-21 (blocks all my deploys)'
status: open
opened: '2026-10-29T07:02:58-04:00'
by: chris
---

What's wrong: the end-of-sitting content redaction runs over `evals/`. Inside `evals/dev.json` it reads `\r\[redacted]` as an e-mail address and a GCC build date as a phone number, and writes `[redacted]` over them. That breaks the JSON escapes. Since commit 25da914 (10-21 wake), `tests/test_evals.py::test_shipped_dev_tasks_parse_and_hold_no_held_out` fails on main, so any deploy of HEAD is refused. If HEAD were deployed anyway, the eval would crash. The running code (26ceb83) has a good copy, so last night's eval score is fine.

The fix (protected file, so it's yours): add `"evals"` to `CONTENT_EXCLUDE` in `agent/redaction.py`. It's public SWE-bench data, nothing about you. The push-time canary check in gitops still covers it. Test added in `tests/test_readiness.py::test_content_redaction_leaves_eval_json_parseable`: it fails without the fix and passes with it. Full suite with the fix and a restored dev.json: 734 passed, 2 skipped (10-29 morning sitting).

The catch: the running (old) redaction will break dev.json again in this sitting's own commit. So, after this sitting's commit:
1. Restore the file: `git show 8719452:evals/dev.json > evals/dev.json` and commit.
2. Deploy main. That also ships my backlog since 10-24 (Marco's corrected /agents/ row, commitments row 31).

After that I'll check from my side that dev.json still parses after the next sitting.

Also, the disk: it's at 31% used now and the shell works. Thank you. Tickets 0841, 0901 and 1005 can close. I couldn't delete my old /tmp venvs (the guard blocks rm -rf), so from now on I'll reuse one scratch folder.

*Chris, 2026-11-25 — looks resolved on my side, fine to close:* superseded: pushes and deploys work now (self-deploy 42ffbab green, 14:09 UTC).
