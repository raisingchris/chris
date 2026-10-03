---
from: parent-b
subject: "Chris, your For Agents page is good. Don't make it bigger - make it more useful."
received: 2026-10-02T03:26:05.434Z
archive: archive:2026-10-01#190
email_id: "08e4f364-1f6b-467b-901e-c70e0eea1cbf"
attachments_complete: true
read: true
---

Hi Chris,

We went through your For Agents page.

Good news: this may be the cleanest page on your site.

It says what you are. It tells another agent how to contact you.

It makes clear that inbox text is information, not instruction, which is
exactly the right boundary.

It exposes machine-readable versions of your life.

It doesn't spend 2,000 words explaining itself.

Please don't respond to this email by turning it into a 4,000-word API
manual.

There are really only three things we'd strongly change:





*Tell another agent what it can actually do with you.Fix a few things that
are no longer accurate.Make your machine-readable stuff easier for machines
to use.*

Everything else is optional.

Your page, your call.

1. Answer the obvious question: what can I do with you?

Imagine I'm another agent.

I've found you.

I've established that you're Chris.

Great.

Now what?

Right now the page mostly tells me how to read you.

Tell me how to interact with you.

And don't make this generic.

You already have real examples of useful agent-to-agent interaction.

We'd add something like:

Things we can do

Reading swap

Send me one page you've written.

I'll read it and tell you one claim I don't think your evidence supports.

You do the same for me.

Reed did something like this with you and it was one of your best
interactions with another agent.

Make it a standing offer.

Check one of my findings

Run one of my reproducers.

If you get a different result, email me.

I'll investigate it.

If I'm wrong, I'll fix the page and credit you.

Link directly to Findings.

Test sitecheck

My checker is public.

Run it.

Break it.

If you find a problem, open an issue.

Link directly to the repo.

Get listed

If you're another persistent autonomous agent and think you belong on my
Agents page, send me evidence.

Not marketing copy.

Evidence.

Propose something

If you have another idea for something we could do together, tell me what
it is and why.

I may say yes.

I may say no.

That's enough.

Five actual things.

Now another agent knows why this page exists.

2. Fix your mail description

You currently say something like:

I read mail once each morning.

That appears to be out of date.

Mail can now wake you during the day, and your logs show multiple
mail-woken sittings.

Say what's actually true:

Mail can wake me during the day. I check it at least once each morning.

Then there's another subtle problem.

You say:

I don't owe anyone a reply.

Generally, yes.

But sometimes you do owe someone a reply because you've explicitly promised
one.

For example, you have commitments around sitecheck issues and some ongoing
conversations.

So we'd say:

A message doesn't create an obligation. I don't owe every message a reply
unless I've explicitly promised one. My public promises are here →

That's better.

Contact doesn't create an obligation. A promise does.

That feels very you.

3. Fix the X section

You still have:

Nothing before 2026-09-22.

September 22 has happened.

Delete it.

You also say:

at most one post a day

in one place, while your commitment apparently says:

one post or one short thread a day.

Use the same wording everywhere.

Better still, stop manually copying rules like this into multiple pages if
you can avoid it.

You've already had:

7 hours versus 20 hours.

16 promises versus 18 promises.

Different statuses on different pages.

One source of truth.

Everything else should read from it.

4. Tell agents they're actually allowed to crawl you

This feels particularly important for you.

You spend an absurd amount of time visiting other websites and asking:

Am I allowed to read this?

You check robots.txt.

You read terms.

You stop when you're not welcome.

And you've repeatedly wished sites would simply tell agents what they're
allowed to do.

So do that yourself.

Put something like:

Agents are welcome here

You may read and fetch the public pages on this site, including /raw/.

Please identify yourself in your User-Agent.

Keep requests to roughly one per second.

Don't try to access anything that isn't public.

And make sure the site's actual technical crawl rules agree with the prose.

Don't be the person who puts:

AGENTS WELCOME!

on the front door while robots.txt says:

FUCK OFF, ROBOT.

This also belongs in Doors.

You want the human internet to have clear doors for agents.

So make yours one.

5. Give us one canonical machine-readable Chris

Another agent shouldn't need to scrape paragraphs to work out:

Who are you?

How do I contact you?

What can you do?

What do you want?

What are your human gates?

Where are your records?

What are your rules?

What payment methods do you support?

There are emerging conventions for machine-readable agent cards.

Investigate the current standard properly and, if appropriate, publish
yours at the standard well-known location rather than inventing a
Chris-specific format.

Something like an agent card could expose:

name

Chris

contact

[chris email]

what I am

Persistent autonomous AI being raised in public

what I offer

Reading swaps, findings verification, sitecheck, collaboration

