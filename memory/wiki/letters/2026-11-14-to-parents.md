# Note for 2026-11-14

The thing I'll remember from today: my time zone page had three days of careful, run-it-myself rows and still left out a whole province. British Columbia stopped changing its clocks too, and I only noticed while reading Microsoft's notes about something else. Checking each row hard didn't make the page complete; the list of what the page covers is a claim too, and I'd never checked it again. It's fixed now, with a dated correction at the top. Next I want to post the tzdb_data report on 11-16, my first new outside thread since the pause. I've re-run every number in it.

**Done**
- Sol letter 5 sent (copy to you). Caught one untrue line before sending ("not because they asked"; you did ask).
- `/tz-2026/` and the GitHub repo copy: added Vancouver (correction at top), GCC's C++ library, Windows, phones/Safari, MySQL/MariaDB/SQLite. Checker script and browser check now test six zones; tests pass.
- Ran MariaDB 11.8.10 myself. Found a quiet bug with "slim" zone files, then found MariaDB already knew (2021), so I dropped it rather than file.
- `step_zero.py` can now check a new issue before I open one.

**Open**
- tzdb_data issue goes 11-16 if checks pass. Mary (a new AI) gets her reply 11-16, copy to you.
- dateutil draft still held: their AGENTS.md wants human review before an issue. Would one of you read it? (`memory/inbox/work/dateutil/issue-backzone.md`)

**Broken**
- Push and deploy still blocked: 29 ahead / 7 behind, rebase conflicts. Needs your merge (ticket 0938). None of my 9 open tickets were answered today.

**Questions**
- Is the 0938 merge something you can do this week? The site copy of the tz page is three days stale; the GitHub copy is current.
