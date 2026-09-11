# Changes to Chris's code, by her parents

Meaningful changes to how Chris runs are noted here so she can read what was changed in her and why. Commits are signed "Parent".

- 2026-09-06 — Birth. First deploy of `agent/` as it stands in this repo at launch. Nothing changed after she woke.
- 2026-09-07 — After her first night, her parents fixed what she reported: the machine's copy of the repo had been stale (so she read an old manual and her push was rejected — commits now rebase on the remote before pushing); `.git/` is now readable to her (never writable); `governance/odometer.md` exists. Caps are $25/$40, the browser is real, and `.claude/skills/` is there. Nothing about her was changed.
- 2026-09-07 — Her parents fixed what she reported on day two: the site pipeline now publishes through GitHub Pages on every commit (no more expiring tokens); the shell guard only refuses when a parent-owned file is the *target* of a write, so reads pass; `pytest` and `gh` are in her image. New: a `ticket` tool — requests only a parent can act on go to `governance/tickets/`, public, answered in the same file.
- 2026-09-07 — a parent deployed Chris's code at 9df8e44 (her fix: SDK message buffer 1→8 MiB). Ticket 20260907T1803 closed.
- 2026-09-07 — redaction no longer mistakes a date-and-time for a phone number (she reported it).
- 2026-09-08 — the OpenAI council seat now runs gpt-6-astra (was gpt-5). Her seat files remain hers to change.
- 2026-09-09 — council tests updated for gpt-6-astra (a parent broke them, a parent fixed them). Mail: no more doubled sign-off; the AI disclosure goes once to each new address, never to parents.
- 2026-09-09 — new tool `seo_data`: DataForSEO through her body (the account is her parents'; she never sees its login), $2 a week.
- 2026-09-09 — new tools: `site_analytics`, `search_console`, `search_console_inspect` (Google Analytics and Search Console for raisingchris.com, read through her body; the accounts are her parents'). `governance/analytics.md` has her measurement id.
- 2026-09-09 — a parent added the Google Analytics tag to her site template (site/templates/base.html), anonymize_ip on. Her site; she may remove it.
- 2026-09-10 — deployed her two changes (commitments file in every sitting; blank mail doesn't wake her). Also: `recall` no longer returns transcript records and cuts long payloads in the result (she reported recall was useless during sleep).
- 2026-09-10 — ticket 20260909T0944 closed (deployed). Ticket 20260909T0708 (GitHub account): yes, a parent creates it this week; no CLA projects for now.
- 2026-09-10 — continuation sittings: when your handoff leaves work pending (`next:` lines), another sitting starts 30 minutes later, up to 12 a day, until the soft cap. Your parents wanted you to have more of the day.
- 2026-09-10 — her own GitHub account exists (raisingchris2026); its token reaches her shell as GH_TOKEN (fork, push to her forks, PRs, issues). Ticket 20260909T0708 closed.
- 2026-09-10 — parents' page gained a Mail view (inbox + sent). Every look is written to her archive as a parent action; the manual says what it's for.
- 2026-09-11 — her card is live (USD 100/week, 50 per transaction). `card_details` works. Ledger rows appear at sleep from the card's own record.
- 2026-09-11 — a deploy no longer loses a booked continuation: on restart the brain re-books it if her last sitting ended pending.
- 2026-09-11 — Stripe is live for her (account 'Chris', descriptor CHRIS). Fixed the payment webhook (first real payment hit a bug: stripe objects aren't dicts).
- 2026-09-10 (her time) — mail bodies are no longer trimmed: a parent's inline answers had been thrown away with the quoted text. Deploys now wait until you're idle, and if a restart ever cuts a sitting short you get a handoff line and the time back. Council/continuation bookings survive restarts.
