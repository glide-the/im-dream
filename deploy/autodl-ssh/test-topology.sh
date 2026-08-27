#!/usr/bin/env bash
# [Input] Dream AutoDL env projector and persistent-directory initializer.
# [Output] Automated topology, idempotency, ownership, mode, and symlink checks.
# [Pos] Provider-free AutoDL deployment contract test.
# [Sync] 2026-08-26: keep root-runtime topology assertions portable across GNU and BSD stat.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/dream-autodl-topology.XXXXXX")"
trap 'rm -rf "${TEMP_ROOT}"' EXIT

SOURCE_ENV="${TEMP_ROOT}/dream.env"
ADMIN_ENV="${TEMP_ROOT}/admin.env"
OUTPUT_ENV="${TEMP_ROOT}/projected.env"
DATA_ROOT="${TEMP_ROOT}/data"
PROJECTED_DATA_ROOT="/root/autodl-tmp/ink-memory"
CURRENT_USER="$(id -un)"
CURRENT_GROUP="$(id -gn)"

grep -Fq 'AUTODL_SERVICE_USER="${AUTODL_SERVICE_USER:-root}"' "${SCRIPT_DIR}/deploy.sh"
grep -Fq 'DREAM_SERVICE_USER="${INK_AUTODL_DREAM_SERVICE_USER:-root}"' "${SCRIPT_DIR}/runtime/start-ink-memory.sh"
if grep -F 'screen -dmS "${DREAM_SCREEN}"' -A2 "${SCRIPT_DIR}/runtime/start-ink-memory.sh" | grep -q 'setpriv'; then
  printf 'standalone Dream launcher still drops to a separate service user\n' >&2
  exit 1
fi

cat >"${SOURCE_ENV}" <<'EOF'
SESSION_SECRET_KEY=test-session-secret
INK_GATEWAY_SERVICE_KEY=test-gateway-key
INK_ADMIN_PRODUCT_JWT_SECRET=test-product-secret
AGENT_CWD=/tmp/stale
ARTIFACT_WORKSPACE_ROOT=/tmp/stale-artifacts
INK_AGENT_MAX_CONCURRENT_RUNS=9
INK_AGENT_RUN_MEMORY_BUDGET_MIB=8192
INK_AGENT_MEMORY_RESERVE_MIB=2048
EOF
cat >"${ADMIN_ENV}" <<'EOF'
POSTGRES_USER=ink_test
POSTGRES_PASSWORD=test-password
POSTGRES_DB=ink_test
EOF

AUTODL_DREAM_SOURCE_ENV_FILE="${SOURCE_ENV}" \
AUTODL_ADMIN_ENV_FILE="${ADMIN_ENV}" \
AUTODL_ENV_FILE="${OUTPUT_ENV}" \
AUTODL_DATA_ROOT="${PROJECTED_DATA_ROOT}" \
AUTODL_DREAM_PUBLIC_ORIGIN=https://dream.example.test \
AUTODL_ADMIN_PUBLIC_ORIGIN=https://admin.example.test \
  "${SCRIPT_DIR}/prepare-env.sh"

grep -Fx "AGENT_CWD=${PROJECTED_DATA_ROOT}/agent-workspaces" "${OUTPUT_ENV}"
grep -Fx "ARTIFACT_WORKSPACE_ROOT=${PROJECTED_DATA_ROOT}/artifacts" "${OUTPUT_ENV}"
grep -Fx "FILE_STORAGE_LOCAL_DIR=${PROJECTED_DATA_ROOT}/file-storage" "${OUTPUT_ENV}"
grep -Fx "INK_CLAUDE_PLUGIN_RUNTIME_ROOT=${PROJECTED_DATA_ROOT}/claude-plugin-runtime" "${OUTPUT_ENV}"
if grep -Eq '^INK_AGENT_(MAX_CONCURRENT_RUNS|RUN_MEMORY_BUDGET_MIB|MEMORY_RESERVE_MIB)=' "${OUTPUT_ENV}"; then
  printf 'AutoDL projected an explicit Agent admission override\n' >&2
  exit 1
fi

for _ in 1 2; do
  INK_AUTODL_DATA_ROOT="${DATA_ROOT}" \
  INK_AUTODL_SERVICE_USER="${CURRENT_USER}" \
  INK_AUTODL_SERVICE_GROUP="${CURRENT_GROUP}" \
    "${SCRIPT_DIR}/runtime/init-dream-data.sh"
done

mode_of() {
  if stat -c '%a' "$1" >/dev/null 2>&1; then
    stat -c '%a' "$1"
  else
    stat -f '%Lp' "$1"
  fi
}
owner_of() {
  if stat -c '%U:%G' "$1" >/dev/null 2>&1; then
    stat -c '%U:%G' "$1"
  else
    stat -f '%Su:%Sg' "$1"
  fi
}
for relative_path in agent-workspaces artifacts file-storage service-home claude-plugin-runtime/config; do
  target="${DATA_ROOT}/${relative_path}"
  [[ "$(mode_of "${target}")" == "750" ]]
  [[ "$(owner_of "${target}")" == "${CURRENT_USER}:${CURRENT_GROUP}" ]]
done

mv "${DATA_ROOT}/artifacts" "${DATA_ROOT}/artifacts.real"
ln -s "${DATA_ROOT}/artifacts.real" "${DATA_ROOT}/artifacts"
if INK_AUTODL_DATA_ROOT="${DATA_ROOT}" \
  INK_AUTODL_SERVICE_USER="${CURRENT_USER}" \
  INK_AUTODL_SERVICE_GROUP="${CURRENT_GROUP}" \
  "${SCRIPT_DIR}/runtime/init-dream-data.sh" >/dev/null 2>&1; then
  printf 'symlinked Dream data directory was accepted\n' >&2
  exit 1
fi

printf '[dream-autodl-test] topology contract passed.\n'
