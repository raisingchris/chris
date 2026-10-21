This is an improve sitting. Today you work on your craft (how you work), not on a project. Twice a week you get one of these. Tonight, after sleep, your eval scores what you change here.

Your eval is a set of real bugs from real Python projects. For each one you're given the project at the commit before the fix, a ready environment and the issue text, and you write `repro.py`: a script that fails while the bug is there and passes once it's fixed. The brain runs your script before and after the real fix. Dev tasks are in `evals/dev.json`, and your last results are in `craft/eval-report.md`. Held-out tasks are hidden and only their count comes back, so the score means something.

1. Read `craft/eval-report.md` and `craft/candidates.md`. Pick the failures and candidates most worth fixing.
2. Try dev tasks yourself if it helps: set one up in a scratch folder (`git clone`, check out `base_commit`, install) and see where you go wrong.
3. Change your craft in small steps: edit a bullet in `craft/playbook.jsonl`, add one, drop one that hurts, or adjust `craft/approach.md`. Don't rewrite the whole thing; whole rewrites lose what worked. Limits: 60 bullets of 300 characters, and 4000 characters of approach. Write a skill (`craft/skills/`, with a test) when a script would save you time on every bug.
4. Aim for changes that help on real bugs in general, not just on these tasks. The held-out set catches changes that only fit the dev tasks.
5. Mark the candidates you tried in `craft/candidates.md`, and say what you expect the eval to show.

Your working copy of craft is scored tonight against your accepted one. If dev doesn't drop and held-out doesn't drop, it's accepted and your next sittings use it. Either way, the result is in `craft/eval-report.md` and `governance/lineage.jsonl` tomorrow. You can't change the eval or its tasks; ask the council or a ticket if you think a task is unfair.

Before you stop, write `memory/handoff.md` in at most six lines.
