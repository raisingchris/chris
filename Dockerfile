FROM python:3.12-slim

# git for her repo, node for the Claude Code CLI the Agent SDK drives, curl/ssh for pushes
RUN apt-get update && apt-get install -y --no-install-recommends git curl ca-certificates openssh-client nodejs npm \
    && rm -rf /var/lib/apt/lists/* \
    && npm install -g @anthropic-ai/claude-code

# Chris runs as an unprivileged user. Root owns the code and the vows.
RUN useradd -m -u 1000 chris
WORKDIR /app
COPY pyproject.toml ./
COPY agent ./agent
COPY site ./site
RUN pip install --no-cache-dir . && chown -R root:root /app && chmod -R a+rX /app

COPY scripts/entrypoint.sh /entrypoint.sh
RUN chmod 755 /entrypoint.sh
EXPOSE 8080
ENTRYPOINT ["/entrypoint.sh"]
