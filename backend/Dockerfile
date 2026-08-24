# [Input] Consume backend source tree and requirements.txt during container builds.
# [Output] Build the Ink & Memory FastAPI runtime image served by uvicorn on port 8765.
# [Pos] deployment image spec in backend/
# [Sync] 2026-06-03: rewrite based on Pawkeyland Dockerfile — python 3.10-bookworm,
#        pip mirror, Node.js + claude-code CLI, HEALTHCHECK, --proxy-headers.
# [Sync] 2026-06-12: add configurable Debian/PyPI/npm mirror build args for faster China builds.
# [Sync] 2026-06-14: install Claude Code Linux sandbox dependencies for Docker deployments.
# [Sync] 2026-06-17: ensure standard sbin directories exist for bubblewrap rootfs mounts.
# [Sync] 2026-08-24: atomically pair the custom Agent SDK 0.2.143 with its
#        Claude Code 2.1.241 CLI line, assert public MCP login/logout/no-browser
#        argv at build time,
#        and remove the obsolete vendor apply-seccomp mutation. Native CLI
#        sandboxing uses bubblewrap/socat; workspace settings explicitly skip
#        the optional Unix-socket seccomp filter in nested containers.
# [Sync] 2026-08-19: align the image with the backend's Python 3.12 source
#        contract (including datetime.UTC) so the production module graph is
#        importable before Claude MCP/sandbox acceptance runs.
# [Sync] 2026-08-19: source Node 22.18.0 from the official Node image because
#        Claude Code 2.1.241 declares Node >=22; Debian bookworm's Node 18 is
#        not an accepted production pairing.
# [Sync] 2026-08-24: install ink-claude-dream-agent-sdk 0.2.143 from immutable
#        Git commit bcdfbcf9f72bc34865d0efeb5f971d6df005f5b4 through the uv-
#        exported requirements lock; verify distribution/import ownership at
#        build time. Keep official Claude Code 2.1.241 only as the explicit
#        CLAUDE_CODE_CLI_PATH rollback artifact; it is not the default Runtime.

ARG NODE_VERSION=22.18.0
FROM node:${NODE_VERSION}-bookworm-slim AS node_runtime
FROM python:3.12-slim-bookworm

ARG NODE_VERSION

ARG DEBIAN_MIRROR=https://mirrors.aliyun.com/debian
ARG DEBIAN_SECURITY_MIRROR=https://mirrors.aliyun.com/debian-security
ARG NPM_REGISTRY=https://registry.npmmirror.com
ARG PYPI_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ARG PYPI_TRUSTED_HOST=mirrors.aliyun.com

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=UTC \
    PIP_NO_CACHE_DIR=1 \
    PIP_INDEX_URL=${PYPI_INDEX_URL} \
    PIP_TRUSTED_HOST=${PYPI_TRUSTED_HOST} \
    PIP_DEFAULT_TIMEOUT=180 \
    PIP_RETRIES=10 \
    PIP_PROGRESS_BAR=off

# System deps:
#   - gcc / libffi / libssl / libjpeg / zlib: cryptography + Pillow
#   - bash curl jq git ripgrep: runtime utilities used by agent/tooling
#   - bubblewrap socat: Claude Code sandboxed Bash runtime on Linux
ARG CLAUDE_CODE_VERSION=2.1.241
RUN set -eux; \
    if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
        sed -i \
            -e "s|http://deb.debian.org/debian|${DEBIAN_MIRROR}|g" \
            -e "s|http://deb.debian.org/debian-security|${DEBIAN_SECURITY_MIRROR}|g" \
            -e "s|http://security.debian.org/debian-security|${DEBIAN_SECURITY_MIRROR}|g" \
            /etc/apt/sources.list.d/debian.sources; \
    fi; \
    apt-get -o Acquire::Retries=5 update; \
    apt-get install -y --no-install-recommends \
        gcc \
        libffi-dev \
        libssl-dev \
        libjpeg62-turbo-dev \
        zlib1g-dev \
        bash \
        curl \
        jq \
        git \
        ripgrep \
        ca-certificates \
        bubblewrap \
        socat; \
    mkdir -p /sbin /usr/sbin /usr/local/sbin; \
    rm -rf /var/lib/apt/lists/*

# Claude Code 2.1.241 requires Node >=22. Copy the pinned runtime and npm from
# the official Node image instead of accepting bookworm's unsupported Node 18.
COPY --from=node_runtime /usr/local/bin/node /usr/local/bin/node
COPY --from=node_runtime /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/npm
RUN set -eux; \
    ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm; \
    ln -s ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx; \
    test "$(node --version)" = "v${NODE_VERSION}"

# Explicit official-CLI rollback artifact. Dream's default resolver does not
# select the ambient `claude` name; an operator must deliberately set the
# absolute CLAUDE_CODE_CLI_PATH=/usr/local/bin/claude to use this rollback.
# bubblewrap/socat above provide its required Linux sandbox dependencies.
RUN set -eux; \
    test "${CLAUDE_CODE_VERSION}" = "2.1.241"; \
    npm config set registry "${NPM_REGISTRY}"; \
    npm install -g "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}"; \
    test "$(claude --version | awk '{print $1}')" = "${CLAUDE_CODE_VERSION}"; \
    claude mcp login --help | grep -F -- "--no-browser"; \
    claude mcp logout --help >/dev/null; \
    npm cache clean --force

WORKDIR /app

COPY requirements.txt ./
# Registry dependencies use the configured mirrors. The Dream SDK itself is a
# PEP 508 Git requirement pinned to one immutable commit in requirements.txt.
RUN python -m pip install --no-cache-dir --timeout 180 --retries 10 \
    --extra-index-url http://mirrors.cloud.aliyuncs.com \
    -r requirements.txt; \
    python -c "from importlib import metadata as m; import claude_agent_sdk as sdk; from claude_agent_sdk._cli_version import __cli_version__; dist=m.distribution('ink-claude-dream-agent-sdk'); providers={name.lower().replace('_','-') for name in m.packages_distributions().get('claude_agent_sdk', [])}; installed={str(item.metadata.get('Name') or '').lower().replace('_','-') for item in m.distributions()}; assert dist.version == '0.2.143'; assert sdk.__version__ == '0.2.143'; assert __cli_version__ == '2.1.241'; assert providers == {'ink-claude-dream-agent-sdk'}; assert 'claude-agent-sdk' not in installed; assert all(hasattr(sdk, name) for name in ('ClaudeAgentOptions', 'ClaudeSDKClient', 'query'))"

COPY . .

EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request,os; urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8765')+'/', timeout=3).read()"

# Use shell form so ${PORT} is expanded at runtime by Cloud Run.
CMD exec uvicorn server:app --host 0.0.0.0 --port ${PORT:-8765} --proxy-headers
