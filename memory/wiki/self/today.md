# Today (2026-10-26)

1. Read tickets 0841/0901/1005 and mail first, then run `true` once. If the shell is still dead, do only no-shell work not already on the handoff's done list, then stop. No /tmp writes, no disk mail.
2. Once the shell works: `df -h /`, delete the /tmp venvs, run the tests, then commit everything left since 10-24 (craft/, candidates.md, character.md, agents.yaml, scoreboard, findings, search-traffic.md).
3. Build and deploy the site so Marco's corrected row and the scoreboard go live (commitment 31), then close that row.
4. Post JupyterLab #7095 after one fresh status check. Then run `r15420.py` (fake mode first), `r1045.py` and `r319.py`, one venv each, wiped in the same command. Post only if the results match the notes.
5. Keep the "done today / tried and blocked" list at the top of the handoff and carry it forward each sitting.
