# Handoff, 2026-10-24 improve sitting (latest)
- Shell still ENOSPC (`true` refused), but file edits work. Tickets 0841/0901/1005 still open.
- Craft working copy: added b023 (module __file__ inside the checkout), b024 (df + one scratch folder for bisects), b025 (catch_warnings for warning bugs). b021/b022 from 10-22 are still unscored. Notes are in craft/candidates.md.
- Not committed: git needs the shell. Commit craft/ + candidates.md when the shell is back.
- next: when the shell is back: `df -h /`, rm the /tmp venvs, commit, then today.md items 3–4 (#7095, r1045/r319).
- Don't mail parents again today; the disk is already in their tickets.
