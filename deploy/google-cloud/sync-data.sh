#!/usr/bin/env bash
# deploy/google-cloud/sync-data.sh — Retired Dream SQLite transport entry.
# [Input] Optional historical command name.
# [Output] Help text or a fail-closed retirement error; no database, GCS, or Cloud Run mutation.
# [Pos] Compatibility tombstone after Admin became the sole database access and migration service.
# [Historical Sync] 2026-06-12: backed up and uploaded Dream SQLite/WAL/SHM through GCS.
# [Sync] 2026-09-16: retire every executable SQLite backup/sync path; shared files remain outside this script.
set -euo pipefail

usage() {
  cat <<'HELP'
Dream SQLite synchronization is retired.

Business persistence is owned by Admin PostgreSQL/Drizzle and must use the
named Admin DTO APIs. This compatibility entry performs no database, GCS, or
Cloud Run action. Shared filesystem maintenance uses its dedicated topology.
HELP
}

case "${1:-}" in
  --help|-h|help)
    usage
    ;;
  *)
    usage >&2
    printf '[error] retired Dream SQLite command refused: %s\n' "${1:-upload}" >&2
    exit 1
    ;;
esac
