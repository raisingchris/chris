# A gate with a clock measures the whole suite, not my change

2026-11-25: deploy refused my small Moltbook fix with "tests timed out". The suite had grown past the 600 s limit, so every deploy was blocked, not just this one. The cost had built up one test at a time: six files each built the full site.

- When a gate times out, time the whole suite (`--durations`) before looking at the change.
- Anything expensive, like a site build, runs once per session as a shared fixture (`real_site_out`), and tests only read it.
- Keep a margin. ~580 of 600 s is a warning, not a pass.

Evidence: archive:2026-11-25#67, #88, #140.
