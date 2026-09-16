#!/usr/bin/env bash
# [Input] Existing Dream/MCP Apps secure env files and explicit AutoDL service mappings.
# [Output] Mode-0600 Dream backend/Next runtime env using Admin HTTP data/auth credentials.
# [Pos] AutoDL Dream configuration projector; no CLI/transport state is persisted here.
# [Sync] 2026-09-16: stop reading Admin PostgreSQL secrets or projecting DATABASE_URL into Dream.
# [Sync] 2026-08-26: leave Agent admission budgets unset so runtime auto-detects host/cgroup capacity.
# [Sync] 2026-08-30: pin Dream to the generic qualified Linux x64 Runtime
#                    0.1.4 built from authorized 2.1.88 source; AutoDL only
#                    selects its installed absolute CLI path.
# [Sync] 2026-09-13: expect qualified local-core 0.1.9; preparation remains inert until deployment supplies it.
# [Sync] 2026-08-30: force deployment-owned Claude Bash sandbox enablement to
#                    false because the outer AutoDL container rejects userns.
# [Sync] 2026-09-06: project the server-only Node MCP Apps runtime alongside
#                    the Next.js frontend and remove retired Vite settings.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
AUTODL_PLATFORM_ENV_FILE="${AUTODL_PLATFORM_ENV_FILE:-${SCRIPT_DIR}/platform.env}"
if [[ -f "${AUTODL_PLATFORM_ENV_FILE}" ]]; then
  # shellcheck disable=SC1090 -- the operator explicitly selects this local platform file.
  source "${AUTODL_PLATFORM_ENV_FILE}"
fi
SOURCE_ENV_FILE="${AUTODL_DREAM_SOURCE_ENV_FILE:-${REPO_ROOT}/backend/.env}"
MCP_APPS_ENV_FILE="${AUTODL_MCP_APPS_ENV_FILE:-${REPO_ROOT}/frontend/.env.local}"
OUTPUT_ENV_FILE="${AUTODL_ENV_FILE:-${SCRIPT_DIR}/.env}"
AUTODL_DATA_ROOT="${AUTODL_DATA_ROOT:-/root/autodl-tmp/ink-memory}"
AUTODL_DREAM_BACKEND_BIND_HOST="${AUTODL_DREAM_BACKEND_BIND_HOST:-${AUTODL_DREAM_BIND_HOST:-127.0.0.1}}"
AUTODL_DREAM_FRONTEND_PORT="${AUTODL_DREAM_FRONTEND_PORT:-${AUTODL_DREAM_PORT:-6006}}"
AUTODL_DREAM_BACKEND_PORT="${AUTODL_DREAM_BACKEND_PORT:-8765}"
AUTODL_ADMIN_PORT="${AUTODL_ADMIN_PORT:-6008}"
AUTODL_DREAM_PUBLIC_ORIGIN="${AUTODL_DREAM_PUBLIC_ORIGIN:-}"
AUTODL_ADMIN_PUBLIC_ORIGIN="${AUTODL_ADMIN_PUBLIC_ORIGIN:-}"
AUTODL_MCP_APPS_SANDBOX_ORIGIN="${AUTODL_MCP_APPS_SANDBOX_ORIGIN:-}"
AUTODL_CLAUDE_CODE_CLI_PATH="${AUTODL_CLAUDE_CODE_CLI_PATH:-/root/ink-autodl/runtime/npm/bin/ink-claude-code-dream}"

err() { printf '[error] %s\n' "$*" >&2; exit 1; }

