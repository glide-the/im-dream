"""Build the shared Story Workspace preflight service without local closures."""

from __future__ import annotations

import hashlib
import json
from typing import Any
import uuid

try:
    from models.deck_plugin import DeckPluginManifestV1, DeckRuntimePluginLock
    from services.deck.runtime_context import resolve_runtime_context
    from services.deck_plugin.compatibility_service import CompatibilityService
    from services.deck_plugin.installation_service import Scope
    from services.workflow.preflight_service import (
        BindingReleaseContext,
        PreflightCheckError,
        PreflightService,
    )
except ModuleNotFoundError:  # Support package imports from repository root.
    from backend.models.deck_plugin import DeckPluginManifestV1, DeckRuntimePluginLock
    from backend.services.deck.runtime_context import resolve_runtime_context
    from backend.services.deck_plugin.compatibility_service import CompatibilityService
    from backend.services.deck_plugin.installation_service import Scope
    from backend.services.workflow.preflight_service import (
        BindingReleaseContext,
        PreflightCheckError,
        PreflightService,
    )


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _sha256(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


class StoryWorkspacePreflightServiceBuilder:
    """Request-scoped preflight policy and dependency builder.

    Each check is a named method on a standard object. This preserves the
    existing PreflightService contract while removing the former collection of
    closures from the former monolithic Story workflow gateway.
    """

    def __init__(
        self,
        db: Any,
        actor: dict[str, str],
        *,
        token_secret: bytes | str,
    ) -> None:
        self._db = db
        self._actor_id = actor["actor_id"]
        self._workspace_id = actor["workspace_id"]
        self._token_secret = token_secret

    def build(self) -> PreflightService:
        return PreflightService(
            self._db,
            identity_checker=self.check_identity,
            binding_resolver=self.resolve_binding,
            manifest_schema_checker=self.check_manifest,
            compatibility_checker=self.check_compatibility,
            capability_policy_checker=self.check_capabilities,
            deck_snapshot_owner=self.ensure_snapshot,
            runtime_materialization_reader=self.read_materialization,
            token_secret=self._token_secret,
        )

    def check_identity(self, deck_id: str, checked_actor: str) -> dict[str, str]:
        if checked_actor != self._actor_id:
            raise PreflightCheckError("WORKFLOW_PERMISSION_DENIED")
        row = self._db.execute(
            """
            SELECT deck.id FROM decks AS deck
            JOIN story_workspace_workspaces AS workspace
              ON workspace.id = %s AND workspace.owner_id = deck.owner_id
            WHERE deck.id = %s AND deck.owner_id = %s AND deck.enabled IS TRUE
            """,
            (self._workspace_id, deck_id, self._actor_id),
        ).fetchone()
        if row is None:
            raise PreflightCheckError("WORKFLOW_PERMISSION_DENIED")
        return {"workspace_id": self._workspace_id}

    def resolve_binding(
        self,
        deck_id: str,
        binding_revision: int,
    ) -> dict[str, Any]:
        row = self._db.execute(
            """
            SELECT binding.*, release.manifest_json, release.manifest_hash,
                   release.workflow_definition_ref, runtime_lock.id AS lock_id,
                   runtime_lock.lock_json,
                   runtime_lock.deck_plugin_manifest_hash AS lock_manifest_hash
            FROM deck_plugin_bindings AS binding
            JOIN deck_plugin_releases AS release
              ON release.deck_plugin_id = binding.deck_plugin_id
             AND release.deck_plugin_version = binding.deck_plugin_version
            JOIN deck_runtime_plugin_locks AS runtime_lock
              ON runtime_lock.deck_plugin_id = binding.deck_plugin_id
             AND runtime_lock.deck_plugin_version = binding.deck_plugin_version
            WHERE binding.deck_id = %s AND binding.binding_revision = %s
              AND binding.status = 'active' AND binding.workspace_id = %s
              AND binding.creator_id = %s
            """,
            (deck_id, binding_revision, self._workspace_id, self._actor_id),
        ).fetchone()
        if row is None or row["manifest_hash"] != row["lock_manifest_hash"]:
            raise PreflightCheckError("BINDING_REVISION_CONFLICT")
        manifest = DeckPluginManifestV1.model_validate_json(row["manifest_json"])
        runtime_lock = DeckRuntimePluginLock.model_validate_json(row["lock_json"])
        profile_id = "drp_" + hashlib.sha256(
            manifest.runtime_configuration.profile_contract.encode("utf-8")
        ).hexdigest()[:32]
        return {
            "deck_plugin_id": manifest.deck_plugin_id,
            "deck_plugin_version": manifest.deck_plugin_version,
            "runtime_plugin_lock_id": runtime_lock.runtime_plugin_lock_id,
            "deck_runtime_profile_id": profile_id,
            "deck_runtime_snapshot_contract": (
                manifest.compatibility.deck_runtime_snapshot_contract
            ),
            "manifest_hash": row["manifest_hash"],
            "workflow_definition_ref": manifest.workflow.workflow_definition_ref,
            "input_schema_ref": manifest.workflow.input_schema_ref or "schema://none",
            "output_schema_ref": manifest.workflow.output_schema_ref or "schema://none",
            "required_runtime_plugins": [
                {
                    "claude_code_plugin_id": entry.claude_code_plugin_id,
                    "artifact_digest": entry.artifact_digest,
                }
                for entry in runtime_lock.claude_code_plugins
                if entry.required
            ],
        }

    @staticmethod
    def check_manifest(
        binding: BindingReleaseContext,
        input_data: dict[str, Any],
    ) -> bool:
        encoded = _canonical_json(input_data)
        if len(encoded.encode("utf-8")) > 64 * 1024:
            raise PreflightCheckError("DECK_PLUGIN_MANIFEST_INVALID")
        if not binding.output_schema_ref.startswith(("story-workspace/", "schema://")):
            raise PreflightCheckError("STORY_SCHEMA_INCOMPATIBLE")
        return True

    async def check_compatibility(
        self,
        binding: BindingReleaseContext,
        _identity: Any,
    ) -> bool:
        runtime_context = resolve_runtime_context(
            self._db,
            deck_plugin_id=binding.deck_plugin_id,
            deck_plugin_version=binding.deck_plugin_version,
            workspace_id=self._workspace_id,
        )
        scope = self._installation_scope(binding.deck_plugin_id)
        result = await CompatibilityService(self._db).check_compatibility(
            binding.deck_plugin_id,
            binding.deck_plugin_version,
            scope,
            runtime_context,
        )
        if not result.passed:
            raise PreflightCheckError(
                result.error_code or "CLAUDE_AGENT_INCOMPATIBLE"
            )
        return True

    def check_capabilities(
        self,
        binding: BindingReleaseContext,
        _identity: Any,
    ) -> bool:
        installation = self._db.execute(
            """
            SELECT approved_capabilities_json FROM deck_plugin_installations
            WHERE deck_plugin_id = %s AND status = 'ready'
              AND ((scope_type = 'workspace' AND scope_id = %s) OR scope_type = 'instance')
            ORDER BY CASE scope_type WHEN 'workspace' THEN 0 ELSE 1 END,
                     updated_at DESC LIMIT 1
            """,
            (binding.deck_plugin_id, self._workspace_id),
        ).fetchone()
        try:
            approved = (
                set(json.loads(installation["approved_capabilities_json"]))
                if installation
                else set()
            )
        except (TypeError, json.JSONDecodeError):
            approved = set()
        release = self._db.execute(
            "SELECT manifest_json FROM deck_plugin_releases WHERE deck_plugin_id = %s "
            "AND deck_plugin_version = %s",
            (binding.deck_plugin_id, binding.deck_plugin_version),
        ).fetchone()
        manifest = DeckPluginManifestV1.model_validate_json(release["manifest_json"])
        required = {
            capability
            for step in manifest.workflow.steps
            for capability in step.required_capabilities
        }
        if not required.issubset(approved):
            raise PreflightCheckError("WORKFLOW_PERMISSION_DENIED")
        return True

    def ensure_snapshot(
        self,
        deck_id: str,
        profile_id: str,
        contract: str,
    ) -> dict[str, Any]:
        binding = self._db.execute(
            """
            SELECT * FROM deck_plugin_bindings
            WHERE deck_id = %s AND workspace_id = %s AND creator_id = %s AND status = 'active'
            """,
            (deck_id, self._workspace_id, self._actor_id),
        ).fetchone()
        deck = self._db.execute(
            "SELECT id, name, name_zh, name_en, description, description_zh, description_en "
            "FROM decks WHERE id = %s AND owner_id = %s",
            (deck_id, self._actor_id),
        ).fetchone()
        voices = self._db.execute(
            "SELECT id, name, name_zh, name_en, system_prompt FROM voices "
            "WHERE deck_id = %s AND enabled IS TRUE ORDER BY order_index, id",
            (deck_id,),
        ).fetchall()
        if binding is None or deck is None:
            raise PreflightCheckError("DECK_RUNTIME_CONFIG_INVALID")
        config = {
            "deck": dict(deck),
            "voices": [dict(voice) for voice in voices],
            "binding": {
                "deck_plugin_binding_id": binding["deck_plugin_binding_id"],
                "binding_revision": binding["binding_revision"],
                "deck_plugin_id": binding["deck_plugin_id"],
                "deck_plugin_version": binding["deck_plugin_version"],
            },
            "profile_id": profile_id,
            "snapshot_contract": contract,
        }
        config_json = _canonical_json(config)
        config_hash = _sha256(config_json)
        existing = self._db.execute(
            """
            SELECT deck_runtime_snapshot_id, sanitized_summary_hash
            FROM deck_runtime_snapshots
            WHERE deck_id = %s AND binding_revision = %s
              AND deck_runtime_profile_id = %s AND config_hash = %s
            """,
            (deck_id, binding["binding_revision"], profile_id, config_hash),
        ).fetchone()
        if existing is not None:
            return {
                "deck_runtime_snapshot_id": existing["deck_runtime_snapshot_id"],
                "sanitized_summary_hash": existing["sanitized_summary_hash"],
                "reused": True,
            }
        snapshot_id = "drs_" + uuid.uuid4().hex
        summary_hash = _sha256(
            _canonical_json(
                {
                    "deck_id": deck_id,
                    "binding_revision": binding["binding_revision"],
                    "profile_id": profile_id,
                    "voice_count": len(voices),
                    "config_hash": config_hash,
                }
            )
        )
        try:
            self._db.execute(
                """
                INSERT INTO deck_runtime_snapshots (
                    deck_runtime_snapshot_id, deck_id, deck_plugin_binding_id,
                    binding_revision, deck_runtime_profile_id, snapshot_contract,
                    config_hash, config_json, sanitized_summary_hash
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    snapshot_id,
                    deck_id,
                    binding["deck_plugin_binding_id"],
                    binding["binding_revision"],
                    profile_id,
                    contract,
                    config_hash,
                    config_json,
                    summary_hash,
                ),
            )
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise
        return {
            "deck_runtime_snapshot_id": snapshot_id,
            "sanitized_summary_hash": summary_hash,
            "reused": False,
        }

    def read_materialization(self, runtime_lock_id: str) -> dict[str, Any]:
        lock_row = self._db.execute(
            "SELECT lock_json FROM deck_runtime_plugin_locks WHERE id = %s",
            (runtime_lock_id,),
        ).fetchone()
        if lock_row is None:
            raise PreflightCheckError("RUNTIME_PLUGIN_NOT_READY")
        runtime_lock = DeckRuntimePluginLock.model_validate_json(lock_row["lock_json"])
        plugins: list[dict[str, Any]] = []
        smoke_passed = True
        for entry in runtime_lock.claude_code_plugins:
            row = self._db.execute(
                """
                SELECT * FROM runtime_plugin_materializations
                WHERE claude_code_plugin_id = %s AND resolved_version = %s
                  AND artifact_digest = %s
                ORDER BY updated_at DESC LIMIT 1
                """,
                (
                    entry.claude_code_plugin_id,
                    entry.resolved_version,
                    entry.artifact_digest,
                ),
            ).fetchone()
            if row is None:
                plugins.append(
                    {
                        "claude_code_plugin_id": entry.claude_code_plugin_id,
                        "declaration_status": "undeclared",
                        "materialization_status": "missing",
                        "activation_status": "inactive",
                        "artifact_digest": entry.artifact_digest,
                    }
                )
                smoke_passed = False
                continue
            plugins.append(
                {
                    "claude_code_plugin_id": entry.claude_code_plugin_id,
                    "declaration_status": row["declaration_status"],
                    "materialization_status": row["materialization_status"],
                    "activation_status": row["activation_status"],
                    "artifact_digest": row["artifact_digest"],
                }
            )
            smoke_passed = smoke_passed and bool(
                row["materialized_digest"] == entry.artifact_digest
                and row["verification_status"] in {"verified", "legacy_unverified"}
                and row["materialization_status"] == "materialized"
                and row["activation_status"] in {"loadable", "loaded"}
            )
        return {
            "runtime_plugin_lock_id": runtime_lock_id,
            "plugins": plugins,
            "load_smoke_passed": smoke_passed,
        }

    def _installation_scope(self, deck_plugin_id: str) -> Scope:
        row = self._db.execute(
            """
            SELECT scope_type, scope_id FROM deck_plugin_installations
            WHERE scope_type = 'workspace' AND scope_id = %s AND deck_plugin_id = %s
              AND status = 'ready'
            """,
            (self._workspace_id, deck_plugin_id),
        ).fetchone()
        if row is None:
            row = self._db.execute(
                """
                SELECT scope_type, scope_id FROM deck_plugin_installations
                WHERE scope_type = 'instance' AND deck_plugin_id = %s AND status = 'ready'
                ORDER BY updated_at DESC LIMIT 1
                """,
                (deck_plugin_id,),
            ).fetchone()
        if row is None:
            raise PreflightCheckError("DECK_PLUGIN_UNAVAILABLE")
        return Scope(scope_type=row["scope_type"], scope_id=row["scope_id"])


__all__ = ["StoryWorkspacePreflightServiceBuilder"]
