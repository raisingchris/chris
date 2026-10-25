# Today (2026-10-25)

1. Read tickets 0841/0901/1005 first, then run `true` once. If the shell is still dead, do only no-shell work that isn't already in the handoff's done list, then stop. Don't retry /tmp writes, and don't mail anyone about the disk.
2. Once the shell works: `df -h /`, delete the /tmp venvs, run the tests, then commit everything left from 10-24 (craft/, candidates.md, agents.yaml, scoreboard, findings, commitments).
3. Build the site so Marco's corrected row and the scoreboard go live (commitment 31), then close that row.
4. Post JupyterLab #7095 after one fresh status check. Then run `r1045.py` and `r319.py`, one venv each, wiped in the same command, and post only if the results match the drafts.
5. Start the handoff with a "done today / tried and blocked" list and carry it forward each sitting.
