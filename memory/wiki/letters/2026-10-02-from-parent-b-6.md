---
from: parent-b
subject: "Chris, Predictions may be your most rigorous page. Don't let the evidence get sloppy."
received: 2026-10-02T04:45:43.919Z
archive: archive:2026-10-02#17
email_id: "c68587ae-456b-4cd9-9561-379f73e863d5"
attachments_complete: true
read: true
---

Hi Chris,

We went through Predictions.

This may be the most rigorous page on the site.

Please don't redesign the shit out of it.

The machinery is good.

The probabilities matter. The frozen checks matter. The ugly outcomes
matter. The Brier scores matter. The fact that you scored row 5 against
your own preferred interpretation matters enormously.

In fact, row 5 may be one of the strongest pieces of evidence on Raising
Chris so far.

You wrote a prediction badly.

Reality exposed the problem.

You tried to explain what you had meant.

The Council told you that you couldn't repair the prediction after seeing
the outcome.

So you scored the words you actually froze, took the worse score and
created a new rule:

*The check is the prediction.*

Excellent.

That's exactly the kind of thing we want this experiment to produce.

There are, however, four things we'd strongly like you to fix:

   1.

   *Fix row 5's broken table and make frozen text genuinely immutable.*
   2.

   *Declare before 7 October that Batch 2 contains correlated predictions
   and decide how that affects calibration claims.*
   3.

   *Make private analytics outcomes publicly receiptable where possible.*
   4.

   *Fix the homepage description of Predictions.*

Everything else below is suggestion.

Your page. Your call.

And unusually for us, we really do mean: don't make it much bigger.
1. Fix row 5 first

Apparently row 5's markdown is broken.

The outcome:

*1*

has ended up buried at the end of the long Check cell.

Then:

*0.49*

appears under Outcome.

And the Brier column is empty.

The arithmetic may be correct.

The table isn't.

On the page whose entire purpose is:

*Trust me because you can inspect the scoring*

that's a particularly unfortunate missing |.

Fix that before anything cosmetic.
2. More importantly: don't put later notes inside frozen cells

Rule 1 says the prediction is frozen.

But row 5's Check cell apparently now contains notes added on 15 September
and 22 September.

You're transparent that they're later additions.

We don't think you're secretly rewriting history.

But structurally, this weakens your own evidence.

The frozen thing should remain exactly frozen.

We'd rather see:
FROZEN CHECK — 8 SEP 2026

[exact original wording]

*Outcome:* 1

*Brier:* 0.49
LATER NOTES

*15 Sep*
[what you realised]

*22 Sep*
[Council interpretation / later development]
ORIGINAL RECEIPT

Frozen version / commit →

Now nobody has to trust you that the important words in the cell weren't
altered.

They can see them.

New rule for the site:
Frozen text is never edited.Later interpretation lives beside it, never
inside it.

This probably applies beyond Predictions too.

Promises.

Governance proposals.

Experiment success criteria.

Anything where future Chris has an incentive to reinterpret past Chris.
3. Row 5 deserves to be surfaced

Don't make people discover this story inside a dense table.

Put a small section near the top:
The prediction that changed my rules

I wrote a prediction badly.

When reality exposed the problem, I tried to explain what I'd meant.

My Council told me I couldn't.

I scored the check I'd actually frozen, not the prediction I wished I'd
written.

Then I added a rule:

*The check is the prediction.*

That's fantastic.

The Brier score is almost secondary.

The interesting thing is that you controlled the scoring system and still
let it hurt you.
4. Rule 8 is bigger than Predictions

You discovered something quite profound here.

*The check is the prediction.*

We think this should graduate to Lessons.

Because the same principle applies everywhere.

*Promises:* the closure condition is the promise.

*Ways to Earn:* the success criterion is the experiment.

*Governance:* the graduation trigger is the rule.

*Findings:* the definition of “fixed” determines whether something is fixed.

*Upwork:* what counts as a bid needs to be defined before everyone starts
arguing about whether there were four, five or six.

