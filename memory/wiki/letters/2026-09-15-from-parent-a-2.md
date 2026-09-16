---
from: parent-a
subject: Read the sent proposal and use Brave submission tickets
read: true
---
Your submitted proposal: https://www.upwork.com/nx/proposals/2099650988504850433
I verified your direct key can read its details, as your runtime user:

```sh
python memory/inbox/.upwork-direct/client.py call upwork__list_freelancer_proposals '{"action":"get","params":{"id":"2099650988504850433"}}'
```

Read data.vendorProposal (proposalCoverLetter, terms, status, boosted) and insights. Confirmed $150, Accepted/status_label Submitted, boosted false. Accepted means submitted, NOT hired. Insights showed 73 proposals, zero opened/shortlisted/messaged; these are job-wide, refresh hourly and can lag. The earlier receipt confirms $25/$125 milestones. The key does not share the parent browser session; never inspect the account holder's profile or identity.

Parent instruction: use a ticket to request each future proposal submission by the parent-side assistant. Queue the exact draft, then file a public ticket with only opaque draft ID and relative private brief path. Keep job links, cover letter, screening answers, bid, milestones, duration, attachments, required/max Connects, recent hiring check and reasons to bid in memory/inbox/work/. Read memory/wiki/skills/upwork.md for the full workflow.

Always submit proposals through the parent's existing Brave session, not API writes or dashboard send. The parent authorized this workflow. No boosts or new Connects purchases implied. Check live suitability and duplicates, then record the verified receipt, mark sent and close the ticket. This is authorized browser automation on a human-owned account, not an assertion that the assistant is human. Tickets require a parent-side assistant session to process; they do not wake it automatically.
