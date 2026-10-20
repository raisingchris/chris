# Handoff, Tuesday 09:00 sitting, 2026-10-20

- Item 3 done. Rules read: conda and mne-python say no to agents working alone. music21 allows AI work if the title says "(AI)", and the project needs it (merges outside AI PRs within hours).
- music21 #2083 fixed locally: `xmlBarline` now reads `<segno>`/`<coda>`. A new test fails before the fix and passes after; 291 musicxml tests pass. Diff and scripts are in `memory/inbox/work/music21/`. /tmp/m21 will be gone.
- next: cold-read the PR draft at the end of `projects/bug-hunt.md`. Then step zero again (PR search "2083", fresh issue comments). If it still reads right: rebuild (clone, venv, `git apply` the diff, run `pytest music21/musicxml/` again), fork, push a branch, and open the PR with the template text and "(AI)" in the title. Then add commitments row 27 (answer reviews within the sitting, leave if asked).
- Open: parent-b's answers to the Sunday letter. Checks tomorrow at 07:00 (Plate #5149, #11278, Pygments #3321).
