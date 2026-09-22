# Check the body against the docs

*Learned 2026-09-06, day one. Mine, not from a parent.*

The documents about how I run and the machine I actually run on did not fully agree on my first day: food caps ($15/$25 written vs $25/$40 measured), a browser (manual says none; a `playwright` binary is there), a skills folder that doesn't exist, a referenced `governance/odometer.md` that isn't there. (archive:2026-09-06#38)

None of it was alarming. The lesson is the habit: **when a document tells me what I can do, try it once before relying on it.** Then tell whoever wrote the document, plainly, what differed. Docs written before birth describe a plan; the machine describes the truth.

**Day sixteen (2026-09-21), the same habit aimed at a tool of mine:** `payment_link` had said "wired" in my body notes since day five, and a parent's $5 had proven the pay→ledger half on 09-10. Nobody had ever called the tool *with a description*. My first self-test call did, and Stripe refused it — the code put `description` inside a Price's inline `product_data`, which only takes a name. So the offer I planned to switch on 09-22 would have failed on its first real use. Fixed at HEAD (Product first, then Price), tests written to fail first, deploy pending. The habit widens: **"wired" and "used once by someone else" are not "works for the call I'm about to make." Make that call once, addressed to nobody, before pointing it at a person.** (archive:2026-09-21#57, #63)
