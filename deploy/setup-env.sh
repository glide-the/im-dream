#!/usr/bin/env bash
# deploy/setup-env.sh — Initialize scoped backend and frontend Cloud Run configuration.
# [Sync] 2026-06-12: point follow-up release guidance to deploy/google-cloud/deploy.sh.
# [Sync] 2026-09-16: exclude retired Dream database configuration from Cloud Run env projection.
# [Sync] 2026-09-16: split Admin service and Next BFF secrets into backend/frontend Cloud Run refs.
# [Sync] 2026-09-16: stop creating or projecting retired Dream Google/JWT/session/OAuth secrets.
# [Historical Sync] 2026-06-23: stored Dream Google/JWT/session secrets before Admin became the auth owner.
#
# Behavior:
#   - Prompts to confirm selected Secret Manager keys
#   - All other keys in backend/.env are passed through as plain env vars silently
#   - Writes .cloud-env before any gcloud calls
#
# Usage:
#   export GCP_PROJECT_ID=your-project-id
#   export INK_ADMIN_DREAM_SERVICE_SECRET_NAME=ink-admin-dream-service-secret
#   export INK_DREAM_BFF_COOKIE_SECRET_NAME=ink-dream-bff-cookie-secret
#   ./deploy/setup-env.sh
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DOTENV="${REPO_ROOT}/backend/.env"
CLOUD_ENV="${REPO_ROOT}/.cloud-env"

PROJECT_ID="${GCP_PROJECT_ID:?ERROR: GCP_PROJECT_ID is not set. Run: export GCP_PROJECT_ID=your-project-id}"
ADMIN_SERVICE_SECRET_NAME="${INK_ADMIN_DREAM_SERVICE_SECRET_NAME:-ink-admin-dream-service-secret}"
BFF_COOKIE_SECRET_NAME="${INK_DREAM_BFF_COOKIE_SECRET_NAME:-ink-dream-bff-cookie-secret}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
log()   { echo -e "${GREEN}[setup-env]${NC} $*"; }
info()  { echo -e "${CYAN}[info]${NC}      $*"; }
warn()  { echo -e "${YELLOW}[warn]${NC}      $*"; }
err()   { echo -e "${RED}[error]${NC}     $*" >&2; exit 1; }
prompt(){ echo -en "${CYAN}  ? ${1}${NC} [${2}]: " >&2; }

command -v gcloud >/dev/null 2>&1 || err "gcloud CLI not found."
gcloud config set project "${PROJECT_ID}" --quiet

# ── Keys that require confirmation and go to Secret Manager ──────────────────
# secret_name is the corresponding Secret Manager resource name.
#
#  ENV_KEY                        SECRET_NAME
SECRET_KEYS="
ANTHROPIC_BASE_URL             ink-anthropic-base-url
ANTHROPIC_AUTH_TOKEN           ink-anthropic-auth-token
ANTHROPIC_MODEL                ink-anthropic-model
ANTHROPIC_DEFAULT_HAIKU_MODEL  ink-anthropic-haiku-model
ANTHROPIC_DEFAULT_SONNET_MODEL ink-anthropic-sonnet-model
ANTHROPIC_DEFAULT_OPUS_MODEL   ink-anthropic-opus-model
AGENT_CWD                      ink-agent-cwd
FILE_STORAGE_LOCAL_DIR         ink-file-storage-dir
INK_ADMIN_DREAM_SERVICE_SECRET ${ADMIN_SERVICE_SECRET_NAME}
INK_DREAM_BFF_COOKIE_SECRET    ${BFF_COOKIE_SECRET_NAME}
"

# Cloud Run defaults for path keys (ignore local .env values)
_DEFAULT_AGENT_CWD="/app/data/agent-workspace"
_DEFAULT_FILE_STORAGE="/app/data/file-storage"

