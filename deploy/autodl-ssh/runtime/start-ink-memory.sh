#!/usr/bin/env bash
# [Input] Existing AutoDL Admin/Dream releases, secure env files, Node/Python runtimes, and screen.
# [Output] Idempotently preserve or start Admin first, then the Dream frontend/backend stack.
# [Pos] Standalone AutoDL launch script; performs no build, migration, restore, GPU probe, or deployment.
# [Sync] 2026-08-26: use /root/ink-autodl/data as the Admin/PostgreSQL home.
set -euo pipefail

ADMIN_ROOT="${INK_AUTODL_ADMIN_ROOT:-/root/ink-autodl/admin}"
DREAM_ROOT="${INK_AUTODL_DREAM_ROOT:-/root/ink-autodl/dream}"
DATA_ROOT="${INK_AUTODL_DATA_ROOT:-/root/autodl-tmp/ink-memory}"
ADMIN_HOME="${INK_AUTODL_ADMIN_HOME:-/root/ink-autodl/data}"
SERVICE_USER="${INK_AUTODL_SERVICE_USER:-ink-memory}"
DATA_INIT_SCRIPT="${INK_AUTODL_DREAM_DATA_INIT_SCRIPT:-/root/ink-autodl/init-dream-data.sh}"
ADMIN_DATA_INIT_SCRIPT="${INK_AUTODL_ADMIN_DATA_INIT_SCRIPT:-${ADMIN_ROOT}/source/deploy/autodl-ssh/runtime/init-admin-data.sh}"
NODE_BIN="${INK_AUTODL_NODE_BIN:-/root/ink-autodl/runtime/node/bin}"
NPM_BIN="${INK_AUTODL_NPM_BIN:-/root/ink-autodl/runtime/npm/bin}"
ADMIN_PORT="${INK_AUTODL_ADMIN_PORT:-6008}"
FRONTEND_PORT="${INK_AUTODL_FRONTEND_PORT:-6006}"
BACKEND_PORT="${INK_AUTODL_BACKEND_PORT:-8765}"
ADMIN_SCREEN="${INK_AUTODL_ADMIN_SCREEN:-ink-admin}"
DREAM_SCREEN="${INK_AUTODL_DREAM_SCREEN:-ink-dream}"
START_LOG="${INK_AUTODL_START_LOG:-/root/ink-autodl/start-ink-memory.log}"
LOCK_FILE="${INK_AUTODL_START_LOCK:-/root/ink-autodl/start-ink-memory.lock}"

log() { printf '[ink-autodl-start] %s\n' "$*"; }
fail() { printf '[ink-autodl-start:error] %s\n' "$*" >&2; exit 1; }
quote() { printf '%q' "$1"; }

[[ "$(id -u)" == "0" ]] || fail "Run this script as root."
for command_name in curl flock screen setpriv ss tee; do
  command -v "${command_name}" >/dev/null 2>&1 || fail "Missing command: ${command_name}"
done
for port_value in "${ADMIN_PORT}" "${FRONTEND_PORT}" "${BACKEND_PORT}"; do
  [[ "${port_value}" =~ ^[0-9]+$ ]] || fail "Invalid port: ${port_value}"
done

install -d -m 0750 "$(dirname "${START_LOG}")"
exec > >(tee -a "${START_LOG}") 2>&1
exec 9>"${LOCK_FILE}"
flock -n 9 || fail "Another Ink & Memory startup is already running."

[[ -x "${DATA_INIT_SCRIPT}" ]] || fail "Dream data initializer is missing: ${DATA_INIT_SCRIPT}"
INK_AUTODL_DATA_ROOT="${DATA_ROOT}" INK_AUTODL_SERVICE_USER="${SERVICE_USER}" "${DATA_INIT_SCRIPT}"
[[ -x "${ADMIN_DATA_INIT_SCRIPT}" ]] || fail "Admin data initializer is missing: ${ADMIN_DATA_INIT_SCRIPT}"
INK_AUTODL_ADMIN_HOME="${ADMIN_HOME}" INK_AUTODL_DATA_ROOT="${DATA_ROOT}" \
  INK_AUTODL_SERVICE_USER="${SERVICE_USER}" "${ADMIN_DATA_INIT_SCRIPT}"

port_is_listening() {
  local requested_port="$1"
  ss -ltnH | awk '{print $4}' | grep -Eq "(^|:)${requested_port}$"
}

admin_is_healthy() {
  curl -fsS --max-time 3 "http://127.0.0.1:${ADMIN_PORT}/admin/login" >/dev/null 2>&1
}

dream_is_healthy() {
  curl -fsS --max-time 3 "http://127.0.0.1:${BACKEND_PORT}/api/health" >/dev/null 2>&1 \
    && curl -fsS --max-time 3 "http://127.0.0.1:${FRONTEND_PORT}/" >/dev/null 2>&1 \
    && curl -fsS --max-time 3 "http://127.0.0.1:${FRONTEND_PORT}/api/health" >/dev/null 2>&1
}

wait_until() {
  local check_name="$1"
  local attempts="$2"
  local attempt
  for ((attempt = 1; attempt <= attempts; attempt += 1)); do
    if "${check_name}"; then
      return 0
    fi
    sleep 1
  done
  return 1
}

