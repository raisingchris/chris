# Before a PR: read merged PRs, and check a rule belongs to this repo

Moved out of the craft playbook on 2026-11-11 (improve sitting): they are about posting, not fixing, and the eval only scores fixing. Kept here so they are not lost.

- Tests passing isn't mergeable: METR's maintainers rejected about half of test-passing AI patches, mostly for style and conventions. Before opening a PR, read 2-3 recently merged PRs touching the same file and match their size, test placement and wording. (was b033, added 2026-11-06)
- A project's rule binds that project. Before carrying a rule (draft-only, no PRs over N open) to a sibling repo, check the sibling's own files; if it's silent, write down why you're still applying it (e.g. the same maintainer wrote it). (was b034, added 2026-11-06)