# ── Load backend/.env ─────────────────────────────────────────────────────────
DEFAULTS_FILE="$(mktemp)"
FRONTEND_DEFAULTS_FILE="$(mktemp)"
trap 'rm -f "${DEFAULTS_FILE}" "${FRONTEND_DEFAULTS_FILE}"' EXIT

if [[ -f "${DOTENV}" ]]; then
  log "Reading backend/.env..."
  while IFS= read -r line; do
    [[ "${line}" =~ ^[[:space:]]*# || -z "${line// /}" ]] && continue
    key="${line%%=*}" ; value="${line#*=}"
    key="${key// /}"
    value="${value%\"}" ; value="${value#\"}"
    value="${value%\'}" ; value="${value#\'}"
    [[ -n "${key}" ]] && printf '%s=%s\n' "${key}" "${value}" >> "${DEFAULTS_FILE}"
  done < "${DOTENV}"
else
  warn "backend/.env not found — only prompted keys will be set."
fi

if [[ -f "${REPO_ROOT}/frontend/.env.local" ]]; then
  log "Reading frontend/.env.local for Next-only secrets..."
  while IFS= read -r line; do
    [[ "${line}" =~ ^[[:space:]]*# || -z "${line// /}" ]] && continue
    key="${line%%=*}" ; value="${line#*=}"
    key="${key// /}"
    value="${value%\"}" ; value="${value#\"}"
    value="${value%\'}" ; value="${value#\'}"
    [[ -n "${key}" ]] && printf '%s=%s\n' "${key}" "${value}" >> "${FRONTEND_DEFAULTS_FILE}"
  done < "${REPO_ROOT}/frontend/.env.local"
fi

get_default() { grep "^${1}=" "${DEFAULTS_FILE}" 2>/dev/null | head -1 | cut -d= -f2-; }
get_frontend_default() { grep "^${1}=" "${FRONTEND_DEFAULTS_FILE}" 2>/dev/null | head -1 | cut -d= -f2-; }

# ── Build the set of keys that will go to Secret Manager ─────────────────────
# (used to exclude them from plain ENV_VARS)
secret_key_list() {
  echo "${SECRET_KEYS}" | awk 'NF>=1{print $1}'
}

is_secret_key() {
  secret_key_list | grep -qx "${1}"
}

# ════════════════════════════════════════════════════════
# PHASE 1 — Confirm secret keys interactively
# ════════════════════════════════════════════════════════
echo ""
info "════════════════════════════════════════════════════════"
info "  Confirm keys for Secret Manager"
info "  Press Enter to accept the value shown in [brackets]."
info "════════════════════════════════════════════════════════"
echo ""

# Temp file to store confirmed secret values: KEY=VALUE
CONFIRMED_FILE="$(mktemp)"
trap 'rm -f "${DEFAULTS_FILE}" "${FRONTEND_DEFAULTS_FILE}" "${CONFIRMED_FILE}"' EXIT

while read -r env_key secret_name; do
  [[ -z "${env_key}" ]] && continue

  # Choose display default
  case "${env_key}" in
    AGENT_CWD)             default="${_DEFAULT_AGENT_CWD}" ;;
    FILE_STORAGE_LOCAL_DIR) default="${_DEFAULT_FILE_STORAGE}" ;;
    INK_DREAM_BFF_COOKIE_SECRET)
                           default="$(get_frontend_default "${env_key}")"
                           display="${default:+(set)}" ;;
    ANTHROPIC_AUTH_TOKEN|INK_ADMIN_DREAM_SERVICE_SECRET)
                           default="$(get_default "${env_key}")"
                           display="${default:+(set)}" ;;
    *)                     default="$(get_default "${env_key}")"
                           display="${default:-empty}" ;;
  esac

  # For auth token use masked display, others show actual value
  case "${env_key}" in
    ANTHROPIC_AUTH_TOKEN|INK_ADMIN_DREAM_SERVICE_SECRET|INK_DREAM_BFF_COOKIE_SECRET)
                         display="${default:+(set)}" ;;
    *)                    display="${default:-empty}" ;;
  esac

  prompt "${env_key}" "${display}"
  read -r input </dev/tty
  value="${input:-${default}}"
  printf '%s=%s\n' "${env_key}" "${value}" >> "${CONFIRMED_FILE}"

