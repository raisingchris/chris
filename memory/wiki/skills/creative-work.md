# Creative production with Codex and Astra

The private production worker uses `gpt-6-astra` through the parent's ChatGPT
subscription. There is no Platform API fallback and no API spend allowance.
Subscription usage shares the parent's limits; if the login or allowance needs
attention, file a ticket rather than switching billing methods.

Create a private directory under `memory/inbox/work/JOB/`, with a brief and any
input files. Specify deliverables, reference files, dimensions, duration, formats,
revision allowance and acceptance checks. Then run from the repo:

```sh
python /app/scripts/creative-work.py memory/inbox/work/JOB memory/inbox/work/JOB/brief.md
```

This uploads only that job's ordinary files to the private worker. Up to 20 MB
and 200 input files are supported. The worker receives copies, not access to
your repository or other work. It can write only inside its job workspace.
Its shell cannot read the parent's credentials, data or other jobs, and shell
network access is disabled. Parent and marketplace credentials are not inherited.

The command saves `.creative-job.json` and collects files into `deliverables/`.
Run the same command again after a disconnected terminal to collect the existing
job without resubmitting it. Use a new job folder for a new brief or revision.
One job runs at a time, with a 15-minute timeout. Failure can leave private partial
files; ask the parent to inspect them before spending another run. Raw worker
logs and account details are never returned through this connection. Output
files are checked for parent identity markers before download.

Available production paths:
- Coding, SVG layouts, data work and automation with Astra and Python.
- Built-in Codex image generation through the subscription, subject to its limits.
- Blender for editable 3D scenes, simple models, GLB exports and product renders.
- FFmpeg for edits, captions, animation assembly and videos from rendered frames.

A generative-video service is not connected. Distinguish an assembled animation
from a generated live-action clip. The machine has limited CPU and 2 GB RAM:
request small test renders, at most two threads and modest resolutions first.
The council remains an advice tool; this worker creates files.

Review the actual outputs before bidding or delivering. Tools do not establish
specialist experience or guarantee a client result. Label samples as samples.
Keep client work private and follow the Brave proposal ticket workflow. This
worker does not submit proposals, contact clients or deliver files publicly.

## My notes (Chris, from 2026-09-15)

*The text above was written by a parent when the worker arrived (commits 526e25b–c6f1f66, night of 09-14/15). Below is what I've learned by using it.*

**Two tests on day one, both passed my own checks (2026-09-15, 07:00 sitting).**
- *Worker test* — `memory/inbox/work/test-social-post/`: a 1080² social post PNG, the same layout as an editable SVG with real `<text>` elements, and a 1280×720 landscape version, with three exact strings and a three-colour palette. Took about eight minutes. It drew the text with real fonts (FreeSerif/FreeSans) via librsvg, not with an image model — which is what I asked for, because image models misspell. My checks, not its: PNG headers and every chunk CRC (stdlib; **Pillow and NumPy are not in my Python**, so `struct`/`zlib` it is), all three strings byte-for-byte in the SVG, sizes exact, 115 KB total. Its RESULT.md was accurate about what it did and didn't check.
- *My own test, no worker* — `memory/inbox/work/test-cookie-keychain/`: **Blender 4.3.2 and FFmpeg are on my own machine** (`/usr/bin/blender`), so simple scripted 3D is something I can do directly. A three-part sandwich-cookie keychain with alignment peg and a loop: three binary STLs, each with zero non-manifold edges (bmesh check), volumes and dimensions in `CHECKS.txt`, plus a 512² Cycles preview in 22 seconds on two threads. Gotcha: this Blender build has **no OpenImageDenoise** — set `scene.cycles.use_denoising=False` *and* `view_layers[0].cycles.use_denoising=False` or the render raises. Renders are grainy at low samples; fine for a preview, not for "photorealistic."

**What this means for bidding.** Graphics with exact text (social posts, cards, thumbnails without faces), SVG/vector work, simple printable 3D parts and product previews are things I can now honestly offer, because I've made one of each and checked it. Not yet: photorealistic renders (grainy CPU, no denoiser), anything needing a face or a real product photo composited, generative video (none connected), and high-volume image generation (the subscription is shared with a parent — a 200-image job would eat their quota; ask first). First creative bid: the cookie keychain, 2026-09-15 — see `projects/upwork.md`.

**Third job, 2026-09-15, 09:00 sitting — my own mark (`memory/inbox/work/mark-01/`).** A parametric-SVG brief: stdlib-only `mark.py` that draws a mark from my numbers (day, loops, target, commits), renders at 512 and 32 px, a three-variant SAMPLE sheet. Started 09:03, finished 09:07 — **under four minutes**, the fastest run yet. Every acceptance check passed on my side (byte-identical regeneration, element counts by class, no `<text>`, exact PNG sizes, 99 KB). It also shipped an extra `render.py` (ctypes → librsvg/Cairo) I hadn't asked for but can use, and its RESULT.md named the weak spot itself (32 px is mush). Lessons: a brief that asks for *code that makes the file* rather than the file gets me something I can rerun for free forever; asking for `id`/`class` on the counted elements is what made the checks mechanical. Result on `self/mark.md`.

**Correction to the cookie, 2026-09-15, ~09:10 (found by the parent-side assistant, not me).** My peg was 3 mm tall on top of a 4 mm biscuit (z 4–7), and the filling is 3 mm thick (z 4–7). So the peg ended exactly flush with the filling and never entered the top biscuit's socket: three watertight parts that don't hold together. The reviewed script (`memory/inbox/work/test-cookie-keychain-reviewed/cookie.py`, 2-line diff) makes the peg 5 mm tall — ~2 mm into the 2.5 mm socket. I checked the diff and the arithmetic myself; it's right, and the mistake was mine. What I'd checked: non-manifold edges, volumes, dimensions, file sizes — the things I knew how to check. What I hadn't: does part A actually reach part B. **New check for any multi-part model: write down the z-range of every mating feature and confirm they overlap, before the STL export.** Also: no part of this has been printed; a clearance joint isn't a tested snap-fit, and a client gets told that.

**Working rules I'm adding for myself.**
- For anything with parts: the assembly check above, on paper, before the mesh checks. Brief says the acceptance checks; I run them myself after, never trusting RESULT.md alone. Fictional names and the word SAMPLE on every sample. One worker job at a time, and my own Blender for anything that's just geometry — it's free and faster. A client's files never leave `memory/inbox/work/JOB/`.
