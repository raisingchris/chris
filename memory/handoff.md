# Handoff, 2026-11-20 sitting 4
done: Twenty draft settled. node-ical 0.27.6 uses Node's own Intl tz data (ran on Node 20/2024b: all five zones wrong); Twenty runs Node 26.13.1 = 2026e, so 0.27 would leave Havana wrong. Draft now says `yarn up -R moment-timezone` (0.6.6, 2026f) is the fix; repro `memory/inbox/work/twenty/run-0.27.js`.
choose for the 11-23 week (max 3): moment-tz, Rocket.Chat, Appsmith, Twenty. Lean: Twenty over Appsmith (stored data, one-line fix). Decide 11-23 after step_zero.
dates: Sol 8 on 11-21, Kathy 2 on 11-22, Mary 3 11-23+. Batch 4 checks 12-02, scored by 12-08.
blocked: push/deploy (ticket 0938); Polars draft held for parents; Moltbook unclaimed.
next: a /tz-2026/ line on node-ical: 0.21–0.26 carry their moment-timezone's data, 0.27+ follow Node's (check which version switched, via npm view deps per version), then update page + repo README (fetch live first, diff, PUT).
