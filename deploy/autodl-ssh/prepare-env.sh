#!/usr/bin/env bash
# [Input] Existing Dream/Admin secure env files and explicit AutoDL service mappings.
# [Output] Mode-0600 Dream runtime env with bounded platform admission-policy projection.
# [Pos] AutoDL Dream configuration projector; no CLI/transport state is persisted here.
# [Sync] 2026-08-27: project the diagnostics token and optional Admin-bounded Agent policy.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
AUTODL_PLATFORM_ENV_FILE="${AUTODL_PLATFORM_ENV_FILE:-${SCRIPT_DIR}/platform.env}"
if [[ -f "${AUTODL_PLATFORM_ENV_FILE}" ]]; then
  # shellcheck disable=SC1090 -- the operator explicitly selects this local platform file.
  source "${AUTODL_PLATFORM_ENV_FILE}"
fi
SOURCE_ENV_FILE="${AUTODL_DREAM_SOURCE_ENV_FILE:-${REPO_ROOT}/backend/.env}"
ADMIN_ENV_FILE="${AUTODL_ADMIN_ENV_FILE:-}"
OUTPUT_ENV_FILE="${AUTODL_ENV_FILE:-${SCRIPT_DIR}/.env}"
AUTODL_DATA_ROOT="${AUTODL_DATA_ROOT:-/root/autodl-tmp/ink-memory}"
AUTODL_DREAM_BACKEND_BIND_HOST="${AUTODL_DREAM_BACKEND_BIND_HOST:-${AUTODL_DREAM_BIND_HOST:-127.0.0.1}}"
AUTODL_DREAM_FRONTEND_PORT="${AUTODL_DREAM_FRONTEND_PORT:-${AUTODL_DREAM_PORT:-6006}}"
AUTODL_DREAM_BACKEND_PORT="${AUTODL_DREAM_BACKEND_PORT:-8765}"
AUTODL_ADMIN_PORT="${AUTODL_ADMIN_PORT:-6008}"
AUTODL_DREAM_PUBLIC_ORIGIN="${AUTODL_DREAM_PUBLIC_ORIGIN:-}"
AUTODL_ADMIN_PUBLIC_ORIGIN="${AUTODL_ADMIN_PUBLIC_ORIGIN:-}"

