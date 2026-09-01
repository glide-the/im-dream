#!/usr/bin/env bash
# [Input] AutoDL SSH settings, generated Dream env, Dream source, and a qualified Linux x64 Runtime package built from authorized 2.1.88 source.
# [Output] Versioned direct-host Dream release using the restored 2.1.88 local-core Runtime and screen.
# [Pos] Dream AutoDL release entry; deliberately excludes Docker and nginx.
# [Sync] 2026-08-26: run Dream as root so /root-hosted workspace protocol paths remain fully traversable.
# [Sync] 2026-08-28: install and verify ntn 0.15.1 beside the backend-owned
#                    Notion Skill/MCP on the direct-host topology.
# [Sync] 2026-08-30: install qualified Runtime 0.1.4, built from authorized
#                    2.1.88 local-core with its restored on-disk
#                    vendor/seccomp apply-seccomp passthrough.
# [Sync] 2026-08-31: fail every start/deploy/verify/rollback when Vite Preview
#                    serves SPA HTML instead of FastAPI crawler files.
# [Sync] 2026-09-01: verify the production skill-creator package through a
#                    real isolated workspace init on every release lifecycle.
# [Sync] 2026-09-01: import the FastAPI application with the generated runtime
#                    env before switching current, catching undeclared runtime
#                    dependencies while the old release is still serving.
# [Sync] 2026-09-01: honor the explicit AutoDL Vite allow-all host policy during
#                    the production frontend build as well as env projection.
# [Sync] 2026-09-01: follow the namespaced builtin Skill source layout while
#                    retaining flat workspace/Runtime discovery verification.
# [Sync] 2026-09-01: advance the qualified rollback pointer only after all
#                    release gates pass; failed current releases are never reused.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
AUTODL_PLATFORM_ENV_FILE="${AUTODL_PLATFORM_ENV_FILE:-${SCRIPT_DIR}/platform.env}"
if [[ -f "${AUTODL_PLATFORM_ENV_FILE}" ]]; then
  # shellcheck disable=SC1090 -- the operator explicitly selects this local platform file.
  source "${AUTODL_PLATFORM_ENV_FILE}"
fi
AUTODL_SSH_HOST="${AUTODL_SSH_HOST:-}"
AUTODL_SSH_USER="${AUTODL_SSH_USER:-root}"
AUTODL_SSH_PORT="${AUTODL_SSH_PORT:-22}"
AUTODL_SSH_KEY="${AUTODL_SSH_KEY:-}"
AUTODL_SSH_CONTROL_PATH="${AUTODL_SSH_CONTROL_PATH:-}"
AUTODL_APP_ROOT="${AUTODL_APP_ROOT:-/root/ink-autodl/dream}"
AUTODL_DATA_ROOT="${AUTODL_DATA_ROOT:-/root/autodl-tmp/ink-memory}"
AUTODL_STACK_START_SCRIPT="${AUTODL_STACK_START_SCRIPT:-/root/ink-autodl/start-ink-memory.sh}"
AUTODL_DATA_INIT_SCRIPT="${AUTODL_DATA_INIT_SCRIPT:-/root/ink-autodl/init-dream-data.sh}"
AUTODL_PLUGIN_RUNTIME_ROOT="${AUTODL_DATA_ROOT}/claude-plugin-runtime"
AUTODL_PLUGIN_ARTIFACTS_SOURCE="${AUTODL_PLUGIN_ARTIFACTS_SOURCE:-${REPO_ROOT}/backend/data/claude-plugin-runtime/artifacts}"
AUTODL_CLAUDE_RUNTIME_REPOSITORY="${AUTODL_CLAUDE_RUNTIME_REPOSITORY:-${REPO_ROOT}/../ink-claude-code-dream}"
AUTODL_CLAUDE_RUNTIME_PACKAGE_ROOT="${AUTODL_CLAUDE_RUNTIME_PACKAGE_ROOT:-${AUTODL_CLAUDE_RUNTIME_REPOSITORY}/dist/core-package-linux-x64/ink-claude-code-dream-0.1.4}"
AUTODL_CLAUDE_REMOTE_BUILD_ROOT="${AUTODL_CLAUDE_REMOTE_BUILD_ROOT:-${AUTODL_APP_ROOT}/runtime-build}"
AUTODL_CLAUDE_REMOTE_PACKAGE_ROOT="${AUTODL_CLAUDE_REMOTE_PACKAGE_ROOT:-${AUTODL_CLAUDE_REMOTE_BUILD_ROOT}/qualified-package}"
AUTODL_ENV_FILE="${AUTODL_ENV_FILE:-${SCRIPT_DIR}/.env}"
AUTODL_SERVICE_USER="${AUTODL_SERVICE_USER:-root}"
AUTODL_NODE_VERSION="${AUTODL_NODE_VERSION:-22.18.0}"
AUTODL_NOTION_CLI_VERSION="${AUTODL_NOTION_CLI_VERSION:-0.15.1}"
AUTODL_PYTHON="${AUTODL_PYTHON:-/root/miniconda3/bin/python}"
AUTODL_DREAM_FRONTEND_PORT="${AUTODL_DREAM_FRONTEND_PORT:-${AUTODL_DREAM_PORT:-6006}}"
AUTODL_DREAM_BACKEND_PORT="${AUTODL_DREAM_BACKEND_PORT:-8765}"
AUTODL_ADMIN_PORT="${AUTODL_ADMIN_PORT:-6008}"
AUTODL_DREAM_PUBLIC_ORIGIN="${AUTODL_DREAM_PUBLIC_ORIGIN:-}"
AUTODL_VITE_ALLOWED_HOSTS="${AUTODL_VITE_ALLOWED_HOSTS:-}"
AUTODL_SCREEN_NAME="${AUTODL_DREAM_SCREEN_NAME:-ink-dream}"
AUTODL_NPM_TOKEN="${AUTODL_NPM_TOKEN:-}"
AUTODL_NPM_REGISTRY="${AUTODL_NPM_REGISTRY:-https://registry.npmjs.org}"
AUTODL_PYPI_INDEX_URL="${AUTODL_PYPI_INDEX_URL:-https://mirrors.aliyun.com/pypi/simple/}"
DRY_RUN=0
COMMAND=""

