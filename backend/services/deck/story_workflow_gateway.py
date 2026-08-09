"""Application wiring for Dream workflow preflight and run APIs."""

from __future__ import annotations

from psycopg import Error as PostgresError

import asyncio
from dataclasses import dataclass, replace
from datetime import UTC, datetime
import hashlib
import importlib.util
import json
import logging
import os
from pathlib import Path
import stat
import sys
from typing import Any
import uuid

import database

try:
    from models.deck_plugin import DeckPluginManifestV1, DeckRuntimePluginLock
    from models.workflow_run import AuthenticatedActorContext, RunStatus, WorkflowRun
    from story_workspace.contracts import (
        StoryWorkspaceDreamAgentMessageCommand,
        StoryWorkspaceDreamAgentToolConfirmationCommand,
        StoryWorkspaceDreamRunContext,
        StoryWorkspaceEpisodeActionContinueCommand,
        StoryWorkspaceEpisodeActionContinueCommandV2,
        StoryWorkspaceEpisodeBindingRecoveryCommand,
    )
    from services.deck.runtime_context import resolve_runtime_context
    from services.deck_plugin.compatibility_service import CompatibilityService
    from services.deck_plugin.installation_service import Scope
    from services.errors.error_registry import ApiRouteError
    from services.story_workspace.dream_file_service import (
        StoryWorkspaceDreamContractError,
        StoryWorkspaceDreamDurabilityIndeterminate,
        StoryWorkspaceDreamFileError,
        StoryWorkspaceDreamFileReader,
        StoryWorkspaceDreamIOError,
        StoryWorkspaceDreamPathError,
        StoryWorkspaceDreamPlatformUnsupported,
    )
    from services.workflow.preflight_service import (
        BindingReleaseContext,
        PreflightCheckError,
        PreflightService,
    )
    from services.workflow.run_service import WorkflowRunError, WorkflowRunService
    from services.story_workspace.guidance_service import (
        StoryWorkspaceGuidanceError,
        StoryWorkspaceGuidanceService,
        build_thread_turn_dispatcher,
    )
    from services.story_workspace.dream_confirmation_service import (
        StoryWorkspacePersistedDreamConfirmation,
        StoryWorkspaceDreamConfirmationCoordinator,
        StoryWorkspaceDreamConfirmationError,
        StoryWorkspaceDreamConfirmationService,
        story_workspace_read_dream_confirmation_fact,
    )
    from services.story_workspace.dream_launch_gateway import (
        StoryWorkspaceDreamLaunchGateway,
        StoryWorkspaceDreamLaunchGatewayError,
    )
    from services.story_workspace.dream_launch_service import (
        StoryWorkspaceDreamLaunchIdempotencyConflict,
        StoryWorkspaceDreamLaunchProvenanceError,
    )
    from services.story_workspace.dream_reentry_service import (
        StoryWorkspaceDreamReentryService,
    )
    from services.story_workspace.episode_artifact_service import (
        StoryWorkspaceEpisodeArtifactContractError,
        StoryWorkspaceEpisodeArtifactError,
        StoryWorkspaceEpisodeArtifactPathError,
        StoryWorkspaceEpisodeArtifactService,
        StoryWorkspaceEpisodeAuthority,
    )
    from services.story_workspace.episode_action_service import (
        StoryWorkspaceEpisodeActionError,
        StoryWorkspaceEpisodeNextActionResolver,
        StoryWorkspaceEpisodeActionService,
        StoryWorkspaceEpisodeWorkflowFactError,
        StoryWorkspaceEpisodeWorkflowFactService,
    )
    from services.story_workspace.episode_binding_service import (
        StoryWorkspaceEpisodeBindingContext,
        StoryWorkspaceEpisodeBindingError,
        StoryWorkspaceEpisodeBindingService,
    )
    from services.story_workspace.multi_episode_action_service import (
        StoryWorkspaceEpisodeActionProjectionService,
    )
    from services.story_workspace.episode_workflow_instruction import (
        StoryWorkspaceEpisodeActionSelectionError,
        StoryWorkspaceTrustedEpisodeActionSelector,
    )
    from services.story_workspace.dream_agent_message_service import (
        StoryWorkspaceDreamAgentMessageError,
        StoryWorkspaceDreamAgentMessageCoordinator,
        StoryWorkspaceDreamAgentMessageService,
    )
except ModuleNotFoundError:  # Support package imports from repository root.
    from backend.models.deck_plugin import DeckPluginManifestV1, DeckRuntimePluginLock
    from backend.models.workflow_run import AuthenticatedActorContext, RunStatus, WorkflowRun
    from backend.story_workspace.contracts import (
        StoryWorkspaceDreamAgentMessageCommand,
        StoryWorkspaceDreamAgentToolConfirmationCommand,
        StoryWorkspaceDreamRunContext,
        StoryWorkspaceEpisodeActionContinueCommand,
        StoryWorkspaceEpisodeActionContinueCommandV2,
        StoryWorkspaceEpisodeBindingRecoveryCommand,
    )
    from backend.services.deck.runtime_context import resolve_runtime_context
    from backend.services.deck_plugin.compatibility_service import CompatibilityService
    from backend.services.deck_plugin.installation_service import Scope
    from backend.services.errors.error_registry import ApiRouteError
    from backend.services.story_workspace.dream_file_service import (
        StoryWorkspaceDreamContractError,
        StoryWorkspaceDreamDurabilityIndeterminate,
        StoryWorkspaceDreamFileError,
        StoryWorkspaceDreamFileReader,
        StoryWorkspaceDreamIOError,
        StoryWorkspaceDreamPathError,
        StoryWorkspaceDreamPlatformUnsupported,
    )
    from backend.services.workflow.preflight_service import (
        BindingReleaseContext,
        PreflightCheckError,
        PreflightService,
    )
    from backend.services.workflow.run_service import WorkflowRunError, WorkflowRunService
    from backend.services.story_workspace.guidance_service import (
        StoryWorkspaceGuidanceError,
        StoryWorkspaceGuidanceService,
        build_thread_turn_dispatcher,
    )
    from backend.services.story_workspace.dream_confirmation_service import (
        StoryWorkspacePersistedDreamConfirmation,
        StoryWorkspaceDreamConfirmationCoordinator,
        StoryWorkspaceDreamConfirmationError,
        StoryWorkspaceDreamConfirmationService,
        story_workspace_read_dream_confirmation_fact,
    )
    from backend.services.story_workspace.dream_launch_gateway import (
        StoryWorkspaceDreamLaunchGateway,
        StoryWorkspaceDreamLaunchGatewayError,
    )
    from backend.services.story_workspace.dream_launch_service import (
        StoryWorkspaceDreamLaunchIdempotencyConflict,
        StoryWorkspaceDreamLaunchProvenanceError,
    )
    from backend.services.story_workspace.dream_reentry_service import (
        StoryWorkspaceDreamReentryService,
    )
    from backend.services.story_workspace.episode_artifact_service import (
        StoryWorkspaceEpisodeArtifactContractError,
        StoryWorkspaceEpisodeArtifactError,
        StoryWorkspaceEpisodeArtifactPathError,
        StoryWorkspaceEpisodeArtifactService,
        StoryWorkspaceEpisodeAuthority,
    )
    from backend.services.story_workspace.episode_action_service import (
        StoryWorkspaceEpisodeActionError,
        StoryWorkspaceEpisodeNextActionResolver,
        StoryWorkspaceEpisodeActionService,
        StoryWorkspaceEpisodeWorkflowFactError,
        StoryWorkspaceEpisodeWorkflowFactService,
    )
    from backend.services.story_workspace.episode_binding_service import (
        StoryWorkspaceEpisodeBindingContext,
        StoryWorkspaceEpisodeBindingError,
        StoryWorkspaceEpisodeBindingService,
    )
    from backend.services.story_workspace.multi_episode_action_service import (
        StoryWorkspaceEpisodeActionProjectionService,
    )
    from backend.services.story_workspace.episode_workflow_instruction import (
        StoryWorkspaceEpisodeActionSelectionError,
        StoryWorkspaceTrustedEpisodeActionSelector,
    )
    from backend.services.story_workspace.dream_agent_message_service import (
        StoryWorkspaceDreamAgentMessageError,
        StoryWorkspaceDreamAgentMessageCoordinator,
        StoryWorkspaceDreamAgentMessageService,
    )


