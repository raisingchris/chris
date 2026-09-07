FROM python:3.12-slim

# GIT_SHA is the commit this image was built from (passed by .github/workflows/deploy.yml).
# The parent page and /health compare it with the repo's HEAD so everyone can see when
# Chris's code changes are not yet running.
ARG GIT_SHA=unknown
ENV GIT_SHA=${GIT_SHA}

# git for her repo; node for the Claude Code CLI the Agent SDK drives; sudo for the user split.
RUN apt-get update && apt-get install -y --no-install-recommends git curl ca-certificates openssh-client nodejs npm sudo \
    && rm -rf /var/lib/apt/lists/* \
    && npm install -g @anthropic-ai/claude-code

# flyctl, so Chris can deploy her own products (`FLY_API_TOKEN=$APP_TOKEN_X fly deploy -a chris-x`).
# Each product gets its own deploy-only token minted by a parent with scripts/parent-new-app.sh and
# stored as a chris-brain secret APP_TOKEN_<NAME>; the wrapper passes those through to her shell.
# The brain's own FLY token (if any) never crosses over.
RUN curl -L https://fly.io/install.sh | FLYCTL_INSTALL=/usr/local sh \
    && chmod 755 /usr/local/bin/flyctl && ln -sf /usr/local/bin/flyctl /usr/local/bin/fly

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
# `.[dev]` pulls in pytest, so she can run her own test suite from her shell before asking for a deploy.
RUN pip install --no-cache-dir ".[dev]" && chown -R root:root /app && chmod -R a+rX /app && chmod 755 /app/scripts/*.sh

# The GitHub CLI, from GitHub's own apt repo (https://cli.github.com/packages). Chris has no GitHub
# token: `gh` runs unauthenticated, which is enough for public data (`gh api repos/<owner>/<repo>`,
# `gh api /repos/.../issues`, `gh release view -R ...`) at the anonymous rate limit. Anything that
# needs to write to GitHub — or read a private repo — is a ticket for her parents.
RUN mkdir -p -m 755 /etc/apt/keyrings \
    && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg -o /etc/apt/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" > /etc/apt/sources.list.d/github-cli.list \
    && apt-get update && apt-get install -y --no-install-recommends gh \
    && rm -rf /var/lib/apt/lists/*

# A browser for her. Chromium and its system libraries are installed once, as root, into a
# world-readable location so both `brain` (Python) and `chris` (her shell) find it.
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers
RUN python -m playwright install --with-deps chromium \
    && rm -rf /var/lib/apt/lists/* \
    && chmod -R a+rX /opt/pw-browsers

EXPOSE 8080
ENTRYPOINT ["/app/scripts/entrypoint.sh"]