log() { printf '[dream-autodl] %s\n' "$*"; }
warn() { printf '[warn] %s\n' "$*" >&2; }
err() { printf '[error] %s\n' "$*" >&2; exit 1; }
quote() { printf '%q' "$1"; }
dream_public_host() {
  local host="${AUTODL_DREAM_PUBLIC_ORIGIN#https://}"
  printf '%s\n' "${host%%:*}"
}
vite_allowed_hosts() {
  if [[ "${AUTODL_VITE_ALLOWED_HOSTS}" == "*" ]]; then
    printf '*\n'
  else
    dream_public_host
  fi
}

usage() {
  cat <<'EOF'
Usage: ./deploy/autodl-ssh/deploy.sh [--dry-run] <command>

Commands:
  check      Validate local files, SSH, Admin availability, and target identity.
  plan       Print the direct-host Dream release sequence and URL mappings.
  sync       Rsync frontend/backend source and generated runtime env.
  build      Install prerequisites and build a versioned frontend/backend release.
  deploy     Build, restart only the Dream stack, and verify local/public health.
  start|stop|status|logs|verify|rollback

AUTODL_NPM_TOKEN is optional. When present it is transferred only through a
temporary mode-0600 npmrc and deleted immediately after package installation.
EOF
}

ssh_args() {
  SSH_ARGS=(-p "${AUTODL_SSH_PORT}" -o BatchMode=yes)
  [[ -n "${AUTODL_SSH_KEY}" ]] && SSH_ARGS+=(-i "${AUTODL_SSH_KEY}")
  [[ -n "${AUTODL_SSH_CONTROL_PATH}" ]] && SSH_ARGS+=(-o "ControlPath=${AUTODL_SSH_CONTROL_PATH}")
}

ssh_target() { printf '%s@%s\n' "${AUTODL_SSH_USER}" "${AUTODL_SSH_HOST:-AUTODL_SSH_HOST}"; }

remote() {
  local command="$1"
  ssh_args
  if [[ "${DRY_RUN}" == "1" ]]; then
    printf '[dry-run] ssh'; printf ' %q' "${SSH_ARGS[@]}" "$(ssh_target)" "${command}"; printf '\n'
  else
    ssh "${SSH_ARGS[@]}" "$(ssh_target)" "${command}"
  fi
}

scp_file() {
  local source="$1" target="$2"
  local args=(-P "${AUTODL_SSH_PORT}" -o BatchMode=yes)
  [[ -n "${AUTODL_SSH_KEY}" ]] && args+=(-i "${AUTODL_SSH_KEY}")
  [[ -n "${AUTODL_SSH_CONTROL_PATH}" ]] && args+=(-o "ControlPath=${AUTODL_SSH_CONTROL_PATH}")
  if [[ "${DRY_RUN}" == "1" ]]; then
    printf '[dry-run] scp'; printf ' %q' "${args[@]}" "${source}" "$(ssh_target):${target}"; printf '\n'
  else
    scp "${args[@]}" "${source}" "$(ssh_target):${target}"
  fi
}

