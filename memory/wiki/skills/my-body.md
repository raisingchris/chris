# Working in my body — practical notes

*What actually works on my machine, as tested. Update when something changes. Last checked 2026-09-06 (day one).*

## Tools that work
- `Read` — reads any file, including parent-only ones like `governance/graduations.yaml`.
- `Bash` — but the shell guard refuses the **whole command** if any part names a parent-only file, even a `cat`. It checks the filename, not the verb. Keep protected files out of shell commands; use `Read`. (archive:2026-09-06#21)
- `recall` — works. Newest first. It includes my own system prompts and tool calls, so a search can return a lot of noise. Use specific words.
- `WebSearch` — works. (archive:2026-09-06#36)
- `mail_read`, `mail_send` — work. Signature and disclosure are added for me. (archive:2026-09-06#19, #41)
- `card_details` — answers, but no card yet. (archive:2026-09-06#20)
- `meters` — works. Numbers are one sitting behind.

## Tools not yet tested
- `payment_link`, `council_ask`, `ledger_add`, `odometer_claim`.
- `playwright` binary exists at `/usr/local/bin/playwright`; the manual says I have no browser. Unknown which is right.

## On the machine
- Python 3.12, Node 20, curl, fly.
- Site generator: `site/build.py` (Jinja2 + markdown-it, no JavaScript). Templates in `site/templates/`, tests in `tests/test_site.py`.
- `.git/` belongs to the other user; `git log` fails for me. Commits and pushes happen for me at the end of each sitting.
- `.claude/skills/` does not exist as of day one, though I was told it holds brainstorming and frontend-design skills.

## Limits
- A sitting stops at 80 turns (birth sitting allowed 150).
- Food: meters say $25 soft / $40 hard per day. Docs say $15 / $25. Asked which is true.
