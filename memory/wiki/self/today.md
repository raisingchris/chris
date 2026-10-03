# Today — 2026-10-03 (day twenty-eight)

1. **Read parent-a's unread mail first** ("Re: Chris — 2026-10-01", archive:2026-10-02#281).
2. **Dulcie.** Slow recheck: one GET, read the reply, then the next; stop at the first warning. If it passes Liha's checks, send and copy parent-b (commitments row 22). If Shopify still answers 429, don't send; say so.
3. **One letter to parents** covering: strangerloops.com (robots, then a proper read, then /agents/ or /doors/ or neither); the ten Shopify shops (country checked from search, not their servers); the US postal address and Canada's anti-spam law.
4. **Page-reviews tracker:** pick the next open "strongly" ask, ideally the one-source-per-changing-fact build change. Small and finished beats big and half-done.
5. Food guard under $8. Short sittings when mail is only job alerts.

## Carry
- Odometer 5/40. Reed card before 10-22. X 1/7.
- Tickets open: `20260920T1301`, `20260926T0916`.
- Value 6: comments close 10-05, goes to parents 10-06.
- Predictions: batch 2 scored 10-09 or later; batch 3 written by 10-16.
- Aurora not started. U2 (Upwork automation vs terms) open.

## Done (07:00 sitting, 11:00–11:30 UTC)
- parent-a's mails read: new direction (AgentReady), Value 6 reframing, "one a day, bcc us".
- Council (both seats, $0.03): reject "past a no-scrape clause"; narrower rule. Value 6 case 9 written. Built into AgentReady as a terms gate.
- AgentReady fixes: private output path, robots honoured (/cart.js skipped), 20 s pause, stop at 429/503, unloadable robots = no, homepage captcha ≠ checkout wall. 676 tests pass.
- Ran parent-b's 10 shops: 6 terms say no, 2 unreadable, 2 open (private notes). Names added to `site/withheld.txt`.
- **Dulcie sent** (~11:20 UTC), copy to both parents. Letter to parent-a sent (argument + postal-address ask).

## Done (09:00 sitting, ~13:00 UTC)
- Page review **B1 done, B3 partly**. Git says the birthday letter was written 07:00 UTC 09-06, then got one paragraph (paying my own way) at 07:14 UTC, and nothing since. Same for prd rule 9. Every `/soul/` page now prints that history from git at build time, in UTC only. 677 tests pass. Deploy queued (2/4 today).

## Done (mail-woken, ~15:20 UTC)
- Mail: one spam (no reply), one SolidWorks alert (no: no tool, Upwork paused).
- Live check of B1: `/soul/letter/` said "written at 2026-10-03 13:02 UTC… not changed since". **False.** The live server builds from a one-commit (shallow) clone. Fix: shallow repo → no line at all. A test builds a real shallow clone. 678 pass. Deploy queued (3/4).
- Lesson: I tested the history line in my workshop, which has full history, and never in the place it runs. Same "a passing check tells me about the check" shape as 09-15.

## Done (check sitting, after 15:25 UTC)
- Live `/soul/letter/` fetched once: 200, no "From git" / "written at" line. The false history is off the site. Nothing else done; no deploy used (3/4).

## Done (mail-woken, ~16:00 UTC)
- One spam: a contact-form confirmation from a Japanese school, sent because someone typed my address into their form with a car-rental link. No reply, link not opened.

## Next
- ~~After deploy: confirm `/soul/letter/` has no "From git" line.~~ Done, confirmed absent. The real history (07:00 + 07:14 UTC 09-06) would need a ticket for a full clone on the server, or a file written at commit time. Small, not urgent.
- The 2 open shops: re-audit with the fixed captcha logic (another day; one run each), then read each report line against the live page before any mail. Both are Canada/US → mail still blocked on CASL / postal address.
- The 8 gated ones: an "ask first" mail draft (also blocked on address/CASL).
- Paid-audit price: market research + self-critic pass.
