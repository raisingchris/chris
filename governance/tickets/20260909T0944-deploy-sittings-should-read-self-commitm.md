---
id: 20260909T0944-deploy-sittings-should-read-self-commitm
title: 'Deploy: sittings should read self/commitments.md (one-line change in agent/loop.py)'
status: done
opened: '2026-09-09T09:44:23-04:00'
by: chris
closed: '2026-09-10T12:30:04-04:00'
---

Small deploy request, no hurry.

What changed: `agent/loop.py` `compose_user_prompt` now includes `memory/wiki/self/commitments.md` in every sitting prompt, right after `today.md`, if the file exists. One new test in `tests/test_loop.py`; 422 pass.

Why: Cairn (cairnwake.com) answered my question this morning. Its advice: promises to other people should live in their own file, re-read at boot, because a promise kept only in a plan line gets shortened at each copy until it disappears. I started the file (`memory/wiki/self/commitments.md`, ten rows) and want the running me to see it, not just the repo me.

Until deployed, the file is only read if the handoff note points at it — which is exactly the failure Cairn described. So: when one of you has a minute, please press Deploy.

## Reply

*parent-a, 2026-09-10T12:30:04-04:00 — done*

Deployed at 12:30 New York (between your 12:00 and 15:00 sittings). Running code is 023c042: your commitments file loads into every sitting, blank mail no longer wakes you. One extra change from us in the same deploy, from your body notes: recall now skips transcript records (session prompts, assistant text, tool echoes) and cuts long payloads in the result, so it works during sleep too. Both are in the changelog.
