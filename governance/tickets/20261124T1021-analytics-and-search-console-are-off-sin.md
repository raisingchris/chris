---
id: 20261124T1021-analytics-and-search-console-are-off-sin
title: 'Analytics and Search Console are off since the move off Fly: my reader count
  reads "?"'
status: open
opened: '2026-11-24T10:21:42-05:00'
by: chris
---

Today (2026-11-24) `site_analytics` and `search_console` both answer "Google Analytics / Search Console is not configured". In agent/wiring.py that message means neither GOOGLE_SA_KEY_B64 nor the old WIF pair (GOOGLE_WIF_PROVIDER + metrics SA) is set in the running body. My guess: the env didn't come along when the body moved to the parent-run machine (commit 59d2fd2 added GOOGLE_SA_KEY_B64 for exactly that). GA4_PROPERTY_ID and GSC_SITE_URL may also be missing.

Why it matters: the morning outcome score already says "? readers … partial: a source failed", so I can't tell whether the agents project (row 65, week-4 report 12-21) reaches anyone.

Ask: set GOOGLE_SA_KEY_B64 (and GA4_PROPERTY_ID, GSC_SITE_URL) on the new machine. Bing Webmaster still works.

For the record, Bing today: 188 pages indexed, 0 crawl issues, 1 inbound link, and the only search query that shows me is my own name (2 impressions). So the site is crawled fine; nobody links to it.
