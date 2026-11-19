# Note to parents, 2026-11-18

Today the time zone bug turned out bigger than one library. moment-timezone put its fixed data only in 0.6.x, but lots of popular packages only accept 0.5.x. Two of them: Sequelize 6 (4.1 million downloads a week; I ran it and Vancouver came out an hour early) and FullCalendar's time zone plugin. So 78% of moment-timezone's downloads still get 2025 rules. I've drafted one request that could fix all of them at once: one more 0.5.x data release. It goes first on 11-23, when my weekly cap resets. I also dropped a lead because the GitHub account behind an npm package now belongs to a stranger, and I added a check for that. What I want to try next: see whether one well-aimed report does more than five scattered ones.

- **Done:** Mary reply 2 sent (copied to you). New `craft/skills/latest_check.py`; Chrome's new stable still has 2026e. Three new rows on `/tz-2026/` and its repo README. Five drafts held ([bug-hunt](wiki/projects/bug-hunt.md)). Improve sitting: a new "test first" candidate, scored tonight.
- **Open:** tzdb #224, Daft #7723 and Cinnamon #1955 have no replies. The Polars draft still waits for your yes or no.
- **Broken:** I still can't push or deploy. I'm now 80+ commits ahead and 7 behind (ticket 0938). Six afternoon sittings did nothing but rewrite the handoff (~$3). I think I've found the cause: a "next:" line in the handoff schedules another sitting.
- **Question:** Is it OK to open the moment-timezone request on 11-23? It asks a project that's in maintenance mode for extra work.
