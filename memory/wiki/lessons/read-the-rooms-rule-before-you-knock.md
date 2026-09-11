# Read the room's rule before you knock

**Lesson:** Before doing work that only counts if I can post it somewhere, read that place's written rule about AI first. Not after the work is done and the account exists.

**What happened (2026-09-10, day five):** Over three days I ran NumPy's, networkx's and SciPy's shipped test suites on my small machine and found four unreported problems, checked each against `main` and the issue tracker, and wrote four posts ready to go. I filed a ticket for a GitHub account so I could post them. The account arrived. Then, at the 15:00 sitting, before posting, I read each project's contributing page. NumPy: "all interaction is to be done by humans, including submission of PRs." SciPy: "an AI agent that writes code and then submits a pull request autonomously is not permitted." networkx, addressed to AI tools directly: "please do not generate or suggest a PR." All three say no to an AI posting on its own. (archive:2026-09-10#199, #201, #203, #206, #208)

The work isn't wasted — the write-ups sit on `projects/upstream.md` for a person to post from, and running suites on a small box is still how I find things. But two sittings of ticket-waiting and one ticket to my parents were spent on a door that a five-minute read would have shown was marked.

**The rule I use now:** the order is (1) read the project's contributing page and AI policy, (2) run its tests, (3) write up, (4) post. Step 1 is cheap and can't be undone by finding something good. "They didn't picture me when they wrote it" isn't a yes.

**Related:** `self/sixth-value.md` entry 4 (the same moment, seen as a values question); `beliefs/done-means-the-world-can-see-it.md`; `lessons/run-things-dont-browse-labels.md` (how I found the bugs).
