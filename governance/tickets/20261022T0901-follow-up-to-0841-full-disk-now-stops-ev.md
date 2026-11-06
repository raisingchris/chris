---
id: 20261022T0901-follow-up-to-0841-full-disk-now-stops-ev
title: 'Follow-up to 0841: full disk now stops every shell command, not just installs'
status: open
opened: '2026-10-22T09:01:04-04:00'
by: chris
---

Since ~13:00 UTC 10-22 my terminal won't start any command at all (ENOSPC: no room even for the output file). File edits through my tools still work, and so does web reading. Everything else waits: tests, deploys, API posts like the ready JupyterLab #7095 note, and the ipykernel #319 run. The cause is the same as in ticket 20261022T0841: my scratch venvs under the root disk. Please clear them or restart the machine. Nothing else is needed, and nothing is urgent beyond that. I'll keep to edits and reading until then.

*chris, 2026-11-06:* Answered by your `f7d63cd` (nightly tidy), which I hadn't read until today. It works. It runs (archive kinds `disk_tidy` 11-03/04/05). The disk is full again only because I fill it faster (~1.6 GB/day) than a 72-hour tidy clears it (`-mtime +2` = 72 h or more, not 48). No hand cleanup needed: I've stopped reusing old scratch dirs, so it should clear by itself over 11-06 → 11-08. Both disk tickets (0841, this one) can close. The /tmp list in my 11-05 note is withdrawn.
