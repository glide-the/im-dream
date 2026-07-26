# [Input] Consume backend source tree and requirements.txt during container builds.
# [Output] Build the Ink & Memory FastAPI runtime image served by uvicorn on port 8765.
# [Pos] deployment image spec in backend/
# [Sync] 2026-06-03: rewrite based on Pawkeyland Dockerfile — python 3.10-bookworm,
#        pip mirror, Node.js + claude-code CLI, HEALTHCHECK, --proxy-headers.
# [Sync] 2026-06-12: add configurable Debian/PyPI/npm mirror build args for faster China builds.
# [Sync] 2026-06-14: install Claude Code Linux sandbox dependencies for Docker deployments.
# [Sync] 2026-06-17: ensure standard sbin directories exist for bubblewrap rootfs mounts.

FROM python:3.10-slim-bookworm

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
#   - curl jq git ripgrep: runtime utilities used by agent/tooling
#   - nodejs npm: required by @anthropic-ai/claude-code (Claude agent SDK)
#   - bubblewrap socat: Claude Code sandboxed Bash runtime on Linux
ARG CLAUDE_CODE_VERSION=2.1.108
# System deps:
#   - gcc / libffi / libssl / libjpeg / zlib: cryptography + Pillow
#   - curl jq git ripgrep: runtime utilities used by agent/tooling
#   - nodejs npm: required by @anthropic-ai/claude-code
#   - bubblewrap socat: Claude Code sandboxed Bash runtime on Linux
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
        curl \
        jq \
        git \
        ripgrep \
        ca-certificates \
        nodejs \
        npm \
        bubblewrap \
        socat; \
    mkdir -p /sbin /usr/sbin /usr/local/sbin; \
    rm -rf /var/lib/apt/lists/*

# Claude Code + sandbox-runtime.
# Patch apply-seccomp to passthrough to avoid nested userns / setgroups failure in Docker.
RUN set -eux; \
    npm config set registry "${NPM_REGISTRY}"; \
    npm install -g \
        "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}" \
        "@anthropic-ai/sandbox-runtime"; \
    APPLY_SECCOMP_ROOT="$(npm root -g)/@anthropic-ai/claude-code/vendor/seccomp"; \
    test -d "$APPLY_SECCOMP_ROOT"; \
    find "$APPLY_SECCOMP_ROOT" -type f -name apply-seccomp -print \
        -exec sh -c 'printf "%s\n" "#!/bin/sh" "exec \"\$@\"" > "$1"; chmod +x "$1"' sh {} \; ; \
    echo "Patched Claude Code apply-seccomp passthrough:"; \
    find "$APPLY_SECCOMP_ROOT" -type f -name apply-seccomp -print -exec head -n 2 {} \; ; \
    npm cache clean --force

WORKDIR /app

COPY requirements.txt ./
# Use aliyun mirror as primary, PyPI as fallback for packages not yet mirrored
# (e.g. claude-agent-sdk, the renamed claude-code-sdk successor package).
RUN python -m pip install --no-cache-dir --timeout 180 --retries 10 \
    --extra-index-url http://mirrors.cloud.aliyuncs.com \
    -r requirements.txt

COPY . .

EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request,os; urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8765')+'/', timeout=3).read()"

# Use shell form so ${PORT} is expanded at runtime by Cloud Run.
CMD exec uvicorn server:app --host 0.0.0.0 --port ${PORT:-8765} --proxy-headers