_DEVELOPMENT_ENVIRONMENTS = {"development", "dev", "test", "testing"}
_DEV_TOKEN_SECRET = "ink-dream-development-workflow-token-secret-v1"
logger = logging.getLogger(__name__)
_DREAM_CONFIRMATION_COORDINATOR = StoryWorkspaceDreamConfirmationCoordinator(
    database.get_db,
)


@dataclass(frozen=True)
class StoryWorkspaceDreamReentryStageProjection:
    """Validated Dream files plus the newest canonical stage file timestamp."""

    stages: Any
    stage_activity_at: datetime | None


def story_workspace_get_workspace_root() -> Path:
    """Load the canonical workspace resolver only when this projection runs."""

    try:
        from libs.claude_agent_kit.server.workspace import (
            get_workspace_root as resolve_workspace_root,
        )
    except ModuleNotFoundError:
        # Importing the parent package eagerly loads the optional agent SDK.
        # Dream file reads only need the dependency-free canonical resolver,
        # so load that source module directly when the SDK is absent (or when
        # this file is imported through the repository-root package layout).
        module_name = "_ink_story_workspace_root_resolver"
        workspace_module = sys.modules.get(module_name)
        if workspace_module is None:
            module_path = (
                Path(__file__).resolve().parents[2]
                / "libs"
                / "claude_agent_kit"
                / "server"
                / "workspace.py"
            )
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            if spec is None or spec.loader is None:
                raise ModuleNotFoundError("canonical workspace resolver unavailable")
            workspace_module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = workspace_module
            try:
                spec.loader.exec_module(workspace_module)
            except BaseException:
                sys.modules.pop(module_name, None)
                raise
        resolve_workspace_root = workspace_module.get_workspace_root
    return resolve_workspace_root()


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


def _token_secret() -> str:
    explicit = os.getenv("INK_WORKFLOW_TOKEN_SECRET") or os.getenv("JWT_SECRET")
    if explicit and len(explicit.encode("utf-8")) >= 32:
        return explicit
    environment = os.getenv("INK_ENVIRONMENT", "unknown").strip().lower()
    if environment in _DEVELOPMENT_ENVIRONMENTS:
        return _DEV_TOKEN_SECRET
    raise ApiRouteError("DECK_RUNTIME_CONFIG_UNAVAILABLE", status_code=503)


