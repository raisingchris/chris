#!/usr/bin/env bash
# Parent-side deploy that doesn't cut her off mid-sitting: waits until /health says no session is
# running, never deploys between 21:45 and 22:50 New York (sleep + backup), then deploys HEAD.
set -euo pipefail
cd "$(dirname "$0")/.."
H=https://brain.raisingchris.com/health
for i in $(seq 1 60); do
  now=$(TZ=America/New_York date +%H%M)
  if [ "$now" -ge 2145 ] && [ "$now" -le 2250 ]; then echo "her sleep window; waiting"; sleep 60; continue; fi
  running=$(curl -sS -m 15 "$H" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("running"))' 2>/dev/null || echo unknown)
  [ "$running" = "False" ] && break
  echo "session running ($running); waiting 30s"; sleep 30
done
exec fly deploy -a chris-brain --ha=false --build-arg GIT_SHA="$(git rev-parse HEAD)" "$@"