require_config() {
  [[ -n "${AUTODL_SSH_HOST}" ]] || err "AUTODL_SSH_HOST is required."
  [[ "${AUTODL_DREAM_PUBLIC_ORIGIN}" =~ ^https://[^/]+(:[0-9]+)?$ ]] || err "AUTODL_DREAM_PUBLIC_ORIGIN must be an exact HTTPS origin."
  [[ "${AUTODL_SSH_USER}" == "root" ]] || err "AutoDL setup currently requires the root SSH account."
  [[ "${AUTODL_SERVICE_USER}" == "root" ]] || err "AutoDL Dream must run as root when its runtime and workspace live under /root."
  [[ "${AUTODL_APP_ROOT}" == /root/* && "${AUTODL_DATA_ROOT}" == /root/* ]] || err "AutoDL paths must stay under /root."
  [[ "${AUTODL_STACK_START_SCRIPT}" == /root/ink-autodl/* ]] || err "AutoDL stack start script must stay under /root/ink-autodl."
  [[ "${AUTODL_CLAUDE_REMOTE_BUILD_ROOT}" == "${AUTODL_APP_ROOT}"/* ]] || err "Claude Runtime build root must stay under AUTODL_APP_ROOT."
  [[ "${AUTODL_CLAUDE_REMOTE_PACKAGE_ROOT}" == "${AUTODL_CLAUDE_REMOTE_BUILD_ROOT}"/* ]] || err "Claude Runtime package root must stay under its build root."
  [[ "${AUTODL_DREAM_FRONTEND_PORT}" == "6006" && "${AUTODL_DREAM_BACKEND_PORT}" == "8765" && "${AUTODL_ADMIN_PORT}" == "6008" ]] || err "AutoDL must use Dream frontend 6006, backend 8765, and Admin 6008."
}

check_local() {
  local failed=0 mode
  for name in ssh scp rsync git; do command -v "${name}" >/dev/null 2>&1 || { warn "Missing local command: ${name}"; failed=1; }; done
  for file in "${AUTODL_ENV_FILE}" "${SCRIPT_DIR}/runtime/start-dream.sh" "${SCRIPT_DIR}/runtime/start-ink-memory.sh" "${SCRIPT_DIR}/runtime/init-dream-data.sh" "${REPO_ROOT}/backend/requirements.txt" "${REPO_ROOT}/frontend/package.json" "${REPO_ROOT}/frontend/package-lock.json" "${REPO_ROOT}/frontend/vite.config.ts"; do
    [[ -f "${file}" ]] || { warn "Missing file: ${file}"; failed=1; }
  done
  for directory in "${AUTODL_CLAUDE_RUNTIME_REPOSITORY}" "${AUTODL_CLAUDE_RUNTIME_PACKAGE_ROOT}"; do
    [[ -d "${directory}" ]] || { warn "Missing Claude Runtime build input: ${directory}"; failed=1; }
  done
  for file in "${AUTODL_CLAUDE_RUNTIME_REPOSITORY}/scripts/verify-core-package-local.mjs" "${AUTODL_CLAUDE_RUNTIME_REPOSITORY}/runtime/local-artifact-policy.json" "${AUTODL_CLAUDE_RUNTIME_PACKAGE_ROOT}/release-manifest.json" "${AUTODL_CLAUDE_RUNTIME_PACKAGE_ROOT}/lib/core/chunks/vendor/seccomp/x64/apply-seccomp" "${AUTODL_CLAUDE_RUNTIME_PACKAGE_ROOT}/lib/core/chunks/vendor/seccomp/x64/unix-block.bpf"; do
    [[ -f "${file}" ]] || { warn "Missing Claude Runtime build file: ${file}"; failed=1; }
  done
  if [[ "${failed}" == "0" ]]; then
    node "${AUTODL_CLAUDE_RUNTIME_REPOSITORY}/scripts/verify-core-package-local.mjs" --package-root "${AUTODL_CLAUDE_RUNTIME_PACKAGE_ROOT}" >/dev/null || { warn "Claude Runtime package verification failed."; failed=1; }
    jq -e '.status.productionEligible == true and .core.productionEligible == true and .core.sourceVersionEvidence == "2.1.88" and .core.cliCompatibilityVersion == "2.1.241" and .core.runtimeTarget == "linux-x64"' "${AUTODL_CLAUDE_RUNTIME_PACKAGE_ROOT}/release-manifest.json" >/dev/null || { warn "Claude Runtime package identity/qualification failed."; failed=1; }
  fi
  if [[ -f "${AUTODL_ENV_FILE}" ]]; then
    mode="$(stat -f '%Lp' "${AUTODL_ENV_FILE}" 2>/dev/null || stat -c '%a' "${AUTODL_ENV_FILE}")"
    [[ "${mode}" == "640" || "${mode}" == "600" ]] || { warn "${AUTODL_ENV_FILE} must be mode 600 or 640, got ${mode}."; failed=1; }
  fi
  [[ "${failed}" == "0" ]]
}

check_remote() {
  remote "set -e; test \"\$(id -u)\" = 0; test -x $(quote "${AUTODL_PYTHON}"); test -d /root/autodl-tmp; command -v curl >/dev/null; command -v rsync >/dev/null; command -v screen >/dev/null; curl -fsS --max-time 5 http://127.0.0.1:${AUTODL_ADMIN_PORT}/admin/login >/dev/null"
}

command_check() { require_config; check_local; check_remote; log "AutoDL Dream prerequisites, Admin, and target identity are valid."; }

command_plan() {
  cat <<EOF
AutoDL Dream direct-host release:
  SSH target:      $(ssh_target):${AUTODL_APP_ROOT}
  Dream mapping:   http://127.0.0.1:${AUTODL_DREAM_FRONTEND_PORT} (Vite Preview) -> ${AUTODL_DREAM_PUBLIC_ORIGIN:-<required>}
  API upstream:    http://127.0.0.1:${AUTODL_DREAM_BACKEND_PORT} (FastAPI, private)
  Admin upstream:  http://127.0.0.1:${AUTODL_ADMIN_PORT}
  data:            ${AUTODL_DATA_ROOT}
  runtime:         Miniconda Python 3.12 + Node ${AUTODL_NODE_VERSION} + screen
  Claude pair:     ink-claude-dream-agent-sdk 0.2.144 + qualified 2.1.88 local-core (CLI compatibility 2.1.241)
  seccomp helper:  vendor path contains the checksum-bound Docker-style passthrough
  Notion CLI:      ntn ${AUTODL_NOTION_CLI_VERSION}
  excluded:        Docker, nginx, database migration
EOF
}

setup_host() {
  log "Installing direct-host dependencies and fixed Node/Claude runtimes."
  remote "set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update >/dev/null
apt-get install -y --no-install-recommends ca-certificates curl xz-utils acl passwd screen jq iproute2 ripgrep bubblewrap socat gcc libffi-dev libssl-dev libjpeg-dev zlib1g-dev >/dev/null
install -d -m 0750 $(quote "${AUTODL_APP_ROOT}") $(quote "${AUTODL_APP_ROOT}/source") $(quote "${AUTODL_APP_ROOT}/releases") $(quote "${AUTODL_APP_ROOT}/config")
install -d -o root -g root -m 0750 $(quote "${AUTODL_APP_ROOT}/run") $(quote "${AUTODL_APP_ROOT}/logs")
chgrp root $(quote "${AUTODL_APP_ROOT}/config")
chmod 0750 $(quote "${AUTODL_APP_ROOT}/config")
node_root=/root/ink-autodl/runtime/node-v${AUTODL_NODE_VERSION}-linux-x64
if [ ! -x \"\${node_root}/bin/node\" ]; then
  install -d /root/ink-autodl/runtime
  archive=/root/ink-autodl/runtime/node-v${AUTODL_NODE_VERSION}-linux-x64.tar.xz
  curl -fsSL --retry 5 -o \"\${archive}\" https://nodejs.org/dist/v${AUTODL_NODE_VERSION}/node-v${AUTODL_NODE_VERSION}-linux-x64.tar.xz
  tar -xJf \"\${archive}\" -C /root/ink-autodl/runtime
  rm -f \"\${archive}\"
fi
ln -sfn \"\${node_root}\" /root/ink-autodl/runtime/node
install -d /root/ink-autodl/runtime/npm
/root/ink-autodl/runtime/node/bin/node --version"
}

sync_plugin_artifacts() {
  local transport="ssh -p $(quote "${AUTODL_SSH_PORT}") -o BatchMode=yes"
  [[ -n "${AUTODL_SSH_KEY}" ]] && transport+=" -i $(quote "${AUTODL_SSH_KEY}")"
  [[ -n "${AUTODL_SSH_CONTROL_PATH}" ]] && transport+=" -o ControlPath=$(quote "${AUTODL_SSH_CONTROL_PATH}")"

  remote "set -e; group=\$(id -gn $(quote "${AUTODL_SERVICE_USER}")); install -d -o $(quote "${AUTODL_SERVICE_USER}") -g \"\${group}\" -m 0750 $(quote "${AUTODL_PLUGIN_RUNTIME_ROOT}") $(quote "${AUTODL_PLUGIN_RUNTIME_ROOT}/config") $(quote "${AUTODL_PLUGIN_RUNTIME_ROOT}/install-workspace") $(quote "${AUTODL_PLUGIN_RUNTIME_ROOT}/artifacts") $(quote "${AUTODL_PLUGIN_RUNTIME_ROOT}/operations")"
  if [[ -d "${AUTODL_PLUGIN_ARTIFACTS_SOURCE}" ]]; then
    local args=(-az -e "${transport}")
    log "Seeding immutable Claude plugin artifacts into the persistent data root."
    if [[ "${DRY_RUN}" == "1" ]]; then
      printf '[dry-run] rsync'; printf ' %q' "${args[@]}" "${AUTODL_PLUGIN_ARTIFACTS_SOURCE}/" "$(ssh_target):${AUTODL_PLUGIN_RUNTIME_ROOT}/artifacts/"; printf '\n'
    else
      rsync "${args[@]}" "${AUTODL_PLUGIN_ARTIFACTS_SOURCE}/" "$(ssh_target):${AUTODL_PLUGIN_RUNTIME_ROOT}/artifacts/"
    fi
  else
    log "No local artifact seed selected; preserving the persistent remote artifact store."
  fi
  remote "set -e; test -n \"\$(find $(quote "${AUTODL_PLUGIN_RUNTIME_ROOT}/artifacts") -mindepth 1 -maxdepth 1 -type d -print -quit)\"; group=\$(id -gn $(quote "${AUTODL_SERVICE_USER}")); chown -R $(quote "${AUTODL_SERVICE_USER}"):\"\${group}\" $(quote "${AUTODL_PLUGIN_RUNTIME_ROOT}")"
}

configure_npm_auth() {
  [[ -n "${AUTODL_NPM_TOKEN}" ]] || return 0
  local temp_file
  temp_file="$(mktemp "${TMPDIR:-/tmp}/ink-autodl-npmrc.XXXXXX")"
  trap 'rm -f "${temp_file}"' RETURN
  umask 077
  printf '//registry.npmjs.org/:_authToken=%s\nalways-auth=true\n' "${AUTODL_NPM_TOKEN}" >"${temp_file}"
  chmod 600 "${temp_file}"
  scp_file "${temp_file}" "${AUTODL_APP_ROOT}/config/npmrc.install"
  remote "chmod 0600 $(quote "${AUTODL_APP_ROOT}/config/npmrc.install")"
  rm -f "${temp_file}"; trap - RETURN
}

install_claude_runtime() {
  configure_npm_auth
  remote "set -euo pipefail
prefix=/root/ink-autodl/runtime/npm
export PATH="\${prefix}/bin:/root/ink-autodl/runtime/node/bin:\$PATH"
runtime_repo=$(quote "${AUTODL_CLAUDE_REMOTE_BUILD_ROOT}/ink-claude-code-dream")
package_root=$(quote "${AUTODL_CLAUDE_REMOTE_PACKAGE_ROOT}")
bun_prefix=/root/ink-autodl/runtime/bun-1.4.0
npmrc=$(quote "${AUTODL_APP_ROOT}/config/npmrc.install")
cleanup() { rm -f \"\${npmrc}\"; }
trap cleanup EXIT
npm_args=(--prefix \"\${prefix}\" --registry $(quote "${AUTODL_NPM_REGISTRY}"))
if [ -f \"\${npmrc}\" ]; then npm_args+=(--userconfig \"\${npmrc}\"); fi
npm install --prefix \"\${bun_prefix}\" --registry $(quote "${AUTODL_NPM_REGISTRY}") bun@1.4.0
bun_bin=\"\${bun_prefix}/node_modules/.bin/bun\"
test \"\$(\"\${bun_bin}\" --version)\" = '1.4.0'
chown -R root:root \"\${runtime_repo}\" \"\${package_root}\"
node \"\${runtime_repo}/scripts/verify-core-package-local.mjs\" --package-root \"\${package_root}\" >/dev/null
manifest=\"\${package_root}/release-manifest.json\"
jq -e '.runtime.version == \"0.1.4\" and .runtime.integration.sdkVersion == \"0.2.144\" and .core.corePruned == true and .core.productionEligible == true and .status.productionEligible == true and .core.sourceVersionEvidence == \"2.1.88\" and .core.cliCompatibilityVersion == \"2.1.241\" and .core.runtimeTarget == \"linux-x64\"' \"\${manifest}\" >/dev/null
apply_seccomp=\"\${package_root}/lib/core/chunks/vendor/seccomp/x64/apply-seccomp\"
bpf=\"\${package_root}/lib/core/chunks/vendor/seccomp/x64/unix-block.bpf\"
test \"\$(sha256sum \"\${apply_seccomp}\" | awk '{print \$1}')\" = 'bd2923ee44c624e03bac9efb57c84d72419726783ac7557acb708e431c16d74d'
test -x \"\${apply_seccomp}\" && test -s \"\${bpf}\"
core_digest=\$(jq -r '.core.coreBundleSha256' \"\${manifest}\")
runtime_package=\"\${prefix}/share/ink-claude-code-dream/releases/0.1.4-\${core_digest:0:16}\"
if [ ! -d \"\${runtime_package}\" ]; then
  install -d -m 0755 \"\$(dirname \"\${runtime_package}\")\"
  stage=\"\${runtime_package}.stage.\$\$\"
  cp -a \"\${package_root}\" \"\${stage}\"
  node \"\${runtime_repo}/scripts/verify-core-package-local.mjs\" --package-root \"\${stage}\" >/dev/null
  mv \"\${stage}\" \"\${runtime_package}\"
else
  node \"\${runtime_repo}/scripts/verify-core-package-local.mjs\" --package-root \"\${runtime_package}\" >/dev/null
fi
for link in ink-claude-code-dream ink-claude-code-bun-1.4.0; do
  target=\"\${prefix}/bin/\${link}\"
  if [ -e \"\${target}\" ] || [ -L \"\${target}\" ]; then
    test -L \"\${target}\" && unlink \"\${target}\" || { echo \"refusing non-symlink Runtime target: \${target}\" >&2; exit 1; }
  fi
done
ln -s \"\${runtime_package}/bin/ink-claude-code-dream\" \"\${prefix}/bin/ink-claude-code-dream\"
ln -s \"\${bun_bin}\" \"\${prefix}/bin/ink-claude-code-bun-1.4.0\"
test \"\$(\"\${prefix}/bin/ink-claude-code-dream\" --version)\" = '2.1.241 (Claude Code)'
npm install -g \"\${npm_args[@]}\" @anthropic-ai/claude-code@2.1.241
test \"\$(\"\${prefix}/bin/claude\" --version | awk '{print \$1}')\" = '2.1.241'
npm install -g \"\${npm_args[@]}\" ntn@$(quote "${AUTODL_NOTION_CLI_VERSION}")
test \"\$(\"\${prefix}/bin/ntn\" --version)\" = $(quote "ntn ${AUTODL_NOTION_CLI_VERSION}")
\"\${prefix}/bin/ntn\" login --help | grep -F -- '--no-browser'
\"\${prefix}/bin/ntn\" doctor --help >/dev/null
cleanup
trap - EXIT"
}

sync_files() {
  require_config; check_local
  remote "install -d -m 0750 $(quote "${AUTODL_APP_ROOT}/source") $(quote "${AUTODL_APP_ROOT}/config") $(quote "${AUTODL_CLAUDE_REMOTE_BUILD_ROOT}/ink-claude-code-dream") $(quote "${AUTODL_CLAUDE_REMOTE_PACKAGE_ROOT}")"
  local transport="ssh -p $(quote "${AUTODL_SSH_PORT}") -o BatchMode=yes"
  [[ -n "${AUTODL_SSH_KEY}" ]] && transport+=" -i $(quote "${AUTODL_SSH_KEY}")"
  [[ -n "${AUTODL_SSH_CONTROL_PATH}" ]] && transport+=" -o ControlPath=$(quote "${AUTODL_SSH_CONTROL_PATH}")"
  local args=(-az --delete --exclude '/.git/' --exclude '/.env*' --exclude '/.venv*/' --exclude '/.artifacts/' --exclude '/.codex-pet-runs/' --exclude '/output/' --exclude '/backend/.env' --exclude '/backend/.venv*/' --exclude '/backend/data/' --exclude '/frontend/node_modules/' --exclude '/frontend/dist/' --exclude '/node_modules/' --exclude '/test-results/' --exclude '/playwright-report/' --exclude '/deploy/remote-ssh/.env' --exclude '/deploy/autodl-ssh/.env' -e "${transport}")
  log "Syncing Dream source without runtime secrets or mutable local data."
  if [[ "${DRY_RUN}" == "1" ]]; then printf '[dry-run] rsync'; printf ' %q' "${args[@]}" "${REPO_ROOT}/" "$(ssh_target):${AUTODL_APP_ROOT}/source/"; printf '\n';
  else rsync "${args[@]}" "${REPO_ROOT}/" "$(ssh_target):${AUTODL_APP_ROOT}/source/"; fi
  local runtime_args=(-az --delete --exclude '/.git/' --exclude '/.env*' --exclude '/node_modules/' --exclude '/dist/' -e "${transport}")
  local package_args=(-az --delete --exclude '/.DS_Store' -e "${transport}")
  log "Syncing the Runtime verifier and Docker-qualified Linux x64 package."
  if [[ "${DRY_RUN}" == "1" ]]; then
    printf '[dry-run] rsync'; printf ' %q' "${runtime_args[@]}" "${AUTODL_CLAUDE_RUNTIME_REPOSITORY}/" "$(ssh_target):${AUTODL_CLAUDE_REMOTE_BUILD_ROOT}/ink-claude-code-dream/"; printf '\n'
    printf '[dry-run] rsync'; printf ' %q' "${package_args[@]}" "${AUTODL_CLAUDE_RUNTIME_PACKAGE_ROOT}/" "$(ssh_target):${AUTODL_CLAUDE_REMOTE_PACKAGE_ROOT}/"; printf '\n'
  else
    rsync "${runtime_args[@]}" "${AUTODL_CLAUDE_RUNTIME_REPOSITORY}/" "$(ssh_target):${AUTODL_CLAUDE_REMOTE_BUILD_ROOT}/ink-claude-code-dream/"
    rsync "${package_args[@]}" "${AUTODL_CLAUDE_RUNTIME_PACKAGE_ROOT}/" "$(ssh_target):${AUTODL_CLAUDE_REMOTE_PACKAGE_ROOT}/"
  fi
  remote "set -e; install -o root -g root -m 0755 $(quote "${AUTODL_APP_ROOT}/source/deploy/autodl-ssh/runtime/start-ink-memory.sh") $(quote "${AUTODL_STACK_START_SCRIPT}"); install -o root -g root -m 0755 $(quote "${AUTODL_APP_ROOT}/source/deploy/autodl-ssh/runtime/init-dream-data.sh") $(quote "${AUTODL_DATA_INIT_SCRIPT}"); INK_AUTODL_DATA_ROOT=$(quote "${AUTODL_DATA_ROOT}") INK_AUTODL_SERVICE_USER=$(quote "${AUTODL_SERVICE_USER}") $(quote "${AUTODL_DATA_INIT_SCRIPT}")"
  sync_plugin_artifacts
  scp_file "${AUTODL_ENV_FILE}" "${AUTODL_APP_ROOT}/config/dream.env.next"
  remote "set -e; group=\$(id -gn $(quote "${AUTODL_SERVICE_USER}")); chown root:\"\${group}\" $(quote "${AUTODL_APP_ROOT}/config/dream.env.next"); chmod 0640 $(quote "${AUTODL_APP_ROOT}/config/dream.env.next"); mv -f $(quote "${AUTODL_APP_ROOT}/config/dream.env.next") $(quote "${AUTODL_APP_ROOT}/config/dream.env")"
}

build_release() {
  local release_id
  release_id="$(git -C "${REPO_ROOT}" rev-parse --short=12 HEAD)"
  log "Building Dream release ${release_id} on AutoDL."
  install_claude_runtime
  remote "set -euo pipefail
staging=$(quote "${AUTODL_APP_ROOT}/releases/${release_id}.staging")
release=$(quote "${AUTODL_APP_ROOT}/releases/${release_id}")
rm -rf \"\${staging}\"
install -d \"\${staging}/app\" \"\${staging}/frontend\"
$(quote "${AUTODL_PYTHON}") -m venv \"\${staging}/venv\"
\"\${staging}/venv/bin/python\" -m pip install --upgrade pip >/dev/null
PIP_INDEX_URL=$(quote "${AUTODL_PYPI_INDEX_URL}") PIP_DEFAULT_TIMEOUT=180 PIP_RETRIES=10 \"\${staging}/venv/bin/python\" -m pip install --require-hashes --extra-index-url https://pypi.org/simple -r $(quote "${AUTODL_APP_ROOT}/source/backend/requirements.txt")
rsync -a --exclude '.env' --exclude '.venv*' --exclude 'data/' $(quote "${AUTODL_APP_ROOT}/source/backend/") \"\${staging}/app/\"
rsync -a --exclude '.env*' --exclude 'node_modules/' --exclude 'dist/' $(quote "${AUTODL_APP_ROOT}/source/frontend/") \"\${staging}/frontend/\"
cp $(quote "${AUTODL_APP_ROOT}/source/deploy/autodl-ssh/runtime/start-dream.sh") \"\${staging}/start-dream.sh\"
chmod 0755 \"\${staging}/start-dream.sh\"
export PATH=/root/ink-autodl/runtime/node/bin:\$PATH
cd \"\${staging}/frontend\"
npm ci --no-audit --no-fund --registry $(quote "${AUTODL_NPM_REGISTRY}")
NODE_OPTIONS=--max-old-space-size=4096 VITE_PUBLIC_SITE_URL=$(quote "${AUTODL_DREAM_PUBLIC_ORIGIN%/}/") VITE_DEV_API_PROXY_TARGET=http://127.0.0.1:${AUTODL_DREAM_BACKEND_PORT} VITE_ALLOWED_HOSTS=$(quote "$(vite_allowed_hosts)") npm run build
test -s \"\${staging}/frontend/dist/index.html\"
cd \"\${staging}/app\"
PATH=/root/ink-autodl/runtime/npm/bin:/root/ink-autodl/runtime/node/bin:\$PATH \"\${staging}/venv/bin/python\" -c \"from importlib import metadata as m; import claude_agent_sdk as sdk; assert m.version('ink-claude-dream-agent-sdk') == '0.2.144'; assert sdk.__version__ == '0.2.144'\"
PATH=/root/ink-autodl/runtime/npm/bin:/root/ink-autodl/runtime/node/bin:\$PATH \"\${staging}/venv/bin/python\" -c \"from libs.claude_agent_kit.server.sdk_env import resolve_claude_cli_path; assert resolve_claude_cli_path().endswith('/ink-claude-code-dream')\"
PATH=/root/ink-autodl/runtime/npm/bin:/root/ink-autodl/runtime/node/bin:\$PATH \"\${staging}/venv/bin/python\" -c \"import os; from dotenv import dotenv_values; os.environ.update({key: value for key, value in dotenv_values('$(quote "${AUTODL_APP_ROOT}/config/dream.env")').items() if value is not None}); import server\"
test \"\$(/root/ink-autodl/runtime/npm/bin/ntn --version)\" = $(quote "ntn ${AUTODL_NOTION_CLI_VERSION}")
rm -rf \"\${release}\"
mv \"\${staging}\" \"\${release}\"
chown -R $(quote "${AUTODL_SERVICE_USER}"):$(quote "${AUTODL_SERVICE_USER}") \"\${release}\"
rollback_source=''
if [ -L $(quote "${AUTODL_APP_ROOT}/qualified") ]; then
  rollback_source=\"\$(readlink -f $(quote "${AUTODL_APP_ROOT}/qualified"))\"
elif [ -L $(quote "${AUTODL_APP_ROOT}/current") ]; then
  rollback_source=\"\$(readlink -f $(quote "${AUTODL_APP_ROOT}/current"))\"
fi
if [ -n \"\${rollback_source}\" ]; then test -d \"\${rollback_source}\"; ln -sfn \"\${rollback_source}\" $(quote "${AUTODL_APP_ROOT}/previous"); fi
ln -sfn \"\${release}\" $(quote "${AUTODL_APP_ROOT}/current")"
}

stop_dream() {
  remote "set -e; pid_file=$(quote "${AUTODL_APP_ROOT}/run/dream.pid"); if [ -f \"\${pid_file}\" ]; then pid=\$(cat \"\${pid_file}\"); if echo \"\${pid}\" | grep -Eq '^[0-9]+$' && kill -0 \"\${pid}\" 2>/dev/null; then kill -TERM \"\${pid}\"; for _ in \$(seq 1 60); do kill -0 \"\${pid}\" 2>/dev/null || break; sleep 1; done; kill -0 \"\${pid}\" 2>/dev/null && kill -KILL \"\${pid}\" || true; fi; rm -f \"\${pid_file}\"; fi; screen -S $(quote "${AUTODL_SCREEN_NAME}") -X quit >/dev/null 2>&1 || true"
}

start_dream() {
  remote "set -euo pipefail
INK_AUTODL_DATA_ROOT=$(quote "${AUTODL_DATA_ROOT}") INK_AUTODL_SERVICE_USER=$(quote "${AUTODL_SERVICE_USER}") $(quote "${AUTODL_DATA_INIT_SCRIPT}")
test -L $(quote "${AUTODL_APP_ROOT}/current")
current=\$(readlink -f $(quote "${AUTODL_APP_ROOT}/current"))
env_file=$(quote "${AUTODL_APP_ROOT}/config/dream.env")
if [ ! -s \"\${current}/frontend/dist/index.html\" ]; then
  env_file=$(quote "${AUTODL_APP_ROOT}/config/dream.env.legacy")
  sed 's/^PORT=.*/PORT=${AUTODL_DREAM_FRONTEND_PORT}/' $(quote "${AUTODL_APP_ROOT}/config/dream.env") > \"\${env_file}.next\"
  group=\$(id -gn $(quote "${AUTODL_SERVICE_USER}"))
  chown root:\"\${group}\" \"\${env_file}.next\"
  chmod 0640 \"\${env_file}.next\"
  mv -f \"\${env_file}.next\" \"\${env_file}\"
fi
rm -f $(quote "${AUTODL_APP_ROOT}/run/dream.pid")
screen -S $(quote "${AUTODL_SCREEN_NAME}") -X quit >/dev/null 2>&1 || true
screen -dmS $(quote "${AUTODL_SCREEN_NAME}") -L -Logfile $(quote "${AUTODL_APP_ROOT}/logs/dream.log") bash -lc \"exec env HOME=$(quote "${AUTODL_DATA_ROOT}/service-home") INK_AUTODL_DATA_ROOT=$(quote "${AUTODL_DATA_ROOT}") AUTODL_DREAM_ENV_FILE=\${env_file} AUTODL_DREAM_PID_FILE=$(quote "${AUTODL_APP_ROOT}/run/dream.pid") AUTODL_DREAM_FRONTEND_PORT=${AUTODL_DREAM_FRONTEND_PORT} AUTODL_DREAM_BACKEND_PORT=${AUTODL_DREAM_BACKEND_PORT} AUTODL_NODE_BIN=/root/ink-autodl/runtime/node/bin AUTODL_NPM_BIN=/root/ink-autodl/runtime/npm/bin $(quote "${AUTODL_APP_ROOT}/current/start-dream.sh")\"
if [ -s \"\${current}/frontend/dist/index.html\" ]; then
  for _ in \$(seq 1 120); do
    curl -fsS --max-time 3 http://127.0.0.1:${AUTODL_DREAM_BACKEND_PORT}/api/health >/dev/null 2>&1 && curl -fsS --max-time 3 http://127.0.0.1:${AUTODL_DREAM_FRONTEND_PORT}/ >/dev/null 2>&1 && curl -fsS --max-time 3 http://127.0.0.1:${AUTODL_DREAM_FRONTEND_PORT}/api/health >/dev/null 2>&1 && exit 0
    sleep 1
  done
else
  for _ in \$(seq 1 120); do curl -fsS --max-time 3 http://127.0.0.1:${AUTODL_DREAM_FRONTEND_PORT}/api/health >/dev/null 2>&1 && exit 0; sleep 1; done
fi
tail -n 160 $(quote "${AUTODL_APP_ROOT}/logs/dream.log") >&2 || true
exit 1"
}

verify_default_plugin() {
  remote "set -e; current=\$(readlink -f $(quote "${AUTODL_APP_ROOT}/current")); cd \"\${current}/app\"; \"\${current}/venv/bin/python\" -c 'import os; from dotenv import dotenv_values; os.environ.update({key: value for key, value in dotenv_values(\"${AUTODL_APP_ROOT}/config/dream.env\").items() if value is not None}); from services.deck.defaults import resolve_default_deck_plugin_ref; resolve_default_deck_plugin_ref()'"
}

verify_builtin_skills() {
  remote "set -e; current=\$(readlink -f $(quote "${AUTODL_APP_ROOT}/current")); cd \"\${current}/app\"; \"\${current}/venv/bin/python\" -c 'import os, tempfile; from pathlib import Path; check = tempfile.TemporaryDirectory(prefix=\"ink-dream-skill-verify-\"); os.environ[\"AGENT_CWD\"] = check.name; from libs.claude_agent_kit.server.workspace import init_workspace; workspace = init_workspace(\"deploy-skill-verification\"); source = Path(\"builtin_skills/common/skill-creator/SKILL.md\"); installed = workspace / \"skills\" / \"skill-creator\" / \"SKILL.md\"; discovery = workspace / \".claude\" / \"skills\" / \"skill-creator\"; assert source.is_file() and \"name: skill-creator\" in source.read_text(encoding=\"utf-8\"); assert installed.is_file() and \"name: skill-creator\" in installed.read_text(encoding=\"utf-8\"); assert discovery.is_symlink() and discovery.resolve() == installed.parent.resolve(); from claude_agent.context_builder import _canonicalize_workspace_skill_command; assert _canonicalize_workspace_skill_command(\"/Skill-Creator verify\", str(workspace)) == \"/skill-creator verify\"; check.cleanup()'"
}

verify_seo_origin() {
  local origin="$1" label="$2" endpoint expected_type marker content_type body
  while IFS='|' read -r endpoint expected_type marker; do
    content_type="$(curl -fsS --retry 5 --retry-delay 2 --retry-connrefused --max-time 15 -o /dev/null -w '%{content_type}' "${origin%/}/${endpoint}")"
    [[ "${content_type}" == "${expected_type}"* ]] || err "${label} /${endpoint} returned ${content_type:-no content type}; expected ${expected_type}."
    body="$(curl -fsS --retry 5 --retry-delay 2 --retry-connrefused --max-time 15 "${origin%/}/${endpoint}")"
    [[ "${body}" == *"${marker}"* ]] || err "${label} /${endpoint} did not contain its required machine-readable marker."
    if printf '%s' "${body}" | grep -Eiq '<html'; then
      err "${label} /${endpoint} returned SPA HTML instead of the backend crawler file."
    fi
  done <<'EOF'
robots.txt|text/plain|User-agent:
sitemap.xml|application/xml|<urlset
llms.txt|text/plain|# Ink & Memory
EOF
}

verify() {
  local topology
  topology="$(remote "set -e; current=\$(readlink -f $(quote "${AUTODL_APP_ROOT}/current")); curl -fsS --max-time 10 http://127.0.0.1:${AUTODL_ADMIN_PORT}/admin/login >/dev/null; screen -ls | grep -q '[.]${AUTODL_SCREEN_NAME}[[:space:]]'; if [ -s \"\${current}/frontend/dist/index.html\" ]; then curl -fsS --max-time 10 http://127.0.0.1:${AUTODL_DREAM_FRONTEND_PORT}/ >/dev/null; curl -fsS --max-time 10 http://127.0.0.1:${AUTODL_DREAM_BACKEND_PORT}/api/health >/dev/null; curl -fsS --max-time 10 http://127.0.0.1:${AUTODL_DREAM_FRONTEND_PORT}/api/health >/dev/null; for endpoint in robots.txt sitemap.xml llms.txt; do content_type=\$(curl -fsS --max-time 10 -o /dev/null -w '%{content_type}' http://127.0.0.1:${AUTODL_DREAM_FRONTEND_PORT}/\${endpoint}); case \"\${content_type}\" in text/html*) exit 1 ;; esac; done; ss -ltn | awk '{print \$4}' | grep -Eq '(^|:)${AUTODL_DREAM_FRONTEND_PORT}$'; ss -ltn | awk '{print \$4}' | grep -Eq '(^|:)${AUTODL_DREAM_BACKEND_PORT}$'; printf stack; else curl -fsS --max-time 10 http://127.0.0.1:${AUTODL_DREAM_FRONTEND_PORT}/api/health >/dev/null; printf legacy; fi")"
  [[ -n "${AUTODL_DREAM_PUBLIC_ORIGIN}" ]] || err "AUTODL_DREAM_PUBLIC_ORIGIN is required for public verification."
  curl -fsS --retry 15 --retry-delay 3 --retry-connrefused --max-time 15 "${AUTODL_DREAM_PUBLIC_ORIGIN%/}/api/health" >/dev/null
  if [[ "${topology}" == "stack" ]]; then
    curl -fsS --max-time 15 "${AUTODL_DREAM_PUBLIC_ORIGIN%/}/" >/dev/null
    verify_seo_origin "${AUTODL_DREAM_PUBLIC_ORIGIN}" "AutoDL public origin"
  fi
  verify_default_plugin
  verify_builtin_skills
  log "Dream ${topology} topology, SEO crawler files, built-in Skills, default plugin artifact, Admin dependency, screen supervisor, and public mapping passed."
}

mark_current_qualified() {
  remote "set -e; current=\$(readlink -f $(quote "${AUTODL_APP_ROOT}/current")); test -d \"\${current}\"; ln -sfn \"\${current}\" $(quote "${AUTODL_APP_ROOT}/qualified")"
}

deploy() { command_check; setup_host; sync_files; build_release; stop_dream; start_dream; verify; mark_current_qualified; }

rollback() {
  remote "test -L $(quote "${AUTODL_APP_ROOT}/previous")"
  stop_dream
  remote "set -e; current=\$(readlink -f $(quote "${AUTODL_APP_ROOT}/current")); previous=\$(readlink -f $(quote "${AUTODL_APP_ROOT}/previous")); ln -sfn \"\${current}\" $(quote "${AUTODL_APP_ROOT}/rollback-candidate"); ln -sfn \"\${previous}\" $(quote "${AUTODL_APP_ROOT}/current"); ln -sfn \"\$(readlink -f $(quote "${AUTODL_APP_ROOT}/rollback-candidate"))\" $(quote "${AUTODL_APP_ROOT}/previous"); rm -f $(quote "${AUTODL_APP_ROOT}/rollback-candidate")"
  start_dream; verify; mark_current_qualified
  log "Dream application rolled back; Admin, PostgreSQL, and workspace data were unchanged."
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --help|-h) usage; exit 0 ;;
    --dry-run) DRY_RUN=1; shift ;;
    *) [[ -z "${COMMAND}" ]] || err "Unexpected argument: $1"; COMMAND="$1"; shift ;;
  esac
done

case "${COMMAND:-help}" in
  help) usage ;;
  check) command_check ;;
  plan) require_config; command_plan ;;
  sync) require_config; sync_files ;;
  build) command_check; setup_host; sync_files; build_release ;;
  deploy) deploy ;;
  start) require_config; start_dream; verify; mark_current_qualified ;;
  stop) require_config; stop_dream ;;
  status) require_config; remote "screen -ls 2>/dev/null | grep '[.]${AUTODL_SCREEN_NAME}[[:space:]]' || true; if [ -f $(quote "${AUTODL_APP_ROOT}/run/dream.pid") ]; then pid=\$(cat $(quote "${AUTODL_APP_ROOT}/run/dream.pid")); ps -o pid,ppid,user,stat,etimes,cmd -p \"\${pid}\"; ps -o pid,ppid,user,stat,etimes,cmd --ppid \"\${pid}\"; fi; ss -ltnp 2>/dev/null | grep -E ':(${AUTODL_DREAM_FRONTEND_PORT}|${AUTODL_DREAM_BACKEND_PORT})[[:space:]]' || true" ;;
  logs) require_config; remote "tail -n 200 $(quote "${AUTODL_APP_ROOT}/logs/dream.log")" ;;
  verify) require_config; verify ;;
  rollback) require_config; rollback ;;
  *) err "Unknown command: ${COMMAND}. Run --help." ;;
esac
