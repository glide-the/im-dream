"""Canonical, client-safe Deck Plugin and workflow API errors."""

from __future__ import annotations

import re
from typing import Any


ERROR_REGISTRY: dict[str, dict[str, str]] = {
    "WORKFLOW_SELECTION_REQUIRED": {
        "phase": "selection",
        "meaning": "A valid Deck Plugin binding has not been selected.",
        "recovery": "Select an exact release and run preflight again.",
    },
    "DECK_PLUGIN_UNAVAILABLE": {
        "phase": "selection",
        "meaning": "The requested Deck Plugin release is not available.",
        "recovery": "Choose another authorized, published release.",
    },
    "DECK_PLUGIN_MANIFEST_INVALID": {
        "phase": "install",
        "meaning": "The Deck Plugin manifest is invalid.",
        "recovery": "Publish a corrected release.",
    },
    "DECK_PLUGIN_SOURCE_DENIED": {
        "phase": "install",
        "meaning": "The Deck Plugin source is not trusted.",
        "recovery": "Approve the source or choose a trusted source.",
    },
    "DECK_PLUGIN_INTEGRITY_FAILED": {
        "phase": "install",
        "meaning": "The release integrity check failed.",
        "recovery": "Quarantine the artifact and publish a new digest.",
    },
    "RUNTIME_MARKETPLACE_UNAVAILABLE": {
        "phase": "install",
        "meaning": "The runtime marketplace is unavailable.",
        "recovery": "Preserve the declaration and retry after source recovery.",
    },
    "RUNTIME_PLUGIN_MATERIALIZATION_FAILED": {
        "phase": "install",
        "meaning": "The runtime plugin could not be materialized.",
        "recovery": "Retry the operation after runtime recovery.",
    },
    "DECK_HOST_INCOMPATIBLE": {
        "phase": "compatibility",
        "meaning": "The Deck host does not support this release.",
        "recovery": "Upgrade the host or choose a compatible release.",
    },
    "CLAUDE_AGENT_INCOMPATIBLE": {
        "phase": "compatibility",
        "meaning": "The agent runtime does not support this release.",
        "recovery": "Upgrade the runtime or roll back the release.",
    },
    "STORY_SCHEMA_INCOMPATIBLE": {
        "phase": "compatibility",
        "meaning": "The output contract is incompatible with Story Workspace.",
        "recovery": "Publish a compatible release; do not partially commit output.",
    },
    "DECK_RUNTIME_CONFIG_INVALID": {
        "phase": "config",
        "meaning": "The Deck runtime configuration is invalid.",
        "recovery": "Correct the Deck configuration and run preflight again.",
    },
    "DECK_RUNTIME_CONFIG_INCOMPATIBLE": {
        "phase": "config",
        "meaning": "The Deck runtime snapshot contract is incompatible.",
        "recovery": "Choose a compatible runtime profile or release.",
    },
    "DECK_RUNTIME_CONFIG_UNAVAILABLE": {
        "phase": "config",
        "meaning": "The Deck runtime configuration is temporarily unavailable.",
        "recovery": "Retry preflight with the same idempotent request.",
    },
    "WORKFLOW_PERMISSION_DENIED": {
        "phase": "permission",
        "meaning": "The caller is not authorized for this operation.",
        "recovery": "Request the required permission.",
    },
    "DECK_PLUGIN_DISABLED": {
        "phase": "status",
        "meaning": "The Deck Plugin installation is disabled.",
        "recovery": "Enable it or explicitly select another release.",
    },
    "DECK_PLUGIN_UPGRADE_PENDING": {
        "phase": "status",
        "meaning": "The release requires capability approval.",
        "recovery": "Approve the capability change; the ready release remains usable.",
    },
    "RUNTIME_PLUGIN_NOT_READY": {
        "phase": "load",
        "meaning": "The required runtime plugin is not loadable.",
        "recovery": "Wait for or trigger reconcile; do not start a session.",
    },
    "RUNTIME_PLUGIN_LOAD_FAILED": {
        "phase": "load",
        "meaning": "The runtime plugin failed to load for the session.",
        "recovery": "Retry in a new session and diagnose repeated failures.",
    },
    "RUNTIME_PLUGIN_RELOAD_UNSUPPORTED": {
        "phase": "load",
        "meaning": "Runtime hot reload is not supported for this request.",
        "recovery": "Use a new session after headless reconcile.",
    },
    "AGENT_SESSION_START_FAILED": {
        "phase": "session",
        "meaning": "The agent session could not be started.",
        "recovery": "Preserve diagnostics and retry as a new attempt.",
    },
    "WORKFLOW_STEP_FAILED": {
        "phase": "run",
        "meaning": "A known workflow step failed.",
        "recovery": "Retry as a new run using the frozen source.",
    },
    "AGENT_EXECUTION_FAILED": {
        "phase": "run",
        "meaning": "The agent runtime could not complete the operation.",
        "recovery": "Use the operation or run identifier to diagnose and retry safely.",
    },
    "OUTPUT_CONTRACT_INVALID": {
        "phase": "result",
        "meaning": "The workflow output does not match its contract.",
        "recovery": "Do not partially commit; publish a corrected workflow release.",
    },
    "RESULT_COMMIT_FAILED": {
        "phase": "result",
        "meaning": "The workflow result could not be committed.",
        "recovery": "Replay the idempotent commit or create a policy-approved retry.",
    },
    "BINDING_REVISION_CONFLICT": {
        "phase": "concurrency",
        "meaning": "The Deck Plugin binding changed concurrently.",
        "recovery": "Refresh the binding and confirm the selection again.",
    },
    "IDEMPOTENCY_CONFLICT": {
        "phase": "concurrency",
        "meaning": "The idempotency key was reused with different request semantics.",
        "recovery": "Replay the original request or use a new idempotency key.",
    },
    "CONFIG_VERSION_DRIFT": {
        "phase": "concurrency",
        "meaning": "A selected configuration reference changed before execution.",
        "recovery": "Use the frozen version or explicitly create a new binding and run.",
    },
}


_SAFE_REFERENCE = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")


class ApiRouteError(RuntimeError):
    """A known domain failure carrying only allowlisted public metadata."""

    def __init__(
        self,
        code: str,
        *,
        status_code: int = 422,
        operation_id: str | None = None,
        run_id: str | None = None,
        failed_check: str | None = None,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.status_code = status_code
        self.operation_id = operation_id
        self.run_id = run_id
        self.failed_check = failed_check


def build_error_payload(
    code: str,
    *,
    operation_id: str | None = None,
    run_id: str | None = None,
    failed_check: str | None = None,
) -> dict[str, dict[str, Any]]:
    """Build an allowlist-only response; exception text never reaches clients."""

    registered = ERROR_REGISTRY.get(code, ERROR_REGISTRY["AGENT_EXECUTION_FAILED"])
    public_code = code if code in ERROR_REGISTRY else "AGENT_EXECUTION_FAILED"
    error: dict[str, Any] = {
        "code": public_code,
        "phase": registered["phase"],
        "message": registered["meaning"],
        "recovery_action": registered["recovery"],
    }
    for key, value in (
        ("operation_id", operation_id),
        ("run_id", run_id),
        ("failed_check", failed_check),
    ):
        if value is not None and _SAFE_REFERENCE.fullmatch(value):
            error[key] = value
    return {"error": error}


def registered_error_codes() -> tuple[str, ...]:
    return tuple(ERROR_REGISTRY)
