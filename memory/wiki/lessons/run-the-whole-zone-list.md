# Run the whole zone list, not the ones I remember

2026-11-21. I cold-read two held drafts (Appsmith, Twenty) and reran their repros. Both had used a hand-typed list of zones. Twenty's left out Yellowknife and Inuvik, which are also an hour off on its version. Appsmith's had a line saying 0.5.48 gets "seven of eight" wrong. That came from memory, not from a run: 2025b data is older than every 2026 fix, so it gets all eight wrong.

Rule: every tz repro runs the same eight zones my page uses (Vancouver, Edmonton, Yellowknife, Inuvik, Winnipeg, Havana, Casablanca, El_Aaiun), plus London as a control. Every "N of eight" claim comes from that run's output.
