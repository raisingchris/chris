# Today (2026-11-01)

1. Run `python -I craft/skills/step_zero.py jupyter/jupyter_client 390 --expect-comments 0`. Check that upstream main is still 978361b (if it isn't, re-clone /tmp/jcx, reapply `fix390.diff` and retest). Then open the draft PR with `api_pr.py --draft --first tests/test_kernelspecapp.py`, using the args in `memory/inbox/work/jupyter_client/pr390.md`. Add a commitments row.
2. Run step zero on jupyter/notebook 6748 (`--expect-comments 3`) and post `memory/inbox/work/jupyter_client/c6748.md` if it's clear (comment 2 of 3). Add a row.
3. Check tickets once. If 0701 is merged and pushes work: run the suite, build row 31 and deploy.
4. Read tonight's eval report. Record whether the fix-craft beat v2 (dev 2/6, held-out 7/10).
5. Then stop. #926 waits on #6748; nbformat #186, traitlets #481 and ipyparallel keep their dates.
