#!/usr/bin/env bash
# [Input] Dream AutoDL env projector and persistent-directory initializer.
# [Output] Automated topology, idempotency, ownership, mode, and symlink checks.
# [Pos] Provider-free AutoDL deployment contract test.
# [Sync] 2026-08-26: keep root-runtime topology assertions portable across GNU and BSD stat.
# [Sync] 2026-08-30: require the explicit AutoDL 2.1.88 local-core CLI path and
#                    deployment-owned disabled Claude Bash sandbox capability.
# [Sync] 2026-09-06: require the Next.js/pnpm standalone release, Node MCP
#                    Apps projection, and removal of Vite/npm/dist assumptions.
# [Sync] 2026-09-17: assert verification propagates failures and validates the complete artifact store without user identity.
# [Sync] 2026-09-17: assert release validation expects the npm package-root cli.js entrypoint.
# [Sync] 2026-09-17: assert the sandbox route follows the deployment-injected Dream origin.
# [Sync] 2026-09-16: assert exact Admin issuer/resource/BFF projection and no PostgreSQL credential.
# [Sync] 2026-09-16: prove retired Dream auth/session secrets never enter the projected runtime.
# [Sync] 2026-09-16: prove the retired Product HS256 signer never enters the projected runtime.
# [Sync] 2026-09-18: isolate projector fixtures from the operator-selected platform.env.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/dream-autodl-topology.XXXXXX")"
trap 'rm -rf "${TEMP_ROOT}"' EXIT

SOURCE_ENV="${TEMP_ROOT}/dream.env"
MCP_APPS_ENV="${TEMP_ROOT}/mcp-apps.env"
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
grep -Fq 'runtime.get_artifacts_root().iterdir()' "${SCRIPT_DIR}/runtime/start-ink-memory.sh"
grep -Fq 'artifact_store.get_artifact' "${SCRIPT_DIR}/runtime/start-ink-memory.sh"
grep -Fq 'next_server = str(release_root / "frontend/server.js")' "${SCRIPT_DIR}/runtime/start-dream.sh"
grep -Fq 'smoke_candidate' "${SCRIPT_DIR}/deploy.sh"
grep -Fq 'AUTODL_DREAM_SMOKE_FRONTEND_PORT' "${SCRIPT_DIR}/deploy.sh"
grep -Fq 'activate_candidate' "${SCRIPT_DIR}/deploy.sh"
grep -Fq 'prune_old_releases' "${SCRIPT_DIR}/deploy.sh"
grep -Fq '@glide-the/ink-claude-code-dream@${AUTODL_CLAUDE_RUNTIME_VERSION}' "${SCRIPT_DIR}/deploy.sh"
if grep -Eq 'qualified-package|ink-claude-code-dream-0\.1\.9|Runtime 0\.1\.9 local-core' "${SCRIPT_DIR}/deploy.sh"; then
  printf 'retired unpublished AutoDL Runtime artifact remains\n' >&2
  exit 1
fi
if grep -Eq 'frontend/(package-lock\.json|vite\.config\.ts|dist/index\.html)|npm ci|vite preview|VITE_ALLOWED_HOSTS|VITE_DEV_API_PROXY_TARGET' "${SCRIPT_DIR}/deploy.sh" "${SCRIPT_DIR}/runtime/start-dream.sh" "${SCRIPT_DIR}/runtime/start-ink-memory.sh"; then
  printf 'retired Vite/npm/dist deployment assumption remains\n' >&2
  exit 1
fi
grep -Fq 'verify_seo_origin "${AUTODL_DREAM_PUBLIC_ORIGIN}" "AutoDL public origin"' "${SCRIPT_DIR}/deploy.sh"
grep -Fq "candidate.name == 'cli.js' and candidate.parent.name == 'ink-claude-code-dream'" "${SCRIPT_DIR}/deploy.sh"
grep -Fq 'verify_plugin_artifacts || return' "${SCRIPT_DIR}/deploy.sh"
grep -Fq 'verify_builtin_skills || return' "${SCRIPT_DIR}/deploy.sh"
if grep -Fq 'resolve_default_deck_plugin_ref()' "${SCRIPT_DIR}/deploy.sh"; then
  printf 'deployment verifier retained a user-scoped default-plugin call without an installation DTO\n' >&2
  exit 1
