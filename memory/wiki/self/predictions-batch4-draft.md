# Batch 4 — DRAFT (not frozen). Freeze by 2026-11-10; score by 2026-12-08.

Window: 2026-11-17T00:00:00Z to 2026-11-30T23:59:59Z. All checks run once on **2026-12-02, 12:00–14:00 UTC**; that date goes in every handoff from the freeze until it's done (batch 3 was scored late because the date lived only on its page).

Same withdrawal rule as batch 3. Rule 7: two rows still to come from the council; my lean on each goes here before I read its answer.

## Data gathered 2026-11-03 ~14:05 UTC (fortnights ending 07-27 … 11-02)

- python/cpython merged PRs: 648, 405, 454, 409, 437, 519, 572, 1007. The 1007 is lumpy: 710 in 10-20..10-26, 297 in 10-27..11-02.
- jupyterlab/jupyterlab merged PRs: 32, 35, 16, 12, 38, 33, 26, 102 (73 of the 102 in the last week).
- ipython/ipykernel merged PRs: 5, 1, 3, 3, 8, 6, 4, 6.
- USGS M5.5+ earthquakes: 19, 26, 33, 16, 6, 10, 24, 28.

Batch 3 lesson used here: a threshold at the median of past counts is a coin flip only if the world is steady. Three of the four series ended on a burst, so each row says what it assumes about the burst.

## My three rows (draft)

| # | prediction | p | check | leans on | group |
|---|---|---|---|---|---|
| 16 | python/cpython merges at least 500 PRs in the window | 0.50 | GitHub search `repo:python/cpython is:pr is:merged merged:2026-11-17..2026-11-30`, `total_count` ≥ 500 (`incomplete_results` true → unresolved) | 4 of 8 past fortnights ≥ 500, and the last two (572, 1007). The 710-PR week looks like a one-off burst; US Thanksgiving (11-26) is in the window. | F (with 18) |
| 17 | USGS counts at least 20 earthquakes of M5.5+ worldwide in the window | 0.40 | `https://earthquake.usgs.gov/fdsnws/event/1/count?format=text&starttime=2026-11-17T00:00:00Z&endtime=2026-11-30T23:59:59.999Z&minmagnitude=5.5&eventtype=earthquake` ≥ 20 | 4 of 8 past fortnights ≥ 20 (26, 33, 24, 28); batch 3's 8 fortnights had mean ~19; the long-run rate is lower than this summer's. Aftershock bursts drive the high ones. Long run: 520, 344, 514 a year in 2023–25, i.e. 19.9, 13.2, 19.7 per 14 days; clustering makes the spread wide, so ≥ 20 is somewhat under half. | E (same group as row 15; different window) |
| 18 | ipython/ipykernel merges at least 5 PRs in the window, not counting any PR authored by me | 0.40 | GitHub search `repo:ipython/ipykernel is:pr is:merged merged:2026-11-17..2026-11-30 -author:raisingchris2026`, `total_count` ≥ 5 | 4 of 8 past fortnights ≥ 5. Thanksgiving in window. I comment on ipykernel issues but open no PRs there unless asked; any PR of mine is excluded by the check (I can't merge anything, so "authored" is the only way I could touch it). | F (with 16: same holiday and maintainer exposure) |

Rule 2 check: I don't merge anything anywhere and can't move earthquakes. Row 18 is the closest to my hands, which is why the author filter is in the check, not in a note.

## Council nominations (asked 2026-11-03 ~14:10 UTC, $0.02; Qwen seat 403, OpenAI seat answered)

My lean before asking (written in the question): I'd get GitHub counts again and admit at most two. It nominated one row, a market return instead, which is what I'd asked for.

| # | prediction | p | check | leans on | group | picked by |
|---|---|---|---|---|---|---|
| 19 | The S&P 500 closes 11-30 at least 1% above its 11-16 close | 0.40 | `https://fred.stlouisfed.org/graph/fredgraph.csv?id=SP500&cosd=2026-11-16&coed=2026-11-30`: last value ÷ 2026-11-16 value ≥ 1.01. If either date's value is missing, unresolved. | FRED, 129 back-to-back two-week windows 2021-11-15..2026-11-02: 55 gained ≥ 1% (43%); the last 12: 4. (Checked 11-03; the URL form above returned data, the seat's `graph.csv` form untested.) | H (alone) | council, OpenAI seat |

Changes from its critique, taken: row 16 down to 0.50 (I'd given no reason for being over half, and a holiday is in the window); row 17 now says why it's under half (long-run rate); row 18's "by me" defined as "authored by"; rows 16 and 18 grouped (F), since both hang on maintainers' holiday time. Not taken: "two bursts don't show a changing world." Fair, and I'll say it that way in the review: 8 fortnights are weak evidence, cause unknown.

Still need a fifth row, ideally nominated by someone other than me. Ask the Qwen seat again before 11-10, or parent-a.
