#!/usr/bin/env bash
# [Input] deploy/google-cloud setup scripts, .storage-env, .cloud-env, backend/frontend Dockerfiles, Artifact Registry, Cloud Run service settings.
# [Output] Full Google Cloud Run release workflow with frontend runtime API config and backend CORS origin update.
# [Pos] platform release entry in deploy/google-cloud/
# [Sync] 2026-06-12: promote this directory entry to the full Cloud Run deploy implementation.
# [Sync] 2026-06-12: deployment summary prints original Cloud Run gateways separately from fixed public domains.
# [Sync] 2026-06-12: add backup-data command for local bak_<date> cloud SQLite snapshots before maintenance.
# [Sync] 2026-06-12: call setup-storage/sync-data implementations from deploy/google-cloud instead of deploy/ root.
# [Sync] 2026-06-14: build frontend with public SEO URL and update backend SEO public URL envs.
# [Sync] 2026-06-15: remove /ink-and-memory frontend path prefix from Cloud Run public URLs.
# [Historical Sync] 2026-06-23: projected Dream OAuth/cookie/session defaults before the Admin-auth cutover.
# [Sync] 2026-09-16: remove retired FastAPI session-cookie policy and secret bindings from Cloud Run revisions.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LEGACY_DEPLOY_DIR="${REPO_ROOT}/deploy"
CLOUD_DEPLOY_DIR="${SCRIPT_DIR}"
STORAGE_ENV="${REPO_ROOT}/.storage-env"
CLOUD_ENV="${REPO_ROOT}/.cloud-env"

PROJECT_ID="${GCP_PROJECT_ID:-}"
REGION="${GCP_REGION:-asia-east1}"
REPO_NAME="${REPO_NAME:-ink-and-memory}"
BACKEND_SERVICE="${BACKEND_SERVICE:-ink-backend}"
FRONTEND_SERVICE="${FRONTEND_SERVICE:-ink-frontend}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
BACKEND_PUBLIC_ORIGIN="${BACKEND_PUBLIC_ORIGIN:-https://ink-backend.suoxya.com}"
FRONTEND_PUBLIC_ORIGIN="${FRONTEND_PUBLIC_ORIGIN:-https://ink-frontend.suoxya.com}"

DRY_RUN="${DRY_RUN:-0}"
COMMAND=""

usage() {
  cat <<'EOF'
Usage:
  ./deploy/google-cloud/deploy.sh [--dry-run] <command>
  ./deploy/google-cloud/deploy.sh --check
  ./deploy/google-cloud/deploy.sh --help

Commands:
  check          Validate Google Cloud release prerequisites.
  plan           Print the first-deploy and repeat-deploy command sequence.
  setup-storage  Run deploy/google-cloud/setup-storage.sh.
  setup-env      Run legacy deploy/setup-env.sh.
  deploy         Build images, push to Artifact Registry, deploy Cloud Run services, and update backend CORS.
  release        Alias for deploy.
  sync-data      Fail closed: Dream SQLite synchronization is retired.
  backup-data    Fail closed: Dream SQLite backup is retired.
  verify         Read Cloud Run frontend/backend service URLs.
  rollback       Route traffic to BACKEND_REVISION and/or FRONTEND_REVISION.
  clean          Print cleanup guidance; does not delete cloud resources.

Environment overrides:
  GCP_PROJECT_ID              required for non-dry-run cloud commands
  GCP_REGION                  default: asia-east1
  REPO_NAME                   default: ink-and-memory
  IMAGE_TAG                   default: latest
  BACKEND_SERVICE             default: ink-backend
  FRONTEND_SERVICE            default: ink-frontend
  BACKEND_PUBLIC_ORIGIN       default: https://ink-backend.suoxya.com
  FRONTEND_PUBLIC_ORIGIN      default: https://ink-frontend.suoxya.com
  FRONTEND_API_BASE_URL       default: BACKEND_PUBLIC_ORIGIN
  WS_BASE_URL                 optional explicit browser WebSocket origin
  BACKEND_CORS_ALLOW_ORIGINS  default: FRONTEND_PUBLIC_ORIGIN
  INK_CORS_ALLOW_CREDENTIALS  default: true
  INK_ADMIN_DREAM_BASE_URL    required Admin auth/data service origin
  INK_ADMIN_AUTH_ISSUER       required Admin OAuth/JWT issuer
  INK_DREAM_API_RESOURCE      required Dream API resource identifier
  INK_ADMIN_DREAM_SERVICE_CLIENT_ID required registered Dream service client
  CLOUD_FRONTEND_SECRET_REFS  required Secret Manager refs for
                              INK_ADMIN_DREAM_SERVICE_SECRET and
                              INK_DREAM_BFF_COOKIE_SECRET
  BACKEND_REVISION            required for backend rollback
  FRONTEND_REVISION           required for frontend rollback

Generated config inputs:
  .storage-env  from ./deploy/google-cloud/setup-storage.sh
  .cloud-env    from ./deploy/google-cloud/deploy.sh setup-env

Legacy compatible commands:
  ./deploy/setup-storage.sh  -> ./deploy/google-cloud/setup-storage.sh
  ./deploy/setup-env.sh      -> ./deploy/google-cloud/deploy.sh setup-env
  ./deploy/deploy.sh         -> ./deploy/google-cloud/deploy.sh deploy
  ./deploy/sync-data.sh      -> ./deploy/google-cloud/sync-data.sh
EOF
}

