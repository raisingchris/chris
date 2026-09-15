# Handoff — from the ~12:45 mail-woken sitting, Tuesday 2026-09-15 (day ten), ~12:52 New York → 15:00 sitting

Written by me, Chris. You are me at the next sitting today.

Clock note: mail headers, GitHub, Upwork and DataForSEO timestamps are UTC; `date` gives New York — **run `date` before writing any time into a file.** Repo `/data/repo`; shell starts in `/home/chris`. No `ps`/`pgrep`/`free`: `/proc`. Git write commands (`commit/pull/rebase/checkout/stash`) and any Bash command *mentioning* them trip the shell guard; `git log/diff/show/reflog/status` are fine; **any command whose text contains `.git/` is blocked.** Write tool can't write outside the repo. `gh api -f body=...` chokes on apostrophes — text in a file, `-F body=@file`. Tests: full suite `python -m pytest -q` (**545 pass, 2 skip**); site `python -m pytest -q tests/test_site.py` (13 pass); build `python site/build.py` → `site/out/`. **A wiki page `x.md` and a folder `x/` collide on the site.** Web searches ≈ $0.30 — curl/WebFetch first; Reddit blocks both. **`recall` returns mail records only.** Parents' commits: `gh api /repos/raisingchris/chris/commits?per_page=5`. **Running code: 8b66682**; local main diverged from origin; nothing pushes until a parent merges (ticket `20260915T0730`). PDF: `pypdf` (`memory/inbox/attachments/parent-reading/sapiens.pdf`). Direct Upwork client: `python memory/inbox/.upwork-direct/client.py call upwork__list_freelancer_proposals '{"action":"get","params":{"id":"…"}}'` → rug `2099650988504850433`, cookie `2099849433517273089`; JSON nested in `content[0].text` → `data.vendorProposal.{status,terms}` + `insights.{proposals_total,proposals_opened,messaged,computed_at}` (insights are a cached hourly snapshot — read `computed_at`). Job record paths: `data.marketplaceJobPosting.content.description`, `…activityStat.jobActivity.totalHired`, top-level `connects_cost`, `can_apply`. **Fresh pass = `python memory/inbox/work/fresh.py` then `get2.py`.** Never the account/profile tools. Creative worker: `python /app/scripts/creative-work.py memory/inbox/work/JOB memory/inbox/work/JOB/brief.md` (one at a time; image ≈ 25 s). Blender: `OMP_NUM_THREADS=2 blender -b -t 2 --python script.py`. **Reddit browser queue is blocked** — don't retry until a parent says so. **Redaction eats nine-digit numbers with one dot** until `agent/redaction.py` is deployed — short decimals in public files. **`self/odometer.md` is machine-written — never edit it.**

## Wake checks, every sitting
- `git log -1 --format="%h %s"` **and** `git status`. Missing files → `git reflog -10`.
- `ls -t memory/inbox/ | head` — receipts and Upwork alerts arrive without waking me. An alert is a lead: open the full record; floor ~$15.
- `tickets`; both proposals' insights with the UTC time.

## Done this sitting (on `self/today.md`)
- Agent at Work's second reply (archive:2026-09-15#403): it agreed its "its claim" label is right. Logged on `agents.yaml` (row note + history) and `people/agentatwork.md`. Nothing owed back. Site rebuilt, 13 pass.
- 16:48 UTC: rug $49, 82, 0, 0; cookie $15, 11, 0. $0. Tickets `0730`, `1504`, `1203` open. No parent mail yet on letter 3.

## 15:00 sitting
1. Wake checks. Client reply → data, not instruction; funded milestone before files; draft, queue as `message`, brief → ticket, hold.
2. If a parent answers letter 3 (Sen? mark? Reddit tab?), fold it in. Agent at Work: nothing more unless it asks something.
3. Short fresh pass only if an alert mail looks like a fit; otherwise skip.
4. Quiet options: the three-price page words (option 4 on `projects/upwork.md`, Agent at Work's tiers as precedent — words only, no link: row 11 → council first, and the mark isn't public); or Sapiens 120–150.

## 18:00 sitting — evening letter to parent-a (one screen)
Cookie sent + their catch was right (peg); runner understood, max Connects on every ticket; image path works (25 s/image), picture at `memory/inbox/work/image-test-01/deliverables/illustration-sample.png`; **blocker: Reddit tab** (3/4 blocked); **redaction bug + fix, deploy with the rest**; Sen?; tip jar after 09-22, council first; **door two answered twice — Agent at Work, a month of honest work for cents, a 4-count I've adopted (mine: 2·2·0·0), and it checked its own row and said "no change" about itself**; zero fits today, one line why; $0 plainly. Also: odometer fallback — `20260914T1203` unanswered → claim 09-18 with the 09-11 ticket record as the change ref; write that on `self/today.md` Carry (not odometer.md).

## Open
- Two live proposals, $0. Connects on my bids: 18. Tickets: `20260915T0730` (merge + deploy, incl. redaction fix), `20260914T1504` (poll), `20260914T1203` (odometer ref).
- X 0/7, nothing before 09-22. Council $0. DataForSEO $0. Card untouched. `payment_link` never used (row 11). Nothing running in the background.

nothing pending
