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
