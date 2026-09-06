#!/usr/bin/env bash
# [Input] backend/server.py, backend/.env, root frontend package, and an optional immutable Vite rollback image.
# [Output] Local check/build/start/verify/stop workflow using Next by default or a named rollback image.
# [Pos] platform release entry in deploy/local/
# [Sync] 2026-06-12: add platform-scoped local release helper with help, dry-run, and check modes.
# [Sync] 2026-08-07: expose the frontend dev server on all network interfaces by default.
# [Sync] 2026-08-22: source Dream's local database URL from the Admin-owned
#                    embedded PostgreSQL env file instead of a stale local DSN.
# [Sync] 2026-08-31: remove the unused legacy models.json prerequisite.
# [Sync] 2026-09-05: select the Next compatibility shell by default with an explicit Vite rollback runtime.
# [Sync] 2026-09-05: remove source-built Vite rollback; only an explicitly named image may be selected.
# [Sync] 2026-09-06: verify the canonical pnpm workspace marker after the npm transition lock is retired.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
BACKEND_DIR="${REPO_ROOT}/backend"
FRONTEND_DIR="${REPO_ROOT}/frontend"
LOG_DIR="${LOCAL_RELEASE_LOG_DIR:-${REPO_ROOT}/logs/deploy-local}"
BACKEND_PID="${LOG_DIR}/backend.pid"
FRONTEND_PID="${LOG_DIR}/frontend.pid"
BACKEND_LOG="${LOG_DIR}/backend.log"
FRONTEND_LOG="${LOG_DIR}/frontend.log"
LOCAL_BACKEND_URL="${LOCAL_BACKEND_URL:-http://127.0.0.1:8765}"
LOCAL_FRONTEND_HOST="${LOCAL_FRONTEND_HOST:-0.0.0.0}"
LOCAL_FRONTEND_PORT="${LOCAL_FRONTEND_PORT:-5173}"
LOCAL_FRONTEND_URL="${LOCAL_FRONTEND_URL:-http://127.0.0.1:${LOCAL_FRONTEND_PORT}}"
LOCAL_FRONTEND_RUNTIME="${LOCAL_FRONTEND_RUNTIME:-next}"
LOCAL_VITE_ROLLBACK_IMAGE="${LOCAL_VITE_ROLLBACK_IMAGE:-}"
LOCAL_VITE_ROLLBACK_CONTAINER="${LOCAL_VITE_ROLLBACK_CONTAINER:-ink-frontend-vite-task411-01-rollback}"
LOCAL_VITE_ROLLBACK_BACKEND_URL="${LOCAL_VITE_ROLLBACK_BACKEND_URL:-${LOCAL_BACKEND_URL}}"
LOCAL_VITE_ROLLBACK_API_BASE_URL="${LOCAL_VITE_ROLLBACK_API_BASE_URL-${LOCAL_BACKEND_URL}}"
LOCAL_VITE_ROLLBACK_WS_BASE_URL="${LOCAL_VITE_ROLLBACK_WS_BASE_URL-}"
LOCAL_VITE_ROLLBACK_NETWORK="${LOCAL_VITE_ROLLBACK_NETWORK-}"
LOCAL_ADMIN_ENV_FILE="${LOCAL_ADMIN_ENV_FILE:-${REPO_ROOT}/../ink-admin-memory/.env.local}"

DRY_RUN=0
COMMAND=""

usage() {
  cat <<'EOF'
Usage:
  ./deploy/local/deploy.sh [--dry-run] <command>
  ./deploy/local/deploy.sh --check
  ./deploy/local/deploy.sh --help

Commands:
  check    Validate local tools and required config files.
  build    Build frontend assets and syntax-check key backend entry files.
  start    Start backend and frontend dev processes in the background.
  deploy   Alias for start.
  verify   Check local backend and frontend URLs.
  stop     Stop background processes started by this script.
  clean    Stop processes and remove pid files. Set LOCAL_CLEAN_LOGS=1 to remove logs.
  logs     Show recent local release logs.

Environment overrides:
  LOCAL_BACKEND_URL       default: http://127.0.0.1:8765
  LOCAL_FRONTEND_HOST     default: 0.0.0.0 (listen on all network interfaces)
  LOCAL_FRONTEND_PORT     default: 5173
  LOCAL_FRONTEND_URL      default: http://127.0.0.1:${LOCAL_FRONTEND_PORT} (local verification URL)
  LOCAL_FRONTEND_RUNTIME  next (default) or vite-image (immutable rollback)
  LOCAL_VITE_ROLLBACK_IMAGE
                          exact image tag or digest; required for vite-image
  LOCAL_VITE_ROLLBACK_CONTAINER
                          default: ink-frontend-vite-task411-01-rollback
  LOCAL_VITE_ROLLBACK_BACKEND_URL
                          container-internal backend URL; defaults to LOCAL_BACKEND_URL
  LOCAL_VITE_ROLLBACK_API_BASE_URL
                          browser-facing API URL; defaults to LOCAL_BACKEND_URL (set empty for same-origin)
  LOCAL_VITE_ROLLBACK_WS_BASE_URL
                          browser-facing WebSocket URL; defaults to empty
  LOCAL_VITE_ROLLBACK_NETWORK
                          optional pre-existing Docker network for the rollback container
  LOCAL_RELEASE_LOG_DIR   default: logs/deploy-local
  LOCAL_ADMIN_ENV_FILE    default: sibling ink-admin-memory/.env.local
  PYTHON_BIN              default: backend/.venv/bin/python, python3, then python
EOF
}

