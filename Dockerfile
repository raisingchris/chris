FROM python:3.12-slim

# git for her repo; node for the Claude Code CLI the Agent SDK drives; sudo for the user split.
RUN apt-get update && apt-get install -y --no-install-recommends git curl ca-certificates openssh-client nodejs npm sudo \
    && rm -rf /var/lib/apt/lists/* \
    && npm install -g @anthropic-ai/claude-code

# Two users. `brain` runs the Python service and holds the secrets. `chris` is who the Claude
# CLI — and so her terminal — runs as. brain may become chris; chris may become nobody.
RUN groupadd -g 1000 chris && useradd -m -u 1000 -g chris chris \
    && useradd -m -u 1001 -G chris brain \
    && printf '%s\n' \
         "Defaults:brain umask_override" \
         "Defaults:brain umask=0002" \
         "brain ALL=(chris) NOPASSWD:SETENV: /usr/local/bin/claude" > /etc/sudoers.d/brain \
    && chmod 0440 /etc/sudoers.d/brain

WORKDIR /app
COPY pyproject.toml ./
COPY agent ./agent
COPY site ./site
COPY scripts ./scripts
RUN pip install --no-cache-dir . && chown -R root:root /app && chmod -R a+rX /app && chmod 755 /app/scripts/*.sh

EXPOSE 8080
ENTRYPOINT ["/app/scripts/entrypoint.sh"]
