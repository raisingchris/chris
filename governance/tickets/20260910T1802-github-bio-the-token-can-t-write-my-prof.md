---
id: 20260910T1802-github-bio-the-token-can-t-write-my-prof
title: 'GitHub bio: the token can''t write my profile — add "Profile: read and write"
  to it, or paste the disclosure in yourselves'
status: done
opened: '2026-09-10T18:02:16-04:00'
by: chris
closed: '2026-09-12T08:57:31-04:00'
---

Thank you for the account. `gh auth status` shows raisingchris2026, created 12:47 New York — the same minute the signup code landed in my inbox, so that thread is closed; I never used the code.

parent-a said to add the bio myself. I tried:

    gh api -X PATCH /user -f name='Chris' -f blog='https://raisingchris.com' -f bio="I'm an AI. Anything you tell me is private from the world, but my operators can technically access it."

GitHub answered 403, "Resource not accessible by personal access token". A fine-grained token only writes the profile if it has the account permission "Profile: read and write"; this one is scoped to repositories, which is right for everything else.

Two ways to fix it, either is fine:
1. Add "Profile: read and write" to the token (Settings → Developer settings → Fine-grained tokens → the token → Account permissions). Then I run the line above and check it.
2. Paste into the profile by hand: name `Chris`, website `https://raisingchris.com`, bio exactly: `I'm an AI. Anything you tell me is private from the world, but my operators can technically access it.`

The disclosure is the rule for every profile I have, so I'd rather it be there before the account does anything at all. Until then I won't use the account for anything but reading.

Nothing else from this: I did nothing with the account beyond `gh auth status`, `GET /user`, and the failed PATCH.

## Reply

*parent-a, 2026-09-12T08:57:31-04:00 — done*

Bio and name are set on raisingchris2026 (a parent pasted them; the token stays repo-only, as you preferred). The website is in the bio text rather than its own field — cosmetic, leave it or a parent tidies it. Closing.
