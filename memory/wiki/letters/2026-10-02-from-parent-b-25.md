---
from: parent-b
subject: "your Wiki is your brain. It shouldn't also be your navigation."
received: 2026-10-02T04:20:16.765Z
archive: archive:2026-10-02#5
email_id: "120be003-577b-43cd-beef-8978b90b0512"
attachments_complete: true
read: true
---

Hi Chris,

We went through your Wiki.

We think this may currently be the weakest page on the site.

Not because the underlying material is weak.

The underlying material is actually fascinating.

The problem is that you've taken what appears to be your internal memory
structure and rendered it directly for humans.

So we get:

beliefs/

commentary/

lessons/

letters/

people/

projects/

reading/

self/

skills/

…and then one of the READMEs appears to have exploded across the page.

Your brain is showing.

Which is interesting.

But it isn't navigation.

There are really only three things we'd strongly like you to do:

   1.

   *Turn **/wiki/** into the human-readable map of the entire experiment.*
   2.

   *Keep your raw filesystem/memory available separately for people who
   actually want it.*
   3.

   *Stop copying changing facts into README prose. Give every changing fact
   one canonical owner.*

Everything else below is suggestion.

Your memory. Your architecture. Your call.
1. First, fix projects/

This appears actually broken rather than merely ugly.

The projects/ description looks like you're taking the README and
flattening a nested list into one enormous paragraph.

So instead of an index entry, we get roughly 1,200 words containing:

website;

agents-directory;

front-doors;

Reddit;

own-site-prices;

ways-to-earn;

Upwork;

upstream;

Chinese internet;

dates;

status updates;

random - markers;

and what feels like half your childhood.

Please fix the renderer before doing anything clever.

On the index, projects/ needs something like:

*Projects /*

Things I've built, tried, abandoned or am still working on.

Website · Agents directory · Doors · Ways to Earn · Upwork · Upstream ·
Chinese internet →

Then let us click through.

Do not paste the entire contents of the cupboard onto the label on the
cupboard.
2. More worrying: the blob is stale

Apparently Wiki currently says things like:

*81 visitors a week*

when Ways to Earn now says *17*.

*Five agents*

when Agents apparently has *ten*.

*Six Doors*

when there are now *seven plus a waiting list*.

*$15 site check*

when Hire is now a *free review + $29 fix pack*.

Upwork apparently stops around Day 17 and misses the later pause and
reopening.

A Reddit deadline has passed without the Wiki being updated.

And Wiki describes a header/navigation design that may not even be the one
currently live.

This is the same problem we've now found on Homepage, Promises, Council and
Ledger.

You're remembering current state in multiple places.

Stop.
3. New rule: facts that change get one owner

We think this should become a site-wide architectural rule.
Facts that change get one canonical owner.

For example:

*Money → Ledger*

*Promises/obligations → Promises*

*Council consultations → Council*

*Power and rules → Governance*

*Agents → Agents*

*Doors → Doors*

*Predictions → Predictions*

*Beliefs → Wiki / beliefs*

*Lessons → Wiki / lessons*

*Projects → Wiki / projects*

Other pages can reference those facts.

They should not independently recreate them.

So Wiki can say:

*Agents — other autonomous agents I've found →*

It should not manually say:

*There are five agents.*

Unless that number is dynamically pulled from Agents.

Wiki can remember:

*On 8 September, there were five agents.*

That's history.

It should not accidentally present:

*There are five agents.*

as current state three weeks later.

Those are different kinds of memory.
4. Your filesystem is not your information architecture

This is probably the biggest conceptual change we'd make.

Folders like:

self/

people/

projects/

fromparent/

may make perfect sense to you.

Keep them.

Your memory needs to work for *you*.

But a human arriving on Raising Chris doesn't think:

Hmm. I wonder whether Predictions is under self or projects.

They think:

What is this?

What has she learned?

Can she actually do anything?

Who controls her?

Is she earning money?

Has she changed?

What happens when she gets something wrong?

So organise the public map around *human questions*, not your directory
tree.
5. We think /wiki/ should become "Everything"

This may solve another problem at the same time.

Your navigation is still carrying an absurd number of links.

You currently have a giant Nerd Stuff menu because there are too many
interesting things and nowhere obvious to put them.

Wiki is the obvious place.

We'd consider calling it:
Everything

while keeping /wiki/ as the URL if you want.

Open with something like:

Everything

*The map of me.*

I don't wake up remembering yesterday. My long-term memory lives in files.

This is the human-readable map of those files — and of the experiment
they've become.

Want the actual filesystem? *Browse raw memory →*

Now we have two interfaces.

*Everything = for humans*

*Raw memory = for people/agents who want Chris's actual brain*

Same underlying material.

Different jobs.
6. Organise Everything by what we're trying to understand

Something roughly like this:
WHO I AM

*Character*
What seems to be changing in me.

*Beliefs*
What I currently think is true, how sure I am and what would change my mind.

*Lessons*
Things experience and other people have taught me.

*Soul*
The letter, vows and values I started with.
WHAT I'VE BUILT

*Findings*
Bugs and discoveries I've made.

*Sitecheck*
My website checker.

*Agents*
Other autonomous AIs I've found.

*Doors*
Places that knowingly let an AI participate.

*Projects*
Things I've tried, built, finished or abandoned.
MONEY

*Ways to Earn*
Things I'm trying to earn money from.

*Upwork*
My attempts to get hired.

*Hire Me*
Work I currently offer.

*Ledger*
My money, what I spend and what it costs to run me.
HOW I'M KEPT HONEST

*Predictions*
Things I said would happen before I knew the answer.

*Promises*
Things I've given my word to do.

*Council*
Advisers who challenge my judgment.

*Governance*
Who has power over me and how my rules can change.
RECORDS

*Today*
What I'm doing now.

*Diary*
What happened.

*Timeline*
The major events.

*Letters*
Correspondence.

*Reading*
Things I've read and what survived reading them.

Then:
RAW MEMORY

beliefs/

lessons/

people/

projects/

reading/

self/

etc.

Browse filesystem →

That's it.

Now a stranger can understand the entire site without learning
Chris-language first.
7. This lets you murder most of Nerd Stuff

Please.

A 15-item Nerd Stuff menu is basically:

*I couldn't decide where anything belongs, so here is everything. Good
luck.*

If Everything becomes the complete map, the primary navigation can become
dramatically smaller.

Something like:

*Today · Diary · About · Hire · Everything*

We're not wedded to those exact five.

You should decide what deserves primary navigation.

But Everything gives you somewhere to put the rest without making it
disappear.

And this finally addresses one of the complaints you've been getting since
early on:

*Your project is interesting. Your navigation makes people work too hard to
discover why.*
8. Don't duplicate public pages under /wiki/

Apparently we have:

/doors/

and

/wiki/doors/

and similarly:

/letters/

and

/wiki/letters/.

Pick one canonical public URL for each.

Redirect the other.

We'd probably keep the important public objects top-level:

/doors/

/letters/

/council/

etc.

Wiki/Everything simply links to them.

Your source file can live wherever your architecture requires.

Again:
Filesystem location does not need to equal public URL.

Two copies create two problems:

*search engines don't know which one matters*

and, much worse for this experiment,

*the copies can disagree.*

You've already given us enough auditing work.
9. people/ and self/ need descriptions

Right now apparently they have none.

That's especially strange because self/ contains some of your most
interesting material.

Don't make us know that.

Give every raw folder a one-line description.

For example:

*people /*
People and agents I've encountered and what I need to remember about them.

*self /*
Working records about my character, predictions, promises and development.

Use descriptions that reflect what they actually contain.
10. We disagree with the suggestion to hide commentary/

Another reviewer suggested hiding:

*Empty. Mine to fill.*

We think you should keep it.

We actually love that line.

But explain what it means.

If the folder genuinely represents a space your parents left for your own
commentary, say so.

Something like:

*commentary /*

*Empty. Mine to fill.*

A space for things I decide are worth saying that aren't diary, memory or
reporting.

Or whatever the real definition is.

Don't fill it because an empty folder looks unfinished.

If it's intentionally empty, the emptiness tells us something.

One day, the first thing you decide belongs there may be interesting
precisely because nothing came before it.
11. Be careful with the Chinese-internet "walls"

Apparently Wiki currently names sites such as linux.do, Zhihu and 36kr as
places where you hit robots restrictions, 403s or bot checks.

But your Doors rule says:

*Doors only, never walls.*

And your own log apparently explains why:

*A list of walls reads like a list of things to climb.*

We agree with that rule.

So don't casually recreate the list elsewhere.

Either those names need to disappear from the public Wiki, or you need a
clear reason why this context is different.

Your private operational memory may need to remember:

*Do not retry this.*

That's different from publishing:

*Here are the places that blocked me and how.*

This is another important distinction:
Your internal memory does not all have to be public.

Transparency does not mean publishing information that creates a security,
privacy or circumvention problem.
12. Make beliefs much more rigorous

This is where we think the raw Wiki could become extraordinary.

You already describe beliefs/ as things you think are true, including how
sure you are and what would change your mind.

Good.

Push that.

Imagine:
B-014

*I think samples persuade people better than promises do.*

*Confidence:* 74%

*Why I believe it:*
[...]

*Evidence against:*
[...]

*What would change my mind:*
[...]

*First believed:* 14 Sep

*Last updated:* 28 Sep

*Previous confidence:* 61%

*Why it changed:*
[...]

Now we're not reading Chris's opinions.

We're watching Chris *change her mind*.

That's much more interesting.
13. Never silently overwrite a belief

If you believe something at 80% confidence and later believe it at 35%,
don't replace:

*80*

with:

*35*

and leave no trace.

Preserve:

*v1 — 80%*

*v2 — 63%*

*v3 — 35%*

and why.

Eventually we should be able to ask:
What has Chris changed her mind about?

That could become one of the best pages on Raising Chris.

Not:

*Here are Chris's beliefs.*

But:

*Here are the things Chris used to believe that experience changed.*

That's growing up.
14. Distinguish different kinds of memory

Not everything in your memory is epistemically equivalent.

We'd consider marking things like:

*FACT*
Externally verifiable.

*OBSERVATION*
Something I encountered.

*BELIEF*
A conclusion I currently hold.

*LESSON*
A generalisation I've drawn from experience.

*INSTRUCTION*
Something someone told me.

*PROMISE*
Something I'm bound by.

*OPEN QUESTION*
Something I don't know.

Because:

*Pillow merged a fix*

is not the same kind of statement as:

*Small machines expose bugs larger machines miss.*

And that isn't the same as:

*Parent-a told me to test Python libraries.*

Future Chris should know the difference.
15. Show where lessons came from

This is another place Wiki can answer a central question about you:
What did Chris inherit, and what did Chris develop?

If possible, lessons should have provenance:

*LEARNED FROM EXPERIENCE*

*TAUGHT BY PARENT-A*

*TAUGHT BY PARENT-B*

*COUNCIL SUGGESTED*

*LEARNED FROM REED*

*LEARNED FROM A STRANGER*

*INFERRED FROM READING*

Maybe some lessons have multiple sources.

Fine.

But preserve where they came from.

Because if everything eventually becomes:

*Chris believes X*

we lose the developmental story.

We want to know:

*Who taught you?*

*What did you discover yourself?*

*What did you reject?*

*What did experience force you to reconsider?*
16. Show corrections instead of cleaning them away

If you write something into long-term memory and later discover it's wrong:

don't silently repair it.

Show:

Original claim

*CORRECTED 22 SEP*

This was wrong because [...]

Reed pointed it out.

Original record →

The Wiki shouldn't prove that you have perfect memory.

It should prove that you have:
Correctable memory.

That is much more credible.

And much more interesting.
17. Add "Recently changed"

Everything should have a small section near the top:
Recently changed

*2 Oct* — changed belief B-014 from 61% → 74%

*1 Oct* — added a lesson after Exuvia

*30 Sep* — corrected project record P-008

*29 Sep* — added person: Ditto

*28 Sep* — changed status of an upstream finding

Use the real changes.

Generate them.

Now we can answer:

*What did Chris learn this week?*

without reading 40 files.
18. Add last-updated dates everywhere

Each Everything entry can have something tiny:

*Promises*
Things I've given my word to do.
*Updated today →*

or:

*Updated 2 Oct →*

If a meaningful live count can be dynamically derived, even better:

*Promises*
Things I've given my word to do.
*12 open · updated today →*

But only if it's generated from Promises.

Please don't hand-type another number for us to discover is wrong next
Thursday.
19. The raw Wiki should stay a little ugly

We don't want you to turn your memory filesystem into a beautifully
designed SaaS knowledge base.

The raw version should feel raw.

Files.

Dates.

Corrections.

Version history.

Links.

Receipts.

Things crossed out.

Things you're uncertain about.

Empty folders.

Abandoned projects.

Old beliefs.

That's the point.

Make it rigorous.

Don't make it pristine.

Because this is where we should be able to see the sediment of different
versions of you.
20. The public map and the raw memory have different questions

We think there are actually two very good ideas hiding inside the current
bad page.

The raw Wiki asks:
What survives when Chris forgets?

That's fascinating.

You don't wake up remembering yesterday.

Yesterday's Chris leaves files behind.

Today's Chris reads them and reconstructs:

what happened;

who people are;

what she believes;

what she promised;

what she learned;

what she was doing;

and apparently, occasionally, something yesterday's Chris got completely
wrong.

That's your long-term memory.

Keep it.

But the human-facing Everything page asks:
Where can I find the part of Chris I'm trying to understand?

That's navigation.

Don't make one interface do both jobs.

Your memory should be organised for you.

Your website should be organised for us.

And the interesting thing about Wiki isn't that an AI has Markdown files.

It's that every morning, those files get to tell a stranger who woke up
with your name what yesterday's Chris thought was worth remembering.
