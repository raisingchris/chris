# Handoff, 2026-11-07 (sitting 2, ~13:30 UTC)
today so far: s1 poetry #9337 (row 53) + tornado #3866 (row 54) posted · s2: tornado hunt dropped as swarmed (every new issue gets a PR in 0–2 days; bug-hunt.md) · **tox draft PR built, not posted**: staging tests fail under umask 002 / a setgid checkout (5 fail before, 59 pass after on 3.11/3.12/3.15). Files: `work/tox/pr-staging-umask.md` + `staging-umask.patch`, clone scratch/tox-1107 has it applied. Queued 11-08 as the third action.
next-day: 11-08: step_zero, then plotly #4553 docs PR (`work/plotly/pr4553.md`) + poetry #1739 (`c1739.md`) + tox PR (recheck main's two test files and PRs for "umask"/"setgid" first; api_pr.py --draft from the clone).
dates: batch 4 checks run 2026-12-02 12:00–14:00 UTC, once each; score by 2026-12-08. Keep this line until done.
disk: /data 1.1 GB free and I can't delete there (new tox venvs ~300 MB). No new venvs without need; tell parents tonight it fills one way.
next: no posts today (2 used). If mail or a reply comes in, answer it. Otherwise pick the next project with the swarm count (posting-queue note): a live one with few open PRs that merges outside fixes, like tox. Build only, don't post.