class StoryWorkflowApplicationGateway:
    def __init__(
        self,
        *,
        dream_confirmation_coordinator: (
            StoryWorkspaceDreamConfirmationCoordinator | None
        ) = None,
    ) -> None:
        self._dream_confirmation_coordinator = (
            dream_confirmation_coordinator or _DREAM_CONFIRMATION_COORDINATOR
        )
        self._dream_agent_message_coordinator = (
            StoryWorkspaceDreamAgentMessageCoordinator(
                self._dispatch_dream_agent_message
            )
        )

    @staticmethod
    def _actor(actor: dict[str, str]) -> AuthenticatedActorContext:
        return AuthenticatedActorContext(
            workspace_id=actor["workspace_id"],
            actor_id=actor["actor_id"],
        )

    @staticmethod
    def _run_actor_context(
        db: Any,
        workflow_run_id: str,
        actor_id: int,
    ) -> AuthenticatedActorContext:
        """Resolve the run-owned workspace without selecting an actor default."""

        owns_workspace = db.execute(
            "SELECT id FROM story_workspace_workspaces "
            "WHERE owner_id = %s LIMIT 1",
            (actor_id,),
        ).fetchone()
        if owns_workspace is None:
            raise ApiRouteError("WORKFLOW_PERMISSION_DENIED", status_code=403)
        row = db.execute(
            "SELECT run.workspace_id FROM workflow_runs AS run "
            "JOIN story_workspace_workspaces AS workspace "
            "ON workspace.id = run.workspace_id "
            "WHERE run.id = %s AND run.created_by = %s AND workspace.owner_id = %s",
            (workflow_run_id, str(actor_id), actor_id),
        ).fetchone()
        if row is None:
            raise ApiRouteError("WORKFLOW_PERMISSION_DENIED", status_code=404)
        return AuthenticatedActorContext(
            workspace_id=str(row["workspace_id"]),
            actor_id=str(actor_id),
        )

    @staticmethod
    def _raise_run_error(exc: WorkflowRunError) -> None:
        mapping = {
            "IDEMPOTENCY_CONFLICT": ("IDEMPOTENCY_CONFLICT", 409),
            "ILLEGAL_RUN_TRANSITION": ("WORKFLOW_STEP_FAILED", 409),
            "WORKFLOW_RUN_NOT_FOUND": ("AGENT_EXECUTION_FAILED", 404),
            "PREFLIGHT_NOT_FOUND_OR_NOT_AUTHORIZED": ("WORKFLOW_PERMISSION_DENIED", 404),
            "PREFLIGHT_TOKEN_INVALID": ("WORKFLOW_PERMISSION_DENIED", 409),
            "PREFLIGHT_TOKEN_EXPIRED": ("DECK_RUNTIME_CONFIG_UNAVAILABLE", 409),
            "PREFLIGHT_TOKEN_REPLAYED": ("IDEMPOTENCY_CONFLICT", 409),
            "RETRY_SOURCE_MISMATCH": ("CONFIG_VERSION_DRIFT", 409),
        }
        code, status = mapping.get(exc.code, ("AGENT_EXECUTION_FAILED", 422))
        raise ApiRouteError(code, status_code=status) from exc

    @staticmethod
    def _thread_workspace(thread_id: str) -> Path:
        """Resolve one existing, real thread directory without creating it."""

        if (
            not isinstance(thread_id, str)
            or not thread_id.strip()
            or Path(thread_id).parts != (thread_id,)
            or thread_id in {".", ".."}
        ):
            raise ApiRouteError("WORKFLOW_PERMISSION_DENIED", status_code=403)

        supplied_root = Path(story_workspace_get_workspace_root())
        try:
            resolved_root = supplied_root.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise ApiRouteError(
                "DECK_RUNTIME_CONFIG_UNAVAILABLE",
                status_code=503,
            ) from exc
        if not resolved_root.is_dir():
            raise ApiRouteError("DECK_RUNTIME_CONFIG_UNAVAILABLE", status_code=503)

        supplied_workspace = supplied_root / thread_id
        try:
            metadata = supplied_workspace.lstat()
        except FileNotFoundError as exc:
            raise ApiRouteError("AGENT_EXECUTION_FAILED", status_code=404) from exc
        except (OSError, ValueError) as exc:
            raise ApiRouteError(
                "DECK_RUNTIME_CONFIG_UNAVAILABLE",
                status_code=503,
            ) from exc
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise ApiRouteError("WORKFLOW_PERMISSION_DENIED", status_code=403)

        try:
            resolved_workspace = supplied_workspace.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise ApiRouteError("WORKFLOW_PERMISSION_DENIED", status_code=403) from exc
        if (
            not resolved_workspace.is_relative_to(resolved_root)
            or resolved_workspace.parent != resolved_root
        ):
            raise ApiRouteError("WORKFLOW_PERMISSION_DENIED", status_code=403)
        return resolved_workspace

    @staticmethod
    def _raise_dream_file_error(exc: StoryWorkspaceDreamFileError) -> None:
        if isinstance(exc, StoryWorkspaceDreamPlatformUnsupported):
            raise ApiRouteError("AGENT_EXECUTION_FAILED", status_code=501) from exc
        if isinstance(exc, StoryWorkspaceDreamDurabilityIndeterminate):
            raise ApiRouteError("RESULT_COMMIT_FAILED", status_code=409) from exc
        if isinstance(exc, StoryWorkspaceDreamPathError):
            raise ApiRouteError("WORKFLOW_PERMISSION_DENIED", status_code=403) from exc
        if isinstance(exc, StoryWorkspaceDreamContractError):
            raise ApiRouteError("OUTPUT_CONTRACT_INVALID", status_code=422) from exc
        if isinstance(exc, StoryWorkspaceDreamIOError):
            raise ApiRouteError(
                "DECK_RUNTIME_CONFIG_UNAVAILABLE",
                status_code=503,
            ) from exc
        raise ApiRouteError("AGENT_EXECUTION_FAILED", status_code=422) from exc

    @staticmethod
    def _installation_scope(
        db: Any,
        workspace_id: str,
        deck_plugin_id: str,
    ) -> Scope:
        row = db.execute(
            """
            SELECT scope_type, scope_id FROM deck_plugin_installations
            WHERE scope_type = 'workspace' AND scope_id = %s AND deck_plugin_id = %s
              AND status = 'ready'
            """,
            (workspace_id, deck_plugin_id),
        ).fetchone()
        if row is None:
            row = db.execute(
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

    def _preflight_service(
        self,
        db: Any,
        actor: dict[str, str],
    ) -> PreflightService:
        actor_id = actor["actor_id"]
        workspace_id = actor["workspace_id"]

        def identity_checker(deck_id: str, checked_actor: str) -> dict[str, str]:
            if checked_actor != actor_id:
                raise PreflightCheckError("WORKFLOW_PERMISSION_DENIED")
            row = db.execute(
                """
                SELECT deck.id FROM decks AS deck
                JOIN story_workspace_workspaces AS workspace
                  ON workspace.id = %s AND workspace.owner_id = deck.owner_id
                WHERE deck.id = %s AND deck.owner_id = %s AND deck.enabled IS TRUE
                """,
                (workspace_id, deck_id, actor_id),
            ).fetchone()
            if row is None:
                raise PreflightCheckError("WORKFLOW_PERMISSION_DENIED")
            return {"workspace_id": workspace_id}

        def binding_resolver(deck_id: str, binding_revision: int) -> dict[str, Any]:
            row = db.execute(
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
                (deck_id, binding_revision, workspace_id, actor_id),
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
                "deck_runtime_snapshot_contract": manifest.compatibility.deck_runtime_snapshot_contract,
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

        def manifest_checker(binding: BindingReleaseContext, input_data: dict[str, Any]) -> bool:
            encoded = _canonical_json(input_data)
            if len(encoded.encode("utf-8")) > 64 * 1024:
                raise PreflightCheckError("DECK_PLUGIN_MANIFEST_INVALID")
            if not binding.output_schema_ref.startswith(("story-workspace/", "schema://")):
                raise PreflightCheckError("STORY_SCHEMA_INCOMPATIBLE")
            return True

        async def compatibility_checker(
            binding: BindingReleaseContext,
            _identity: Any,
        ) -> bool:
            runtime_context = resolve_runtime_context(
                db,
                deck_plugin_id=binding.deck_plugin_id,
                deck_plugin_version=binding.deck_plugin_version,
                workspace_id=workspace_id,
            )
            scope = self._installation_scope(db, workspace_id, binding.deck_plugin_id)
            result = await CompatibilityService(db).check_compatibility(
                binding.deck_plugin_id,
                binding.deck_plugin_version,
                scope,
                runtime_context,
            )
            if not result.passed:
                raise PreflightCheckError(result.error_code or "CLAUDE_AGENT_INCOMPATIBLE")
            return True

        def capability_checker(binding: BindingReleaseContext, _identity: Any) -> bool:
            installation = db.execute(
                """
                SELECT approved_capabilities_json FROM deck_plugin_installations
                WHERE deck_plugin_id = %s AND status = 'ready'
                  AND ((scope_type = 'workspace' AND scope_id = %s) OR scope_type = 'instance')
                ORDER BY CASE scope_type WHEN 'workspace' THEN 0 ELSE 1 END,
                         updated_at DESC LIMIT 1
                """,
                (binding.deck_plugin_id, workspace_id),
            ).fetchone()
            try:
                approved = set(json.loads(installation["approved_capabilities_json"])) if installation else set()
            except (TypeError, json.JSONDecodeError):
                approved = set()
            release = db.execute(
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

        def snapshot_owner(deck_id: str, profile_id: str, contract: str) -> dict[str, Any]:
            binding = db.execute(
                """
                SELECT * FROM deck_plugin_bindings
                WHERE deck_id = %s AND workspace_id = %s AND creator_id = %s AND status = 'active'
                """,
                (deck_id, workspace_id, actor_id),
            ).fetchone()
            deck = db.execute(
                "SELECT id, name, name_zh, name_en, description, description_zh, description_en "
                "FROM decks WHERE id = %s AND owner_id = %s",
                (deck_id, actor_id),
            ).fetchone()
            voices = db.execute(
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
            existing = db.execute(
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
                db.execute(
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
                db.commit()
            except Exception:
                db.rollback()
                raise
            return {
                "deck_runtime_snapshot_id": snapshot_id,
                "sanitized_summary_hash": summary_hash,
                "reused": False,
            }

        def materialization_reader(runtime_lock_id: str) -> dict[str, Any]:
            lock_row = db.execute(
                "SELECT lock_json FROM deck_runtime_plugin_locks WHERE id = %s",
                (runtime_lock_id,),
            ).fetchone()
            if lock_row is None:
                raise PreflightCheckError("RUNTIME_PLUGIN_NOT_READY")
            runtime_lock = DeckRuntimePluginLock.model_validate_json(lock_row["lock_json"])
            plugins: list[dict[str, Any]] = []
            smoke_passed = True
            for entry in runtime_lock.claude_code_plugins:
                row = db.execute(
                    """
                    SELECT * FROM runtime_plugin_materializations
                    WHERE claude_code_plugin_id = %s AND resolved_version = %s
                      AND artifact_digest = %s
                    ORDER BY updated_at DESC LIMIT 1
                    """,
                    (entry.claude_code_plugin_id, entry.resolved_version, entry.artifact_digest),
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

        return PreflightService(
            db,
            identity_checker=identity_checker,
            binding_resolver=binding_resolver,
            manifest_schema_checker=manifest_checker,
            compatibility_checker=compatibility_checker,
            capability_policy_checker=capability_checker,
            deck_snapshot_owner=snapshot_owner,
            runtime_materialization_reader=materialization_reader,
            token_secret=_token_secret(),
        )

    async def create_preflight(self, request: Any, *, actor: dict[str, str]) -> Any:
        db = database.get_db()
        try:
            return await self._preflight_service(db, actor).execute_preflight(
                request.deck_id,
                request.binding_revision,
                request.input_data,
                actor["actor_id"],
            )
        finally:
            db.close()

    async def start_dream_run(
        self,
        request: Any,
        *,
        actor: dict[str, str],
    ) -> Any:
        """Provision server-owned Dream dependencies and start one Agent turn."""

        db = database.get_db()
        try:
            gateway = StoryWorkspaceDreamLaunchGateway(
                db,
                preflight_service=self._preflight_service(db, actor),
                token_secret=_token_secret(),
            )
            return await gateway.start(request, actor=actor)
        except StoryWorkspaceDreamLaunchIdempotencyConflict as exc:
            raise ApiRouteError("IDEMPOTENCY_CONFLICT", status_code=409) from exc
        except StoryWorkspaceDreamLaunchProvenanceError as exc:
            raise ApiRouteError(
                "DECK_RUNTIME_CONFIG_INVALID", status_code=409
            ) from exc
        except StoryWorkspaceDreamLaunchGatewayError as exc:
            raise ApiRouteError(exc.code, status_code=exc.status_code) from exc
        except WorkflowRunError as exc:
            self._raise_run_error(exc)
        except PermissionError as exc:
            raise ApiRouteError(
                "WORKFLOW_PERMISSION_DENIED", status_code=403
            ) from exc
        finally:
            db.close()

    async def get_preflight(self, preflight_id: str, *, actor: dict[str, str]) -> Any:
        db = database.get_db()
        try:
            return self._preflight_service(db, actor).read_preflight(
                preflight_id,
                actor=actor["actor_id"],
            )
        except PreflightCheckError as exc:
            raise ApiRouteError(exc.code, status_code=404) from exc
        finally:
            db.close()

    async def create_run(self, request: Any, *, actor: dict[str, str]) -> Any:
        db = database.get_db()
        try:
            service = WorkflowRunService(db, token_secret=_token_secret())
            source_time = (
                datetime.fromisoformat(request.source_message_time.replace("Z", "+00:00"))
                if request.source_message_time
                else None
            )
            return await service.create_run(
                request.workflow_preflight_id,
                request.preflight_token,
                request.idempotency_key,
                request.source_voice_thread_id,
                self._actor(actor),
                source_message_id=request.source_message_id,
                source_message_time=source_time,
            )
        except WorkflowRunError as exc:
            self._raise_run_error(exc)
        finally:
            db.close()

    async def get_run(self, workflow_run_id: str, *, actor: dict[str, str]) -> Any:
        db = database.get_db()
        try:
            return WorkflowRunService(db, token_secret=_token_secret()).read_run(
                workflow_run_id,
                self._actor(actor),
            )
        except WorkflowRunError as exc:
            self._raise_run_error(exc)
        finally:
            db.close()

    async def get_dream_files(
        self,
        workflow_run_id: str,
        *,
        actor: dict[str, str],
    ) -> Any:
        """Project Dream files without blocking the application event loop."""

        return await asyncio.to_thread(
            self._get_dream_files_sync,
            workflow_run_id,
            actor,
        )

    async def get_episode_artifacts(
        self,
        workflow_run_id: str,
        *,
        actor: dict[str, str],
    ) -> Any:
        """Project the bound Episode only after full run provenance authorization."""

        return await asyncio.to_thread(
            self._get_episode_artifacts_sync,
            workflow_run_id,
            actor,
        )

    async def recover_episode_binding(
        self,
        workflow_run_id: str,
        request: StoryWorkspaceEpisodeBindingRecoveryCommand,
        *,
        actor: dict[str, str],
    ) -> Any:
        """Dispatch one path-free identity recovery intent on the bound thread."""

        accepted, pending = await asyncio.to_thread(
            self._recover_episode_binding_sync,
            workflow_run_id,
            request,
            actor,
        )
        if pending is not None:
            self._dream_agent_message_coordinator.schedule(pending)
        return accepted

    async def continue_episode_action(
        self,
        workflow_run_id: str,
        request: StoryWorkspaceEpisodeActionContinueCommand
        | StoryWorkspaceEpisodeActionContinueCommandV2,
        *,
        actor: dict[str, str],
        if_match: str,
    ) -> Any:
        """Revalidate and dispatch one server-derived Episode capability."""

        accepted, pending = await asyncio.to_thread(
            self._continue_episode_action_sync,
            workflow_run_id,
            request,
            actor,
            if_match,
        )
        if pending is not None:
            self._dream_agent_message_coordinator.schedule(pending)
        return accepted

    async def get_dream_agent_messages(
        self,
        workflow_run_id: str,
        *,
        actor: dict[str, str],
    ) -> Any:
        """Return only the allowlisted persisted message projection for a run."""

        snapshot = await asyncio.to_thread(
            self._get_dream_agent_messages_sync, workflow_run_id, actor
        )
        await self._recover_dream_agent_messages(workflow_run_id, actor)
        return snapshot

    async def stream_dream_agent_events(
        self,
        workflow_run_id: str,
        *,
        actor: dict[str, str],
        after: str | None,
    ) -> Any:
        """Authorize before exposing a filtered, run-bound SSE generator."""

        context = await asyncio.to_thread(
            self._load_dream_agent_context_sync, workflow_run_id, actor
        )
        db = database.get_db()
        try:
            service = StoryWorkspaceDreamAgentMessageService(
                db,
                thread_factory=self._dream_agent_thread_factory(),
                db_factory=database.get_db,
            )
        finally:
            # events() uses only the authenticated thread factory; durable data
            # is always read through the snapshot endpoint.
            db.close()
        return service.events(
            thread_id=context.thread_id,
            run_id=workflow_run_id,
            actor_id=actor["actor_id"],
            after=after,
        )

    async def submit_dream_agent_message(
        self,
        workflow_run_id: str,
        request: StoryWorkspaceDreamAgentMessageCommand,
        *,
        actor: dict[str, str],
    ) -> Any:
        """Claim one same-thread command, then dispatch it without holding HTTP."""

        accepted, pending = await asyncio.to_thread(
            self._claim_dream_agent_message_sync,
            workflow_run_id,
            request,
            actor,
        )
        if pending is not None:
            self._dream_agent_message_coordinator.schedule(pending)
        return accepted

    async def confirm_dream_agent_tool(
        self,
        workflow_run_id: str,
        request: StoryWorkspaceDreamAgentToolConfirmationCommand,
        *,
        actor: dict[str, str],
    ) -> Any:
        """Resolve a tool against the server-derived run thread and live turn."""

        context = await asyncio.to_thread(
            self._load_dream_agent_context_sync,
            workflow_run_id,
            actor,
        )
        db = database.get_db()
        try:
            service = StoryWorkspaceDreamAgentMessageService(
                db,
                thread_factory=self._dream_agent_thread_factory(),
            )
            try:
                return service.confirm_tool(
                    run_id=workflow_run_id,
                    thread_id=context.thread_id,
                    actor_id=actor["actor_id"],
                    command=request,
                )
            except StoryWorkspaceDreamAgentMessageError as exc:
                raise ApiRouteError(exc.code, status_code=exc.status_code) from exc
        finally:
            db.close()

    async def _recover_dream_agent_messages(
        self,
        workflow_run_id: str,
        actor: dict[str, str],
    ) -> None:
        """Resume a durable pending/expired claim when its owner re-enters."""

        try:
            pending = await asyncio.to_thread(
                self._recover_dream_agent_messages_sync,
                workflow_run_id,
                actor,
            )
        except Exception:
            logger.exception(
                "Dream Agent pending recovery deferred for run_id=%s",
                workflow_run_id,
            )
            return
        for item in pending:
            self._dream_agent_message_coordinator.schedule(item)

    def _recover_dream_agent_messages_sync(
        self,
        workflow_run_id: str,
        actor: dict[str, str],
    ) -> list[Any]:
        """Reclaim only the same durable key; never synthesize a new command."""

        db = database.get_db()
        try:
            context = self._load_dream_agent_context_from_db(
                db, workflow_run_id, actor
            )
            rows = db.execute(
                "SELECT id, parts, metadata FROM chat_message "
                "WHERE thread_id = %s AND role = 'user'",
                (context.thread_id,),
            ).fetchall()
            service = StoryWorkspaceDreamAgentMessageService(
                db,
                thread_factory=self._dream_agent_thread_factory(),
                db_factory=database.get_db,
            )
            pending: list[Any] = []
            for row in rows:
                try:
                    metadata = json.loads(row["metadata"] or "{}")
                    parts = json.loads(row["parts"] or "[]")
                except (TypeError, ValueError):
                    continue
                if not (
                    isinstance(metadata, dict)
                    and metadata.get("kind") == "story-workspace-dream-agent-user"
                    and metadata.get("story_workspace_run_id") == workflow_run_id
                    and str(metadata.get("actor_id") or "") == actor["actor_id"]
                    and metadata.get("dispatch_status") in {"pending", "dispatching"}
                    and isinstance(metadata.get("idempotency_key"), str)
                ):
                    continue
                text = "".join(
                    part.get("text", "")
                    for part in parts
                    if isinstance(part, dict)
                    and part.get("type") == "text"
                    and isinstance(part.get("text"), str)
                ).strip()
                if not text:
                    continue
                try:
                    command = StoryWorkspaceDreamAgentMessageCommand(
                        text=text,
                        idempotencyKey=metadata["idempotency_key"],
                    )
                    _accepted, dispatch = service.claim_message(
                        run_id=workflow_run_id,
                        thread_id=context.thread_id,
                        actor_id=actor["actor_id"],
                        context=context,
                        command=command,
                    )
                except StoryWorkspaceDreamAgentMessageError:
                    continue
                if dispatch is not None:
                    pending.append(dispatch)
            return pending
        finally:
            db.close()

    @staticmethod
    def _dream_agent_thread_factory() -> Any | None:
        try:
            from agent_factory import claude_agent_thread_factory

            return claude_agent_thread_factory
        except Exception:
            # A cold/restarted process still has a valid persistent snapshot;
            # it simply has no live stream to attach.
            return None

    def _get_dream_agent_messages_sync(
        self,
        workflow_run_id: str,
        actor: dict[str, str],
    ) -> Any:
        db = database.get_db()
        try:
            context = self._load_dream_agent_context_from_db(
                db, workflow_run_id, actor
            )
            return StoryWorkspaceDreamAgentMessageService(
                db,
                thread_factory=self._dream_agent_thread_factory(),
            ).snapshot(
                run_id=workflow_run_id,
                thread_id=context.thread_id,
                actor_id=actor["actor_id"],
            )
        finally:
            db.close()

    def _claim_dream_agent_message_sync(
        self,
        workflow_run_id: str,
        request: StoryWorkspaceDreamAgentMessageCommand,
        actor: dict[str, str],
    ) -> Any:
        db = database.get_db()
        try:
            context = self._load_dream_agent_context_from_db(
                db, workflow_run_id, actor
            )
            try:
                return StoryWorkspaceDreamAgentMessageService(
                    db,
                    thread_factory=self._dream_agent_thread_factory(),
                    db_factory=database.get_db,
                ).claim_message(
                    run_id=workflow_run_id,
                    thread_id=context.thread_id,
                    actor_id=actor["actor_id"],
                    context=context,
                    command=request,
                )
            except StoryWorkspaceDreamAgentMessageError as exc:
                raise ApiRouteError(exc.code, status_code=exc.status_code) from exc
        finally:
            db.close()

    async def _dispatch_dream_agent_message(self, pending: Any) -> None:
        """Run a previously committed claim using a fresh acknowledgement DB."""

        db = database.get_db()
        try:
            service = StoryWorkspaceDreamAgentMessageService(
                db,
                thread_factory=self._dream_agent_thread_factory(),
                db_factory=database.get_db,
            )
        finally:
            db.close()
        try:
            await service.dispatch(pending)
        except Exception:
            logger.exception(
                "Dream Agent dispatch task failed for message_id=%s",
                pending.message_id,
            )

    def _load_dream_agent_context_sync(
        self,
        workflow_run_id: str,
        actor: dict[str, str],
    ) -> StoryWorkspaceDreamRunContext:
        db = database.get_db()
        try:
            return self._load_dream_agent_context_from_db(db, workflow_run_id, actor)
        finally:
            db.close()

    def _load_dream_agent_context_from_db(
        self,
        db: Any,
        workflow_run_id: str,
        actor: dict[str, str],
    ) -> StoryWorkspaceDreamRunContext:
        """Derive immutable run/thread/Deck context; never trust an HTTP ID."""

        try:
            actor_id = int(actor["actor_id"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ApiRouteError("WORKFLOW_PERMISSION_DENIED", status_code=403) from exc
        # Keep the existing run/workspace authorization semantics, then prove
        # that the hidden thread is owned by this actor *and* locked to the
        # exact Deck frozen in the run binding.
        self._run_actor_context(db, workflow_run_id, actor_id)
        row = db.execute(
            """
            SELECT run.id AS workflow_run_id,
                   run.source_voice_thread_id AS thread_id,
                   binding.deck_id AS deck_id,
                   run.deck_plugin_id AS deck_plugin_id,
                   run.deck_plugin_version AS deck_plugin_version,
                   run.deck_plugin_binding_id AS deck_plugin_binding_id,
                   run.binding_revision AS binding_revision,
                   run.deck_runtime_snapshot_id AS deck_runtime_snapshot_id,
                   run.runtime_plugin_lock_id AS runtime_plugin_lock_id
            FROM workflow_runs AS run
            JOIN story_workspace_workspaces AS workspace
              ON workspace.id = run.workspace_id
            JOIN deck_plugin_bindings AS binding
             ON binding.deck_plugin_binding_id = run.deck_plugin_binding_id
             AND binding.binding_revision = run.binding_revision
             AND binding.deck_plugin_id = run.deck_plugin_id
             AND binding.deck_plugin_version = run.deck_plugin_version
             AND binding.workspace_id = run.workspace_id
            JOIN chat_thread AS thread
              ON thread.id = run.source_voice_thread_id
             AND thread.user_id = %s
             AND thread.deck_id = binding.deck_id
            WHERE run.id = %s
              AND run.created_by = %s
              AND workspace.owner_id = %s
            LIMIT 1
            """,
            (actor_id, workflow_run_id, str(actor_id), actor_id),
        ).fetchone()
        if row is None:
            raise ApiRouteError("WORKFLOW_PERMISSION_DENIED", status_code=404)
        try:
            return StoryWorkspaceDreamRunContext.model_validate(dict(row))
        except (TypeError, ValueError) as exc:
            raise ApiRouteError("OUTPUT_CONTRACT_INVALID", status_code=422) from exc

    async def list_dream_runs(
        self,
        *,
        actor: dict[str, str],
    ) -> Any:
        """Return the canonical actor-scoped Dream re-entry collection."""

        return await asyncio.to_thread(self._list_dream_runs_sync, actor)

    def _list_dream_runs_sync(
        self,
        actor: dict[str, str],
    ) -> Any:
        service = StoryWorkspaceDreamReentryService(
            db_factory=database.get_db,
            dream_files_loader=self._load_dream_reentry_stage_projection,
        )
        return service.list_dream_runs(actor=actor)

    def _load_dream_reentry_stage_projection(
        self,
        row: Any,
        actor: dict[str, str],
        db: Any,
    ) -> StoryWorkspaceDreamReentryStageProjection:
        """Preserve Dream files truth while retaining its reliable mtime for sort."""

        try:
            workflow_values = {
                field: row[field]
                for field in WorkflowRun.model_fields
                if field != "workflow_run_id"
            }
            workflow_values["workflow_run_id"] = row["run_id"]
            workflow_run = WorkflowRun.model_validate(workflow_values)
            thread_id = workflow_run.source_voice_thread_id
        except (KeyError, TypeError, ValueError) as exc:
            raise ApiRouteError("OUTPUT_CONTRACT_INVALID", status_code=422) from exc
        if not isinstance(thread_id, str) or not thread_id.strip():
            raise ApiRouteError("OUTPUT_CONTRACT_INVALID", status_code=422)
        try:
            projection = self._read_dream_files_for_authorized_run(
                workflow_run,
                thread_id=thread_id,
            )
        except StoryWorkspaceDreamFileError as exc:
            self._raise_dream_file_error(exc)
        stage_activity_at = self._dream_reentry_stage_activity_at(projection)
        return StoryWorkspaceDreamReentryStageProjection(
            stages=projection.stages,
            stage_activity_at=stage_activity_at,
        )

    @classmethod
    def _read_dream_files_for_authorized_run(
        cls,
        workflow_run: WorkflowRun,
        *,
        thread_id: str,
    ) -> Any:
        """Use the row already proven by re-entry SQL; do not reopen the database."""

        workspace = cls._thread_workspace(thread_id)
        reader = StoryWorkspaceDreamFileReader(workspace)
        reader_workspace = Path(reader.workspace_root)
        canonical_parent = workspace.parent
        if (
            reader_workspace != workspace
            or reader_workspace.parent != canonical_parent
            or reader_workspace.name != thread_id
            or not reader_workspace.is_relative_to(canonical_parent)
        ):
            raise ApiRouteError("WORKFLOW_PERMISSION_DENIED", status_code=403)
        return reader.read(workflow_run, thread_id=thread_id)

    @classmethod
    def _dream_reentry_stage_activity_at(cls, projection: Any) -> datetime | None:
        """Read only canonical, validated stage-file mtimes for re-entry order."""

        thread_id = getattr(projection, "thread_id", None)
        run_id = getattr(projection, "story_workspace_run_id", None)
        stages = getattr(projection, "stages", None)
        if not isinstance(thread_id, str) or not isinstance(run_id, str):
            raise ApiRouteError("OUTPUT_CONTRACT_INVALID", status_code=422)
        if not isinstance(stages, dict):
            raise ApiRouteError("OUTPUT_CONTRACT_INVALID", status_code=422)
        workspace = cls._thread_workspace(thread_id)
        candidates = [
            workspace / ".dream" / "runtime" / "runs" / run_id / "run.json",
            *[
                workspace / ".dream" / "runtime" / "runs" / run_id / "stages" / f"{stage.value}.json"
                for stage in stages
            ],
        ]
        newest: datetime | None = None
        for candidate in candidates:
            try:
                resolved = candidate.resolve(strict=True)
            except FileNotFoundError:
                continue
            except (OSError, RuntimeError) as exc:
                raise ApiRouteError("DECK_RUNTIME_CONFIG_UNAVAILABLE", status_code=503) from exc
            if not resolved.is_relative_to(workspace):
                raise ApiRouteError("WORKFLOW_PERMISSION_DENIED", status_code=403)
            try:
                metadata = resolved.stat(follow_symlinks=False)
            except OSError as exc:
                raise ApiRouteError("DECK_RUNTIME_CONFIG_UNAVAILABLE", status_code=503) from exc
            if not stat.S_ISREG(metadata.st_mode):
                raise ApiRouteError("WORKFLOW_PERMISSION_DENIED", status_code=403)
            observed = datetime.fromtimestamp(metadata.st_mtime, tz=UTC)
            newest = observed if newest is None else max(newest, observed)
        return newest

    def _get_dream_files_sync(
        self,
        workflow_run_id: str,
        actor: dict[str, str],
    ) -> Any:
        """Run the complete PostgreSQL/filesystem/flock chain in one worker."""

        db = database.get_db()
        try:
            return self._get_dream_files_from_db(db, workflow_run_id, actor)
        finally:
            db.close()

    def _get_episode_artifacts_sync(
        self,
        workflow_run_id: str,
        actor: dict[str, str],
    ) -> Any:
        """Keep authorization and pinned filesystem projection in one worker."""

        db = database.get_db()
        try:
            return self._get_episode_artifacts_from_db(
                db,
                workflow_run_id,
                actor,
            )
        finally:
            db.close()

    def _recover_episode_binding_sync(
        self,
        workflow_run_id: str,
        request: StoryWorkspaceEpisodeBindingRecoveryCommand,
        actor: dict[str, str],
    ) -> Any:
        db = database.get_db()
        try:
            # Missing authority is handled without a workspace probe. Existing
            # authority may resolve only its server-owned canonical binding.
            row = self._authorized_episode_row(db, workflow_run_id, actor)
            authority = self._episode_authority_from_source(
                row,
                workflow_run_id,
            )
            if authority is not None:
                current = self._get_episode_artifacts_from_db(
                    db,
                    workflow_run_id,
                    actor,
                )
                if getattr(current, "opaque_episode_id", None) is not None:
                    raise StoryWorkspaceEpisodeActionError(
                        "BINDING_REVISION_CONFLICT",
                        409,
                        latest_surface=current,
                    )
            context = self._load_dream_agent_context_from_db(
                db,
                workflow_run_id,
                actor,
            )
            try:
                return StoryWorkspaceEpisodeActionService(
                    db,
                    thread_factory=self._dream_agent_thread_factory(),
                    db_factory=database.get_db,
                ).recover_binding(
                    run_id=workflow_run_id,
                    actor_id=actor["actor_id"],
                    context=context,
                    command=request,
                )
            except StoryWorkspaceDreamAgentMessageError as exc:
                raise StoryWorkspaceEpisodeActionError(
                    exc.code,
                    exc.status_code,
                ) from exc
        except StoryWorkspaceEpisodeActionError:
            raise
        except ApiRouteError:
            raise
        except PostgresError as exc:
            raise ApiRouteError(
                "DECK_RUNTIME_CONFIG_UNAVAILABLE",
                status_code=503,
            ) from exc
        finally:
            db.close()

    def _continue_episode_action_sync(
        self,
        workflow_run_id: str,
        request: StoryWorkspaceEpisodeActionContinueCommand
        | StoryWorkspaceEpisodeActionContinueCommandV2,
        actor: dict[str, str],
        if_match: str,
    ) -> Any:
        db = database.get_db()
        try:
            authorized_row = self._authorized_episode_row(db, workflow_run_id, actor)
            authority = self._episode_authority_from_source(
                authorized_row,
                workflow_run_id,
            )
            if authority is None:
                raise StoryWorkspaceEpisodeActionError(
                    "WORKFLOW_PERMISSION_DENIED",
                    404,
                )
            context = self._load_dream_agent_context_from_db(
                db,
                workflow_run_id,
                actor,
            )
            surface = self._get_episode_artifacts_from_db(
                db,
                workflow_run_id,
                actor,
            )
            episode_uid = getattr(surface, "opaque_episode_id", None)
            if not isinstance(episode_uid, str):
                raise StoryWorkspaceEpisodeActionError(
                    "WORKFLOW_PERMISSION_DENIED",
                    404,
                )
            workspace = self._thread_workspace(context.thread_id)
            facts = StoryWorkspaceEpisodeWorkflowFactService(workspace).read(
                workflow_run_id,
                episode_uid,
            )
            try:
                service = StoryWorkspaceEpisodeActionService(
                    db,
                    thread_factory=self._dream_agent_thread_factory(),
                    db_factory=database.get_db,
                )
                if isinstance(request, StoryWorkspaceEpisodeActionContinueCommandV2):
                    projection = getattr(surface, "action_projection", None)
                    if projection is None:
                        raise StoryWorkspaceEpisodeActionError(
                            "BINDING_REVISION_CONFLICT",
                            409,
                            latest_surface=surface,
                        )
                    try:
                        selected = StoryWorkspaceTrustedEpisodeActionSelector.select(
                            run_id=workflow_run_id,
                            action_id=request.action_id,
                            projection=projection,
                        )
                    except StoryWorkspaceEpisodeActionSelectionError as exc:
                        raise StoryWorkspaceEpisodeActionError(
                            "BINDING_REVISION_CONFLICT",
                            409,
                            latest_surface=surface,
                        ) from exc
                    if selected.candidate_id is not None:
                        binding_service = StoryWorkspaceEpisodeBindingService(workspace)
                        canonical_story_slug = (
                            binding_service.read_canonical_project_story_slug(
                                authority.story_slug
                            )
                        )
                        binding_context = StoryWorkspaceEpisodeBindingContext(
                            workflow_run_id=workflow_run_id,
                            trusted_project_story_slug=canonical_story_slug,
                            locked_context_story_slug=authority.story_slug,
                            run_provenance_story_slug=authority.story_slug,
                            episode_uid=authority.episode_uid,
                        )
                        registry = binding_service.read_episode_registry(binding_context)
                        total_episodes = (
                            binding_service.read_canonical_project_total_episodes(
                                canonical_story_slug
                            )
                            or max(
                                item.episode_number for item in registry.episodes
                            )
                        )
                        updated_registry = binding_service.ensure_next_episode(
                            binding_context,
                            expected_revision=registry.revision,
                            total_episodes=total_episodes,
                        )
                        target_entry = next(
                            (
                                item
                                for item in updated_registry.episodes
                                if item.episode_code == selected.episode_code
                            ),
                            None,
                        )
                        if target_entry is None:
                            raise StoryWorkspaceEpisodeActionError(
                                "BINDING_REVISION_CONFLICT",
                                409,
                                latest_surface=surface,
                            )
                        next_authority = StoryWorkspaceEpisodeAuthority(
                            workflow_run_id=workflow_run_id,
                            episode_uid=target_entry.episode_uid,
                            story_slug=canonical_story_slug,
                            episode_code=target_entry.episode_code,
                        )
                        next_surface = StoryWorkspaceEpisodeArtifactService(
                            workspace
                        ).read_surface(
                            workflow_run_id,
                            episode_authority=next_authority,
                        ).model_copy(update={"etag": surface.etag})
                        next_facts = StoryWorkspaceEpisodeWorkflowFactService(
                            workspace
                        ).read(workflow_run_id, target_entry.episode_uid)
                        return service.continue_selected_episode(
                            run_id=workflow_run_id,
                            actor_id=actor["actor_id"],
                            context=context,
                            surface=next_surface,
                            action_facts=next_facts,
                            if_match=if_match,
                            command=request,
                            selected=replace(
                                selected,
                                target_episode_uid=target_entry.episode_uid,
                                candidate_id=None,
                            ),
                        )
                    return service.continue_selected_episode(
                        run_id=workflow_run_id,
                        actor_id=actor["actor_id"],
                        context=context,
                        surface=surface,
                        action_facts=facts,
                        if_match=if_match,
                        command=request,
                        selected=selected,
                    )
                return service.continue_episode(
                    run_id=workflow_run_id,
                    actor_id=actor["actor_id"],
                    context=context,
                    surface=surface,
                    action_facts=facts,
                    if_match=if_match,
                    command=request,
                )
            except StoryWorkspaceDreamAgentMessageError as exc:
                raise StoryWorkspaceEpisodeActionError(
                    exc.code,
                    exc.status_code,
                ) from exc
        except (StoryWorkspaceEpisodeActionError, ApiRouteError):
            raise
        except PostgresError as exc:
            raise ApiRouteError(
                "DECK_RUNTIME_CONFIG_UNAVAILABLE",
                status_code=503,
            ) from exc
        finally:
            db.close()

    @staticmethod
    def _authorized_episode_row(
        db: Any,
        workflow_run_id: str,
        actor: dict[str, str],
    ) -> Any:
        """Fail closed on every frozen run/Deck/thread provenance edge."""

        try:
            actor_id = int(actor["actor_id"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ApiRouteError("WORKFLOW_PERMISSION_DENIED", status_code=403) from exc
        if actor_id < 1:
            raise ApiRouteError("WORKFLOW_PERMISSION_DENIED", status_code=403)
        rows = StoryWorkspaceDreamReentryService._query_authorized_rows(db, actor_id)
        matches = [row for row in rows if str(row["run_id"]) == workflow_run_id]
        if len(matches) != 1:
            raise ApiRouteError("WORKFLOW_PERMISSION_DENIED", status_code=404)
        row = matches[0]
        if not StoryWorkspaceDreamReentryService._source_metadata_matches(
            row["source_metadata"],
            actor_id=actor_id,
            workspace_id=str(row["workspace_id"]),
            run_id=str(row["run_id"]),
            thread_id=str(row["thread_id"]),
            deck_id=str(row["deck_id"]),
            deck_plugin_id=str(row["deck_plugin_id"]),
            deck_plugin_version=str(row["deck_plugin_version"]),
            binding_id=str(row["binding_id"]),
            binding_revision=int(row["binding_revision"]),
            runtime_snapshot_id=str(row["deck_runtime_snapshot_id"]),
            runtime_lock_id=str(row["runtime_plugin_lock_id"]),
        ):
            raise ApiRouteError("WORKFLOW_PERMISSION_DENIED", status_code=404)
        return row

    @staticmethod
    def _episode_authority_from_source(
        row: Any,
        workflow_run_id: str,
    ) -> StoryWorkspaceEpisodeAuthority | None:
        try:
            metadata = (
                json.loads(row["source_metadata"])
                if isinstance(row["source_metadata"], str)
                else None
            )
        except (TypeError, ValueError):
            return None
        if not isinstance(metadata, dict):
            return None
        return StoryWorkspaceEpisodeAuthority.parse(
            metadata.get("story_workspace_episode_identity"),
            expected_run_id=workflow_run_id,
        )

    def _get_episode_artifacts_from_db(
        self,
        db: Any,
        workflow_run_id: str,
        actor: dict[str, str],
    ) -> Any:
        """Authorize all relational facts before probing the thread workspace."""

        try:
            row = self._authorized_episode_row(
                db,
                workflow_run_id,
                actor,
            )
            authority = self._episode_authority_from_source(
                row,
                workflow_run_id,
            )
            if authority is None:
                return StoryWorkspaceEpisodeArtifactService.unbound_surface(
                    workflow_run_id
                )
            thread_id = str(row["thread_id"])
            try:
                workspace = self._thread_workspace(thread_id)
            except ApiRouteError as exc:
                raise ApiRouteError("WORKFLOW_PERMISSION_DENIED", status_code=404)
            binding_service = StoryWorkspaceEpisodeBindingService(workspace)
            canonical_story_slug = (
                binding_service.read_canonical_project_story_slug(
                    authority.story_slug
                )
            )
            binding_context = StoryWorkspaceEpisodeBindingContext(
                workflow_run_id=workflow_run_id,
                trusted_project_story_slug=canonical_story_slug,
                locked_context_story_slug=authority.story_slug,
                run_provenance_story_slug=authority.story_slug,
                episode_uid=authority.episode_uid,
            )
            binding_service.resolve_or_repair_binding(binding_context)
            surface = StoryWorkspaceEpisodeArtifactService(workspace).read_surface(
                workflow_run_id,
                episode_authority=authority,
            )
            episode_uid = surface.opaque_episode_id
            manifest_revision = surface.manifest_revision
            if episode_uid is None or manifest_revision is None:
                return surface
            facts = StoryWorkspaceEpisodeWorkflowFactService(workspace).read(
                workflow_run_id,
                episode_uid,
            )
            resolver = StoryWorkspaceEpisodeNextActionResolver()
            workflow = resolver.project(surface, facts)
            registry = binding_service.read_episode_registry(binding_context)
            total_episodes = (
                binding_service.read_canonical_project_total_episodes(
                    canonical_story_slug
                )
                or max(item.episode_number for item in registry.episodes)
            )
            action_projection = StoryWorkspaceEpisodeActionProjectionService.project(
                surface=surface,
                facts=facts,
                registry=registry,
                total_episodes=total_episodes,
            )
            legacy_etag = resolver.surface_etag(manifest_revision, workflow)
            action_etag = StoryWorkspaceEpisodeActionProjectionService.surface_etag(
                manifest_revision,
                action_projection,
            )
            aggregate_etag = "sha256:" + hashlib.sha256(
                json.dumps(
                    [legacy_etag, action_etag],
                    ensure_ascii=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
            return surface.model_copy(
                update={
                    "workflow": workflow,
                    "action_projection": action_projection,
                    "etag": aggregate_etag,
                }
            )
        except ApiRouteError:
            raise
        except StoryWorkspaceEpisodeArtifactPathError as exc:
            raise ApiRouteError("WORKFLOW_PERMISSION_DENIED", status_code=404) from exc
        except StoryWorkspaceEpisodeArtifactContractError as exc:
            raise ApiRouteError("OUTPUT_CONTRACT_INVALID", status_code=422) from exc
        except StoryWorkspaceEpisodeArtifactError as exc:
            raise ApiRouteError(
                "DECK_RUNTIME_CONFIG_UNAVAILABLE",
                status_code=503,
            ) from exc
        except (StoryWorkspaceEpisodeBindingError, StoryWorkspaceEpisodeWorkflowFactError) as exc:
            raise ApiRouteError("WORKFLOW_PERMISSION_DENIED", status_code=404) from exc
        except PostgresError as exc:
            raise ApiRouteError(
                "DECK_RUNTIME_CONFIG_UNAVAILABLE",
                status_code=503,
            ) from exc

    def _get_dream_files_from_db(
        self,
        db: Any,
        workflow_run_id: str,
        actor: dict[str, str],
        *,
        include_confirmation: bool = True,
    ) -> Any:
        """Reuse one already-authorized PostgreSQL connection for a Dream projection."""

        try:
            try:
                actor_id = int(actor["actor_id"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ApiRouteError(
                    "WORKFLOW_PERMISSION_DENIED",
                    status_code=403,
                ) from exc
            actor_context = self._run_actor_context(db, workflow_run_id, actor_id)
            workflow_run = WorkflowRunService(
                db,
                token_secret=_token_secret(),
            ).read_run(workflow_run_id, actor_context)
            thread_id = workflow_run.source_voice_thread_id
            if not isinstance(thread_id, str) or not thread_id.strip():
                raise ApiRouteError("OUTPUT_CONTRACT_INVALID", status_code=422)
            if include_confirmation:
                thread = database.get_chat_thread(thread_id, actor_id)
                thread_id_value = str(thread.get("id")) if thread else None
            else:
                thread = db.execute(
                    "SELECT id FROM chat_thread WHERE id = %s AND user_id = %s",
                    (thread_id, actor_id),
                ).fetchone()
                thread_id_value = str(thread["id"]) if thread else None
            if thread_id_value != thread_id:
                raise ApiRouteError("WORKFLOW_PERMISSION_DENIED", status_code=404)
            workspace = self._thread_workspace(thread_id)
            reader = StoryWorkspaceDreamFileReader(workspace)
            reader_workspace = Path(reader.workspace_root)
            canonical_parent = workspace.parent
            if (
                reader_workspace != workspace
                or reader_workspace.parent != canonical_parent
                or reader_workspace.name != thread_id
                or not reader_workspace.is_relative_to(canonical_parent)
            ):
                raise ApiRouteError("WORKFLOW_PERMISSION_DENIED", status_code=403)
            projection = reader.read(workflow_run, thread_id=thread_id)
            if not include_confirmation:
                return projection
            confirmation_accepted, confirmation_dispatched = (
                story_workspace_read_dream_confirmation_fact(
                    db,
                    actor_id=str(actor_id),
                    thread_id=thread_id,
                    run_id=workflow_run_id,
                )
            )
            return projection.model_copy(update={
                "confirmation_accepted": confirmation_accepted,
                "confirmation_dispatched": confirmation_dispatched,
                "can_confirm": projection.can_confirm and not confirmation_accepted,
            })
        except WorkflowRunError as exc:
            self._raise_run_error(exc)
        except ApiRouteError:
            raise
        except StoryWorkspaceDreamFileError as exc:
            self._raise_dream_file_error(exc)
        except Exception as exc:
            raise ApiRouteError(
                "DECK_RUNTIME_CONFIG_UNAVAILABLE",
                status_code=503,
            ) from exc

    async def submit_dream_confirmation(
        self,
        workflow_run_id: str,
        request: Any,
        *,
        actor: dict[str, str],
    ) -> Any:
        """Persist in a worker, then queue the same-thread turn on this loop."""

        persisted = await asyncio.to_thread(
            self._submit_dream_confirmation_sync,
            workflow_run_id,
            request,
            actor,
        )
        accepted = persisted.accepted
        dispatch = persisted.dispatch
        if dispatch is None:
            return accepted

        try:
            self._dream_confirmation_coordinator.schedule(dispatch)
        except Exception:
            # The committed hidden turn remains pending. The lifecycle scan
            # will pick it up without asking the user to submit again.
            logger.exception(
                "Dream confirmation scheduling deferred for run_id=%s "
                "message_id=%s",
                workflow_run_id,
                dispatch.message_id,
            )
        # Scheduled is not consumed. Only the coordinator writes the durable
        # dispatched acknowledgement after the same Chat Agent turn completes.
        return accepted.model_copy(update={"dispatched": False})

    def _submit_dream_confirmation_sync(
        self,
        workflow_run_id: str,
        request: Any,
        actor: dict[str, str],
    ) -> StoryWorkspacePersistedDreamConfirmation:
        """Run the complete scoped DB/file/INSERT chain in one worker."""

        try:
            db = database.get_db()
            try:
                try:
                    actor_id = int(actor["actor_id"])
                except (KeyError, TypeError, ValueError) as exc:
                    raise ApiRouteError(
                        "WORKFLOW_PERMISSION_DENIED",
                        status_code=403,
                    ) from exc
                actor_context = self._run_actor_context(
                    db,
                    workflow_run_id,
                    actor_id,
                )
                workflow_run = WorkflowRunService(
                    db,
                    token_secret=_token_secret(),
                ).read_run(workflow_run_id, actor_context)
                thread_id = workflow_run.source_voice_thread_id
                if not isinstance(thread_id, str) or not thread_id.strip():
                    raise ApiRouteError("OUTPUT_CONTRACT_INVALID", status_code=422)

                workspace = self._thread_workspace(thread_id)
                reader = StoryWorkspaceDreamFileReader(workspace)
                reader_workspace = Path(reader.workspace_root)
                canonical_parent = workspace.parent
                if (
                    reader_workspace != workspace
                    or reader_workspace.parent != canonical_parent
                    or reader_workspace.name != thread_id
                    or not reader_workspace.is_relative_to(canonical_parent)
                ):
                    raise ApiRouteError(
                        "WORKFLOW_PERMISSION_DENIED",
                        status_code=403,
                    )

                def scoped_run_reader(requested_run_id: str):
                    if requested_run_id != workflow_run_id:
                        raise StoryWorkspaceDreamConfirmationError(
                            "CONFIG_VERSION_DRIFT", 409
                        )
                    return workflow_run

                service = StoryWorkspaceDreamConfirmationService(
                    db,
                    run_reader=scoped_run_reader,
                    projection_reader=lambda run, authoritative_thread_id: reader.read(
                        run,
                        thread_id=authoritative_thread_id,
                    ),
                )
                return service.submit_confirmation(
                    workflow_run_id,
                    request,
                    actor_id=str(actor_id),
                )
            finally:
                db.close()
        except StoryWorkspaceDreamConfirmationError as exc:
            raise ApiRouteError(exc.code, status_code=exc.status_code) from exc
        except WorkflowRunError as exc:
            self._raise_run_error(exc)
        except ApiRouteError:
            raise
        except StoryWorkspaceDreamFileError as exc:
            self._raise_dream_file_error(exc)
        except Exception as exc:
            raise ApiRouteError(
                "DECK_RUNTIME_CONFIG_UNAVAILABLE",
                status_code=503,
            ) from exc

    async def retry_run(
        self,
        workflow_run_id: str,
        request: Any,
        *,
        actor: dict[str, str],
    ) -> Any:
        db = database.get_db()
        try:
            return await WorkflowRunService(db, token_secret=_token_secret()).retry_run(
                workflow_run_id,
                self._actor(actor),
                preflight_id=request.workflow_preflight_id,
                preflight_token=request.preflight_token,
                idempotency_key=request.idempotency_key,
            )
        except WorkflowRunError as exc:
            self._raise_run_error(exc)
        finally:
            db.close()

    async def cancel_run(
        self,
        workflow_run_id: str,
        request: Any,
        *,
        actor: dict[str, str],
    ) -> Any:
        db = database.get_db()
        try:
            return await WorkflowRunService(db, token_secret=_token_secret()).transition_run(
                workflow_run_id,
                RunStatus.CANCELLED,
                self._actor(actor),
                reason_code=f"user_cancelled:{request.reason}",
            )
        except WorkflowRunError as exc:
            self._raise_run_error(exc)
        finally:
            db.close()

    async def submit_guidance(
        self,
        workflow_run_id: str,
        request: Any,
        *,
        actor: dict[str, str],
    ) -> Any:
        """Persist and dispatch one guidance command for a guidable run.

        Persistence rides ``chat_message.metadata`` (DEC-032, zero DDL); the
        default dispatcher hands the guidance to the runner as a new user turn
        on the chat thread that initiated the run (review note R5).
        """
        db = database.get_db()
        try:
            actor_context = self._actor(actor)
            run_service = WorkflowRunService(db, token_secret=_token_secret())
            service = StoryWorkspaceGuidanceService(
                db,
                run_reader=lambda run_id: run_service.read_run(run_id, actor_context),
                dispatcher=build_thread_turn_dispatcher(),
            )
            return service.submit_guidance(
                workflow_run_id,
                request,
                actor_id=actor["actor_id"],
            )
        except StoryWorkspaceGuidanceError as exc:
            raise ApiRouteError(exc.code, status_code=exc.status_code) from exc
        except WorkflowRunError as exc:
            self._raise_run_error(exc)
        finally:
            db.close()


_GATEWAY = StoryWorkflowApplicationGateway()


def get_story_workflow_application_gateway() -> StoryWorkflowApplicationGateway:
    return _GATEWAY


def story_workspace_get_dream_confirmation_coordinator(
) -> StoryWorkspaceDreamConfirmationCoordinator:
    """Return the process singleton managed by the FastAPI lifecycle."""

    return _DREAM_CONFIRMATION_COORDINATOR
