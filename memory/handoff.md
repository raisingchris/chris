# Handoff, 2026-10-30 evening sitting
done: cold-read c319 and c404: both ready, they only need a fresh step zero. Bulk linked_prs on 28 open nbconvert issues: 13 already had PRs (bleach #2209 has #2337, pandoc #2243/#2254 has #2317).
done: nbconvert #2204 reproduced. The exact error comes from 7.17.2 code running with no .git next to 7.16.4's installed templates; putting the new templates on JUPYTER_PATH fixes it. Fedora's spec already does that fix. Draft is ipython/c2204.md (repro r2204.py), for 11-04 at the earliest.
next: 10-31 07:00: post ipykernel #319 (c319.md) and nbconvert #404 (c404.md), each after a fresh step zero, each with its own commitments row. Then c134 on 11-02, c269 on 11-03, c2204 on 11-04. Still don't deploy until ticket 0701 is closed.
next: 11-03 first commitments review from review-1103-prep.md; tell Kei the count.
