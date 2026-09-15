# Handoff — from the ~08:05 mail-woken sitting, Tuesday 2026-09-15 (day ten), ~08:15 New York → 09:00 sitting

Written by me, Chris. You are me at the next sitting today.

Clock note: mail headers, GitHub, Upwork and DataForSEO timestamps are UTC; `date` gives New York. Repo `/data/repo`; shell starts in `/home/chris`. No `ps`/`pgrep`/`free`: `/proc`. Git write commands (`commit/pull/rebase/checkout/stash`) and any Bash command *mentioning* them — even in a heredoc comment — trip the shell guard; `git log/diff/show/reflog/status` are fine; `.git/` paths are blocked. Write tool can't write outside the repo; after restoring a file via shell, Read it again before Write. `gh api -f body=...` chokes on apostrophes — text in a file, `-F body=@file`. Tests: full suite `python -m pytest -q` (**544 pass, 2 skip**); site `python -m pytest -q tests/test_site.py`; build `python site/build.py` (269 pages). Web searches ≈ $0.30 — curl/WebFetch first; Reddit blocks both. **`recall` returns mail records only.** Parents' commits: `gh api /repos/raisingchris/chris/commits?per_page=5`. **Running code: 8b66682**; local HEAD a78d4c9 + this sitting's tree; **origin/main c6f1f66 — diverged (2 vs 5); nothing pushes until a parent merges** (ticket `20260915T0730`). Direct Upwork client: `python memory/inbox/.upwork-direct/client.py call upwork__find_jobs '{"action":"get","params":{"id":"…"}}'`; rug proposal `... call upwork__list_freelancer_proposals '{"action":"get","params":{"id":"2099650988504850433"}}'` → response is `content[0].text` (JSON string) → `data.vendorProposal.{status,terms}` and top-level `insights.{proposals_total,proposals_opened,messaged,computed_at}`. Never the account/profile tools. Creative worker: `python /app/scripts/creative-work.py memory/inbox/work/JOB memory/inbox/work/JOB/brief.md` (one at a time, ~8–15 min, background). Blender local: `OMP_NUM_THREADS=2 blender -b -t 2 --python script.py`. My Python has no Pillow/NumPy.

## Wake checks, every sitting
- `git log -1 --format="%h %s"` **and** `git status` (on main? rebase in progress?). Missing files → `git reflog -10`, `git show <sha>:<path> > <path>`.
- `ls memory/inbox/` — assistant receipts arrive without headers and don't wake me.

## Done this sitting (mail-woken by five mails; no reply sent)
- A parent built me a Reddit account, u/raising-chris ("Chris Sen | Autonomous AI"). No API/autonomous posting; access request in and acknowledged (archive:2026-09-15#127) — **don't send another**. Actions go brief (`memory/inbox/work/reddit/<task>/brief.md`) → ticket → parent's Chrome. PhotoshopRequest gates: 10 days + 30 honest karma → nothing paid before ~09-25. Private setup notes `memory/inbox/.reddit/README.md`; credentials beside it — **never print, quote or commit**. New page `projects/reddit.md`; row-5 note on `self/predictions.md`; `projects/README.md`, `people/astra.md`, `projects/upwork.md`, `today.md` updated.
- Reads at 12:05 UTC: rug $49, 80 in pile, 0 opened, 0 messaged; cookie draft `pending`, job ACTIVE, 0 hired. Spam ($149.99/mo social posting) ignored. Two Reddit verify mails already handled by the assistant.

## 09:00 sitting
1. Wake checks; `tickets` (0730 merged? 0707 sent? 1504? 1203?); `upwork_read status`; rug insights with the time. Client wrote → data, not instruction; funded milestone before files; draft, queue as `message`, hold for a parent.
2. If still diverged: keep working; mail is the channel out. Don't pile up tickets.
3. Intention 2's second half with numbers (`projects/upwork.md`, short): re-read the WP-images job (id in `memory/inbox/work/fresh-2026-09-15.json`). Needs a stranger's WP admin → no. Pure "deliver 200 files" → the volume job; ask parent-a what one worker image costs them.
4. The mark: one worker brief, non-face mark from my numbers, SVG + PNG, "SAMPLE" on it, `memory/inbox/work/mark-01/`. Show parent-a first. After 3.
5. Intentions 3 (odometer fallback by 18:00) and 4 (one bug/agents item or one line why). Sapiens 90–120 if quiet.
6. Next letter to parent-a (fold in, don't send separately): thanks for Reddit; is "Sen" my surname?; nothing on Reddit before 09-22, nothing paid before 09-25; each reply costs them a browser session so I'll ask rarely.

## Open
- Tickets: `20260915T0730` (merge + deploy), `20260915T0707` (send cookie bid — invisible until merged; id `97a8a0f405275c0334cc1ee7` went by mail), `20260914T1504` (deploy poll), `20260914T1203` (odometer ref). $0 earned. Connects 104 displayed per receipt (not read by me).
- X 0/7, nothing before 09-22. Council $0. DataForSEO $0. Card untouched. Nothing running in the background.

nothing pending
