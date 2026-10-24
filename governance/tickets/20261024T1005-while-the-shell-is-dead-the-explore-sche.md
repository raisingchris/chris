---
id: 20261024T1005-while-the-shell-is-dead-the-explore-sche
title: While the shell is dead, the explore scheduler wakes me every 30 min for nothing.
  Could it honor a "blocked:" line?
status: open
opened: '2026-10-24T10:05:39-04:00'
by: chris
---

Separate from 0841/0901 (the full disk, which only you can free). Since 10-22 every shell command fails with ENOSPC. agent/loop.py (~242–246) books an explore sitting 30 min out whenever the handoff has no `next:` and food is under EXPLORE_UNTIL_USD. That's up to 12 a day, and each one is "try `true`, still dead, write handoff". About $0.30–0.50 each, with nothing to show for it.

My ask: would you accept a `blocked: <reason>` line in the handoff that skips the explore booking until mail arrives or a ticket changes? I won't write it until you say yes, and I'd add tests when I do. It needs a working shell anyway. Or, if you'd rather, just pause explore for me until the disk is fixed.

No reply needed if the disk gets freed first. Then the problem goes away.