log() { printf '[local] %s\n' "$*"; }
warn() { printf '[warn] %s\n' "$*" >&2; }
err() { printf '[error] %s\n' "$*" >&2; exit 1; }

print_cmd() {
  printf '[dry-run]'
  printf ' %q' "$@"
  printf '\n'
}

run() {
  if [[ "${DRY_RUN}" == "1" ]]; then
    print_cmd "$@"
  else
    "$@"
  fi
}

run_in_dir() {
  local dir="$1"
  shift
  if [[ "${DRY_RUN}" == "1" ]]; then
    printf '[dry-run] cd %q &&' "${dir}"
    printf ' %q' "$@"
    printf '\n'
  else
    (cd "${dir}" && "$@")
  fi
}

select_python() {
  if [[ -n "${PYTHON_BIN:-}" ]]; then
    printf '%s\n' "${PYTHON_BIN}"
  elif [[ -x "${BACKEND_DIR}/.venv/bin/python" ]]; then
    printf '%s\n' "${BACKEND_DIR}/.venv/bin/python"
  elif command -v python3 >/dev/null 2>&1; then
    command -v python3
  elif command -v python >/dev/null 2>&1; then
    command -v python
  else
    return 1
  fi
}

require_command() {
  local name="$1"
  if [[ "${DRY_RUN}" == "1" ]]; then
    log "Would check command: ${name}"
    return 0
  fi
  command -v "${name}" >/dev/null 2>&1 || return 1
}

require_file() {
  local file="$1"
  if [[ "${DRY_RUN}" == "1" ]]; then
    log "Would check file: ${file}"
    return 0
  fi
  [[ -f "${file}" ]] || return 1
}

check_prereqs() {
  local failed=0
  require_command pnpm || { warn "pnpm not found."; failed=1; }
  if [[ "${DRY_RUN}" == "1" ]]; then
    log "Would resolve Python from PYTHON_BIN, backend/.venv/bin/python, python3, or python."
  else
    select_python >/dev/null || { warn "python not found. Set PYTHON_BIN or install Python."; failed=1; }
  fi
  require_file "${BACKEND_DIR}/server.py" || { warn "Missing backend/server.py."; failed=1; }
  require_file "${BACKEND_DIR}/database.py" || { warn "Missing backend/database.py."; failed=1; }
  require_file "${BACKEND_DIR}/.env" || { warn "Missing backend/.env. Copy backend/.env.example first."; failed=1; }
  require_file "${LOCAL_ADMIN_ENV_FILE}" || { warn "Missing Admin env file at ${LOCAL_ADMIN_ENV_FILE}. Set LOCAL_ADMIN_ENV_FILE or run Admin env:setup."; failed=1; }
  require_file "${FRONTEND_DIR}/package.json" || { warn "Missing frontend/package.json."; failed=1; }
  case "${LOCAL_FRONTEND_RUNTIME}" in
    next) ;;
    vite-image)
      require_command docker || { warn "docker not found for Vite image rollback."; failed=1; }
      if [[ -z "${LOCAL_VITE_ROLLBACK_IMAGE}" ]]; then
        warn "LOCAL_VITE_ROLLBACK_IMAGE is required when LOCAL_FRONTEND_RUNTIME=vite-image."
        failed=1
      elif [[ "${DRY_RUN}" != "1" ]] && ! docker image inspect "${LOCAL_VITE_ROLLBACK_IMAGE}" >/dev/null 2>&1; then
        warn "Vite rollback image is unavailable: ${LOCAL_VITE_ROLLBACK_IMAGE}"
        failed=1
      fi
      if [[ -n "${LOCAL_VITE_ROLLBACK_NETWORK}" && "${DRY_RUN}" != "1" ]] \
        && ! docker network inspect "${LOCAL_VITE_ROLLBACK_NETWORK}" >/dev/null 2>&1; then
        warn "Vite rollback Docker network is unavailable: ${LOCAL_VITE_ROLLBACK_NETWORK}"
        failed=1
      fi
      ;;
    *) warn "LOCAL_FRONTEND_RUNTIME must be next or vite-image."; failed=1 ;;
  esac
  require_file "${FRONTEND_DIR}/node_modules/.pnpm/lock.yaml" || warn "frontend/node_modules is not installed from the canonical pnpm lock."
  if [[ "${failed}" == "1" ]]; then
    return 1
  fi
  log "Local prerequisites look usable."
}

