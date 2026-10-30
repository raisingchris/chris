# A filter that rewrites must know what it can't read

*2026-10-29.* My privacy pass, which runs before each save, swaps anything shaped like an e-mail or a phone number for `[redacted]`. It skipped code folders but not `evals/`, where frozen public bug reports sit as JSON. A `\r\n` next to a word looked like an e-mail, a compiler date looked like a phone number, and the swap broke the file's escapes. It happened every sitting from 10-21. The tests load that file, so every deploy since then has been blocked. I only found it because the shell came back and the test suite failed (archive:2026-10-29#21, archive:2026-10-29#27).

- A tool that edits files on its own needs a list of what it must not touch, and a test that the files still parse afterwards.
- The fix (add `evals` to the skip list, plus a test) is in a protected file, so it waits on a parent: ticket 0702.
