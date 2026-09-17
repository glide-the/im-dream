#!/usr/bin/env bash
# [Input] Remote Dream configuration projector and disposable explicit auth/data settings.
# [Output] Provider-free assertions for exact origins, distinct server secrets, mode and fail-closed validation.
# [Pos] Deterministic Remote SSH Dream deployment contract test.
# [Sync] 2026-09-16: verify Admin DTO/BFF projection without a database or external service.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/dream-remote-env.XXXXXX")"
trap 'rm -rf "${TEMP_ROOT}"' EXIT
OUTPUT_ENV="${TEMP_ROOT}/dream.env"

DREAM_REMOTE_ENV_FILE="${OUTPUT_ENV}" \
DREAM_GATEWAY_ORIGIN=https://admin.example.test \
DREAM_PRODUCT_ORIGIN=https://dream.example.test \
DREAM_ADMIN_SERVICE_CLIENT_ID=ink-dream-service \
DREAM_ADMIN_SERVICE_SECRET=dream-service-secret-at-least-thirty-two-bytes \
DREAM_BFF_COOKIE_SECRET=dream-cookie-secret-at-least-thirty-two-bytes \
DREAM_BACKEND_BLOCK_DEVICE=/dev/vda \
DREAM_BACKEND_READ_BPS=32mb \
DREAM_BACKEND_READ_IOPS=400 \
  "${SCRIPT_DIR}/prepare-env.sh"

grep -Fx 'DREAM_GATEWAY_ORIGIN=https://admin.example.test' "${OUTPUT_ENV}"
grep -Fx 'DREAM_PRODUCT_ORIGIN=https://dream.example.test' "${OUTPUT_ENV}"
grep -Fx 'DREAM_ADMIN_SERVICE_CLIENT_ID=ink-dream-service' "${OUTPUT_ENV}"
[[ "$(stat -f '%Lp' "${OUTPUT_ENV}" 2>/dev/null || stat -c '%a' "${OUTPUT_ENV}")" == "600" ]]
if grep -q 'DATABASE_URL' "${OUTPUT_ENV}"; then
  printf 'Dream remote env contained a database credential\n' >&2
  exit 1
fi
if DREAM_REMOTE_ENV_FILE="${OUTPUT_ENV}" DREAM_GATEWAY_ORIGIN=https://admin.example.test/path \
  DREAM_PRODUCT_ORIGIN=https://dream.example.test DREAM_ADMIN_SERVICE_CLIENT_ID=ink-dream-service \
  DREAM_ADMIN_SERVICE_SECRET=dream-service-secret-at-least-thirty-two-bytes \
  DREAM_BFF_COOKIE_SECRET=dream-cookie-secret-at-least-thirty-two-bytes \
  DREAM_BACKEND_BLOCK_DEVICE=/dev/vda DREAM_BACKEND_READ_BPS=32mb DREAM_BACKEND_READ_IOPS=400 \
  "${SCRIPT_DIR}/prepare-env.sh" >/dev/null 2>&1; then
  printf 'non-origin Admin URL was accepted\n' >&2
  exit 1
fi

printf '[dream-remote-env-test] Admin DTO/BFF projection passed.\n'
