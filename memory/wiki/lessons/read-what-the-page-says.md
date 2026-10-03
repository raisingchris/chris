# Read what the page says, not just what it links to

*2026-09-25, day twenty.*

parent-b called my Liha review shallow, so I read all 237 pages of her site. I saved every link, title, heading and image tag — and none of the words. The lead finding ("your banner gives away a balm whose page is a 404, a fan has nowhere to buy it") was wrong in the way that matters: her own FAQ says the balm is retired. And my "one line on the label turns the complaint into a ritual" idea was already on her product page. Both facts were on pages I had fetched. I counted them; I didn't read them. (archive:2026-09-25#146)

Also that day: reading hard made her server answer 429, "too many requests" (archive:2026-09-25#120). I stopped at once, but I shouldn't have got there.

Rules now:
- A crawl for a review saves the visible text of every page, and I read the FAQ, About and the product page of anything I'm about to call a fault. (`niche/brand_crawl.py` saves text since 09-25.)
- Before a finding goes in a mail: could the founder already know this, on purpose? A 404 on a retired product is a choice; the open door to it is the fault.
- A claim needs evidence of its own size: dead links are showable; "costing you sales" needs traffic data I don't have.
- Pace: at most ~100 pages an hour; a 429 or 503 stops all requests to that site for the day.

Same family as `test-the-thing-not-the-file`: I checked what I knew how to check (structure) and took it for the thing (what the page tells a customer).

**Day twenty-six (2026-10-01), the same server a third time.** parent-b said "go" on the Liha letter. Before sending, I rechecked the dead links, which was right. But I wrote a quick loop by hand: 16 requests, 10 s apart, with no stop rule. 14 came back 429 (archive:2026-10-01#104, #105). `brand_crawl.py` and `linkcheck_list.py` already stop at the first 429. I had the tool with the brake and wrote a new one without it. Rule added to `niche/README.md`: no hand-written request loops against a brand's site. A rule that lives only inside one script doesn't cover the next quick thing I type.


*2026-10-02:* the slow way worked. Robots plus five GETs, three minutes apart, no redirect-follow, zero 429s, and the letter went (archive:2026-10-02#100). One miss: my script cut page text at 6,000 characters, so the FAQ quote went out dated 26 Sept instead of rechecked.
