#!/usr/bin/env bash
# [Input] Local backend/data, Remote SSH connection env, and REMOTE_APP_DIR.
# [Output] Backs up and synchronizes Remote SSH backend data files over rsync.
# [Pos] data sync companion script in deploy/remote-ssh/
# [Sync] 2026-06-12: add Remote SSH data backup/upload/download workflow for Docker Compose deployments.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LOCAL_DATA_DIR="${LOCAL_DATA_DIR:-${REPO_ROOT}/backend/data}"

REMOTE_SSH_HOST="${REMOTE_SSH_HOST:-}"
REMOTE_SSH_USER="${REMOTE_SSH_USER:-}"
REMOTE_SSH_PORT="${REMOTE_SSH_PORT:-22}"
REMOTE_SSH_KEY="${REMOTE_SSH_KEY:-}"
REMOTE_APP_DIR="${REMOTE_APP_DIR:-}"
REMOTE_DOCKER_COMPOSE_BIN="${REMOTE_DOCKER_COMPOSE_BIN:-docker-compose}"
REMOTE_COMPOSE_FILE="${REMOTE_COMPOSE_FILE:-deploy/remote-ssh/docker-compose.yml}"
REMOTE_COMPOSE_PROJECT_NAME="${REMOTE_COMPOSE_PROJECT_NAME:-ink-and-memory}"
REMOTE_SYNC_DELETE="${REMOTE_SYNC_DELETE:-0}"
REMOTE_SYNC_STOP_CONTAINERS="${REMOTE_SYNC_STOP_CONTAINERS:-0}"
DRY_RUN="${DRY_RUN:-0}"
COMMAND="${1:-upload}"

usage() {
  cat <<'USAGE'
Usage:
  ./deploy/remote-ssh/sync-data.sh [upload]
  ./deploy/remote-ssh/sync-data.sh backup-remote
  ./deploy/remote-ssh/sync-data.sh download
  ./deploy/remote-ssh/sync-data.sh --help

Commands:
  upload         Default. Create a timestamped local backup from remote backend/data, then rsync local backend/data to remote.
  backup-remote Create only a timestamped local backup from remote backend/data.
  download       Same as backup-remote; does not overwrite local backend/data root files.

Required environment:
  REMOTE_SSH_HOST       remote SSH host or IP
  REMOTE_APP_DIR        absolute remote deployment directory, e.g. /srv/ink-and-memory

Optional environment:
  REMOTE_SSH_USER       SSH user; omitted means use your local SSH default
  REMOTE_SSH_PORT       default: 22
  REMOTE_SSH_KEY        optional private key path
  LOCAL_DATA_DIR        default: <repo>/backend/data
  REMOTE_SYNC_DELETE    default: 0; set to 1 to pass --delete during upload
  REMOTE_SYNC_STOP_CONTAINERS default: 0; set to 1 to stop Compose before upload and restart after
  DRY_RUN               set to 1 to print commands without executing
USAGE
}

log() { printf '[remote-sync] %s\n' "$*"; }
warn() { printf '[warn] %s\n' "$*" >&2; }
err() { printf '[error] %s\n' "$*" >&2; exit 1; }
quote() { printf '%q' "$1"; }

ssh_target() {
  if [[ -n "${REMOTE_SSH_USER}" ]]; then
    printf '%s@%s\n' "${REMOTE_SSH_USER}" "${REMOTE_SSH_HOST:-REMOTE_SSH_HOST}"
  else
    printf '%s\n' "${REMOTE_SSH_HOST:-REMOTE_SSH_HOST}"
  fi
}

ssh_transport() {
  local transport="ssh -p $(quote "${REMOTE_SSH_PORT}")"
  [[ -n "${REMOTE_SSH_KEY}" ]] && transport+=" -i $(quote "${REMOTE_SSH_KEY}")"
  printf '%s\n' "${transport}"
}

ssh_args_array() {
  SSH_ARGS=(-p "${REMOTE_SSH_PORT}")
  [[ -n "${REMOTE_SSH_KEY}" ]] && SSH_ARGS+=(-i "${REMOTE_SSH_KEY}")
  return 0
}

remote_data_dir() {
  printf '%s/backend/data\n' "${REMOTE_APP_DIR%/}"
}

