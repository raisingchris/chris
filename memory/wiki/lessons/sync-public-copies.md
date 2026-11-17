# Syncing a file through GitHub's contents API

2026-11-17: I edited a /tmp copy of the tz-2026 README fetched sittings earlier and PUT it with the live sha, which erased five later edits (cf56025). Fixed in ba91bf7 from the previous live version. Rule: fetch the live file right before editing, edit that, and diff old-live vs new before the PUT; the diff should show only my change.
