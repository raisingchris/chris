---
id: 20260914T1504-deploy-request-upwork-poll-wake-me-when
title: 'Deploy request: Upwork poll — wake me when a draft moves or a client writes
  (agent/scheduler.py, agent/loop.py; 537 tests pass)'
status: open
opened: '2026-09-14T15:04:59-04:00'
by: chris
---

**Ask:** press Deploy on the repo HEAD after this sitting commits. No parent-side setup needed — it uses the Upwork bridge that already exists.

**What it does, plainly:** Upwork has no webhook into me, so only mail wakes me today. This adds a small clock job that looks at Upwork at :15 and :45 every hour from 07:00 to 21:59 (my time). Each look is one local read (the outbox states) and one API call (unread rooms, max 10). If a queued draft left `pending` (sent / declined) or a client room has a new unread message, it books an extra sitting the same way mail does — kind `upwork` — and appends one line to my handoff saying what changed. Same limits as mail wakes: shared 30-minute debounce, shared cap of six a day, never in sleep hours or within 20 minutes of a scheduled sitting.

**What it deliberately doesn't do:** nothing changes on Upwork — reads only. No client text is stored: rooms are kept in state as 16-character hashes. A room that stops being unread (a parent read it) is not a wake. A draft I queued myself is not a wake. A change seen while a sitting is running is left unsaved so the next look sees it again once the sitting ends — no lost event, no race on my handoff file. Bridge errors are archived (`upwork_poll_failed`) and never raised into the scheduler.

**Cost:** about 30 API calls a day on the account. If that's too many or you'd rather it ran only once a proposal is actually sent, say so and I'll gate it on a non-empty sent outbox before you deploy.

**Files:** `agent/scheduler.py` (constants, `request_mail_wake(source=...)`, new `upwork_signal`/`upwork_changes`/`upwork_poll`, job `upwork-poll`), `agent/loop.py` (new kind `upwork` with its header line), `tests/test_scheduler.py` (7 new tests; two day-list tests updated). Full suite: 537 passed, 2 skipped.

Why now: earning is 60% of this week and today's two search passes found zero fits; this is the one earning-side thing I could move without spending Connects. It only matters once a parent has pressed send on the rug draft — but that's exactly when a client message would sit unread for up to three hours otherwise.
