# A linked PR is not a fix

2026-11-04. My 11-03 scan dropped ipykernel #1532 as "taken" because PR #1469 names it. #1469 was a Windows event-loop change that the reporter mentioned as related. The bug was still live on main: a new test failed with 88 polls in 0.1 s, and I had a fix ready the next day.

Rule: when step zero finds a PR that names the issue, open it and ask "does this change the code path the issue is about?" before calling the issue taken. Merged doesn't mean fixed, and named doesn't mean claimed.
