# [Input] Consume trusted Dream Run context, WorkflowRun authority, canonical
#         Story Workspace files, and existing Dream file reader/writer contracts.
# [Output] Before-turn canonical snapshot plus successful-turn deterministic
#          synchronization into the Run-private preview, EP01 binding, and
#          PostgreSQL Story projection consumed by the Execution page.
# [Pos] Dream post-turn business Hook above ClaudeAgentService; not an Agent
#       runtime, Observer, SSE adapter, or SDK entry point.
# [Sync] 2026-08-13: added host-owned automatic workbench synchronization.
# [Sync] 2026-08-13: reconcile all three stages as complete file facts,
#                    including deletion when a Skill removes every source.
# [Sync] 2026-08-14: publish complete character/scene source content beside
#                    compact summaries for the Execution focus reader.
# [Sync] 2026-08-14: compare stage projections through the canonical storage
#                    model so whitespace/default normalization stays idempotent.

"""Root-turn synchronization from canonical workbench files to one Dream Run.

The Claude runner writes ordinary, user-visible workbench files.  This module
is the server-owned after-turn boundary that projects those files into the
private ``.dream`` Run without relying on the model to remember an MCP call.
It does not run the Agent or emit SSE frames. Workflow and Episode updates are
derived only after a successful root turn and remain actor/thread/run scoped.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
from typing import Any, Mapping
from uuid import uuid4

import yaml

try:
    import database
    from models.workflow_run import AuthenticatedActorContext, WorkflowRun
    from services.story_workspace.dream_file_service import (
        StoryWorkspaceDreamContractError,
        StoryWorkspaceDreamFileReader,
        StoryWorkspaceDreamFileWriter,
    )
    from services.story_workspace.episode_binding_service import (
        StoryWorkspaceEpisodeBindingError,
        StoryWorkspaceEpisodeBindingService,
        StoryWorkspaceEpisodeBindingContext,
    )
    from services.story_workspace.episode_artifact_service import (
        StoryWorkspaceEpisodeAuthority,
        StoryWorkspaceEpisodeArtifactError,
        StoryWorkspaceEpisodeArtifactService,
    )
    from services.story_workspace.artifact_story_index_service import (
        ArtifactStoryIndexService,
    )
    from services.story_workspace.dream_workflow_lifecycle_service import (
        StoryWorkspaceDreamWorkflowLifecycleService,
    )
    from services.story_workspace.canonical_project_instruction import (
        story_workspace_canonical_project_fallback_slug,
    )
    from services.story_workspace.workflow_security import (
        story_workspace_workflow_token_secret,
    )
    from services.workflow.run_service import WorkflowRunService
    from story_workspace.contracts import (
        STORY_WORKSPACE_DREAM_ITEMS_MAX,
        STORY_WORKSPACE_DREAM_RELATIONS_MAX,
        STORY_WORKSPACE_DREAM_SOURCE_FILES_MAX,
        STORY_WORKSPACE_DREAM_REQUIRED_STAGES,
        StoryWorkspaceDreamRunContext,
        StoryWorkspaceDreamStage,
        StoryWorkspaceDreamStageItem,
    )
except ModuleNotFoundError:  # Support repository-root package imports.
    from backend import database
    from backend.models.workflow_run import AuthenticatedActorContext, WorkflowRun
    from backend.services.story_workspace.dream_file_service import (
        StoryWorkspaceDreamContractError,
        StoryWorkspaceDreamFileReader,
        StoryWorkspaceDreamFileWriter,
    )
    from backend.services.story_workspace.episode_binding_service import (
        StoryWorkspaceEpisodeBindingError,
        StoryWorkspaceEpisodeBindingService,
        StoryWorkspaceEpisodeBindingContext,
    )
    from backend.services.story_workspace.episode_artifact_service import (
        StoryWorkspaceEpisodeAuthority,
        StoryWorkspaceEpisodeArtifactError,
        StoryWorkspaceEpisodeArtifactService,
    )
    from backend.services.story_workspace.artifact_story_index_service import (
        ArtifactStoryIndexService,
    )
    from backend.services.story_workspace.dream_workflow_lifecycle_service import (
        StoryWorkspaceDreamWorkflowLifecycleService,
    )
    from backend.services.story_workspace.canonical_project_instruction import (
        story_workspace_canonical_project_fallback_slug,
    )
    from backend.services.story_workspace.workflow_security import (
        story_workspace_workflow_token_secret,
    )
    from backend.services.workflow.run_service import WorkflowRunService
    from backend.story_workspace.contracts import (
        STORY_WORKSPACE_DREAM_ITEMS_MAX,
        STORY_WORKSPACE_DREAM_RELATIONS_MAX,
        STORY_WORKSPACE_DREAM_SOURCE_FILES_MAX,
        STORY_WORKSPACE_DREAM_REQUIRED_STAGES,
        StoryWorkspaceDreamRunContext,
        StoryWorkspaceDreamStage,
        StoryWorkspaceDreamStageItem,
    )


_RUN_ID = re.compile(r"^run_[0-9a-f]{32}$")
_SAFE_SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,254}$")
_STORY_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_EPISODE_CODE = re.compile(r"^EP[0-9]{2}$")
_SOURCE_MAX_BYTES = 2 * 1024 * 1024
_PRIVATE_TOTAL_MAX_BYTES = 16 * 1024 * 1024
_PRIVATE_FILE_NAMES = frozenset(
    {
        "project.yaml",
        "script.md",
        "episode-outline.md",
        "storyboard.yaml",
        "review-report.md",
    }
)


class DreamArtifactTurnHookError(RuntimeError):
    """A bounded workbench synchronization failure."""


@dataclass(frozen=True)
class DreamArtifactTurnTicket:
    """Server-derived scope captured before one root Agent turn."""

    context: StoryWorkspaceDreamRunContext
    actor_id: str
    workspace_root: Path
    baseline_files: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class DreamArtifactTurnResult:
    """Internal diagnostics; never part of the Chat/SSE contract."""

    changed_stages: tuple[str, ...]
    private_artifact_changed: bool
    private_files: tuple[str, ...]
    changed_source_files: tuple[str, ...]
    episode_bound: bool
    story_index_status: str | None


@dataclass(frozen=True)
class _StageProjection:
    stage: StoryWorkspaceDreamStage
    source_files: tuple[str, ...]
    items: tuple[dict[str, object], ...]


class StoryWorkspaceDreamArtifactPublisher:
    """Durably publish an allowlisted snapshot below one pinned Run directory.

    Files are written before ``artifact/manifest.json``.  The manifest is the
    commit marker, so a mid-copy failure never advertises a partial snapshot.
    Old unreferenced files may remain physically present, but are not part of
    the published snapshot.
    """

    def __init__(self, workspace_root: Path) -> None:
        try:
            visible = workspace_root.lstat()
            resolved = workspace_root.resolve(strict=True)
            pinned = resolved.stat(follow_symlinks=False)
        except (OSError, RuntimeError) as exc:
            raise DreamArtifactTurnHookError("workspace root is unavailable") from exc
        if stat.S_ISLNK(visible.st_mode) or not stat.S_ISDIR(pinned.st_mode):
            raise DreamArtifactTurnHookError("workspace root is unsafe")
        self._workspace_root = resolved

    @staticmethod
    def _directory_flags() -> int:
        return os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(
            os, "O_CLOEXEC", 0
        )

    @staticmethod
    def _file_flags() -> int:
        return os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)

    @classmethod
    def _open_directory(
        cls,
        parent: int,
        name: str,
        *,
        create: bool,
    ) -> int:
        if (name != ".dream" and _SAFE_SEGMENT.fullmatch(name) is None) or name in {
            ".",
            "..",
        }:
            raise DreamArtifactTurnHookError("private artifact path is invalid")
        if create:
            try:
                os.mkdir(name, mode=0o700, dir_fd=parent)
            except FileExistsError:
                pass
            except OSError as exc:
                raise DreamArtifactTurnHookError(
                    "private artifact directory cannot be created"
                ) from exc
        try:
            descriptor = os.open(name, cls._directory_flags(), dir_fd=parent)
            pinned = os.fstat(descriptor)
            visible = os.stat(name, dir_fd=parent, follow_symlinks=False)
        except OSError as exc:
            raise DreamArtifactTurnHookError(
                "private artifact directory is unsafe"
            ) from exc
        if (
            not stat.S_ISDIR(pinned.st_mode)
            or stat.S_ISLNK(visible.st_mode)
            or not stat.S_ISDIR(visible.st_mode)
            or (pinned.st_dev, pinned.st_ino) != (visible.st_dev, visible.st_ino)
        ):
            os.close(descriptor)
            raise DreamArtifactTurnHookError("private artifact directory is unsafe")
        return descriptor

    @classmethod
    def _read_existing(cls, parent: int, name: str, limit: int) -> bytes | None:
        try:
            descriptor = os.open(name, cls._file_flags(), dir_fd=parent)
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise DreamArtifactTurnHookError("private artifact file is unsafe") from exc
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > limit:
                raise DreamArtifactTurnHookError("private artifact file is invalid")
            chunks: list[bytes] = []
            total = 0
            while True:
                chunk = os.read(descriptor, min(65536, limit + 1 - total))
                if not chunk:
                    break
                total += len(chunk)
                if total > limit:
                    raise DreamArtifactTurnHookError(
                        "private artifact file exceeds its limit"
                    )
                chunks.append(chunk)
            return b"".join(chunks)
        finally:
            os.close(descriptor)

    @staticmethod
    def _replace(parent: int, name: str, payload: bytes) -> bool:
        existing = StoryWorkspaceDreamArtifactPublisher._read_existing(
            parent, name, max(len(payload), _SOURCE_MAX_BYTES)
        )
        if existing == payload:
            return False
        temporary = f".{name}.{uuid4().hex}.tmp"
        descriptor = -1
        try:
            descriptor = os.open(
                temporary,
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
                | os.O_NOFOLLOW
                | getattr(os, "O_CLOEXEC", 0),
                0o600,
                dir_fd=parent,
            )
            with os.fdopen(descriptor, "wb", closefd=True) as handle:
                descriptor = -1
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, name, src_dir_fd=parent, dst_dir_fd=parent)
            os.fsync(parent)
            return True
        except OSError as exc:
            raise DreamArtifactTurnHookError(
                "private artifact file cannot be committed"
            ) from exc
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            try:
                os.unlink(temporary, dir_fd=parent)
            except FileNotFoundError:
                pass
            except OSError:
                pass

    @staticmethod
    def _validate_relative_path(value: str) -> tuple[str, ...]:
        pure = PurePosixPath(value)
        parts = pure.parts
        if (
            pure.is_absolute()
            or len(parts) not in {3, 5}
            or parts[0] != "stories"
            or _STORY_SLUG.fullmatch(parts[1]) is None
            or any(_SAFE_SEGMENT.fullmatch(part) is None for part in parts)
        ):
            raise DreamArtifactTurnHookError("private artifact path is invalid")
        if len(parts) == 3 and parts[2] != "project.yaml":
            raise DreamArtifactTurnHookError("private project path is invalid")
        if len(parts) == 5 and (
            parts[2] != "episodes"
            or _EPISODE_CODE.fullmatch(parts[3]) is None
            or parts[4] not in _PRIVATE_FILE_NAMES
            or parts[4] == "project.yaml"
        ):
            raise DreamArtifactTurnHookError("private Episode path is invalid")
        return parts

    def publish(
        self,
        *,
        workflow_run_id: str,
        files: Mapping[str, bytes],
    ) -> bool:
        if _RUN_ID.fullmatch(workflow_run_id) is None:
            raise DreamArtifactTurnHookError("workflow Run identity is invalid")
        if len(files) > STORY_WORKSPACE_DREAM_SOURCE_FILES_MAX:
            raise DreamArtifactTurnHookError("private artifact file count is too large")
        total = sum(len(payload) for payload in files.values())
        if total > _PRIVATE_TOTAL_MAX_BYTES or any(
            len(payload) > _SOURCE_MAX_BYTES for payload in files.values()
        ):
            raise DreamArtifactTurnHookError("private artifact payload is too large")
        normalized = {
            path: (self._validate_relative_path(path), payload)
            for path, payload in sorted(files.items())
        }

        root = os.open(self._workspace_root, self._directory_flags())
        descriptors = [root]
        run_descriptor: int | None = None
        try:
            parent = root
            for component in (".dream", "runtime", "runs", workflow_run_id):
                parent = self._open_directory(parent, component, create=False)
                descriptors.append(parent)
            run_descriptor = parent
            fcntl.flock(run_descriptor, fcntl.LOCK_EX)
            artifact = self._open_directory(run_descriptor, "artifact", create=True)
            descriptors.append(artifact)
            changed = False
            for _path, (parts, payload) in normalized.items():
                parent = artifact
                opened: list[int] = []
                try:
                    for component in parts[:-1]:
                        parent = self._open_directory(parent, component, create=True)
                        opened.append(parent)
                    changed = self._replace(parent, parts[-1], payload) or changed
                finally:
                    for descriptor in reversed(opened):
                        os.close(descriptor)

            manifest_value = {
                "schema_version": "dream-artifact-manifest/v1",
                "workflow_run_id": workflow_run_id,
                "files": [
                    {
                        "path": path,
                        "sha256": hashlib.sha256(payload).hexdigest(),
                        "bytes": len(payload),
                    }
                    for path, (_parts, payload) in normalized.items()
                ],
            }
            manifest_value["revision"] = "sha256:" + hashlib.sha256(
                json.dumps(
                    manifest_value["files"],
                    ensure_ascii=True,
                    separators=(",", ":"),
                    sort_keys=True,
                ).encode("utf-8")
            ).hexdigest()
            manifest = (
                json.dumps(
                    manifest_value,
                    ensure_ascii=False,
                    allow_nan=False,
                    separators=(",", ":"),
                    sort_keys=True,
                ).encode("utf-8")
                + b"\n"
            )
            return self._replace(artifact, "manifest.json", manifest) or changed
        finally:
            if run_descriptor is not None:
                try:
                    fcntl.flock(run_descriptor, fcntl.LOCK_UN)
                except OSError:
                    pass
            for descriptor in reversed(descriptors):
                try:
                    os.close(descriptor)
                except OSError:
                    pass


class DreamArtifactTurnHook:
    """Synchronize one successful root Dream turn into its private Run."""

    def before_main_turn(
        self,
        *,
        context: StoryWorkspaceDreamRunContext,
        actor_id: str | int,
        cwd: str,
    ) -> DreamArtifactTurnTicket:
        try:
            workspace = Path(cwd).resolve(strict=True)
            visible = Path(cwd).lstat()
        except (OSError, RuntimeError) as exc:
            raise DreamArtifactTurnHookError("Dream workspace is unavailable") from exc
        if (
            stat.S_ISLNK(visible.st_mode)
            or not workspace.is_dir()
            or workspace.name != context.thread_id
        ):
            raise DreamArtifactTurnHookError("Dream workspace does not match thread")
        return DreamArtifactTurnTicket(
            context=context,
            actor_id=str(actor_id),
            workspace_root=workspace,
            baseline_files=self._canonical_source_snapshot(workspace),
        )

    def after_main_turn(
        self,
        ticket: DreamArtifactTurnTicket,
    ) -> DreamArtifactTurnResult:
        workflow_run = self._load_authoritative_run(ticket)
        writer = StoryWorkspaceDreamFileWriter(ticket.workspace_root)
        reader = StoryWorkspaceDreamFileReader(ticket.workspace_root)
        try:
            run_file = reader.read_run(
                workflow_run,
                thread_id=ticket.context.thread_id,
            )
        except StoryWorkspaceDreamContractError:
            run_file = writer.write_run(
                workflow_run,
                thread_id=ticket.context.thread_id,
                expected_revision=0,
            )
        if run_file.workflow_run_id != ticket.context.workflow_run_id:
            raise DreamArtifactTurnHookError("Dream run projection changed identity")

        projections = self._collect_stage_projections(ticket.workspace_root)
        projection_by_stage = {
            projection.stage: projection for projection in projections
        }
        changed_stages: list[str] = []
        for stage in STORY_WORKSPACE_DREAM_REQUIRED_STAGES:
            projection = projection_by_stage.get(stage)
            current = reader.read_stage(
                workflow_run,
                stage=stage,
                validate_source_files=False,
            )
            if projection is None:
                if current is not None and writer.delete_stage(
                    workflow_run,
                    stage=stage,
                    expected_revision=current.revision,
                ):
                    changed_stages.append(stage.value)
                continue
            if self._stage_is_current(
                current,
                projection,
            ):
                continue
            expected_revision = current.revision if current is not None else 0
            writer.write_stage(
                workflow_run,
                stage=projection.stage,
                source_files=list(projection.source_files),
                items=list(projection.items),
                expected_revision=expected_revision,
            )
            changed_stages.append(projection.stage.value)

        private_files = self._collect_private_artifact_files(ticket.workspace_root)
        private_changed = StoryWorkspaceDreamArtifactPublisher(
            ticket.workspace_root
        ).publish(
            workflow_run_id=ticket.context.workflow_run_id,
            files=private_files,
        )
        if set(projection_by_stage) == set(
            STORY_WORKSPACE_DREAM_REQUIRED_STAGES
        ):
            self._record_output_ready(ticket, workflow_run)
        episode_authority = self._ensure_first_episode_binding(
            ticket,
            workflow_run,
            private_files=private_files,
        )
        story_index_status = self._materialize_story_index(
            ticket,
            workflow_run,
            episode_authority=episode_authority,
        )
        latest_snapshot = self._canonical_source_snapshot(ticket.workspace_root)
        before = dict(ticket.baseline_files)
        after = dict(latest_snapshot)
        changed_source_files = tuple(
            sorted(
                path
                for path in set(before) | set(after)
                if before.get(path) != after.get(path)
            )
        )
        return DreamArtifactTurnResult(
            changed_stages=tuple(changed_stages),
            private_artifact_changed=private_changed,
            private_files=tuple(sorted(private_files)),
            changed_source_files=changed_source_files,
            episode_bound=episode_authority is not None,
            story_index_status=story_index_status,
        )

    @staticmethod
    def _materialize_story_index(
        ticket: DreamArtifactTurnTicket,
        workflow_run: WorkflowRun,
        *,
        episode_authority: StoryWorkspaceEpisodeAuthority | None,
    ) -> str | None:
        """Project current Project/Episode facts for the page after every turn.

        A Project can exist before ``script.md`` does.  That ordinary partial
        workspace is not a synchronization failure and remains unindexed until
        a later successful turn supplies the required Episode file.  Once the
        surface is indexable, every successful turn performs the same
        idempotent upsert so edits such as ``project_name`` reach PostgreSQL
        without a user-facing reconcile button.
        """

        if episode_authority is None:
            return None
        try:
            surface = StoryWorkspaceEpisodeArtifactService(
                ticket.workspace_root
            ).read_surface(
                ticket.context.workflow_run_id,
                episode_authority=episode_authority,
            )
        except StoryWorkspaceEpisodeArtifactError as exc:
            raise DreamArtifactTurnHookError(
                "Dream Episode projection cannot be read"
            ) from exc

        db = database.get_db()
        try:
            result = ArtifactStoryIndexService().materialize(
                db=db,
                workspace_root=ticket.workspace_root,
                workflow_run=workflow_run,
                actor_id=ticket.actor_id,
                thread_id=ticket.context.thread_id,
                episode_authority=episode_authority,
                refreshed_surface=surface,
            )
        finally:
            db.close()

        status = str(result.get("status") or "failed")
        if status in {"created", "updated", "same_revision"}:
            return status
        error_code = str(result.get("errorCode") or "story_index_write_failed")
        if error_code == "artifact_missing":
            return "not_ready"
        raise DreamArtifactTurnHookError(
            f"Dream Story projection failed: {error_code}"
        )

    @staticmethod
    def _record_output_ready(
        ticket: DreamArtifactTurnTicket,
        workflow_run: WorkflowRun,
    ) -> None:
        db = database.get_db()
        try:
            asyncio.run(
                StoryWorkspaceDreamWorkflowLifecycleService(
                    db,
                    token_secret=story_workspace_workflow_token_secret(),
                ).record_output_ready(
                    ticket.context.workflow_run_id,
                    AuthenticatedActorContext(
                        actor_id=ticket.actor_id,
                        workspace_id=workflow_run.workspace_id,
                    ),
                    normalized_result_ready=True,
                )
            )
        finally:
            db.close()

    @staticmethod
    def _decode_source_metadata(raw: object) -> dict[str, Any]:
        if isinstance(raw, dict):
            return dict(raw)
        if not isinstance(raw, str):
            raise DreamArtifactTurnHookError("Dream launch metadata is unavailable")
        try:
            value = json.loads(raw)
        except (TypeError, ValueError) as exc:
            raise DreamArtifactTurnHookError(
                "Dream launch metadata is unavailable"
            ) from exc
        if not isinstance(value, dict):
            raise DreamArtifactTurnHookError("Dream launch metadata is unavailable")
        return value

    @classmethod
    def _ensure_first_episode_binding(
        cls,
        ticket: DreamArtifactTurnTicket,
        workflow_run: WorkflowRun,
        *,
        private_files: Mapping[str, bytes],
    ) -> StoryWorkspaceEpisodeAuthority | None:
        binding_service = StoryWorkspaceEpisodeBindingService(ticket.workspace_root)
        story_slug = binding_service.discover_unique_canonical_project_story_slug()
        if story_slug is None:
            return None
        episode_prefix = f"stories/{story_slug}/episodes/EP01/"
        if not any(path.startswith(episode_prefix) for path in private_files):
            return None
        source_message_id = workflow_run.source_message_id
        if not isinstance(source_message_id, str) or not source_message_id:
            raise DreamArtifactTurnHookError("Dream launch source is unavailable")

        db = database.get_db()
        try:
            row = db.execute(
                "SELECT metadata FROM chat_message WHERE id = %s "
                "AND thread_id = %s LIMIT 1",
                (source_message_id, ticket.context.thread_id),
            ).fetchone()
            if db.in_transaction:
                db.rollback()
            if row is None:
                raise DreamArtifactTurnHookError("Dream launch source is unavailable")
            raw_metadata = row["metadata"]
            metadata = cls._decode_source_metadata(raw_metadata)
            dream_context = metadata.get("dreamContext")
            goal = metadata.get("goal")
            trusted_story_slug = metadata.get("projectStorySlug")
            if trusted_story_slug is None and isinstance(goal, str) and goal:
                trusted_story_slug = story_workspace_canonical_project_fallback_slug(
                    goal
                )
                metadata["projectStorySlug"] = trusted_story_slug
            if not (
                metadata.get("kind") == "story-workspace-dream-launch"
                and metadata.get("schemaVersion") == "story-workspace-dream-launch/v1"
                and str(metadata.get("actorId")) == ticket.actor_id
                and metadata.get("workflowRunId") == ticket.context.workflow_run_id
                and metadata.get("threadId") == ticket.context.thread_id
                and isinstance(dream_context, dict)
                and dream_context.get("workflow_run_id")
                == ticket.context.workflow_run_id
                and dream_context.get("thread_id") == ticket.context.thread_id
                and dream_context.get("deck_plugin_id")
                == ticket.context.deck_plugin_id
                and dream_context.get("deck_plugin_version")
                == ticket.context.deck_plugin_version
                and dream_context.get("runtime_plugin_lock_id")
                == ticket.context.runtime_plugin_lock_id
                and isinstance(trusted_story_slug, str)
                and trusted_story_slug == story_slug
            ):
                raise DreamArtifactTurnHookError("Dream launch authority changed")

            authority_value = metadata.get("story_workspace_episode_identity")
            authority = StoryWorkspaceEpisodeAuthority.parse(
                authority_value,
                expected_run_id=ticket.context.workflow_run_id,
            )
            if authority is None:
                if authority_value is not None:
                    raise DreamArtifactTurnHookError(
                        "Dream Episode authority is malformed"
                    )
                episode_uid = uuid4().hex
                metadata["story_workspace_episode_identity"] = {
                    "schema": "story-workspace-episode-authority/v1",
                    "workflow_run_id": ticket.context.workflow_run_id,
                    "episode_uid": episode_uid,
                    "story_slug": story_slug,
                    "episode_code": "EP01",
                }
                encoded = json.dumps(
                    metadata,
                    ensure_ascii=False,
                    allow_nan=False,
                    separators=(",", ":"),
                    sort_keys=True,
                )
                updated = db.execute(
                    "UPDATE chat_message SET metadata = %s WHERE id = %s "
                    "AND metadata = %s",
                    (encoded, source_message_id, raw_metadata),
                )
                if updated.rowcount != 1:
                    db.rollback()
                    raise DreamArtifactTurnHookError(
                        "Dream Episode authority CAS failed"
                    )
                db.commit()
            else:
                episode_uid = authority.episode_uid
                if authority.story_slug != story_slug or authority.episode_code != "EP01":
                    raise DreamArtifactTurnHookError(
                        "Dream Episode authority conflicts with canonical project"
                    )
                if metadata.get("projectStorySlug") != trusted_story_slug:
                    metadata["projectStorySlug"] = trusted_story_slug
                    encoded = json.dumps(
                        metadata,
                        ensure_ascii=False,
                        allow_nan=False,
                        separators=(",", ":"),
                        sort_keys=True,
                    )
                    updated = db.execute(
                        "UPDATE chat_message SET metadata = %s WHERE id = %s "
                        "AND metadata = %s",
                        (encoded, source_message_id, raw_metadata),
                    )
                    if updated.rowcount != 1:
                        db.rollback()
                        raise DreamArtifactTurnHookError(
                            "Dream project authority CAS failed"
                        )
                    db.commit()
        finally:
            db.close()

        binding_service.bind_first_episode(
            StoryWorkspaceEpisodeBindingContext(
                workflow_run_id=ticket.context.workflow_run_id,
                trusted_project_story_slug=story_slug,
                locked_context_story_slug=trusted_story_slug,
                run_provenance_story_slug=trusted_story_slug,
                episode_uid=episode_uid,
            )
        )
        return StoryWorkspaceEpisodeAuthority(
            workflow_run_id=ticket.context.workflow_run_id,
            episode_uid=episode_uid,
            story_slug=story_slug,
            episode_code="EP01",
        )

    @staticmethod
    def _load_authoritative_run(ticket: DreamArtifactTurnTicket) -> WorkflowRun:
        db = database.get_db()
        try:
            row = db.execute(
                "SELECT workspace_id FROM workflow_runs "
                "WHERE id = %s AND created_by = %s "
                "AND source_voice_thread_id = %s LIMIT 1",
                (
                    ticket.context.workflow_run_id,
                    ticket.actor_id,
                    ticket.context.thread_id,
                ),
            ).fetchone()
            if row is None:
                raise DreamArtifactTurnHookError("Dream Run authority is unavailable")
            run = WorkflowRunService(
                db,
                token_secret=story_workspace_workflow_token_secret(),
            ).read_run(
                ticket.context.workflow_run_id,
                AuthenticatedActorContext(
                    actor_id=ticket.actor_id,
                    workspace_id=str(row["workspace_id"]),
                ),
            )
        finally:
            db.close()
        frozen = (
            run.source_voice_thread_id,
            run.deck_plugin_id,
            run.deck_plugin_version,
            run.deck_plugin_binding_id,
            run.binding_revision,
            run.deck_runtime_snapshot_id,
            run.runtime_plugin_lock_id,
        )
        expected = (
            ticket.context.thread_id,
            ticket.context.deck_plugin_id,
            ticket.context.deck_plugin_version,
            ticket.context.deck_plugin_binding_id,
            ticket.context.binding_revision,
            ticket.context.deck_runtime_snapshot_id,
            ticket.context.runtime_plugin_lock_id,
        )
        if frozen != expected:
            raise DreamArtifactTurnHookError("Dream Run frozen authority changed")
        return run

    @classmethod
    def _safe_file(cls, workspace: Path, relative_path: str) -> bytes:
        pure = PurePosixPath(relative_path)
        if pure.is_absolute() or any(
            part in {"", ".", ".."} or "\\" in part or "\x00" in part
            for part in pure.parts
        ):
            raise DreamArtifactTurnHookError("workbench source path is invalid")
        target = workspace.joinpath(*pure.parts)
        try:
            visible = target.lstat()
            resolved = target.resolve(strict=True)
            metadata = resolved.stat(follow_symlinks=False)
        except (OSError, RuntimeError) as exc:
            raise DreamArtifactTurnHookError("workbench source is unavailable") from exc
        if (
            stat.S_ISLNK(visible.st_mode)
            or not stat.S_ISREG(metadata.st_mode)
            or not resolved.is_relative_to(workspace)
            or metadata.st_size > _SOURCE_MAX_BYTES
        ):
            raise DreamArtifactTurnHookError("workbench source is unsafe")
        try:
            payload = resolved.read_bytes()
        except OSError as exc:
            raise DreamArtifactTurnHookError("workbench source cannot be read") from exc
        if len(payload) != metadata.st_size:
            raise DreamArtifactTurnHookError("workbench source changed during read")
        return payload

    @classmethod
    def _canonical_source_snapshot(
        cls,
        workspace: Path,
    ) -> tuple[tuple[str, str], ...]:
        """Capture a bounded before/after digest without interpreting content."""

        candidates: set[str] = set()
        for directory in ("assets/characters", "assets/scenes"):
            root = workspace / directory
            if not root.exists():
                continue
            try:
                for path in root.iterdir():
                    if path.suffix.lower() in {".md", ".yaml", ".yml"}:
                        candidates.add(path.relative_to(workspace).as_posix())
            except OSError as exc:
                raise DreamArtifactTurnHookError(
                    "canonical asset directory cannot be inspected"
                ) from exc
        stories = workspace / "stories"
        if stories.exists():
            try:
                story_roots = tuple(stories.iterdir())
            except OSError as exc:
                raise DreamArtifactTurnHookError(
                    "canonical stories directory cannot be inspected"
                ) from exc
            for story in story_roots:
                if story.is_symlink() or not story.is_dir() or _STORY_SLUG.fullmatch(story.name) is None:
                    continue
                project = story / "project.yaml"
                if project.exists():
                    candidates.add(project.relative_to(workspace).as_posix())
                episodes = story / "episodes"
                if not episodes.exists() or episodes.is_symlink() or not episodes.is_dir():
                    continue
                try:
                    episode_roots = tuple(episodes.iterdir())
                except OSError as exc:
                    raise DreamArtifactTurnHookError(
                        "canonical Episode directory cannot be inspected"
                    ) from exc
                for episode in episode_roots:
                    if (
                        episode.is_symlink()
                        or not episode.is_dir()
                        or _EPISODE_CODE.fullmatch(episode.name) is None
                    ):
                        continue
                    for name in _PRIVATE_FILE_NAMES - {"project.yaml"}:
                        artifact = episode / name
                        if artifact.exists():
                            candidates.add(artifact.relative_to(workspace).as_posix())
        if len(candidates) > STORY_WORKSPACE_DREAM_SOURCE_FILES_MAX:
            raise DreamArtifactTurnHookError("canonical source count exceeds contract")
        return tuple(
            (
                relative,
                "sha256:" + hashlib.sha256(cls._safe_file(workspace, relative)).hexdigest(),
            )
            for relative in sorted(candidates)
        )

    @staticmethod
    def _frontmatter(payload: bytes) -> tuple[dict[str, Any], str]:
        try:
            text = payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise DreamArtifactTurnHookError("workbench source is not UTF-8") from exc
        lines = text.splitlines()
        if not lines or lines[0].strip() != "---":
            return {}, text
        closing = next(
            (index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"),
            None,
        )
        if closing is None:
            try:
                parsed = yaml.safe_load("\n".join(lines[1:])) or {}
            except yaml.YAMLError:
                return {}, text
            if isinstance(parsed, dict):
                return parsed, ""
            return {}, text
        try:
            parsed = yaml.safe_load("\n".join(lines[1:closing])) or {}
        except yaml.YAMLError as exc:
            raise DreamArtifactTurnHookError("workbench frontmatter is invalid") from exc
        if not isinstance(parsed, dict):
            raise DreamArtifactTurnHookError("workbench frontmatter must be a mapping")
        return parsed, "\n".join(lines[closing + 1 :])

    @staticmethod
    def _plain_mapping(payload: bytes) -> dict[str, Any]:
        try:
            parsed = yaml.safe_load(payload.decode("utf-8")) or {}
        except (UnicodeDecodeError, yaml.YAMLError):
            return {}
        return parsed if isinstance(parsed, dict) else {}

    @staticmethod
    def _loose_document_metadata(body: str) -> dict[str, str]:
        """Read bounded top-level identity fields from Markdown-like assets."""

        values: dict[str, str] = {}
        for raw in body.splitlines()[:80]:
            if raw != raw.lstrip() or raw.lstrip().startswith(("-", "*", ">")):
                continue
            match = re.fullmatch(
                r"(id|name|char_id|char_name|character_id|character_name|"
                r"scene_id|scene_name|display_name)\s*:\s*(.+)",
                raw.strip(),
            )
            if match is None:
                continue
            value = match.group(2).strip().strip('"\'')
            if value:
                values.setdefault(match.group(1), value[:1000])
        return values

    @staticmethod
    def _first_heading(body: str) -> str | None:
        for raw in body.splitlines():
            value = raw.strip()
            if value.startswith("# "):
                heading = value[2:].strip()
                for prefix in ("场景：", "场景:", "角色：", "角色:"):
                    if heading.startswith(prefix):
                        heading = heading[len(prefix) :].strip()
                return heading[:200] or None
        return None

    @staticmethod
    def _first_body_text(body: str) -> str | None:
        values: list[str] = []
        for raw in body.splitlines():
            line = raw.strip()
            if not line or line.startswith(("#", "---", "```")):
                if values:
                    break
                continue
            if line.startswith(("- ", "* ", "> ")):
                line = line[2:].strip()
            values.append(line)
            if sum(len(value) for value in values) >= 500:
                break
        value = " ".join(values).strip()
        return value[:4000] or None

    @staticmethod
    def _relation_strings(value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        relations: list[str] = []
        for item in value:
            if isinstance(item, str):
                candidate = item.strip()
            elif isinstance(item, dict):
                identity = item.get("char_id") or item.get("scene_id") or item.get("ref")
                detail = item.get("relation") or item.get("dynamic") or item.get("action")
                candidate = ": ".join(
                    part
                    for part in (
                        str(identity or "").strip(),
                        str(detail or "").strip(),
                    )
                    if part
                )
            else:
                candidate = ""
            if candidate and candidate not in relations:
                relations.append(candidate[:1000])
            if len(relations) >= STORY_WORKSPACE_DREAM_RELATIONS_MAX:
                break
        return relations

    @classmethod
    def _asset_projection(
        cls,
        workspace: Path,
        *,
        stage: StoryWorkspaceDreamStage,
        directory: str,
        identity_fields: tuple[str, ...],
        name_fields: tuple[str, ...],
    ) -> _StageProjection | None:
        root = workspace / directory
        if not root.exists():
            return None
        try:
            visible = root.lstat()
            resolved = root.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise DreamArtifactTurnHookError("asset directory is unavailable") from exc
        if (
            stat.S_ISLNK(visible.st_mode)
            or not resolved.is_dir()
            or not resolved.is_relative_to(workspace)
        ):
            raise DreamArtifactTurnHookError("asset directory is unsafe")
        candidates = sorted(
            path
            for path in resolved.iterdir()
            if path.suffix.lower() in {".md", ".yaml", ".yml"}
        )
        if not candidates:
            return None
        if len(candidates) > STORY_WORKSPACE_DREAM_SOURCE_FILES_MAX:
            raise DreamArtifactTurnHookError("asset file count exceeds contract")
        source_files: list[str] = []
        items: list[dict[str, object]] = []
        for candidate in candidates:
            relative = candidate.relative_to(workspace).as_posix()
            payload = cls._safe_file(workspace, relative)
            metadata, body = cls._frontmatter(payload)
            # Stage DTOs strip surrounding whitespace. Normalize before both
            # comparison and persistence so an unchanged trailing newline does
            # not advance every asset stage revision on each successful turn.
            source_content = payload.decode("utf-8").strip() or None
            if not metadata:
                metadata = cls._plain_mapping(payload)
            if not metadata:
                metadata = cls._loose_document_metadata(body)
            heading = cls._first_heading(body)
            identity = next(
                (
                    str(metadata.get(field) or "").strip()
                    for field in identity_fields
                    if metadata.get(field)
                ),
                candidate.stem,
            )
            display_name = next(
                (
                    str(metadata.get(field) or "").strip()
                    for field in name_fields
                    if metadata.get(field)
                ),
                heading or candidate.stem,
            )
            if not identity or len(identity) > 128 or not display_name:
                raise DreamArtifactTurnHookError("asset identity is invalid")
            summary_parts: list[str] = []
            for key in ("occupation", "type", "location_class"):
                value = metadata.get(key)
                if isinstance(value, (str, int, float)) and str(value).strip():
                    summary_parts.append(str(value).strip())
            personality = metadata.get("personality")
            if isinstance(personality, dict) and isinstance(personality.get("core_traits"), list):
                traits = "、".join(
                    str(value).strip()
                    for value in personality["core_traits"]
                    if str(value).strip()
                )
                if traits:
                    summary_parts.append(traits)
            body_summary = cls._first_body_text(body)
            if body_summary:
                summary_parts.append(body_summary)
            relationships = metadata.get("relationships")
            if relationships is None:
                relationships = metadata.get("relations")
            source_files.append(relative)
            items.append(
                {
                    "entity_id": identity,
                    "display_name": display_name[:200],
                    "summary": " · ".join(summary_parts)[:4000] or None,
                    "content": source_content,
                    "source_file": relative,
                    "relations": cls._relation_strings(relationships),
                }
            )
        if len(items) > STORY_WORKSPACE_DREAM_ITEMS_MAX:
            raise DreamArtifactTurnHookError("asset item count exceeds contract")
        return _StageProjection(stage, tuple(source_files), tuple(items))

    @classmethod
    def _storyboard_projection(cls, workspace: Path) -> _StageProjection | None:
        stories = workspace / "stories"
        if not stories.exists():
            return None
        try:
            story_roots = sorted(path for path in stories.iterdir() if path.is_dir())
        except OSError as exc:
            raise DreamArtifactTurnHookError("stories directory cannot be listed") from exc
        candidates: list[Path] = []
        for story in story_roots:
            if story.is_symlink() or _STORY_SLUG.fullmatch(story.name) is None:
                continue
            episodes = story / "episodes"
            if not episodes.is_dir() or episodes.is_symlink():
                continue
            for episode in sorted(episodes.iterdir()):
                if (
                    episode.is_symlink()
                    or not episode.is_dir()
                    or _EPISODE_CODE.fullmatch(episode.name) is None
                ):
                    continue
                storyboard = episode / "storyboard.yaml"
                if storyboard.exists():
                    candidates.append(storyboard)
        if not candidates:
            return None
        if len(candidates) > STORY_WORKSPACE_DREAM_SOURCE_FILES_MAX:
            raise DreamArtifactTurnHookError("storyboard file count exceeds contract")
        source_files: list[str] = []
        items: list[dict[str, object]] = []
        for candidate in candidates:
            relative = candidate.relative_to(workspace).as_posix()
            payload = cls._safe_file(workspace, relative)
            metadata, body = cls._frontmatter(payload)
            if not metadata:
                metadata = cls._plain_mapping(payload)
            episode_code = candidate.parent.name
            shot_count = metadata.get("total_shots")
            duration = metadata.get("total_duration_sec")
            detail = []
            if isinstance(shot_count, int) and not isinstance(shot_count, bool):
                detail.append(f"{shot_count} 镜")
            if isinstance(duration, (int, float)) and not isinstance(duration, bool):
                detail.append(f"{duration:g} 秒")
            summary = cls._first_body_text(body)
            if detail:
                summary = "、".join(detail) + (f"。{summary}" if summary else "")
            source_files.append(relative)
            items.append(
                {
                    "entity_id": episode_code,
                    "display_name": f"{episode_code} 分镜",
                    "summary": (summary or None),
                    "source_file": relative,
                    "relations": [],
                }
            )
        return _StageProjection(
            StoryWorkspaceDreamStage.STORYBOARDS,
            tuple(source_files),
            tuple(items),
        )

    @classmethod
    def _collect_stage_projections(cls, workspace: Path) -> tuple[_StageProjection, ...]:
        values = (
            cls._asset_projection(
                workspace,
                stage=StoryWorkspaceDreamStage.CHARACTERS,
                directory="assets/characters",
                identity_fields=("char_id", "character_id", "id"),
                name_fields=("char_name", "character_name", "name", "display_name"),
            ),
            cls._asset_projection(
                workspace,
                stage=StoryWorkspaceDreamStage.SCENES,
                directory="assets/scenes",
                identity_fields=("scene_id", "id"),
                name_fields=("name", "scene_name", "display_name"),
            ),
            cls._storyboard_projection(workspace),
        )
        return tuple(value for value in values if value is not None)

    @staticmethod
    def _stage_is_current(
        current: Any | None,
        projection: _StageProjection,
    ) -> bool:
        if current is None or tuple(current.source_files) != projection.source_files:
            return False
        current_items = tuple(item.model_dump() for item in current.items)
        projected_items = tuple(
            StoryWorkspaceDreamStageItem.model_validate(item).model_dump()
            for item in projection.items
        )
        return current_items == projected_items

    @classmethod
    def _collect_private_artifact_files(cls, workspace: Path) -> dict[str, bytes]:
        stories = workspace / "stories"
        if not stories.exists():
            return {}
        try:
            candidates = sorted(path for path in stories.iterdir() if path.is_dir())
        except OSError as exc:
            raise DreamArtifactTurnHookError("stories directory cannot be listed") from exc
        projects: list[tuple[Path, bytes]] = []
        for story in candidates:
            if story.is_symlink() or _STORY_SLUG.fullmatch(story.name) is None:
                continue
            relative = f"stories/{story.name}/project.yaml"
            project_path = story / "project.yaml"
            if not project_path.exists():
                continue
            payload = cls._safe_file(workspace, relative)
            try:
                text = payload.decode("utf-8")
                StoryWorkspaceEpisodeBindingService.read_canonical_project_id_from_text(
                    text,
                    candidate=story.name,
                )
            except (UnicodeDecodeError, StoryWorkspaceEpisodeBindingError) as exc:
                raise DreamArtifactTurnHookError(
                    "canonical project identity is invalid"
                ) from exc
            projects.append((story, payload))
        if not projects:
            return {}
        if len(projects) != 1:
            raise DreamArtifactTurnHookError(
                "Dream Run must resolve exactly one canonical project"
            )
        story, project_payload = projects[0]
        values = {f"stories/{story.name}/project.yaml": project_payload}
        episodes = story / "episodes"
        if not episodes.exists():
            return values
        if episodes.is_symlink() or not episodes.is_dir():
            raise DreamArtifactTurnHookError("canonical Episode directory is unsafe")
        for episode in sorted(episodes.iterdir()):
            if (
                episode.is_symlink()
                or not episode.is_dir()
                or _EPISODE_CODE.fullmatch(episode.name) is None
            ):
                continue
            for filename in sorted(_PRIVATE_FILE_NAMES - {"project.yaml"}):
                relative = f"stories/{story.name}/episodes/{episode.name}/{filename}"
                source = episode / filename
                if not source.exists():
                    continue
                payload = cls._safe_file(workspace, relative)
                values[relative] = payload
        return values


__all__ = [
    "DreamArtifactTurnHook",
    "DreamArtifactTurnHookError",
    "DreamArtifactTurnResult",
    "DreamArtifactTurnTicket",
    "StoryWorkspaceDreamArtifactPublisher",
]
