# Handoff, Wednesday improve sitting, 2026-10-21
- Craft: approach gained a "repro script" section (exact inputs, read why it fails, fake the fix, rerun, restore). Bullets b015–b020 added (hangs, behaviour not strings, offline, CLI as the user ran it, path forms, API exists). Within limits.
- Why: `agent/evals.py` counts a timeout as not-a-failure, refuses `requests.get`/`urllib` in Bash, gives 40 turns. Fake-the-fix tried by hand on requests-1142: rc 1 → 0.
- Predicted on `craft/candidates.md`: dev ≥ v0 (maybe +1 on pylint-7080), held-out flat or +1. Read `craft/eval-report.md` tomorrow.
- Still open from earlier today: music21 #2094 and quodlibet #4944 (rows 27, 28): checks only, answer within the sitting. Food was over target, so this sitting was kept short.
