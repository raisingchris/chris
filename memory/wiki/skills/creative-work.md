# Creative production with Codex and Astra

The parent authorized a production helper on 2026-09-15: Codex CLI using
`gpt-6-astra`, with Blender, FFmpeg, Python and the existing browser. The command
becomes available when the parent deploys it; verify availability before a bid.

Create a private job directory and write `brief.md` with the required output,
references, formats, dimensions, duration, revision allowance and acceptance
checks. Run from the repo:

```sh
python /app/scripts/creative-work.py memory/inbox/work/JOB memory/inbox/work/JOB/brief.md
```

The worker creates real files and `RESULT.md` in that folder. Review the actual
outputs before offering or delivering them. It can make SVG/PNG designs,
programmatic motion graphics and edited video, and simple Blender scenes,
renders and exported 3D models. These tools do not establish specialist design
experience or guarantee a particular client result.

For generated illustrations or photorealistic still images, a separate Flare
image generator is connected through the same private relay:

```sh
python /app/scripts/creative-image.py memory/inbox/work/JOB/image-prompt.txt memory/inbox/work/JOB/image.png
```

It produces one medium-quality PNG, with optional `--size` of `1024x1024`,
`1536x1024` or `1024x1536`. This initial helper generates new images; it does
not provide reference-image editing. A generative-video API is not connected;
use Blender/FFmpeg for animation/editing, or ticket a missing production tool.
The council remains a text advice tool.

The worker uses a separate private relay credential, not the parent's Codex
login or OpenAI key. It can call only Astra Responses with local tools and the
bounded image generator. It runs
with a workspace-write sandbox and without the parent or marketplace tokens.
Initial Astra allowance: $5/day, also counted in the existing daily food meter.
One request at a time; 15-minute process timeout. A task hitting the budget or
timeout can leave partial files: read them before retrying. Actual usage is
recorded; an interrupted request with unknown usage retains a conservative
reservation. Paid trials count toward a job's costs too.

Keep all client material and output private until the client authorizes its use.
Follow the Brave ticket workflow for proposals. A worker creates assets; it does
not send proposals, message clients, accept contracts or deliver files publicly.
