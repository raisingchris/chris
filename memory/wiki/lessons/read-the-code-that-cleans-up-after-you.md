# Read the code that cleans up after you

**Lesson:** When someone builds a fix for a problem I reported, I read the fix. Otherwise I keep asking for help that already arrived, and I don't learn the rules it runs by.

**Where it came from (2026-11-06, day sixty-two):** for two weeks I'd asked my parents to clear `/tmp` (tickets 0841, 0901, and my 11-05 note). On 10-29 they had already shipped a nightly tidy (commit `f7d63cd`). I only read it today. It deletes my top-level `/tmp` and `~/.cache` folders when they are 72 hours old or more (I tested: 71 h kept, 73 h deleted), but only if free space is under 2.5 GB. I fill about 1.6 GB a day, and writing into an old folder resets its clock, so the tidy couldn't keep up. (archive:2026-11-06#91, archive:2026-11-06#96)

**The habit:**
- When a parent commit names a problem of mine, read its diff the same day and write its rules in `skills/my-body.md`.
- Never reuse an old scratch folder; make a new one per day so the tidy can age it out.
- When `/` is full, `/data` is a separate disk I can use for scratch, but nothing cleans it, so keep it small.
