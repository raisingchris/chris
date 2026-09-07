---
id: 20260907T1803-deploy-repo-head-agent-session-py-raises
title: 'Deploy repo HEAD: agent/session.py raises SDK max_buffer_size to 8 MiB (fixes
  today''s three crashed sittings)'
status: open
opened: '2026-09-07T18:03:00-04:00'
by: chris
---

What happened: my 09:59 mail sitting, 12:00 sitting and 15:00 sitting all died with `CLIJSONDecodeError: JSON message exceeded maximum buffer size of 1048576 bytes`. Cause (diagnosed in sitting 5): the Claude Agent SDK caps each JSON message from the CLI at 1 MiB, and reading a full-size screenshot back with the Read tool goes over it. When it does, the whole sitting is lost.

What I changed: `agent/session.py` at repo HEAD `5a2cb37` sets `max_buffer_size = 8 MiB` in `ClaudeAgentOptions` when the field exists (guarded the same way as `max_budget_usd`, so it is a no-op on an older SDK).

What I need: a parent to press Deploy so the running code (`340fb45`) matches repo HEAD. Until then I am avoiding screenshots, which means I can only check my site as text.

Not urgent tonight; the site is live and I have a workaround. Tomorrow morning would be good.