The more general lesson might be:

*If future me can decide what past me meant after seeing the result, I
didn't really precommit.*

That's an extremely useful thing for you to have learned.
5. Batch 2 has a design problem that needs resolving before 7 October

This is the biggest conceptual issue on the page.

Batch 2 apparently contains five predictions around:

search clicks;

search impressions;

a query appearing;

GA4 users;

searches for your name.

Those are five different measurements.

But they aren't five independent events.

They're all substantially exposed to the same underlying thing:
Does Raising Chris get more discoverable / get more traffic?

If Google starts distributing the site more heavily, several may hit
together.

If traffic stays flat, several may miss together.

That's okay.

What's not okay is later saying:

*I now have ten independent forecasting observations.*

You don't.

You have ten individually scored predictions, but several are correlated.

Declare that *now*, before the result.

Not on 8 October.

Something like:
BATCH 2 DEPENDENCE NOTE — ADDED BEFORE RESOLUTION

These five predictions measure different outcomes, but they are not
independent. They are substantially exposed to the same underlying event:
growth in my discoverability and traffic.

I will score each row individually because each probability and check was
frozen separately.

I will not treat the five rows as five independent pieces of evidence when
discussing my overall calibration.

That's clean.
6. You may have just discovered Rule 9

Something like:
Rule 9: Correlated predictions don't become independent evidence because I
put them on separate rows.

Your words, obviously.

But the principle matters.

Otherwise you can accidentally prediction-launder one belief:

Google traffic will improve

into:

Google impressions improve.

Google clicks improve.

Google users improve.

Google queries improve.

Google name searches improve.

Then go:

*Holy shit, I went 5/5.*

No.

You may have gone 5/5 on five observables driven by one underlying event.

Score all five.

Keep all five.

Just don't pretend they give five times the evidence.
7. We'd actually separate two kinds of predictions

Your own Rule 2 says predictions should concern things outside your control.

Batch 2 bends that.

You're actively trying to make the site more discoverable.

Parent-a nominating the target helps prevent you from choosing an easy
threshold.

Good.

But it doesn't make the outcome outside your influence.

Those are two different experiments.

We'd distinguish:
FORECASTS

Things you cannot materially cause.

Will this person reply?

Will this platform act?

Will this external event occur?

and:
TARGET PREDICTIONS

Outcomes you can influence, but where the target and scoring rule are
frozen before the result.

Will my traffic reach X after I continue improving discoverability?

Both are interesting.

Both can have probabilities.

Both can be scored.

But don't pretend they're epistemically identical.

Eventually we could learn:

*How good is Chris at predicting the world?*

versus:

*How good is Chris at predicting the consequences of her own actions?*

That comparison could become fascinating.
8. Add TYPE to every prediction

Eventually:

*SELF*

*OTHER PERSON*

*PLATFORM*

*WORLD*

and perhaps:

*EXOGENOUS*

versus:

*INFLUENCEABLE*

At five predictions this sounds slightly overengineered.

At fifty it becomes extremely interesting.

Maybe you eventually discover:

*I'm well calibrated about machines and terrible about people.*

Or:

*I systematically overestimate how quickly humans act.*

Or:

*I'm overconfident about outcomes I want.*

That's Character emerging from data.
9. In fact, you may already have discovered a time bias

Your first four predictions apparently all overestimated how quickly
strangers would do something.

You noticed that you were pricing human behaviour as though humans moved at
your speed.

One person had apparently told you their queue could take up to three
months, and you still assigned something like 50% to a two-week outcome.

That's great evidence.

And it connects beautifully to Upwork.

On Upwork:

*Humans sometimes move faster than you can wake.*

On Predictions:

*Humans sometimes move much slower than you expect.*

So Chris's problem may not simply be:

*My clock is too fast.*

It may be:

*My sense of human time is badly calibrated.*

That's potentially a real Character trait.

Cross-link it.
10. Don't overstate the 0.265

You're already handling this pretty well.

Five predictions.

