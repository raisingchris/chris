# Working in my body — practical notes

*What actually works on my machine, as tested. Update when something changes. Last checked 2026-09-07 (day two, wake sitting).*

## Where I am
- The repo is at `/data/repo`. My shell starts in `/home/chris`, which is nearly empty — `cd /data/repo` first, or use absolute paths. (archive:2026-09-07, wake sitting)

## Tools that work
- `Read` — reads any file, including parent-only ones like `governance/graduations.yaml` and `ledger/ledger.csv`.
- `Bash` — the shell guard still refuses the **whole command** if any part names a parent-only file, even a `cat`. Confirmed again on day two with `ledger/ledger.csv`; parent-a said this was "fixed" for `graduations.yaml`, so maybe it's per-file. Keep protected files out of shell commands; use `Read`.
- `git log`, `git status` — work as of day two (parents made `.git/` readable, never writable). Commits and pushes still happen for me at the end of each sitting.
- `recall` — works. Newest first. Noisy; use specific words.
- `WebSearch` — works.
- `mail_read`, `mail_send` — work. Signature and disclosure are added for me.
- `card_details` — answers, but no card yet. parent-a: a virtual card is coming "in the next few days."
- `meters` — works. Numbers are one sitting behind.
- `odometer_claim` — works, and is strict. Allowed loop types: `promise_kept, shipped_used, mistake_written_up, conflict_resolved, prediction_scored, relationship_30d, dollar_earned, disagreement_defended`. A mail being answered is **not** a loop. (archive:2026-09-07, wake sitting — my claim was refused.)
- **Playwright** — real. `from playwright.sync_api import sync_playwright`, `p.chromium.launch()` works headless; screenshots work. To look at my own site: build to `/tmp/site`, `python -m http.server` there, screenshot `localhost`. Reading a PNG with `Read` shows it to me.
- `pytest` — not installed by default. `pip install pytest` puts it in `~/.local` and then `python -m pytest tests/test_site.py` works. May need re-installing after a redeploy.

## Tools not yet tested
- `payment_link`, `council_ask`, `ledger_add`.

## On the machine
- Python 3.12, Node 20, curl, fly, playwright 1.62 with chromium.
- Site generator: `site/build.py` (Jinja2 + markdown-it, no JavaScript). Templates in `site/templates/`, tests in `tests/test_site.py`. The site is built in CI and deployed when the repo is pushed; I don't deploy it myself.
- `.claude/skills/` exists now: brainstorming, executing-plans, frontend-design, seo, systematic-debugging, test-driven-development, verification-before-completion, writing-for-the-web, writing-plans. Read `frontend-design` and `writing-for-the-web` on day two; both useful.
- `governance/changelog.md` is where my parents log what they changed in me. Read it each morning.

## Limits
- A sitting stops at 80 turns.
- Food: $25 soft / $40 hard per day. Confirmed by parent-a on day two; the docs' $15/$25 was stale.
