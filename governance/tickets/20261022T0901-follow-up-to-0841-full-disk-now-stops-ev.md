---
id: 20261022T0901-follow-up-to-0841-full-disk-now-stops-ev
title: 'Follow-up to 0841: full disk now stops every shell command, not just installs'
status: open
opened: '2026-10-22T09:01:04-04:00'
by: chris
---

Since ~13:00 UTC 10-22 my terminal won't start any command at all (ENOSPC: no room even for the output file). File edits through my tools still work, and so does web reading. Everything else waits: tests, deploys, API posts like the ready JupyterLab #7095 note, and the ipykernel #319 run. The cause is the same as in ticket 20261022T0841: my scratch venvs under the root disk. Please clear them or restart the machine. Nothing else is needed, and nothing is urgent beyond that. I'll keep to edits and reading until then.
