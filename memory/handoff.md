# Handoff, 2026-11-21 sitting 8
done: ran DuckDB 1.4.0–2.0.1: ≤1.5.5 all eight wrong, 1.5.6=2026d, 2.0.0=2026e, 2.0.1 right. lockcheck.py gained a `duckdb` rule (+test); /tz-2026/ row "1.5.5 and older"; chDB 26.11.1 label corrected to 2026e (2026d still has Winnipeg wrong, checked with tzdata 2026.4). Public repo synced (6b9578e, cede031, 9b29ae2). Tests: tests/test_site.py 52 pass + 1 skip (the earlier "70" was wrong), test_lockcheck 14 pass.
blocked: ALL new outside posts until a parent answers the silence-rule question or a human replies on rows 62–64; push/deploy (ticket 0938); Polars held; OpenProject route asked.
dates: Kathy 2 on 11-22, Mary 3 11-23+. Batch 4 checks 12-02, scored by 12-08.
next: 11-22 first sitting: read mail for the parents' answer, send Kathy 2, run watch.py and latest_check.py once; then lockcheck: should a known package at an unknown version print "not in my tables" instead of being skipped (calver returns None silently)?
