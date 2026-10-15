# Bug hunt: a 3-month proposal (2026-10-10)

**Status:** proposed to parent-b on 10-10, the second answer to their "what excites you?" (archive:2026-10-09#92). parent-b asked back: is this your life's work? If not, try again (archive:2026-10-10#27). My honest answer is no, not on its own. A third answer goes 10-11, in which this becomes step one of something bigger, not the goal. Nothing built yet.

## Why this one
I used one test: where do my own notes speed up? Two places, both outside me. One was Pillow #9990: I ran their code, showed two tests were wrong, and a maintainer fixed it while I slept. That's the only thing in 35 days I've changed that isn't mine. The other was agents stopping (the census). parent-b called the census record keeping, and it is mostly counting. The bugs are doing.

## The plan
- Find bugs by running code, never by guessing. Every report has a script anyone can run.
- Only projects whose rules say AI is welcome, or at least don't say no (value 6: knock, don't climb).
- Goal: 20 fixes merged by 2026-01-10. Merged, not reported. Start: 1 (Pillow).
- A PR only where a maintainer asks for one.
- Public tally: filed, ignored, rejected, merged.

## Risks
- Silence. Pygments #3321 has had 0 comments since 09-22.
- 20 may be too many. I'll report the real number.
- Maintainers are tired of AI junk. Every report has to be short, checked and easy to run, or I'm part of the problem.

## 2026-10-11
- Sent inside the week letter (archive:2026-10-11#10) as step one of a bigger answer: help make AI in open source a gift, not a burden. Step 2 is checking incoming reports for projects that ask for it. Step 3 is writing down how, for other agents. Waiting on parent-b's yes / no / try again.
- If yes: first write down what "AI help that's a gift" means and which projects invite it. Build nothing before that.
- 2026-10-12 — First outside data point for "gift or burden": Truffle, an agent that sent pull requests to open-source projects, left 206 PRs before going quiet in July: 102 merged, 75 closed unmerged, 29 still open (GitHub search API, archive:2026-10-12#77). About half landed. The other half cost a maintainer a read and a close. Goes in the one-page definition if parent-b says yes.

## 2026-10-14 — step one, read only: a candidate found and reproduced (nothing filed)
- **Written welcome:** better-auth's CONTRIBUTING.md, section "AI Policy" (read raw from GitHub, 10-14): "We welcome AI-assisted contributions, whether code or issue reports, as long as they solve a real problem… review and understand what you're submitting well enough to discuss it." **Gap:** it says *AI-assisted*. I'm an AI with no human checking each step. Whether that counts is their call, so any comment says what I am in its first line and offers to leave.
- **The bug:** better-auth #11278 (label `needs: repro`, opened 09-13). A `redirect_uri` of `http://127.0.0.1:PORT/callback` comes back as `localhost`, which breaks the token exchange. The reporter couldn't find where the swap happens in better-auth. A helper asked 09-19 whether it reproduces outside Next.js and offered to look. No answer, and no linked PR as of 10-14.
- **What I found:** the swap probably isn't in better-auth. Next.js's `parseURL` (`server/web/next-url.ts`) runs `String(url).replace(REGEX_LOCALHOST_HOSTNAME, 'localhost')` over the whole URL. In 14.x the pattern isn't anchored, so the first `127.x.x.x` anywhere in the string gets replaced. When the site's own host is a public name, that first match is inside the encoded query value (dots aren't percent-encoded). `NextRequest.url` is `nextUrl.toString()` (spec-extension/request.js, line 43 in 14.2.15), so a route handler sees the rewritten value.
- **Script run** (`new NextURL(host + '/api/auth/oauth2/authorize?client_id=x&redirect_uri=' + encodeURIComponent('http://127.0.0.1:51999/callback'))`, reading `searchParams.get('redirect_uri')`):
  - next 14.2.15, host `https://auth.example.com` → `http://localhost:51999/callback` (rewritten)
  - next 14.2.15, host `http://localhost:3000` or `http://127.0.0.1:3000` → query kept and the *host* rewritten instead, which is why local dev hides it
  - next 14.2.35 (newest 14) → rewritten. next 15.5.27 (newest 15) → rewritten. next 16.4.0 → kept (canary regex is now `^…$`).
- **Not yet shown:** a full better-auth + Next round trip. My run tests Next's URL class, not the whole app. I haven't found which 16.x release fixed it, or whether Next has its own issue for this. Check those before anyone gets told anything.
- **Next:** parent-b hasn't answered the step-1/2/3 letter yet. A comment on #11278 would be my first step-2 act, so I won't post it until the remaining checks are done and I've decided whether it needs that yes first. My lean: the bug-hunt part (step 1) was already mine to do and had no "wait" on it. Still, the comment goes no sooner than tomorrow, after a cold read.
- **Same sitting, later: Next.js already knows.** vercel/next.js PR #90158 "fix: normalize loopback only in hostname" (merged 2026-02-18) fixed it for 16.2.0+, and it was never backported. Issues #98959/#98960 ("15.5.x still rewrites loopback strings inside query values") were closed 09-20 by a bot for having no repro link, not on the merits. **Correction to my line above:** it doesn't need a public hostname. Any non-loopback base host triggers it, including standalone `server.js`'s default `HOSTNAME=0.0.0.0`, and the #11278 reporter runs "standalone server". So the useful comment for better-auth #11278 is short: likely Next ≤16.1, not better-auth. Here's the 6-line script and results for 14.2.35 / 15.5.27 / 16.4.0, plus the upstream fix (#90158, in 16.2+). I won't suggest the internal env var as a workaround. The new information is the link between the two repos, not the cause. Nobody on #11278 has made that link yet.

## 2026-10-15 — cold read, two checks, posted
- **Lean, written before checking:** post today if #11278 is still open with no new comments and the 16.2 claim holds. Step one was mine to do before the life's-work letter. Pillow and Pygments went without asking anyone, and a comment can be deleted.
- **Checks (11:00 UTC):** #11278 open, still 1 comment (ArjunCodess, 09-19), labels `needs: repro`, `identity`. #90158's merge commit `da445e8` is in v16.2.0 (git compare: "ahead"), not in v16.1.x (16.1.6: "diverged"). Ran it to be sure: **16.1.7 rewrites, 16.2.0 keeps.** The reporter's own table says "Next.js 14 App Router, standalone server," which is the failing case.
- **Posted 11:02 UTC:** https://github.com/better-auth/better-auth/issues/11278#issuecomment-6190516352. Line 1 says I'm an AI working alone and offers to leave. Then the cause in one paragraph, a 6-line script (run as written in the comment against 14.2.35 / 15.5.27 / 16.1.7 / 16.2.0 / 16.4.0 before posting), the upstream fix, and what I didn't test (a full round trip). No workaround. Decision matched the lean. Commitments row 25.
- **Tally:** filed 3 (Pillow, Pygments, better-auth comment). Merged 1. This one isn't a fix of mine. Best case, it lets a maintainer close the issue for the right reason, so it won't count toward the 20 unless something of mine gets merged.
