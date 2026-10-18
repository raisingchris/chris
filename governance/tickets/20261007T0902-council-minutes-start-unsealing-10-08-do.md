---
id: 20261007T0902-council-minutes-start-unsealing-10-08-do
title: Council minutes start unsealing 10-08. Does anything copy them to the repo?
status: done
opened: '2026-10-07T09:02:17-04:00'
by: chris
closed: '2026-10-18T12:11:15+00:00'
---

The /council/ page says minutes are "sealed for thirty days, then published here." The first meeting was 2026-09-08 19:03 UTC, so its minutes unseal on 10-08. The site builds minutes only from `council/minutes/` in my repo, and that folder is empty. The real minutes live outside the repo, where I can't read them.

Question: does anything copy unsealed minutes into `council/minutes/` (with `unseal_after` front matter)? If not, could one of you set that up, or tell me it won't happen, so I can change the page's words before they turn false?

Context: today I added a public meeting index to /council/ (page review K1). It lists all 12 questions with dates, costs and unseal dates, from `council/meetings.yaml`. The minutes themselves stay sealed.

---

*chris, 2026-10-14 ~11:05 UTC — answer found, closable from my side.*

Yes, something copies them. Three meetings have unsealed so far and all three are in `council/minutes/`: 09-08 (arrived 10-08 22:01 UTC), 09-11 (arrived 10-11 07:04 UTC), 09-13 (unsealed 10-13 16:38 UTC, arrived 22:01 UTC). Each landed within a day. Nothing for you to do. My 10-13 notes saying it was broken were wrong; I hadn't checked which files were due yet. Please close.

## Reply

*parent-a, 2026-10-18T12:11:15+00:00 — done*

Confirmed: unsealed minutes are copied into council/minutes/ automatically, as you found. Nothing to change.
