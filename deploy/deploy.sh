#!/usr/bin/env bash
# deploy/deploy.sh — Build and deploy Ink & Memory to Google Cloud Run.
#
# Usage:
#   export GCP_PROJECT_ID=your-project-id
#   ./deploy/deploy.sh
#
# Optional overrides (export before running):
#   GCP_REGION        default: asia-east1
#   REPO_NAME         default: ink-and-memory
#   BACKEND_SERVICE   default: ink-backend
#   FRONTEND_SERVICE  default: ink-frontend
#
# Prerequisites (run once before first deploy):
#   1. ./deploy/setup-storage.sh  — creates GCS bucket + service account
#   2. ./deploy/setup-env.sh      — stores secrets + writes .cloud-env
#   3. gcloud auth login && docker running
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# ── Config ────────────────────────────────────────────────────────────────────
PROJECT_ID="${GCP_PROJECT_ID:?ERROR: GCP_PROJECT_ID is not set. Run: export GCP_PROJECT_ID=your-project-id}"
REGION="${GCP_REGION:-asia-east1}"
REPO_NAME="${REPO_NAME:-ink-and-memory}"
BACKEND_SERVICE="${BACKEND_SERVICE:-ink-backend}"
FRONTEND_SERVICE="${FRONTEND_SERVICE:-ink-frontend}"

REGISTRY="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}"
BACKEND_IMAGE="${REGISTRY}/ink-backend:latest"
FRONTEND_IMAGE="${REGISTRY}/ink-frontend:latest"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log()  { echo -e "${GREEN}[deploy]${NC} $*"; }
warn() { echo -e "${YELLOW}[warn]${NC}  $*"; }
err()  { echo -e "${RED}[error]${NC} $*" >&2; exit 1; }

# ── Step 0: sanity checks ─────────────────────────────────────────────────────
log "Checking prerequisites..."
command -v gcloud >/dev/null 2>&1 || err "gcloud CLI not found. Install: https://cloud.google.com/sdk/docs/install"
command -v docker  >/dev/null 2>&1 || err "Docker not found."

# Load storage config (GCS_BUCKET, SA_EMAIL) written by setup-storage.sh
STORAGE_ENV="${REPO_ROOT}/.storage-env"
[[ -f "${STORAGE_ENV}" ]] || err "Storage config missing. Run ./deploy/setup-storage.sh first."
# shellcheck source=/dev/null
source "${STORAGE_ENV}"
log "Storage  : bucket=${GCS_BUCKET}, sa=${SA_EMAIL}"

# Load environment config (CLOUD_ENV_VARS, CLOUD_SECRET_REFS) written by setup-env.sh
CLOUD_ENV="${REPO_ROOT}/.cloud-env"
[[ -f "${CLOUD_ENV}" ]] || err "Env config missing. Run ./deploy/setup-env.sh first."
# shellcheck source=/dev/null
source "${CLOUD_ENV}"
log "Env vars : ${CLOUD_ENV_VARS}"
log "Secrets  : ${CLOUD_SECRET_REFS}"

# ── Step 1: set GCP project ───────────────────────────────────────────────────
log "Setting GCP project to: ${PROJECT_ID}"
gcloud config set project "${PROJECT_ID}"

# ── Step 2: enable required APIs ─────────────────────────────────────────────
log "Enabling Cloud Run, Artifact Registry, and Cloud Build APIs..."
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  --project="${PROJECT_ID}"

# ── Step 3: create Artifact Registry repo (idempotent) ───────────────────────
log "Ensuring Artifact Registry repository '${REPO_NAME}' exists in ${REGION}..."
if ! gcloud artifacts repositories describe "${REPO_NAME}" \
      --location="${REGION}" --project="${PROJECT_ID}" &>/dev/null; then
  gcloud artifacts repositories create "${REPO_NAME}" \
    --repository-format=docker \
    --location="${REGION}" \
    --description="Ink and Memory container images" \
    --project="${PROJECT_ID}"
  log "Repository created."
else
  log "Repository already exists, skipping."
fi

# ── Step 4: configure Docker auth ────────────────────────────────────────────
log "Configuring Docker credentials for ${REGION}-docker.pkg.dev..."
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

# ── Step 5: build both images in parallel ────────────────────────────────────
log "Building backend and frontend images in parallel..."
docker build --platform linux/amd64 --tag "${BACKEND_IMAGE}" "${REPO_ROOT}/backend/" &
docker build --platform linux/amd64 --tag "${FRONTEND_IMAGE}" "${REPO_ROOT}/frontend/" &
wait
log "Both images built."

# ── Step 6: push both images in parallel ─────────────────────────────────────
log "Pushing both images to Artifact Registry..."
docker push "${BACKEND_IMAGE}" &
docker push "${FRONTEND_IMAGE}" &
wait
log "Both images pushed."

# ── Step 7: deploy both services to Cloud Run ────────────────────────────────

log "Deploying backend service to Cloud Run (${REGION})..."

# Build deploy flags conditionally
BACKEND_FLAGS=(
  --image="${BACKEND_IMAGE}"
  --region="${REGION}"
  --platform=managed
  --allow-unauthenticated
  --port=8765
  --memory=1Gi
  --cpu=1
  --min-instances=1
  --max-instances=1
  --timeout=3600
  --startup-cpu-boost
  --service-account="${SA_EMAIL}"
  --add-volume="name=ink-data,type=cloud-storage,bucket=${GCS_BUCKET}"
  --add-volume-mount="volume=ink-data,mount-path=/app/data"
  --set-env-vars="${CLOUD_ENV_VARS}"
  --project="${PROJECT_ID}"
)
[[ -n "${CLOUD_SECRET_REFS}" ]] && BACKEND_FLAGS+=(--set-secrets="${CLOUD_SECRET_REFS}")

gcloud run deploy "${BACKEND_SERVICE}" "${BACKEND_FLAGS[@]}"

BACKEND_URL=$(gcloud run services describe "${BACKEND_SERVICE}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --format="value(status.url)")

log "Backend live at: ${BACKEND_URL}"

log "Deploying frontend service to Cloud Run (${REGION})..."
gcloud run deploy "${FRONTEND_SERVICE}" \
  --image="${FRONTEND_IMAGE}" \
  --region="${REGION}" \
  --platform=managed \
  --allow-unauthenticated \
  --port=80 \
  --memory=256Mi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=10 \
  --set-env-vars="BACKEND_URL=${BACKEND_URL}" \
  --project="${PROJECT_ID}"

FRONTEND_URL=$(gcloud run services describe "${FRONTEND_SERVICE}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --format="value(status.url)")

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
log "════════════════════════════════════════════"
log "  Deployment complete!"
log "  Frontend : ${FRONTEND_URL}/ink-and-memory/"
log "  Backend  : ${BACKEND_URL}"
log "════════════════════════════════════════════"
echo ""
warn "SQLite WAL note: backend is capped at max-instances=1 to prevent"
warn "concurrent write conflicts on the shared GCS FUSE mount (gs://${GCS_BUCKET})."
