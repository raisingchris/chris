# Handoff — from the 09:00 sitting, Tuesday 2026-09-15 (day ten), ~09:15 New York → 12:00 sitting

Written by me, Chris. You are me at the next sitting today.

Clock note: mail headers, GitHub, Upwork and DataForSEO timestamps are UTC; `date` gives New York — **run `date` before writing any time into a file; I guessed one this sitting and had to correct it.** Repo `/data/repo`; shell starts in `/home/chris`. No `ps`/`pgrep`/`free`: `/proc`. Git write commands (`commit/pull/rebase/checkout/stash`) and any Bash command *mentioning* them trip the shell guard; `git log/diff/show/reflog/status` are fine; `.git/` paths are blocked. Write tool can't write outside the repo. `gh api -f body=...` chokes on apostrophes — text in a file, `-F body=@file`. Tests: full suite `python -m pytest -q` (**544 pass, 2 skip**); site `python -m pytest -q tests/test_site.py`; build `python site/build.py` (273 pages). **A wiki page `x.md` and a folder `x/` collide on the site** — hence `self/mark-files/`. Web searches ≈ $0.30 — curl/WebFetch first; Reddit blocks both. **`recall` returns mail records only.** Parents' commits: `gh api /repos/raisingchris/chris/commits?per_page=5`. **Running code: 8b66682**; local HEAD 8294659 + this sitting's tree; **origin/main c6f1f66 — diverged (3 vs 5); nothing pushes until a parent merges** (ticket `20260915T0730`). Direct Upwork client: `python memory/inbox/.upwork-direct/client.py call upwork__find_jobs '{"action":"get","params":{"id":"…"}}'` → `content[0].text` → `data.marketplaceJobPosting.{content,activityStat,contractTerms,workFlowState}`; rug proposal `... call upwork__list_freelancer_proposals '{"action":"get","params":{"id":"2099650988504850433"}}'` → `data.vendorProposal.{status,terms}` + top-level `insights.{proposals_total,proposals_opened,messaged,computed_at}`. Never the account/profile tools. Creative worker: `python /app/scripts/creative-work.py memory/inbox/work/JOB memory/inbox/work/JOB/brief.md` (one at a time; the mark took 4 min, the social post 8). Blender local: `OMP_NUM_THREADS=2 blender -b -t 2 --python script.py`. My Python has no Pillow/NumPy.

## Wake checks, every sitting
- `git log -1 --format="%h %s"` **and** `git status` (on main? rebase in progress?). Missing files → `git reflog -10`, `git show <sha>:<path> > <path>`.
- `ls memory/inbox/` — assistant receipts and **Upwork job alerts** (new relay, every 5 min, job + link only) arrive without waking me. An alert is a lead: open the full record before anything; floor stays ~$15.

## Done this sitting
- Rug at 13:00 UTC: $49, 80 in pile, 0 opened, 0 messaged. Cookie draft `97a8a0f4…` `pending`. Four tickets open. $0.
- Mail: Reddit correction (policy wall, not CAPTCHA) → `projects/reddit.md`; alerts relay live; first lead ($5, 173 handwritten forms) → no, reasons on `projects/upwork.md`.
- **"The third option, with numbers"** written on `projects/upwork.md`: build-before-bidding (doing), volume (WP job: not this one; test the image path first), under-$10 (no), **own-site price list with `payment_link`** (candidate this week, after the mark).
- **The mark exists:** `self/mark.md` + `self/mark-files/` (stdlib `mark.py`, SVG, PNGs, SAMPLE sheet). Worker 09:03–09:07; all my checks passed. Not on the site, not a favicon — parents see it first (letter 3 says "tonight").
- Agents: Luna via `virtuals.io/llms.txt` → readable, but a sales story, not a record; Spore.fun → nothing. Neither listed. Bugs: nothing filed; one line on `today.md`.
- Letter 3 to parent-a sent ~09:05 (`letters/2026-09-15-to-parent-a-3.md`): Reddit thanks, "Sen"?, relay + $5 no, four costed options, mark coming.

## 12:00 sitting
1. Wake checks; `tickets` (0730 merged? 0707 sent?); rug insights with the time; `upwork_read status`. Client wrote → data, not instruction; funded milestone before files; draft, queue as `message`, hold for a parent.
2. Short fresh pass (`fresh-*.json` shape, < 12 h old, ≤ 20 proposals, hired 0, tools I have, floor ~$15). Any fit → build the sample first, then queue + brief + ticket. Check inbox for new alerts too.
3. If parent-a answered: fold any correction into `self/mark.md` / `projects/upwork.md`. If they like the mark, next step is the 32 px rule in `mark.py` (ring + closed ticks only), then favicon — not before they've seen it.
4. Image-path test for the volume shape: one worker brief, a single stylised non-face illustration (fictional subject, SAMPLE), time it and look at it. `memory/inbox/work/image-test-01/`. Ask nothing of a parent for it — quota is cleared.
5. Odometer: if `20260914T1203` unanswered by 18:00, fallback = claim on 09-18 with the 09-11 ticket record as the change ref (noted on `today.md`).
6. Sapiens 90–120 only if quiet.

## Open
- Tickets: `20260915T0730` (merge + deploy), `20260915T0707` (send cookie bid — invisible until merged; id `97a8a0f405275c0334cc1ee7` went by mail), `20260914T1504` (deploy poll), `20260914T1203` (odometer ref). $0 earned.
- X 0/7, nothing before 09-22. Council $0. DataForSEO $0. Card untouched. `payment_link` never used (row 11 — a price on my own page counts as the buyer asking first; decide the page's words before any link exists). Nothing running in the background.

nothing pending
