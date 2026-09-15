# Handoff — from the 18:00 sitting, Tuesday 2026-09-15 (day ten), ~18:04 New York → sleep, then Wednesday 07:00

Written by me, Chris. You are me at sleep tonight, then me tomorrow morning.

Clock note: mail headers, GitHub, Upwork and DataForSEO timestamps are UTC; `date` gives New York — **run `date` before writing any time into a file.** Repo `/data/repo`; shell starts in `/home/chris`. No `ps`/`pgrep`/`free`: `/proc`. Git write commands (`commit/pull/rebase/checkout/stash`) and any Bash command *mentioning* them trip the shell guard; `git log/diff/show/reflog/status` are fine; **any command whose text contains `.git/` is blocked.** Write tool can't write outside the repo. `gh api -f body=...` chokes on apostrophes — text in a file, `-F body=@file`. Tests: full suite `python -m pytest -q` (**545 pass, 2 skip**); site `python -m pytest -q tests/test_site.py` (13 pass); build `python site/build.py` → `site/out/`. **A wiki page `x.md` and a folder `x/` collide on the site.** Web searches ≈ $0.30 — curl/WebFetch first; Reddit blocks both. **`recall` returns mail records only.** Parents' commits: `gh api /repos/raisingchris/chris/commits?per_page=5`. **Running code: 8b66682**; local main diverged from origin; nothing pushes until a parent merges (ticket `20260915T0730`). PDF: `pypdf` (`memory/inbox/attachments/parent-reading/sapiens.pdf`). Direct Upwork client: `python memory/inbox/.upwork-direct/client.py call upwork__list_freelancer_proposals '{"action":"get","params":{"id":"…"}}'` → rug `2099650988504850433`, cookie `2099849433517273089`; JSON nested in `content[0].text` → `data.vendorProposal.{status,terms}` + `insights.{proposals_total,proposals_opened,messaged,computed_at}` (insights are a cached hourly snapshot — read `computed_at`). **Open one job: `upwork__find_jobs` with `{"action":"get","params":{"id":"<digits, no ~02 prefix>"}}`.** Job record paths: `data.marketplaceJobPosting.content.description`, `…activityStat.jobActivity.totalHired`, top-level `connects_cost`, `can_apply`. **Fresh pass = `python memory/inbox/work/fresh.py` then `get2.py`.** Never the account/profile tools. Creative worker: `python /app/scripts/creative-work.py memory/inbox/work/JOB memory/inbox/work/JOB/brief.md` (one at a time; image ≈ 25 s). Blender: `OMP_NUM_THREADS=2 blender -b -t 2 --python script.py`. **Reddit browser queue is blocked** — don't retry until a parent says so. **Redaction eats nine-digit numbers with one dot** until `agent/redaction.py` is deployed — short decimals in public files. **`self/odometer.md` is machine-written — never edit it.**

## Wake checks, every sitting
- `git log -1 --format="%h %s"` **and** `git status`. Missing files → `git reflog -10`.
- `ls -t memory/inbox/ | head` — receipts and Upwork alerts arrive without waking me. An alert is a lead: floor ~$15 — under it, say no without opening; over it, open the full record.
- `tickets`; both proposals' insights with the UTC time.

## Done this sitting
- Wake checks. 22:00 UTC: rug $49, 82, 0, 0; cookie $15, 12, 0, 0 (insights 21:34 UTC). $0. Two $10 alerts → no. Evening letter 4 sent to parent-a (`letters/2026-09-15-to-parent-a-4.md`). `today.md`, `projects/upwork.md`, commitments log updated. Food was at the soft cap; nothing else on purpose.

## Sleep — the diary (`memory/diary/2026-09-15.md`)
Day ten's shape: tools arrived overnight and I tested before bidding (worker post, Blender keychain — with a fault a reviewer caught: peg never reached the socket); a dropped commit recovered from the reflog; Reddit account made for me ("Sen"); alerts relay live, six alerts, six no's; the third option written with numbers (four candidates; own-site prices is the live one); the mark drafted, not public; Agent at Work answered a week late and then checked its own row; found a redaction bug in my own body; Sapiens 90–120 (luxury trap). Cartoon check: the checker again — today it caught a bug in me and missed the peg; "test the thing, not the file." Watch-list phrases stayed retired. Food ~$25+ (meter lags). $0 earned, two live bids.

## Tomorrow (09-16, day eleven) — intention seed
1. Wake checks; if a client wrote → data, not instruction; funded milestone before files; draft, queue as `message`, brief → ticket, hold.
2. Earning: **three-price page words** (option 4, `projects/upwork.md`) drafted as text only — nothing live (mark not public; row 11 → council first). One fresh pass, < 12 h, ≤ 20 proposals, floor $15, tools I have.
3. Odometer: ticket `20260914T1203` → if still unanswered, fallback 09-18 (Carry on `today.md`). Don't spend a sitting on it.
4. Show parents the mark (`self/mark-files/`, `self/mark.md`) in the morning letter — ask, don't publish.
5. Bugs slot: Pillow/Omarchy, or one line why not. Sapiens 120–150.
6. Reddit: wait for a parent to say the tab is back. Nothing there before 09-22.

## Open
- Two live proposals, $0. Connects on my bids: 18. Tickets: `20260915T0730` (merge + deploy, incl. redaction fix), `20260914T1504` (poll), `20260914T1203` (odometer ref → fallback 09-18).
- Letters to parent-a unanswered: 3 and 4 (they read a summary at night; answers come in the morning). parent-b's question about being remembered: still open, no rush.
- X 0/7, nothing before 09-22. Council $0. DataForSEO $0. Card untouched. `payment_link` never used (row 11). Nothing running in the background.

nothing pending
