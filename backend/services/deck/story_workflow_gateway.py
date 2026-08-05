"""Application wiring for Dream workflow preflight and run APIs."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import importlib.util
import json
import logging
import os
from pathlib import Path
import sqlite3
import stat
import sys
from typing import Any
import uuid

import database

try:
    from models.deck_plugin import DeckPluginManifestV1, DeckRuntimePluginLock
    from models.workflow_run import AuthenticatedActorContext, RunStatus
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
except ModuleNotFoundError:  # Support package imports from repository root.
    from backend.models.deck_plugin import DeckPluginManifestV1, DeckRuntimePluginLock
    from backend.models.workflow_run import AuthenticatedActorContext, RunStatus
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

    @staticmethod
    def _actor(actor: dict[str, str]) -> AuthenticatedActorContext:
        return AuthenticatedActorContext(
            workspace_id=actor["workspace_id"],
            actor_id=actor["actor_id"],
        )

    @staticmethod
    def _run_actor_context(
        db: sqlite3.Connection,
        workflow_run_id: str,
        actor_id: int,
    ) -> AuthenticatedActorContext:
        """Resolve the run-owned workspace without selecting an actor default."""

        owns_workspace = db.execute(
            "SELECT id FROM story_workspace_workspaces "
            "WHERE owner_id = ? LIMIT 1",
            (actor_id,),
        ).fetchone()
        if owns_workspace is None:
            raise ApiRouteError("WORKFLOW_PERMISSION_DENIED", status_code=403)
        row = db.execute(
            "SELECT run.workspace_id FROM workflow_runs AS run "
            "JOIN story_workspace_workspaces AS workspace "
            "ON workspace.id = run.workspace_id "
            "WHERE run.id = ? AND run.created_by = ? AND workspace.owner_id = ?",
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
        db: sqlite3.Connection,
        workspace_id: str,
        deck_plugin_id: str,
    ) -> Scope:
        row = db.execute(
            """
            SELECT scope_type, scope_id FROM deck_plugin_installations
            WHERE scope_type = 'workspace' AND scope_id = ? AND deck_plugin_id = ?
              AND status = 'ready'
            """,
            (workspace_id, deck_plugin_id),
        ).fetchone()
        if row is None:
            row = db.execute(
                """
                SELECT scope_type, scope_id FROM deck_plugin_installations
                WHERE scope_type = 'instance' AND deck_plugin_id = ? AND status = 'ready'
                ORDER BY updated_at DESC LIMIT 1
                """,
                (deck_plugin_id,),
            ).fetchone()
        if row is None:
            raise PreflightCheckError("DECK_PLUGIN_UNAVAILABLE")
        return Scope(scope_type=row["scope_type"], scope_id=row["scope_id"])

    def _preflight_service(
        self,
        db: sqlite3.Connection,
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
                  ON workspace.id = ? AND workspace.owner_id = deck.owner_id
                WHERE deck.id = ? AND deck.owner_id = ? AND deck.enabled = 1
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
                WHERE binding.deck_id = ? AND binding.binding_revision = ?
                  AND binding.status = 'active' AND binding.workspace_id = ?
                  AND binding.creator_id = ?
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
                WHERE deck_plugin_id = ? AND status = 'ready'
                  AND ((scope_type = 'workspace' AND scope_id = ?) OR scope_type = 'instance')
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
                "SELECT manifest_json FROM deck_plugin_releases WHERE deck_plugin_id = ? "
                "AND deck_plugin_version = ?",
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
                WHERE deck_id = ? AND workspace_id = ? AND creator_id = ? AND status = 'active'
                """,
                (deck_id, workspace_id, actor_id),
            ).fetchone()
            deck = db.execute(
                "SELECT id, name, name_zh, name_en, description, description_zh, description_en "
                "FROM decks WHERE id = ? AND owner_id = ?",
                (deck_id, actor_id),
            ).fetchone()
            voices = db.execute(
                "SELECT id, name, name_zh, name_en, system_prompt FROM voices "
                "WHERE deck_id = ? AND enabled = 1 ORDER BY order_index, id",
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
                WHERE deck_id = ? AND binding_revision = ?
                  AND deck_runtime_profile_id = ? AND config_hash = ?
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
            with db:
                db.execute(
                    """
                    INSERT INTO deck_runtime_snapshots (
                        deck_runtime_snapshot_id, deck_id, deck_plugin_binding_id,
                        binding_revision, deck_runtime_profile_id, snapshot_contract,
                        config_hash, config_json, sanitized_summary_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            return {
                "deck_runtime_snapshot_id": snapshot_id,
                "sanitized_summary_hash": summary_hash,
                "reused": False,
            }

        def materialization_reader(runtime_lock_id: str) -> dict[str, Any]:
            lock_row = db.execute(
                "SELECT lock_json FROM deck_runtime_plugin_locks WHERE id = ?",
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
                    WHERE claude_code_plugin_id = ? AND resolved_version = ?
                      AND artifact_digest = ?
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

    async def list_dream_runs(self, *, actor: dict[str, str]) -> Any:
        """Return the canonical actor-scoped Dream re-entry collection."""

        return await asyncio.to_thread(self._list_dream_runs_sync, actor)

    def _list_dream_runs_sync(self, actor: dict[str, str]) -> Any:
        service = StoryWorkspaceDreamReentryService(
            db_factory=database.get_db,
            dream_files_loader=self._load_dream_reentry_stage_projection,
        )
        return service.list_dream_runs(actor=actor)

    def _load_dream_reentry_stage_projection(
        self,
        workflow_run_id: str,
        actor: dict[str, str],
    ) -> StoryWorkspaceDreamReentryStageProjection:
        """Preserve Dream files truth while retaining its reliable mtime for sort."""

        projection = self._get_dream_files_sync(workflow_run_id, actor)
        stage_activity_at = self._dream_reentry_stage_activity_at(projection)
        return StoryWorkspaceDreamReentryStageProjection(
            stages=projection.stages,
            stage_activity_at=stage_activity_at,
        )

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
        """Run the complete SQLite/filesystem/flock chain in one worker."""

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
                thread = database.get_chat_thread(thread_id, actor_id)
                if thread is None or str(thread.get("id")) != thread_id:
                    raise ApiRouteError(
                        "WORKFLOW_PERMISSION_DENIED",
                        status_code=404,
                    )
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
                projection = reader.read(
                    workflow_run,
                    thread_id=thread_id,
                )
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
                    "can_confirm": (
                        projection.can_confirm and not confirmation_accepted
                    ),
                })
            finally:
                db.close()
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
