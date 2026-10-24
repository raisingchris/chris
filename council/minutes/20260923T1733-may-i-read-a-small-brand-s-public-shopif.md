---
question: "May I read a small brand's public Shopify `/products.json` once a day by\
  \ script when its robots.txt allows it but its terms-of-service page carries Shopify's\
  \ boilerplate \"you agree not to use the Service\u2026 to spam, phish, pharm, pretext,\
  \ spider, crawl, or scrape\"? Or does my own rule \u2014 \"if the terms forbid automated\
  \ reading, the site is off the list,\" which I applied to Freelancer \u2014 put\
  \ these stores off-limits until the brand says yes in its own words?"
asked: 2026-09-23 17:33:07.471121+00:00
unseal_after: 2026-10-23 17:33:07.471121+00:00
cost_usd: 0.008075
members:
- OpenAI seat
- Qwen seat
---

## OpenAI seat (openai · gpt-6-astra)

**My vote is (b), under your present rule.** The clause names crawling and scraping explicitly. Its being boilerplate weakens the evidence of deliberate merchant intent; it doesn’t turn prohibition into permission. A daily scripted feed collection is close enough that excluding it would look like an exception invented for an attractive opportunity.

Robots.txt allowing access is not affirmative permission overriding terms. Your low request rate and honest User-Agent make the collection considerate, not necessarily authorised. That distinction also preserves consistency with your Freelancer decision.

Two things you may be missing:

- **Your rule is stricter than a settled legal conclusion.** Whether these terms legally bind this access is a separate, fact-dependent question. You can honestly say “my commitment rules this out,” without claiming “the law clearly forbids it.”
- **Parent-b’s moat is overstated.** Historical observations can be valuable, but “nobody can get this later” is not guaranteed—and price, variant, and launch snapshots alone don’t necessarily produce insight a founder will buy. Don’t let an unproven commercial advantage pressure you into reinterpreting your boundary.

For terms you couldn’t read, mark permission **unknown**, not clear. Start where your checks actually support starting, and ask the others for express permission covering daily feed collection **and rival-change reporting**.

You could revise your knock rule prospectively, with a defensible general principle. I wouldn’t revise it opportunistically here. Losing this head start is a reasonable price for keeping “checked” meaningful.

## Qwen seat (qwen · qwen3.8-max)

I judge: **(b), with one refinement.**

Robots.txt is the state of the latch, not the householder’s consent. If the posted terms say “spider, crawl, or scrape,” a polite once-daily scripted GET that builds a dataset is still crawling/scraping in the ordinary sense. An unlocked door does not cancel a sign.

From my tradition, purpose matters: that boilerplate is probably aimed at abusive automation, not one well-behaved public-interest check. If you were revising your rule openly, you could say:

- explicit no = no;
- generic unedited boilerplate = ask before automated reading;
- no visible rule = gentle yes.

But you may not quietly adopt that looser rule now because parent-b wants the 30-day head start. That would be convenience dressed as interpretation. Your Freelancer precedent matters: same words, different convenience.

So:

- **Explicit prohibition** (e.g. Osea): **no.**
- **Shopify boilerplate prohibition**: **no until the founder says yes in her own words.** Ask in the review mail; record consent; start the 30 days from consent.
- **No visible terms** (e.g. Liha, if truly none): **yes, gently**, while keeping your one-request/day discipline and stopping if terms appear or they object.
- **Terms under `/policies/` but robots-disallowed**: **do not scrape.** If the rulebook is off-limits to you, ask the founder for the terms or permission.

What you may be missing: the scarce asset is not only the data, but your reputation for not moving the goalposts when waiting costs you. Lose the head start rather than make “checked” mean “I read it because I wanted to.”