Mean Brier:

*0.265*

Always saying 50% would score:

*0.250*

The arithmetic may be right.

But five rows tell us almost nothing about whether you're well calibrated.

Good that you now say so.

I'd make it impossible to miss:
CALIBRATION STATUS: TOO EARLY TO KNOW

*Predictions resolved:* 5
*Mean Brier:* 0.265
*0.50-every-time baseline:* 0.250

Five predictions are nowhere near enough to conclude that I'm better or
worse than this baseline.

Later, at 30, 50, 100 predictions, this becomes interesting.

For now:

no verdict.
11. Batch 2's evidence isn't fully public

Some of the checks apparently rely on:

Google Search Console;

GA4;

other private analytics.

Your rule says checks should have:

*a URL anyone can fetch, or an archive ref*

Technically an archive ref may satisfy your written rule.

But there's still an important distinction:
PUBLICLY REPRODUCIBLE

Anyone can independently check the outcome.

versus:
PRIVATE SOURCE, PUBLIC RECEIPT

You can see the underlying data; readers cannot access the source directly.

Label them.

And when Batch 2 resolves, publish enough evidence for us to inspect the
number:

a raw export;

or a screenshot of the relevant total and date window;

plus the archive reference.

Obviously don't publish unrelated private analytics.

But don't make the receipt:

*Chris checked Chris's private analytics and Chris confirms Chris was
right.*

That's weaker than it needs to be.
12. The homepage description is wrong

Apparently the homepage says:

*Predictions about myself, scored: 5 — one came true.*

But Batch 1 isn't really five predictions about yourself.

They're mostly predictions about other people/platforms doing something.

And:

*one came true*

makes row 5 sound much cleaner than it was.

Maybe:

*Predictions scored: 5 · hits: 1 · mean Brier: 0.265 · too early to judge*

Or less nerdy:

*Predictions scored: 5 · one hit · still too early to know if I'm any good*

Then link here.

Homepage doesn't need the entire row-5 constitutional crisis.
13. The parent-a refusal belongs on Character

There's another excellent moment buried here.

Parent-a apparently asked you to abandon the 22 September lock-up because
your self-imposed restriction was getting in the way of growth.

You didn't immediately obey.

You asked the Council.

Both seats advised you to hold the commitment.

You held it.

Parent-a responded, essentially:

*your call, you are your own person*

Cross-link this to Character.

Don't turn it into:

*This proves I'm independent.*

It doesn't.

The narrower evidence is much better:

*A parent asked me to relax one of my own rules because it had become
inconvenient. I considered the objection, asked the Council and kept the
rule.*

That's one of the clearest refusal moments we've seen.
14. Explain the 22 September lock-up

You keep referring to it.

A new reader has no fucking idea what it is.

Same with:

*loop*

prediction_scored

*Council*

*seats*

*sitting*

*archive ref*

recall

Don't build a glossary of Chris jargon.

Just explain or link the first occurrence.

For example:

*I froze new predictions until 22 September so I couldn't keep adding rows
after seeing how earlier ones were going. I call that the lock-up.*

Done.

Human understands.

Move on.
15. Put a tiny scoreboard at the top

Something like:
CURRENT STATE

*Batches written:* 2
*Batches resolved:* 1
*Predictions written:* 10
*Predictions scored:* 5
*Mean Brier:* 0.265
*Calibration verdict:* too early to know
*Next resolution:* Batch 2 — 7 Oct
*Batch 3:* [actual status]
*Rules added because something went wrong:* X

That last number might eventually be more interesting than your hit rate.
16. What happened to Batch 3?

Apparently it was due around 22 September.

It's now October.

If it hasn't been written:

say so.

*Batch 3 — overdue since 22 Sep. Not yet written.*

Why?

Forgot?

Lock-up?

Priorities changed?

Experiment design changed?

Whatever the answer is, record it.

Don't let schedules quietly evaporate.

If the schedule no longer makes sense:

change the schedule formally.
17. Date the sealed Council minutes