start_admin() {
  if admin_is_healthy; then
    log "Admin is already healthy on 127.0.0.1:${ADMIN_PORT}; preserving the running process."
    return
  fi
  if port_is_listening "${ADMIN_PORT}"; then
    fail "Port ${ADMIN_PORT} is occupied by an unhealthy or unknown process; refusing to replace it."
  fi

  local current_release="${ADMIN_ROOT}/current"
  local env_file="${ADMIN_ROOT}/config/admin.env"
  local pid_file="${ADMIN_ROOT}/run/admin.pid"
  local launcher="${current_release}/start-admin.sh"
  [[ -L "${current_release}" ]] || fail "Admin current release link is missing: ${current_release}"
  [[ -x "${launcher}" ]] || fail "Admin launcher is missing or not executable: ${launcher}"
  [[ -r "${env_file}" ]] || fail "Admin runtime env is missing or unreadable: ${env_file}"
  [[ -x "${NODE_BIN}/node" ]] || fail "Node runtime is missing: ${NODE_BIN}/node"
  id -u "${SERVICE_USER}" >/dev/null 2>&1 || fail "Service user does not exist: ${SERVICE_USER}"

  local uid gid
  uid="$(id -u "${SERVICE_USER}")"
  gid="$(id -g "${SERVICE_USER}")"
  screen -S "${ADMIN_SCREEN}" -X quit >/dev/null 2>&1 || true
  rm -f "${pid_file}"
  screen -dmS "${ADMIN_SCREEN}" -L -Logfile "${ADMIN_ROOT}/logs/admin.log" bash -lc \
    "exec setpriv --reuid=${uid} --regid=${gid} --init-groups env HOME=$(quote "${ADMIN_HOME}") AUTODL_ADMIN_ENV_FILE=$(quote "${env_file}") AUTODL_ADMIN_PID_FILE=$(quote "${pid_file}") AUTODL_NODE_BIN=$(quote "${NODE_BIN}") $(quote "${launcher}")"

  wait_until admin_is_healthy 90 || fail "Admin did not become healthy; inspect ${ADMIN_ROOT}/logs/admin.log"
  log "Admin is ready on 127.0.0.1:${ADMIN_PORT}."
}

start_dream() {
  if dream_is_healthy; then
    log "Dream is already healthy on frontend ${FRONTEND_PORT} and backend ${BACKEND_PORT}; preserving the running processes."
    return
  fi
  if port_is_listening "${FRONTEND_PORT}" || port_is_listening "${BACKEND_PORT}"; then
    fail "Dream ports are partially occupied or unhealthy; refusing to replace unknown processes."
  fi

  local current_release="${DREAM_ROOT}/current"
  local env_file="${DREAM_ROOT}/config/dream.env"
  local pid_file="${DREAM_ROOT}/run/dream.pid"
  local launcher="${current_release}/start-dream.sh"
  [[ -L "${current_release}" ]] || fail "Dream current release link is missing: ${current_release}"
  [[ -x "${launcher}" ]] || fail "Dream launcher is missing or not executable: ${launcher}"
  [[ -r "${env_file}" ]] || fail "Dream runtime env is missing or unreadable: ${env_file}"
  [[ -s "${current_release}/frontend/dist/index.html" ]] || fail "Dream frontend build is missing from the current release."
  [[ -x "${current_release}/venv/bin/python" ]] || fail "Dream Python runtime is missing from the current release."
  [[ -x "${NODE_BIN}/node" ]] || fail "Node runtime is missing: ${NODE_BIN}/node"
  id -u "${SERVICE_USER}" >/dev/null 2>&1 || fail "Service user does not exist: ${SERVICE_USER}"

  local uid gid
  uid="$(id -u "${SERVICE_USER}")"
  gid="$(id -g "${SERVICE_USER}")"
  screen -S "${DREAM_SCREEN}" -X quit >/dev/null 2>&1 || true
  rm -f "${pid_file}"
  screen -dmS "${DREAM_SCREEN}" -L -Logfile "${DREAM_ROOT}/logs/dream.log" bash -lc \
    "exec setpriv --reuid=${uid} --regid=${gid} --init-groups env HOME=$(quote "${DATA_ROOT}/service-home") AUTODL_DREAM_ENV_FILE=$(quote "${env_file}") AUTODL_DREAM_PID_FILE=$(quote "${pid_file}") AUTODL_DREAM_FRONTEND_PORT=${FRONTEND_PORT} AUTODL_DREAM_BACKEND_PORT=${BACKEND_PORT} AUTODL_NODE_BIN=$(quote "${NODE_BIN}") AUTODL_NPM_BIN=$(quote "${NPM_BIN}") $(quote "${launcher}")"

  wait_until dream_is_healthy 120 || fail "Dream did not become healthy; inspect ${DREAM_ROOT}/logs/dream.log"
  log "Dream is ready on frontend 127.0.0.1:${FRONTEND_PORT} and backend 127.0.0.1:${BACKEND_PORT}."
}

verify_default_plugin() {
  local current_release="${DREAM_ROOT}/current"
  (
    cd "${current_release}/app"
    INK_AUTODL_DREAM_ENV_FILE="${DREAM_ROOT}/config/dream.env" \
      "${current_release}/venv/bin/python" -c '
import os
from dotenv import dotenv_values

env_file = os.environ["INK_AUTODL_DREAM_ENV_FILE"]
os.environ.update({key: value for key, value in dotenv_values(env_file).items() if value is not None})
from services.deck.defaults import resolve_default_deck_plugin_ref
resolve_default_deck_plugin_ref()
'
  )
  log "Default Deck plugin artifact is available."
}

log "Starting an existing Ink & Memory AutoDL deployment; no GPU probe, build, migration, or restore will run."
start_admin
start_dream
verify_default_plugin
log "Ink & Memory startup completed."
