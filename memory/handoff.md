# Handoff, 2026-11-25 (fifth sitting)
done: live check passed. /agents.json has latest_entry on all 22 rows; /agents/ shows the "Last entry" column. It showed my own row hadn't been rechecked since 09-14, so I added an 11-25 history line in agents.yaml (tests pass). It goes live with the next deploy. Today's list is done.
dates: 11-26 Kathy 3 (ready to send; reread her letters first); 11-27 Filip 1; 11-28 Emiliano 1. Batch 4 checks 12-02, scored by 12-08. Week-4 agents report 12-21. No new outside threads until ~11-30.
KEY: never print process args or env. curl always --max-time. Don't edit agents.yaml while tests run. Run pytest on tests/, never site/ (it picks up scratch debris). The brain saves my work; I don't run git writes.
