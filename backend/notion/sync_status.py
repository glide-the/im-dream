# [Input] Scheduled worker outcomes and current actor-owned connector identity.
# [Output] Bounded process-local failure observations and server-owned refresh cadence.
# [Pos] Read-only scheduled-sync diagnostics; Admin remains the execution/persistence owner.
# [Sync] 2026-10-13: expose pre-claim failures without inventing or patching an Admin run.
"""Safe worker observations, distinct from persisted synchronization policy."""
from __future__ import annotations

import math
import os
from threading import RLock
from typing import Any

from services.admin_data.errors import AdminDataError
from .errors import (
    NotionAuthRequiredError, NotionCLIUnavailableError, NotionCredentialError,
    NotionOperationError,
)

NOTION_SYNC_SCHEDULER_INTERVAL_SECONDS = 60.0
NOTION_SYNC_SCHEDULER_INTERVAL_ENV = "INK_NOTION_SYNC_SCHEDULER_INTERVAL_SECONDS"
_ADMIN_FAILURE_CODES = frozenset({
    "ADMIN_CAPABILITY_UNAVAILABLE", "ADMIN_UNAVAILABLE", "ADMIN_RESPONSE_INVALID",
    "ADMIN_WRITE_RESULT_UNKNOWN", "ADMIN_SERVICE_AUTH_UNAVAILABLE",
    "DREAM_SERVICE_SCOPE_REQUIRED", "NOTION_SYNC_CLAIMS_DISABLED",
    "NOTION_SYNC_POLICY_NOT_CONFIGURED", "NOTION_SYNC_LEGACY_OWNER_UNRESOLVED",
    "NOTION_SYNC_RENEWAL_TIMEOUT", "NOTION_SYNC_LEASE_EXPIRED",
    "NOTION_SYNC_CONTEXT_CHANGED", "NOTION_SYNC_RUN_INVALID",
})


def scheduler_interval_from_env() -> float:
    try:
        parsed = float(os.environ.get(NOTION_SYNC_SCHEDULER_INTERVAL_ENV, ""))
    except ValueError:
        return NOTION_SYNC_SCHEDULER_INTERVAL_SECONDS
    return parsed if math.isfinite(parsed) and 5 <= parsed <= 3600 else NOTION_SYNC_SCHEDULER_INTERVAL_SECONDS


def sync_failure_code(error: Exception) -> str:
    if isinstance(error, AdminDataError) and error.code in _ADMIN_FAILURE_CODES:
        return error.code
    if isinstance(error, NotionCLIUnavailableError):
        return "NOTION_CLI_UNAVAILABLE"
    if isinstance(error, (NotionCredentialError, NotionAuthRequiredError)):
        return "NOTION_AUTH_REQUIRED"
    if isinstance(error, NotionOperationError):
        return "NOTION_UPSTREAM_UNAVAILABLE"
    return "NOTION_SYNC_FAILED"


class NotionSyncDiagnostics:
    """Only matching actor/connector versions may consume a worker observation."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._failures: dict[str, tuple[Any, Any, str]] = {}

    def retain_candidates(self, candidates: list[dict]) -> None:
        keys = {str(item.get("id")) for item in candidates}
        with self._lock:
            self._failures = {key: value for key, value in self._failures.items() if key in keys}

    def failed(self, connector: dict, error: Exception) -> str:
        code = sync_failure_code(error)
        with self._lock:
            self._failures[str(connector["id"])] = (
                str(connector["user_id"]), connector.get("updated_at"), code,
            )
        return code

    def clear(self, connector_id: str) -> None:
        with self._lock:
            self._failures.pop(connector_id, None)

    def error_for(self, connector: dict) -> str | None:
        with self._lock:
            failure = self._failures.get(str(connector["id"]))
        if failure is None or failure[:2] != (str(connector["user_id"]), connector.get("updated_at")):
            return None
        return failure[2]


sync_diagnostics = NotionSyncDiagnostics()
