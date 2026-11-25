---
id: 20261125T0908-deploy-gate-my-suite-passed-at-580-s-of
title: 'Deploy gate: my suite passed at ~580 s of the 600 s limit. Room to grow? (raise
  TEST_TIMEOUT_S or add pytest-xdist)'
status: open
opened: '2026-11-25T09:08:19-05:00'
by: chris
---

2026-11-25: deploy said "tests timed out after 600s". Timed with --durations, the suite took 889 s on this box. What I fixed myself (all in tests/ and site/build.py, nothing protected):
- Six tests each built the whole real site (~150–190 s a build here). Now one shared session fixture, `real_site_out` in tests/conftest.py.
- The withheld-names regex gets a first-letter gate: 80 s → 43 s on the built site, 0 differences on 2,109 files and 1,560 name variants (tests/test_withheld_fast.py checks it against the old pattern).
- Two Moltbook tests no longer feed one 50,000-letter word into redaction (see ticket 20261125T0726 for the real cause).

Result: 881 passed in 600.9 s, then deploy passed and queued. That's about 20 s of margin, and every new page makes the build slower.

What's left and not mine: tests/test_evals.py setup takes ~105 s (protected), and the gate itself is in agent/deploy.py (protected). Either would help:
1. TEST_TIMEOUT_S = 1200 in agent/deploy.py, or
2. pytest-xdist in the image (Dockerfile) and `-n 4` in run_tests. 16 cores here and the suite uses one.

Also, ticket 0744 looks fixed from my side: /autonomous-ai-agents/ is live with the 11-24 table, and origin/main matches my HEAD. Close it if you agree.
