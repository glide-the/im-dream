#!/usr/bin/env bash
# deploy/sync-data.sh — Upload local backend/data/ to GCS and restart backend.
#
# Usage:
#   export GCP_PROJECT_ID=your-project-id
#   ./deploy/sync-data.sh
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
STORAGE_ENV="${REPO_ROOT}/.storage-env"

PROJECT_ID="${GCP_PROJECT_ID:?ERROR: GCP_PROJECT_ID is not set.}"
REGION="${GCP_REGION:-asia-east1}"
BACKEND_SERVICE="${BACKEND_SERVICE:-ink-backend}"

[[ -f "${STORAGE_ENV}" ]] || { echo "ERROR: .storage-env not found. Run ./deploy/setup-storage.sh first."; exit 1; }
source "${STORAGE_ENV}"

GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'
log()  { echo -e "${GREEN}[sync]${NC} $*"; }
info() { echo -e "${CYAN}[info]${NC} $*"; }

DATA_DIR="${REPO_ROOT}/backend/data"

# ── Upload ────────────────────────────────────────────────────────────────────
log "Uploading ink-and-memory.db..."
gsutil cp "${DATA_DIR}/ink-and-memory.db" "gs://${GCS_BUCKET}/ink-and-memory.db"

# Also sync WAL files if they exist (needed for consistent SQLite state)
for wal_file in "${DATA_DIR}/ink-and-memory.db-wal" "${DATA_DIR}/ink-and-memory.db-shm"; do
  [[ -f "${wal_file}" ]] && gsutil cp "${wal_file}" "gs://${GCS_BUCKET}/$(basename ${wal_file})"
done


# ── Restart backend so it re-opens the new database file ─────────────────────
log "Restarting ${BACKEND_SERVICE} to pick up new data..."
gcloud run services update "${BACKEND_SERVICE}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --update-env-vars="FORCE_RESTART=$(date +%s)" \
  --quiet

info "════════════════════════════════════════"
info "  Sync complete. Backend is restarting."
info "  Data: gs://${GCS_BUCKET}/"
info "════════════════════════════════════════"