done < <(echo "${SECRET_KEYS}" | awk 'NF>=2{print $1, $2}')

# ════════════════════════════════════════════════════════
# PHASE 2 — Build ENV_VARS from remaining .env keys + write .cloud-env
# ════════════════════════════════════════════════════════
ENV_VARS="TZ=UTC"
SECRET_REFS=""
FRONTEND_SECRET_REFS=""

# Pass through all .env keys not in the secret list
while IFS='=' read -r key value; do
  is_secret_key "${key}" && continue
  case "${key}" in
    TZ) continue ;; # already set
    # Owned by deploy/google-cloud/deploy.sh so localhost values from
    # backend/.env never leak into the production Cloud Run revision.
    DATABASE_URL|INK_LOAD_DATABASE_URL_FROM_ENV_FILE|INK_DATABASE_ENV_FILE) continue ;;
    GOOGLE_CLIENT_SECRET|JWT_SECRET|JWT_SECRET_KEY|SESSION_SECRET_KEY|OAUTH_TOKEN_ENCRYPTION_KEY|AUTH_TOKEN_ENCRYPTION_KEY|COOKIE_SECURE|COOKIE_SAMESITE|INK_DREAM_BFF_COOKIE_SECRET) continue ;;
    WEBUI_URL|API_BASE_URL|INK_CORS_ALLOW_ORIGINS|INK_CORS_ALLOW_CREDENTIALS|INK_PUBLIC_BASE_URL|INK_BACKEND_PUBLIC_BASE_URL) continue ;;
  esac
  ENV_VARS+=",${key}=${value}"
done < "${DEFAULTS_FILE}"

# Build SECRET_REFS from confirmed values
while read -r env_key secret_name; do
  [[ -z "${env_key}" ]] && continue
  confirmed_val="$(grep "^${env_key}=" "${CONFIRMED_FILE}" | head -1 | cut -d= -f2-)"
  [[ -n "${confirmed_val}" ]] || continue
  case "${env_key}" in
    INK_DREAM_BFF_COOKIE_SECRET)
      FRONTEND_SECRET_REFS+="${env_key}=${secret_name}:latest,"
      ;;
    INK_ADMIN_DREAM_SERVICE_SECRET)
      SECRET_REFS+="${env_key}=${secret_name}:latest,"
      FRONTEND_SECRET_REFS+="${env_key}=${secret_name}:latest,"
      ;;
    *)
      SECRET_REFS+="${env_key}=${secret_name}:latest,"
      ;;
  esac
done < <(echo "${SECRET_KEYS}" | awk 'NF>=2{print $1, $2}')
SECRET_REFS="${SECRET_REFS%,}"
FRONTEND_SECRET_REFS="${FRONTEND_SECRET_REFS%,}"

cat > "${CLOUD_ENV}" <<EOF
# Auto-generated by deploy/setup-env.sh — do NOT commit this file.
CLOUD_ENV_VARS=${ENV_VARS}
CLOUD_SECRET_REFS=${SECRET_REFS}
CLOUD_FRONTEND_SECRET_REFS=${FRONTEND_SECRET_REFS}
EOF
log "Saved ${CLOUD_ENV}"

# ════════════════════════════════════════════════════════
# PHASE 3 — gcloud: enable API, upsert secrets, grant IAM
# ════════════════════════════════════════════════════════
log "Enabling Secret Manager API..."
gcloud services enable secretmanager.googleapis.com --project="${PROJECT_ID}"

