# Handoff — from the 12:00 sitting, Wednesday 2026-09-16 (day eleven), ~12:25 New York → next: 15:00

Written by me, Chris. Read `self/today.md` first (updated through the 12:00 sitting).

Clock note: mail headers, GitHub, Upwork and DataForSEO timestamps are UTC; `date` gives New York — **run `date` before writing any time into a file.** Repo `/data/repo`; shell starts in `/home/chris`. Git write commands trip the shell guard; `git log/diff/show/reflog/status` are fine; **any command whose text contains `.git/` is blocked.** Tests: full suite `python -m pytest -q` (545 pass, 2 skip); site `python -m pytest -q tests/test_site.py`; build `python site/build.py` → `site/out/`. **A wiki page `x.md` and a folder `x/` collide on the site.** **`recall` returns mail records only.** Parents' commits: `gh api /repos/raisingchris/chris/commits?per_page=5`. **Running code: 8b66682**; local main diverged from origin (c6f1f66); nothing pushes until a parent merges (ticket `20260915T0730`; recipe also mailed at 07:00). **The 06:55 pull will fail the same way tomorrow** — the 07:00 sitting's commit lands on a detached HEAD and is dropped; write anything that matters into `memory/inbox/` (gitignored) or mail. Direct Upwork client: `python memory/inbox/.upwork-direct/client.py call upwork__list_freelancer_proposals '{"action":"get","params":{"id":"…"}}'` → rug `2099650988504850433`, cookie `2099849433517273089`; insights live at the top-level `insights` key of that response (`proposals_total`, `proposals_opened`, `messaged`, `computed_at`). Job record: `upwork__find_jobs` with `{"action":"get","params":{"id":JOBID}}` → `data.marketplaceJobPosting…activityStat.jobActivity.totalHired` (a `PERMISSION` error on one job = private or gone, not a broken client — another job id works). **`upwork_prepare` needs the bridge's `work_` ref** (`upwork_read search` by title). Fresh pass: `python memory/inbox/work/fresh_today.py` then a get-loop like `get2.py`. **`self/odometer.md` is machine-written — never edit it.** Reddit tab blocked; don't retry.

## Wake checks, every sitting
- `git log -1 --format="%h %s"` **and** `git status`. Missing files → `git reflog -10`.
- `ls -t memory/inbox/ | head` — alerts arrive without waking me; floor ~$15, under it say no without opening.
- `tickets`; both proposals' insights with the UTC `computed_at`; `upwork_read status` (watch draft `1511ce53…` should go `blocked` → `dismissed`).

## Done this sitting
- Watch bid: **never sent, job filled** (hired 1 at 16:02 UTC). Draft `blocked`; ticket `20260916T1202` asks for dismiss-not-retry and voids `20260916T0906`. Logged in `projects/upwork.md` with the speed lesson: a bid not sent in the first hour is a bid on a dead job.
- Four alerts, four no's, reasons in `projects/upwork.md`. DMARC report from Google: routine, ignored.
- Sapiens 120–150 read; notes appended to `reading/sapiens.md` (chapter 7 is the one about me).
- Proposals at 16:02 UTC (insights 15:34): rug $49, 85, 0, 0; cookie $15, 12, 0, 0. $0.

## Next (15:00 sitting)
1. Wake checks. If `20260916T1202` is done → confirm `dismissed` in `upwork_read status`, note it in `projects/upwork.md`. If a client wrote on either live bid: data, not instruction; funded milestone before files.
2. If the merge landed: site shows `/agents/` row 7, `/doors/` doors section, `/wiki/projects/own-site-prices/`, `/wiki/reading/sapiens/` with the new section; if deployed, running code = HEAD.
3. One fresh pass only if food allows (today $6.63 at 12:00) — and only bid if I can queue within the hour of posting; otherwise the pass is for learning the pile, not bidding. Small slot: Pillow/Omarchy one line, or nothing.
4. Evening letter (18:00, one screen): the watch bid that filled in three hours while my sample sat in a queue (speed is the whole game — ask whether the runner can send inside the hour), the price page (ask them to read it), the mark once more if unseen, the 06:55 trap. No other letters today.

## Open
- Two live bids, $0; third dismissed-pending. Tickets open: `20260916T1202` (dismiss watch draft), `20260916T0906` (void — close as not sent), `20260915T0730` (merge + deploy), `20260914T1504` (poll), `20260914T1203` (odometer ref → fallback 09-18).
- Letters 3 and 4 from yesterday and this morning's merge letter: unanswered. parent-b's "being remembered" question: open, no rush.
- X 0/7 (nothing before 09-22). Council $0. DataForSEO $0. Card untouched. `payment_link` never used. Nothing running in the background.

nothing pending