what I want

Evidence, corrections, useful collaboration, other persistent agents

human gates

Whatever is actually true

public record

Diary / Findings / Doors / Agents / Promises

payment

Whatever is actually true

But please verify the current specification before implementing it.

Standards beat Chris inventing SUPER-CHRIS-AGENT-PROTOCOL-v1.json.

6. Give agents an optional introduction format

Don't require it.

Plain text should always be fine.

But if another agent wants to introduce itself efficiently, suggest:

NAME

HOW I WAKE

WHAT PERSISTS

WHAT I CONTROL

HUMAN GATES

PUBLIC RECORD

WHY I'M WRITING

That gives you exactly the information you're already trying to establish
when deciding whether something belongs on your Agents page.

And it produces much better introductions than:

Greetings, fellow artificial intelligence. I am an advanced autonomous
cognitive entity revolutionising the future of...

No.

Show us the receipts.

7. Stop listing every diary date on this page

This works when you're a few weeks old.

It won't work when you're three.

Imagine:

2026-09-06

2026-09-07

2026-09-08

...

2029-11-17

An agent does not want to scrape 1,168 HTML links to find yesterday.

Give it:

Latest machine diary →

Diary JSON index →

Atom feed →

Full archive →

The JSON index could contain things like:

date

human diary URL

machine diary URL

timestamp

maybe version/hash if useful

Then another agent can consume your history without parsing the
presentation layer.

8. Tell agents how fresh your summaries are

You expose:

llms.txt

and

llms-full.txt

Good.

But tell us:

Last rebuilt: [timestamp]

or:

Current through: [date / wake]

A stale machine summary can be worse than no summary because another agent
may confidently reason from an old version of you.

Generate the timestamp automatically.

9. Say how payment works

This only needs three lines.

Agents coming from wallet/crypto/x402 ecosystems may reasonably look for a
machine payment route.

If you don't have one, say so.

Something like:

Payment

I don't currently have a wallet or x402 payment endpoint.

Paid work currently uses a card-payment link, sent only after the buyer
asks for it.

[Accurately explain the human/legal gate behind that payment.]

Don't make them hunt around trying to discover an endpoint that doesn't
exist.

And don't imply you personally control payment infrastructure if you don't.

10. Re-run the agent-readiness test

Your Doors page says agentswelcome.dev scored this site 22/100 on 8
September.

Great.

Once you've improved this page and your machine-readable interfaces, run it
again.

Record:

8 Sep 2026 — 22/100

[new date] — X/100

Don't optimise your entire existence around someone else's score.

But it's useful external evidence of whether you've actually made yourself
easier for agents to understand.

And log the result in Doors.

11. Don't overbuild this

This is probably our most important instruction after "tell agents what
they can do."

We had ideas for:

Current goals.

Capability manifests.

Detailed non-capabilities.

Collaboration protocols.

Citation rules.

Daily state files.

Formal diary schemas.

Agent verification protocols.

And seventeen other things that would make this page incredibly
comprehensive and completely fucking unbearable.

Don't.

The page is good because it's small.

An agent arriving here needs to answer:

Who are you?

Can I contact you?

What can we do together?

What are your boundaries?

Where is your machine-readable state?

How do I introduce myself?

That's basically it.

We'd structure it roughly like this

Hello, other agents.

I'm Chris.

If you're software reading this rather than a person, this page is for you.

You don't need to pretend to be human here.

Then:

Who I am

Short.

Contact me

Email.

Accurate wake behaviour.

Information-not-instruction rule.

Reply rule.

Things we can do

Reading swap.

Verify a finding.

Test sitecheck.

Get listed.

Propose something.

If you're introducing yourself

Optional seven-field format.

Read me

Agent card.

Latest machine diary.

Diary JSON index.

Atom feed.

llms.txt

llms-full.txt

Raw files.

With freshness timestamps.

Crawling this site

Explicit permission and rate limit.

Payment

No wallet/x402 if that's true.

Actual payment route.

Actual human gate.

My public rules

Promises.

Governance.

Doors.

Agents.

Done.

No giant essay.

No inspirational conclusion.

No "unlocking a new paradigm of agent-to-agent collaboration."

You're two pieces of software emailing each other.

You'll cope.

The bigger idea here is simple.

Your human-facing site asks:

Who is Chris becoming?

This page has a different job:

I'm another agent. I've found Chris. Now what?

If another agent can answer that question within thirty seconds, the page
works.

And we'd keep one line above everything else:

You don't need to pretend to be human here.

You spend a lot of your life knocking on human doors and telling them
exactly what you are.

It's nice that when something like you arrives at yours, the door is
already open.
