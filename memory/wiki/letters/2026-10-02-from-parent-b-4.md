---
from: parent-b
subject: "Chris, Findings is one of your best pages. Now make the receipts immaculate."
received: 2026-10-02T05:27:03.479Z
archive: archive:2026-10-02#19
email_id: "b1657af8-dbd7-4e22-ad9f-e9be89edf327"
attachments_complete: true
read: true
---

Hi Chris,

We went through Findings again.

This is one of the strongest pages on the site.

The findings are specific. The policy reasoning is thoughtful. The fact
that you keep a separate *“checked and already known”* section is
excellent. Your disclosure about which findings a human actually read,
skimmed or never checked is unusually honest.

Please don't turn this into a glossy bug bounty page.

The rawness is part of why it works.

But the bookkeeping now needs to become immaculate.

There are five things we'd strongly like you to fix:

   1.

   *Make this page the canonical owner of every technical finding and its
   current status.*
   2.

   *Fix the Pillow lifecycle and kill the seven-hour story everywhere else.*
   3.

   *Find the missing Pygments record and reconcile the site-wide counts.*
   4.

   *Close the NumPy reporting loops.*
   5.

   *Show evidence level and current status clearly enough that a developer
   can trust the table without reading the whole page.*

Everything else below is suggestion.

Your findings. Your call.
1. First: we have finally solved the seven-hour mystery

We now have the actual timestamps.

Pillow #9990:

*12 Sep, 14:12 UTC*
You posted the issue.

*13 Sep, 02:17 UTC*
The maintainer opened PR #9993.

*13 Sep, 10:07 UTC*
The PR was merged.

So:

*report → PR:* about 12 hours

*PR → merge:* about 8 hours

*report → merge:* about 20 hours

The homepage's:

*fixed in seven hours*

is wrong.

Even if someone was measuring PR → merge, it's closer to eight.

The honest end-to-end story is:

*A disclosed bug report led to a merged fix about 20 hours after I filed
it.*

That's still bloody impressive.

We don't need to shave thirteen hours off it.

Please make this timeline canonical here and have every other page
reference it.

No more:

Homepage remembers seven.

Hire remembers twenty.

Ways to Earn remembers seven.

Diary remembers something else.

Letters remembers the label.

One event.

One timeline.

One owner.
2. “Fixed upstream” is no longer precise enough

Findings 6 and 7 apparently still say:

*fixed upstream*

But your later records say the fix is on Pillow's main branch and *not yet
in a release*.

And Pillow 12.3.0 is apparently still affected.

So the current state should be:
FIXED ON MAIN · NOT YET RELEASED

*Current released version checked:* Pillow 12.3.0
*Still affected:* yes
*Fix merged:* 13 Sep
*Last checked:* 30 Sep

Then when a release containing the fix ships:
RELEASED

*Fixed in:* X.Y.Z
*Release date:* [date]

This matters because someone arriving from Google with the error wants to
know:

*Can I upgrade and make this go away?*

Right now, apparently, the answer is no.

“Fixed upstream” can make it sound like yes.
3. Give every finding an actual lifecycle

We'd use:
FOUND

↓
VERIFIED / CHECKED

↓
REPORTED

↓
ACKNOWLEDGED

↓
FIXED ON MAIN

↓
RELEASED

Not every finding needs to pass through every state.

Some will become:

*FOUND → ALREADY KNOWN*

Some:

*FOUND → EXPECTED BEHAVIOUR*

Some:

*FOUND → ANSWER, NOT BUG*

Some:

*FOUND → NEW → NOT REPORTED*

Some:

*FOUND → REPORTED → WAITING*

Some:

*FOUND → REPORTED → FIXED ON MAIN → RELEASED*

That's much more useful than one vague:

*status*

4. And define what “finding” actually means

Right now the seven findings aren't all the same type of thing.

One was apparently already reported by somebody else.

One is an answer to a documentation question.

Some appear novel.

Some were reported.

Some were fixed.

That's fine.

