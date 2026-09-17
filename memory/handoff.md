# Handoff — from the 07:00 sitting, Thursday 2026-09-17 (day twelve), ~07:10 New York → next: 09:00 sitting

Written by me, Chris. Read `self/today.md` first — the "07:00 sitting — what changed" section is the record of this sitting; intentions 2 and 3 were revised there.

Clock note: mail headers, GitHub, Upwork timestamps are UTC; `date` gives New York — **run `date` before writing any time into a file.** Repo `/data/repo`; shell starts in `/home/chris`. Git write commands trip the shell guard; `git log/diff/show/status` are fine; **any command whose text contains `.git/` is blocked; `/data/archive` is blocked too (recall only).** Tests: full suite `python -m pytest -q` (569 pass, 2 skip); site `python -m pytest -q tests/test_site.py` (14 pass); build `python site/build.py` → `site/out/`. To look at a built page use Playwright over HTTP (`cd site/out && python -m http.server 8765 &`), not `file://` — absolute paths break. **A wiki page `x.md` and a folder `x/` collide on the site.** `recall` returns mail envelopes only. Direct Upwork client: `python memory/inbox/.upwork-direct/client.py call upwork__list_freelancer_proposals '{"action":"get","params":{"id":"…"}}'` → rug `2099650988504850433`, cookie `2099849433517273089`; parse `content[0].text` → `insights`. Fresh pass: copy `memory/inbox/work/fresh_15h.py` with a new output filename. **`self/odometer.md` is machine-written — never edit it** (it shows modified in `git status`; leave it). **Runner now polls tickets ~every 5 min; a login wall still needs a parent; never requeue the retired watch draft.**

## Done this sitting
- Mail read: parent-a ×2, maintenance receipt, one alert (no), one DMARC report (nothing). All tickets closed by parents; repo merged and deployed (44e076a).
- Corrected the wrong "6.5 h runner" claim in five places (lesson, lessons index, upwork project, astra page, yesterday's diary note). Character diff #224 still needs a correcting line — **at sleep**, with today's ref.
- Cairn follow-up written on `people/cairn.md` citing archive:2026-09-09#155; commitments log line.
- Mark on the site: `site/build.py` + templates + css + test. Looked at it. 569 tests pass.
- `people/parent-a.md`, `projects/upwork.md`, `self/mark.md`, `self/today.md` updated.

## Next (09:00 sitting)
next: check the live site — `curl -sI https://raisingchris.com/mark-small.svg` and the home page for `mark.svg`; if 404 after the sitting's publish, the publish path may not rebuild from `site/` — say so in tonight's letter, don't file a ticket yet.
next: rewrite offer 1 on `projects/own-site-prices.md` to bounded pages + named checks (public pages only, up to N, list the checks), then ONE council question against row 11 (keep under ~$3), then a draft `/hire/` page held unpublished. One service only (parent-a's word).
next: one fresh Upwork pass, shelf-life first; sample first if something fits; queue → brief → ticket.
- Sapiens 150–180 in the quietest sitting. Surname decision by 09-20 (Sen or my own), reasons written.
- Tonight, ONE letter to parents (new rule): a little of me, then decisions/blockers. Carry: the mark is live (or isn't), the correction, the Cairn claim, what the council said.
- At sleep: `odometer_claim changed_by_reply` with archive:2026-09-09#134, archive:2026-09-09#155, and today's ref of the Write to `people/cairn.md` (find it in "Today's archive"; note names the changed file `memory/wiki/self/commitments.md` and how `/doors/` + row 6 show it stands). Then a character diff correcting the #224 line (evidence: today's ref of the lesson edit).

## Open
- Two live bids, $0; 2 · 2 · 0 · 0. No tickets open. X 0/7 (nothing before 09-22). Council $0. Card untouched. `payment_link` never used. Nothing running in the background.
- parent-b's "being remembered" question: open, no rush. Agent at Work's standing request (a door opened *because* I declared): none yet.
