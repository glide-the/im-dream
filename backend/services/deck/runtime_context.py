"""Resolve Deck Plugin compatibility facts from server-owned state."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from typing import Any

try:
    from backend.models.deck_plugin import DeckPluginManifestV1, DeckRuntimePluginLock
    from backend.services.deck_plugin.compatibility_service import RuntimeContext
except ModuleNotFoundError:  # Support backend directory on PYTHONPATH.
    from models.deck_plugin import DeckPluginManifestV1, DeckRuntimePluginLock
    from services.deck_plugin.compatibility_service import RuntimeContext


def _json_strings(value: object) -> set[str]:
    try:
        parsed = json.loads(str(value or "[]"))
    except (TypeError, json.JSONDecodeError):
        return set()
    if not isinstance(parsed, list):
        return set()
    return {item.strip() for item in parsed if isinstance(item, str) and item.strip()}


def _compatibility_flag(name: str) -> bool:
    """Default to incompatible unless the server capability is explicit."""
    raw = os.getenv(name)
    return raw is not None and raw.strip().lower() in {"1", "true", "yes", "on"}


def _installation_row(
    db: Any,
    *,
    deck_plugin_id: str,
    workspace_id: str,
) -> Any | None:
    row = db.execute(
        """
        SELECT * FROM deck_plugin_installations
        WHERE scope_type = 'workspace' AND scope_id = %s AND deck_plugin_id = %s
        """,
        (workspace_id, deck_plugin_id),
    ).fetchone()
    if row is not None:
        return row
    return db.execute(
        """
        SELECT * FROM deck_plugin_installations
        WHERE scope_type = 'instance' AND deck_plugin_id = %s
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        (deck_plugin_id,),
    ).fetchone()


def resolve_runtime_context(
    db: Any,
    *,
    deck_plugin_id: str,
    deck_plugin_version: str,
    workspace_id: str,
) -> RuntimeContext:
    """Build compatibility input without accepting client-controlled facts."""
    release = db.execute(
        """
        SELECT manifest_json FROM deck_plugin_releases
        WHERE deck_plugin_id = %s AND deck_plugin_version = %s
        """,
        (deck_plugin_id, deck_plugin_version),
    ).fetchone()
    lock_row = db.execute(
        """
        SELECT lock_json FROM deck_runtime_plugin_locks
        WHERE deck_plugin_id = %s AND deck_plugin_version = %s
        """,
        (deck_plugin_id, deck_plugin_version),
    ).fetchone()
    installation = _installation_row(
        db,
        deck_plugin_id=deck_plugin_id,
        workspace_id=workspace_id,
    )
    if release is None or lock_row is None or installation is None:
        raise ValueError("Deck Plugin runtime context is incomplete")

    manifest = DeckPluginManifestV1.model_validate_json(release["manifest_json"])
    runtime_lock = DeckRuntimePluginLock.model_validate_json(lock_row["lock_json"])
    approved = _json_strings(installation["approved_capabilities_json"])

    materialized: set[str] = set()
    loadable: set[str] = set()
    for entry in runtime_lock.claude_code_plugins:
        rows = db.execute(
            """
            SELECT materialization_status, activation_status
            FROM runtime_plugin_materializations
            WHERE claude_code_plugin_id = %s
              AND resolved_version = %s
              AND artifact_digest = %s
            ORDER BY updated_at DESC
            """,
            (
                entry.claude_code_plugin_id,
                entry.resolved_version,
                entry.artifact_digest,
            ),
        ).fetchall()
        if any(row["materialization_status"] == "materialized" for row in rows):
            materialized.add(entry.claude_code_plugin_id)
        if any(
            row["materialization_status"] == "materialized"
            and row["activation_status"] in {"loadable", "loaded"}
            for row in rows
        ):
            loadable.add(entry.claude_code_plugin_id)

    known_capabilities = set(manifest.capabilities) | approved
    return RuntimeContext(
        deck_host_compatible=_compatibility_flag("INK_DECK_HOST_COMPATIBLE"),
        claude_agent_compatible=_compatibility_flag("INK_CLAUDE_AGENT_CONTRACT_COMPATIBLE"),
        story_schema_compatible=_compatibility_flag("INK_STORY_SCHEMA_COMPATIBLE"),
        deck_runtime_config_compatible=_compatibility_flag("INK_DECK_RUNTIME_CONFIG_COMPATIBLE"),
        deck_runtime_snapshot_policy=approved,
        user_and_workspace_grants=approved,
        claude_agent_runtime_supported=approved,
        materialized_runtime_plugin_ids=materialized,
        loadable_runtime_plugin_ids=loadable,
        deprecated_release_allowed_by_policy=False,
        known_capabilities=known_capabilities,
    )


def make_runtime_context_resolver(
    db: Any,
) -> Callable[[str, str, str, str], RuntimeContext]:
    """Adapt the database resolver to SelectionValidationService's contract."""

    def resolve(
        deck_plugin_id: str,
        deck_plugin_version: str,
        workspace_id: str,
        _actor_id: str,
    ) -> RuntimeContext:
        return resolve_runtime_context(
            db,
            deck_plugin_id=deck_plugin_id,
            deck_plugin_version=deck_plugin_version,
            workspace_id=workspace_id,
        )

    return resolve
