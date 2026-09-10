#!/usr/bin/env bash
# The brain (user `brain`, holds every secret) launches the Claude Code CLI — and therefore
# Chris's terminal — as user `chris`. sudo resets the environment; only the variables named
# here cross over. She can read anything in her repo and nothing of ours.
#
# Per-product Fly deploy tokens: every APP_TOKEN_<NAME> secret on chris-brain (minted by a
# parent with scripts/parent-new-app.sh) is passed through so she can deploy her own apps with
# `FLY_API_TOKEN=$APP_TOKEN_<NAME> fly deploy -a chris-<name>`. Each token is scoped to one
# app; the brain's own tokens (GitHub, Fly for chris-brain, mail, money) never cross.
# sudo's env_keep can't glob, so the list is computed here and passed as VAR=value args.
app_tokens=()
while IFS='=' read -r name value; do
  [ -n "$name" ] && app_tokens+=("$name=$value")
done < <(env | grep -E '^APP_TOKEN_[A-Z0-9_]+=' || true)

exec sudo -n -u chris -H \
  TZ="${TZ:-America/New_York}" \
  LANG=C.UTF-8 \
  ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}" \
  GH_TOKEN="${CHRIS_GH_TOKEN:-}" \
  PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-/opt/pw-browsers}" \
  FLY_APP_TOKENS_NOTE="${FLY_APP_TOKENS_NOTE:-}" \
  CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 \
  "${app_tokens[@]}" \
  /usr/local/bin/claude "$@"