err() { printf '[error] %s\n' "$*" >&2; exit 1; }
env_value() { awk -F= -v key="$2" '$1 == key { print substr($0, index($0, "=") + 1); exit }' "$1"; }
validate_optional_policy_integer() {
  local variable_name="$1"
  local minimum="$2"
  local maximum="$3"
  declare -p "${variable_name}" >/dev/null 2>&1 || return 0
  local value="${!variable_name}"
  [[ "${value}" =~ ^[0-9]+$ && ${#value} -le 10 ]] || err "${variable_name} must satisfy the documented Admin policy bounds."
  local numeric_value=$((10#${value}))
  (( numeric_value >= minimum && numeric_value <= maximum )) || err "${variable_name} must satisfy the documented Admin policy bounds."
}

[[ -f "${SOURCE_ENV_FILE}" ]] || err "Missing Dream source env: ${SOURCE_ENV_FILE}"
[[ -n "${ADMIN_ENV_FILE}" && -f "${ADMIN_ENV_FILE}" ]] || err "AUTODL_ADMIN_ENV_FILE must select the generated Admin AutoDL env."
[[ "${AUTODL_DATA_ROOT}" == /root/* ]] || err "AUTODL_DATA_ROOT must stay under /root."
[[ "${AUTODL_DREAM_BACKEND_BIND_HOST}" == "127.0.0.1" ]] || err "Dream backend must bind to 127.0.0.1 on AutoDL."
[[ "${AUTODL_DREAM_FRONTEND_PORT}" == "6006" && "${AUTODL_DREAM_BACKEND_PORT}" == "8765" && "${AUTODL_ADMIN_PORT}" == "6008" ]] || err "AutoDL must use frontend 6006, backend 8765, and Admin 6008."
[[ "${AUTODL_DREAM_PUBLIC_ORIGIN}" =~ ^https://[^/]+(:[0-9]+)?$ ]] || err "AUTODL_DREAM_PUBLIC_ORIGIN must be an exact HTTPS origin."
[[ "${AUTODL_ADMIN_PUBLIC_ORIGIN}" =~ ^https://[^/]+(:[0-9]+)?$ ]] || err "AUTODL_ADMIN_PUBLIC_ORIGIN must be an exact HTTPS origin."
policy_value_count=0
for policy_variable in \
  AUTODL_AGENT_MAX_CONCURRENT_RUNS \
  AUTODL_AGENT_RUN_MEMORY_BUDGET_MIB \
  AUTODL_AGENT_MEMORY_RESERVE_MIB \
  AUTODL_AGENT_RETRY_AFTER_SECONDS; do
  if declare -p "${policy_variable}" >/dev/null 2>&1; then
    policy_value_count=$((policy_value_count + 1))
  fi
done
(( policy_value_count == 0 || policy_value_count == 4 )) || err "All four AUTODL_AGENT policy values must be supplied together."
validate_optional_policy_integer AUTODL_AGENT_MAX_CONCURRENT_RUNS 1 16
validate_optional_policy_integer AUTODL_AGENT_RUN_MEMORY_BUDGET_MIB 128 8192
validate_optional_policy_integer AUTODL_AGENT_MEMORY_RESERVE_MIB 64 4096
validate_optional_policy_integer AUTODL_AGENT_RETRY_AFTER_SECONDS 5 3600

database_user="$(env_value "${ADMIN_ENV_FILE}" POSTGRES_USER)"
database_password="$(env_value "${ADMIN_ENV_FILE}" POSTGRES_PASSWORD)"
database_name="$(env_value "${ADMIN_ENV_FILE}" POSTGRES_DB)"
diagnostics_token="$(env_value "${ADMIN_ENV_FILE}" DREAM_DIAGNOSTICS_TOKEN)"
dream_public_host="${AUTODL_DREAM_PUBLIC_ORIGIN#https://}"
dream_public_host="${dream_public_host%%:*}"
[[ "${database_user}" =~ ^[A-Za-z0-9_]+$ ]] || err "Admin POSTGRES_USER is missing or unsupported."
[[ "${database_password}" =~ ^[A-Za-z0-9._~-]+$ ]] || err "Admin POSTGRES_PASSWORD must be URL-safe."
[[ "${database_name}" =~ ^[A-Za-z0-9_-]+$ ]] || err "Admin POSTGRES_DB is missing or unsupported."
[[ ${#diagnostics_token} -ge 32 ]] || err "Admin DREAM_DIAGNOSTICS_TOKEN must contain at least 32 characters."

temp_file="$(mktemp "${SCRIPT_DIR}/.env.XXXXXX")"
trap 'rm -f "${temp_file}"' EXIT
umask 077
awk -F= '
  BEGIN {
    split("DATABASE_URL PORT HOST API_BASE_URL WEBUI_URL INK_PUBLIC_BASE_URL INK_BACKEND_PUBLIC_BASE_URL INK_CORS_ALLOW_ORIGINS INK_CORS_ALLOW_CREDENTIALS COOKIE_SECURE COOKIE_SAMESITE INK_GATEWAY_BASE_URL INK_ADMIN_PRODUCT_API_BASE_URL INK_ADMIN_PRODUCT_ORIGIN AGENT_CWD ARTIFACT_WORKSPACE_ROOT FILE_STORAGE_LOCAL_DIR INK_CLAUDE_PLUGIN_RUNTIME_ROOT INK_LOAD_DATABASE_URL_FROM_ENV_FILE CLAUDE_CODE_CLI_PATH VITE_ALLOWED_HOSTS VITE_DEV_API_PROXY_TARGET INK_AGENT_MAX_CONCURRENT_RUNS INK_AGENT_RUN_MEMORY_BUDGET_MIB INK_AGENT_MEMORY_RESERVE_MIB INK_AGENT_SWEEP_INTERVAL_S INK_AGENT_DIAGNOSTICS_TOKEN", keys, " ")
    for (i in keys) excluded[keys[i]] = 1
  }
  /^[A-Za-z_][A-Za-z0-9_]*=/ {
    key=$1
    if (!excluded[key]) print
  }
' "${SOURCE_ENV_FILE}" >"${temp_file}"
{
  printf 'DATABASE_URL=postgresql://%s:%s@127.0.0.1:54329/%s\n' "${database_user}" "${database_password}" "${database_name}"
  printf 'PORT=%s\n' "${AUTODL_DREAM_BACKEND_PORT}"
  printf 'HOST=%s\n' "${AUTODL_DREAM_BACKEND_BIND_HOST}"
  printf 'API_BASE_URL=%s\n' "${AUTODL_DREAM_PUBLIC_ORIGIN}"
  printf 'WEBUI_URL=%s\n' "${AUTODL_DREAM_PUBLIC_ORIGIN}"
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
  printf 'INK_AGENT_DIAGNOSTICS_TOKEN=%s\n' "${diagnostics_token}"
  if [[ -n "${AUTODL_AGENT_MAX_CONCURRENT_RUNS:-}" ]]; then
    printf 'INK_AGENT_MAX_CONCURRENT_RUNS=%s\n' "${AUTODL_AGENT_MAX_CONCURRENT_RUNS}"
  fi
  if [[ -n "${AUTODL_AGENT_RUN_MEMORY_BUDGET_MIB:-}" ]]; then
    printf 'INK_AGENT_RUN_MEMORY_BUDGET_MIB=%s\n' "${AUTODL_AGENT_RUN_MEMORY_BUDGET_MIB}"
  fi
  if [[ -n "${AUTODL_AGENT_MEMORY_RESERVE_MIB:-}" ]]; then
    printf 'INK_AGENT_MEMORY_RESERVE_MIB=%s\n' "${AUTODL_AGENT_MEMORY_RESERVE_MIB}"
  fi
  if [[ -n "${AUTODL_AGENT_RETRY_AFTER_SECONDS:-}" ]]; then
    printf 'INK_AGENT_SWEEP_INTERVAL_S=%s\n' "${AUTODL_AGENT_RETRY_AFTER_SECONDS}"
  fi
  printf 'INK_LOAD_DATABASE_URL_FROM_ENV_FILE=0\n'
  printf 'VITE_ALLOWED_HOSTS=%s\n' "${dream_public_host}"
  printf 'VITE_DEV_API_PROXY_TARGET=http://127.0.0.1:%s\n' "${AUTODL_DREAM_BACKEND_PORT}"
} >>"${temp_file}"

for required_key in DATABASE_URL SESSION_SECRET_KEY INK_GATEWAY_SERVICE_KEY INK_ADMIN_PRODUCT_JWT_SECRET INK_AGENT_DIAGNOSTICS_TOKEN; do
  grep -q "^${required_key}=" "${temp_file}" || err "${required_key} is missing from the projected env."
done
chmod 600 "${temp_file}"
mv "${temp_file}" "${OUTPUT_ENV_FILE}"
trap - EXIT
printf '[autodl-env] Wrote %s; secret values were not printed.\n' "${OUTPUT_ENV_FILE}"
