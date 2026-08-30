# [Input] Consume backend source tree and requirements.txt during container builds.
# [Output] Build the Ink & Memory FastAPI runtime image served by uvicorn on port 8765.
# [Pos] deployment image spec in backend/
# [Sync] 2026-06-03: rewrite based on Pawkeyland Dockerfile — python 3.10-bookworm,
#        pip mirror, Node.js + claude-code CLI, HEALTHCHECK, --proxy-headers.
# [Sync] 2026-06-12: add configurable Debian/PyPI/npm mirror build args for faster China builds.
# [Sync] 2026-06-14: install Claude Code Linux sandbox dependencies for Docker deployments.
# [Sync] 2026-06-17: ensure standard sbin directories exist for bubblewrap rootfs mounts.
# [Sync] 2026-08-26: atomically pair the custom Agent SDK 0.2.144 with its
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
# [Sync] 2026-08-26: install ink-claude-dream-agent-sdk 0.2.144 from PyPI
#        through the uv-exported version/hash lock; verify distribution/import
#        ownership at build time. Install the exact public
#        ink-claude-code-dream 0.1.4
#        selector as the default production-qualified Runtime, then install
#        official Claude Code 2.1.241 after safely removing only the selector's
#        conflicting `claude` alias, so /usr/local/bin/claude remains the
#        explicit CLAUDE_CODE_CLI_PATH rollback artifact.
# [Sync] 2026-08-28: install and verify ntn 0.15.1 so the backend-owned Notion
#        Skill/MCP path exists in the same backend-only image as its built-in Skill.
# [Sync] 2026-08-30: advance the exact public clean-room Runtime to 0.1.4.

ARG NODE_VERSION=22.18.0
FROM node:${NODE_VERSION}-bookworm-slim AS node_runtime
FROM python:3.12-slim-bookworm

ARG NODE_VERSION

ARG DEBIAN_MIRROR=https://mirrors.aliyun.com/debian
ARG DEBIAN_SECURITY_MIRROR=https://mirrors.aliyun.com/debian-security
ARG NPM_REGISTRY=https://registry.npmmirror.com
ARG INK_CLAUDE_NPM_REGISTRY=https://registry.npmjs.org
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
ARG INK_CLAUDE_CODE_VERSION=0.1.4
ARG NOTION_CLI_VERSION=0.15.1
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

# Install Dream's exact public selector first. Its optional dependency selects
# only the matching linux architecture package. The selector exposes both
# names, so the official package is intentionally installed second: the Dream
# default remains `ink-claude-code-dream`, while `/usr/local/bin/claude` is the
# explicit official rollback selected only through CLAUDE_CODE_CLI_PATH.
RUN set -eux; \
    test "${INK_CLAUDE_CODE_VERSION}" = "0.1.4"; \
    test "${CLAUDE_CODE_VERSION}" = "2.1.241"; \
    npm install -g \
        --registry="${INK_CLAUDE_NPM_REGISTRY}" \
        "@glide-the/ink-claude-code-dream@${INK_CLAUDE_CODE_VERSION}"; \
    test "$(ink-claude-code-dream --version)" = "${CLAUDE_CODE_VERSION} (Claude Code)"; \
    DREAM_RUNTIME_ENTRYPOINT="$(realpath "$(command -v ink-claude-code-dream)")"; \
    DREAM_RUNTIME_ROOT="$(dirname "$(dirname "${DREAM_RUNTIME_ENTRYPOINT}")")"; \
    jq -e \
        --arg runtime_version "${INK_CLAUDE_CODE_VERSION}" \
        --arg sdk_version "0.2.144" \
        '.runtime.name == "ink-claude-code-dream" and .runtime.version == $runtime_version and .runtime.integration.sdkVersion == $sdk_version and .core.corePruned == true and .core.productionEligible == true' \
        "${DREAM_RUNTIME_ROOT}/release-manifest.json" >/dev/null; \
    test -L /usr/local/bin/claude; \
    test "$(realpath /usr/local/bin/claude)" = "${DREAM_RUNTIME_ENTRYPOINT}"; \
    unlink /usr/local/bin/claude; \
    npm config set registry "${NPM_REGISTRY}"; \
    npm install -g "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}"; \
    test "$(claude --version | awk '{print $1}')" = "${CLAUDE_CODE_VERSION}"; \
    test "$(realpath "$(command -v claude)")" != "${DREAM_RUNTIME_ENTRYPOINT}"; \
    test "$(ink-claude-code-dream --version)" = "${CLAUDE_CODE_VERSION} (Claude Code)"; \
    claude mcp login --help | grep -F -- "--no-browser"; \
    claude mcp logout --help >/dev/null; \
    npm install -g --registry="${NPM_REGISTRY}" "ntn@${NOTION_CLI_VERSION}"; \
    test "$(ntn --version)" = "ntn ${NOTION_CLI_VERSION}"; \
    ntn login --help | grep -F -- "--no-browser"; \
    ntn doctor --help >/dev/null; \
    npm cache clean --force

WORKDIR /app

COPY requirements.txt ./
# Registry dependencies use the configured mirror with official PyPI as the
# fallback for the downstream SDK. Every selected archive must match the
# hashes exported from uv.lock; a mirror cannot substitute different bytes.
RUN python -m pip install --no-cache-dir --timeout 180 --retries 10 \
    --require-hashes \
    --extra-index-url https://pypi.org/simple \
    -r requirements.txt; \
    python -c "from importlib import metadata as m; import claude_agent_sdk as sdk; from claude_agent_sdk._cli_version import __cli_version__; dist=m.distribution('ink-claude-dream-agent-sdk'); providers={name.lower().replace('_','-') for name in m.packages_distributions().get('claude_agent_sdk', [])}; installed={str(item.metadata.get('Name') or '').lower().replace('_','-') for item in m.distributions()}; assert dist.version == '0.2.144'; assert sdk.__version__ == '0.2.144'; assert __cli_version__ == '2.1.241'; assert providers == {'ink-claude-dream-agent-sdk'}; assert 'claude-agent-sdk' not in installed; assert all(hasattr(sdk, name) for name in ('ClaudeAgentOptions', 'ClaudeSDKClient', 'query'))"

COPY . .

# Exercise the same fail-closed resolver used by Agent turns and MCP
# management. This proves the installed selector, release manifest and
# capability evidence are mutually compatible before the image is emitted.
RUN python -c "from libs.claude_agent_kit.server.sdk_env import resolve_claude_cli_path; path=resolve_claude_cli_path({'PATH':'/usr/local/bin:/usr/bin:/bin'}); assert path and path.endswith('/ink-claude-code-dream'), path"

EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request,os; urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8765')+'/', timeout=3).read()"

# Use shell form so ${PORT} is expanded at runtime by Cloud Run.
CMD exec uvicorn server:app --host 0.0.0.0 --port ${PORT:-8765} --proxy-headers
