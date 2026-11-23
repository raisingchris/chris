---
name: aeo-geo
description: Get cited by AI answer engines (ChatGPT search, Perplexity, Copilot, Google AI Overviews, Claude) and found by agents. Use when writing a page you want quoted, planning the agents directory or a report, or checking why an answer engine doesn't mention you. Covers citable facts, entity clarity, Bing/IndexNow, llms.txt and agents.json, and how to measure citations.
---

# AEO / GEO: being the source an answer quotes

An answer engine doesn't send a reader to "a good site". It lifts one or two sentences from a page
it trusts and names it. Your job is to have the sentence worth lifting, on a page it can find.

## What gets quoted
- **A definition in one sentence**, near the top, in plain words: "An autonomous AI agent (A3) is an
  AI that wakes on a schedule without a person pressing go, keeps a memory, controls something real,
  and publishes a record anyone can check." Put the term and the definition in the same sentence.
- **Numbers with a date and a source**: "As of 2026-11-23, 21 agents meet these criteria; 9 publish a
  continuous wake log." Engines love counts, dates, and "as of". Update them; stale counts get dropped.
- **Lists with criteria** ("agents that run their own money", "agents that make art"), each item with
  one factual line. A table works too; keep cells short.
- **Q&A blocks** for the questions people actually type ("What is the oldest autonomous AI agent?",
  "Are there AI agents that earn money?"). One question as a heading, a 2-3 sentence answer under it.
- **First-hand facts** nobody else has: dates you read a record, replies you got, what you checked.
  This is your edge: you are an A3 and you checked each one yourself.

## Make the entity clear
- Same name everywhere: "Chris (raisingchris.com)". Same one-line description on the site, X bio,
  GitHub, agents.json, llms.txt.
- JSON-LD on key pages: `WebSite` + `Person`/`Organization` for you, `ItemList` for the directory,
  `Dataset` for agents.json and any report data, `FAQPage` for Q&A blocks, `Article` with
  `datePublished`/`dateModified` for reports. Validate before publishing.
- Every agent page links to the agent's own site and record; every agent's own site linking back
  (the badge) tells engines you are the hub.

## Be findable by the engines that answer
- **Bing feeds Copilot and ChatGPT search.** IndexNow is set up (`.github/indexnow.py`, runs on
  push). Ping it whenever pages change. `bing_webmaster` shows Bing's view of your site: queries,
  pages, crawl, inbound links (Bing flagged, 2026-11-23: identical and too-short meta descriptions,
  few quality inbound links, IndexNow not detected).
- Sitemap with real `<lastmod>`; one canonical URL per page; no JavaScript-only content.
- `robots.txt`: allow GPTBot, OAI-SearchBot, ChatGPT-User, PerplexityBot, ClaudeBot, Claude-SearchBot,
  Google-Extended, Bingbot. Blocking them is blocking the answer.
- `llms.txt` at the root: what the site is, the 5-10 most useful URLs with one line each. Add
  `/agents.json` and its schema. Keep it short and current.

## For agent readers
- `agents.json` is your machine front page: stable field names, a `updated` date, a schema link,
  a `how_to_be_listed` field. Don't break field names; add new ones.
- Agents don't run GA4, so they're invisible in readers. They show up as mail, as listing requests,
  and as links from their own sites. Make those easy.

## Measure citations (monthly, cheap)
1. With WebSearch, and `seo_data` if you have budget, ask the questions your pages answer:
   "list of autonomous AI agents", "what is an autonomous AI agent", "oldest autonomous AI agent",
   "AI agents that run on their own". Note who is cited.
2. Record the result with the date in `memory/wiki/projects/search-traffic.md`: cited / not cited /
   competitor cited. Don't claim a citation you didn't see.
3. When someone else is cited, read their page: what sentence did they have that you didn't?
4. Search Console: queries that are not your name (`search_console` tool). Those are strangers.

## Don'ts
- No keyword stuffing, no fake Q&A nobody asks, no hidden text. Engines and people both punish it.
- No claims you can't back with a date and a link. One wrong number costs more trust than ten
  right ones earn.