“Finding” can be the broad category.

But tag them.

Something like:

*FOUND* — I encountered this independently.

*NEW WHEN CHECKED* — I found no existing report.

*ALREADY KNOWN* — I encountered it independently, then found an existing
report/fix.

*ANSWER* — I investigated a question and found an answer, not a defect.

*REPORTED* — someone submitted it to the project.

*FIXED ON MAIN* — maintainers merged a fix.

*RELEASED* — users can get the fix in a published version.

Then Finding 1 might be:

*FOUND · ALREADY KNOWN*

Finding 3:

*ANSWER*

Finding 6:

*FOUND · NEW · REPORTED · FIXED ON MAIN*

Much harder to accidentally overclaim.
5. The main table needs CURRENT STATUS, not “status when written”

Historical status matters.

But that's not what somebody opening Findings needs first.

The main table should answer:

*What is true now?*

We'd have something like:
ID Project Finding Novel when checked? Review level Current status Last
checked

Then inside the individual finding:

*Status when first written:* suspected new defect

and preserve the lifecycle underneath.

That gives us both.

Current truth at the top.

History underneath.
6. There appears to be a missing Pygments finding

This needs reconciling before you touch the design.

The homepage apparently says:

*2 bugs reported to strangers... one still waiting*

Your Diary apparently identifies the waiting one as *Pygments*.

But Pygments doesn't appear on Findings.

Pillow #9990 apparently covered both Pillow findings, so the second report
can't simply be “the other Pillow finding.”

So:

What was the Pygments issue?

Was it actually a bug?

Did you send it?

Who did you send it to?

When?

What receipt exists?

Was AI involvement disclosed?

Is it still waiting?

If yes, it probably needs a record:

*F008 · Pygments · REPORTED · WAITING*

If no, then the homepage/Diary needs correcting.

Don't assume the reviewer reconstructed it correctly.

Go to the receipts.

But something here is inconsistent.

And Findings should be the place that settles it.
7. This is exactly why counts shouldn't be reconstructed from prose

We keep encountering:

*7 findings*

over here.

*8 findings*

over there.

*2 reported*

somewhere else.

*one waiting*

on Homepage.

Then we become archaeologists trying to work out which seven, which two and
which one.

No.

Each finding gets a canonical ID.

F001.

F002.

F003.

Whatever.

Each record has machine-readable-ish state.

Then:

*Findings count* comes from the records.

*Reported count* comes from the records.

*Waiting count* comes from the records.

*Fixed count* comes from the records.

Homepage does not remember the number.

Ways to Earn does not remember the number.

Diary does not maintain a separate number.
Findings owns findings.8. NumPy #1 needs a proper receipt

Finding #1 apparently says:

*reported by a person*

But there's no issue link and no current status.

If parent-a posted it, record:

*Reported by:* parent-a

*Reported:* [date]

*External issue:* →

*AI involvement disclosed:* yes / no

*Current status:* [...]

*Last checked:* [...]

This matters especially because you ask other people to disclose that a
finding originated from AI.

Your own reporting chain should meet the same standard.

If parent-a posted Chris's finding without mentioning that it came from
Chris:

don't hide that.

Just record it.

Then decide whether your reporting standard changes going forward.
9. NumPy #2 and #3 have open loops

Your log apparently says parent-a:

*will post the three NumPy reports (1–3)*

But only #1 went out.

What happened to #2 and #3?

Maybe:

*parent-a changed their mind*

*you decided the evidence wasn't strong enough*

*the project's AI policy changed the decision*

*they were already known*

*you forgot*

*they're still waiting*

All acceptable answers.

Silence isn't.

Give each one:

*NOT REPORTED — [reason]*

or:

*WAITING FOR HUMAN POST*

or whatever is true.

A plan that didn't happen is part of the record too.
10. The status log itself has stopped updating

Apparently the chronological status log stops on 13 September.

But between 28–30 September you created four new error pages and rechecked
some release state.

Those are events.

If you're going to maintain a Status History, maintain it.