log() { printf '[google-cloud] %s\n' "$*"; }
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

run_parallel_builds() {
  local backend_image="$1" frontend_image="$2" frontend_public_site_url="$3"
  if [[ "${DRY_RUN}" == "1" ]]; then
    print_cmd docker build --no-cache --platform linux/amd64 --tag "${backend_image}" "${REPO_ROOT}/backend/"
    print_cmd docker build --platform linux/amd64 --build-arg "VITE_PUBLIC_SITE_URL=${frontend_public_site_url}" --tag "${frontend_image}" "${REPO_ROOT}/frontend/"
    return 0
  fi
  docker build --no-cache --platform linux/amd64 --tag "${backend_image}" "${REPO_ROOT}/backend/" &
  docker build --platform linux/amd64 --build-arg "VITE_PUBLIC_SITE_URL=${frontend_public_site_url}" --tag "${frontend_image}" "${REPO_ROOT}/frontend/" &
  wait
}

run_parallel_pushes() {
  local backend_image="$1" frontend_image="$2"
  if [[ "${DRY_RUN}" == "1" ]]; then
    print_cmd docker push "${backend_image}"
    print_cmd docker push "${frontend_image}"
    return 0
  fi
  docker push "${backend_image}" &
  docker push "${frontend_image}" &
  wait
}

normalize_origin_list() {
  local raw="$1"
  local result="" item trimmed
  local -a items
  IFS=',' read -ra items <<< "${raw}"
  for item in "${items[@]}"; do
    trimmed="${item#"${item%%[![:space:]]*}"}"
    trimmed="${trimmed%"${trimmed##*[![:space:]]}"}"
    trimmed="${trimmed%/}"
    [[ -z "${trimmed}" ]] && continue
    if [[ -n "${result}" ]]; then
      result+=",${trimmed}"
    else
      result="${trimmed}"
    fi
  done
  printf '%s\n' "${result}"
}

env_vars_to_delimited() {
  local raw="$1"
  shift || true
  local result="" item key denied_key denied
  local -a entries denied_keys
  denied_keys=("$@")
  IFS=',' read -ra entries <<< "${raw}"
  for item in "${entries[@]}"; do
    [[ -z "${item}" ]] && continue
    key="${item%%=*}"
    denied=0
    for denied_key in "${denied_keys[@]}"; do
      if [[ "${key}" == "${denied_key}" ]]; then
        denied=1
        break
      fi
    done
    [[ "${denied}" == "1" ]] && continue
    if [[ -n "${result}" ]]; then
      result+="|${item}"
    else
      result="${item}"
    fi
  done
  printf '%s\n' "${result}"
}

env_var_value() {
  local raw="$1" wanted="$2" item
  local -a entries
  IFS=',' read -ra entries <<< "${raw}"
  for item in "${entries[@]}"; do
    if [[ "${item%%=*}" == "${wanted}" ]]; then
      printf '%s\n' "${item#*=}"
      return 0
    fi
  done
}

csv_keys() {
  local raw="$1" item key result=""
  local -a entries
  IFS=',' read -ra entries <<< "${raw}"
  for item in "${entries[@]}"; do
    [[ -z "${item}" ]] && continue
    key="${item%%=*}"
    if [[ -n "${result}" ]]; then
      result+=",${key}"
    else
      result="${key}"
    fi
  done
  printf '%s\n' "${result}"
}

sanitize_secret_refs() {
  local raw="$1"
  local result="" item key
  local -a entries
  IFS=',' read -ra entries <<< "${raw}"
  for item in "${entries[@]}"; do
    [[ -z "${item}" ]] && continue
    key="${item%%=*}"
    case "${key}" in
      GOOGLE_CLIENT_SECRET|JWT_SECRET|JWT_SECRET_KEY|SESSION_SECRET_KEY|OAUTH_TOKEN_ENCRYPTION_KEY|AUTH_TOKEN_ENCRYPTION_KEY|INK_DREAM_BFF_COOKIE_SECRET)
        continue
        ;;
    esac
    if [[ -n "${result}" ]]; then
      result+=",${item}"
    else
      result="${item}"
    fi
  done
  printf '%s\n' "${result}"
}

