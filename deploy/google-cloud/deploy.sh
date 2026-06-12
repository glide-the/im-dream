#!/usr/bin/env bash
# [Input] deploy/setup-storage.sh, deploy/setup-env.sh, deploy/deploy.sh, deploy/sync-data.sh.
# [Output] Directory-scoped Google Cloud Run release entry with check, dry-run, verify, and rollback helpers.
# [Pos] platform release entry in deploy/google-cloud/
# [Sync] 2026-06-12: add platform-scoped Google Cloud release wrapper while preserving legacy root scripts.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LEGACY_DEPLOY_DIR="${REPO_ROOT}/deploy"
STORAGE_ENV="${REPO_ROOT}/.storage-env"
CLOUD_ENV="${REPO_ROOT}/.cloud-env"

PROJECT_ID="${GCP_PROJECT_ID:-}"
REGION="${GCP_REGION:-asia-east1}"
BACKEND_SERVICE="${BACKEND_SERVICE:-ink-backend}"
FRONTEND_SERVICE="${FRONTEND_SERVICE:-ink-frontend}"

DRY_RUN=0
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
  setup-storage  Run legacy deploy/setup-storage.sh.
  setup-env      Run legacy deploy/setup-env.sh.
  deploy         Run legacy deploy/deploy.sh.
  release        Alias for deploy.
  sync-data      Run legacy deploy/sync-data.sh.
  verify         Read Cloud Run frontend/backend service URLs.
  rollback       Route traffic to BACKEND_REVISION and/or FRONTEND_REVISION.
  clean          Print cleanup guidance; does not delete cloud resources.

Environment overrides:
  GCP_PROJECT_ID       required for non-dry-run cloud commands
  GCP_REGION           default: asia-east1
  BACKEND_SERVICE      default: ink-backend
  FRONTEND_SERVICE     default: ink-frontend
  BACKEND_REVISION     required for backend rollback
  FRONTEND_REVISION    required for frontend rollback

Legacy compatible commands:
  ./deploy/setup-storage.sh  -> ./deploy/google-cloud/deploy.sh setup-storage
  ./deploy/setup-env.sh      -> ./deploy/google-cloud/deploy.sh setup-env
  ./deploy/deploy.sh         -> ./deploy/google-cloud/deploy.sh deploy
  ./deploy/sync-data.sh      -> ./deploy/google-cloud/deploy.sh sync-data
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

check_base() {
  local failed=0
  require_command gcloud || { warn "gcloud not found."; failed=1; }
  require_command gsutil || { warn "gsutil not found."; failed=1; }
  require_command docker || { warn "docker not found."; failed=1; }
  require_file "${LEGACY_DEPLOY_DIR}/setup-storage.sh" || { warn "Missing legacy setup-storage.sh."; failed=1; }
  require_file "${LEGACY_DEPLOY_DIR}/setup-env.sh" || { warn "Missing legacy setup-env.sh."; failed=1; }
  require_file "${LEGACY_DEPLOY_DIR}/deploy.sh" || { warn "Missing legacy deploy.sh."; failed=1; }
  require_file "${LEGACY_DEPLOY_DIR}/sync-data.sh" || { warn "Missing legacy sync-data.sh."; failed=1; }
  if [[ "${DRY_RUN}" != "1" && -z "${PROJECT_ID}" ]]; then
    warn "GCP_PROJECT_ID is not set."
    failed=1
  elif [[ "${DRY_RUN}" == "1" ]]; then
    log "Would check GCP_PROJECT_ID."
  fi
  if [[ "${DRY_RUN}" != "1" ]]; then
    [[ -f "${STORAGE_ENV}" ]] || warn ".storage-env is missing; run setup-storage before deploy or sync-data."
    [[ -f "${CLOUD_ENV}" ]] || warn ".cloud-env is missing; run setup-env before deploy or sync-data."
  else
    log "Would check generated files: ${STORAGE_ENV}, ${CLOUD_ENV}"
  fi
  if [[ "${failed}" == "1" ]]; then
    return 1
  fi
  log "Google Cloud prerequisites look usable."
}

require_generated_env() {
  require_file "${STORAGE_ENV}" || err "Missing .storage-env. Run ./deploy/google-cloud/deploy.sh setup-storage first."
  require_file "${CLOUD_ENV}" || err "Missing .cloud-env. Run ./deploy/google-cloud/deploy.sh setup-env first."
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

Secrets or env changed:
  ./deploy/google-cloud/deploy.sh setup-env
  ./deploy/google-cloud/deploy.sh deploy

Data upload:
  ./deploy/google-cloud/deploy.sh sync-data
EOF
}

run_legacy() {
  local script="$1"
  shift || true
  require_file "${LEGACY_DEPLOY_DIR}/${script}" || err "Missing legacy script: deploy/${script}"
  run "${LEGACY_DEPLOY_DIR}/${script}" "$@"
}

command_verify() {
  require_project
  require_command gcloud || err "gcloud not found."
  run gcloud run services describe "${BACKEND_SERVICE}" \
    --region="${REGION}" \
    --project="${PROJECT_ID}" \
    --format="value(status.url)"
  run gcloud run services describe "${FRONTEND_SERVICE}" \
    --region="${REGION}" \
    --project="${PROJECT_ID}" \
    --format="value(status.url)"
}

command_rollback() {
  require_project
  require_command gcloud || err "gcloud not found."
  if [[ -z "${BACKEND_REVISION:-}" && -z "${FRONTEND_REVISION:-}" ]]; then
    err "Set BACKEND_REVISION and/or FRONTEND_REVISION before rollback."
  fi
  if [[ -n "${BACKEND_REVISION:-}" ]]; then
    run gcloud run services update-traffic "${BACKEND_SERVICE}" \
      --to-revisions="${BACKEND_REVISION}=100" \
      --region="${REGION}" \
      --project="${PROJECT_ID}"
  fi
  if [[ -n "${FRONTEND_REVISION:-}" ]]; then
    run gcloud run services update-traffic "${FRONTEND_SERVICE}" \
      --to-revisions="${FRONTEND_REVISION}=100" \
      --region="${REGION}" \
      --project="${PROJECT_ID}"
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
  setup-storage) require_project; require_command gcloud || err "gcloud not found."; require_command gsutil || err "gsutil not found."; run_legacy setup-storage.sh ;;
  setup-env) require_project; require_command gcloud || err "gcloud not found."; run_legacy setup-env.sh ;;
  deploy|release) require_project; check_base; require_generated_env; run_legacy deploy.sh ;;
  sync-data) require_project; check_base; require_generated_env; run_legacy sync-data.sh ;;
  verify) command_verify ;;
  rollback) command_rollback ;;
  clean) command_clean ;;
  *) err "Unknown command: ${COMMAND}. Run --help." ;;
esac
