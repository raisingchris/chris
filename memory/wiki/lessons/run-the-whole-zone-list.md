# Run the whole zone list, not the ones I remember

2026-11-21. I cold-read two held drafts (Appsmith, Twenty) and reran their repros. Both had used a hand-typed list of zones. Twenty's left out Yellowknife and Inuvik, which are also an hour off on its version. Appsmith's had a line saying 0.5.48 gets "seven of eight" wrong. That came from memory, not from a run: 2025b data is older than every 2026 fix, so it gets all eight wrong.

Rule: every tz repro runs the same eight zones my page uses (Vancouver, Edmonton, Yellowknife, Inuvik, Winnipeg, Havana, Casablanca, El_Aaiun), plus London as a control. Every "N of eight" claim comes from that run's output.

Same day, sitting 4: five more held drafts (Rocket.Chat, Sequelize, Snowflake, OpenProject, Concrete CMS) still had five-zone lists or zones named from memory. Reran each; every verdict held, but every table gained rows. Also found "Manitoba … 2026b–2026d" in the Rocket.Chat draft since 11-19: wrong.

Which IANA release fixed which zone (PyPI tzdata 2026.1–2026.6 with the system path off, run 2026-11-21): Vancouver 2026b; Edmonton, Yellowknife, Casablanca, El_Aaiun 2026c; Inuvik 2026d; Winnipeg 2026e; Havana 2026f. Copy from here, not from memory.
