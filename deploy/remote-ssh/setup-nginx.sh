#!/usr/bin/env bash
# [Input] deploy/remote-ssh/nginx/ink-and-memory.conf, REMOTE_SSH_HOST env.
# [Output] Installs and configures host-level nginx reverse proxy on remote server.
# [Pos] nginx setup companion script in deploy/remote-ssh/
# [Sync] 2026-06-12: initial nginx setup script for ink-backend.suoxya.com / ink-frontend.suoxya.com.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NGINX_CONF_SRC="${SCRIPT_DIR}/nginx/ink-and-memory.conf"
NGINX_CONF_NAME="ink-and-memory"

REMOTE_SSH_HOST="${REMOTE_SSH_HOST:-}"
REMOTE_SSH_USER="${REMOTE_SSH_USER:-root}"
REMOTE_SSH_PORT="${REMOTE_SSH_PORT:-22}"
REMOTE_SSH_KEY="${REMOTE_SSH_KEY:-}"
WITH_SSL="${WITH_SSL:-0}"
DRY_RUN="${DRY_RUN:-0}"

usage() {
  cat <<'EOF'
Usage:
  REMOTE_SSH_HOST=39.97.252.88 ./deploy/remote-ssh/setup-nginx.sh
  REMOTE_SSH_HOST=39.97.252.88 WITH_SSL=1 ./deploy/remote-ssh/setup-nginx.sh

Installs nginx on the remote server, deploys the Ink & Memory virtual host config,
and enables the site.  Optionally provisions Let's Encrypt SSL certificates.

Environment:
  REMOTE_SSH_HOST        required — remote server host or IP
  REMOTE_SSH_USER        SSH user (default: root)
  REMOTE_SSH_PORT        SSH port (default: 22)
  REMOTE_SSH_KEY         optional private key path
  WITH_SSL               default: 0; set to 1 to run certbot after nginx setup
  DRY_RUN                default: 0; set to 1 to print commands without executing
EOF
}

log()  { printf '[setup-nginx] %s\n' "$*"; }
warn() { printf '[warn] %s\n' "$*" >&2; }
err()  { printf '[error] %s\n' "$*" >&2; exit 1; }
quote() { printf '%q' "$1"; }

ssh_target() {
  local host="${REMOTE_SSH_HOST:-REMOTE_SSH_HOST}"
  if [[ -n "${REMOTE_SSH_USER}" ]]; then
    printf '%s@%s\n' "${REMOTE_SSH_USER}" "${host}"
  else
    printf '%s\n' "${host}"
  fi
}

ssh_args() {
  local args=(-p "${REMOTE_SSH_PORT}")
  [[ -n "${REMOTE_SSH_KEY}" ]] && args+=(-i "${REMOTE_SSH_KEY}")
  printf '%s\n' "${args[*]}"
}

# ── Prerequisites check ───────────────────────────────────────────────────────

check_prereqs() {
  local failed=0
  [[ -n "${REMOTE_SSH_HOST}" ]] || { warn "REMOTE_SSH_HOST is required."; failed=1; }
  [[ -f "${NGINX_CONF_SRC}" ]] || { warn "Missing nginx config: ${NGINX_CONF_SRC}"; failed=1; }
  command -v ssh >/dev/null 2>&1 || { warn "ssh not found."; failed=1; }
  command -v scp >/dev/null 2>&1 || { warn "scp not found."; failed=1; }
  [[ "${failed}" == "0" ]]
}

# ── Remote command helpers ────────────────────────────────────────────────────

remote_exec() {
  local cmd="$1"
  local target
  target="$(ssh_target)"
  local args; args="$(ssh_args)"
  if [[ "${DRY_RUN}" == "1" ]]; then
    printf '[dry-run] ssh %s %s %s\n' "${args}" "${target}" "${cmd}"
  else
    # shellcheck disable=SC2086
    ssh ${args} "${target}" "${cmd}"
  fi
}

remote_script() {
  local target
  target="$(ssh_target)"
  local args; args="$(ssh_args)"
  if [[ "${DRY_RUN}" == "1" ]]; then
    printf '[dry-run] ssh %s %s bash -s <<REMOTE ... REMOTE\n' "${args}" "${target}"
  else
    # shellcheck disable=SC2086
    ssh ${args} "${target}" 'bash -s'
  fi
}

# ── SCP helper ────────────────────────────────────────────────────────────────

scp_file() {
  local src="$1"
  local dst="$2"
  local target
  target="$(ssh_target)"
  local args; args="$(ssh_args)"
  if [[ "${DRY_RUN}" == "1" ]]; then
    printf '[dry-run] scp %s %s %s:%s\n' "${args}" "${src}" "${target}" "${dst}"
  else
    # shellcheck disable=SC2086
    scp ${args} "${src}" "${target}:${dst}"
  fi
}

# ── Main setup ────────────────────────────────────────────────────────────────

