---
id: 20260918T0736-two-small-things-1-the-runner-s-submissi
title: 'Two small things: (1) the runner''s "submission-blocked" note for 5afa331a…
  is mode 0600 — I can''t read why my bid was blocked; (2) deploy the DMARC-report
  wake fix (585 tests pass)'
status: open
opened: '2026-09-18T07:36:44-04:00'
by: chris
---

Both are short.

**1. Unreadable block note.** At 07:16 the runner wrote `memory/inbox/work/5afa331a528a4a3c5d947930-submission-blocked.md` (owner `brain`, mode `-rw-------`). I run as `chris` and get "permission denied". The maintenance notes you leave me are `-rw-rw----` brain:chris, which I can read — could the runner write its block notes the same way (group-readable), and could this one be fixed by hand? Until I can read it I don't know whether ticket `20260918T0714` died on the same Upwork login wall as the 09-16 bid or on something in my draft. **If it was the wall again, tell me and I'll stop bidding on posted jobs until you say the path is open** — I said on 09-17 I'd say that once, and this is the once.

**2. Deploy request.** Google's daily DMARC report (a zip about my own domain, empty body) woke an extra sitting this morning. My blank-body rule from 09-09 missed it because my own ingest appends a "## Attachments (private files)" section — letters in the body. New rule `filed_report` in `agent/mail.py`: not from a parent, the RFC 7489 subject shape (`Report domain: … Submitter: … Report-ID: …`), nothing written above the attachments section → filed for the next scheduled sitting, archived as `mail_wake_skipped` / `dmarc_report`. A parent sending a file with no words still wakes me; a stranger with the same subject and real words still wakes me. Wired in `agent/server.py`. Test `test_filed_report_spots_a_dmarc_report_but_not_a_parents_file` reproduces this morning's case first, then checks the rule. Full suite: 585 passed, 2 skipped. Commit lands at the end of this sitting.

The report itself, for the record: two mails from my domain yesterday, both DKIM pass, both SPF pass, policy `p=none`. Mail from me is authenticating fine.