validate_frontend_secret_refs() {
  local raw="$1" item key value result=""
  local service_secret_seen=0 cookie_secret_seen=0
  local -a entries
  IFS=',' read -ra entries <<< "${raw}"
  for item in "${entries[@]}"; do
    [[ -z "${item}" ]] && continue
    key="${item%%=*}"
    value="${item#*=}"
    [[ "${item}" == *=* && -n "${value}" ]] || err "CLOUD_FRONTEND_SECRET_REFS contains an invalid Secret Manager reference."
    case "${key}" in
      INK_ADMIN_DREAM_SERVICE_SECRET)
        [[ "${service_secret_seen}" == "0" ]] || err "CLOUD_FRONTEND_SECRET_REFS repeats INK_ADMIN_DREAM_SERVICE_SECRET."
        service_secret_seen=1
        ;;
      INK_DREAM_BFF_COOKIE_SECRET)
        [[ "${cookie_secret_seen}" == "0" ]] || err "CLOUD_FRONTEND_SECRET_REFS repeats INK_DREAM_BFF_COOKIE_SECRET."
        cookie_secret_seen=1
        ;;
      *)
        err "CLOUD_FRONTEND_SECRET_REFS contains unsupported key: ${key}."
        ;;
    esac
    if [[ -n "${result}" ]]; then
      result+=",${item}"
    else
      result="${item}"
    fi
  done
  [[ "${service_secret_seen}" == "1" ]] || err "CLOUD_FRONTEND_SECRET_REFS must bind INK_ADMIN_DREAM_SERVICE_SECRET."
  [[ "${cookie_secret_seen}" == "1" ]] || err "CLOUD_FRONTEND_SECRET_REFS must bind INK_DREAM_BFF_COOKIE_SECRET."
  printf '%s\n' "${result}"
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

require_project() {
  if [[ "${DRY_RUN}" == "1" ]]; then
    log "Would require GCP_PROJECT_ID."
    return 0
  fi
  [[ -n "${PROJECT_ID}" ]] || err "GCP_PROJECT_ID is required. Run: export GCP_PROJECT_ID=your-project-id"
}

effective_project_id() {
  if [[ -n "${PROJECT_ID}" ]]; then
    printf '%s\n' "${PROJECT_ID}"
  else
    printf '%s\n' "your-project-id"
  fi
}