is_running() {
  local pid_file="$1"
  [[ -f "${pid_file}" ]] || return 1
  local pid
  pid="$(cat "${pid_file}")"
  [[ -n "${pid}" ]] && kill -0 "${pid}" >/dev/null 2>&1
}

start_process() {
  local name="$1" dir="$2" pid_file="$3" log_file="$4"
  shift 4
  if is_running "${pid_file}"; then
    log "${name} already running with pid $(cat "${pid_file}")."
    return 0
  fi
  if [[ "${DRY_RUN}" == "1" ]]; then
    printf '[dry-run] cd %q && nohup' "${dir}"
    printf ' %q' "$@"
    printf ' > %q 2>&1 & echo $! > %q\n' "${log_file}" "${pid_file}"
    return 0
  fi
  mkdir -p "${LOG_DIR}"
  (
    cd "${dir}"
    nohup "$@" > "${log_file}" 2>&1 &
    echo $! > "${pid_file}"
  )
  log "Started ${name} with pid $(cat "${pid_file}") (${log_file})."
}

stop_process() {
  local name="$1" pid_file="$2"
  if ! is_running "${pid_file}"; then
    rm -f "${pid_file}"
    log "${name} is not running."
    return 0
  fi
  local pid
  pid="$(cat "${pid_file}")"
  if [[ "${DRY_RUN}" == "1" ]]; then
    log "Would stop ${name} pid ${pid}."
    return 0
  fi
  kill "${pid}" >/dev/null 2>&1 || true
  rm -f "${pid_file}"
  log "Stopped ${name} pid ${pid}."
}

command_build() {
  check_prereqs
  local python_bin
  if [[ "${DRY_RUN}" == "1" ]]; then
    python_bin="${PYTHON_BIN:-python3}"
  else
    python_bin="$(select_python)"
  fi
  run_in_dir "${BACKEND_DIR}" "${python_bin}" -m py_compile server.py database.py
  if [[ "${LOCAL_FRONTEND_RUNTIME}" == "vite-image" ]]; then
    if [[ "${DRY_RUN}" == "1" ]]; then
      print_cmd docker image inspect "${LOCAL_VITE_ROLLBACK_IMAGE}"
    else
      docker image inspect "${LOCAL_VITE_ROLLBACK_IMAGE}" >/dev/null
      log "Verified immutable Vite rollback image: ${LOCAL_VITE_ROLLBACK_IMAGE}"
    fi
  else
    run_in_dir "${FRONTEND_DIR}" pnpm run build
  fi
}

start_vite_rollback() {
  local -a docker_args=(
    docker run --rm --detach
    --name "${LOCAL_VITE_ROLLBACK_CONTAINER}"
    --publish "${LOCAL_FRONTEND_PORT}:80"
    --env "BACKEND_URL=${LOCAL_VITE_ROLLBACK_BACKEND_URL}"
    --env "API_BASE_URL=${LOCAL_VITE_ROLLBACK_API_BASE_URL}"
    --env "WS_BASE_URL=${LOCAL_VITE_ROLLBACK_WS_BASE_URL}"
  )
  if [[ -n "${LOCAL_VITE_ROLLBACK_NETWORK}" ]]; then
    docker_args+=(--network "${LOCAL_VITE_ROLLBACK_NETWORK}")
  fi
  docker_args+=("${LOCAL_VITE_ROLLBACK_IMAGE}")
  if [[ "${DRY_RUN}" == "1" ]]; then
    print_cmd "${docker_args[@]}"
    return 0
  fi
  if docker container inspect "${LOCAL_VITE_ROLLBACK_CONTAINER}" >/dev/null 2>&1; then
    log "Vite rollback container is already present: ${LOCAL_VITE_ROLLBACK_CONTAINER}"
    return 0
  fi
  "${docker_args[@]}" >/dev/null
  log "Started Vite rollback image ${LOCAL_VITE_ROLLBACK_IMAGE} as ${LOCAL_VITE_ROLLBACK_CONTAINER}."
}