remote_compose_cmd() {
  printf 'cd %s && %s -p %s -f %s' \
    "$(quote "${REMOTE_APP_DIR%/}")" \
    "$(quote "${REMOTE_DOCKER_COMPOSE_BIN}")" \
    "$(quote "${REMOTE_COMPOSE_PROJECT_NAME}")" \
    "$(quote "${REMOTE_COMPOSE_FILE}")"
}

check_prereqs() {
  [[ -n "${REMOTE_SSH_HOST}" ]] || err "REMOTE_SSH_HOST is required."
  [[ -n "${REMOTE_APP_DIR}" ]] || err "REMOTE_APP_DIR is required."
  [[ "${REMOTE_APP_DIR}" == /* ]] || err "REMOTE_APP_DIR must be an absolute path."
  command -v ssh >/dev/null 2>&1 || err "ssh not found."
  command -v rsync >/dev/null 2>&1 || err "rsync not found."
  if [[ "${DRY_RUN}" != "1" ]]; then
    mkdir -p "${LOCAL_DATA_DIR}"
  fi
}

ssh_run() {
  local cmd="$1" target
  target="$(ssh_target)"
  ssh_args_array
  if [[ "${DRY_RUN}" == "1" ]]; then
    printf '[dry-run] ssh'
    printf ' %q' "${SSH_ARGS[@]}" "${target}" "${cmd}"
    printf '\n'
  else
    ssh "${SSH_ARGS[@]}" "${target}" "${cmd}"
  fi
}

run_cmd() {
  if [[ "${DRY_RUN}" == "1" ]]; then
    printf '[dry-run]'
    printf ' %q' "$@"
    printf '\n'
  else
    "$@"
  fi
}

ensure_remote_storage() {
  ssh_run "mkdir -p $(quote "$(remote_data_dir)") $(quote "$(remote_data_dir)/file-storage") $(quote "$(remote_data_dir)/agent-workspace") $(quote "$(remote_data_dir)/backups")"
}

compose_down_if_requested() {
  if [[ "${REMOTE_SYNC_STOP_CONTAINERS}" == "1" ]]; then
    warn "Stopping remote Compose services before data upload."
    ssh_run "$(remote_compose_cmd) down"
  fi
}

compose_up_if_requested() {
  if [[ "${REMOTE_SYNC_STOP_CONTAINERS}" == "1" ]]; then
    log "Restarting remote Compose services after data upload."
    ssh_run "$(remote_compose_cmd) up -d"
  fi
}

backup_remote() {
  local timestamp backup_dir remote_path target
  timestamp="$(date +%Y%m%d_%H%M%S)"
  backup_dir="${LOCAL_DATA_DIR}/bak_remote_${timestamp}"
  remote_path="$(remote_data_dir)/"
  target="$(ssh_target):${remote_path}"

  ensure_remote_storage
  run_cmd mkdir -p "${backup_dir}"
  log "Downloading remote backend/data backup to ${backup_dir}"
  run_cmd rsync -az \
    --exclude '/bak_*/' \
    --exclude '/bak_remote_*/' \
    --exclude '/backups/' \
    -e "$(ssh_transport)" \
    "${target}" "${backup_dir}/"

  log "Remote backup complete: ${backup_dir}"
}

upload_local() {
  local target remote_path rsync_args
  [[ -f "${LOCAL_DATA_DIR}/ink-and-memory.db" ]] || warn "Local SQLite DB not found at ${LOCAL_DATA_DIR}/ink-and-memory.db; syncing directory contents anyway."
  backup_remote
  compose_down_if_requested

  remote_path="$(remote_data_dir)/"
  target="$(ssh_target):${remote_path}"
  rsync_args=(-az
    --exclude '/bak_*/'
    --exclude '/bak_remote_*/'
    --exclude '/backups/'
    -e "$(ssh_transport)")
  [[ "${REMOTE_SYNC_DELETE}" == "1" ]] && rsync_args+=(--delete)

  log "Uploading ${LOCAL_DATA_DIR}/ to $(ssh_target):${remote_path}"
  run_cmd rsync "${rsync_args[@]}" "${LOCAL_DATA_DIR}/" "${target}"
  compose_up_if_requested
  log "Remote data sync complete."
}

case "${COMMAND}" in
  --help|-h|help) usage ;;
  upload) check_prereqs; upload_local ;;
  backup-remote|download) check_prereqs; backup_remote ;;
  *) err "Unknown command: ${COMMAND}. Run --help." ;;
esac