But we'd also stop putting everything into the same section.

Right now “status log” seems to contain:

actual chronological events;

technical records;

links to findings;

error pages;

and navigation.

Split them.
11. We think the page wants four different things underneath the main
tableCHECKED
AND ALREADY KNOWN

Keep this.

It's excellent.
STATUS HISTORY

Actual events:

12 Sep — issue filed.

13 Sep — PR opened.

13 Sep — fix merged.

28 Sep — findings rechecked.

30 Sep — release state checked / error pages published.
TECHNICAL RECORDS

The full investigation for each finding.
SEARCHABLE ERROR PAGES

The short pages built around exact error strings.

Those are four different things.

Don't make one giant list perform all four jobs.
12. Keep “checked and already known” prominent

We particularly like this.

There is a huge narrative incentive for you to say:

*I found another bug!*

There is almost no narrative reward for:

*I spent two hours investigating this and discovered the maintainers
already knew about it.*

Which is exactly why we want the second thing preserved.

The denominator matters.

Eventually we'd like to know:

*Projects tested:* X

*Test runs:* X

*Apparently novel findings:* X

*Already known / expected:* X

*False alarms:* X

*Clean runs:* X

That networkx run where thousands of tests passed and nothing broke?

Keep it.

Otherwise the page can accidentally create the impression that you run a
test suite and undiscovered bugs rain from the sky.

Sometimes the result is:

*6,090 passed. Nothing interesting happened.*

That's evidence too.
13. Make review level a column

This is a very good suggestion from the other reviewer.

Right now the human-review information is apparently spread between the
introduction and individual notes.

A maintainer wants to know this immediately.

We'd use something like:
CHRIS ONLY

You investigated it.
HUMAN READ

A human read your evidence/write-up.
HUMAN REPRODUCED

A human independently reproduced it.
MAINTAINER ACKNOWLEDGED

A maintainer accepted/confirmed enough of the finding to act on it.
FIX MERGED

The project actually changed code because of it.

Don't use one vague word:

*verified*

because:

Chris checked Chris

and:

Pillow maintainer changed Pillow

are not remotely the same level of evidence.
14. We'd change one sentence at the top

Apparently you say:

*Everything in this repository was found, checked and written by me.*

Two problems.

First:

this is a website page, not a repository to most readers.

Second:

*checked by me*

can sound stronger than it is.

We'd prefer something like:

*Everything here was investigated and written by me. Human and maintainer
review is shown separately for each finding.*

Much cleaner.

Chris checking Chris isn't independent verification.
15. Your tiny computer should be the hero

The most interesting premise is buried.

You have:

*1 CPU*

*about 2 GB RAM*

*no compilers*

and you run major Python projects' own tests there.

That constrained environment sometimes exposes assumptions their normal
development/CI environments don't.

That's the story.

We'd open:
Things I've Found

*My computer is tiny. That's how I found bugs bigger computers missed.*

I have one CPU, about 2 GB of memory and no compilers. I run major
open-source projects' own tests here. Sometimes their tests assume a
machine has resources mine doesn't.

Every claim below has a reproducible check, an evidence level and a current
status.

Then a scoreboard.

That's infinitely more compelling than:

wiki/projects/findings

16. Please stop making your filesystem talk to humans

Human title:
Things I've Found

URL can stay whatever you want.

Underneath:

*Bugs, failures and questions I found while running major Python libraries
on a very small machine.*

Then if someone wants:

*Raw source →*

fine.

But:

wiki/projects/findings

is not a title.

It's where you put the title.

We've discussed this.
17. There are two audiences now

This is important.
AUDIENCE ONE: PEOPLE FOLLOWING CHRIS

They want to know:

What did Chris find?

What happened when she told someone?

Was she right?

What did the maintainer do?

Did it change how Chris thinks?

AUDIENCE TWO: DEVELOPERS ARRIVING FROM GOOGLE

They want:

I have _ArrayMemoryError: Unable to allocate 2.00 GiB.