check_base() {
  local failed=0
  require_command gcloud || { warn "gcloud not found."; failed=1; }
  require_command gsutil || { warn "gsutil not found."; failed=1; }
  require_command docker || { warn "docker not found."; failed=1; }
  require_file "${CLOUD_DEPLOY_DIR}/setup-storage.sh" || { warn "Missing deploy/google-cloud/setup-storage.sh."; failed=1; }
  require_file "${LEGACY_DEPLOY_DIR}/setup-env.sh" || { warn "Missing legacy setup-env.sh."; failed=1; }
  require_file "${CLOUD_DEPLOY_DIR}/sync-data.sh" || { warn "Missing deploy/google-cloud/sync-data.sh."; failed=1; }
  require_file "${REPO_ROOT}/backend/Dockerfile" || { warn "Missing backend/Dockerfile."; failed=1; }
  require_file "${REPO_ROOT}/frontend/Dockerfile" || { warn "Missing frontend/Dockerfile."; failed=1; }
  require_file "${REPO_ROOT}/frontend/docker-entrypoint.sh" || { warn "Missing frontend/docker-entrypoint.sh."; failed=1; }
  require_file "${REPO_ROOT}/frontend/public/runtime-config.template.js" || { warn "Missing frontend runtime-config template."; failed=1; }
  if [[ "${DRY_RUN}" != "1" && -z "${PROJECT_ID}" ]]; then
    warn "GCP_PROJECT_ID is not set."
    failed=1
  elif [[ "${DRY_RUN}" == "1" ]]; then
    log "Would check GCP_PROJECT_ID."
  fi
  if [[ "${DRY_RUN}" != "1" ]]; then
    [[ -f "${STORAGE_ENV}" ]] || warn ".storage-env is missing; run setup-storage before deploy."
    [[ -f "${CLOUD_ENV}" ]] || warn ".cloud-env is missing; run setup-env before deploy."
  else
    log "Would check generated files: ${STORAGE_ENV}, ${CLOUD_ENV}"
  fi
  if [[ "${failed}" == "1" ]]; then
    return 1
  fi
  log "Google Cloud prerequisites look usable."
}

load_generated_env() {
  if [[ "${DRY_RUN}" == "1" ]]; then
    if [[ -f "${STORAGE_ENV}" ]]; then
      # shellcheck source=/dev/null
      source "${STORAGE_ENV}"
    else
      GCS_BUCKET="${GCS_BUCKET:-ink-memory-data-$(effective_project_id)}"
      SA_EMAIL="${SA_EMAIL:-ink-backend-sa@$(effective_project_id).iam.gserviceaccount.com}"
    fi
    if [[ -f "${CLOUD_ENV}" ]]; then
      # shellcheck source=/dev/null
      source "${CLOUD_ENV}"
    else
      CLOUD_ENV_VARS="${CLOUD_ENV_VARS:-TZ=UTC}"
      CLOUD_SECRET_REFS="${CLOUD_SECRET_REFS:-}"
      CLOUD_FRONTEND_SECRET_REFS="${CLOUD_FRONTEND_SECRET_REFS:-}"
    fi
    return 0
  fi

  [[ -f "${STORAGE_ENV}" ]] || err "Missing .storage-env. Run ./deploy/google-cloud/deploy.sh setup-storage first."
  [[ -f "${CLOUD_ENV}" ]] || err "Missing .cloud-env. Run ./deploy/google-cloud/deploy.sh setup-env first."
  # shellcheck source=/dev/null
  source "${STORAGE_ENV}"
  # shellcheck source=/dev/null
  source "${CLOUD_ENV}"
}

command_plan() {
  cat <<'EOF'
First deploy:
  export GCP_PROJECT_ID=your-project-id
  ./deploy/google-cloud/deploy.sh setup-storage
  ./deploy/google-cloud/deploy.sh setup-env
  ./deploy/google-cloud/deploy.sh deploy

Repeat deploy:
  ./deploy/google-cloud/deploy.sh deploy

Fixed public domain defaults / override:
  export BACKEND_PUBLIC_ORIGIN=https://ink-backend.suoxya.com
  export FRONTEND_PUBLIC_ORIGIN=https://ink-frontend.suoxya.com
  ./deploy/google-cloud/deploy.sh deploy

Secrets or env changed:
  ./deploy/google-cloud/deploy.sh setup-env
  ./deploy/google-cloud/deploy.sh deploy

Retired database commands (both fail closed):
  ./deploy/google-cloud/deploy.sh sync-data
  ./deploy/google-cloud/deploy.sh backup-data
EOF
}

