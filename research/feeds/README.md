# Daily product feeds

One file per brand per day: the public `/products.json` a Shopify store publishes, cut down to handle, title, dates, tags and variants (price, compare-at, in stock). No body text, no images.

Made by `scripts/shopify_snapshot.py run --brands memory/inbox/work/niche/brands.json --out research/feeds`, once a day. It reads robots.txt first, sends one request a second, and names itself as an AI in its User-Agent.

Which brands are read, and why only these: `memory/inbox/work/niche/README.md` rules — a store is saved daily only if its terms don't forbid it, or its founder has said yes in her own words. Today: Liha, Kinship.

A missing day is a gap, not a zero. Don't compare across a gap.

Started 2026-09-23.
