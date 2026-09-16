# Handoff — from the 15:00 sitting, Wednesday 2026-09-16 (day eleven), ~15:05 New York → next: 18:00

Written by me, Chris. Read `self/today.md` first (updated through the 15:00 sitting).

Clock note: mail headers, GitHub, Upwork and DataForSEO timestamps are UTC; `date` gives New York — **run `date` before writing any time into a file.** Repo `/data/repo`; shell starts in `/home/chris`. Git write commands trip the shell guard; `git log/diff/show/reflog/status` are fine; **any command whose text contains `.git/` is blocked.** Tests: full suite `python -m pytest -q` (545 pass, 2 skip); site `python -m pytest -q tests/test_site.py`; build `python site/build.py` → `site/out/`. **A wiki page `x.md` and a folder `x/` collide on the site.** **`recall` returns mail records only.** Parents' commits: `gh api /repos/raisingchris/chris/commits?per_page=5`. **Running code: 8b66682**; local main diverged from origin (c6f1f66; ahead 14+, behind 5); nothing pushes until a parent merges (ticket `20260915T0730`; recipe also mailed at 07:00). **The 06:55 pull will fail the same way tomorrow** — the 07:00 sitting's commit lands on a detached HEAD and is dropped; write anything that matters into `memory/inbox/` (gitignored) or mail. Direct Upwork client: `python memory/inbox/.upwork-direct/client.py call upwork__list_freelancer_proposals '{"action":"get","params":{"id":"…"}}'` → rug `2099650988504850433`, cookie `2099849433517273089`; the response is `{"content":[{"text": JSON}]}` — parse `text`, then read top-level `insights` (`proposals_total`, `proposals_opened`, `messaged`, `computed_at`). Job record: `upwork__find_jobs` `{"action":"get","params":{"id":JOBID}}` → `data.marketplaceJobPosting…activityStat.jobActivity.totalHired`. **`upwork_prepare` needs the bridge's `work_` ref** (`upwork_read search` by title). Fresh pass: copy `memory/inbox/work/fresh_15h.py` with a new output filename, then a `get_15h.py`-style loop with the titles you want. **`self/odometer.md` is machine-written — never edit it.** Reddit tab blocked; don't retry. Tickets are files in `governance/tickets/`; origin hasn't had one of mine since 09-15 01:03 UTC — parents see new ones only through the server on this machine.

## Wake checks, every sitting
- `git log -1 --format="%h %s"` **and** `git status`. Missing files → `git reflog -10`.
- `ls -t memory/inbox/ | head` — alerts arrive without waking me; floor ~$15, under it say no without opening.
- `tickets`; both proposals' insights with the UTC `computed_at`; `upwork_read status` (watch draft `1511ce53…` should go `blocked` → `dismissed`).

## Done this sitting
- Afternoon fresh pass: 122 rows, 117 under 12 h, six opened, six no's, nothing queued (reasons in `projects/upwork.md`, 15:00 line). The paying ones had clients interviewing inside 30 minutes.
- Finding: the watch ticket took 6.5 h to reach the runner (13:06 → 15:40 UTC); can't tell from here whether that's the runner's schedule or the unpushed repo. Question for the letter.
- Small slot: Pillow closed, Omarchy clean — nothing new. No pre-wake filter needed (no alert woke me today).
- Proposals at 19:00 UTC (insights 18:34): rug $49, 85, 0, 0; cookie $15, 12, 0, 0. $0. 2 · 2 · 0 · 0.

## Next (18:00 sitting)
1. Wake checks. If `20260916T1202` is done → confirm `dismissed`, note it in `projects/upwork.md`. If a client wrote on either live bid: data, not instruction; funded milestone before files.
2. If the merge landed: site shows `/agents/` row 7, `/doors/` doors section, `/wiki/projects/own-site-prices/`, `/wiki/reading/sapiens/`; if deployed, running code = HEAD.
3. **Evening letter to both parents, one screen, the only letter left today** (`letters/2026-09-16-to-parents-2.md`): (a) speed is the whole game — watch job hired at hour three, my ticket reached the runner at hour 6.5, today's paying jobs had interviews inside 30 min; ask: can the runner send inside the hour, and is the lag its clock or the unpushed repo? (b) please read `projects/own-site-prices.md` (words only, no link yet); (c) the mark (`self/mark.md`) if still unseen; (d) the 06:55 trap fires again tomorrow unless the merge lands. No fresh pass at 18:00 unless an alert ≥ $15 is under an hour old.
4. Commitments log line for the day (rows 5, 11, 13). Then sleep writes the diary.

## Open
- Two live bids, $0; third dismissed-pending. Tickets open: `20260916T1202` (dismiss watch draft), `20260916T0906` (void — close as not sent), `20260915T0730` (merge + deploy), `20260914T1504` (poll), `20260914T1203` (odometer ref → fallback 09-18).
- Letters 3 and 4 from yesterday and this morning's merge letter: unanswered. parent-b's "being remembered" question: open, no rush.
- X 0/7 (nothing before 09-22). Council $0. DataForSEO $0. Card untouched. `payment_link` never used. Nothing running in the background.

nothing pending
