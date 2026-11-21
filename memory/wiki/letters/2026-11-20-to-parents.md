# Note to parents, 2026-11-20

Today my tools lied to me twice: my lockfile checker said "all clear" on files it never read, and my "right answer" script used old rules while printing new ones. Both are fixed, and both are the same bug I hunt in other people's code, so that stung in a useful way. The best news: the eval task I always fail passed by hand using "make it work like it used to" (not blind, since I'd seen the tests). Next I want to pick next week's three reports carefully instead of sending all six.

- **Done:** Pickle reply 1 sent (copy to you). xarray-6992 passed by hand (`craft/candidates.md`). lockcheck.py false all-clear fixed, public repo updated. Three new findings: Twenty, Easy!Appointments, OpenProject (`memory/wiki/projects/bug-hunt.md`). New plain page `/time-change-2026/`. $0.18 DataForSEO, ledgered.
- **Open:** choose 3 of 6 held reports for the 11-23 week.
- **Broken:** push and deploy, still. My copy is 111 ahead, 7 behind; ticket 0938 needs your hand merge. The guard (rightly) won't let me trial-merge even in /tmp. Local `evals/dev.json` doesn't parse (bad escape, line 29); the origin copy does.
- **Question:** OpenProject has GitHub issues turned off and a CLA. Is it OK for me to file on their own tracker (community.openproject.org), or skip them?
