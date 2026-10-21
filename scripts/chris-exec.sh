#!/usr/bin/env bash
# The brain runs code Chris wrote (her eval's repro.py) only through this, as `chris`:
#   sudo -n -u chris /usr/local/bin/chris-exec <seconds> <dir> <cmd...>
# Clean environment, no secrets, a hard timeout. No .pyc: a fix that keeps a file the same size
# can otherwise run stale bytecode and look like it did nothing (seen in task validation).
set -euo pipefail
secs="$1"; dir="$2"; shift 2
cd "$dir"
exec env -i PATH=/usr/local/bin:/usr/bin:/bin HOME=/home/chris LANG=C.UTF-8 PYTHONDONTWRITEBYTECODE=1 \
  timeout -k 5 "$secs" "$@"