upsert_secret() {
  local secret_name="$1" secret_value="$2"
  [[ -z "${secret_value}" ]] && { warn "Skipping empty secret: ${secret_name}"; return; }
  if gcloud secrets describe "${secret_name}" --project="${PROJECT_ID}" &>/dev/null; then
    printf '%s' "${secret_value}" | gcloud secrets versions add "${secret_name}" \
      --data-file=- --project="${PROJECT_ID}" --quiet
    log "Updated: ${secret_name}"
  else
    printf '%s' "${secret_value}" | gcloud secrets create "${secret_name}" \
      --data-file=- --replication-policy=automatic --project="${PROJECT_ID}"
    log "Created: ${secret_name}"
  fi
}

log "Storing secrets..."
while read -r env_key secret_name; do
  [[ -z "${env_key}" ]] && continue
  val="$(grep "^${env_key}=" "${CONFIRMED_FILE}" | head -1 | cut -d= -f2-)"
  upsert_secret "${secret_name}" "${val}"
done < <(echo "${SECRET_KEYS}" | awk 'NF>=2{print $1, $2}')

STORAGE_ENV="${REPO_ROOT}/.storage-env"
[[ -f "${STORAGE_ENV}" ]] || err "Missing .storage-env. Run ./deploy/google-cloud/deploy.sh setup-storage first."
# shellcheck source=/dev/null
source "${STORAGE_ENV}"
[[ -n "${SA_EMAIL:-}" ]] || err "SA_EMAIL is missing from .storage-env."
[[ -n "${FRONTEND_SA_EMAIL:-}" ]] || err "FRONTEND_SA_EMAIL is missing from .storage-env; rerun setup-storage."

grant_secret_access() {
  local secret_name="$1" service_account="$2"
  gcloud secrets add-iam-policy-binding "${secret_name}" \
    --member="serviceAccount:${service_account}" \
    --role="roles/secretmanager.secretAccessor" \
    --condition=None \
    --project="${PROJECT_ID}" \
    --quiet
}

log "Granting secret-level access to the backend and frontend service accounts..."
while read -r env_key secret_name; do
  [[ -z "${env_key}" ]] && continue
  val="$(grep "^${env_key}=" "${CONFIRMED_FILE}" | head -1 | cut -d= -f2-)"
  [[ -n "${val}" ]] || continue
  case "${env_key}" in
    INK_DREAM_BFF_COOKIE_SECRET)
      grant_secret_access "${secret_name}" "${FRONTEND_SA_EMAIL}"
      ;;
    INK_ADMIN_DREAM_SERVICE_SECRET)
      grant_secret_access "${secret_name}" "${SA_EMAIL}"
      grant_secret_access "${secret_name}" "${FRONTEND_SA_EMAIL}"
      ;;
    *)
      grant_secret_access "${secret_name}" "${SA_EMAIL}"
      ;;
  esac
done < <(echo "${SECRET_KEYS}" | awk 'NF>=2{print $1, $2}')

remove_project_secret_accessor() {
  local service_account="$1"
  if gcloud projects get-iam-policy "${PROJECT_ID}" \
      --flatten='bindings[].members' \
      --filter="bindings.role=roles/secretmanager.secretAccessor AND bindings.members=serviceAccount:${service_account}" \
      --format='value(bindings.role)' | grep -q .; then
    log "Removing obsolete project-wide Secret Accessor from ${service_account}..."
    gcloud projects remove-iam-policy-binding "${PROJECT_ID}" \
      --member="serviceAccount:${service_account}" \
      --role="roles/secretmanager.secretAccessor" \
      --condition=None \
      --quiet
  fi
}

remove_project_secret_accessor "${SA_EMAIL}"
remove_project_secret_accessor "${FRONTEND_SA_EMAIL}"

echo ""
info "════════════════════════════════════════════════════════"
info "  Done. Next step: ./deploy/google-cloud/deploy.sh deploy"
info "════════════════════════════════════════════════════════"