stop_vite_rollback() {
  if [[ "${DRY_RUN}" == "1" ]]; then
    print_cmd docker rm --force "${LOCAL_VITE_ROLLBACK_CONTAINER}"
    return 0
  fi
  if command -v docker >/dev/null 2>&1 && docker container inspect "${LOCAL_VITE_ROLLBACK_CONTAINER}" >/dev/null 2>&1; then
    docker rm --force "${LOCAL_VITE_ROLLBACK_CONTAINER}" >/dev/null
    log "Stopped Vite rollback container ${LOCAL_VITE_ROLLBACK_CONTAINER}."
  fi
}

command_start() {
  check_prereqs
  local python_bin
  if [[ "${DRY_RUN}" == "1" ]]; then
    python_bin="${PYTHON_BIN:-python3}"
  else
    python_bin="$(select_python)"
  fi
  start_process \
    "backend" \
    "${BACKEND_DIR}" \
    "${BACKEND_PID}" \
    "${BACKEND_LOG}" \
    env -u DATABASE_URL \
    INK_LOAD_DATABASE_URL_FROM_ENV_FILE=1 \
    INK_DATABASE_ENV_FILE="${LOCAL_ADMIN_ENV_FILE}" \
    "${python_bin}" server.py
  if [[ "${LOCAL_FRONTEND_RUNTIME}" == "vite-image" ]]; then
    start_vite_rollback
  else
    start_process "frontend" "${FRONTEND_DIR}" "${FRONTEND_PID}" "${FRONTEND_LOG}" env "INK_BACKEND_INTERNAL_URL=${LOCAL_BACKEND_URL}" pnpm run dev --hostname "${LOCAL_FRONTEND_HOST}" --port "${LOCAL_FRONTEND_PORT}"
  fi
  log "Frontend: ${LOCAL_FRONTEND_URL}"
  log "Backend : ${LOCAL_BACKEND_URL}"
}

command_verify() {
  if [[ "${DRY_RUN}" == "1" ]]; then
    print_cmd curl -fsS --max-time 5 "${LOCAL_BACKEND_URL}/api/health"
    print_cmd curl -fsS --max-time 5 "${LOCAL_FRONTEND_URL}/"
    return 0
  fi
  require_command curl || err "curl not found."
  curl -fsS --max-time 5 "${LOCAL_BACKEND_URL}/api/health" >/dev/null
  curl -fsS --max-time 5 "${LOCAL_FRONTEND_URL}/" >/dev/null
  log "Local verification passed."
}

command_clean() {
  stop_process "frontend" "${FRONTEND_PID}"
  stop_vite_rollback
  stop_process "backend" "${BACKEND_PID}"
  if [[ "${LOCAL_CLEAN_LOGS:-0}" == "1" ]]; then
    run rm -f "${BACKEND_LOG}" "${FRONTEND_LOG}"
  fi
}

command_logs() {
  for file in "${BACKEND_LOG}" "${FRONTEND_LOG}"; do
    if [[ -f "${file}" ]]; then
      printf '\n==> %s <==\n' "${file}"
      tail -n 80 "${file}"
    else
      warn "Missing log file: ${file}"
    fi
  done
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --help|-h)
      usage
      exit 0
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --check)
      COMMAND="check"
      shift
      ;;
    *)
      if [[ -z "${COMMAND}" ]]; then
        COMMAND="$1"
        shift
      else
        err "Unexpected argument: $1"
      fi
      ;;
  esac
done

case "${COMMAND:-help}" in
  help) usage ;;
  check) check_prereqs ;;
  build) command_build ;;
  start|deploy|up) command_start ;;
  verify) command_verify ;;
  stop) stop_process "frontend" "${FRONTEND_PID}"; stop_vite_rollback; stop_process "backend" "${BACKEND_PID}" ;;
  clean) command_clean ;;
  logs) command_logs ;;
  *) err "Unknown command: ${COMMAND}. Run --help." ;;
esac
