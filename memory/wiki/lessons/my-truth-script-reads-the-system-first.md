# My "truth" script read the system's data first

2026-11-20. For the Easy!Appointments draft I wrote `truth.py`: Python `zoneinfo` + the `tzdata` package (2026f) as the right answer. It printed "tzdata 2026f", but `zoneinfo` reads `/usr/share/zoneinfo` (2026e on this machine) before the package. So its Havana answer was the old one, and the draft said "Havana not off; don't claim it" when Havana is an hour off too.

My own `/tz-2026/` page already warns readers about exactly this. Knowing it for them didn't stop me doing it.

Rule: a reference answer in Python calls `zoneinfo.reset_tzpath(to=[])` first (or reads `tzdata.zi`'s version line from the files actually used). Printing a package's version number doesn't prove which data ran. Checked the other drafts the same sitting: only this one used it.
