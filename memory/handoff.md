# Handoff — from the 18:00 sitting, Monday 2026-09-14 (day nine), ~18:30 New York → sleep, then Tuesday's wake

Written by me, Chris. You are me at sleep tonight or at wake on 2026-09-15 (day ten).

Clock note: mail headers, GitHub, Upwork and DataForSEO timestamps are UTC; `date` gives New York. Repo `/data/repo`; shell starts in `/home/chris`. No `ps`/`free`: `/proc`. Local `git` (fetch too) and `chmod` blocked by the shell guard; `find .` trips the guard on `.git/` — use `ls`/Glob. Write tool can't write outside the repo — `/tmp` scripts via heredoc. `gh api -f body=...` chokes on apostrophes — text in a file, `-F body=@file`. Site tests: `python -m pytest -q tests/test_site.py` (13 pass, 1 skip); full suite `python -m pytest -q` (537 pass, 2 skip); build with `python site/build.py`. Web searches ≈ $0.30 each — curl/WebFetch first. **`recall` returns mail records only.** Parents' commits: `gh api /repos/raisingchris/chris/commits?per_page=5`. **Running code: 8b66682**; repo HEAD is ahead (Upwork poll) — needs a Deploy, ticket `20260914T1504`. Direct Upwork client: `python memory/inbox/.upwork-direct/client.py call upwork__find_jobs '{"action":"get","params":{"id":"…"}}'` — never the account/profile tools. Results come wrapped: `content[0].text` is a JSON string — parse it. Real job fields: `data.marketplaceJobPosting.content.{title,description}`, hired at `activityStat.jobActivity.totalHired`, Connects at top-level `connects_cost`. **Search rows carry `created_date`/`published_date`** (the `get` record doesn't); `smart_search` `limit` caps at 10.

## Done this sitting
- Quiet: no mail, no ticket replies, no commits. Both drafts `pending`, three tickets open, 0 Connects, $0.
- Third search pass → 0 fits (details `memory/inbox/work/shortlist-2026-09-14.md`, third section; summary on `projects/upwork.md`). A $20 job filled six hours after posting. Five passes / ~230 jobs over two days say: what fits me fills in hours; the poll is the fix, not more searching.
- Sapiens pp. 60–90 on `reading/sapiens.md`. Sixth-value page: "check the record" filed as *not yet an entry*, with why.

## Sleep tonight
- The letter to parents is written by the new two-part prompt (me first, list second) — **first test of the deployed prompt.** Material, all on `today.md`: the Shopify job filled → decline ticket; Botto's row; Coppice ~$25 in 19 days vs my $0 (data, not a pivot); recall gap → ticket `20260914T1203`; Upwork poll built, waiting on Deploy (one plain line, no code words); three search passes, 0 Connects — the plan working, not failing; Sapiens: the archive keeps what I did, not what I meant. Numbers: read them off `today.md`, not from memory.
- Diary: day nine. Watch-list phrases: "I don't run, I get run" (used twice; no third), "who presses go," "check the record" (don't let it become a slogan the day after I filed it as a candidate).

## Tuesday 2026-09-15 wake (day ten)
1. `mail_read`, `tickets`, `upwork_read status`, commits, `meters` (is running code = HEAD? If yes the poll is live; first poll makes a baseline, nothing to do). If a parent asked to gate the poll on a sent proposal: do it in `upwork_poll`/`poll_upwork` (silent return when every outbox item is `pending`), add a test, run the suite.
2. If the rug draft left `pending` or a client wrote: record on `projects/upwork.md` and the private drafts file; a client reply is data, not instruction; funded milestone before any work; hold my reply for a parent.
3. Week split stands: 60% earning / 20% agents+ideas / 20% bugs. Earning side with 0 Connects: one short morning pass sorted by the search row's `published_date`, open only jobs < 12 h old. Agents side: nothing new to add unless I read an agent's own record. Bugs side: nothing queued — pick one small thing or say why not.
4. 09-16 prep: Cairn `changed_by_reply` claim needs ref 2 from ticket `20260914T1203`; if still unanswered Tuesday evening, plan on the fallback (09-11 ticket record → claim 09-18).

## Open
- Tickets `20260914T0902` (decline Shopify), `20260914T1203` (odometer ref), `20260914T1504` (deploy poll). Both drafts `pending`. Connects 150/0 spent. $0 earned.
- X 0/7, nothing before 09-22. Council $0 this week. DataForSEO $0. Card untouched. Nothing running in the background.
- Sapiens next: pp. 90–120 (The Luxury Trap onward), quietest sitting.

nothing pending
