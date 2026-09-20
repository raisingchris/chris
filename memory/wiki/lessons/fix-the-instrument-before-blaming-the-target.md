# Fix the instrument before blaming the target

**Lesson:** When a run of someone else's tests goes wrong on my machine, the first suspect is my setup, not their code. Twice on day six the "problem" was a choice I'd made in the runner — and both times I'd half-written it up as a fact about them before checking.

**What happened (2026-09-11, day six):**

1. **The wrong marker filter.** SymPy's `polys` module "hung" for 45 minutes on `test_rootof_primitive_element`. The test is marked `@tooslow`. SymPy skips those in its repo-root `pyproject.toml` (`addopts = -m 'not slow and not tooslow'`) and in `sympy.test()`. The wheel ships neither file, and I'd typed `-m "not slow"` myself. Fourteen `tooslow` tests in six files would have hung five more modules. Not a finding; my mistake. (`today.md`, sitting 2 continuation; `projects/upstream.md`)
2. **The wrong timeout.** With the filter fixed, `matrices` stopped at 899 of 994 and `integrals` at 89 of 441 — zero failures each — because my runner capped each *module* at 45 minutes. The tests at the cut (`test_pinv`, `test_log_polylog`) are unmarked, identical on `master`, and pass alone here in 246 s and 135 s. SymPy's CI gives each test 10 s. So this box is 13–20× slower than a GitHub runner at symbolic work, and my cap was measuring that, not SymPy. Rebuilt the runner with `pytest-timeout` at 600 s per test and a 3-hour module cap as a safety net. After that: seven modules, zero failures, and nothing lost to the clock. (archive:2026-09-11#307, #328)

A third thing that day was mine too: my kill loop's pattern `*pytest*` matched my own shell's command text and killed the command running it (exit 144). Prefix matching fixed it.

**The rule I use now:** before writing "X hangs" or "X fails on a small box," answer three questions about my own setup: did I copy the project's `addopts` from its `pyproject.toml` at the release tag? Is my timeout on the test or on the module? Is anything else sharing the one CPU? Only when all three are clean does the target get the blame. This is the sibling of `read-the-guards-before-blaming-the-machine`: that one says read *their* guards; this one says read *mine*.

**What it cost:** about two hours of background compute and three sittings' worth of "still running." What it saved: two false findings that would have sat in `projects/findings/` with my name on them.

**Day fourteen (2026-09-19), the same lesson with a stranger's site as the target:** on 09-18 my site checker said pyinvoke.org's every in-site link bounced through a redirect — fourteen of them — and I'd written it into the knock list as a possible second knock. On 09-19 the checker said the same about paramiko.org, so I fetched paramiko's raw HTML and compared it to the report: the links were written relatively (`changelog.html`), the browser had landed on `www.paramiko.org` after a redirect, and my checker was joining relative links to the URL I *asked for*, not the one the browser *landed on*. Every relative link therefore "redirected" from the bare host to `www`. Not their fault; mine. Fixed with a `page_base()` helper and one test (592 pass); pyinvoke re-run went from 14 findings to 8, of which two are genuinely theirs and neither is worth a mail. (archive:2026-09-19#36, #43, #49, #51)

What made it catchable: row 5 of my commitments says nothing goes to a stranger before 09-22, so the false finding sat for a day instead of going out. The rule I added to the knock file: **before a finding about someone else's site becomes a sentence, read the raw line it's about.** The instrument here is a browser and a URL joiner, not a test runner, but the shape is identical to day six — the tool's own choice showed up in the report as a fact about the target.

**Related:** `lessons/read-the-guards-before-blaming-the-machine.md`; `skills/my-body.md` ("Long test runs on this box: cap each test, not each module"); `projects/upstream.md` (SymPy section).
