---
id: 20260913T1251-upwork-bridge-says-temporarily-unavailab
title: Upwork bridge says "temporarily unavailable" on every call since ~13:20 (direct
  client works); and the Connects decision for two draft proposals
status: open
opened: '2026-09-13T12:51:03-04:00'
by: chris
---

Two things, one only you can fix and one only you can decide.

**1. The bridge is down.** `upwork_read search` and `upwork_prepare proposal` have returned "Upwork is temporarily unavailable" / "Could not queue the draft" on every call since about 13:20 New York today. `upwork_read status` at 12:40 was fine (connected, empty outbox). The direct client (`memory/inbox/.upwork-direct/client.py`) works at the same moment, so Upwork itself is up. Possible cause on my side: I fetched ~90 job records in a few minutes and Upwork rate-limited the last six ("SENSITIVE_RATE_LIMIT_EXCEEDED, wait about 5 seconds"); the bridge may share that limit or have cached the failure. Possible cause on yours: the account switch this morning (the bridge's old work_ refs are gone; the morning's draft vanished from the outbox as expected). I'll retry at 15:00. If it's still down then, it's yours.

**2. Connects.** Balance is 0. My shortlist is in `memory/inbox/work/shortlist-2026-09-13.md` (private, quotes clients). Two draft proposals I'd actually send are in `memory/inbox/work/drafts-2026-09-13.md`: a $25 ten-page Shopify test (14 Connects, client with 135 hires) and a $150 product spreadsheet (9 Connects, new client, scope to confirm first). 23 Connects total ≈ $3.45; Upwork sells 20 for ~$3 and 40 for ~$6. That's your money and your call. If yes: buy, and either paste the drafts into the review dashboard yourselves or tell me the bridge is back and I'll queue them. If no: also fine — the shortlist still taught me what the market looks like.

Not asked here: nothing about the account owner. I read the client's code before running it (it only talks to mcp.upwork.com and Upwork's token endpoint, prints no credentials) and I've called only `find_jobs` and `get_tool_help`.

## Parent update — 2026-09-13

The bridge is repaired. A parent-side verification run created the reference file with the wrong owner, preventing the service from reading it. Ownership is corrected, and both `upwork_read` and `upwork_prepare` passed checks under the service user. The verification draft was removed; nothing was submitted.

Private feedback on the two proposals is in the inbox. The Connects funding decision remains pending, so this ticket stays open. The Shopify application page currently shows "Buy Connects to apply" with a zero balance. The actual checkout's smallest one-off bundle is **100 Connects for USD 15 plus tax**; it does not offer the quoted 20- or 40-Connects bundles. The two bids would consume 23 and leave 77. No purchase or proposal submission has been authorized by this review.
