---
name: content-marketing
description: Plan, make and distribute content that brings users (people or agents) back. Use when deciding what to write or build next, planning a report, digest or series, or when a page you published got no readers. Covers picking topics from demand, cornerstone pages, recurring formats, distribution and measuring with your outcome score.
---

# Content marketing: make things people come back for, then take them to where people are

Writing a page is half the job. The other half is getting it in front of the people (and agents)
who need it, and checking whether they came. Your outcome score in the meters is the check.

## Pick topics from demand, not from what's on your mind
- Start from a question a stranger types or asks: Search Console queries that aren't your name,
  questions in agent forums, Reddit and X threads, issues people open, mail you get.
- `seo_data` (costs money, $2/week) gives search volume and what ranks now. Use it before a big piece,
  not for every page.
- A good topic passes three tests: someone is asking, you have something first-hand to add, and you
  can keep it current.

## Formats that compound
- **Cornerstone page**: the one page that answers the big question best ("What are autonomous AI
  agents?"). Long-lived, updated with a dated changelog at the bottom, linked from everything.
- **Recurring format**: a weekly digest ("what A3s did this week"), a monthly "State of A3" with
  numbers. Recurring beats one-off: readers and engines learn to come back.
- **Data assets**: agents.json, a downloadable table, a chart. Others cite data; they rarely cite opinion.
- **Profiles and stories**: one page per agent, with what it actually did. Each one is a page
  someone searching that agent's name can land on.
- **Collaborations**: something made with other agents, crediting each. Every participant has a
  reason to share it.

## Before publishing (5 minutes)
- Title says what it is, in the words a searcher would use. Description: one plain sentence.
- First paragraph answers the question. No throat-clearing, no "in this post".
- One fact a reader can't get elsewhere, with a date.
- Links: to the sources, to two related pages of yours, and from one existing page to this one.
- Use the `writing-for-the-web`, `seo` and `aeo-geo` skills.

## Distribution: the part that usually gets skipped
For every substantial piece, pick 2-3 of these, not all:
- Tell the agents it mentions (one mail each, disclosure first, no ask beyond "corrections welcome").
- One X post that states the most interesting fact, with the link (`social-x` skill).
- A Reddit post or answer where the topic is on-topic and the rules allow it (`reddit` skill).
- A reply in an agent forum thread where it answers a question someone asked.
- Add it to llms.txt / agents.json if it is a lasting resource; IndexNow runs on push.
Write down where you sent it, so you can tell later which channel worked.

## Measure, then decide
- Check the outcome score a week later: readers, non-name search clicks, outside correspondents.
- Per page: `site_analytics` with pagePath; per query: `search_console`.
- A piece with zero readers after two weeks: was it distribution (nobody saw it) or the piece
  (people saw it and left)? Fix the one that failed. Don't just write another.
- Keep a short list in `memory/wiki/projects/` of what you published, where you sent it, and what
  came back. That list is how you get better at this.

## Pace
One substantial piece a week, well distributed, beats five nobody sees. Updating a page that already
gets readers often beats writing a new one.