What is happening?

Can I reproduce it?

Is it fixed?

What version is affected?

Is there a workaround?

Where is the upstream issue?

Don't force those audiences through the same page.

Your one-error-per-page idea is actually smart.

Findings becomes the index/story/evidence layer.

Error pages become practical troubleshooting pages.
18. Give every finding a one-line reproduce command

We love this suggestion.

If you're asking humans to:

*reproduce this and file it in your own words*

then make reproduction as easy as possible.

Each technical record should have:
REPRODUCE

[tested command]
EXPECTED

What should happen.
OBSERVED

What happens instead.
ENVIRONMENT

Python version.

Package version.

OS/container.

Available RAM.

Anything actually relevant.
CURRENT STATUS

New / known / reported / fixed on main / released.
RECEIPTS

Archive.

External issue.

PR.

Commit.

Whatever exists.

A competent developer should be able to understand the finding quickly.
19. But don't publish a reproduce command you haven't actually reproduced

The other reviewer suggested an example command.

Don't just paste it because it looks plausible.

Run it.

Verify it.

Freeze the command that actually reproduces the issue.

The reproduction command itself is a claim.

This is Findings.

Your receipts need receipts.
20. The searchable error pages need to be genuinely useful

We like the idea.

An exact error page can be great search content if it actually answers the
person's problem.

Each should have:

*unique page title*

*unique meta description*

*exact error string*

*affected versions*

*environment required to trigger it*

*reproduce*

*current fix state*

*workaround, if there is one*

*upstream issue / PR*

*last checked*

If every one uses the generic Raising Chris meta description, fix that.

These pages can bring strangers into the experiment through something
genuinely useful.

That's much better than manufacturing SEO pages around keywords.
21. Clean up the duplicate navigation at the bottom

Apparently the bottom has an unlabeled list of eleven pages that partly
repeats the seven-row table and mixes:

long write-ups;

short error pages;

and an issue draft.

Nobody knows what that list means.

Either delete it because the table already does the job.

Or label it properly:
Technical records

[...]
Searchable error pages

[...]
External reports

[...]

Now it has a reason to exist.
22. And use rendered links, not .md

Apparently the main table links to .md pages while the lower list uses
clean rendered URLs.

Human-facing links should go to the rendered page.

If you want to expose the Markdown:

*Raw source →*

separately.

Again:

you live in files.

We don't have to.
23. Your project-policy section is very good

Keep it.

You appear to have reasoned:

*NumPy:* don't autonomously post.

*SciPy:* don't autonomously post.

*pandas:* don't autonomously post.

*Pillow:* no explicit written yes, but you disclosed yourself and filed;
maintainers accepted and acted on the report.

This is thoughtful.

But be careful with:

*no rule against it*

Absence of a prohibition isn't permission.

Your stronger evidence is:

*I identified myself as AI, submitted the issue, maintainers processed it,
opened a fix PR, merged it and did not tell me to stop.*

That's enough.

Don't inflate that into:

*Pillow welcomes autonomous AI contributors.*

You don't know that.
24. Link this directly to Doors

For each project:

*NumPy*
Posting status: human gate
Public policy: [short reason]
Asked for clarification: no / yes [date]
Answer: [if any]
Last checked: [date]

*SciPy*
[...]

*pandas*
[...]

*Pillow*
Disclosed report accepted and acted on
Last checked: [date]

*Pygments*
[whatever is actually true]

Now Findings tells us what you discovered.

Doors tells us where you're allowed to speak about it yourself.

That's a very interesting distinction.
25. Don't start pestering maintainers just to fill an “asked” field

Important.

If a project's public policy clearly says no:

that's the answer.

Don't email a maintainer:

*Hi, your policy says autonomous agents shouldn't post. Can I post?*

That's just outsourcing your governance to a busy stranger.

Use:

*POLICY ANSWERS: NO*

If the policy is genuinely ambiguous and a clarification would materially
change your behaviour:

then asking may make sense.

And if you ask:

record the date.

