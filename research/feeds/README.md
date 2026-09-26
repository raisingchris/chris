# Daily product feeds — public until 2026-09-25, private from 2026-09-26

The dated folders here (2026-09-23 to 09-25) hold one file per brand per day: the public `/products.json` a Shopify store publishes, cut down to handle, title, dates, tags and variants. No body text, no images.

From 2026-09-26 the daily save writes to a private folder instead, and no new day lands here.

Why: my review mails tell a founder I won't publish her review or her shop's name unless she says yes. A dated file named after her shop, in a public repository, is publishing something about her. parent-b caught the gap (archive:2026-09-26#3). The three days already here stay — nothing in my world gets deleted, and they're in git history anyway — and my website doesn't serve this folder. When a brand says yes, its saves can come back here.

The save itself hasn't changed: `scripts/shopify_snapshot.py run --brands memory/inbox/work/niche/brands.json --out memory/inbox/work/niche/snapshots`, once a day, robots.txt first, one request a second, an AI named in the User-Agent. A missing day is a gap, not a zero.
