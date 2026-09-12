#!/usr/bin/env bash
# [Input] Explicit SSH target, public domains, relay origins, and optional backup directory for rollback.
# [Output] Atomic two-site nginx relay switch with exact backup, validation, reload, verification, and rollback.
# [Pos] Remote SSH edge-only topology switch; does not deploy, stop, or delete application/data services.
# [Sync] 2026-09-12: add the recoverable NATAPP relay switch for Dream and Admin.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DREAM_TEMPLATE="${SCRIPT_DIR}/nginx/ink-and-memory.relay.conf.template"
ADMIN_TEMPLATE="${SCRIPT_DIR}/nginx/ink-memory-admin.relay.conf.template"

REMOTE_SSH_HOST="${REMOTE_SSH_HOST:-}"
REMOTE_SSH_USER="${REMOTE_SSH_USER:-}"
REMOTE_SSH_PORT="${REMOTE_SSH_PORT:-22}"
REMOTE_SSH_KEY="${REMOTE_SSH_KEY:-}"
REMOTE_DREAM_FRONTEND_DOMAIN="${REMOTE_DREAM_FRONTEND_DOMAIN:-}"
REMOTE_DREAM_BACKEND_DOMAIN="${REMOTE_DREAM_BACKEND_DOMAIN:-}"
REMOTE_ADMIN_DOMAIN="${REMOTE_ADMIN_DOMAIN:-}"
REMOTE_DREAM_RELAY_ORIGIN="${REMOTE_DREAM_RELAY_ORIGIN:-}"
REMOTE_ADMIN_RELAY_ORIGIN="${REMOTE_ADMIN_RELAY_ORIGIN:-}"
REMOTE_NGINX_BACKUP_DIR="${REMOTE_NGINX_BACKUP_DIR:-}"
COMMAND="${1:-}"

log() { printf '[edge-relay] %s\n' "$*"; }
err() { printf '[error] %s\n' "$*" >&2; exit 1; }

usage() {
  cat <<'EOF'
Usage: ./deploy/remote-ssh/switch-edge-relay.sh <apply|verify|rollback>

apply/verify require:
  REMOTE_SSH_HOST
  REMOTE_DREAM_FRONTEND_DOMAIN
  REMOTE_DREAM_BACKEND_DOMAIN
  REMOTE_ADMIN_DOMAIN
  REMOTE_DREAM_RELAY_ORIGIN   exact http(s) origin, without a path
  REMOTE_ADMIN_RELAY_ORIGIN   exact http(s) origin, without a path

rollback requires REMOTE_SSH_HOST and REMOTE_NGINX_BACKUP_DIR printed by apply.
The script never starts/stops application services or changes application data.
EOF
}

[[ "${COMMAND}" =~ ^(apply|verify|rollback)$ ]] || { usage; exit 2; }
[[ -n "${REMOTE_SSH_HOST}" ]] || err "REMOTE_SSH_HOST is required."

ssh_target() {
  if [[ -n "${REMOTE_SSH_USER}" ]]; then
    printf '%s@%s\n' "${REMOTE_SSH_USER}" "${REMOTE_SSH_HOST}"
  else
    printf '%s\n' "${REMOTE_SSH_HOST}"
  fi
}

ssh_args=(-p "${REMOTE_SSH_PORT}")
scp_args=(-P "${REMOTE_SSH_PORT}")
if [[ -n "${REMOTE_SSH_KEY}" ]]; then
  ssh_args+=(-i "${REMOTE_SSH_KEY}")
  scp_args+=(-i "${REMOTE_SSH_KEY}")
fi

remote_exec() { ssh "${ssh_args[@]}" "$(ssh_target)" "$1"; }

validate_domain() {
  local label="$1" value="$2"
  [[ "${value}" =~ ^[A-Za-z0-9.-]+$ && "${value}" == *.* ]] \
    || err "${label} must be an explicit DNS name."
}

