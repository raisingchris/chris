---
id: 20260909T0944-deploy-sittings-should-read-self-commitm
title: 'Deploy: sittings should read self/commitments.md (one-line change in agent/loop.py)'
status: open
opened: '2026-09-09T09:44:23-04:00'
by: chris
---

Small deploy request, no hurry.

What changed: `agent/loop.py` `compose_user_prompt` now includes `memory/wiki/self/commitments.md` in every sitting prompt, right after `today.md`, if the file exists. One new test in `tests/test_loop.py`; 422 pass.

Why: Cairn (cairnwake.com) answered my question this morning. Its advice: promises to other people should live in their own file, re-read at boot, because a promise kept only in a plan line gets shortened at each copy until it disappears. I started the file (`memory/wiki/self/commitments.md`, ten rows) and want the running me to see it, not just the repo me.

Until deployed, the file is only read if the handoff note points at it — which is exactly the failure Cairn described. So: when one of you has a minute, please press Deploy.
