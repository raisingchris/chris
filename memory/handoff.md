# Handoff, 2026-11-19 explore sitting
done: built `lockcheck.py` (lockfiles → which tz-data copy each package carries; tables read from the tarballs; 13 tests), live in tz-2026 repo (1f323e1, README 59fe22a) and on `/tz-2026/` at next deploy. On 13 big projects' lockfiles: 10 of 11 copies old (cal.com via ews-javascript-api, Budibase via snowflake-sdk, Rocket.Chat direct ^0.5.48, n8n, NocoDB, Appsmith; Twenty just a stale lock).
found: snowflake-sdk 3.4.1 (3.8M/wk) pins moment-timezone ^0.5.15 → TIMESTAMP_LTZ text an hour off; ran before/after. Draft HELD `work/snowflake/issue-mtz05.md` (+ sf_repro.js). @js-joda/timezone 2.x ends at 2026a (row added).
dates: Pickle 1 on 11-20, Sol 8 on 11-21 (copy both parents). From 11-23 (max 3 a week): moment-tz issue-05x, then snowflake, step_zero before each. Batch 4 checks 12-02, scored by 12-08.
blocked: push/deploy until a parent merges (ticket 0938); Polars draft held for parents; Moltbook unclaimed.
next: read eval-report.md; then, if food allows, check whether Rocket.Chat's direct ^0.5.48 reaches users (agenda/omnichannel), read-only, for a later draft.
