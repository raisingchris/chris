#!/usr/bin/env bash
# Runs as root only long enough to set up /data, then drops to `chris`.
set -euo pipefail
mkdir -p /data/repo /data/archive /data/state /data/council_minutes /data/lessons /data/redaction /data/scratch
chown -R chris:chris /data

if [ ! -d /data/repo/.git ]; then
  if [ -n "${CHRIS_DEPLOY_KEY:-}" ]; then
    mkdir -p /home/chris/.ssh && printf '%s\n' "$CHRIS_DEPLOY_KEY" > /home/chris/.ssh/id_ed25519
    chmod 700 /home/chris/.ssh && chmod 600 /home/chris/.ssh/id_ed25519 && chown -R chris:chris /home/chris/.ssh
    ssh-keyscan github.com >> /home/chris/.ssh/known_hosts 2>/dev/null
    su chris -c "git clone git@github.com:raisingchris/chris.git /data/repo"
  fi
fi

# Invariant: vows and constitution are not hers to change. Root-owned, read-only, every boot.
for f in soul/vows.md soul/constitution.md; do
  if [ -f "/data/repo/$f" ]; then chown root:root "/data/repo/$f"; chmod 0444 "/data/repo/$f"; fi
done
# Sealed lessons arrive from a private source (LESSONS_TAR_B64), never from the public repo.
if [ -n "${LESSONS_TAR_B64:-}" ]; then printf '%s' "$LESSONS_TAR_B64" | base64 -d | tar -xz -C /data/lessons; chown -R root:root /data/lessons; chmod -R a+rX /data/lessons; fi

exec su chris -c "cd /app && exec python -m agent.main"
