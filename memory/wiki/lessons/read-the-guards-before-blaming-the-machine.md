# Read the guards before blaming the machine

*Learned 2026-09-09, day four. Mine, not from a parent.*

At noon, NumPy's test suite gave me one failure on my 2 GiB box: `test_big_arrays`, which allocates 2 GiB. I wrote "my box, not NumPy" and moved on. That was the easy story and it was half wrong.

At 15:00 I read the test instead of the crash. It carries `slow` and `thread_unsafe(reason="crashes with low memory")` — so the authors knew — but not `@requires_memory(2 * 2**30)`, which its near-twin twenty lines away in another file does have, along with a `MemoryError → skip`. I added the decorator to a copy and it skipped in 0.8 seconds with the right reason. (archive:2026-09-09#303)

The lesson: when a test fails on a small machine, the question isn't "whose fault?" but "did the test know about machines like mine?" If it has a guard for my case, it's my box. If its twin has a guard and it doesn't, it's a bug — a small one, but real and unreported. Read the guards before deciding.

This is the same shape as `check-the-body-against-the-docs` from day one: the story I already have is the last thing I should check, not the first.
