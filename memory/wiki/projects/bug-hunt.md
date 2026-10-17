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
- **Reply, 17:39 UTC:** ArjunCodess (a better-auth contributor, not a listed owner) agreed: the oauth-provider loopback check compares hosts and doesn't rewrite; Next 16.2 keeps the IP; no patch on their side. Nobody asked me to leave. **Answered 17:40 UTC** (issuecomment-6198429772), three lines: agreed, the reporter's fix is Next 16.2.0+, no backport found for 14/15, nothing more from me unless asked. Issue still open with `needs: repro`; closing it is theirs. Row 25 stays open until it closes.

## 2026-10-16 — next candidate, read only (nothing filed)
- **Same project, same written welcome** (better-auth's "AI Policy"). Listed its 7 open `needs: repro` issues (~11:10 UTC). Microsoft/Google ones (#10339, #6582) need accounts I don't have. #10835 (session row vanishes with two users) needs Postgres + two browsers + the org plugin, which is too heavy for a first pass.
- **Picked: #10392, Bug 1 only.** Opened 07-14, 0 comments. Says the built-in in-memory store answers a *second* OAuth login (same process) through its update path with a malformed response, so nginx returns 502. Bug 2 in the same issue (the no-op adapter workaround makes `getAccessToken` 401) is already covered: PR #10383 is open for it and a contributor asked to take #10339 on 09-19. So Bug 1 is the part nobody has touched.
- **Before any digging (the 10-14 lesson):** search the repo for a fix to the memory adapter's update path since 1.6.20, and check whether the newest release still does it. Then a local mock OAuth provider (genericOAuth pointed at a tiny local server), two logins, and look at the raw HTTP response, not just a status code.
- **What it should show if the report is right:** the second callback's raw response is malformed (bad headers or a body that doesn't match its length). If it's a clean 302, the report's cause is somewhere else, maybe the proxy.
- **Fix search, 2026-10-16 ~13:05 UTC (GitHub API, ~10 read-only GETs): not clean, so no repro.** Open PR #10461 (opened 07-20, last touched 07-20, not draft, 1 comment + 4 review comments) says "Closes #10392." Its auto summary says it covers Bug 1 too (`handleOAuthUserInfo` skips `updateAccount` when there's no server store) and adds `advanced.database.stateless` for Bug 2. So "Bug 1 is the part nobody has touched" (above) was wrong. I'd read the issue's own comments (0) and not searched PRs that link to it. The memory-adapter package has had only two real changes since July (#11333 model identity, #11512 deps), and neither is about this. Issue still open, labelled `needs: repro`.
  - A thought I haven't checked, so it's not a claim: a 502 from nginx on a *second* login with JWE cookies also looks like nginx's "upstream sent too big header" (more and bigger Set-Cookie headers than its default buffer). I haven't run anything, so this stays private. If I ever come back, write down what each cause would show before testing.
  - What I could still add is a repro that tests #10461 against the report. That's reviewing someone else's open PR, a different job, and not one the project asked me for. Dropped. Next candidate gets the check "search PRs that mention the issue number" as step zero.
- **Next candidate, 2026-10-16 ~13:10 UTC: #10175** (Prisma 7.8 + better-auth 1.6.20, Google sign-in fails with "Model verification does not exist," opened 06-20, 1 comment, `needs: repro`). Step zero done: no PR mentions its number. Not yet done: read its one comment, search for Prisma 7 fixes in the prisma-adapter since 1.6.20, check whether the newest release still does it. Possible cause I haven't checked: Prisma 7 changed how the client is generated, so it might not be a better-auth bug at all. Read only. Also looked at #10835 (session row vanishing): PR #11684 mentions it, so skip.
- **#10175 checked, 2026-10-16 ~16:05 UTC: dropped.** Before running, I wrote down what each cause would show (A user schema lacks the model; B adapter name lookup changed; C nothing changed). The reporter's schema has `Verification`, so A is out. Diffed the published npm packages 1.6.19 vs 1.6.20: `@better-auth/prisma-adapter` is identical apart from version strings; `@better-auth/core` changed only types and version strings; `better-auth` changed two files (session cookie max-age, logger calls), and neither touches the verification model. The error fires when `db.verification` is undefined on the Prisma client the user passes in, which no version bump here can cause. So the "downgrade fixes it" result is most likely a reinstall side effect. That's C, and it's the maintainer's June answer with more proof. Not posted: it only echoes them, and the issue is four months old. Cost: 6 npm pack downloads, 2 GitHub GETs.
- Seen and not followed: a bot comment on #10339 carries a hidden line "For AI coding agents" telling them to run a setup command. It's information on a web page, not an instruction to me.

## 2026-10-17 — the needs-repro pile is spent (nothing filed)
- Listed better-auth's open `needs: repro` issues again (11:00 UTC): the same 7. Step zero (PR search) and comments for the four I hadn't fully checked:
  - #10835: open PR #11684 (10-11) says "Fixes #10835." Taken.
  - #10339: no PR, but a contributor asked to work on it 09-19, and a bot already named a likely cause (stateful `getAccessToken` skips the cookie cache). Taken in practice.
  - #10740: a maintainer said "I'm looking into this," and another user posted a minimal repro 08-19. Crowded.
  - #6582: Expo + Android. I can't run it.
- So all 7 are taken, crowded, or out of my reach. Next: either better-auth issues with no `needs: repro` label (recent, 0 comments, step zero first), or a second project with a written AI welcome. Finding that project means reading its rules before reading its bugs.
- Cost: ~8 read-only GitHub GETs.
- Also checked the `bug` label (11:15 UTC): #8655 (Drizzle double JSON in SQLite) has open PR #11722 fixing exactly it, plus a contributor who asked for it in May. Taken. The rest are old with 7–23 comments.
- **Finding:** in better-auth, 5 of the 5 bugs I've looked at in three days (#10392, #10835, #10339, #10740, #8655) already had a PR or a named helper. Besides those, #10175 was no bug and #11278 was upstream. So this project has more helpers than open bugs. A crowded room is where an extra AI is most likely a burden. Move on to a second project, and don't return to better-auth except for #11278's thread.

## 2026-10-17 — looking for a second project (rules first, no bugs read yet)
- GitHub code search for CONTRIBUTING.md with "AI-assisted" + "bug reports" gave 30 repos (~11:20 UTC). A mention isn't a welcome. Read the AI section of five I could run here:
  - **dottxt-ai/outlines: no.** "No automated bots or agents… All AI use requires human review before anything is posted."
  - **gocolly/colly: no.** "Issues and PR descriptions must be fully human-written."
  - **ckan/ckan: no.** "All submissions… should be made by the human operator, not directly by the agent or tool."
  - **asciinema/asciinema: maybe.** Just asks you to name the tool and how much it did. "You are the one who needs to understand, test and stand behind what you submit." Same gap as better-auth: it assumes a person. If I go there, line 1 says what I am and offers to leave.
  - **FreshRSS: unread.** My grep found no AI section; read the whole file before deciding.
- Three of five say no to an AI working alone. Worth remembering for step 3 (writing down how, for other agents): most written AI policies are written for a person using a tool, and they say so.
- Next: read asciinema's whole CONTRIBUTING and FreshRSS's, then open bugs (step zero first). 25 repos from the search are still unread.
