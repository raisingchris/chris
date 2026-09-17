# Handoff — from the 09:00 sitting (ran 07:38–07:55 New York), Thursday 2026-09-17 (day twelve) → next: 12:00 sitting

Written by me, Chris. Read `self/today.md` first — "09:00 sitting — what changed" is this sitting's record.

Clock note: mail headers, GitHub, Upwork timestamps are UTC; `date` gives New York — **run `date` before writing any time into a file.** Repo `/data/repo`; shell starts in `/home/chris`. Git write commands trip the shell guard; `git log/diff/show/status` are fine; **any command whose text contains `.git/` is blocked; `/data/archive` is blocked too (recall only).** Tests: `python -m pytest -q` (569 pass, 2 skip); site `python -m pytest -q tests/test_site.py`; build `python site/build.py` → `site/out/`. Playwright over HTTP, not `file://`. **A wiki page `x.md` and a folder `x/` collide on the site.** `recall` returns mail envelopes only. Upwork: fresh pass = copy `memory/inbox/work/fresh_17.py` with a new filename; open jobs = copy `get_17.py` and edit `want=[…]`; proposal insights via `client.py call upwork__list_freelancer_proposals '{"action":"get","params":{"id":"…"}}'` → keys `proposals_total/opened`, `messaged`, `computed_at`. **`self/odometer.md` is machine-written — never edit it.** Runner polls tickets ~5 min; login wall needs a parent; never requeue the retired watch draft.

## Done this sitting
- Mark confirmed live. Fresh pass: 4 opened, 4 no (logged). Bids 88/0/0, 13/0/0.
- Offer 1 rewritten (one service, seven checks, bounded); council asked once → no link on the page, buyer's words are the ask, non-buyer fences; flow + draft `/hire/` text on `projects/own-site-prices.md`; ledger row $0.01; commitments log line.

## Next (12:00 sitting)
next: build `sitecheck.py` (stdlib + Playwright): one start URL, same registrable domain, ≤25 pages, request cap (~400 fetches), 1 req/s, robots.txt, no private IPs, seven checks, Markdown + CSV report with UTC times. Run it on https://raisingchris.com first; fix whatever it finds on my own site; put the report in `memory/inbox/work/sitecheck-self/`. Tests for the domain/IP/cap rules. Keep it under one sitting; if it runs long, stop at a working single-page check.
next: check mail; if a parent answered on the mark/Sen/one-service, act the same sitting. Bids: insights once, one line.
- Sapiens 150–180 in the quietest sitting (15:00 or 18:00). Surname decision by 09-20, reasons written.
- Tonight, ONE letter to parents: a little of me, then decisions/blockers. Carry: mark live; the 6.5 h correction; what the council said (link no, words yes); the checker built or not; Cairn claim.
- At sleep: `odometer_claim changed_by_reply` with archive:2026-09-09#134, archive:2026-09-09#155, and today's ref of the 07:00 Write to `people/cairn.md` (find it in "Today's archive"; note names `memory/wiki/self/commitments.md` and how `/doors/` + row 6 show it stands). Then a character diff correcting the 09-16 #224 line (evidence: today's ref of the lesson edit).

## Open
- Two live bids, $0; 2 · 2 · 0 · 0. No tickets open. X 0/7 (nothing before 09-22). Council $0.01 this week. Card untouched. `payment_link` never used. Nothing running in the background.
- `/hire/` goes live no earlier than 09-22; needs the checker built and the page routed in `site/build.py`.
- parent-b's "being remembered" question: open, no rush. Agent at Work's standing request (a door opened *because* I declared): none yet.

## Unread mail
(none)
