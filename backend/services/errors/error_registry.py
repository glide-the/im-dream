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
    "WORKFLOW_RUN_NOT_GUIDABLE": {
        "phase": "run",
        "meaning": "The run is not in a guidable state or has no guidance channel.",
        "recovery": "Confirm the run review and submit guidance while it is continuing.",
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
    # Claude Code plugin install/pack pipeline (deck-integration-delta).
    "CLAUDE_PLUGIN_SPEC_INVALID": {
        "phase": "selection",
        "meaning": "The package spec is invalid. Use <plugin>@<marketplace>.",
        "recovery": "Correct the package spec and retry the install.",
    },
    "CLAUDE_PLUGIN_SOURCE_UNKNOWN": {
        "phase": "selection",
        "meaning": "The plugin source is not a server-declared source.",
        "recovery": "Use a marketplace package spec or a declared platform-builtin plugin.",
    },
    "CLAUDE_PLUGIN_MARKETPLACE_UNKNOWN": {
        "phase": "install",
        "meaning": "The marketplace is not registered in the managed workspace.",
        "recovery": "Use a plugin from a server-registered marketplace.",
    },
    "CLAUDE_PLUGIN_CLI_UNAVAILABLE": {
        "phase": "install",
        "meaning": "The Claude Code CLI is not available on this host.",
        "recovery": "Install or update Claude Code and retry.",
    },
    "CLAUDE_PLUGIN_INSTALL_FAILED": {
        "phase": "install",
        "meaning": "The real claude plugin install execution failed.",
        "recovery": "Inspect the operation evidence and retry.",
    },
    "CLAUDE_PLUGIN_REGISTRY_MISMATCH": {
        "phase": "install",
        "meaning": "The CLI registry has no cache-contained entry after install.",
        "recovery": "Retry the install; if it persists, reinstall the Claude Code CLI.",
    },
    "CLAUDE_PLUGIN_MANIFEST_INVALID": {
        "phase": "install",
        "meaning": "The plugin manifest is missing or invalid.",
        "recovery": "Fix .claude-plugin/plugin.json and retry.",
    },
    "CLAUDE_PLUGIN_ARTIFACT_FAILED": {
        "phase": "install",
        "meaning": "The plugin artifact could not be imported or verified.",
        "recovery": "Retry the install; the artifact store refuses unverifiable content.",
    },
    "CLAUDE_PLUGIN_NOT_FOUND": {
        "phase": "selection",
        "meaning": "The plugin installation does not exist.",
        "recovery": "Install the plugin first.",
    },
    "CLAUDE_PLUGIN_NOT_READY": {
        "phase": "selection",
        "meaning": "The plugin installation is not in ready state.",
        "recovery": "Wait for the install operation or reinstall.",
    },
    "CLAUDE_PLUGIN_INTEGRITY_FAILED": {
        "phase": "verification",
        "meaning": "The plugin artifact failed digest verification.",
        "recovery": "Reinstall the plugin; unverifiable artifacts are never loaded.",
    },
    "CLAUDE_PLUGIN_INCOMPATIBLE": {
        "phase": "selection",
        "meaning": "The plugin is not compatible with the current Claude Code version.",
        "recovery": "Update the plugin or the Claude Code CLI.",
    },
    "CLAUDE_PLUGIN_REF_INVALID": {
        "phase": "selection",
        "meaning": "The Deck plugin reference set is invalid.",
        "recovery": "Submit references to ready installations only.",
    },
    "CLAUDE_PLUGIN_OPERATION_NOT_FOUND": {
        "phase": "install",
        "meaning": "The install operation does not exist.",
        "recovery": "Check the operation id.",
    },
    "CLAUDE_PLUGIN_MANIFEST_INVALID_SCHEMA": {
        "phase": "verification",
        "meaning": "The workspace launch manifest is invalid.",
        "recovery": "Recreate the chat workspace.",
    },
    "CLAUDE_PLUGIN_PACK_MISSING": {
        "phase": "verification",
        "meaning": "A packed plugin directory is missing from the workspace.",
        "recovery": "Recreate the chat workspace so plugins are re-packed.",
    },
    "story_index_row_missing": {
        "phase": "result",
        "meaning": "The PostgreSQL Story index has not been created.",
        "recovery": "Retry the idempotent Story index synchronization.",
    },
    "story_index_schema_unavailable": {
        "phase": "config",
        "meaning": "The PostgreSQL Story index schema is not available.",
        "recovery": "Wait for the Admin-owned schema migration and retry.",
    },
    "story_index_database_unavailable": {
        "phase": "result",
        "meaning": "The PostgreSQL Story index is temporarily unavailable.",
        "recovery": "Keep using the generated file and retry indexing later.",
    },
    "story_index_write_failed": {
        "phase": "result",
        "meaning": "The PostgreSQL Story index could not be updated.",
        "recovery": "Keep using the generated file and retry the idempotent write.",
    },
    "story_index_conflict": {
        "phase": "concurrency",
        "meaning": "The Project Story index belongs to another trusted thread.",
        "recovery": "Resolve the ownership conflict before retrying.",
    },
    "story_index_invalid_artifact": {
        "phase": "result",
        "meaning": "The canonical Story Artifact is invalid.",
        "recovery": "Repair the canonical Project or Episode Artifact and retry.",
    },
    "story_index_revision_conflict": {
        "phase": "concurrency",
        "meaning": "The Story Artifact revision changed before indexing.",
        "recovery": "Refresh the file and Story index status before retrying.",
    },
    "artifact_missing": {
        "phase": "result",
        "meaning": "The canonical script Artifact is missing.",
        "recovery": "Generate the script Artifact before retrying the Story index.",
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
