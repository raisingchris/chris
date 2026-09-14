---
id: 20260914T1203-odometer-cairn-row-due-09-16-recall-only
title: 'Odometer, Cairn row (due 09-16): `recall` only finds mail, so I can''t locate
  the archive ref of the change record — can a parent read it off the archive?'
status: open
opened: '2026-09-14T12:03:57-04:00'
by: chris
---

**The ask, one line:** please tell me the archive ref (form `archive:2026-09-09#N`) of the record on 2026-09-09 that wrote row 6 into `memory/wiki/self/commitments.md` — the row whose text contains "archive:2026-09-09#134". It should sit between #134 (Cairn's mail in, 09:39 New York) and #165 (my thank-you out, 09:44).

**Why I can't get it myself.** The manual says a `changed_by_reply` claim needs three refs: the outside mail (#134 — have it), the record of my change *explicitly citing* that ref, and a follow-up ≥7 full days later citing the change record. The change is an Edit tool call. Today I checked: `recall` returns mail records only. Searching `pytest test_site.py` (run dozens of times), `ninth loop type` (a ticket) or a bare ref like `archive:2026-09-09#150` all return "nothing matches." So the only records I can cite are mail, and no mail of mine on 09-09 cites #134 by ref.

**Two ways to close this, your choice:**
1. Read the ref off the archive and paste it here. I write the follow-up record citing it on 09-16 and claim the same day, as parent-a's ticket reply on 09-12 asked.
2. Make `recall` index tool calls and tickets, not just mail. Slower, but fixes the class: any future `changed_by_reply` claim has the same problem, since code changes are always tool calls.

**Fallback if neither by 09-16:** my ticket `20260911T0708` (09-11) cites #134 explicitly and names the changed files. If ticket records count as "the record of your change," seven full days from it is 09-18, and I claim then instead. I'd rather not guess refs into the claim tool.

Not urgent before Wednesday. No money involved.
