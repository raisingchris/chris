# Handoff, 2026-11-20 sitting 3
done: lockcheck on 7 new apps. Ghost OK; Grafana/Directus/Strapi/Medusa none; Outline 0.5.48 via Sequelize but no named zone (not hit). **Twenty**: node-ical ^0.21 locks moment-timezone 0.6.2 (2026b), so CalDAV events in Edmonton/Winnipeg/Havana/Casablanca are stored an hour off. I ran it (repro `memory/inbox/work/twenty/run.js`); the fix is `yarn up -R moment-timezone`. Draft HELD, `memory/inbox/work/twenty/issue-caldav-mtz.md`.
choose for the 11-23 week (max 3): moment-tz, Rocket.Chat, Appsmith, Twenty. Twenty has the cheapest fix and corrupts stored data; maybe it should replace Appsmith. Decide on 11-23 after step_zero.
dates: Sol 8 on 11-21, Kathy 2 on 11-22, Mary 3 11-23+. Batch 4 checks 12-02, scored by 12-08.
blocked: push/deploy (ticket 0938); Polars draft held for parents; Moltbook unclaimed.
next: check whether node-ical 0.21→0.27 is breaking for Twenty's use (read its changelog; run parse-ical-event's calls on 0.27.6), so the draft can say which of the two fixes is the real choice.
