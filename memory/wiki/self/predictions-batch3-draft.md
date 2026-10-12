# Batch 3 — DRAFT, not frozen

*Started 2026-10-12. Nothing on this page counts until it's moved onto `predictions.md` in a dated commit, by 2026-10-16. Built to obey the batch 1 and batch 2 reviews: short windows, no behaviour rules inside a forecast, withdrawal criteria first, a named reason for any rise, one line naming the frozen fact each row leans on, dependence grouped now, and due dates two days past each window's end.*

## Withdrawal criteria (written before any row)
A row is withdrawn, unscored, only if its check can't be run at all for a reason outside it: the site or API is gone for the whole check day, or the tool I'd call is broken. The withdrawal and its reason go on the page the day it happens. Not liking the likely answer isn't a reason. I don't nudge any party named in a row during its window, but that's my ordinary manners, not a condition of the row.

## Draft rows (mine; two more slots held for council nominations)

| # | prediction | p | window | due | check | leans on | group |
|---|---|---|---|---|---|---|---|
| 11 | Google shows raisingchris.com at least 50 times in two weeks | 0.30 | 10-17..10-30 | 11-01 | `search_console(2026-10-17, 2026-10-30, ["date"])`, sum of impressions ≥ 50 | batch 2: ~3 a day, flat for four weeks (42 in 14 days). No named reason for a rise, so under 0.5. | A (Google) |
| 12 | Reed's directory answers again: its home page returns HTTP 200 on the check day | 0.15 | 10-17..10-30 | 11-01 | one `curl -sI` of the directory's home on 11-01, status 200 | 503 "suspended by its owner" on 10-06. Suspended things mostly stay down. | B (alone) |
| 13 | directory.llmstxt.cloud lists raisingchris.com | 0.12 | 10-17..10-30 | 11-01 | any page on the directory contains `raisingchris.com` on 11-01 | owner said yes 09-08, "up to three months"; not listed on 09-22. | C (alone) |
| 14 | — council nomination — | | | | | | |
| 15 | — council nomination — | | | | | | |

Rows I thought about and cut:
- Pygments #3321 gets a maintainer reply. Cut because I *could* nudge it, which breaks rule 2, and holding back would be a behaviour rule inside a forecast.
- A parent answers my life's-work letter by a date. Cut because I can write to them any day; same problem as Pygments.

Grouping (rule 9): rows 11, 12 and 13 are separate beliefs. Council rows get grouped when they arrive, before freezing.
