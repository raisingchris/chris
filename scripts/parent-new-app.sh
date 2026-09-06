#!/usr/bin/env bash
# A parent runs this on their own machine to give Chris a new Fly app for one of her products.
#
#   scripts/parent-new-app.sh <name>       e.g. scripts/parent-new-app.sh shoplist
#
# It creates Fly app `chris-<name>` (org personal, region iad), mints a deploy-only token
# scoped to that single app, and prints the `fly secrets set` line that hands the token to
# chris-brain as APP_TOKEN_<NAME>. scripts/claude-as-chris.sh passes every APP_TOKEN_* through
# to her shell, so in a sitting she can run:
#
#   FLY_API_TOKEN=$APP_TOKEN_<NAME> fly deploy -a chris-<name>
#
# The token can deploy that one app and nothing else — not chris-brain, not the org.
set -euo pipefail

name="${1:-}"
if [ -z "$name" ] || ! [[ "$name" =~ ^[a-z0-9][a-z0-9-]{0,40}$ ]]; then
  echo "usage: $0 <name>   (lowercase letters, digits, dashes)" >&2
  exit 2
fi
app="chris-$name"
var="APP_TOKEN_$(echo "$name" | tr 'a-z-' 'A-Z_')"

command -v fly >/dev/null || { echo "flyctl not found; install from https://fly.io/docs/flyctl/install/" >&2; exit 1; }

echo "Creating Fly app $app (org personal, region iad)..."
fly apps create "$app" --org personal >/dev/null
# Region is chosen at first deploy; a fly.toml in her product repo should set primary_region = "iad".

echo "Minting a deploy-only token for $app..."
token="$(fly tokens create deploy -a "$app" --name "chris deploys $app" -x 8760h)"

cat <<EOF

Done. Give the token to chris-brain (it stays a brain secret; the wrapper hands it to her shell):

  fly secrets set -a chris-brain $var=$token

Then tell her (mail or memory/inbox) that $app exists and that \$$var is its deploy token:

  FLY_API_TOKEN=\$$var fly deploy -a $app
EOF