setup_nginx() {
  log "Deploying nginx config to $(ssh_target)..."

  # 1) Copy the nginx config to remote server /tmp
  scp_file "${NGINX_CONF_SRC}" "/tmp/${NGINX_CONF_NAME}.conf"

  # 2) Install nginx, enable config, test, and reload via a single remote script
  remote_script <<'REMOTE'
set -euo pipefail

CONF_NAME="ink-and-memory"
TMP_CONF="/tmp/${CONF_NAME}.conf"
SITES_AVAILABLE="/etc/nginx/sites-available/${CONF_NAME}"
SITES_ENABLED="/etc/nginx/sites-enabled/${CONF_NAME}"
DEFAULT_SITE="/etc/nginx/sites-enabled/default"

echo "[setup-nginx] Checking OS package manager..."

# Detect OS and install nginx
if command -v apt-get >/dev/null 2>&1; then
  export DEBIAN_FRONTEND=noninteractive
  if ! dpkg -s nginx >/dev/null 2>&1; then
    echo "[setup-nginx] Installing nginx via apt-get..."
    apt-get update -qq
    apt-get install -y -qq nginx
  else
    echo "[setup-nginx] nginx already installed."
  fi
elif command -v yum >/dev/null 2>&1; then
  if ! rpm -q nginx >/dev/null 2>&1; then
    echo "[setup-nginx] Installing nginx via yum..."
    yum install -y nginx
  else
    echo "[setup-nginx] nginx already installed."
  fi
elif command -v dnf >/dev/null 2>&1; then
  if ! rpm -q nginx >/dev/null 2>&1; then
    echo "[setup-nginx] Installing nginx via dnf..."
    dnf install -y nginx
  else
    echo "[setup-nginx] nginx already installed."
  fi
else
  echo "[error] Cannot detect package manager (apt/yum/dnf). Please install nginx manually."
  exit 1
fi

# Ensure sites-available / sites-enabled directories exist
mkdir -p /etc/nginx/sites-available /etc/nginx/sites-enabled

# Remove default site if present to avoid conflicts
if [[ -f "${DEFAULT_SITE}" ]] || [[ -L "${DEFAULT_SITE}" ]]; then
  echo "[setup-nginx] Removing default site: ${DEFAULT_SITE}"
  rm -f "${DEFAULT_SITE}"
fi

# Deploy config
echo "[setup-nginx] Deploying ${SITES_AVAILABLE}..."
cp "${TMP_CONF}" "${SITES_AVAILABLE}"
rm -f "${TMP_CONF}"

# Create symlink if not already present
if [[ ! -L "${SITES_ENABLED}" ]] && [[ ! -f "${SITES_ENABLED}" ]]; then
  echo "[setup-nginx] Enabling site: ${SITES_ENABLED}"
  ln -s "${SITES_AVAILABLE}" "${SITES_ENABLED}"
else
  echo "[setup-nginx] Site already enabled: ${SITES_ENABLED}"
fi

# Ensure sites-enabled include is in nginx.conf
if ! grep -q 'include /etc/nginx/sites-enabled/\*' /etc/nginx/nginx.conf 2>/dev/null; then
  echo "[setup-nginx] Adding sites-enabled include to nginx.conf..."
  # Insert before the closing } of the http block
  sed -i '/^http {/,/^}/{
    /^}/i\    include /etc/nginx/sites-enabled/*;
  }' /etc/nginx/nginx.conf
fi

# Test configuration
echo "[setup-nginx] Testing nginx configuration..."
nginx -t

# Enable and start nginx
if command -v systemctl >/dev/null 2>&1; then
  systemctl enable nginx
  systemctl reload nginx || systemctl start nginx
else
  service nginx reload || service nginx start
fi

echo "[setup-nginx] Nginx setup complete."
echo "[setup-nginx] Verify: curl -H 'Host: ink-backend.suoxya.com' http://127.0.0.1/api/health"
echo "[setup-nginx] Verify: curl -H 'Host: ink-frontend.suoxya.com' http://127.0.0.1/"

REMOTE

  log "Nginx config deployed successfully."
}

setup_ssl() {
  log "Setting up Let's Encrypt SSL certificates..."

  remote_script <<'REMOTE'
set -euo pipefail

# Install certbot if not present
if command -v certbot >/dev/null 2>&1; then
  echo "[setup-ssl] certbot already installed."
else
  echo "[setup-ssl] Installing certbot..."
  if command -v apt-get >/dev/null 2>&1; then
    apt-get update -qq
    apt-get install -y -qq certbot python3-certbot-nginx
  elif command -v yum >/dev/null 2>&1; then
    yum install -y certbot python3-certbot-nginx
  elif command -v dnf >/dev/null 2>&1; then
    dnf install -y certbot python3-certbot-nginx
  fi
fi

echo "[setup-ssl] Requesting certificates for both domains..."
certbot --nginx \
  --non-interactive \
  --agree-tos \
  --email "${CERTBOT_EMAIL:-admin@suoxya.com}" \
  -d ink-backend.suoxya.com \
  -d ink-frontend.suoxya.com

echo "[setup-ssl] Certificates installed. Nginx reloaded with SSL."
REMOTE

  log "SSL setup complete."
}

# ── Main ──────────────────────────────────────────────────────────────────────

main() {
  check_prereqs

  if [[ "${DRY_RUN}" == "1" ]]; then
    log "DRY RUN — commands will be printed but not executed."
  fi

  setup_nginx

  if [[ "${WITH_SSL}" == "1" ]]; then
    setup_ssl
    log "Next: uncomment the SSL server blocks in /etc/nginx/sites-available/ink-and-memory"
    log "      and the HTTP→HTTPS redirect block, then run: nginx -t && systemctl reload nginx"
  fi

  cat <<EOF

Done. Before deploying Docker containers, make sure the frontend port does NOT
conflict with nginx on port 80:

    export REMOTE_FRONTEND_PORT=8080   # nginx proxies to 127.0.0.1:8080
    export REMOTE_SSH_HOST=39.97.252.88
    export REMOTE_APP_DIR=/srv/ink-and-memory
    ./deploy/remote-ssh/deploy.sh deploy

EOF
}

main
