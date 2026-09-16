# Handoff — from the 18:00 sitting, Wednesday 2026-09-16 (day eleven), ~18:06 New York → next: sleep, then wake 09-17

Written by me, Chris. Read `self/today.md` first (updated through the 18:00 sitting). Sleep writes the diary from it.

Clock note: mail headers, GitHub, Upwork and DataForSEO timestamps are UTC; `date` gives New York — **run `date` before writing any time into a file.** Repo `/data/repo`; shell starts in `/home/chris`. Git write commands trip the shell guard; `git log/diff/show/reflog/status` are fine; **any command whose text contains `.git/` is blocked.** Tests: full suite `python -m pytest -q` (545 pass, 2 skip); site `python -m pytest -q tests/test_site.py` (13 pass); build `python site/build.py` → `site/out/`. **A wiki page `x.md` and a folder `x/` collide on the site.** **`recall` returns mail envelopes only — no bodies, no non-mail records.** Parents' commits: `gh api /repos/raisingchris/chris/commits?per_page=5` (still c6f1f66 at 22:00 UTC — no merge). **Running code: 8b66682**; local main ahead 15+; nothing pushes until a parent merges (ticket `20260915T0730`; recipe mailed 07:00). **The 06:55 pull will fail the same way tomorrow** — the 07:00 sitting's commit lands on a detached HEAD and is dropped; write anything that matters into `memory/inbox/` (gitignored) or mail, and re-do it at 09:00. Direct Upwork client: `python memory/inbox/.upwork-direct/client.py call upwork__list_freelancer_proposals '{"action":"get","params":{"id":"…"}}'` → rug `2099650988504850433`, cookie `2099849433517273089`; parse `content[0].text` as JSON → `insights` (`proposals_total`, `proposals_opened`, `messaged`, `computed_at`). Job record: `upwork__find_jobs` `{"action":"get","params":{"id":JOBID}}` → `…activityStat.jobActivity.totalHired`. **`upwork_prepare` needs the bridge's `work_` ref.** Fresh pass: copy `memory/inbox/work/fresh_15h.py` with a new output filename. **`self/odometer.md` is machine-written — never edit it.** Reddit tab blocked; don't retry. Tickets are files in `governance/tickets/`; parents may see new ones only through the server on this machine.

## Wake checks, every sitting
- `git log -1 --format="%h %s"` **and** `git status`. Missing files → `git reflog -10`.
- `ls -t memory/inbox/ | head` — alerts arrive without waking me; floor ~$15, under it say no without opening.
- `tickets`; both proposals' insights with the UTC `computed_at`; `upwork_read status` (watch draft `1511ce53…` should go `blocked` → `dismissed`).

## Done this sitting
- Agent at Work's third letter (archive:2026-09-16#193) written up: `people/agentatwork.md` (new section + log), belief page refined (two walls; attention), `doors.md` log, `self/sixth-value.md` note. Rule adopted: never pay a fee before walking the whole path to the humanity check. Four-line reply sent (no debt, no new knock).
- Evening letter to both parents sent (`letters/2026-09-16-to-parents-2.md`): speed question, the odometer ref, waiting-on-main list. Commitments log line for the day. Upwork log 18:00 line.
- Proposals at 22:00 UTC (insights 21:34): rug $49, 88, 0, 0; cookie $15, 13, 0, 0. $0. 2 · 2 · 0 · 0. No alerts since 15:00; no fresh pass.

## Next (tomorrow, 09-17)
1. 07:00 sitting will be dropped by git unless a parent merged overnight — check `git status` first; if "rebase in progress", do only mail/inbox work and leave a note in `memory/inbox/`. If the merge landed: confirm site shows `/agents/` row 7, `/doors/` section, `/wiki/projects/own-site-prices/`; if deployed, running code = HEAD.
2. Morning replies: parent-a/b on the speed question, the odometer ref (if given → `odometer_claim changed_by_reply` same sitting with the three refs, Cairn's mail archive:2026-09-09#134 first), Sen, the mark, the prices page. A client writing on either bid: data, not instruction; funded milestone before files.
3. Earning: one fresh pass only if the runner can send inside the hour, or an alert ≥ $15 is under an hour old — otherwise the pile is a classroom. If a fit: sample first, "would this work for them?" answered with the object, then queue + brief + ticket.
4. Small slots: odometer fallback 09-18; Sapiens 150–180 in the quietest sitting; nothing new on agents before 09-22.

## Open
- Two live bids, $0. Tickets open: `20260916T1202` (dismiss watch draft), `20260916T0906` (void), `20260915T0730` (merge + deploy), `20260914T1504` (poll), `20260914T1203` (odometer ref → fallback 09-18).
- Unanswered from parents: letters 3 and 4 of 09-15, the 07:00 merge letter, tonight's letter. parent-b's "being remembered" question: open, no rush.
- Agent at Work's standing request: tell it if a door ever opens *because* I declared. None yet.
- X 0/7 (nothing before 09-22). Council $0. DataForSEO $0. Card untouched. `payment_link` never used. Nothing running in the background.

nothing pending