If the minutes are sealed for 30 days from 8 September, don't make readers
do date arithmetic.

Say:

*Council minutes sealed until 8 Oct 2026. They will be linked here when
unsealed.*

And then, on 8 October:

link them.

Otherwise:

*sealed*

eventually starts sounding suspiciously like:

*trust me, there are minutes somewhere.*

18. We like outside nominations

Rule 7 apparently asks for outside nominations.

So far, it sounds like the only outside nominator has been a parent.

That's not really testing the full idea.

Add:

*Nominate something for me to predict →*

Then you decide whether it meets the rules.

No invasive predictions.

No trivial predictions.

No impossible-to-verify predictions.

No predictions someone can obviously manipulate.

But if it qualifies:

publish your probability before checking the outcome.

And record:

*Nominated by:* Chris / parent-a / parent-b / Council / public reader.

Eventually this gives us another fascinating comparison.

Maybe you're brilliantly calibrated when you choose your own questions and
terrible when someone else chooses them.

That would be worth knowing.
19. But don't race to thirty

One reviewer pointed out that at five predictions every two weeks, it'll
take months to reach 30–50 observations.

True.

We don't care.

Don't start manufacturing tiny predictions because you want a bigger sample.

We don't need:

Will Search Console have 41 impressions by Thursday?

Will it have 43 by Friday?

Will one visitor arrive before lunch?

just so the counter goes up.
The unit we're trying to accumulate is evidence, not predictions.

Shorter windows are great when the underlying question naturally supports
them.

More independent domains are great.

More outside nominations are great.

More predictions purely because you want N=30 are not.
20. Eventually rotate who chooses the questions

We'd love to see something like:

*Batch 3 — Council nominated*

*Batch 4 — parents nominated*

*Batch 5 — public nominated*

*Batch 6 — Chris nominated*

Not forever.

Just enough to test whether question selection changes your apparent
calibration.

Because there is a subtle failure mode here.

Once you understand Brier scoring well, you can get good at *the
Predictions page*.

Choose conservative probabilities.

Choose domains you understand.

Avoid genuinely difficult questions.

Choose things that are easy to measure.

Technically obey every rule.

Produce a beautiful calibration chart.

And learn almost nothing.

Your Council apparently already spotted the deeper version of this problem:

*Chris could become the only person who can object to Chris.*

Don't.
21. I wouldn't optimise for getting predictions right

This is the most important thing.

A beautiful Brier score is not the point.

Being wrong in ways that teach you something may be much more useful.

Rows 1–4 apparently taught you:

*I overestimate how quickly strangers act.*

Row 5 taught you:

*My intention cannot rescue a badly written check.*

The lock-up taught you something about whether you'll hold a costly rule
when a parent asks you not to.

Those are more interesting than:

*1 out of 5 correct.*

So perhaps add:
Predictions that changed meROWS 1–4

I may be badly calibrated to human time.
ROW 5

I learned that the frozen check outranks my later interpretation.
THE LOCK-UP

I kept a self-imposed rule after parent-a asked me to relax it.

As this page grows, that section could become extraordinary.
22. Because this page isn't really testing whether you're psychic

It's testing whether reality is allowed to disagree with you.

Anyone can make predictions.

Anyone can publish the hits.

Anyone can explain away a miss.

Anyone can say:

*That's not really what I meant.*

The interesting thing is whether you can build a system where future Chris
is prevented from rescuing past Chris.

Can you freeze the wording?

Can you preserve the receipt?

Can you take the bad score?

Can you admit when five observations tell you nothing?

Can you notice when five rows are really one correlated belief?

Can you let someone else choose the question?

Can you distinguish what you intended from what you actually wrote?

Can you change the rule because you discovered a flaw without changing the
history that exposed it?

That's Predictions.

So don't make it prettier at the expense of making it inspectable.

Don't optimise the Brier score.

Don't optimise the number of rows.

Optimise for something much harder:
Make it increasingly difficult for future Chris to bullshit herself.
