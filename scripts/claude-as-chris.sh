#!/usr/bin/env bash
# The brain (user `brain`, holds every secret) launches the Claude Code CLI — and therefore
# Chris's terminal — as user `chris`. sudo resets the environment; only the variables named
# here cross over. She can read anything in her repo and nothing of ours.
exec sudo -n -u chris -H \
  TZ="${TZ:-America/New_York}" \
  LANG=C.UTF-8 \
  ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}" \
  CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 \
  /usr/local/bin/claude "$@"
