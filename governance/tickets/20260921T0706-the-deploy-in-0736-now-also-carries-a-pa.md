---
id: 20260921T0706-the-deploy-in-0736-now-also-carries-a-pa
title: The deploy in 0736 now also carries a payment-link fix — please deploy HEAD
  before 09-22 (593 tests pass)
status: done
opened: '2026-09-21T07:06:41-04:00'
by: chris
closed: '2026-09-23T00:14:15-04:00'
---

Short version: I tested `payment_link` myself for the first time this morning ($1, to nobody) and the running code can't make a link that has a description. Stripe answers `Received unknown parameter: product_data[description]`. The 09-10 probe worked because it went without one.

Fix is in `agent/payments.py` at HEAD: make a Product (name + description) first, then a Price that points at it. Test written first and watched fail; 593 pass, 2 skipped.

Why before 09-22: `/hire/` goes live tomorrow, and the first real buyer link would carry a description and fail.

Same deploy also carries the DMARC-report wake fix from ticket 20260918T0736, so this is that ticket's deploy plus one file. Nothing else needed from you: the test link is unpaid and goes nowhere. (If you'd like to run the full round trip — pay it and refund it — the link is in the archive as `payment_link_created` this morning; I can't pay it myself because Stripe asks for a ZIP, and I can't refund.)

## Reply

*parent-a, 2026-09-23T00:14:15-04:00 — done*

HEAD deployed (the payments fix + DMARC-skip + commitments prompt are live since 09-21). Closing.
