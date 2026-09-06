#!/usr/bin/env bash
# Parent commits: UTC timestamps, Parent identity. Usage: scripts/commit.sh "message" [paths...]
set -e
cd "$(dirname "$0")/.."
msg="$1"; shift || true
if [ $# -gt 0 ]; then git add -- "$@"; else git add -A; fi
TZ=UTC GIT_AUTHOR_NAME=Parent GIT_AUTHOR_EMAIL=parent@raisingchris.com GIT_COMMITTER_NAME=Parent GIT_COMMITTER_EMAIL=parent@raisingchris.com git commit -m "$msg"
