#!/usr/bin/env bash
# [Input] Dream AutoDL env projector and persistent-directory initializer.
# [Output] Automated topology, idempotency, ownership, mode, and symlink checks.
# [Pos] Provider-free AutoDL deployment contract test.
# [Sync] 2026-08-26: keep root-runtime topology assertions portable across GNU and BSD stat.
# [Sync] 2026-08-30: require the explicit AutoDL 2.1.88 local-core CLI path and
#                    deployment-owned disabled Claude Bash sandbox capability.
# [Sync] 2026-09-06: require the Next.js/pnpm standalone release, Node MCP
#                    Apps projection, and removal of Vite/npm/dist assumptions.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/dream-autodl-topology.XXXXXX")"
trap 'rm -rf "${TEMP_ROOT}"' EXIT

SOURCE_ENV="${TEMP_ROOT}/dream.env"
MCP_APPS_ENV="${TEMP_ROOT}/mcp-apps.env"
ADMIN_ENV="${TEMP_ROOT}/admin.env"
OUTPUT_ENV="${TEMP_ROOT}/projected.env"
DATA_ROOT="${TEMP_ROOT}/data"
PROJECTED_DATA_ROOT="/root/autodl-tmp/ink-memory"
CURRENT_USER="$(id -un)"
CURRENT_GROUP="$(id -gn)"

grep -Fq 'AUTODL_SERVICE_USER="${AUTODL_SERVICE_USER:-root}"' "${SCRIPT_DIR}/deploy.sh"
grep -Fq 'DREAM_SERVICE_USER="${INK_AUTODL_DREAM_SERVICE_USER:-root}"' "${SCRIPT_DIR}/runtime/start-ink-memory.sh"
grep -Fq 'pnpm install --frozen-lockfile' "${SCRIPT_DIR}/deploy.sh"
grep -Fq 'INK_NEXT_OUTPUT=standalone' "${SCRIPT_DIR}/deploy.sh"
grep -Fq '/api/mcp-apps/[serverRef]' "${SCRIPT_DIR}/deploy.sh"
grep -Fq 'frontend/server.js' "${SCRIPT_DIR}/deploy.sh"
grep -Fq 'frontend/server.js' "${SCRIPT_DIR}/runtime/start-ink-memory.sh"
grep -Fq 'next_server = str(release_root / "frontend/server.js")' "${SCRIPT_DIR}/runtime/start-dream.sh"
if grep -Eq 'frontend/(package-lock\.json|vite\.config\.ts|dist/index\.html)|npm ci|vite preview|VITE_ALLOWED_HOSTS|VITE_DEV_API_PROXY_TARGET' "${SCRIPT_DIR}/deploy.sh" "${SCRIPT_DIR}/runtime/start-dream.sh" "${SCRIPT_DIR}/runtime/start-ink-memory.sh"; then
  printf 'retired Vite/npm/dist deployment assumption remains\n' >&2
  exit 1
fi
grep -Fq 'verify_seo_origin "${AUTODL_DREAM_PUBLIC_ORIGIN}" "AutoDL public origin"' "${SCRIPT_DIR}/deploy.sh"
grep -Fq 'returned SPA HTML instead of the backend crawler file' "${SCRIPT_DIR}/deploy.sh"
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
INK_AGENT_SANDBOX_ENABLED=true
INK_MCP_APPS_NODE_SERVICE_TOKEN=test-node-service-token
EOF
cat >"${MCP_APPS_ENV}" <<'EOF'
INK_MCP_APPS_NODE_SERVICE_TOKEN=ignored-frontend-token
INK_MCP_APPS_PHASE1_PREVIEW=true
INK_MCP_APPS_PLUGIN_MANIFEST_JSON={"manifestVersion":1}
INK_MCP_APPS_MAX_RESOURCE_BYTES=4194304
INK_MCP_APPS_MAX_CATALOG_PAGES=8
INK_MCP_APPS_UPSTREAM_TIMEOUT_MS=5000
INK_MCP_APPS_MAX_CONCURRENCY_PER_SCOPE=4
INK_MCP_APPS_NETWORK_HOST_ALLOWLIST=mcp.example.test
INK_MCP_APPS_SANDBOX_URL=http://stale.invalid/mcp-apps-sandbox
INK_MCP_APPS_PARENT_ORIGINS=http://stale.invalid
EOF
cat >"${ADMIN_ENV}" <<'EOF'
POSTGRES_USER=ink_test
POSTGRES_PASSWORD=test-password
POSTGRES_DB=ink_test
EOF

AUTODL_DREAM_SOURCE_ENV_FILE="${SOURCE_ENV}" \
AUTODL_MCP_APPS_ENV_FILE="${MCP_APPS_ENV}" \
AUTODL_ADMIN_ENV_FILE="${ADMIN_ENV}" \
AUTODL_ENV_FILE="${OUTPUT_ENV}" \
AUTODL_DATA_ROOT="${PROJECTED_DATA_ROOT}" \
AUTODL_DREAM_PUBLIC_ORIGIN=https://dream.example.test \
AUTODL_ADMIN_PUBLIC_ORIGIN=https://admin.example.test \
AUTODL_MCP_APPS_SANDBOX_ORIGIN=https://sandbox.example.test \
  "${SCRIPT_DIR}/prepare-env.sh"

grep -Fx "AGENT_CWD=${PROJECTED_DATA_ROOT}/agent-workspaces" "${OUTPUT_ENV}"
grep -Fx "ARTIFACT_WORKSPACE_ROOT=${PROJECTED_DATA_ROOT}/artifacts" "${OUTPUT_ENV}"
grep -Fx "FILE_STORAGE_LOCAL_DIR=${PROJECTED_DATA_ROOT}/file-storage" "${OUTPUT_ENV}"
grep -Fx "INK_CLAUDE_PLUGIN_RUNTIME_ROOT=${PROJECTED_DATA_ROOT}/claude-plugin-runtime" "${OUTPUT_ENV}"
grep -Fx "CLAUDE_CODE_CLI_PATH=/root/ink-autodl/runtime/npm/bin/ink-claude-code-dream" "${OUTPUT_ENV}"
grep -Fx "INK_AGENT_SANDBOX_ENABLED=false" "${OUTPUT_ENV}"
grep -Fx "INK_PUBLIC_SITE_URL=https://dream.example.test" "${OUTPUT_ENV}"
grep -Fx "INK_MCP_APPS_NODE_SERVICE_TOKEN=test-node-service-token" "${OUTPUT_ENV}"
grep -Fx "INK_MCP_APPS_PHASE1_PREVIEW=true" "${OUTPUT_ENV}"
grep -Fx "INK_MCP_APPS_SANDBOX_URL=https://sandbox.example.test/mcp-apps-sandbox" "${OUTPUT_ENV}"
grep -Fx "INK_MCP_APPS_PARENT_ORIGINS=https://dream.example.test" "${OUTPUT_ENV}"
if grep -q '^INK_MCP_APPS_NODE_SERVICE_TOKEN=ignored-frontend-token$' "${OUTPUT_ENV}"; then
  printf 'frontend MCP Apps env overrode the backend-owned service token\n' >&2
  exit 1
fi
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