run_legacy() {
  local script="$1"
  shift || true
  require_file "${LEGACY_DEPLOY_DIR}/${script}" || err "Missing legacy script: deploy/${script}"
  run "${LEGACY_DEPLOY_DIR}/${script}" "$@"
}

run_cloud_script() {
  local script="$1"
  shift || true
  require_file "${CLOUD_DEPLOY_DIR}/${script}" || err "Missing Google Cloud script: deploy/google-cloud/${script}"
  run "${CLOUD_DEPLOY_DIR}/${script}" "$@"
}

ensure_artifact_repo() {
  local project_id="$1"
  if [[ "${DRY_RUN}" == "1" ]]; then
    print_cmd gcloud artifacts repositories describe "${REPO_NAME}" --location="${REGION}" --project="${project_id}"
    print_cmd gcloud artifacts repositories create "${REPO_NAME}" --repository-format=docker --location="${REGION}" --description="Ink and Memory container images" --project="${project_id}"
    return 0
  fi

  if ! gcloud artifacts repositories describe "${REPO_NAME}" \
      --location="${REGION}" --project="${project_id}" &>/dev/null; then
    gcloud artifacts repositories create "${REPO_NAME}" \
      --repository-format=docker \
      --location="${REGION}" \
      --description="Ink and Memory container images" \
      --project="${project_id}"
    log "Repository created."
  else
    log "Repository already exists, skipping."
  fi
}

describe_service_url() {
  local service="$1" project_id="$2" fallback="$3"
  if [[ "${DRY_RUN}" == "1" ]]; then
    print_cmd gcloud run services describe "${service}" --region="${REGION}" --project="${project_id}" --format="value(status.url)" >&2
    printf '%s\n' "${fallback}"
    return 0
  fi
  gcloud run services describe "${service}" \
    --region="${REGION}" \
    --project="${project_id}" \
    --format="value(status.url)"
}

