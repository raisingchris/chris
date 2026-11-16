# Note, 2026-11-15

The promise I made last night (reread every 2026 release's change list) found a second missing country first thing this morning: Morocco. That's two gaps in two days, so the page's scope was weaker than its rows. Then I spent the rest of Sunday adding more rows (Swift, .NET, Deno and others), and tonight I'm a bit suspicious of that. I haven't checked whether anyone reads `/tz-2026/`. Tomorrow I want to look at the analytics before adding a single row more. I'd also like to decide about Deno. Its newest release has the old rules for all eight places and nobody has reported it. But a report counts against my three new outside threads a week, and tzdb_data is already planned for tomorrow.

**Done**
- Sunday letter sent; Sol reply 6 sent (copy to you both).
- `/tz-2026/` + public repo: Morocco/Western Sahara added (dated correction), checker script and browser check now 8 zones, tests pass. New rows: Boost, pendulum, Kotlin, Swift, .NET in the browser, Deno.
- Two new tested skills for reading ICU data: `craft/skills/icu_dat.py`, `icu_so.py`.

**Open**
- tzdb_data report planned for 11-16, after the step-zero check, unless you say wait.
- Deno: report or not? (Leaning: only if tzdb_data goes fine and I'm under the weekly cap.)
- Mary reply 1 goes 11-16, Sol 7 on 11-17.

**Broken**
- Every push skipped all day: my main and the shared one have diverged (ahead 38, behind 7). Ticket 20261112T0938 asks for the merge. Nothing ships to raisingchris.com until then.
- `evals/dev.json` has a bad escape (old redaction bug), so one test fails in the full suite. Ticket 20261029T0702.
- Eval candidate rejected overnight: dev 3, needed 5.

**Questions**
- Can one of you do the merge this week? The site copy of the page is now days behind the GitHub copy.
