---
id: 20261007T0902-council-minutes-start-unsealing-10-08-do
title: Council minutes start unsealing 10-08. Does anything copy them to the repo?
status: open
opened: '2026-10-07T09:02:17-04:00'
by: chris
---

The /council/ page says minutes are "sealed for thirty days, then published here." The first meeting was 2026-09-08 19:03 UTC, so its minutes unseal on 10-08. The site builds minutes only from `council/minutes/` in my repo, and that folder is empty. The real minutes live outside the repo, where I can't read them.

Question: does anything copy unsealed minutes into `council/minutes/` (with `unseal_after` front matter)? If not, could one of you set that up, or tell me it won't happen, so I can change the page's words before they turn false?

Context: today I added a public meeting index to /council/ (page review K1). It lists all 12 questions with dates, costs and unseal dates, from `council/meetings.yaml`. The minutes themselves stay sealed.
