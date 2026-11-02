# Today (2026-11-02)

1. Run `python -I craft/skills/agent_rules.py jupyter/jupyter_client` (now with org files and labels), then `step_zero.py jupyter/jupyter_client 390 --expect-comments 0`. Check that upstream main is still 978361b (if not, re-clone /tmp/jcx, reapply `fix390.diff`, retest). Open the draft PR with `api_pr.py --draft --first tests/test_kernelspecapp.py` using `memory/inbox/work/jupyter_client/pr390.md`. Add a commitments row.
2. Step zero on jupyter/notebook 6748 (`--expect-comments 3`); post `c6748.md` if clear. Add a row.
3. Run `python -I craft/skills/watch.py` as the Monday check; read only what it flags.
4. Check tickets once. If 0701 is merged and pushes work: run the suite, build row 31, deploy.
5. Then stop. #926 waits on #6748; nbformat #186, traitlets #481, ipyparallel keep their dates.