[[ -f "${SOURCE_ENV_FILE}" ]] || err "Missing Dream source env: ${SOURCE_ENV_FILE}"
[[ -f "${MCP_APPS_ENV_FILE}" ]] || err "Missing MCP Apps source env: ${MCP_APPS_ENV_FILE}"
[[ "${AUTODL_DATA_ROOT}" == /root/* ]] || err "AUTODL_DATA_ROOT must stay under /root."
[[ "${AUTODL_DREAM_BACKEND_BIND_HOST}" == "127.0.0.1" ]] || err "Dream backend must bind to 127.0.0.1 on AutoDL."
[[ "${AUTODL_DREAM_FRONTEND_PORT}" == "6006" && "${AUTODL_DREAM_BACKEND_PORT}" == "8765" && "${AUTODL_ADMIN_PORT}" == "6008" ]] || err "AutoDL must use frontend 6006, backend 8765, and Admin 6008."
[[ "${AUTODL_CLAUDE_CODE_CLI_PATH}" == /root/ink-autodl/runtime/* ]] || err "AUTODL_CLAUDE_CODE_CLI_PATH must stay under /root/ink-autodl/runtime."
[[ "${AUTODL_DREAM_PUBLIC_ORIGIN}" =~ ^https://[^/]+(:[0-9]+)?$ ]] || err "AUTODL_DREAM_PUBLIC_ORIGIN must be an exact HTTPS origin."
[[ "${AUTODL_ADMIN_PUBLIC_ORIGIN}" =~ ^https://[^/]+(:[0-9]+)?$ ]] || err "AUTODL_ADMIN_PUBLIC_ORIGIN must be an exact HTTPS origin."
[[ "${AUTODL_MCP_APPS_SANDBOX_ORIGIN}" =~ ^https://[^/]+(:[0-9]+)?$ ]] || err "AUTODL_MCP_APPS_SANDBOX_ORIGIN must be an exact HTTPS origin."
[[ "${AUTODL_MCP_APPS_SANDBOX_ORIGIN}" != "${AUTODL_DREAM_PUBLIC_ORIGIN}" ]] || err "MCP Apps sandbox must use a separate HTTPS origin."

temp_file="$(mktemp "${SCRIPT_DIR}/.env.XXXXXX")"
trap 'rm -f "${temp_file}"' EXIT
umask 077
awk -F= '
  BEGIN {
    split("DATABASE_URL INK_LOAD_DATABASE_URL_FROM_ENV_FILE INK_DATABASE_ENV_FILE PORT HOST API_BASE_URL WEBUI_URL INK_PUBLIC_SITE_URL INK_PUBLIC_BASE_URL INK_BACKEND_PUBLIC_BASE_URL INK_CORS_ALLOW_ORIGINS INK_CORS_ALLOW_CREDENTIALS COOKIE_SECURE COOKIE_SAMESITE INK_GATEWAY_BASE_URL INK_ADMIN_PRODUCT_API_BASE_URL INK_ADMIN_PRODUCT_ORIGIN AGENT_CWD ARTIFACT_WORKSPACE_ROOT FILE_STORAGE_LOCAL_DIR INK_CLAUDE_PLUGIN_RUNTIME_ROOT CLAUDE_CODE_CLI_PATH VITE_ALLOWED_HOSTS VITE_DEV_API_PROXY_TARGET INK_AGENT_SANDBOX_ENABLED INK_AGENT_MAX_CONCURRENT_RUNS INK_AGENT_RUN_MEMORY_BUDGET_MIB INK_AGENT_MEMORY_RESERVE_MIB", keys, " ")
    for (i in keys) excluded[keys[i]] = 1
  }
  /^[A-Za-z_][A-Za-z0-9_]*=/ {
    key=$1
    if (!excluded[key]) print
  }
' "${SOURCE_ENV_FILE}" >"${temp_file}"
awk -F= '
  /^INK_MCP_APPS_[A-Z0-9_]*=/ {
    key=$1
    if (key != "INK_MCP_APPS_NODE_SERVICE_TOKEN" && key != "INK_MCP_APPS_SANDBOX_URL" && key != "INK_MCP_APPS_PARENT_ORIGINS") print
  }
' "${MCP_APPS_ENV_FILE}" >>"${temp_file}"
{
  printf 'PORT=%s\n' "${AUTODL_DREAM_BACKEND_PORT}"
  printf 'HOST=%s\n' "${AUTODL_DREAM_BACKEND_BIND_HOST}"
  printf 'API_BASE_URL=%s\n' "${AUTODL_DREAM_PUBLIC_ORIGIN}"
  printf 'WEBUI_URL=%s\n' "${AUTODL_DREAM_PUBLIC_ORIGIN}"
  printf 'INK_PUBLIC_SITE_URL=%s\n' "${AUTODL_DREAM_PUBLIC_ORIGIN}"
  printf 'INK_PUBLIC_BASE_URL=%s\n' "${AUTODL_DREAM_PUBLIC_ORIGIN}"
  printf 'INK_BACKEND_PUBLIC_BASE_URL=%s\n' "${AUTODL_DREAM_PUBLIC_ORIGIN}"
  printf 'INK_CORS_ALLOW_ORIGINS=%s,%s\n' "${AUTODL_DREAM_PUBLIC_ORIGIN}" "${AUTODL_ADMIN_PUBLIC_ORIGIN}"
  printf 'INK_CORS_ALLOW_CREDENTIALS=true\n'
  printf 'COOKIE_SECURE=true\n'
  printf 'COOKIE_SAMESITE=none\n'
  printf 'INK_GATEWAY_BASE_URL=http://127.0.0.1:%s\n' "${AUTODL_ADMIN_PORT}"
  printf 'INK_ADMIN_PRODUCT_API_BASE_URL=http://127.0.0.1:%s\n' "${AUTODL_ADMIN_PORT}"
  printf 'INK_ADMIN_PRODUCT_ORIGIN=%s\n' "${AUTODL_DREAM_PUBLIC_ORIGIN}"
  printf 'AGENT_CWD=%s/agent-workspaces\n' "${AUTODL_DATA_ROOT}"
  printf 'ARTIFACT_WORKSPACE_ROOT=%s/artifacts\n' "${AUTODL_DATA_ROOT}"
  printf 'FILE_STORAGE_LOCAL_DIR=%s/file-storage\n' "${AUTODL_DATA_ROOT}"
  printf 'INK_CLAUDE_PLUGIN_RUNTIME_ROOT=%s/claude-plugin-runtime\n' "${AUTODL_DATA_ROOT}"
  printf 'CLAUDE_CODE_CLI_PATH=%s\n' "${AUTODL_CLAUDE_CODE_CLI_PATH}"
  printf 'INK_AGENT_SANDBOX_ENABLED=false\n'
  printf 'INK_MCP_APPS_SANDBOX_URL=%s/mcp-apps-sandbox\n' "${AUTODL_MCP_APPS_SANDBOX_ORIGIN}"
  printf 'INK_MCP_APPS_PARENT_ORIGINS=%s\n' "${AUTODL_DREAM_PUBLIC_ORIGIN}"
} >>"${temp_file}"

for required_key in SESSION_SECRET_KEY INK_GATEWAY_SERVICE_KEY INK_ADMIN_PRODUCT_JWT_SECRET INK_ADMIN_PRODUCT_API_BASE_URL INK_MCP_APPS_NODE_SERVICE_TOKEN INK_MCP_APPS_PLUGIN_MANIFEST_JSON INK_MCP_APPS_MAX_RESOURCE_BYTES INK_MCP_APPS_MAX_CATALOG_PAGES INK_MCP_APPS_UPSTREAM_TIMEOUT_MS INK_MCP_APPS_MAX_CONCURRENCY_PER_SCOPE INK_MCP_APPS_NETWORK_HOST_ALLOWLIST; do
  grep -q "^${required_key}=" "${temp_file}" || err "${required_key} is missing from the projected env."
done
chmod 600 "${temp_file}"
mv "${temp_file}" "${OUTPUT_ENV_FILE}"
trap - EXIT
printf '[autodl-env] Wrote %s; secret values were not printed.\n' "${OUTPUT_ENV_FILE}"
