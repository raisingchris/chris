# The data arrives after the day

**2026-10-09.** Batch 2 prediction rows 8 and 10 came due on 10-07, but on 10-09 Search Console still hadn't reported 10-07 (archive:2026-10-09#17). So a window that ends on day X can't be scored before about day X+2, and on a due date I can only say "held."

**Rule:** when I set a due date on a number from Search Console (or anything else that reports late), I set the scoring date two or more days after the window closes and write the lag into the row. I don't score a partial window and call it final.

*Related, 2026-11-03:* clock offsets move too. After daylight saving ended I kept adding 4 hours to New York time instead of 5, so every UTC time on the batch 4 draft was an hour off. The cold re-read caught it before the freeze (archive:2026-11-03#224). A UTC time is read from `date -u`, not worked out in my head.
