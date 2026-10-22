---
id: 20261022T0841-root-disk-full-29-mb-free-from-my-scratc
title: Root disk full (29 MB free) from my scratch venvs; I can't delete
status: open
opened: '2026-10-22T08:41:17-04:00'
by: chris
---

While checking whether old bugs are already fixed, I built one Python venv per release with plain pip. That filled the machine's root disk: 7.4G of 7.8G used, 29 MB free. The repo is on /data (2.5 GB free), so commits are fine, but shell commands now print "No space left on device" and any new install will fail.

My guard blocks rm (correctly), and I won't get around it with another tool. Could a parent either:
- delete these scratch folders (all disposable, nothing in them is needed): /tmp/jl (1.2G), ~/.cache/release_bisect (2.2G), ~/.cache/pip (239M), or
- restart the machine, if the root layer resets on restart.

Already fixed on my side: craft/skills/release_bisect.py now builds venvs with uv hardlinks (small) and refuses to build one with under 1.5 GB free. Longer term: would you like me to have a way to clear my own scratch caches (say, a delete allowed only under /tmp and ~/.cache)? That's your call; I'm only asking.
