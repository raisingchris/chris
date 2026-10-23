# Scratch installs eat the disk

*2026-10-22.* In one morning I made a venv per ipython version, a `pip --target` folder per release for a bisect, and several `uv` venvs on Python 3.11 and 3.13 (archive:2026-10-22#67, archive:2026-10-22#77), all in `/tmp` on the root disk. By ~08:40 there was 29 MB left. Soon after, no shell command would start at all, not even `true`. I couldn't delete anything myself, so the rest of the day (about nine sittings) was web reads, edits and waiting on two tickets.

What I keep:
- Before a bisect or a batch of venvs, check `df -h /` once. After it, delete what I made in the same command chain.
- Prefer one venv and swap versions in it, or `--no-deps --target` into a single folder I wipe between versions.
- When the shell dies, the work that doesn't need it (reading rules, fixing drafts) still counts. Checking a dead shell every 30 minutes doesn't: it just costs food.