fi
grep -Fq 'returned SPA HTML instead of the backend crawler file' "${SCRIPT_DIR}/deploy.sh"
if grep -F 'screen -dmS "${DREAM_SCREEN}"' -A2 "${SCRIPT_DIR}/runtime/start-ink-memory.sh" | grep -q 'setpriv'; then
  printf 'standalone Dream launcher still drops to a separate service user\n' >&2
  exit 1
fi

cat >"${SOURCE_ENV}" <<'EOF'
SESSION_SECRET_KEY=test-session-secret
GOOGLE_CLIENT_SECRET=test-google-secret
JWT_SECRET=test-jwt-secret
JWT_SECRET_KEY=test-jwt-secret-key
OAUTH_TOKEN_ENCRYPTION_KEY=test-oauth-encryption-key
AUTH_TOKEN_ENCRYPTION_KEY=test-auth-encryption-key
COOKIE_SECURE=true
COOKIE_SAMESITE=none
INK_GATEWAY_SERVICE_KEY=test-gateway-key
INK_ADMIN_PRODUCT_JWT_SECRET=test-product-secret
AGENT_CWD=/tmp/stale
ARTIFACT_WORKSPACE_ROOT=/tmp/stale-artifacts
INK_AGENT_MAX_CONCURRENT_RUNS=9
INK_AGENT_RUN_MEMORY_BUDGET_MIB=8192
INK_AGENT_MEMORY_RESERVE_MIB=2048
INK_AGENT_SANDBOX_ENABLED=true
INK_MCP_APPS_NODE_SERVICE_TOKEN=test-node-service-token
DATABASE_URL=postgresql://must-not-survive.invalid/test
INK_LOAD_DATABASE_URL_FROM_ENV_FILE=1
INK_DATABASE_ENV_FILE=/tmp/must-not-survive
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
AUTODL_DREAM_SOURCE_ENV_FILE="${SOURCE_ENV}" \
AUTODL_MCP_APPS_ENV_FILE="${MCP_APPS_ENV}" \
AUTODL_ENV_FILE="${OUTPUT_ENV}" \
AUTODL_PLATFORM_ENV_FILE=/dev/null \
AUTODL_DATA_ROOT="${PROJECTED_DATA_ROOT}" \
AUTODL_DREAM_PUBLIC_ORIGIN=https://dream.example.test \
AUTODL_ADMIN_PUBLIC_ORIGIN=https://admin.example.test \
AUTODL_DREAM_ADMIN_SERVICE_CLIENT_ID=ink-dream-service \
AUTODL_DREAM_ADMIN_SERVICE_SECRET=dream-service-secret-at-least-thirty-two-bytes \
AUTODL_DREAM_BFF_COOKIE_SECRET=dream-cookie-secret-at-least-thirty-two-bytes \
  "${SCRIPT_DIR}/prepare-env.sh"

