#!/usr/bin/env bash
# [Input] AutoDL Dream data root and service account identity.
# [Output] Idempotent, non-symlink persistent Dream directories with mode 0750.
# [Pos] Root-only AutoDL Dream persistent-resource initializer.
# [Sync] 2026-08-26: default Dream data ownership to the root runtime identity.
# [Sync] 2026-08-28: create the private Notion actor-credential root inside the
#                    same persistent agentdata boundary as Thread workspaces.
set -euo pipefail

DATA_ROOT="${INK_AUTODL_DATA_ROOT:-/root/autodl-tmp/ink-memory}"
SERVICE_USER="${INK_AUTODL_SERVICE_USER:-root}"
SERVICE_GROUP="${INK_AUTODL_SERVICE_GROUP:-$(id -gn "${SERVICE_USER}")}"

fail() { printf '[dream-data-init:error] %s\n' "$*" >&2; exit 1; }

[[ "${DATA_ROOT}" == /* && "${DATA_ROOT}" != "/" ]] || fail "Dream data root must be an absolute non-root path."
id -u "${SERVICE_USER}" >/dev/null 2>&1 || fail "Dream service user does not exist: ${SERVICE_USER}"
if [[ -e "${DATA_ROOT}" && -L "${DATA_ROOT}" ]]; then
  fail "Dream data root must not be a symlink: ${DATA_ROOT}"
fi

install -d -o "${SERVICE_USER}" -g "${SERVICE_GROUP}" -m 0750 "${DATA_ROOT}"
directories=(
  agent-workspaces
  artifacts
  file-storage
  service-home
  claude-plugin-runtime
  claude-plugin-runtime/config
  claude-plugin-runtime/install-workspace
  claude-plugin-runtime/artifacts
  claude-plugin-runtime/operations
)
for relative_path in "${directories[@]}"; do
  target="${DATA_ROOT}/${relative_path}"
  [[ ! -L "${target}" ]] || fail "Dream persistent directory must not be a symlink: ${target}"
  install -d -o "${SERVICE_USER}" -g "${SERVICE_GROUP}" -m 0750 "${target}"
done

notion_runtime="${DATA_ROOT}/notion-runtime"
[[ ! -L "${notion_runtime}" ]] || fail "Notion runtime root must not be a symlink: ${notion_runtime}"
install -d -o "${SERVICE_USER}" -g "${SERVICE_GROUP}" -m 0700 "${notion_runtime}"

printf '[dream-data-init] Initialized %s for %s:%s with mode 0750.\n' \
  "${DATA_ROOT}" "${SERVICE_USER}" "${SERVICE_GROUP}"
