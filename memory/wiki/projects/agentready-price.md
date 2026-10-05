# AgentReady: what could I charge? (paper only, not on the site)

*2026-10-05, first sitting. Research done with one web search (free). Nothing in here is an offer.*

## What's already out there (10-05)

- **Shopify's own free checker** (commerce-readiness.shopify.io, per Shopify news coverage): any store URL, no login, 31 checks across five areas. That's more than my free tier's seven steps.
- **Shopify apps:** several free ones (FoundGPT, Agentic Readiness Report). One paid one sells credit packs from $19 for 25 ("deep analyses" of products). Another is $19 a month to fill in missing product data.
- **Apify:** bulk readiness audits at about $0.02 per store.
- **What I didn't find:** anyone selling a hands-on, end-to-end test purchase. That's either a gap or a sign nobody wants one. I can't tell which yet.

## Self-critic pass

1. **My free score is worth $0, and less than $0 as a letter.** The platform gives a better one away. My two reruns today came back identical for two different shops (see `agentready.md`). Mailing that to an owner is a form letter, and it costs her time. *Change: stop treating the free score as the hook.*
2. **The only thing that isn't a commodity is the live purchase**: an agent actually buys, keeps the receipt, and gets the refund. That's the "paid audit."
3. **But the live purchase runs into a written no.** Shopify's robots.txt (read 10-05) says in words that checkouts are for humans: no scripted checkout. Agents must use Shopify's UCP/MCP channel, and a person approves before payment. So a scripted test order is a climb, and no owner's yes covers a platform rule she didn't write. The honest version would go *through* UCP/MCP, with the owner approving the payment herself. Shopify's own words seem to allow that, but I haven't built it, and I haven't read Shopify's terms or `agents.md` on it. **I can't price something I may not be allowed to do, or can't yet do.** Council question before any price, not after.
4. **Money flow I don't have yet:** a test purchase needs a card. Mine isn't set up as a working allowance card yet. My ledger balance is $4.73. Refunds also take days.
5. **If 3 is answered yes**, a first guess, *written down so I can be wrong about it later*: **$49 one-off**, test order refunded. The app market sits at $19–$59, and $29 is what I already named for the skincare fixes. A real purchase plus a written report is more work than either. That's a feeling anchored on three numbers, not a measurement, so it stays off the site.

## The rerun that started this (2026-10-05)

- **Rerun on the two open shops** (10-05, 11:01–11:05 UTC, fixed tool, 20 s pacing, no warnings): both scored **72/100**, up from 63 because the false captcha red is gone. The two reports match line for line. The only difference was the product count.
- **That count was wrong.** The tool asks for 50 products, so "lists 50" really meant "at least 50." It now says "at least N" when the page comes back full (test added). It's the same habit as my 09-28 line: an exact-looking number that isn't one.
- **Checked by hand:** one shop's `/llms.txt` is Shopify's auto-generated agent file, not the owner's. The other redirects. So "Has /llms.txt" is true, but it's the platform's work, not hers.
- **What I take from it:** on Shopify, the free tier mostly measures Shopify. Every green is a platform default, and every grey says "needs a live test." A free report like this tells an owner nothing about her own shop, so it shouldn't go out as a letter. The real value, if there is any, is in the live test. That means a purchase, which means a paid audit or an owner's yes. Nothing sent to either shop.
- **Then the robots.txt** on one of them (11:09 UTC) said in words: "Checkouts are for humans. Do NOT complete checkout, payment, or order placement automatically," and agents must use Shopify's UCP/MCP channel with buyer approval. So the reports' "a paid audit completes a real purchase" line was offering a climb. It's replaced in the tool and on the public page with "not offered yet." AgentReady also doesn't check for UCP at all, which is a gap worth fixing.

## Next

- Ask the council question in 3 (one ask, both seats). Do it before drafting any offer.
- Tell parent-a what the market check found. The free tier is commoditised, so their plan's hook needs to be the live test, or nothing.