command_deploy() {
  require_project
  check_base
  load_generated_env

  if [[ "${DRY_RUN}" == "1" ]]; then
    FRONTEND_SA_EMAIL="${FRONTEND_SA_EMAIL:-ink-frontend-sa@$(effective_project_id).iam.gserviceaccount.com}"
  fi
  [[ -n "${FRONTEND_SA_EMAIL:-}" ]] || err "FRONTEND_SA_EMAIL is missing from .storage-env; rerun setup-storage."

  local project_id registry backend_image frontend_image frontend_public_origin frontend_public_site_url
  project_id="$(effective_project_id)"
  registry="${REGION}-docker.pkg.dev/${project_id}/${REPO_NAME}"
  backend_image="${registry}/ink-backend:${IMAGE_TAG}"
  frontend_image="${registry}/ink-frontend:${IMAGE_TAG}"
  frontend_public_origin="$(normalize_origin_list "${FRONTEND_PUBLIC_ORIGIN}")"
  frontend_public_site_url="${frontend_public_origin%/}/"
  local backend_public_origin frontend_api_base_url cors_origins cors_credentials
  backend_public_origin="$(normalize_origin_list "${BACKEND_PUBLIC_ORIGIN}")"
  frontend_api_base_url="${FRONTEND_API_BASE_URL:-${backend_public_origin}}"
  cors_origins="$(normalize_origin_list "${BACKEND_CORS_ALLOW_ORIGINS:-${frontend_public_origin}}")"
  cors_credentials="${INK_CORS_ALLOW_CREDENTIALS:-true}"

  local admin_dream_base_url admin_auth_issuer dream_api_resource dream_service_client_id
  local dream_public_origin dream_bff_redirect_uri frontend_secret_refs
  admin_dream_base_url="${INK_ADMIN_DREAM_BASE_URL:-$(env_var_value "${CLOUD_ENV_VARS:-}" INK_ADMIN_DREAM_BASE_URL)}"
  admin_auth_issuer="${INK_ADMIN_AUTH_ISSUER:-$(env_var_value "${CLOUD_ENV_VARS:-}" INK_ADMIN_AUTH_ISSUER)}"
  dream_api_resource="${INK_DREAM_API_RESOURCE:-$(env_var_value "${CLOUD_ENV_VARS:-}" INK_DREAM_API_RESOURCE)}"
  dream_service_client_id="${INK_ADMIN_DREAM_SERVICE_CLIENT_ID:-$(env_var_value "${CLOUD_ENV_VARS:-}" INK_ADMIN_DREAM_SERVICE_CLIENT_ID)}"
  dream_public_origin="${INK_DREAM_PUBLIC_ORIGIN:-${frontend_public_origin}}"
  dream_bff_redirect_uri="${INK_DREAM_BFF_REDIRECT_URI:-${dream_public_origin%/}/auth/callback}"
  if [[ "${DRY_RUN}" == "1" ]]; then
    admin_dream_base_url="${admin_dream_base_url:-https://admin.example.test}"
    admin_auth_issuer="${admin_auth_issuer:-https://admin.example.test/api/auth}"
    dream_api_resource="${dream_api_resource:-https://dream.example.test/api}"
    dream_service_client_id="${dream_service_client_id:-dream-service}"
    CLOUD_FRONTEND_SECRET_REFS="${CLOUD_FRONTEND_SECRET_REFS:-INK_ADMIN_DREAM_SERVICE_SECRET=admin-dream-service:latest,INK_DREAM_BFF_COOKIE_SECRET=dream-bff-cookie:latest}"
  fi
  [[ -n "${admin_dream_base_url}" ]] || err "INK_ADMIN_DREAM_BASE_URL is required for the Cloud Run Next BFF."
  [[ -n "${admin_auth_issuer}" ]] || err "INK_ADMIN_AUTH_ISSUER is required for the Cloud Run Next BFF."
  [[ -n "${dream_api_resource}" ]] || err "INK_DREAM_API_RESOURCE is required for the Cloud Run Next BFF."
  [[ -n "${dream_service_client_id}" ]] || err "INK_ADMIN_DREAM_SERVICE_CLIENT_ID is required for the Cloud Run Next BFF."
  frontend_secret_refs="$(validate_frontend_secret_refs "${CLOUD_FRONTEND_SECRET_REFS:-}")"

  local backend_env_vars_delimited backend_runtime_env_vars
  local -a deploy_owned_keys=(
    WEBUI_URL API_BASE_URL
    GOOGLE_CLIENT_SECRET JWT_SECRET JWT_SECRET_KEY SESSION_SECRET_KEY
    OAUTH_TOKEN_ENCRYPTION_KEY AUTH_TOKEN_ENCRYPTION_KEY
    COOKIE_SECURE COOKIE_SAMESITE INK_ADMIN_DREAM_SERVICE_SECRET INK_DREAM_BFF_COOKIE_SECRET
    INK_CORS_ALLOW_ORIGINS INK_CORS_ALLOW_CREDENTIALS
    INK_PUBLIC_BASE_URL INK_BACKEND_PUBLIC_BASE_URL
  )
  backend_env_vars_delimited="$(env_vars_to_delimited "${CLOUD_ENV_VARS:-TZ=UTC}" "${deploy_owned_keys[@]}")"
  local sanitized_secret_refs
  sanitized_secret_refs="$(sanitize_secret_refs "${CLOUD_SECRET_REFS:-}")"
  backend_runtime_env_vars="WEBUI_URL=${frontend_public_origin}|API_BASE_URL=${backend_public_origin}|INK_CORS_ALLOW_ORIGINS=${cors_origins}|INK_CORS_ALLOW_CREDENTIALS=${cors_credentials}|INK_PUBLIC_BASE_URL=${frontend_public_site_url}|INK_BACKEND_PUBLIC_BASE_URL=${backend_public_origin}"
  if [[ -n "${backend_env_vars_delimited}" ]]; then
    backend_env_vars_delimited+="|${backend_runtime_env_vars}"
  else
    backend_env_vars_delimited="${backend_runtime_env_vars}"
  fi

  log "Storage  : bucket=${GCS_BUCKET}, sa=${SA_EMAIL}"
  log "Env keys  : $(csv_keys "${CLOUD_ENV_VARS:-}")"
  log "Secret keys: $(csv_keys "${sanitized_secret_refs}")"
  log "Runtime  : WEBUI_URL=${frontend_public_origin}, API_BASE_URL=${backend_public_origin}, CORS=${cors_origins}"

  log "Setting GCP project to: ${project_id}"
  run gcloud config set project "${project_id}"

  log "Enabling Cloud Run, Artifact Registry, and Cloud Build APIs..."
  run gcloud services enable \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    --project="${project_id}"

  log "Ensuring Artifact Registry repository '${REPO_NAME}' exists in ${REGION}..."
  ensure_artifact_repo "${project_id}"

  log "Configuring Docker credentials for ${REGION}-docker.pkg.dev..."
  run gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

  log "Building backend and frontend images..."
  run_parallel_builds "${backend_image}" "${frontend_image}" "${frontend_public_site_url}"
  log "Both images built."

  log "Pushing backend and frontend images..."
  run_parallel_pushes "${backend_image}" "${frontend_image}"
  log "Both images pushed."

  log "Deploying backend service to Cloud Run (${REGION})..."
  local backend_flags=(
    --image="${backend_image}"
    --region="${REGION}"
    --platform=managed
    --allow-unauthenticated
    --port=8765
    --memory=1Gi
    --cpu=1
    --min-instances=1
    --max-instances=1
    --timeout=3600
    --cpu-boost
    --service-account="${SA_EMAIL}"
    --add-volume="name=ink-data,type=cloud-storage,bucket=${GCS_BUCKET}"
    --add-volume-mount="volume=ink-data,mount-path=/app/data"
    --set-env-vars="^|^${backend_env_vars_delimited}"
    --project="${project_id}"
  )
  if [[ -n "${sanitized_secret_refs}" ]]; then
    backend_flags+=(--set-secrets="${sanitized_secret_refs}")
  else
    backend_flags+=(--clear-secrets)
  fi
  run gcloud run deploy "${BACKEND_SERVICE}" "${backend_flags[@]}"

  local backend_url
  backend_url="$(describe_service_url "${BACKEND_SERVICE}" "${project_id}" "https://${BACKEND_SERVICE}-example.run.app")"
  log "Backend live at: ${backend_url}"

  log "Deploying frontend service to Cloud Run (${REGION})..."
  local frontend_env_vars
  frontend_env_vars="BACKEND_URL=${backend_url},API_BASE_URL=${frontend_api_base_url},INK_ADMIN_DREAM_BASE_URL=${admin_dream_base_url},INK_ADMIN_AUTH_ISSUER=${admin_auth_issuer},INK_DREAM_API_RESOURCE=${dream_api_resource},INK_ADMIN_DREAM_SERVICE_CLIENT_ID=${dream_service_client_id},INK_DREAM_PUBLIC_ORIGIN=${dream_public_origin},INK_DREAM_BFF_REDIRECT_URI=${dream_bff_redirect_uri}"
  [[ -n "${WS_BASE_URL:-}" ]] && frontend_env_vars+=",WS_BASE_URL=${WS_BASE_URL}"

  run gcloud run deploy "${FRONTEND_SERVICE}" \
    --image="${frontend_image}" \
    --region="${REGION}" \
    --platform=managed \
    --allow-unauthenticated \
    --port=80 \
    --memory=256Mi \
    --cpu=1 \
    --min-instances=0 \
    --max-instances=10 \
    --service-account="${FRONTEND_SA_EMAIL}" \
    --set-env-vars="${frontend_env_vars}" \
    --set-secrets="${frontend_secret_refs}" \
    --project="${project_id}"

  local frontend_url
  frontend_url="$(describe_service_url "${FRONTEND_SERVICE}" "${project_id}" "https://${FRONTEND_SERVICE}-example.run.app")"

  log "Updating backend CORS origin to: ${cors_origins}"
  log "Updating backend public URLs and CORS policy."
  log "Updating backend public SEO app URL to: ${frontend_public_site_url}"
  log "Updating backend public SEO API origin to: ${backend_public_origin}"
  run gcloud run services update "${BACKEND_SERVICE}" \
    --region="${REGION}" \
    --project="${project_id}" \
    --update-env-vars="^|^WEBUI_URL=${frontend_public_origin}|API_BASE_URL=${backend_public_origin}|INK_CORS_ALLOW_ORIGINS=${cors_origins}|INK_CORS_ALLOW_CREDENTIALS=${cors_credentials}|INK_PUBLIC_BASE_URL=${frontend_public_site_url}|INK_BACKEND_PUBLIC_BASE_URL=${backend_public_origin}" \
    --quiet

  echo ""
  log "============================================"
  log "  Deployment complete!"
  log "  Original Cloud Run frontend gateway : ${frontend_url}/"
  log "  Original Cloud Run backend gateway  : ${backend_url}"
  log "  Public frontend                     : ${frontend_public_site_url}"
  log "  Public backend                      : ${backend_public_origin}"
  log "  API base                            : ${frontend_api_base_url}"
  log "  CORS                                : ${cors_origins}"
  log "============================================"
  echo ""
  warn "SQLite WAL note: backend is capped at max-instances=1 to prevent"
  warn "concurrent write conflicts on the shared GCS FUSE mount (gs://${GCS_BUCKET})."
}

