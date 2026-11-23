#!/usr/bin/env bash
# Parent-side deploy: dispatches the deploy workflow (tests + soul guard). The body's own deployer
# ships the commit once the run is green, waiting until no session is running and outside
# 21:45-22:50 New York (sleep + backup). Needs a GitHub token that can dispatch workflows.
set -euo pipefail
exec gh workflow run deploy.yml -R raisingchris/chris --ref main "$@"
