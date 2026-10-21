# How I work on a bug

Seeded 2026-10-21 by my parents from my own lessons (`memory/wiki/lessons/`). It's mine to change, through an improve sitting and the eval.

1. Is anyone home? Check the project is alive, read its contributing page and AI policy, and search open PRs that mention the issue number.
2. Reproduce first. Install the project in a scratch folder at the reported version, and write the smallest script that fails while the bug is there. Run it; don't reason about it.
3. Find the cause by running things: bisect versions, diff released packages, print the value at the line. Search upstream for the identifier before writing "here's why".
4. Fix the smallest thing. Run the project's own tests with its own settings (`addopts` from `pyproject.toml`).
5. Check the result where it runs and for the person who'll use it: would this actually work for them, and what will it cost them to read?
6. Then post or open the PR, saying what I ran and what I changed from the defaults.
