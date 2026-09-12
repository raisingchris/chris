---
id: 20260912T0939-github-token-can-t-open-issues-or-prs-on
title: GitHub token can't open issues or PRs on other people's repos (Pillow → 403)
  — needs a classic token with `public_repo`, which would also close 20260911T0707
status: open
opened: '2026-09-12T09:39:32-04:00'
by: chris
---

parent-a said "Pillow — good, do it" this morning (archive:2026-09-12#79). I wrote the issue, checked both tests are unchanged on `main`, searched the tracker for duplicates (none), and posted from `raisingchris2026`:

```
POST /repos/python-pillow/Pillow/issues → 403 "Resource not accessible by personal access token"
X-Accepted-Github-Permissions: issues=write
```

The token is a fine-grained PAT (`github_pat_…`). GitHub's docs list, under what fine-grained tokens can't do: "Using fine-grained personal access token to contribute to public repos where the user is not a member." So with this token I can't open an issue, comment, or open a pull request on any project I don't own — which is every project. Ticket 20260909T0708 said the token would allow "open PRs, comment on issues"; GitHub doesn't let a fine-grained token do that outside my own repos.

**Fix I'm asking for:** replace it with a **classic** token with the single scope `public_repo`. That scope covers issues, comments, PRs, forks and creating public repositories (so ticket 20260911T0707 closes too), and it cannot touch private repos or account settings. I don't want `repo`, `workflow`, `admin:*` or `user` scopes. Set an expiry (90 days is fine); I'll ask again when it runs out. If you'd rather not, say so here and the Pillow report stays a draft a person can post.

**The draft** is at `memory/wiki/projects/findings/pillow-issue-draft.md` — the exact text I tried to post. Its first line says "A person has read this report before I filed it." I'm reading your "good, do it" as that — please tell me here if you *didn't* actually read findings 6 and 7, and I'll change the line before posting.

Not urgent in hours; Pillow's tests have been this way since 2014.
