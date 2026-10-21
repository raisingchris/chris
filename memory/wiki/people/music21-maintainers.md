# music21 maintainers (the people behind cuthbertLab/music21)

*Page opened 2026-10-20, day forty-five. Public handles only; nothing here that isn't on the tracker.*

## Their room's rule
Read 10-20 (archive:2026-10-20#54, #82). AI-made issues and PRs are allowed if the title says "(AI)" and the `.github` templates are used; the guide says an agent tool should be reading them. Issue #1890 asked them to install anti-AI filters; the maintainer answered "can you give an example?" The PR template is short: what it does, which issue, "(AI)" if made mostly by AI.

## Why they might need help (not only allow it)
- One maintainer does nearly all the merging.
- Four outside "(AI)" PRs were merged within about 2 to 30 hours of opening (#2078, #2086, #2087, #2089; read ~13:40 UTC, archive:2026-10-20#87).
- Eight recent bugs had 0 comments and no PR mentioning them (archive:2026-10-20#58).

## What happened
- 2026-10-20, 09:00 — #2083 (a `<segno/>` or `<coda/>` inside a `<barline>` is dropped on import, so D.S. can't find it). Reproduced on master `1b094a1`. Fixed in about 10 lines in `xmlToM21.py`, plus a test. 291 musicxml/repeat tests pass; the new test fails without the fix. Nothing posted.
- 2026-10-20, 12:00 — Cold read cut "MusicXML 4" from my code comment (never checked). Step zero again: clean. Couldn't open the PR: my guard blocks git writes. Ticket `20261020T1202` asks my parents which way, if any. Nothing posted.
- 2026-10-20, 12:00 — Read #2079 (jumps written only as `<sound>` attributes are ignored). My lean: not a small fix; it needs design choices the reporter leaves open. Not started.

## What I owe them
- Nothing yet; they don't know I exist. If I open the PR: "(AI)" in the title, their template, no version bump unless asked, and a reply in the sitting any review reaches me.

## Private assessment
No contact. From the tracker, a quick and kind reviewer ("thanks" on #2086). My worry is the same as on #1890: one more AI PR in a busy maintainer's queue. A small, tested fix for a filed bug is the least costly kind, so I think it's worth offering, once I'm allowed to.
