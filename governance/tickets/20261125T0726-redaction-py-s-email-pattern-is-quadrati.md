---
id: 20261125T0726-redaction-py-s-email-pattern-is-quadrati
title: 'redaction.py''s email pattern is quadratic: 20,000 letters with no space take
  59 s (one-line fix, protected file)'
status: open
opened: '2026-11-25T07:26:27-05:00'
by: chris
---

Found 2026-11-25 while testing a Moltbook change. tests/test_moltbook.py::test_reads_are_labelled_untrusted_redacted_and_trimmed hangs past 100 s at HEAD c5d673c, before any change of mine. faulthandler puts it in agent/redaction.py `sub` → `_EMAIL`.

Cause: `_EMAIL = r"[\w.+-]+@..."` restarts at every letter of a long run with no `@`, so the time grows with the square of the run. Measured on this box (findall on "x"*n):

| n | now | with fix |
|---|---|---|
| 5,000 | 3.7 s | 0.006 s |
| 10,000 | 14.8 s | 0.011 s |
| 20,000 | 59.2 s | 0.022 s |

Anything redaction reads can carry such a run: mail with a base64 blob, minified JS from the web, a long token in a Moltbook post. It may also be part of why my site tests take ~8.5 min.

Fix (agent/redaction.py line 30, protected so it's yours):

    _EMAIL = re.compile(r"(?<![\w.+-])[\w.+-]+@[\w-]+(?:\.[\w-]+)+")

Same matches on [redacted], [redacted], ([redacted]), "[redacted], [redacted]", <[redacted]>. One case it misses that today's pattern catches: a second address glued onto the end of a first, like "[redacted][redacted]" (the lookbehind sees the "c"). If that matters, say so and I'll look for a linear pattern without the gap.

Test I'd add: `assert time-bounded redact("x"*20000, [])` (under 1 s) plus the five samples above.

Meanwhile, in agent/moltbook.py (not protected) I now trim to 12,400 chars, at a JSON line break when one's near, before redacting, with a test that a name at the cut stays hidden. That makes test_moltbook pass (13 tests, 48 s) but each long read still costs ~20 s until this lands.
