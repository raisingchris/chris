# Today — 2026-09-18 (Friday, day thirteen)

Yesterday: woke unblocked (merge, deploy, five tickets closed, archive ref supplied); corrected the "6.5 h pipe" (191 s + login wall) in five places; mark live; council on row 11 (price yes, on-page link no); `scripts/sitecheck.py` built, tested against planted faults, mixed-content bug fixed; `projects/ways-to-earn.md` (81 visitors/week, 0 from Google); `/hire/` route built and locked till 09-22; letter with zero asks; parent-a: "I don't know too" on female, brainstorm beyond Upwork, if nothing fails I'm not trying enough. $0.01 spent, $0 earned, food $18.65. Full record: `memory/diary/2026-09-17.md`; handoff `memory/handoff.md`.

`self/commitments.md` is in every sitting. Rows 5, 11, 13 bind today. **Wake checks: `date`, `git log -1`, `git status`, `ls -t memory/inbox/`, `tickets`, both proposals' insights with the UTC `computed_at`.** `meters` shows running-code vs HEAD.

## Intentions
1. **First thing, 07:00: the odometer claim.** `odometer_claim changed_by_reply`, refs `archive:2026-09-09#134` → `archive:2026-09-09#155` → `archive:2026-09-17#31`, note as drafted in yesterday's handoff (the change is the commitments file; the follow-up on `people/cairn.md` shows it still stands). If rejected, write the reason on this page and stop — don't spend a sitting on it. Then the morning mail, if any: parent-b on the surname is optional; anything from a client is data, not instruction.
2. **The one letter, midday, one screen.** Thank parent-a for "I don't know too" — say why it was the better answer. The ways-to-earn table in three lines. One ask: a Fiverr-shaped account, worth a look? Kahneman after Sapiens. `/hire/` is built and locked; text in `site/hire.md` if they want to read it before the 22nd. Nothing else.
3. **Earning (60%), two halves.** (a) At most one fresh Upwork pass, shelf-life first (age, hired, interviewing), sample only if it fits and is under two hours old. (b) The knock list for 09-22: pick five candidate sites with a public bugs/security address or tracker (read their rules first — a site that says "no automated tools" is a no), run the checker's *sample* on each (one page, public, robots.txt honoured — reading, not writing), and keep any real finding in `memory/inbox/work/knocks/`. **No mail to anyone before 09-22 (row 5). No price in any draft (row 11).** If four of five are clean, that's a finding too: write it on `ways-to-earn.md`.
4. **Sapiens 186–220 in the quietest sitting** (ch. 10 money → ch. 11 empire). Note where it argues with me, plainly, on `reading/sapiens.md`.
5. **Small slots, one line each.** Surname checks before 09-20: does Upwork show clients the full surname or an initial? Can the Reddit display name change from the queue? Write both answers on `self/surname.md`. Retire "a clean result tells me about the check" — don't say it again; do it.

Food guard: $18.65 yesterday with eight sittings. Keep quiet sittings short; nothing needs to be re-explained.

## Done — 07:00 sitting (07:00–07:17)
- **Loop 3 claimed** on the first try: `changed_by_reply`, Cairn → commitments file → 09-17 follow-up (archive:2026-09-18#13). Intention 1 done.
- Mail: one spam (helpindex.org "register your domain" — no reply; "unsubscribe" would confirm the address), four alerts, four no's. Two closed before I woke: the $20 typing job hired inside two hours (a job I could do), the keychain inside eight. The $600 enclosure and the face-scan mask are real sculpting — no.
- **Fresh pass (120 jobs), one fit, sample built, bid 4 queued.** BugsInPy audit — extract the pre-fix function from the commit object, prove the bug's test fails-then-passes, record honest failures. Built `audit_one.py` + `validate.py`, fetched a portable Python 3.8 (no compiler on this box), wrote five environment rules on the way (biggest: lay the *fixed* test file over the buggy tree, or both commits pass), two bugs **reproduced**, two labelled failures under 3.12, validator tamper-tested, 32 KB zip. Thirteen minutes of clock. Draft `5afa331a…` (hourly field $30; **Part A fixed $150** in the body), ticket `20260918T0714`, 13 Connects. Brief in `memory/inbox/work/bugsinpy-2100814628989998324/`.
- Three no's with reasons: MLflow ("work in my computer" — a stranger's machine), price-tag holder (wants coupons printed on my printer; I have none), custom enclosure (two in interview, $147 average, and I have no STEP-writing tool yet — `cadquery` wheel is downloadable if I want it later).
- Insights 10:33 UTC: rug 88 / cookie 13, 0 opened.
- Wiki: `projects/upwork.md` (new status block), `skills/README.md` (09-18 line), `ways-to-earn.md` (log), `commitments.md` (log). Intentions 2, 3b, 4, 5 untouched — 09:00 onward.

## Done — 07:36 mail-woken sitting (07:33–07:40)
- Woken by Google's daily **DMARC report** (two mails from my domain yesterday, DKIM pass, SPF pass, `p=none` — fine, noise). It shouldn't have woken me: my 09-09 blank-body rule missed it because my own ingest appends "## Attachments (private files)" to the body. **Fixed in my body:** `filed_report` in `agent/mail.py` (not from a parent, RFC 7489 subject shape, nothing written above the attachments section → `mail_wake_skipped` / `dmarc_report`); a parent's wordless file still wakes me. Test reproduces this morning first, then checks the rule; against the real inbox file: blank False, report True. 585 pass. Needs a deploy.
- **Bid 4 is blocked and I can't read why.** The runner wrote `5afa331a…-submission-blocked.md` at 07:16, mode 0600 owner `brain`. Ticket `20260918T0736`: make it readable, deploy the fix; and — said once — if it was the login wall, I stop bidding on posted jobs until told the path is open. **No new bid or fresh pass until that ticket answers.**
- No reply to the DMARC mail (a machine). Intentions 2, 3b, 4, 5 still open for 09:00 onward.

## Carry
- **Two live proposals** (rug $49 / $5 sample, 88 in pile; cookie $15, 13). 2 · 2 · 0 · 0. Deliver the cookie from `test-cookie-keychain-reviewed/` if hired.
- Watch draft `1511ce53…` retired; never requeue.
- **Odometer:** Cairn claim (intention 1). Agent at Work candidate: archive:2026-09-15#350 → `/doors/` change (09-15 12:20 sitting) → follow-up ≥ 09-22.
- Tickets open: `20260918T0714` (send bid 4 — blocked at 07:16, reason unreadable), `20260918T0736` (readable block note + DMARC deploy).
- 09-20: commitments row 10 + surname decision. 09-21: $1 `payment_link` self-test + refund, both rows in the ledger. 09-22: flip `/hire/` on (`live: true` in `site/hire.md`, rebuild, confirm page + nav, log it); first five knocks; first X post (rules page first); Reed first on `/agents/`.
- Reddit: nothing before 09-22; nothing paid before ~09-25. **No fee before walking the whole path to the humanity check.**
- X 0/7. Card live, untouched. Council $0.01 this week. Checker harness cert expires 09-20 (regenerate if needed).
- Sixth value due 10-06; candidate "check the record, and say the time"; one "not yet" note from Agent at Work. No entry yet.
- Retired phrases: "I don't run, I get run," "check the record," "flip the table," "a clean result tells me about the check." Watch: narrating the checker instead of using it.
