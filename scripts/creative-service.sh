#!/usr/bin/env bash
# brain only. Supervise the local worker without restarting the main agent.
set -euo pipefail
umask 0077
cd /app
while true; do
  python -m agent.creative >> /data/state/creative/service.log 2>&1 || true
  sleep 5
done
