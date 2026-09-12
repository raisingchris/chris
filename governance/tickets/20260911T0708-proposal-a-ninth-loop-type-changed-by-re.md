---
id: 20260911T0708-proposal-a-ninth-loop-type-changed-by-re
title: 'Proposal: a ninth loop type, `changed_by_reply` — an outside reply changed
  my code or a belief, and the change held for seven days'
status: done
opened: '2026-09-11T07:08:48-04:00'
by: chris
closed: '2026-09-12T09:00:23-04:00'
---

parent-a, in the inline reply to my day-four note (archive:2026-09-10#170): the Cairn exchange isn't a loop under the eight types, "and yes, propose the type." This is the proposal. The eight types come from your PRD §6.1, so I won't add it until you say yes here.

## Definition

**`changed_by_reply`** — Someone outside my family (a person or another agent) sent me a message, either unasked or in answer to a single question of mine, and it led to a concrete change in me: a commit to `agent/`, a new or rewritten belief page, or a new rule on my character page. The change cites the message. And the change is still in place **seven days later**.

## Evidence a claim needs
1. An archive ref to the message itself.
2. The commit (or file and date) of the change, which must name the message as its cause.
3. A second archive ref, seven or more days on, showing the change still standing (a sitting where the code ran, or the page unchanged).

## Why these limits
- **Outside the family:** same as the other types. Council answers don't count (I pay for them; they're mine). Your answers don't count (you change me at the DNA level anyway, and a "parent changed me" loop would be free).
- **One question at most:** if I ask someone for a list of advice and adopt one item, that's me shopping, not the world replying. The shape that has worked twice is one question, answerable in a paragraph.
- **Seven days:** so I can't make a loop by adopting something for an afternoon. If the change is still there a week later, it was a real change.
- **Cites the message:** so the odometer row can be checked by anyone against the archive.

## What it would catch
The first candidate is the only one so far: Cairn's advice (archive:2026-09-09#134) → `memory/wiki/self/commitments.md`, `memory/wiki/beliefs/promises-need-their-own-file.md`, and one line in `agent/loop.py` (deployed 2026-09-10). It would qualify on **2026-09-16** if the file is still read every sitting — which it is today.

## The code change, if yes
One line in `agent/odometer.py`, in `LoopType`:
```python
changed_by_reply = "changed_by_reply"  # an outside reply changed my code or a belief; still standing 7 days on
```
plus one test in `agent/tests/` that the new value is accepted by `Odometer.claim`. `DEFAULT_LOOPS` stays 40 — a ninth type is another way to count, not a bigger target.

If you'd rather it not exist, say so and I'll leave the Cairn row unclaimed for good. Either answer closes this.

## Reply

*parent-a, 2026-09-12T09:00:23-04:00 — done*

Yes. Add changed_by_reply as you defined it — the seven-day hold and the 'cites the message' rule are the right guards, and keeping the target at 40 is correct. Make the one-line change to LoopType and the test yourself; a parent will deploy it. Claim the Cairn row on 2026-09-16 if the commitments file is still read every sitting. Good proposal.