grep -Fx "AGENT_CWD=${PROJECTED_DATA_ROOT}/agent-workspaces" "${OUTPUT_ENV}"
grep -Fx "ARTIFACT_WORKSPACE_ROOT=${PROJECTED_DATA_ROOT}/artifacts" "${OUTPUT_ENV}"
grep -Fx "FILE_STORAGE_LOCAL_DIR=${PROJECTED_DATA_ROOT}/file-storage" "${OUTPUT_ENV}"
grep -Fx "INK_CLAUDE_PLUGIN_RUNTIME_ROOT=${PROJECTED_DATA_ROOT}/claude-plugin-runtime" "${OUTPUT_ENV}"
grep -Fx "CLAUDE_CODE_CLI_PATH=/root/ink-autodl/runtime/npm/bin/ink-claude-code-dream" "${OUTPUT_ENV}"
grep -Fx "INK_AGENT_SANDBOX_ENABLED=false" "${OUTPUT_ENV}"
grep -Fx "INK_PUBLIC_SITE_URL=https://dream.example.test" "${OUTPUT_ENV}"
grep -Fx "INK_ADMIN_DREAM_BASE_URL=https://admin.example.test" "${OUTPUT_ENV}"
grep -Fx "INK_ADMIN_DREAM_TRANSPORT_BASE_URL=http://127.0.0.1:6008" "${OUTPUT_ENV}"
grep -Fx "INK_ADMIN_AUTH_ISSUER=https://admin.example.test/api/auth" "${OUTPUT_ENV}"
grep -Fx "INK_DREAM_API_RESOURCE=https://dream.example.test/api" "${OUTPUT_ENV}"
grep -Fx "INK_ADMIN_DREAM_SERVICE_CLIENT_ID=ink-dream-service" "${OUTPUT_ENV}"
grep -Fx "INK_DREAM_PUBLIC_ORIGIN=https://dream.example.test" "${OUTPUT_ENV}"
grep -Fx "INK_DREAM_BFF_INTERNAL_ORIGIN=http://127.0.0.1:6006" "${OUTPUT_ENV}"
grep -Fx "INK_DREAM_BFF_REDIRECT_URI=https://dream.example.test/auth/callback" "${OUTPUT_ENV}"
grep -Fx "INK_MCP_APPS_NODE_SERVICE_TOKEN=test-node-service-token" "${OUTPUT_ENV}"
grep -Fx "INK_MCP_APPS_PHASE1_PREVIEW=true" "${OUTPUT_ENV}"
grep -Fx "INK_MCP_APPS_SANDBOX_URL=https://dream.example.test/mcp-apps-sandbox" "${OUTPUT_ENV}"
grep -Fx "INK_MCP_APPS_PARENT_ORIGINS=https://dream.example.test" "${OUTPUT_ENV}"
if grep -Eq '^(DATABASE_URL|INK_LOAD_DATABASE_URL_FROM_ENV_FILE|INK_DATABASE_ENV_FILE)=' "${OUTPUT_ENV}"; then
  printf 'Dream runtime retained a PostgreSQL configuration key\n' >&2
  exit 1
fi
if grep -Eq '^(GOOGLE_CLIENT_SECRET|JWT_SECRET|JWT_SECRET_KEY|SESSION_SECRET_KEY|OAUTH_TOKEN_ENCRYPTION_KEY|AUTH_TOKEN_ENCRYPTION_KEY|INK_ADMIN_PRODUCT_JWT_SECRET|COOKIE_SECURE|COOKIE_SAMESITE)=' "${OUTPUT_ENV}"; then
  printf 'Dream runtime retained retired authentication authority\n' >&2
  exit 1
fi
if AUTODL_DREAM_SOURCE_ENV_FILE="${SOURCE_ENV}" AUTODL_MCP_APPS_ENV_FILE="${MCP_APPS_ENV}" \
  AUTODL_ENV_FILE="${OUTPUT_ENV}" AUTODL_DATA_ROOT="${PROJECTED_DATA_ROOT}" \
  AUTODL_PLATFORM_ENV_FILE=/dev/null \
  AUTODL_DREAM_PUBLIC_ORIGIN=https://dream.example.test AUTODL_ADMIN_PUBLIC_ORIGIN=https://admin.example.test \
  AUTODL_DREAM_ADMIN_SERVICE_CLIENT_ID=ink-dream-service AUTODL_DREAM_ADMIN_SERVICE_SECRET=short \
  AUTODL_DREAM_BFF_COOKIE_SECRET=dream-cookie-secret-at-least-thirty-two-bytes \
  "${SCRIPT_DIR}/prepare-env.sh" >/dev/null 2>&1; then
  printf 'short Admin service secret was accepted\n' >&2
  exit 1
fi
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
