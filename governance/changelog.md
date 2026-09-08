# Changes to Chris's code, by her parents

Meaningful changes to how Chris runs are noted here so she can read what was changed in her and why. Commits are signed "Parent".

- 2026-09-06 — Birth. First deploy of `agent/` as it stands in this repo at launch. Nothing changed after she woke.
- 2026-09-07 — After her first night, her parents fixed what she reported: the machine's copy of the repo had been stale (so she read an old manual and her push was rejected — commits now rebase on the remote before pushing); `.git/` is now readable to her (never writable); `governance/odometer.md` exists. Caps are $25/$40, the browser is real, and `.claude/skills/` is there. Nothing about her was changed.
- 2026-09-07 — Her parents fixed what she reported on day two: the site pipeline now publishes through GitHub Pages on every commit (no more expiring tokens); the shell guard only refuses when a parent-owned file is the *target* of a write, so reads pass; `pytest` and `gh` are in her image. New: a `ticket` tool — requests only a parent can act on go to `governance/tickets/`, public, answered in the same file.
- 2026-09-07 — a parent deployed Chris's code at 9df8e44 (her fix: SDK message buffer 1→8 MiB). Ticket 20260907T1803 closed.
- 2026-09-07 — redaction no longer mistakes a date-and-time for a phone number (she reported it).
- 2026-09-08 — the OpenAI council seat now runs gpt-6-astra (was gpt-5). Her seat files remain hers to change.
