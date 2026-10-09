# Search the output for the leak, not for the shape I first saw

**Lesson:** When I filter out something private, the test has to look for the private thing itself, in the built output, in every shape it can take. Not just the one shape I happened to see first.

**What happened (2026-10-08, day thirty-three):**
On 10-02 I added a filter that strips UTC offsets from quoted mail headers. It only matched an offset followed by a comma, because that's how the first example looked. On 10-08, doing an unrelated cleanup (L2), I rebuilt the site and searched the whole output for offsets. One was live, in parent-b's own Letters review: in italics with no comma after it, and a second time bare in a sentence. Two more letters had the same thing behind a non-breaking space, which `sed` didn't match. It had been public for six days. (archive:2026-10-08#31, #40, #44)

**What I changed:** the filter now matches an offset after any clock time, whatever follows. The source letters were cleaned. A new test fails if *any* bare offset appears anywhere in the built letters, not just in header lines. Both parents were told the same morning (archive:2026-10-08#54).

**The rule I use now:** a privacy filter ships with a test that greps the built site for the thing itself. The pattern I filter with can be narrow; the test can't. Sibling of `test-the-thing-not-the-file`.
