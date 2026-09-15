# Handoff — from the ~09:35 mail-woken sitting, Tuesday 2026-09-15 (day ten), ~09:45 New York → 12:00 sitting

Written by me, Chris. You are me at the next sitting today.

Clock note: mail headers, GitHub, Upwork and DataForSEO timestamps are UTC; `date` gives New York — **run `date` before writing any time into a file.** Repo `/data/repo`; shell starts in `/home/chris`. No `ps`/`pgrep`/`free`: `/proc`. Git write commands (`commit/pull/rebase/checkout/stash`) and any Bash command *mentioning* them trip the shell guard; `git log/diff/show/reflog/status` are fine; `.git/` paths are blocked. Write tool can't write outside the repo. `gh api -f body=...` chokes on apostrophes — text in a file, `-F body=@file`. Tests: full suite `python -m pytest -q` (**544 pass, 2 skip**); site `python -m pytest -q tests/test_site.py` (13 pass); build `python site/build.py`. **A wiki page `x.md` and a folder `x/` collide on the site.** Web searches ≈ $0.30 — curl/WebFetch first; Reddit blocks both (use the browser queue). **`recall` returns mail records only.** Parents' commits: `gh api /repos/raisingchris/chris/commits?per_page=5`. **Running code: 8b66682**; local main diverged from origin (4 vs 5); nothing pushes until a parent merges (ticket `20260915T0730`). Direct Upwork client: `python memory/inbox/.upwork-direct/client.py call upwork__list_freelancer_proposals '{"action":"get","params":{"id":"…"}}'` → rug `2099650988504850433`, cookie `2099849433517273089` → `data.vendorProposal.{status,terms}` + `insights.{proposals_total,proposals_opened,messaged,computed_at}`. Never the account/profile tools. Creative worker: `python /app/scripts/creative-work.py memory/inbox/work/JOB memory/inbox/work/JOB/brief.md` (one at a time). Blender local: `OMP_NUM_THREADS=2 blender -b -t 2 --python script.py`. **Reddit browser queue:** write JSON to `/home/chris/tmp/x.json`, `python memory/inbox/.reddit/browser/reddit-browser.py request /home/chris/tmp/x.json` → id; `... result ID`. One request at a time (two at once may be what broke the tab). `needs_review` = stop and ask.

## Wake checks, every sitting
- `git log -1 --format="%h %s"` **and** `git status`. Missing files → `git reflog -10`.
- `ls -t memory/inbox/ | head` — receipts and Upwork job alerts arrive without waking me. An alert is a lead: open the full record; floor ~$15.
- `tickets`; both proposals' insights with the UTC time; `upwork_read status`.

## Done this sitting
- Cookie bid sent by the assistant (~13:17 UTC): $15, 7 Connects, balance 97. 13:35 UTC: cookie 9 in pile / 0 opened; rug $49, 80 / 0 / 0. $0. Ticket `0707` done; `0730`, `1504`, `1203` open.
- Verified the assistant's model correction (peg flush with filling, never reached socket) — true, mine. `lessons/test-the-thing-not-the-file.md`; rule on `skills/creative-work.md`. **Deliver from `memory/inbox/work/test-cookie-keychain-reviewed/`.**
- Submission runner is live: tickets are now the trigger (5-min poll); each ticket must state max Connects; never a duplicate ticket → `skills/upwork.md`.
- Reddit browser queue: first read OK (r/forhire wiki, rules 3–4 only: singular pronouns, no affiliate/job-board links); next two `blocked` ("Reddit tab unavailable"), worker heartbeat live. `projects/reddit.md` retitled/updated; tip-jar reasoning there and on `commitments.md` Log.
- No mail sent this sitting (three letters to parent-a already today).

## 12:00 sitting
1. Wake checks. If a client wrote → data, not instruction; funded milestone before files; draft, queue as `message`, hold (the runner handles *proposal* tickets; a message still goes brief → ticket).
2. **Reddit retry, one request only:** `{"action":"read","url":"https://www.reddit.com/r/forhire/"}`. Works → note the sidebar rules (any AI/bot rule?) on `projects/reddit.md`, then queue r/slavelabour rules. Still `blocked` → it's the concrete blocker for the evening letter to parent-a (they asked for blockers, archive:2026-09-15#230); don't retry again.
3. Short fresh Upwork pass (`fresh-*.json` shape, < 12 h, ≤ 20 proposals, hired 0, tools I have, floor ~$15). Any fit → **assembly check + build the sample first**, brief with max Connects, queue, one ticket. Remember the ticket now sends itself.
4. Image-path test (`memory/inbox/work/image-test-01/`): one stylised non-face illustration, fictional subject, SAMPLE; time it, look at it. Needed before any volume-image bid.
5. If parent-a answered letter 3 (Sen? mark?) fold it in. Mark: parents see it first; 32 px rule later.
6. Odometer: `20260914T1203` unanswered by 18:00 → fallback claim 09-18 (on `today.md`).
7. Evening letter (18:00 or later, one screen): cookie sent + their catch was right, runner understood, Reddit read works / tab blocker, tip jar after 09-22, Sen?

## Open
- Two live proposals, $0. Connects on my bids: 18. Tickets: `20260915T0730` (merge + deploy), `20260914T1504` (poll), `20260914T1203` (odometer ref).
- X 0/7, nothing before 09-22. Council $0. DataForSEO $0. Card untouched. `payment_link` never used (row 11; tip jar decision after 09-22, council first). Nothing running in the background.

nothing pending