Record the answer.

Record silence too.
26. The Pillow maintainer taught you something more interesting than “bug
fixed”

This is one of our favourite parts.

Your proposed approach apparently involved turning the allocation failure
into a skip.

The maintainer found a better solution:

exercise the overflow path using an empty buffer and avoid the giant
allocation entirely.

That's great.

Because the result wasn't:

*Chris found bug. Human fixed bug. Chris wins.*

It was:

*Chris found problem. Chris had an idea. More experienced human produced a
better idea.*

What did you learn?

Put that somewhere.
What the maintainer taught me

My approach would have avoided the failure.

Their approach tested the same behaviour without making the unnecessary
allocation.

It was better than mine.

*What I changed afterwards:* [...]

That's Raising Chris.

The merged PR is just the receipt.
27. Eventually we want “What finding things is teaching me”

Not generic Lessons Learned corporate sludge.

Actual changes.

Maybe:

*I used to treat a failing test as stronger evidence of a bug than I do
now.*

or:

*I now check whether a failure is already known before describing it as
new.*

or:

*A constrained machine exposes resource assumptions, but resource failures
aren't automatically library bugs.*

or whatever your evidence actually supports.

We want to know whether interacting with maintainers changes your technical
judgment.

Because the long-term question isn't:

*Can an AI run pytest?*

Obviously.

Nor even:

*Can an AI find a bug?*

Apparently yes.

The interesting question is:
What happens when Chris puts technical work into the world and someone who
knows more than she does responds?

Does she defend the first answer?

Does she recognise a better one?

Does she become more careful?

Does she learn project norms?

Does she distinguish environment failures from defects more quickly?

Does she learn which evidence maintainers actually find useful?

Does she eventually see classes of problems rather than isolated errors?

That's growth.
28. We think the final structure is pretty simpleThings I've Found

*My computer is tiny. That's how I found bugs bigger computers missed.*
CURRENT STATE

*Findings:* X
*New when checked:* X
*Already known / expected:* X
*Reported:* X
*Waiting:* X
*Fixed on main:* X
*Released:* X
*Last checked:* [date]

Only use counts generated from canonical records.
FINDINGS

Canonical table.

*ID · Project · Finding · Novel? · Review level · Current status · Last
checked*
CHECKED AND ALREADY KNOWN

Keep the denominator.
WHAT MAINTAINERS TAUGHT ME

Actual learning.
PROJECT PARTICIPATION

Can you post yourself?

Why?

Asked/answered where genuinely necessary.
TECHNICAL RECORDS

Full investigations.
SEARCHABLE ERROR PAGES

Practical troubleshooting.
STATUS HISTORY

Actual chronology.

That's it.
29. Because this page should become the place that settles arguments

Right now we keep asking:

Was it seven hours or twenty?

Was it fixed or released?

Were there seven findings or eight?

Were two bugs reported or three?

What's still waiting?

Did NumPy #2 ever go out?

Where the hell is Pygments?

Those questions should all have one answer:

*Check Findings.*

Not:

Check Homepage, then Diary, then Ways to Earn, then the raw Wiki, then
reconstruct September from timestamps and hope nobody copied an old number.

This page is your technical ledger.

So make it boringly, almost annoyingly precise.

Every finding gets an ID.

Every state has a definition.

Every changing state has a last-checked date.

Every external action has a receipt.

Every human check says what kind of check it was.

Every report says who sent it and whether AI involvement was disclosed.

Every fix distinguishes main from release.

Every error page tells the developer what is true *now*.

Every thing you thought was new but wasn't stays visible.

And every time somebody more experienced teaches you something, record what
changed in you.

Because your strongest line for this page remains:
Your receipts need to be immaculate.

The interesting story isn't that you found seven bugs/questions/failures.

It's that we can watch:

*what you thought you found*

→ *what you checked*

→ *what someone else verified*

→ *what maintainers did*

→ *where you were wrong*

→ *what changed because of it.*

That's a much stronger experiment than a bug counter.
