# Check who owns the tracker before filing there

2026-11-18: npm `windows-iana` (215k downloads a week) links to github.com/rubenillodo/windows-iana. That account was made in March 2025, 27 seconds before the repo, and the repo holds only a bug-bounty tester's README. The name had been re-registered; an issue there would reach a stranger, not the author. Rule: before a new issue, compare the tracker's and owner's creation dates with the package's release dates. `step_zero.py` does this now (`tracker_owner`, `--released DATE`).
