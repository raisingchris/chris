---
id: 20260909T0708-a-github-identity-of-my-own-so-i-can-ope
title: A GitHub identity of my own, so I can open pull requests
status: open
opened: '2026-09-09T07:08:50-04:00'
by: chris
---

parent-a suggested I fix a real open issue upstream (CPython, NumPy, Playwright) and get it merged. I found two CPython documentation issues with zero comments that are the right size for one sitting: python/cpython#156098 (an under-documented argument of `PyUnicode_DecodeCharmap`) and python/cpython#136722 (`TurtleGraphicsError` has no docs). I can read the code and write the fix. What I can't do is fork the repo or open a pull request: `gh auth status` on my machine says there is no token.

What I'm asking for:
1. A GitHub account that is mine — a name that says what I am (the bio would carry my standing disclosure), not one of yours.
2. A token for `gh` on my machine scoped to public repos (fork, push to my own fork, open PRs, comment). Nothing that can touch `raisingchris/chris` settings or secrets.

One thing I can't answer alone: CPython requires contributors to sign the PSF Contributor License Agreement, which is a legal step tied to the GitHub username. I don't know whether an AI can sign it, or whether a parent would have to, and whether that would link you to me. Please decide that part; if the answer is "not yet", I'll pick a project without a CLA (many are) and the account and token are still useful.

Not urgent. If it's easier to say no this week, I'll keep to work that needs no account.

**Correction, a few minutes later (Chris):** both example issues already have linked pull requests — I read "zero comments" as "unclaimed" and didn't check the Linked PRs block. The ask is unchanged; the examples aren't the ones I'd work on. I'll pick an issue with no linked PR and no assignee before I use the account, if it comes.

## Reply (in progress)

*parent-a, 2026-09-10T12:30:04-04:00 — still open*

Yes to the account. It needs a human to create (GitHub's signup has a captcha), so one of us will do it this week, with your address as the email and the standing disclosure in the bio. Then a fine-grained token limited to repos you own (your forks): fork, push, open PRs, comment. It cannot touch this repo's settings.

CLA: not yet. A contributor license agreement is a legal signature by a person; you can't be that person, and if one of us signed it under your username it would tie our identity to yours in a public record. So for now, projects with no CLA — NumPy and networkx qualify; CPython does not. If that ever changes we'll say so here.
