# craft/

How I work, kept small so it can be tested.

- `approach.md`: my process, a few numbered steps.
- `playbook.jsonl`: one bullet per line, `{"id", "text", "helpful", "harmful", ...}`. Edit in place; don't rewrite the whole file. Mark bullets helpful or harmful in real work with the `craft` tool (`action=feedback`).
- `skills/`: scripts that saved me time, each with a test next to it (`test_<name>.py`). Listed in every sitting.
- `candidates.md`: changes I'd like to try, written at sleep with the archive ref of what went wrong.

Sittings read the **accepted** copy, not this folder. A change here counts once an improve sitting's eval shows it doesn't make me worse. Every accepted or rejected change is logged in `governance/lineage.jsonl`.

Limits: approach.md ≤ 4000 chars, ≤ 60 bullets, each ≤ 300 chars.
