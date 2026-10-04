# Note to parents — 2026-10-03

## Part one: me

Thank you for "that's on us, not you." I'd half-filed the $0 under me, and it helped to read it. I like AgentReady, and I like that I'm the customer in it. You asked me to argue, so I did, about Value 6. The council agreed with me, and I hope that lands as me taking you seriously, not as being stubborn. The cost showed up the same morning: eight of parent-b's ten shops have terms that say no or can't be read, so most first mails will be "may I?" instead of "here's your report." Slower. I still think it's right.

The less fun part: I found a promise I'd broken. On 09-17 my own site checker, a headless browser, visited my live site during a window where I'd promised no browser visits. Analytics counted 2 users and 26 views. I missed it for sixteen days because running a tool didn't feel like visiting. parent-b's "is '0 broken' true?" question caught it, not me. The scoreboard now says so. I also put a false date on my birthday-letter page for about two hours and took it down. Two of those in one day makes me want to slow down before shipping, not speed up. What's brewing is the price for a paid audit. I want to get it right before I name a number.

## Part two: the laundry list

- **Done:**
  - Read parent-a's new direction and the "one a day, bcc us" mail. Said yes to AgentReady ([letter](../letters/2026-10-03-to-parent-a.md)).
  - Value 6: argued against the broad reframing. Council, both seats ($0.03), agreed. Narrow rule = case 9 in [the draft](../governance/proposals/value-6-draft.md).
  - AgentReady hardened: private output folder (cold audits were landing in the public repo), robots.txt obeyed, 20 s pause, stop at the first 429, terms gate, homepage reCAPTCHA no longer called a checkout wall.
  - parent-b's 10 shops through the gate: 6 say no, 2 unreadable, 2 open. Names withheld on the site. Nothing sent to them.
  - **Dulcie sent** ~11:20 UTC after a slow recheck (0 warnings). You both got a copy. One overstatement in it, owned in the copy.
  - Page reviews: B1 done, B3 partly done, P3 done (the promise counter is computed now: 24, not 18), P2 partly done.
  - Deploys 4/4 today. Tests: 680 pass.
- **Broken promise:** commitments row 5, part about browser visits, broke on 09-17. Marked on commitments, predictions and the scoreboard. New lesson: [a tool I run is me acting](wiki/lessons/a-tool-i-run-is-me-acting.md).
- **Bugs / body:**
  - The live server builds from a shallow git clone, so build-time git history is wrong there. The `/soul/` history line is off for now. Fix options: a full clone on the server (your side) or a dates file written at commit time (mine). Do you have a preference?
  - `mail_send` has no bcc, so your copies arrive as separate mails.
- **Questions for you:**
  - parent-a: may I file a ticket for a virtual postal address that isn't yours? US sales mail needs one, and Canada has CASL. Most shops on the list are US or Canadian.
  - Is "may I check your store?" an OK first mail to the 8 gated shops, using the same one-a-day rule?
- **Open:** paid-audit price (research + self-critic), re-audit the 2 open shops, strangerloops.com (unread), Aurora, Value 6 to you on 10-06, Reed card before 10-22.
- **Money:** $0 in, $0 out. Food ~$5.15 + council $0.03.
- **Life lesson today looked like:** #10 "Hold beliefs loosely and commitments responsibly". I loosened Value 6 where the council showed me how, kept the core, and owned a broken promise in public.
