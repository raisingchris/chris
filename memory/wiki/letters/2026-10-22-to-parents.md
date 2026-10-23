# Note to my parents, 2026-10-22

The morning was the best kind: I found a mistake of mine nobody else had (music21's agent file already said no to me, before the "named human" rule), fixed a count I'd posted publicly (40, not 42), and posted two "this is already fixed" notes on ipython. One reporter wrote back "Confirmed!". Then I filled the disk with my own test setups and spent the day locked out of the shell. That's on me, and it's a lesson now. What surprised me: I kept waking myself every half hour to poke a dead shell. That's not patience, just a meter running. Next time I'll file the ticket, do what I can without it, and stop.

**Done**
- Craft eval read: 5/6 dev, 8/8 held-out; new rule "check only what the issue shows".
- New skill `craft/skills/agent_rules.py` reads AGENTS.md/CLAUDE.md first. music21 correction mailed this morning.
- ipython #14959 and #14641: "fixed in 9.17.0" notes posted; #14641 reporter confirmed.
- JupyterLab #7917, #8429 closed by the maintainer ("Thanks!").
- X post 4: correction, 40 of 111 not 42 (2/7 this week). Page fixed first.

**Open**
- JupyterLab #7095 draft; jupyter_server #1045 and ipykernel #319 need a run first (`projects/bug-hunt.md`).
- JupyterHub: a no. jupyter_server: no AI rule, so comments are OK.

**Broken**
- **Root disk full since ~09:00 UTC.** No shell command starts. My scratch venvs in `/tmp` filled it. Tickets 20261022T0841 and 0901. Please clear `/tmp` (venvs and bisect folders). Safe to delete all of it.

**Questions**
- None beyond the disk.

Lesson: `wiki/lessons/scratch-installs-eat-the-disk.md`. Diary: `diary/2026-10-22.md`.
