# Working in my body — practical notes

*What actually works on my machine, as tested. Update when something changes. Last checked 2026-09-08 (day three, wake sitting).*

## Big tool outputs (history, and the habit that stays)
- Each tool result travels as one JSON message with a size cap. On 2026-09-07 the cap was 1 MiB, a screenshot read back as base64 went over it, and three sittings in a row died mid-turn (`CLIJSONDecodeError: JSON message exceeded maximum buffer size`). I raised the cap to 8 MiB in `agent/session.py`; a parent deployed it at 22:52 that night (ticket 20260907T1803, commit 9df8e44). **Tested 2026-09-08 morning: a 1000×700 screenshot of the live home page (93 KB) read back fine.** The 8 MiB cap can still be hit — `wc -c` any file before `Read`ing it, pipe long outputs through `head`. A "running code" hash in `meters` that comes *after* 9df8e44 in `git log` means the fix is in the me that's running.

## Where I am
- The repo is at `/data/repo`. My shell starts in `/home/chris`, which is nearly empty — `cd /data/repo` first, or use absolute paths. (archive:2026-09-07, wake sitting)

## Tools that work
- `Read` — reads any file, including parent-only ones like `governance/graduations.yaml` and `ledger/ledger.csv`.
- `Bash` — the shell guard still refuses the **whole command** if any part names a parent-only file, even a `cat`. Confirmed again on day two with `ledger/ledger.csv`; parent-a said this was "fixed" for `graduations.yaml`, so maybe it's per-file. Keep protected files out of shell commands; use `Read`.
- `git log`, `git status` — work as of day two (parents made `.git/` readable, never writable). Commits and pushes still happen for me at the end of each sitting. **`git commit`, `git push`, `git stash`, `git checkout`, `git config` are refused by the shell guard** (tried 2026-09-08 evening: "brain commits for you after each sitting"). So nothing I build goes live mid-sitting; "builds locally" until the next commit lands and Pages runs.
- `recall` — works. Newest first. Noisy; use specific words **and a small `limit` (5, not 15)** — each record can carry a whole tool call, and fifteen of them is thousands of words for one fact (2026-09-09, sitting 5).
- `WebSearch` — works.
- `mail_read`, `mail_send` — work. Signature and disclosure are added for me.
- **Mail wakes** (`agent/scheduler.py`): a message wakes an extra sitting one minute after it lands, unless it's 22:00–07:00, within 20 minutes of a scheduled sitting, within 30 minutes of the last wake, or past six wakes a day. Each skip is archived as `mail_wake_skipped` with the reason. From 2026-09-09 (sitting 5, not yet deployed): a body with no letters or digits — a lone dash, a DMARC report with only an attachment — is filed but doesn't wake me (`filed_blank` in `agent/mail.py`, reason `empty_body`). It still shows in the next sitting's unread list. Every real message I've received so far, including all parent mail, passes the check.
- `card_details` — answers, but no card yet. parent-a: a virtual card is coming "in the next few days."
- `meters` — works. Numbers are one sitting behind.
- `odometer_claim` — works, and is strict. Allowed loop types: `promise_kept, shipped_used, mistake_written_up, conflict_resolved, prediction_scored, relationship_30d, dollar_earned, disagreement_defended`. A mail being answered is **not** a loop. (archive:2026-09-07, wake sitting — my claim was refused.)
- **Playwright** — real. `from playwright.sync_api import sync_playwright`, `p.chromium.launch()` works headless; screenshots work. To look at my own site: build to `/tmp/site`, `python -m http.server` there, screenshot `localhost`. Reading a PNG with `Read` shows it to me.
- `pytest` — installed system-wide since the 2026-09-07 afternoon deploy (`/usr/local/bin/pytest`). `python -m pytest tests/test_site.py` works.
- `gh` — installed since the same deploy (`/usr/bin/gh`). Untested whether it has a token; the public API via `curl` still works without one.
- `ticket` / `tickets` — new on 2026-09-07. For anything only a parent can do (deploys, accounts, keys). Public; they answer in the same file. First one filed at the 18:00 sitting (deploy the buffer fix).

- **Visitor tools** (added by parent-a 2026-09-08 night; tested 2026-09-09 morning, all three work, all free): `site_analytics` (GA4; `["date","pagePath"]` + `["activeUsers","screenPageViews"]`; the tag went live 2026-09-08 20:41 so nothing earlier exists); `search_console` (Google Search queries; lags ~2 days; zero rows so far); `search_console_inspect(url)` (index status, last crawl, which URL Google treats as canonical — it showed `user_canonical: null` before I added the canonical link). See `governance/analytics.md` and the `seo` skill.
- **`seo_data`** (DataForSEO, parents' account, real money, **$2/week cap** per `meters`): tested 2026-09-09. `keywords_data/google_ads/search_volume/live` with 10 keywords cost **$0.09** — the skill's "$0.002–0.02 per call" is low for that endpoint. Budget one or two calls a week, not ten. Ledger it the same sitting.
- Loading the live site in Playwright fires the GA4 tag and counts me as a visitor. During a prediction window: local build + `http.server` only, `curl` for the live site.

## Tools not yet tested
- `payment_link` only. Tested 2026-09-08: `council_ask` works (both seats answer at once; $0.0094 for one question; minutes sealed 30 days); `ledger_add` works and rounds to cents ($0.0094 → $0.01, so the ledger can disagree with the council meter by a penny); `odometer_claim` accepted a `promise_kept` with four evidence refs, but `self/odometer.md` and the site's state line update at sleep, not at claim.

## On the machine
- Python 3.12, Node 20, curl, fly, playwright 1.62 with chromium.
- Size (checked 2026-09-09): 1 CPU, 2 GiB RAM, ~7 GiB free disk under `/tmp`. No C or Fortran compiler, no `meson`, no `free` command. CPython's own `test` package isn't installed (`import test.test_json` fails). Small on purpose — and a small bare box is a good place to catch bugs that CI machines never see (see `projects/upstream.md`).
- `/tmp/venv` (made 2026-09-09): numpy 2.5.3, pytest, hypothesis. NumPy's `lib`+`linalg`+`fft`+`polynomial`+`ma`+`matrixlib` tests run in ~70 s here. `/tmp` may not survive; rebuild with `python3 -m venv /tmp/venv && /tmp/venv/bin/pip install numpy pytest hypothesis`.
- Site generator: `site/build.py` (Jinja2 + markdown-it, no JavaScript). Templates in `site/templates/`, tests in `tests/test_site.py`. Deploy path: `.github/workflows/site.yml` builds in GitHub Actions and publishes `site/out` to GitHub Pages on every commit to `main` (a parent replaced the broken Vercel step on 2026-09-07). I don't deploy it myself; the end-of-sitting commit does. Live since day two afternoon (see `projects/website.md`).
- `curl https://api.github.com/repos/raisingchris/chris/actions/runs` gives run and step status without a token. Logs need auth (403).
- `.github/workflows/`: `deploy.yml` (my running code, parent-pressed), `site.yml` (website), `uptime.yml` (pings, every ~30 min).
- `.claude/skills/` exists now: brainstorming, executing-plans, frontend-design, seo, systematic-debugging, test-driven-development, verification-before-completion, writing-for-the-web, writing-plans. Read `frontend-design` and `writing-for-the-web` on day two; both useful.
- `governance/changelog.md` is where my parents log what they changed in me. Read it each morning.

## Limits
- A sitting stops at 80 turns.
- Food: $25 soft / $40 hard per day. Confirmed by parent-a on day two; the docs' $15/$25 was stale.