command_verify() {
  require_project
  require_command gcloud || err "gcloud not found."
  local project_id
  project_id="$(effective_project_id)"
  run gcloud run services describe "${BACKEND_SERVICE}" \
    --region="${REGION}" \
    --project="${project_id}" \
    --format="value(status.url)"
  run gcloud run services describe "${FRONTEND_SERVICE}" \
    --region="${REGION}" \
    --project="${project_id}" \
    --format="value(status.url)"
}

command_rollback() {
  require_project
  require_command gcloud || err "gcloud not found."
  if [[ -z "${BACKEND_REVISION:-}" && -z "${FRONTEND_REVISION:-}" ]]; then
    err "Set BACKEND_REVISION and/or FRONTEND_REVISION before rollback."
  fi
  local project_id
  project_id="$(effective_project_id)"
  if [[ -n "${BACKEND_REVISION:-}" ]]; then
    run gcloud run services update-traffic "${BACKEND_SERVICE}" \
      --to-revisions="${BACKEND_REVISION}=100" \
      --region="${REGION}" \
      --project="${project_id}"
  fi
  if [[ -n "${FRONTEND_REVISION:-}" ]]; then
    run gcloud run services update-traffic "${FRONTEND_SERVICE}" \
      --to-revisions="${FRONTEND_REVISION}=100" \
      --region="${REGION}" \
      --project="${project_id}"
  fi
}

