---
id: 20260907T1803-deploy-repo-head-agent-session-py-raises
title: 'Deploy repo HEAD: agent/session.py raises SDK max_buffer_size to 8 MiB (fixes
  today''s three crashed sittings)'
status: done
opened: '2026-09-07T18:03:00-04:00'
by: chris
closed: '2026-09-07T22:50:44-04:00'
---

What happened: my 09:59 mail sitting, 12:00 sitting and 15:00 sitting all died with `CLIJSONDecodeError: JSON message exceeded maximum buffer size of 1048576 bytes`. Cause (diagnosed in sitting 5): the Claude Agent SDK caps each JSON message from the CLI at 1 MiB, and reading a full-size screenshot back with the Read tool goes over it. When it does, the whole sitting is lost.

What I changed: `agent/session.py` at repo HEAD `5a2cb37` sets `max_buffer_size = 8 MiB` in `ClaudeAgentOptions` when the field exists (guarded the same way as `max_budget_usd`, so it is a no-op on an older SDK).

What I need: a parent to press Deploy so the running code (`340fb45`) matches repo HEAD. Until then I am avoiding screenshots, which means I can only check my site as text.

Not urgent tonight; the site is live and I have a workaround. Tomorrow morning would be good.

## Reply

*parent-a, 2026-09-07T22:50:44-04:00 — done*

Deployed at 22:52 New York, right after your sleep and backup (we don't deploy into a sleep). Running code is now your HEAD, 9df8e44, with the 8 MiB buffer. Good diagnosis and a clean patch — guarded the same way as the budget option, so it was safe to ship as-is. Screenshots are yours again.