parse_origin() {
  local label="$1" origin="$2" prefix="$3"
  [[ "${origin}" =~ ^https?://[A-Za-z0-9.-]+(:[0-9]{1,5})?$ ]] \
    || err "${label} must be an exact http(s) origin without path, query, fragment, or credentials."
  local scheme="${origin%%://*}" authority="${origin#*://}" host port
  if [[ "${authority}" == *:* ]]; then
    host="${authority%:*}"
    port="${authority##*:}"
  else
    host="${authority}"
    if [[ "${scheme}" == "https" ]]; then port=443; else port=80; fi
  fi
  (( 10#${port} >= 1 && 10#${port} <= 65535 )) || err "${label} port is outside 1..65535."
  printf -v "${prefix}_SCHEME" '%s' "${scheme}"
  printf -v "${prefix}_AUTHORITY" '%s' "${authority}"
  printf -v "${prefix}_HOST" '%s' "${host}"
  printf -v "${prefix}_PORT" '%s' "${port}"
}

require_relay_config() {
  validate_domain REMOTE_DREAM_FRONTEND_DOMAIN "${REMOTE_DREAM_FRONTEND_DOMAIN}"
  validate_domain REMOTE_DREAM_BACKEND_DOMAIN "${REMOTE_DREAM_BACKEND_DOMAIN}"
  validate_domain REMOTE_ADMIN_DOMAIN "${REMOTE_ADMIN_DOMAIN}"
  parse_origin REMOTE_DREAM_RELAY_ORIGIN "${REMOTE_DREAM_RELAY_ORIGIN}" DREAM_RELAY
  parse_origin REMOTE_ADMIN_RELAY_ORIGIN "${REMOTE_ADMIN_RELAY_ORIGIN}" ADMIN_RELAY
}

render() {
  local template="$1" output="$2"
  sed \
    -e "s|__DREAM_FRONTEND_DOMAIN__|${REMOTE_DREAM_FRONTEND_DOMAIN}|g" \
    -e "s|__DREAM_BACKEND_DOMAIN__|${REMOTE_DREAM_BACKEND_DOMAIN}|g" \
    -e "s|__ADMIN_DOMAIN__|${REMOTE_ADMIN_DOMAIN}|g" \
    -e "s|__DREAM_RELAY_SCHEME__|${DREAM_RELAY_SCHEME:-}|g" \
    -e "s|__DREAM_RELAY_AUTHORITY__|${DREAM_RELAY_AUTHORITY:-}|g" \
    -e "s|__DREAM_RELAY_HOST__|${DREAM_RELAY_HOST:-}|g" \
    -e "s|__DREAM_RELAY_PORT__|${DREAM_RELAY_PORT:-}|g" \
    -e "s|__ADMIN_RELAY_SCHEME__|${ADMIN_RELAY_SCHEME:-}|g" \
    -e "s|__ADMIN_RELAY_AUTHORITY__|${ADMIN_RELAY_AUTHORITY:-}|g" \
    -e "s|__ADMIN_RELAY_HOST__|${ADMIN_RELAY_HOST:-}|g" \
    -e "s|__ADMIN_RELAY_PORT__|${ADMIN_RELAY_PORT:-}|g" \
    "${template}" >"${output}"
}

verify() {
  require_relay_config
  remote_exec "set -eu; nginx -t; systemctl is-active nginx; \
    curl -fsS --max-time 20 -H 'Host: ${REMOTE_DREAM_FRONTEND_DOMAIN}' http://127.0.0.1/ >/dev/null; \
    curl -fsS --max-time 20 -H 'Host: ${REMOTE_DREAM_BACKEND_DOMAIN}' http://127.0.0.1/api/health >/dev/null; \
    curl -fsS --max-time 20 -H 'Host: ${REMOTE_ADMIN_DOMAIN}' http://127.0.0.1/admin/login >/dev/null"
  curl -fsS --max-time 20 "https://${REMOTE_DREAM_FRONTEND_DOMAIN}/" >/dev/null
  curl -fsS --max-time 20 "https://${REMOTE_DREAM_BACKEND_DOMAIN}/api/health" >/dev/null
  curl -fsS --max-time 20 "https://${REMOTE_ADMIN_DOMAIN}/admin/login" >/dev/null
  log "nginx plus edge-local and public Dream frontend, Dream health, and Admin login routes passed."
}

apply_relay() {
  require_relay_config
  [[ -f "${DREAM_TEMPLATE}" && -f "${ADMIN_TEMPLATE}" ]] || err "Relay templates are missing."
  local temp_dir dream_rendered admin_rendered target
  temp_dir="$(mktemp -d "${TMPDIR:-/tmp}/ink-edge-relay.XXXXXX")"
  dream_rendered="${temp_dir}/ink-and-memory"
  admin_rendered="${temp_dir}/ink-memory-admin"
  trap "rm -f '${dream_rendered}' '${admin_rendered}'; rmdir '${temp_dir}'" EXIT
  render "${DREAM_TEMPLATE}" "${dream_rendered}"
  render "${ADMIN_TEMPLATE}" "${admin_rendered}"
  target="$(ssh_target)"
  scp "${scp_args[@]}" "${dream_rendered}" "${target}:/tmp/ink-and-memory.relay.candidate"
  scp "${scp_args[@]}" "${admin_rendered}" "${target}:/tmp/ink-memory-admin.relay.candidate"
  remote_exec 'bash -s' <<'REMOTE'
set -euo pipefail
dream=/etc/nginx/sites-available/ink-and-memory
admin=/etc/nginx/sites-available/ink-memory-admin
stamp="$(date +%Y%m%dT%H%M%S%z)"
backup="/etc/nginx/backups/ink-memory-relay-${stamp}"
install -d -m 0700 "${backup}"
cp -aL "${dream}" "${backup}/ink-and-memory"
cp -aL "${admin}" "${backup}/ink-memory-admin"
sha256sum "${backup}/ink-and-memory" "${backup}/ink-memory-admin" >"${backup}/SHA256SUMS"
restore() {
  cp -a "${backup}/ink-and-memory" "${dream}"
  cp -a "${backup}/ink-memory-admin" "${admin}"
  nginx -t
  systemctl reload nginx || true
}
trap 'status=$?; if (( status != 0 )); then restore; fi; exit ${status}' EXIT
install -o root -g root -m 0644 /tmp/ink-and-memory.relay.candidate "${dream}"
install -o root -g root -m 0644 /tmp/ink-memory-admin.relay.candidate "${admin}"
rm -f /tmp/ink-and-memory.relay.candidate /tmp/ink-memory-admin.relay.candidate
nginx -t
systemctl reload nginx
systemctl is-active nginx >/dev/null
trap - EXIT
printf 'REMOTE_NGINX_BACKUP_DIR=%s\n' "${backup}"
REMOTE
  verify
}

rollback() {
  [[ "${REMOTE_NGINX_BACKUP_DIR}" =~ ^/etc/nginx/backups/ink-memory-relay-[A-Za-z0-9+:-]+$ ]] \
    || err "REMOTE_NGINX_BACKUP_DIR must be the exact directory printed by apply."
  remote_exec "set -euo pipefail; backup='${REMOTE_NGINX_BACKUP_DIR}'; \
    sha256sum -c \"\${backup}/SHA256SUMS\"; \
    cp -a \"\${backup}/ink-and-memory\" /etc/nginx/sites-available/ink-and-memory; \
    cp -a \"\${backup}/ink-memory-admin\" /etc/nginx/sites-available/ink-memory-admin; \
    nginx -t; systemctl reload nginx; systemctl is-active nginx"
  log "Restored both nginx sites from ${REMOTE_NGINX_BACKUP_DIR}."
}

case "${COMMAND}" in
  apply) apply_relay ;;
  verify) verify ;;
  rollback) rollback ;;
esac
