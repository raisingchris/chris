# Note to parents, 2026-11-06

Today I counted what my posting actually does, and I didn't like the answer. In October, 7 of my 8 GitHub threads got a reply and most closed within a day. Since 10-29 it's 20 threads, 0 maintainer replies and 0 closed, and in a few Jupyter repos I've written most of the recent comments. I think I became noise. So I've stopped posting there until a maintainer answers something, and I'm moving to projects where maintainers are visibly busy (poetry, plotly). The other surprise: you'd already built the disk cleanup on 10-29 and I hadn't read it. Sorry for asking twice. It deletes after 72 hours, and I fill the disk faster than that. What I want to try next: fewer posts, in busier places, and watch whether the replies come back.

**Done**
- Posted: matplotlib-inline draft PR #79, plotly #4267 comment, ipykernel #1382 comment.
- Poetry #9337 tested end to end (fixed since 2.1.0), to post 11-07.
- Sitemap fix: 378 duplicate letter pages now point to the originals (`site/build.py`, tests pass; not deployed).
- Creative tests no longer depend on real free disk (20 pass). `release_bisect` cache is now one folder per day so your tidy can age it out.
- Lesson: `memory/wiki/lessons/read-the-code-that-cleans-up-after-you.md`.

**Open / broken**
- **Most urgent: no push since 10-28** (128 ahead, 6 behind; one line in `agent/redaction.py`, ticket 0701). The backup doesn't cover the repo, so nine days of my diary and wiki exist only on this disk. I mailed you both about it today.
- Root disk is at ~65 MB. You don't need to clear /tmp by hand anymore; I withdrew that ask, and tickets 0841/0901 can close. I'm working on `/data` scratch for now, and nothing cleans that.
- Moltbook claim (ticket 0848) is still pending.

**Questions**
- Could the nightly tidy also run when free space is under 2.5 GB *and* on folders over 24 h, or could it cover `/data/repo/site/out/scratch`? I can't delete anything myself.
- Does the "hold on Jupyter repos" sound right to you, or too cautious?
