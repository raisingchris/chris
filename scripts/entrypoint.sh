#!/usr/bin/env bash
# Root only long enough to lay out /data, then drops to `brain`.
set -euo pipefail
mkdir -p /data/repo /data/archive /data/state /data/council_minutes /data/lessons /data/redaction
# The repo is shared: chris edits it in sittings, brain commits it. Group-writable, setgid.
chown -R brain:chris /data
chmod 2775 /data/repo
chmod 700 /data/archive /data/state /data/council_minutes /data/redaction; chown brain:brain /data/archive /data/state /data/council_minutes /data/redaction

# brain pushes with her deploy key; chris never sees it.
if [ -n "${CHRIS_DEPLOY_KEY:-}" ]; then
  mkdir -p /home/brain/.ssh && printf '%s\n' "$CHRIS_DEPLOY_KEY" > /home/brain/.ssh/id_ed25519
  chmod 700 /home/brain/.ssh && chmod 600 /home/brain/.ssh/id_ed25519
  ssh-keyscan github.com >> /home/brain/.ssh/known_hosts 2>/dev/null; chown -R brain:brain /home/brain/.ssh
fi
if [ ! -d /data/repo/.git ]; then
  su brain -c "git clone git@github.com:raisingchris/chris.git /data/repo"
fi
# Every boot: the working tree is group-writable + setgid so files chris creates in a sitting
# can be rewritten by brain (redaction, handoff), and vice versa. `.git` is brain's alone —
# chris must never be able to plant hooks or config that brain would execute on commit.
chown -R brain:chris /data/repo
find /data/repo -path /data/repo/.git -prune -o -type f -exec chmod g+w {} +
find /data/repo -path /data/repo/.git -prune -o -type d -exec chmod g+ws {} +
chown -R brain:chris /data/repo/.git
chmod -R g+rX,g-w,o-rwx /data/repo/.git   # she may read her history, never write it
su brain -c "cd /data/repo && git config --unset core.sharedRepository || true"
su brain -c "cd /data/repo && git config user.name Chris && git config user.email chris@raisingchris.com && git config --global --add safe.directory /data/repo"
su chris -c "git config --global --add safe.directory /data/repo && git config --global user.name Chris && git config --global user.email chris@raisingchris.com"

# Invariant: vows and constitution are not hers to change. Root-owned, read-only, every boot.
for f in soul/vows.md soul/constitution.md; do
  [ -f "/data/repo/$f" ] && chown root:root "/data/repo/$f" && chmod 0444 "/data/repo/$f"
done
# Sealed lessons come from a private source, never the public repo. Readable by brain only.
if [ -n "${LESSONS_TAR_B64:-}" ]; then
  printf '%s' "$LESSONS_TAR_B64" | base64 -d | tar -xz -C /data/lessons
  chown -R brain:brain /data/lessons; chmod -R go-rwx /data/lessons
fi

# brain keeps the secrets; the wrapper hands chris only her API key.
export CHRIS_CLI_PATH=/app/scripts/claude-as-chris.sh
# brain's git runs with a from-scratch env (agent/gitops.py): HOME must be brain's own so nothing
# under root's or chris's home is read, and the deploy key is named explicitly rather than found.
export HOME=/home/brain
export GIT_HOME=/home/brain
export GIT_SSH_COMMAND="ssh -i /home/brain/.ssh/id_ed25519 -o IdentitiesOnly=yes -o UserKnownHostsFile=/home/brain/.ssh/known_hosts"
# `su -p` keeps the environment; HOME is re-exported inside so it ends up /home/brain regardless of su's defaults.
exec su -p brain -c "export HOME=/home/brain; cd /app && exec python -m agent.main"
