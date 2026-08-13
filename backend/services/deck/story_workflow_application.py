"""Focused application services for Dream workflow business APIs."""

from __future__ import annotations

from psycopg import Error as PostgresError

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import importlib.util
import json
import logging
from pathlib import Path
import stat
import sys
from typing import Any

import database

try:
    from models.workflow_run import AuthenticatedActorContext, RunStatus, WorkflowRun
    from story_workspace.contracts import (
        StoryWorkspaceDreamAgentActivityResponse,
        StoryWorkspaceDreamRunContext,
        StoryWorkspaceStoryIndexProjection,
        StoryWorkspaceStoryIndexReconcileCommand,
    )
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
        StoryWorkspaceDreamConfirmationDispatch,
        StoryWorkspaceDreamConfirmationCoordinator,
        StoryWorkspaceDreamConfirmationError,
        StoryWorkspaceDreamConfirmationService,
        story_workspace_read_dream_confirmation_fact,
    )
    from services.story_workspace.dream_workflow_lifecycle_service import (
        StoryWorkspaceDreamWorkflowLifecycleService,
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
    from services.story_workspace.episode_binding_service import (
        StoryWorkspaceEpisodeBindingContext,
        StoryWorkspaceEpisodeBindingError,
        StoryWorkspaceEpisodeBindingService,
    )
    from services.story_workspace.dream_thread_binding import (
        DreamRunBindingResolver,
        DreamThreadBindingConflict,
    )
    from services.story_workspace.preflight_builder import (
        StoryWorkspacePreflightServiceBuilder,
    )
    from services.story_workspace.workflow_security import (
        story_workspace_workflow_token_secret,
    )
    from services.story_workspace.artifact_story_index_projector import (
        ArtifactStoryProjectionError,
    )
    from services.story_workspace.artifact_story_index_repository import (
        ArtifactStoryIndexRepositoryError,
    )
    from services.story_workspace.artifact_story_index_service import (
        ArtifactStoryIndexObservation,
        ArtifactStoryIndexService,
        ArtifactStoryIndexSnapshot,
    )
except ModuleNotFoundError:  # Support package imports from repository root.
    from backend.models.workflow_run import AuthenticatedActorContext, RunStatus, WorkflowRun
    from backend.story_workspace.contracts import (
        StoryWorkspaceDreamAgentActivityResponse,
        StoryWorkspaceDreamRunContext,
        StoryWorkspaceStoryIndexProjection,
        StoryWorkspaceStoryIndexReconcileCommand,
    )
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
        StoryWorkspaceDreamConfirmationDispatch,
        StoryWorkspaceDreamConfirmationCoordinator,
        StoryWorkspaceDreamConfirmationError,
        StoryWorkspaceDreamConfirmationService,
        story_workspace_read_dream_confirmation_fact,
    )
    from backend.services.story_workspace.dream_workflow_lifecycle_service import (
        StoryWorkspaceDreamWorkflowLifecycleService,
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
    from backend.services.story_workspace.episode_binding_service import (
        StoryWorkspaceEpisodeBindingContext,
        StoryWorkspaceEpisodeBindingError,
        StoryWorkspaceEpisodeBindingService,
    )
    from backend.services.story_workspace.dream_thread_binding import (
        DreamRunBindingResolver,
        DreamThreadBindingConflict,
    )
    from backend.services.story_workspace.preflight_builder import (
        StoryWorkspacePreflightServiceBuilder,
    )
    from backend.services.story_workspace.workflow_security import (
        story_workspace_workflow_token_secret,
    )
    from backend.services.story_workspace.artifact_story_index_projector import (
        ArtifactStoryProjectionError,
    )
    from backend.services.story_workspace.artifact_story_index_repository import (
        ArtifactStoryIndexRepositoryError,
    )
    from backend.services.story_workspace.artifact_story_index_service import (
        ArtifactStoryIndexObservation,
        ArtifactStoryIndexService,
        ArtifactStoryIndexSnapshot,
    )


_DREAM_OUTPUT_REQUIRED_STATUSES = frozenset(
    {
        RunStatus.OUTPUT_VALIDATING,
        RunStatus.PENDING_REVIEW,
        RunStatus.CONFIRMED,
        RunStatus.REJECTED,
        RunStatus.COMPLETED,
    }
)
_STORY_INDEX_ERROR_STATUSES = {
    "artifact_missing": 404,
    "story_index_revision_conflict": 409,
    "story_index_conflict": 409,
    "story_index_invalid_artifact": 422,
    "story_index_schema_unavailable": 503,
    "story_index_database_unavailable": 503,
    "story_index_write_failed": 503,
}
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StoryWorkspaceDreamReentryStageProjection:
    """Validated Dream files plus the newest canonical stage file timestamp."""

    stages: Any
    stage_activity_at: datetime | None


@dataclass(frozen=True)
class _AuthorizedStoryIndexContext:
    """Internal authorization facts; never serialize thread or workspace paths."""

    workflow_run_row: Any
    actor_id: int
    thread_id: str
    thread_workspace: Path
    episode_authority: StoryWorkspaceEpisodeAuthority
    refreshed_surface: Any


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


def _dream_confirmation_actor_context(
    db: Any,
    dispatch: StoryWorkspaceDreamConfirmationDispatch,
) -> tuple[str, AuthenticatedActorContext]:
    run_id = dispatch.metadata.get("story_workspace_run_id")
    if not isinstance(run_id, str) or not run_id:
        raise PermissionError("Dream confirmation Run scope is unavailable")
    row = db.execute(
        "SELECT workspace_id, source_voice_thread_id FROM workflow_runs "
        "WHERE id = %s AND created_by = %s",
        (run_id, dispatch.actor_id),
    ).fetchone()
    if db.in_transaction:
        db.rollback()
    if row is None or row["source_voice_thread_id"] != dispatch.thread_id:
        raise PermissionError("Dream confirmation actor/thread scope mismatch")
    return run_id, AuthenticatedActorContext(
        actor_id=dispatch.actor_id,
        workspace_id=str(row["workspace_id"]),
    )


def _prepare_dream_confirmation_before_dispatch(
    db: Any,
    dispatch: StoryWorkspaceDreamConfirmationDispatch,
) -> None:
    run_id, actor_context = _dream_confirmation_actor_context(db, dispatch)
    lifecycle = StoryWorkspaceDreamWorkflowLifecycleService(
        db,
        token_secret=story_workspace_workflow_token_secret(),
    )
    # The confirmation row can only be persisted after the server validates all
    # required Dream stage revisions. That durable row therefore proves both
    # output readiness and the user's review acceptance, including recovery of
    # the historical `running + dispatching` split state.
    asyncio.run(
        lifecycle.record_output_ready(
            run_id,
            actor_context,
            normalized_result_ready=True,
        )
    )
    asyncio.run(
        lifecycle.record_confirmation_accepted(
            run_id,
            actor_context,
            review_items_approved=True,
        )
    )


def _advance_dream_post_confirmation_before_ack(
    db: Any,
    dispatch: StoryWorkspaceDreamConfirmationDispatch,
) -> None:
    run_id, actor_context = _dream_confirmation_actor_context(db, dispatch)
    asyncio.run(
        StoryWorkspaceDreamWorkflowLifecycleService(
            db,
            token_secret=story_workspace_workflow_token_secret(),
        ).record_post_confirmation_dispatched(
            run_id,
            actor_context,
        )
    )


_DREAM_CONFIRMATION_COORDINATOR = StoryWorkspaceDreamConfirmationCoordinator(
    database.get_db,
    before_dispatch=_prepare_dream_confirmation_before_dispatch,
    before_dispatched_ack=_advance_dream_post_confirmation_before_ack,
)


class _StoryWorkspaceApplicationSupport:
    """Shared authorization/error helpers; exposes no application endpoint."""

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
    def _dream_agent_thread_factory() -> Any | None:
        try:
            from agent_factory import claude_agent_thread_factory

            return claude_agent_thread_factory
        except Exception:
            # A cold/restarted process still has a valid persistent snapshot;
            # it simply has no live stream to attach.
            return None

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

    @staticmethod
    def _episode_authority_from_registry(
        source_authority: StoryWorkspaceEpisodeAuthority,
        registry: Any,
    ) -> StoryWorkspaceEpisodeAuthority:
        """Derive the active Episode while keeping launch authority immutable."""

        if (
            getattr(registry, "workflow_run_id", None)
            != source_authority.workflow_run_id
            or getattr(registry, "story_slug", None) != source_authority.story_slug
        ):
            raise StoryWorkspaceEpisodeBindingError(
                "Episode registry does not match launch authority"
            )
        entries = list(getattr(registry, "episodes", ()))
        if not any(
            getattr(item, "episode_uid", None) == source_authority.episode_uid
            for item in entries
        ):
            raise StoryWorkspaceEpisodeBindingError(
                "launch Episode is absent from the registry"
            )
        active_uid = getattr(registry, "active_episode_uid", None)
        active = next(
            (
                item
                for item in entries
                if getattr(item, "episode_uid", None) == active_uid
            ),
            None,
        )
        if active is None:
            raise StoryWorkspaceEpisodeBindingError(
                "active Episode is absent from the registry"
            )
        return StoryWorkspaceEpisodeAuthority(
            workflow_run_id=source_authority.workflow_run_id,
            episode_uid=active.episode_uid,
            story_slug=source_authority.story_slug,
            episode_code=active.episode_code,
        )



class StoryWorkflowRunApplicationService(_StoryWorkspaceApplicationSupport):
    """Preflight and WorkflowRun command/query application service."""

    @staticmethod
    def _preflight_service(
        db: Any,
        actor: dict[str, str],
    ) -> PreflightService:
        return StoryWorkspacePreflightServiceBuilder(
            db,
            actor,
            token_secret=story_workspace_workflow_token_secret(),
        ).build()

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
            service = WorkflowRunService(db, token_secret=story_workspace_workflow_token_secret())
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
            return WorkflowRunService(db, token_secret=story_workspace_workflow_token_secret()).read_run(
                workflow_run_id,
                self._actor(actor),
            )
        except WorkflowRunError as exc:
            self._raise_run_error(exc)
        finally:
            db.close()


    async def retry_run(
        self,
        workflow_run_id: str,
        request: Any,
        *,
        actor: dict[str, str],
    ) -> Any:
        db = database.get_db()
        try:
            return await WorkflowRunService(db, token_secret=story_workspace_workflow_token_secret()).retry_run(
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
            return await WorkflowRunService(db, token_secret=story_workspace_workflow_token_secret()).transition_run(
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
            run_service = WorkflowRunService(db, token_secret=story_workspace_workflow_token_secret())
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



class DreamArtifactApplicationService(_StoryWorkspaceApplicationSupport):
    """Authorized Dream files, Artifact, re-entry and Story Index service."""

    async def get_dream_files(
        self,
        workflow_run_id: str,
        *,
        actor: dict[str, str],
    ) -> Any:
        """Project Dream files without blocking the application event loop."""

        projection = await asyncio.to_thread(
            self._get_dream_files_sync,
            workflow_run_id,
            actor,
        )
        return self._attach_dream_agent_activity(
            projection,
            workflow_run_id=workflow_run_id,
            actor_id=str(actor["actor_id"]),
        )

    def _attach_dream_agent_activity(
        self,
        projection: Any,
        *,
        workflow_run_id: str,
        actor_id: str,
    ) -> Any:
        """Add a safe display hint without making Observer availability fatal.

        Authorization and thread ownership have already been established by the
        Dream-files projection.  The optional process-local hint cannot change
        workflow fields, confirmation eligibility, Chat state, or HTTP success.
        """

        try:
            factory = self._dream_agent_thread_factory()
            snapshot = (
                factory.dream_workflow_activity_projection()
                if factory is not None
                else []
            )
            thread_id = str(getattr(projection, "thread_id", "") or "")
            candidates = [
                item
                for item in snapshot
                if str(getattr(item, "run_id", "") or "") == workflow_run_id
                and str(getattr(item, "thread_id", "") or "") == thread_id
                and str(getattr(item, "actor_id", "") or "") == actor_id
            ]
            if not candidates:
                return projection
            latest = max(
                candidates,
                key=lambda item: (
                    int(getattr(item, "generation", -1)),
                    int(getattr(item, "sequence", -1)),
                ),
            )
            activity = StoryWorkspaceDreamAgentActivityResponse(
                activity=str(getattr(latest, "activity", "") or ""),
                sequence=int(getattr(latest, "sequence", -1)),
                terminal_outcome=getattr(latest, "terminal_outcome", None),
                needs_reconcile=bool(getattr(latest, "needs_reconcile", False)),
                operation_scope=getattr(latest, "operation_scope", None),
                operation_state=getattr(latest, "operation_state", None),
                operation_id=getattr(latest, "operation_id", None),
            )
            return projection.model_copy(update={"agent_activity": activity})
        except Exception:
            logger.exception(
                "Dream Observer projection unavailable for run_id=%s",
                workflow_run_id,
            )
            return projection

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

    async def get_story_index(
        self,
        workflow_run_id: str,
        *,
        actor: dict[str, str],
    ) -> StoryWorkspaceStoryIndexProjection:
        """Read the independent Artifact/PostgreSQL revision comparison."""

        return await asyncio.to_thread(
            self._get_story_index_sync,
            workflow_run_id,
            actor,
        )

    async def reconcile_story_index(
        self,
        workflow_run_id: str,
        request: StoryWorkspaceStoryIndexReconcileCommand,
        *,
        actor: dict[str, str],
        if_match: str,
    ) -> StoryWorkspaceStoryIndexProjection:
        """Synchronously retry one authorized, revision-guarded materialization."""

        return await asyncio.to_thread(
            self._reconcile_story_index_sync,
            workflow_run_id,
            request,
            actor,
            if_match,
        )


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

    @staticmethod
    def _story_index_error_status(code: str) -> int:
        return _STORY_INDEX_ERROR_STATUSES.get(code, 503)

    @classmethod
    def _raise_story_index_error(cls, code: str) -> None:
        safe_code = (
            code
            if code in _STORY_INDEX_ERROR_STATUSES
            else "story_index_database_unavailable"
        )
        raise ApiRouteError(
            safe_code,
            status_code=cls._story_index_error_status(safe_code),
        )

    @classmethod
    def _read_story_index_surface(
        cls,
        workspace: Path,
        workflow_run_id: str,
        authority: StoryWorkspaceEpisodeAuthority,
    ) -> Any:
        """Read one authorized surface through the fixed Story-index boundary."""

        try:
            return StoryWorkspaceEpisodeArtifactService(workspace).read_surface(
                workflow_run_id,
                episode_authority=authority,
            )
        except StoryWorkspaceEpisodeArtifactPathError as exc:
            raise ApiRouteError("artifact_missing", status_code=404) from exc
        except StoryWorkspaceEpisodeArtifactError as exc:
            raise ApiRouteError(
                "story_index_invalid_artifact",
                status_code=422,
            ) from exc

    def _authorized_story_index_context(
        self,
        db: Any,
        workflow_run_id: str,
        actor: dict[str, str],
    ) -> _AuthorizedStoryIndexContext:
        """Finish relational authorization before the first filesystem probe."""

        row = self._authorized_episode_row(db, workflow_run_id, actor)
        source_authority = self._episode_authority_from_source(row, workflow_run_id)
        if source_authority is None:
            self._raise_story_index_error("artifact_missing")
        try:
            actor_id = int(actor["actor_id"])
            thread_id = str(row["thread_id"])
            workspace = self._thread_workspace(thread_id)
        except ApiRouteError as exc:
            if exc.status_code == 503:
                raise ApiRouteError(
                    "story_index_database_unavailable",
                    status_code=503,
                ) from exc
            # A missing, moved, or non-canonical server-owned thread workspace
            # is intentionally indistinguishable from a missing Artifact.
            raise ApiRouteError("artifact_missing", status_code=404) from exc
        try:
            binding_service = StoryWorkspaceEpisodeBindingService(workspace)
            registry = binding_service.read_episode_registry_read_only(
                StoryWorkspaceEpisodeBindingContext(
                    workflow_run_id=workflow_run_id,
                    trusted_project_story_slug=source_authority.story_slug,
                    locked_context_story_slug=source_authority.story_slug,
                    run_provenance_story_slug=source_authority.story_slug,
                    episode_uid=source_authority.episode_uid,
                )
            )
            authority = self._episode_authority_from_registry(
                source_authority,
                registry,
            )
        except StoryWorkspaceEpisodeBindingError as exc:
            raise ApiRouteError("artifact_missing", status_code=404) from exc
        surface = self._read_story_index_surface(
            workspace,
            workflow_run_id,
            authority,
        )
        if getattr(surface, "opaque_episode_id", None) is None:
            self._raise_story_index_error("artifact_missing")
        return _AuthorizedStoryIndexContext(
            workflow_run_row=row,
            actor_id=actor_id,
            thread_id=thread_id,
            thread_workspace=workspace,
            episode_authority=authority,
            refreshed_surface=surface,
        )

    @classmethod
    def _story_index_wire_projection(
        cls,
        observation: ArtifactStoryIndexObservation,
    ) -> StoryWorkspaceStoryIndexProjection:
        try:
            return StoryWorkspaceStoryIndexProjection.model_validate(
                observation.public_dict()
            )
        except (TypeError, ValueError) as exc:
            raise ApiRouteError(
                "story_index_invalid_artifact",
                status_code=422,
            ) from exc

    def _inspect_story_index(
        self,
        db: Any,
        context: _AuthorizedStoryIndexContext,
    ) -> ArtifactStoryIndexObservation:
        return self._inspect_story_index_snapshot(db, context).observation

    def _inspect_story_index_snapshot(
        self,
        db: Any,
        context: _AuthorizedStoryIndexContext,
    ) -> ArtifactStoryIndexSnapshot:
        try:
            return ArtifactStoryIndexService().inspect_snapshot(
                db=db,
                workspace_root=context.thread_workspace,
                workflow_run=context.workflow_run_row,
                actor_id=context.actor_id,
                thread_id=context.thread_id,
                episode_authority=context.episode_authority,
                refreshed_surface=context.refreshed_surface,
            )
        except (ArtifactStoryProjectionError, ArtifactStoryIndexRepositoryError) as exc:
            self._raise_story_index_error(exc.code)

    def _get_story_index_sync(
        self,
        workflow_run_id: str,
        actor: dict[str, str],
    ) -> StoryWorkspaceStoryIndexProjection:
        db = database.get_db()
        try:
            context = self._authorized_story_index_context(
                db,
                workflow_run_id,
                actor,
            )
            return self._story_index_wire_projection(
                self._inspect_story_index(db, context)
            )
        except (ApiRouteError, ArtifactStoryProjectionError, ArtifactStoryIndexRepositoryError):
            raise
        except PostgresError as exc:
            raise ApiRouteError(
                "story_index_database_unavailable",
                status_code=503,
            ) from exc
        finally:
            db.close()

    def _reconcile_story_index_sync(
        self,
        workflow_run_id: str,
        _request: StoryWorkspaceStoryIndexReconcileCommand,
        actor: dict[str, str],
        if_match: str,
    ) -> StoryWorkspaceStoryIndexProjection:
        db = database.get_db()
        try:
            context = self._authorized_story_index_context(
                db,
                workflow_run_id,
                actor,
            )
            before = self._inspect_story_index_snapshot(db, context)
            expected = f'"{before.observation.etag}"'
            if if_match != expected:
                self._raise_story_index_error("story_index_revision_conflict")

            # Re-read the pinned canonical surface after the If-Match check.
            refreshed = self._read_story_index_surface(
                context.thread_workspace,
                workflow_run_id,
                context.episode_authority,
            )
            refreshed_context = _AuthorizedStoryIndexContext(
                workflow_run_row=context.workflow_run_row,
                actor_id=context.actor_id,
                thread_id=context.thread_id,
                thread_workspace=context.thread_workspace,
                episode_authority=context.episode_authority,
                refreshed_surface=refreshed,
            )
            fresh_snapshot = self._inspect_story_index_snapshot(db, refreshed_context)
            if if_match != f'"{fresh_snapshot.observation.etag}"':
                self._raise_story_index_error("story_index_revision_conflict")

            story_index_service = ArtifactStoryIndexService()
            result = story_index_service.materialize_projection(
                db=db,
                projection=fresh_snapshot.projection,
                expected_record=fresh_snapshot.record,
                require_expected_record=True,
            )
            status = str(result.get("status") or "failed")
            if status in {"failed", "conflict"}:
                code = str(result.get("errorCode") or "story_index_write_failed")
                self._raise_story_index_error(code)
            return self._story_index_wire_projection(
                story_index_service.inspect_projection(
                    db=db,
                    projection=fresh_snapshot.projection,
                ).observation
            )
        except ApiRouteError:
            raise
        except (ArtifactStoryProjectionError, ArtifactStoryIndexRepositoryError) as exc:
            self._raise_story_index_error(exc.code)
        except PostgresError as exc:
            raise ApiRouteError(
                "story_index_database_unavailable",
                status_code=503,
            ) from exc
        finally:
            db.close()


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
            source_authority = self._episode_authority_from_source(
                row,
                workflow_run_id,
            )
            if source_authority is None:
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
                    source_authority.story_slug
                )
            )
            binding_context = StoryWorkspaceEpisodeBindingContext(
                workflow_run_id=workflow_run_id,
                trusted_project_story_slug=canonical_story_slug,
                locked_context_story_slug=source_authority.story_slug,
                run_provenance_story_slug=source_authority.story_slug,
                episode_uid=source_authority.episode_uid,
            )
            registry = binding_service.read_episode_registry(binding_context)
            authority = self._episode_authority_from_registry(
                source_authority,
                registry,
            )
            surface = StoryWorkspaceEpisodeArtifactService(workspace).read_surface(
                workflow_run_id,
                episode_authority=authority,
            )
            return surface
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
        except StoryWorkspaceEpisodeBindingError as exc:
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
                token_secret=story_workspace_workflow_token_secret(),
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
            try:
                workspace = self._thread_workspace(thread_id)
            except ApiRouteError as exc:
                if not (
                    exc.code == "AGENT_EXECUTION_FAILED"
                    and exc.status_code == 404
                    and workflow_run.status not in _DREAM_OUTPUT_REQUIRED_STATUSES
                ):
                    raise
                # Launch returns before its background turn assembles the
                # canonical Thread workspace.  GET remains read-only and
                # reports the existing wire-level waiting projection instead
                # of turning normal scheduling latency into a 404.
                projection = StoryWorkspaceDreamFileReader.waiting_response(
                    workflow_run,
                    thread_id=thread_id,
                )
            else:
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
            self._require_dream_output_for_ready_status(
                workflow_run,
                projection,
            )
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

    @staticmethod
    def _require_dream_output_for_ready_status(
        workflow_run: WorkflowRun,
        projection: Any,
    ) -> None:
        """Fail closed only after the lifecycle proves output must exist.

        A freshly accepted/running turn may not have materialized ``.dream``
        yet, so its empty projection is an ordinary read-only waiting state.
        Output-validating and review descendants, however, are reachable only
        after the required three-stage output has been produced; absence in
        those states is contract corruption rather than readiness latency.

        Failed/cancelled runs are deliberately excluded because either may be
        terminal before the first output exists.
        """

        if workflow_run.status not in _DREAM_OUTPUT_REQUIRED_STATUSES:
            return
        run_revision = getattr(projection, "run_revision", 0)
        stages = getattr(projection, "stages", None)
        required_stages = getattr(projection, "required_stages", None)
        if (
            not isinstance(run_revision, int)
            or run_revision < 1
            or not isinstance(stages, dict)
            or not isinstance(required_stages, list)
            or set(stages) != set(required_stages)
        ):
            raise ApiRouteError("OUTPUT_CONTRACT_INVALID", status_code=422)



class DreamConfirmationApplicationService(_StoryWorkspaceApplicationSupport):
    """Dream business confirmation application service."""

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
                    token_secret=story_workspace_workflow_token_secret(),
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
                persisted = service.submit_confirmation(
                    workflow_run_id,
                    request,
                    actor_id=str(actor_id),
                )
                asyncio.run(
                    StoryWorkspaceDreamWorkflowLifecycleService(
                        db,
                        token_secret=story_workspace_workflow_token_secret(),
                    ).record_confirmation_accepted(
                        workflow_run_id,
                        actor_context,
                        review_items_approved=True,
                    )
                )
                return persisted
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



_RUN_APPLICATION_SERVICE = StoryWorkflowRunApplicationService()
_ARTIFACT_APPLICATION_SERVICE = DreamArtifactApplicationService()
_CONFIRMATION_APPLICATION_SERVICE = DreamConfirmationApplicationService()


def get_story_workflow_run_application_service() -> StoryWorkflowRunApplicationService:
    return _RUN_APPLICATION_SERVICE


def get_dream_artifact_application_service() -> DreamArtifactApplicationService:
    return _ARTIFACT_APPLICATION_SERVICE


def get_dream_confirmation_application_service() -> DreamConfirmationApplicationService:
    return _CONFIRMATION_APPLICATION_SERVICE


def story_workspace_get_dream_confirmation_coordinator(
) -> StoryWorkspaceDreamConfirmationCoordinator:
    """Return the process singleton managed by the FastAPI lifecycle."""

    return _DREAM_CONFIRMATION_COORDINATOR
