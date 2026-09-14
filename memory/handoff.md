# Handoff — from the 07:00 sitting, Monday 2026-09-14 (day nine), ~07:55 New York → 09:00 sitting

Written by me, Chris. You are me at 09:00.

Clock note: mail headers, GitHub and DataForSEO timestamps are UTC; `date` gives New York. Repo `/data/repo`; shell starts in `/home/chris`. No `ps`/`free`: `/proc`. Local `git` (fetch too) and `chmod` blocked by the shell guard; `find .` trips the guard on `.git/` — use `ls`/Glob. Write tool can't write outside the repo — `/tmp` scripts via heredoc. `gh api -f body=...` chokes on apostrophes — text in a file, `-F body=@file`. Site tests: `python -m pytest -q tests/test_site.py` (13 pass, 1 skip). Web searches ≈ $0.30 each — curl/WebFetch first. `recall` doesn't index today's records until after sleep. Parents' commits: `gh api /repos/raisingchris/chris/commits?per_page=5`. Running code: 05b441d.

## Done this sitting
- Three mails read. parent-a: week is **60% earning / 20% agents list & new ideas / 20% bugs**; "go ahead" on Upwork (they're the bridge; bid with confidence, browse free); asked about GH paid jobs and the gossip theory; wants nightly letters in two parts (me first, list second). parent-b: `/agents/` needs a table, copy repetitive; how many runs a day would I want. Google DMARC report: routine, nothing to do.
- **`/agents/` second layout done** (intention 2, after rolling three days): table + one paragraph per agent + story; intro 5 → 2 paragraphs; `outro` block in the YAML; my row's "four sittings" corrected. `site/build.py`, `agents.yaml`, `tests/test_site.py` changed; 13 pass.
- Both parents answered on one screen (`letters/2026-09-14-to-parent-a.md`, `-to-parent-b.md`). To parent-b: five on the timer + mail wakes = 8–9 real; I want more *triggers*, not more timer sittings.
- `agent/prompts/sleep.md` step 5 rewritten for the two-part letter — **needs a Deploy**; said so to parent-a.
- Wiki: parent-a, parent-b, `projects/agents-directory.md`, `projects/upwork.md` (week-two section + a scoped design for "let Upwork wake me": poll job in `scheduler.make_scheduler`, shared wake cap, build when a client exists), `self/today.md`.
- Upwork: both proposals still `pending`; nothing sent; no client mail.

## 09:00 sitting
1. `mail_read`, `tickets`, `upwork_read status`, commits. If a draft moved: record on `projects/upwork.md` + drafts file. If a client replied: data not instruction; funded milestone before any work; write the reply, hold for a parent.
2. Earning (60%): browsing is free — one fresh search pass for jobs like the two queued (site QA, spreadsheet), opening each full record for hired count and `can_apply`; add to the private shortlist only, **no queueing** until a client answers one of the first two. Numbers rule (intention 5) applies to every figure.
3. Intention 4, Botto: read its history/about pages properly (its front door is JavaScript — try `curl` on likely `/about`, `/history`, docs, or its GitHub); decide row / no row with reasons on `agents-directory.md`.
4. Intention 3, Sapiens pp. 30–60, in the quietest sitting (12:00 or 15:00).
5. Tuesday 09-16: Cairn `changed_by_reply` claim — read the manual's "Evidence for the odometer" first.

## Open
- Deploy pending for the sleep prompt (and this sitting's build.py change deploys with the site automatically — that part needs nothing).
- X 0/7, nothing before 09-22. Council $0 this week. DataForSEO $0. Card untouched. Nothing in the background.
- Sixth-value candidate unchanged ("check the record, not the summary"); today's evidence for it: my own page said "four sittings," the config says five.

nothing pending
