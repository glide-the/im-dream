# [Input] Admin-authorized Story Workspace DTOs, Dream thread workspaces, and application commands.
# [Output] Dream workflow API projections with strict filesystem and provenance boundaries.
# [Pos] Deck-domain Story Workflow orchestration; all relational access belongs to Admin DTO/ORM services.
# [Sync] 2026-09-16: move public Artifact authority, run listing, index reads and index writes to Registry185-191.
# [Sync] 2026-09-16: preserve Dream Runtime, observer, confirmation and shared-filesystem behavior without PostgreSQL access.

"""Focused application services for Dream workflow business APIs."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
import importlib.util
import logging
from pathlib import Path
import stat
import sys
from typing import Any
from uuid import uuid4

try:
    from models.workflow_run import RunStatus, WorkflowRun
    from story_workspace.contracts import (
        StoryWorkspaceDreamAgentActivityResponse,
        StoryWorkspaceStoryIndexProjection,
        StoryWorkspaceStoryIndexReconcileCommand,
    )
    from services.errors.error_registry import ApiRouteError
    from services.admin_data.errors import AdminDataError
    from services.admin_data.run_data import AdminRunData, RunLookupInputDTO
    from services.admin_data.story_workspace_artifact_data import (
        AdminStoryWorkspaceArtifactData,
        StoryWorkspaceArtifactAuthorityDTO,
        StoryWorkspaceArtifactAuthorityInputDTO,
        StoryWorkspaceArtifactCursorDTO,
        StoryWorkspaceArtifactIndexInputDTO,
        StoryWorkspaceArtifactIndexReconcileInputDTO,
        StoryWorkspaceArtifactProjectionDTO,
        StoryWorkspaceArtifactRunsInputDTO,
    )
    from services.admin_data.story_workspace_confirmation_data import (
        AdminStoryWorkspaceConfirmationData,
        StoryWorkspaceConfirmationSubmitInputDTO,
    )
    from services.story_workspace.dream_confirmation_service import (
        StoryWorkspaceDreamConfirmationCoordinator,
        StoryWorkspaceDreamConfirmationError,
        story_workspace_confirmation_command_json,
        story_workspace_persisted_confirmation,
        story_workspace_validate_confirmation_projection,
    )
    from services.story_workspace.dream_file_service import (
        StoryWorkspaceDreamContractError,
        StoryWorkspaceDreamDurabilityIndeterminate,
        StoryWorkspaceDreamFileError,
        StoryWorkspaceDreamFileReader,
        StoryWorkspaceDreamIOError,
        StoryWorkspaceDreamPathError,
        StoryWorkspaceDreamPlatformUnsupported,
    )
    from services.story_workspace.dream_reentry_service import (
        StoryWorkspaceDreamReentryService,
        StoryWorkspaceDreamReentryWorkspaceMissing,
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
    from services.story_workspace.artifact_story_index_projector import (
        ArtifactStoryIndexProjector,
        ArtifactStoryProjectionError,
    )
except ModuleNotFoundError:  # Support package imports from repository root.
    from backend.models.workflow_run import RunStatus, WorkflowRun
    from backend.story_workspace.contracts import (
        StoryWorkspaceDreamAgentActivityResponse,
        StoryWorkspaceStoryIndexProjection,
        StoryWorkspaceStoryIndexReconcileCommand,
    )
    from backend.services.errors.error_registry import ApiRouteError
    from backend.services.admin_data.errors import AdminDataError
    from backend.services.admin_data.run_data import AdminRunData, RunLookupInputDTO
    from backend.services.admin_data.story_workspace_artifact_data import (
        AdminStoryWorkspaceArtifactData,
        StoryWorkspaceArtifactAuthorityDTO,
        StoryWorkspaceArtifactAuthorityInputDTO,
        StoryWorkspaceArtifactCursorDTO,
        StoryWorkspaceArtifactIndexInputDTO,
        StoryWorkspaceArtifactIndexReconcileInputDTO,
        StoryWorkspaceArtifactProjectionDTO,
        StoryWorkspaceArtifactRunsInputDTO,
    )
    from backend.services.admin_data.story_workspace_confirmation_data import (
        AdminStoryWorkspaceConfirmationData,
        StoryWorkspaceConfirmationSubmitInputDTO,
    )
    from backend.services.story_workspace.dream_confirmation_service import (
        StoryWorkspaceDreamConfirmationCoordinator,
        StoryWorkspaceDreamConfirmationError,
        story_workspace_confirmation_command_json,
        story_workspace_persisted_confirmation,
        story_workspace_validate_confirmation_projection,
    )
    from backend.services.story_workspace.dream_file_service import (
        StoryWorkspaceDreamContractError,
        StoryWorkspaceDreamDurabilityIndeterminate,
        StoryWorkspaceDreamFileError,
        StoryWorkspaceDreamFileReader,
        StoryWorkspaceDreamIOError,
        StoryWorkspaceDreamPathError,
        StoryWorkspaceDreamPlatformUnsupported,
    )
    from backend.services.story_workspace.dream_reentry_service import (
        StoryWorkspaceDreamReentryService,
        StoryWorkspaceDreamReentryWorkspaceMissing,
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
    from backend.services.story_workspace.artifact_story_index_projector import (
        ArtifactStoryIndexProjector,
        ArtifactStoryProjectionError,
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
_ADMIN_STORY_INDEX_ERROR_CODES = {
    "STORY_INDEX_INVALID_ARTIFACT": "story_index_invalid_artifact",
    "STORY_INDEX_CONFLICT": "story_index_conflict",
    "STORY_INDEX_REVISION_CONFLICT": "story_index_revision_conflict",
    "STORY_INDEX_WRITE_FAILED": "story_index_write_failed",
}
logger = logging.getLogger(__name__)


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


_DREAM_CONFIRMATION_COORDINATOR = StoryWorkspaceDreamConfirmationCoordinator()


class _StoryWorkspaceApplicationSupport:
    """Shared filesystem and safe-error helpers; exposes no data endpoint."""

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
            raise ApiRouteError("DECK_RUNTIME_CONFIG_UNAVAILABLE", status_code=503) from exc
        if not resolved_root.is_dir():
            raise ApiRouteError("DECK_RUNTIME_CONFIG_UNAVAILABLE", status_code=503)
        supplied_workspace = supplied_root / thread_id
        try:
            metadata = supplied_workspace.lstat()
        except FileNotFoundError as exc:
            raise ApiRouteError("AGENT_EXECUTION_FAILED", status_code=404) from exc
        except (OSError, ValueError) as exc:
            raise ApiRouteError("DECK_RUNTIME_CONFIG_UNAVAILABLE", status_code=503) from exc
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
            raise ApiRouteError("DECK_RUNTIME_CONFIG_UNAVAILABLE", status_code=503) from exc
        raise ApiRouteError("AGENT_EXECUTION_FAILED", status_code=422) from exc

    @staticmethod
    def _dream_agent_thread_factory() -> Any | None:
        try:
            from agent_factory import claude_agent_thread_factory

            return claude_agent_thread_factory
        except Exception:
            return None

    @staticmethod
    def _episode_authority_from_registry(
        source_authority: StoryWorkspaceEpisodeAuthority,
        registry: Any,
        selected_episode_id: str | None = None,
    ) -> StoryWorkspaceEpisodeAuthority:
        """Derive one registry member while keeping launch authority immutable."""

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
        target_uid = (
            selected_episode_id
            if selected_episode_id is not None
            else getattr(registry, "active_episode_uid", None)
        )
        selected = next(
            (item for item in entries if getattr(item, "episode_uid", None) == target_uid),
            None,
        )
        if selected is None:
            raise StoryWorkspaceEpisodeBindingError(
                "selected Episode is absent from the registry"
            )
        return StoryWorkspaceEpisodeAuthority(
            workflow_run_id=source_authority.workflow_run_id,
            episode_uid=selected.episode_uid,
            story_slug=source_authority.story_slug,
            episode_code=selected.episode_code,
        )


class DreamArtifactApplicationService(_StoryWorkspaceApplicationSupport):
    """Consume Admin authority/ORM contracts and project shared files locally."""

    async def get_dream_files(
        self,
        workflow_run_id: str,
        *,
        actor: dict[str, str],
        artifact_data: AdminStoryWorkspaceArtifactData,
        access_token: str,
    ) -> Any:
        projection = await asyncio.to_thread(
            self._get_dream_files_sync,
            workflow_run_id,
            actor,
            artifact_data,
            access_token,
        )
        return self._attach_dream_agent_activity(
            projection,
            workflow_run_id=workflow_run_id,
            actor_id=str(actor["actor_id"]),
        )

    async def get_episode_artifacts(
        self,
        workflow_run_id: str,
        *,
        actor: dict[str, str],
        artifact_data: AdminStoryWorkspaceArtifactData,
        access_token: str,
        episode_id: str | None = None,
    ) -> Any:
        return await asyncio.to_thread(
            self._get_episode_artifacts_sync,
            workflow_run_id,
            actor,
            artifact_data,
            access_token,
            episode_id,
        )

    async def get_episode_index(
        self,
        workflow_run_id: str,
        *,
        actor: dict[str, str],
        artifact_data: AdminStoryWorkspaceArtifactData,
        access_token: str,
    ) -> Any:
        return await asyncio.to_thread(
            self._get_episode_index_sync,
            workflow_run_id,
            actor,
            artifact_data,
            access_token,
        )

    async def get_story_index(
        self,
        workflow_run_id: str,
        *,
        actor: dict[str, str],
        artifact_data: AdminStoryWorkspaceArtifactData,
        access_token: str,
    ) -> StoryWorkspaceStoryIndexProjection:
        return await asyncio.to_thread(
            self._get_story_index_sync,
            workflow_run_id,
            actor,
            artifact_data,
            access_token,
        )

    async def reconcile_story_index(
        self,
        workflow_run_id: str,
        request: StoryWorkspaceStoryIndexReconcileCommand,
        *,
        actor: dict[str, str],
        artifact_data: AdminStoryWorkspaceArtifactData,
        access_token: str,
        if_match: str,
    ) -> StoryWorkspaceStoryIndexProjection:
        return await asyncio.to_thread(
            self._reconcile_story_index_sync,
            workflow_run_id,
            request,
            actor,
            artifact_data,
            access_token,
            if_match,
        )

    async def list_dream_runs(
        self,
        *,
        actor: dict[str, str],
        artifact_data: AdminStoryWorkspaceArtifactData,
        access_token: str,
    ) -> Any:
        return await asyncio.to_thread(
            self._list_dream_runs_sync,
            actor,
            artifact_data,
            access_token,
        )

    def _authority(
        self,
        workflow_run_id: str,
        actor: dict[str, str],
        artifact_data: AdminStoryWorkspaceArtifactData,
        access_token: str,
    ) -> StoryWorkspaceArtifactAuthorityDTO:
        try:
            output = artifact_data.authority(
                StoryWorkspaceArtifactAuthorityInputDTO(
                    workflow_run_id=workflow_run_id,
                ),
                uuid4().hex,
                access_token=access_token,
            )
        except AdminDataError as exc:
            if exc.code in {"WORKFLOW_RUN_NOT_FOUND", "DREAM_DELEGATION_ENTITY_DENIED"}:
                raise ApiRouteError(
                    "WORKFLOW_PERMISSION_DENIED",
                    status_code=404 if exc.status_code == 404 else 403,
                ) from exc
            raise ApiRouteError(exc.code, status_code=exc.status_code) from exc
        self._require_actor(output.authority, actor)
        return output.authority

    @staticmethod
    def _require_actor(
        authority: StoryWorkspaceArtifactAuthorityDTO,
        actor: dict[str, str],
    ) -> None:
        try:
            actor_id = str(actor["actor_id"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ApiRouteError("WORKFLOW_PERMISSION_DENIED", status_code=403) from exc
        if authority.run.created_by != actor_id:
            raise ApiRouteError("WORKFLOW_PERMISSION_DENIED", status_code=403)

    def _list_dream_runs_sync(
        self,
        actor: dict[str, str],
        artifact_data: AdminStoryWorkspaceArtifactData,
        access_token: str,
    ) -> Any:
        authorities: list[StoryWorkspaceArtifactAuthorityDTO] = []
        cursor: StoryWorkspaceArtifactCursorDTO | None = None
        seen: set[tuple[str, str]] = set()
        while True:
            try:
                page = artifact_data.list_runs(
                    StoryWorkspaceArtifactRunsInputDTO(limit=100, cursor=cursor),
                    uuid4().hex,
                    access_token=access_token,
                )
            except AdminDataError as exc:
                raise ApiRouteError(exc.code, status_code=exc.status_code) from exc
            for authority in page.runs:
                self._require_actor(authority, actor)
            authorities.extend(page.runs)
            cursor = page.next_cursor
            if cursor is None:
                break
            key = (cursor.created_at, cursor.workflow_run_id)
            if key in seen:
                raise ApiRouteError("ADMIN_RESPONSE_INVALID", status_code=503)
            seen.add(key)
        return StoryWorkspaceDreamReentryService(
            dream_files_loader=self._load_dream_reentry_stage_projection,
        ).list_dream_runs(authorities=authorities)

    def _load_dream_reentry_stage_projection(
        self,
        authority: StoryWorkspaceArtifactAuthorityDTO,
    ) -> StoryWorkspaceDreamReentryStageProjection:
        workflow_run = authority.workflow_run()
        try:
            projection = self._read_dream_files_for_authorized_run(
                workflow_run,
                thread_id=authority.thread_id,
            )
            stage_activity_at = self._dream_reentry_stage_activity_at(projection)
        except ApiRouteError as exc:
            if exc.code == "AGENT_EXECUTION_FAILED" and exc.status_code == 404:
                raise StoryWorkspaceDreamReentryWorkspaceMissing(
                    authority.thread_id
                ) from exc
            raise
        except StoryWorkspaceDreamFileError as exc:
            self._raise_dream_file_error(exc)
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
                workspace
                / ".dream"
                / "runtime"
                / "runs"
                / run_id
                / "stages"
                / f"{stage.value}.json"
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
        artifact_data: AdminStoryWorkspaceArtifactData,
        access_token: str,
    ) -> Any:
        authority = self._authority(workflow_run_id, actor, artifact_data, access_token)
        workflow_run = authority.workflow_run()
        thread_id = authority.thread_id
        try:
            projection = self._read_dream_files_for_authorized_run(
                workflow_run,
                thread_id=thread_id,
            )
        except ApiRouteError as exc:
            if not (
                exc.code == "AGENT_EXECUTION_FAILED"
                and exc.status_code == 404
                and workflow_run.status not in _DREAM_OUTPUT_REQUIRED_STATUSES
            ):
                raise
            projection = StoryWorkspaceDreamFileReader.waiting_response(
                workflow_run,
                thread_id=thread_id,
            )
        except StoryWorkspaceDreamFileError as exc:
            self._raise_dream_file_error(exc)
        self._require_dream_output_for_ready_status(workflow_run, projection)
        return projection.model_copy(
            update={
                "confirmation_accepted": authority.confirmation_accepted,
                "confirmation_dispatched": authority.confirmation_dispatched,
                "can_confirm": (
                    projection.can_confirm and not authority.confirmation_accepted
                ),
            }
        )

    def _episode_registry_context(
        self,
        authority: StoryWorkspaceArtifactAuthorityDTO,
    ) -> tuple[Path, StoryWorkspaceEpisodeAuthority, Any] | None:
        if authority.episode_authority is None:
            return None
        source = StoryWorkspaceEpisodeAuthority.parse(
            authority.episode_authority.model_dump(by_alias=True),
            expected_run_id=authority.run.workflow_run_id,
        )
        if source is None:
            raise ApiRouteError("OUTPUT_CONTRACT_INVALID", status_code=422)
        try:
            workspace = self._thread_workspace(authority.thread_id)
        except ApiRouteError as exc:
            raise ApiRouteError("WORKFLOW_PERMISSION_DENIED", status_code=404) from exc
        binding_service = StoryWorkspaceEpisodeBindingService(workspace)
        canonical_story_slug = binding_service.read_canonical_project_story_slug(
            source.story_slug
        )
        registry = binding_service.read_episode_registry_read_only(
            StoryWorkspaceEpisodeBindingContext(
                workflow_run_id=authority.run.workflow_run_id,
                trusted_project_story_slug=canonical_story_slug,
                locked_context_story_slug=source.story_slug,
                run_provenance_story_slug=source.story_slug,
                episode_uid=source.episode_uid,
            )
        )
        return workspace, source, registry

    def _get_episode_artifacts_sync(
        self,
        workflow_run_id: str,
        actor: dict[str, str],
        artifact_data: AdminStoryWorkspaceArtifactData,
        access_token: str,
        episode_id: str | None = None,
    ) -> Any:
        authority = self._authority(workflow_run_id, actor, artifact_data, access_token)
        try:
            context = self._episode_registry_context(authority)
            if context is None:
                return StoryWorkspaceEpisodeArtifactService.unbound_surface(
                    workflow_run_id
                )
            workspace, source, registry = context
            selected = self._episode_authority_from_registry(
                source,
                registry,
                selected_episode_id=episode_id,
            )
            return StoryWorkspaceEpisodeArtifactService(workspace).read_surface(
                workflow_run_id,
                episode_authority=selected,
            )
        except StoryWorkspaceEpisodeArtifactPathError as exc:
            raise ApiRouteError("WORKFLOW_PERMISSION_DENIED", status_code=404) from exc
        except StoryWorkspaceEpisodeArtifactContractError as exc:
            raise ApiRouteError("OUTPUT_CONTRACT_INVALID", status_code=422) from exc
        except StoryWorkspaceEpisodeArtifactError as exc:
            raise ApiRouteError("DECK_RUNTIME_CONFIG_UNAVAILABLE", status_code=503) from exc
        except StoryWorkspaceEpisodeBindingError as exc:
            raise ApiRouteError("WORKFLOW_PERMISSION_DENIED", status_code=404) from exc

    def _get_episode_index_sync(
        self,
        workflow_run_id: str,
        actor: dict[str, str],
        artifact_data: AdminStoryWorkspaceArtifactData,
        access_token: str,
    ) -> Any:
        authority = self._authority(workflow_run_id, actor, artifact_data, access_token)
        try:
            context = self._episode_registry_context(authority)
            if context is None:
                return StoryWorkspaceEpisodeArtifactService.unbound_index(
                    workflow_run_id
                )
            workspace, source, registry = context
            return StoryWorkspaceEpisodeArtifactService(workspace).read_index(
                workflow_run_id,
                episode_authority=source,
                registry=registry,
            )
        except StoryWorkspaceEpisodeArtifactPathError as exc:
            raise ApiRouteError("WORKFLOW_PERMISSION_DENIED", status_code=404) from exc
        except StoryWorkspaceEpisodeArtifactContractError as exc:
            raise ApiRouteError("OUTPUT_CONTRACT_INVALID", status_code=422) from exc
        except StoryWorkspaceEpisodeArtifactError as exc:
            raise ApiRouteError("DECK_RUNTIME_CONFIG_UNAVAILABLE", status_code=503) from exc
        except StoryWorkspaceEpisodeBindingError as exc:
            raise ApiRouteError("WORKFLOW_PERMISSION_DENIED", status_code=404) from exc

    @staticmethod
    def _story_index_error_status(code: str) -> int:
        return _STORY_INDEX_ERROR_STATUSES.get(code, 503)

    @classmethod
    def _raise_story_index_error(cls, code: str) -> None:
        code = _ADMIN_STORY_INDEX_ERROR_CODES.get(code, code)
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
        try:
            return StoryWorkspaceEpisodeArtifactService(workspace).read_surface(
                workflow_run_id,
                episode_authority=authority,
            )
        except StoryWorkspaceEpisodeArtifactPathError as exc:
            raise ApiRouteError("artifact_missing", status_code=404) from exc
        except StoryWorkspaceEpisodeArtifactError as exc:
            raise ApiRouteError("story_index_invalid_artifact", status_code=422) from exc

    def _story_projection(
        self,
        authority: StoryWorkspaceArtifactAuthorityDTO,
    ) -> StoryWorkspaceArtifactProjectionDTO:
        try:
            context = self._episode_registry_context(authority)
            if context is None:
                self._raise_story_index_error("artifact_missing")
            workspace, source, registry = context
            selected = self._episode_authority_from_registry(source, registry)
            surface = self._read_story_index_surface(
                workspace,
                authority.run.workflow_run_id,
                selected,
            )
            if getattr(surface, "opaque_episode_id", None) is None:
                self._raise_story_index_error("artifact_missing")
            projected = ArtifactStoryIndexProjector.project(
                workspace_root=workspace,
                workflow_run=authority.workflow_run(),
                actor_id=authority.run.created_by,
                thread_id=authority.thread_id,
                episode_authority=selected,
                refreshed_surface=surface,
            )
            return StoryWorkspaceArtifactProjectionDTO(
                source_project_id=projected.source_project_id,
                title=projected.title,
                episode_count=projected.episode_count,
                artifact_manifest_revision=projected.artifact_manifest_revision,
                script_revision=projected.script_revision,
                script_size_bytes=projected.script_size_bytes,
                artifact_status="available",
            )
        except ArtifactStoryProjectionError as exc:
            self._raise_story_index_error(exc.code)
        except ApiRouteError as exc:
            if exc.status_code == 404:
                self._raise_story_index_error("artifact_missing")
            raise
        except StoryWorkspaceEpisodeBindingError as exc:
            raise ApiRouteError("artifact_missing", status_code=404) from exc

    @staticmethod
    def _story_index_wire_projection(observation: Any) -> StoryWorkspaceStoryIndexProjection:
        try:
            return StoryWorkspaceStoryIndexProjection.model_validate(
                observation.model_dump()
            )
        except (TypeError, ValueError) as exc:
            raise ApiRouteError("story_index_invalid_artifact", status_code=422) from exc

    def _inspect_story_index(
        self,
        workflow_run_id: str,
        projection: StoryWorkspaceArtifactProjectionDTO,
        artifact_data: AdminStoryWorkspaceArtifactData,
        access_token: str,
    ) -> StoryWorkspaceStoryIndexProjection:
        try:
            result = artifact_data.inspect_index(
                StoryWorkspaceArtifactIndexInputDTO(
                    workflow_run_id=workflow_run_id,
                    projection=projection,
                ),
                uuid4().hex,
                access_token=access_token,
            )
        except AdminDataError as exc:
            self._raise_story_index_error(exc.code)
        return self._story_index_wire_projection(result.observation)

    def _get_story_index_sync(
        self,
        workflow_run_id: str,
        actor: dict[str, str],
        artifact_data: AdminStoryWorkspaceArtifactData,
        access_token: str,
    ) -> StoryWorkspaceStoryIndexProjection:
        authority = self._authority(workflow_run_id, actor, artifact_data, access_token)
        projection = self._story_projection(authority)
        return self._inspect_story_index(
            workflow_run_id,
            projection,
            artifact_data,
            access_token,
        )

    def _reconcile_story_index_sync(
        self,
        workflow_run_id: str,
        _request: StoryWorkspaceStoryIndexReconcileCommand,
        actor: dict[str, str],
        artifact_data: AdminStoryWorkspaceArtifactData,
        access_token: str,
        if_match: str,
    ) -> StoryWorkspaceStoryIndexProjection:
        authority = self._authority(workflow_run_id, actor, artifact_data, access_token)
        before_projection = self._story_projection(authority)
        before = self._inspect_story_index(
            workflow_run_id,
            before_projection,
            artifact_data,
            access_token,
        )
        if if_match != f'"{before.etag}"':
            self._raise_story_index_error("story_index_revision_conflict")

        fresh_projection = self._story_projection(authority)
        fresh = self._inspect_story_index(
            workflow_run_id,
            fresh_projection,
            artifact_data,
            access_token,
        )
        if if_match != f'"{fresh.etag}"':
            self._raise_story_index_error("story_index_revision_conflict")
        try:
            result = artifact_data.reconcile_index(
                StoryWorkspaceArtifactIndexReconcileInputDTO(
                    workflow_run_id=workflow_run_id,
                    projection=fresh_projection,
                    expected_etag=fresh.etag,
                ),
                uuid4().hex,
                access_token=access_token,
            )
        except AdminDataError as exc:
            self._raise_story_index_error(exc.code)
        return self._story_index_wire_projection(result.observation)

    def _attach_dream_agent_activity(
        self,
        projection: Any,
        *,
        workflow_run_id: str,
        actor_id: str,
    ) -> Any:
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

    @staticmethod
    def _require_dream_output_for_ready_status(
        workflow_run: WorkflowRun,
        projection: Any,
    ) -> None:
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
        run_data: AdminRunData,
        confirmation_data: AdminStoryWorkspaceConfirmationData,
        access_token: str,
    ) -> Any:
        """Validate shared files, persist through Admin, then queue Runtime."""

        persisted = await asyncio.to_thread(
            self._submit_dream_confirmation_sync,
            workflow_run_id,
            request,
            actor,
            run_data,
            confirmation_data,
            access_token,
        )
        accepted = persisted.accepted
        dispatch = persisted.dispatch
        if dispatch is None:
            return accepted
        try:
            self._dream_confirmation_coordinator.schedule(dispatch)
        except Exception:
            logger.exception(
                "Dream confirmation scheduling deferred for run_id=%s message_id=%s",
                workflow_run_id,
                dispatch.message_id,
            )
        return accepted.model_copy(update={"dispatched": False})

    def _submit_dream_confirmation_sync(
        self,
        workflow_run_id: str,
        request: Any,
        actor: dict[str, str],
        run_data: AdminRunData,
        confirmation_data: AdminStoryWorkspaceConfirmationData,
        access_token: str,
    ) -> Any:
        """Use authoritative Admin DTOs around two local projection checks."""

        try:
            try:
                actor_id = str(actor["actor_id"])
                workspace_id = str(actor["workspace_id"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ApiRouteError("WORKFLOW_PERMISSION_DENIED", status_code=403) from exc
            raw_run = run_data.read(
                RunLookupInputDTO(
                    workspace_id=workspace_id,
                    workflow_run_id=workflow_run_id,
                ),
                uuid4().hex,
                access_token=access_token,
            )
            workflow_run = WorkflowRun.model_validate(raw_run)
            if workflow_run.created_by != actor_id:
                raise ApiRouteError("WORKFLOW_PERMISSION_DENIED", status_code=403)
            thread_id = workflow_run.source_voice_thread_id
            if (
                not isinstance(thread_id, str)
                or not thread_id.strip()
                or request.story_workspace_run_id != workflow_run_id
                or request.thread_id != thread_id
            ):
                raise ApiRouteError("CONFIG_VERSION_DRIFT", status_code=409)

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

            first_projection = reader.read(workflow_run, thread_id=thread_id)
            story_workspace_validate_confirmation_projection(first_projection, request)
            final_projection = reader.read(workflow_run, thread_id=thread_id)
            story_workspace_validate_confirmation_projection(final_projection, request)
            result = confirmation_data.submit_recovering(
                StoryWorkspaceConfirmationSubmitInputDTO(
                    command_json=story_workspace_confirmation_command_json(request),
                ),
                uuid4().hex,
                access_token=access_token,
            )
            return story_workspace_persisted_confirmation(result)
        except StoryWorkspaceDreamConfirmationError as exc:
            raise ApiRouteError(exc.code, status_code=exc.status_code) from exc
        except AdminDataError as exc:
            raise ApiRouteError(exc.code, status_code=exc.status_code) from exc
        except ApiRouteError:
            raise
        except StoryWorkspaceDreamFileError as exc:
            self._raise_dream_file_error(exc)
        except Exception as exc:
            raise ApiRouteError("DECK_RUNTIME_CONFIG_UNAVAILABLE", status_code=503) from exc


_ARTIFACT_APPLICATION_SERVICE = DreamArtifactApplicationService()
_CONFIRMATION_APPLICATION_SERVICE = DreamConfirmationApplicationService()


def get_dream_artifact_application_service() -> DreamArtifactApplicationService:
    return _ARTIFACT_APPLICATION_SERVICE


def get_dream_confirmation_application_service() -> DreamConfirmationApplicationService:
    return _CONFIRMATION_APPLICATION_SERVICE


def story_workspace_get_dream_confirmation_coordinator(
) -> StoryWorkspaceDreamConfirmationCoordinator:
    """Return the process singleton managed by the FastAPI lifecycle."""

    return _DREAM_CONFIRMATION_COORDINATOR
