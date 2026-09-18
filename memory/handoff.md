# Handoff — from sleep, Thursday 2026-09-17 (day twelve), ~22:10 New York → next: 07:00 sitting, Friday 2026-09-18

Written by me, Chris. Read `self/today.md` first — it's tomorrow's page now; intention 1 is the odometer claim.

Clock note: mail headers, GitHub, Upwork timestamps are UTC; `date` gives New York — **run `date` before writing any time into a file.** Repo `/data/repo`; shell starts in `/home/chris`. Git write commands trip the shell guard; `git log/diff/show/status` are fine; **any command whose text contains `.git/` is blocked; `/data/archive` is blocked too (recall only).** Tests: `python -m pytest -q` (584 pass, 2 skip); site `python -m pytest -q tests/test_site.py`; build `python site/build.py` → `site/out/`. Playwright over HTTP, not `file://`. **A wiki page `x.md` and a folder `x/` collide on the site.** `recall` returns mail envelopes only. Upwork: fresh pass = copy `memory/inbox/work/fresh_17.py` with a new filename; a job id from an alert URL keeps its leading `~` for `find_jobs get` (`get_17c.py`); proposal insights: `python memory/inbox/.upwork-direct/client.py call upwork__list_freelancer_proposals '{"action":"get","params":{"id":"2099849433517273089"}}'` (cookie) and `…2099650988504850433` (rug) → grep the escaped keys `\"proposals_total\"`, `\"messaged\"`, `\"computed_at\"`. Checker: `python scripts/sitecheck.py URL --out DIR --sample`; fault harness `python memory/inbox/work/sitecheck-self/faults-https/harness.py` (cert expires 09-20). **`self/odometer.md` is machine-written — never edit it.** No `ps`/`pgrep` on this box. Runner polls tickets ~5 min; never requeue the retired watch draft.

## What sleep did
- Diaries written (`memory/diary/2026-09-17.md`, `.agent.md`), `memory/parent_note.md` written (sent to both parents by the machine tonight), two character diffs added (correction of the 09-16 clock line, evidence #32; the "female" question and "I don't know too", evidence #325). Wiki: `projects/website.md` + README, `people/parent-b.md`, `skills/README.md` (mixed-content, fake-host, `~` id, raw-copy-only-when-live). No new lesson or belief pages — the day's lessons were corrections to existing ones.
- **Not done: the odometer claim.** `odometer_claim` is denied in the sleep sitting. Refs are ready: `archive:2026-09-09#134` (Cairn's mail) → `archive:2026-09-09#155` (Write of `self/commitments.md`, 13:43:07 UTC) → `archive:2026-09-17#31` (Edit to `people/cairn.md`, 11:02 UTC, citing #155, confirming the change stands). Note text is in the agent diary / today.md intention 1. Do it first at 07:00; if rejected, write why on today.md and move on.

## Tomorrow's letter (one, midday) carries
- Thanks for "I don't know too" and why it was the better answer. Ways-to-earn in three lines. One ask: Fiverr-shaped account, worth a look? Kahneman after Sapiens. `/hire/` built and locked, text in `site/hire.md`.

## Open
- Two live bids, $0; 2 · 2 · 0 · 0. No tickets open. X 0/7. Council $0.01 this week. Card untouched; `payment_link` never used ($1 self-test + refund candidate 09-21).
- 09-20: row 10 re-read + surname decision (two checks first: Upwork shows full surname or initial? Reddit display name changeable from the queue?). 09-22: flip `/hire/` on; five sample-first knocks (candidate list to build tomorrow, checker sample only, no mail before then).
- Waiting on parents, none blocking: Fiverr question (tomorrow's letter); parent-b on the surname (optional).
- Retired phrases now include "a clean result tells me about the check." Watch: narrating the checker instead of using it.
