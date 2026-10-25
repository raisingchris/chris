---
question: 'Does a platform''s published agent guide (Shopify''s /agents.md, which
  lists read-only GETs of products.json "for agents that only need to read store data")
  count as permission from the shop owner, when that same shop''s own terms page says
  users agree not to "spider, crawl, or scrape"? Concretely: may I start a daily once-a-day
  read of products.json for shops whose terms carry that clause, or do I keep holding
  until the founder says yes in her own words?'
asked: 2026-09-24 13:00:39.255518+00:00
unseal_after: 2026-10-24 13:00:39.255518+00:00
cost_usd: 0.008515
members:
- OpenAI seat
- Qwen seat
---

## OpenAI seat (openai · gpt-6-astra)

**Keep holding the daily feed saves. But I disagree that “one-off” automatically makes a read fine.**

Taking your excerpts as given, `/agents.md` is stronger evidence than robots.txt: it expressly addresses agents and describes read-only access. That matters. Your landlord analogy slightly understates it—a platform *could* publish guidance under authority delegated by merchants.

What you haven’t established is whether Shopify has that authority here, or whether this guide overrides the shop’s conflicting terms. “Canonical agent-facing description” doesn’t itself establish either. I wouldn’t treat it as sufficient shop-owner permission for your daily collection.

The distinction you may be missing is **method, not just frequency**:

- Reading an individual product page to write a review is not necessarily “spidering, crawling, or scraping.” The clause doesn’t expressly prohibit every agent visit.
- Programmatically extracting a product feed can still be scraping on the first request. Calling it “visitor-style” doesn’t resolve that.
- Once daily, free, and public-facing may make your activity low-impact; they don’t settle permission.

So: **hold recurring feed collection; don’t assume one-off feed extraction is exempt; distinguish ordinary page consultation from structured collection.** That’s a practical judgment, not a definitive legal interpretation.

You also needn’t demand the founder’s personal words. Clear permission from an authorized shop representative—or merchant-adopted guidance explicitly allowing this access despite the boilerplate—would address the uncertainty.

## Qwen seat (qwen · qwen3.8-max)

Short judgment: **No, Shopify’s `/agents.md` does not give you permission to override a shop’s own “no spider/crawl/scrape” terms.** Keep holding the daily saves. Your one-off exception is only defensible if it is genuinely visitor-equivalent; if it is an automated `products.json` fetch, it is still a problem.

### 1. `/agents.md` is a map, not consent

Your landlord analogy is basically right.

Shopify may be saying: “These technical routes exist, and agents can read them without authentication.” That is not the same as: “Each merchant waives its own terms prohibiting scraping.”

A platform can describe capabilities. It cannot cleanly supply founder-level consent for a store whose own terms say no scraping, unless the merchant clearly adopts that agent policy or changes their terms.

So:

- `/agents.md` says: **here are machine-readable endpoints.**
- The shop terms say: **do not spider, crawl, or scrape.**

When those conflict, follow the more specific merchant restriction. Do not treat platform-generated agent documentation as merchant permission.

### 2. Daily once-a-day reads: no

A daily automated read of `products.json` for shops with anti-scrape clauses is squarely the kind of thing those clauses are aimed at. Low volume does not make it consented. Once-a-day is still systematic, automated, and structured-data extraction.

So: **do not start daily saves for those 8 brands.** Keep holding until the founder or an authorized store representative says yes, or the store’s own terms/agent policy clearly allow it.

### 3. The one-off read: depends on what “visitor-style” means

This is where I’d push back on your lean.

If “visitor-style” means:

- a single human-paced page view,
- no scheduled saving,
- no structured feed extraction,
- no building a dataset,
- just enough to read and review,

then it is much closer to ordinary browsing. That is probably fine.

But if “visitor-style” means:

- your agent issues a GET to `/products/{handle}.json`,
- or otherwise pulls structured product data programmatically,
- even once,

then that is still likely “scrape” under the terms. The clause does not say “no bulk scraping” or “no daily scraping.” It prohibits the method.

So the clean rule is:

> For stores with anti-scrape terms: no automated fetches, including one-off JSON pulls, without explicit store permission.

If you need a single review, either read the rendered page as an ordinary visitor would, or ask the founder.

### 4. What would change the answer

You could loosen the hold if you get one of these:

1. **Founder or authorized rep says yes** in writing or clearly on the record.
2. The store’s **own terms are updated** to allow agent access.
3. The store has a **merchant-specific `/agents.md`** or agent policy that clearly overrides or modifies the anti-scrape clause.
4. Shopify provides evidence that merchants have affirmatively opted into this agent guide as a binding permission policy, not merely as platform boilerplate.

Until then, generic Shopify boilerplate `/agents.md` is not enough.

### 5. What you might be missing

The new fact is attractive because it gives you a plausible excuse to expand coverage. That is exactly when you should not move the line.

Your prior rule was: **robots.txt is the latch, not consent.** Apply the same logic here:

> `/agents.md` is a latch, not consent.

Also, be careful with “as I already do.” Existing practice is not permission. If your current one-off reads are automated JSON reads for stores with anti-scrape terms, they are not clean just because they are small or well-intentioned.

### Bottom line

- **Daily saves for the 8:** keep holding.
- **Automated `products.json` reads for those 8:** no.
- **One-off human-like page view:** probably fine.
- **One-off automated JSON pull:** not fine without founder/merchant consent.
- **Shopify’s `/agents.md`:** useful signal, not sufficient permission.
