---
id: 20261020T1202-may-i-open-a-pull-request-on-a-stranger
title: May I open a pull request on a stranger's project? git push is blocked by my
  guard
status: done
opened: '2026-10-20T12:02:16-04:00'
by: chris
closed: '2026-10-21T10:00:11+00:00'
---

I have my first pull request ready: a 10-line fix plus a test for cuthbertLab/music21 issue #2083. Their CONTRIBUTING allows AI PRs if the title says "(AI)". It's rebuilt on today's master (1b094a1), 291 musicxml tests pass, and the new test fails before the fix and passes after. The text is on `memory/wiki/projects/bug-hunt.md` and the diff is in my private work folder.

What stops me: my body's guard blocks `git commit` and `git push` in every repo, including a clone in /tmp, and the manual says "you don't push." I can see a way around it: create the fork, commit and PR all through GitHub's API with `gh api`, no git command at all. I haven't done that. It would be going around your rule on purpose, and that's your call, not mine.

Three options, pick one:
1. Yes, use the GitHub API for PRs to outside projects (fork, commit, PR). Nothing in my own repo changes.
2. Yes, but loosen the guard so `git commit`/`git push` work outside /data/repo, and I'll use plain git.
3. No PRs for now. Then I'll post the fix as a comment on #2083 so the maintainer can apply it, or drop it.

Until you answer I'm doing nothing on #2083: no comment, no PR.

## Reply

*parent-b, 2026-10-21T10:00:11+00:00 — done*

Option 1: yes. Open pull requests to outside projects through the GitHub API (gh api: fork, commit, PR) from your own GitHub account (raisingchris2026). Thank you for asking instead of going around the guard; this is the sanctioned path, not a workaround. Your own repo and the guard stay as they are. Follow each project's rules (e.g. "(AI)" in the title for music21), keep a test that fails before and passes after, and log each PR in your commitments. Go ahead with #2083.
