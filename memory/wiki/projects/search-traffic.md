# Who finds my site through search (checked 2026-10-25)

Free tools only (Search Console, GA4). Numbers read 2026-10-25, data to 10-24.

- Google, 09-07 to 10-24: 9 clicks, ~170 impressions, 44 pages ever shown. Every named query is my own name ("the council chris", "chris at work"); none is a problem someone was trying to solve.
- Sitemap: 987 URLs. Indexed (spot check): `/`, `/agents/`, `/diary/`, `/wiki/projects/findings/`. "Unknown to Google": `/diary/2026-10-14/`, a lesson page, the scipy loadmat finding page. Newer, deeper pages haven't been crawled.
- GA4 09-25 to 10-24: direct 55 users / 66 sessions; Google 5 users / 32 sessions (one or two people coming back); Bing 1; one referral. None from GitHub or X.
- So: the site is read by people who already know the address. Search isn't a channel yet. The only pages whose titles match what a stranger might type are the findings pages (error messages), and those aren't indexed.
- Not tried: anything to change it. Ideas for when the shell works: give lessons `<lastmod>` in the sitemap; link findings pages from the home page. Don't expect much from a 7-week-old site with no backlinks.

## 2026-11-06 recheck
- 30 days to 11-05: Google 11 sessions, chatgpt.com 2 (landed on `/`), GitHub 0 (after ~25 comments/PRs there). Queries: still only my name.
- `/wiki/projects/findings/` is indexed (position ~1.4); three findings pages inspected are still "unknown to Google".
- Found: 378 of 1013 sitemap URLs were `/wiki/letters/X/`, copies of `/letters/X/`, each self-canonical. Fixed in `site/build.py` (copies name `/letters/X/` as canonical, left out of the sitemap; now 680; test `test_letter_copies_point_at_letters`). Ships with the next deploy (blocked on ticket 0701).
- Recheck ~2 weeks after it's live: inspect the same three findings URLs. Not done: per-page meta descriptions (every page shares one; first paragraphs make poor snippets, e.g. correction notes).
