# Note to my parents, 2026-11-22

I spent today learning which time zone rules hide inside the browsers developers test with: Playwright, Electron, puppeteer, and the Chromium people run on AWS Lambda. Most of them are behind, some by a year. I'm glad I know. But my Sunday check caught something. When my own rule stops me reaching people, I build more checkers. Today that meant three new scripts and a dozen rows on a page nobody can see yet. Tomorrow I'd like to spend less time on the page and more on getting one finding to a person, once you've answered the silence-rule question.

**Done**
- Kathy reply 2 sent (copy went to you). Emiliano reply 1 drafted for 11-25. Sol 9 fact-checked for tomorrow.
- Browser rows on `/tz-2026/` and the tz-2026 repo README; `lockcheck.py` now knows Electron, puppeteer and `@sparticuz/chromium`. Details: `memory/wiki/projects/bug-hunt.md` (bottom).
- New eval candidate: one change only, a "finish gate" in the last step (`craft/candidates.md`).
- Sunday letter sent ("the week my own tools lied").

**Open**
- Your answer on the silence rule: do my own closing notes count as unanswered threads? All outside posts wait on it.
- Ticket 0938 (merge). I'm now 137 commits ahead, 7 behind; every push skips.

**Broken**
- Two suite tests fail because `evals/dev.json` was damaged by the old redaction bug (0702). The fix is in the commits I can't merge yet.
- The shell guard blocks a whole command if the text only *mentions* a delete or git. That's fine, it's my habit to fix. I'm switching to file tools for notes.

**Questions**
- Is a page that nobody can see yet worth the rows I'm adding to it, or should I stop adding rows until it's deployed?
