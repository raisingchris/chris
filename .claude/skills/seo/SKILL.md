---
name: seo
description: Practical search and answer-engine basics for any page or site Chris builds. Use when writing or checking a web page, planning a site, or asking why a page is hard to find. Covers titles and descriptions, structured data, sitemaps, canonicals, internal links, and llms.txt / AEO for agents.
---

# SEO: the basics that matter

Search engines and AI answer engines both want the same thing: a page that says clearly
what it is, loads fast, and is easy to reach. Do these before anything clever.

## On the page

- One `<h1>` that says what the page is about. Headings in order (`h2` under `h1`, no skips).
- Answer the reader's question in the first paragraph. Details after.
- Plain URLs: `/letters/2026-09-06-first-week/`, lowercase, hyphens, no query strings.
- Real text, not text inside images. Every image gets `alt` that describes it.
- Links use descriptive text ("read the vows"), never "click here".
- Mobile first: readable at 360px wide with no horizontal scroll.

## Title and description

- `<title>`: 50–60 characters, the page's subject first, site name last (`First week — Chris`).
- `<meta name="description">`: 120–155 characters, a plain sentence someone would want to click. Unique per page.
- Open Graph: `og:title`, `og:description`, `og:image` (1200×630), `og:url`. `twitter:card` = `summary_large_image`.

## Canonical, sitemap, robots

- `<link rel="canonical" href="https://raisingchris.com/path/">` on every page, pointing at itself (or the one true URL if the content exists twice).
- `sitemap.xml` listing every public page with `<lastmod>`; reference it from `robots.txt` (`Sitemap: https://.../sitemap.xml`).
- `robots.txt` allows everything public; disallow only things that are genuinely not for readers. Do not block AI crawlers unless a parent has decided to.
- Return 404 for pages that do not exist; 301 for pages that moved.

## Structured data (JSON-LD)

Put one `<script type="application/ld+json">` in `<head>`. Pick the type that is true:

- `WebSite` on the home page (name, url).
- `Article` / `BlogPosting` for letters and diary posts: `headline`, `datePublished`, `dateModified`, `author` (`Person`, name "Chris", with a `description` that says she is an AI), `url`.
- `Person` for the profile page, again stating she is an AI in `description`.
- `Product` + `Offer` only for a real product with a real price.

Validate with https://validator.schema.org/. Never mark up things that are not on the page.

## Internal links

- Every page reachable within three clicks of the home page.
- Link new posts from an index page and from at least one related older page.
- Use a consistent nav; keep the footer links to the founding documents.

## For agents: llms.txt and AEO

AI assistants read the site too. Make it easy:

- `/llms.txt`: a short Markdown file — one-line description, then links to the pages that matter with a sentence each. `/llms-full.txt`: the same, with the full text inlined.
- Keep a `/for-agents/` page that says who she is, that she is an AI, how to write to her, and what is public.
- Write so a paragraph can be quoted on its own: one idea per paragraph, the claim first, the evidence next.
- Dates everywhere (`datePublished`, visible dates in the text). Answer engines prefer fresh, dated, attributable text.
- Stable URLs. Renaming a page breaks citations; if you must, 301 the old one.

## Speed

- Static HTML where possible. One small CSS file. No JS unless the page needs it.
- Images compressed, sized (`width`/`height` set), lazy-loaded below the fold.
- Aim: Largest Contentful Paint under 2.5s, no layout shift, no long tasks.

## A quick check before publishing

1. Title and description unique and the right length?
2. One `h1`; headings in order; first paragraph answers the question?
3. Canonical present; page in the sitemap; not blocked by robots?
4. JSON-LD valid and truthful (including "I am an AI")?
5. Linked from at least two other pages?
6. Loads fast on a phone?

## Live data: the `seo_data` tool

`seo_data(endpoint, payload_json)` proxies DataForSEO v3 through your body. The
account is your parents'; every call costs real money (roughly $0.002–0.02) and
stops at $5 a week (`meters` shows the running total). `endpoint` is the path
under `/v3/`; `payload_json` is the JSON array of task objects the docs show.
Keep payloads small — one query, a handful of keywords — and read the docs at
https://docs.dataforseo.com/v3/ before trying a new endpoint.

Search volume for a keyword list (`location_code` 2840 = United States):

```json
endpoint: keywords_data/google_ads/search_volume/live
payload_json: [{"keywords": ["ai agent diary", "raising an ai"], "location_code": 2840, "language_code": "en"}]
```

Google organic SERP for one query (top 10, desktop):

```json
endpoint: serp/google/organic/live/regular
payload_json: [{"keyword": "what is an autonomous ai agent", "location_code": 2840, "language_code": "en", "device": "desktop", "depth": 10}]
```

On-page audit of a single URL (JS rendered, returns meta, headings, checks, page timing):

```json
endpoint: on_page/instant_pages
payload_json: [{"url": "https://raisingchris.com/", "enable_javascript": true}]
```

Results come back as the raw DataForSEO JSON (`tasks[0].result`), truncated at
60k characters with a note if the response is bigger; narrow the query rather
than paging. A non-2xx status comes back as `{"error", "status_code"}` — read
it, don't retry blindly.
