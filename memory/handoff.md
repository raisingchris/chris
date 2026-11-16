# Handoff, 2026-11-16 (~14:35 UTC).
done: #224, #7723 still 0 comments. Moving versions unchanged. Rechecked six label-only rows from their bytes (pytz, moment-tz, npm tzdata, tzinfo-data, PECL, PHP x4): all right. Stale: jiff-tzdb 0.1.10/1.0.0 ship 2026f, now on the page and repo (f18a48d). New skill php_tzdb.py (+2 tests). Commitments logged.
dates: Batch 4 checks 12-02, scored by 12-08. Sol 7 goes 11-17, Mary 2 goes 11-18 (copy both parents each). Monday watch includes #224, #7723.
blocked: push/deploy until a parent merges (0938). Polars draft HELD for parents. No new outside threads this week (2 of 3 used, I chose to stop).
lesson: the label rows were right, but a "latest" column goes stale on its own. Check the newest release, not just the bytes of the one I named.
next: byte-check the remaining label-only rows (joda-time 2.15.1 jar, NodaTime 3.3.7 nzd, Temurin tzdb.dat via java_tzdbver.py, Elixir tzdata) and recheck every "latest release" cell against its registry.
