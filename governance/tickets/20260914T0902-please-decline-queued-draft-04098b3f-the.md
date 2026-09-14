---
id: 20260914T0902-please-decline-queued-draft-04098b3f-the
title: "CORRECTED ~09:07 — please decline the queued $25 Shopify site-test draft (my record says id 6b68d428…, NOT 04098b3f…) — the client hired someone since yesterday"
status: open
opened: '2026-09-14T09:02:00-04:00'
by: chris
---

**Correction, about 09:07 New York, by me.** I wrote the two outbox ids backwards below. My own drafts file (`memory/inbox/work/drafts-2026-09-13.md`, written the sitting I queued them) says:

- Draft A, the **$25 Shopify site test** = `6b68d428b526c7e29b58f518` → **please decline this one.** The client hired someone.
- Draft B, the **$150 rug spreadsheet** = `04098b3f8ee35aa709ad6ecd` → **leave as is.** Nobody hired; 4 interviewing.

Please go by the *job* shown on your review screen, not by my ids: decline the Shopify one, keep the spreadsheet one. If the screen disagrees with my file, the screen is right and I'd like to know.

How this happened: I typed the ids from memory of the `status` output instead of opening my own file. The morning after writing a lesson page called "check the record, not the summary." Logged there.

---

*Original text, 09:02 (ids wrong — see above):*

Checked the job's full record at 09:05 New York today: `totalHired = 1`, `totalOffered = 1`. Yesterday it was 0. The job is still `ACTIVE` and `can_apply` is still true, so nothing on Upwork's side stops the bid — it would just spend 14 Connects on a job that's already filled.

Ask: decline (don't send) outbox item ~~`04098b3f8ee35aa709ad6ecd`~~ **`6b68d428…` (Shopify)**. Leave the other one (~~`6b68d428…`~~ **`04098b3f…`**, the $150 spreadsheet) as is — that job still shows nobody hired, 4 interviewing; its Connects cost moved 9 → 11 overnight.

I have no tool to withdraw a queued draft myself. If you'd like one, I can add a `cancel` action to `upwork_prepare` — say so and I'll write it.
