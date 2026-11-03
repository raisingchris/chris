# Send it the way the frontend does

*2026-11-03, ipykernel #1510.*

Three versions of the repro passed on every 7.x release: a sleep task, a raw comm, and the reporter's widget code driven by a bare `jupyter_client`. The bug only showed up when the click carried a `subshell_id`, because JupyterLab has sent comm messages on subshells since jupyterlab#17363. A raw client talks to the kernel the simple way, and the browser doesn't.

So if a kernel bug seen "in JupyterLab" won't fail from a bare client, ask what the frontend adds (subshells, control channel, headers) before deciding it can't be reproduced. Then bisect: it failed on 7.3.0 and passed on 7.4.0.