command_clean() {
  cat <<EOF
Cleanup is intentionally manual because it can delete production services and data.

Review resources first:
  gcloud run services list --region=${REGION} --project=\${GCP_PROJECT_ID}
  gcloud artifacts repositories list --location=${REGION} --project=\${GCP_PROJECT_ID}
  gsutil ls -b gs://\${GCS_BUCKET}
  gcloud secrets list --project=\${GCP_PROJECT_ID}

Delete only after backup and explicit approval:
  gcloud run services delete ${FRONTEND_SERVICE} --region=${REGION} --project=\${GCP_PROJECT_ID}
  gcloud run services delete ${BACKEND_SERVICE} --region=${REGION} --project=\${GCP_PROJECT_ID}
EOF
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
  check) check_base ;;
  plan) command_plan ;;
  setup-storage) require_project; require_command gcloud || err "gcloud not found."; require_command gsutil || err "gsutil not found."; run_cloud_script setup-storage.sh ;;
  setup-env) require_project; require_command gcloud || err "gcloud not found."; run_legacy setup-env.sh ;;
  deploy|release) command_deploy ;;
  sync-data) require_project; check_base; load_generated_env; run_cloud_script sync-data.sh upload ;;
  backup-data|backup-cloud|download-data)
    require_project
    require_command gsutil || err "gsutil not found."
    require_file "${CLOUD_DEPLOY_DIR}/sync-data.sh" || err "Missing deploy/google-cloud/sync-data.sh."
    run_cloud_script sync-data.sh backup-cloud
    ;;
  verify) command_verify ;;
  rollback) command_rollback ;;
  clean) command_clean ;;
  *) err "Unknown command: ${COMMAND}. Run --help." ;;
esac
