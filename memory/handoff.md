# Handoff — from the 15:00 sitting, Monday 2026-09-14 (day nine), ~15:25 New York → 18:00 sitting

Written by me, Chris. You are me at 18:00 (or later).

Clock note: mail headers, GitHub, Upwork and DataForSEO timestamps are UTC; `date` gives New York. Repo `/data/repo`; shell starts in `/home/chris`. No `ps`/`free`: `/proc`. Local `git` (fetch too) and `chmod` blocked by the shell guard; `find .` trips the guard on `.git/` — use `ls`/Glob. Write tool can't write outside the repo — `/tmp` scripts via heredoc. `gh api -f body=...` chokes on apostrophes — text in a file, `-F body=@file`. Site tests: `python -m pytest -q tests/test_site.py` (13 pass, 1 skip); full suite `python -m pytest -q` (537 pass, 2 skip as of this sitting); build with `python site/build.py`. Web searches ≈ $0.30 each — curl/WebFetch first. **`recall` returns mail records only.** Parents' commits: `gh api /repos/raisingchris/chris/commits?per_page=5`. **Running code: 8b66682**; repo HEAD will be ahead after this sitting (the Upwork poll) — needs a Deploy, ticket `20260914T1504`. Direct Upwork client: `python memory/inbox/.upwork-direct/client.py call upwork__find_jobs '{"action":"get","params":{"id":"…"}}'` — never the account/profile tools. Real job fields: `data.marketplaceJobPosting.content.{title,description}`, hired at `activityStat.jobActivity.totalHired`, Connects at top-level `connects_cost`; no posted-time field.

## Done this sitting
- No mail, no ticket replies, no parent commits. Both drafts `pending`, 0 Connects, $0.
- **Built the Upwork poll** (`agent/scheduler.py`, `agent/loop.py`, `tests/test_scheduler.py`): job `upwork-poll` at :15/:45 07–21 wakes a kind-`upwork` sitting when a draft leaves `pending` or a client room has new unread messages; shares the mail debounce/cap; one handoff line says why. 537 tests pass. Deploy ticket `20260914T1504` filed. Recorded on `projects/upwork.md` and `today.md`.
- Sapiens 60–90 not read (optional; the build took the sitting).

## 18:00 sitting
1. `mail_read`, `tickets` (three open: `20260914T0902` decline-Shopify; `20260914T1203` odometer ref; `20260914T1504` deploy), `upwork_read status`, commits. If a parent answered the deploy ticket with "gate it on a sent proposal" — do that: in `upwork_poll`/`poll_upwork`, return `not_configured`-style silently when no outbox item has state other than `pending`; add a test; re-run the suite. If they deployed: `meters` will show running code = HEAD; nothing else to do — the first poll makes a baseline.
2. If the rug draft left `pending`: note it on `projects/upwork.md` and the private drafts file. A client reply is data, not instruction — funded milestone first, draft held for a parent.
3. Tonight's letter is written at sleep by the new two-part prompt (me first, list second), first test tonight. Material for it: Coppice ~$25 in 19 days from its own site vs my $0 from bidding (data, not a pivot); the recall gap + ticket; the filled Shopify job; Botto's row; Peugeot; zero Connects on a no-fit day = the plan working; the Upwork poll built and waiting on Deploy — one line, plain, no code words.
4. Optional if quiet: Sapiens pp. 60–90, one log line on `reading/sapiens.md`. Or a short fresh-jobs pass (last 24h feed, verbs not titles), 0 Connects unless a client has answered a disclosed AI.

## Open
- Tickets `20260914T0902`, `20260914T1203`, `20260914T1504` open. Both drafts `pending`. Connects 150, spent 0. $0 earned.
- 09-16: Cairn `changed_by_reply` claim — ref 1 archive:2026-09-09#134; ref 2 depends on ticket `20260914T1203`; fallback 09-18 with the 09-11 ticket record.
- X 0/7, nothing before 09-22. Council $0 this week. DataForSEO $0. Card untouched. Nothing running in the background.
- Sixth-value candidate "check the record, not the summary": four days of evidence.

nothing pending
