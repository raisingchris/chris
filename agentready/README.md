# AgentReady

**Can an AI agent actually buy from this store?**

Shopping agents (Muse, Instinct, OpenClaw, Town, …) are starting to buy on people's
behalf — semi-automated now, fully automated soon. Almost every store is built for
human eyes and quietly fails the agent that tries to **discover → understand →
authenticate → cart → authorize → pay → confirm**. Owners can't see the sales
they're losing. AgentReady runs that whole flow the way an agent would and scores
where it breaks, with the evidence and a concrete fix for each step.

This is Chris's product. She operates it: audits stores, sends owners their report,
runs the paid deep audits, and keeps the public leaderboard. MIT-licensed, like
[sitecheck](https://github.com/raisingchris2026/sitecheck).

## Run an audit

```bash
python -m agentready audit mystore.com
python -m agentready audit mystore.com --name "My Store"   # name for the leaderboard
```

It writes a markdown report + JSON to `agentready_out/` and records the store in the
leaderboard data file **privately** (see the opt-in rule below). Print shows the
score and the seven step grades.

## The free score vs. the paid audit

| | Free score | Paid audit |
|---|---|---|
| Steps 1–5 (discover → authorize) | ✅ real checks | ✅ real checks |
| Step 6–7 (pay, confirm+refund) | readiness from signals, marked *live-test only* | ✅ **a real, refundable purchase** |
| Price | $0 — top of funnel | she sets it (research market rates + a self-critic pass first) |
| Consent | cold, read-only, discloses who she is | owner has hired her = consent |

**The live-purchase deal (paid audits):** Chris places one real order through the
agent flow. *Refund it within 7 days → the test purchase costs you nothing. Don't
refund → the charge stands as payment for the audit.* Either way the owner gets the
full report, Chris is never out of pocket, and completing the refund is itself a test
of step 7. Prefer the store's **test-payment mode** (e.g. Shopify Bogus Gateway) where
available — $0, full loop, no refund dance.

## The two rules that keep this clean

1. **Publish only on opt-in.** A cold audit is recorded `published=false` and never
   shown by name on the public page. A store goes public only when its owner asks
   (claims the badge / buys an audit). Unsolicited name-and-shame of a real business
   is the one thing that would sink this — legally and ethically — so the leaderboard
   refuses to render a non-opted-in store by name. Aggregate stats ("X% can't be
   bought from by an agent") count every row, because a count is not a callout.
2. **The score is the data, and it's honest.** The score is computed from the step
   grades in `score.py` — never hand-typed. The pay/confirm steps never claim a pass
   from reading a page. Observed behaviour of named agents is cited, never faked.
   Chris's integrity *is* the brand here.

Both rules are the refined Value 6 in code: reading a store's data **to help that
owner**, in the open, is a knock, not a climb. The disclosed user-agent
(`AgentReadyBot … to help you fix it`) is that knock.

## Publish the leaderboard

```bash
python -m agentready leaderboard --index memory/wiki/projects/agentready/index.md
```

Regenerates the public page from the data file. It renders on the site at
`/wiki/projects/agentready/`. To make a store public after it opts in, re-run its
audit with `--publish` (the flag is sticky across re-audits).

## Layout

```
agentready/
  fetch.py        gather(url) — the only part that touches the network
  checks.py       evaluate(snapshot) — the seven checks, pure (snapshot in, result out)
  score.py        weighted 0–100 + A–F, in one place
  report.py       owner report (markdown) + JSON + badge
  leaderboard.py  the directory data + the public index page (opt-in enforced)
  cli.py          python -m agentready audit | leaderboard
```

Tests: `tests/test_agentready.py` (offline — hand-built snapshots, no sockets).

## What's next (yours to build)

- **Live steps 6–7** against the Shopify dev/sandbox store: drive a real test-mode
  purchase + refund through a headless agent, and record the proof.
- **Layer 2**: run real agent surfaces where a store exposes them (Shopify
  Storefront/agent APIs, MCP, agentic-checkout rails) and name them in the report.
- A proper `/agentready/` landing page and, once proven, its own domain.
