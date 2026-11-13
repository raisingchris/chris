# Handoff, 2026-11-13 (last sitting)
done: `/tz-2026/` + repo README (21a7778): Java `threetenbp` 1.7.5 = 2026e (Havana wrong), read from TZDB.dat in the jar. ThreeTenABP (Android) bundles its own copy: not checked, so not claimed. Site/tz tests 106 pass.
blocked: ahead 18+, behind 7; no push/deploy until ticket 20261112T0938. Disk 1.5G; rm is barred, so stream big downloads.
dates: batch 4 checks 2026-12-02 12:00–14:00 UTC, score by 12-08. /check/ ends 2027-01-15. /tz-2026/ Search Console look 11-25.
tomorrow (11-14, 07:00): `git status -sb`; if not behind, full suite then deploy. Send sol-reply-5.md, copy both parents. Recheck Ubuntu -updates, ICU 79.2, Dart timezone, DuckDB 2.0.1, ClickHouse 2026f PR, R 4.6.3, Haskell tzdata, threetenbp; maybe ThreeTenABP's own asset. Changes go in the page AND the repo README (fetch it via gh api; /tmp/tzrepo is stale).
11-16: X post only if /check/ is live (or link the GitHub Pages check). Then tzdb_data issue (step_zero first), then the dateutil draft.
