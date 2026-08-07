"""Controlled MCP handlers for Story Workspace Dream runtime writes.

The Claude Agent supplies only the target run, stage payload, and CAS revision.
Actor and Chat-thread identity come exclusively from the host-injected stdio
environment.  Frozen run provenance is loaded from the authoritative
``WorkflowRun`` on every call and is never accepted as a tool argument.
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
import sqlite3
import stat
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, TypeVar
from uuid import uuid4

from models.workflow_run import AuthenticatedActorContext, WorkflowRun
from services.story_workspace.dream_file_service import (
    StoryWorkspaceDreamFileWriter,
    WorkflowRun as DreamFileWorkflowRun,
)
from services.story_workspace.episode_action_service import (
    StoryWorkspaceEpisodeNextActionResolver,
    StoryWorkspaceEpisodeWorkflowFactService,
)
from services.story_workspace.episode_artifact_service import (
    StoryWorkspaceEpisodeArtifactService,
    StoryWorkspaceEpisodeAuthority,
)
from services.story_workspace.episode_binding_service import (
    StoryWorkspaceEpisodeBindingContext,
    StoryWorkspaceEpisodeBindingService,
)
from services.story_workspace.episode_completion_validator import (
    StoryWorkspaceEpisodeCompletionContractError,
    StoryWorkspaceEpisodeCompletionValidator,
)
from services.story_workspace.dream_reentry_service import (
    StoryWorkspaceDreamReentryService,
)
from services.workflow.run_service import WorkflowRunService
from story_workspace.contracts import (
    StoryWorkspaceDreamRunToolInput,
    StoryWorkspaceDreamStageToolInput,
    StoryWorkspaceEpisodeAction,
    StoryWorkspaceEpisodeBindingToolInput,
    StoryWorkspaceEpisodeWorkflowCompletionToolInput,
)

from .workspace import get_workspace_root


_logger = logging.getLogger(__name__)

_TRUSTED_USER_ENV = "INK_AGENT_USER_ID"
_TRUSTED_THREAD_ENV = "INK_AGENT_THREAD_ID"
_TRUSTED_WORKFLOW_RUN_ENV = "INK_AGENT_WORKFLOW_RUN_ID"
_TRUSTED_MESSAGE_ENV = "INK_AGENT_STORY_WORKSPACE_MESSAGE_ID"
_ResultT = TypeVar("_ResultT")


@dataclass(frozen=True)
class StoryWorkspaceToolSpec:
    """Server-owned schema and behavior hints for one Agent-visible tool."""

    description: str
    input_schema: dict[str, Any]


STORY_WORKSPACE_DREAM_TOOL_SPECS: dict[str, StoryWorkspaceToolSpec] = {
    "write_dream_run": StoryWorkspaceToolSpec(
        description=(
            "Initialize or CAS-update the current Story Workspace Dream run metadata. "
            "This writes only the server-controlled .dream runtime protocol; actor, "
            "thread, routing, filenames, and frozen source provenance are host-derived. "
            "It does not advance the WorkflowRun state machine."
        ),
        input_schema=StoryWorkspaceDreamRunToolInput.model_json_schema(by_alias=True),
    ),
    "write_dream_stage": StoryWorkspaceToolSpec(
        description=(
            "CAS-write one canonical Dream stage projection from existing workspace "
            "source files. This writes only the server-controlled .dream runtime "
            "protocol; identity, routing, filename, schema, and provenance are "
            "host-derived. It does not advance the WorkflowRun state machine."
        ),
        input_schema=StoryWorkspaceDreamStageToolInput.model_json_schema(by_alias=True),
    ),
    "bind_first_episode": StoryWorkspaceToolSpec(
        description=(
            "CAS-bind the canonical first Episode after the current controlled "
            "Story Workspace action. The server requires exactly one canonical "
            "project.yaml whose project_id matches its directory; actor, thread, "
            "run, story, message, Episode code/root/UID and launch provenance are "
            "server-owned."
        ),
        input_schema=StoryWorkspaceEpisodeBindingToolInput.model_json_schema(
            by_alias=True
        ),
    ),
    "record_episode_workflow_completion": StoryWorkspaceToolSpec(
        description=(
            "CAS-record completion of the current allowlisted Episode action after "
            "canonical files have been written. This stores only technical revision "
            "evidence and never owns Episode creative content."
        ),
        input_schema=(
            StoryWorkspaceEpisodeWorkflowCompletionToolInput.model_json_schema(
                by_alias=True
            )
        ),
    ),
}


def story_workspace_allowed_tool_names() -> list[str]:
    """Return the complete Story Workspace MCP allowlist entries."""

    return [
        f"mcp__story_workspace__{name}"
        for name in STORY_WORKSPACE_DREAM_TOOL_SPECS
    ]


def _trusted_actor_and_thread() -> tuple[int, str]:
    raw_actor = os.getenv(_TRUSTED_USER_ENV, "").strip()
    thread_id = os.getenv(_TRUSTED_THREAD_ENV, "").strip()
    if not raw_actor.isdigit() or int(raw_actor) <= 0:
        raise PermissionError("trusted actor context is unavailable")
    if (
        not thread_id
        or len(thread_id) > 255
        or Path(thread_id).parts != (thread_id,)
        or thread_id in {".", ".."}
    ):
        raise PermissionError("trusted thread context is unavailable")
    return int(raw_actor), thread_id


def _require_trusted_workflow_run(workflow_run_id: str) -> None:
    trusted_run_id = os.getenv(_TRUSTED_WORKFLOW_RUN_ENV, "").strip()
    if not trusted_run_id or workflow_run_id != trusted_run_id:
        raise PermissionError("trusted workflow run context is unavailable")


def _trusted_message_id() -> str:
    message_id = os.getenv(_TRUSTED_MESSAGE_ENV, "").strip()
    if not re.fullmatch(r"dream_agent_[0-9a-f]{64}", message_id):
        raise PermissionError("trusted Story Workspace message is unavailable")
    return message_id


def _read_actor_scoped_run(
    db: sqlite3.Connection,
    workflow_run_id: str,
    actor_context: AuthenticatedActorContext,
) -> WorkflowRun:
    """Use WorkflowRunService's actor-scoped read path without its DDL constructor.

    ``WorkflowRunService.__init__`` activates run/session tables for write-side
    workflows.  An MCP read must not perform DDL, so this read-only adapter
    supplies only the database dependency required by ``read_run``.
    """

    service = WorkflowRunService.__new__(WorkflowRunService)
    service.db = db
    db.row_factory = sqlite3.Row
    return service.read_run(workflow_run_id, actor_context)


def _existing_thread_workspace(thread_id: str) -> Path:
    """Resolve one existing direct child of the workspace root without creating it."""

    supplied_root = Path(get_workspace_root())
    resolved_root = supplied_root.resolve(strict=True)
    if not resolved_root.is_dir():
        raise PermissionError("workspace root is unavailable")

    supplied_workspace = supplied_root / thread_id
    metadata = supplied_workspace.lstat()
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise PermissionError("thread workspace is unavailable")
    resolved_workspace = supplied_workspace.resolve(strict=True)
    if (
        resolved_workspace.parent != resolved_root
        or not resolved_workspace.is_relative_to(resolved_root)
    ):
        raise PermissionError("thread workspace is unavailable")
    return resolved_workspace


def _with_authoritative_context(
    workflow_run_id: str,
    operation: Callable[[StoryWorkspaceDreamFileWriter, WorkflowRun], _ResultT],
) -> _ResultT:
    """Open one DB connection, resolve trusted context, then execute a write."""

    import database  # Runtime import keeps the stdio child tied to host DB config.

    actor_id, thread_id = _trusted_actor_and_thread()
    db = database.get_db()
    try:
        db.row_factory = sqlite3.Row
        workspace_row = db.execute(
            "SELECT workflow_runs.workspace_id AS id "
            "FROM workflow_runs "
            "INNER JOIN story_workspace_workspaces "
            "ON story_workspace_workspaces.id = workflow_runs.workspace_id "
            "WHERE workflow_runs.id = ? "
            "AND story_workspace_workspaces.owner_id = ? "
            "LIMIT 1",
            (workflow_run_id, actor_id),
        ).fetchone()
        if workspace_row is None:
            raise PermissionError("actor workspace is unavailable")
        actor_context = AuthenticatedActorContext(
            workspace_id=str(workspace_row["id"]),
            actor_id=str(actor_id),
        )
        workflow_run = _read_actor_scoped_run(
            db,
            workflow_run_id,
            actor_context,
        )
        # The backend supports both ``backend.*`` and backend-root imports.
        # Normalize the authoritative model at this boundary so a process that
        # loaded both package spellings still satisfies the writer's strict
        # nominal ``WorkflowRun`` trust check.
        if not isinstance(workflow_run, DreamFileWorkflowRun):
            workflow_run = DreamFileWorkflowRun.model_validate(
                workflow_run.model_dump(mode="python")
            )
        if workflow_run.source_voice_thread_id != thread_id:
            raise PermissionError("run and trusted thread do not match")
        thread_row = db.execute(
            "SELECT id FROM chat_thread WHERE id = ? AND user_id = ?",
            (thread_id, actor_id),
        ).fetchone()
        if thread_row is None or str(thread_row["id"]) != thread_id:
            raise PermissionError("thread ownership is unavailable")

        workspace = _existing_thread_workspace(thread_id)
        writer = StoryWorkspaceDreamFileWriter(workspace)
        if Path(writer.workspace_root) != workspace:
            raise PermissionError("writer workspace binding changed")
        return operation(writer, workflow_run)
    finally:
        db.close()


def _active_episode_action_provenance(
    db: sqlite3.Connection,
    *,
    message_id: str,
    actor_id: int,
    thread_id: str,
    workflow_run_id: str,
) -> dict[str, Any]:
    row = db.execute(
        "SELECT metadata FROM chat_message "
        "WHERE id = ? AND thread_id = ? AND role = 'user' LIMIT 1",
        (message_id, thread_id),
    ).fetchone()
    if row is None:
        raise PermissionError("Story Workspace action provenance is unavailable")
    try:
        metadata = json.loads(row["metadata"] or "{}")
    except (TypeError, ValueError) as exc:
        raise PermissionError(
            "Story Workspace action provenance is unavailable"
        ) from exc
    action = metadata.get("story_workspace_episode_action")
    if (
        not isinstance(metadata, dict)
        or metadata.get("kind") != "story-workspace-dream-agent-user"
        or metadata.get("story_workspace_run_id") != workflow_run_id
        or metadata.get("thread_id") != thread_id
        or str(metadata.get("actor_id") or "") != str(actor_id)
        or metadata.get("dispatch_status") != "dispatching"
        or not isinstance(metadata.get("dispatch_claim_id"), str)
        or not isinstance(metadata.get("dispatch_claim_lease_until"), (int, float))
        or isinstance(metadata.get("dispatch_claim_lease_until"), bool)
        or not math.isfinite(float(metadata["dispatch_claim_lease_until"]))
        or float(metadata["dispatch_claim_lease_until"]) <= time.time()
        or not isinstance(action, dict)
        or set(action)
        != {
            "schema",
            "action",
            "episode_uid",
            "input_revision",
            "expected_facts_revision",
            "expected_manifest_revision",
            "expected_workflow_revision",
        }
        or action.get("schema") != "story-workspace-episode-action/v1"
    ):
        raise PermissionError("Story Workspace action provenance is unavailable")
    return action


def _with_authoritative_episode_context(
    workflow_run_id: str,
    operation: Callable[
        [
            sqlite3.Connection,
            Path,
            WorkflowRun,
            int,
            str,
            str,
            dict[str, Any],
        ],
        _ResultT,
    ],
) -> _ResultT:
    """Authorize host actor/run/thread/message before an Episode technical write."""

    import database

    actor_id, thread_id = _trusted_actor_and_thread()
    message_id = _trusted_message_id()
    db = database.get_db()
    try:
        db.row_factory = sqlite3.Row
        workspace_row = db.execute(
            "SELECT workflow_runs.workspace_id AS id "
            "FROM workflow_runs INNER JOIN story_workspace_workspaces "
            "ON story_workspace_workspaces.id = workflow_runs.workspace_id "
            "WHERE workflow_runs.id = ? "
            "AND workflow_runs.created_by = ? "
            "AND story_workspace_workspaces.owner_id = ? LIMIT 1",
            (workflow_run_id, str(actor_id), actor_id),
        ).fetchone()
        if workspace_row is None:
            raise PermissionError("actor workspace is unavailable")
        run = _read_actor_scoped_run(
            db,
            workflow_run_id,
            AuthenticatedActorContext(
                workspace_id=str(workspace_row["id"]),
                actor_id=str(actor_id),
            ),
        )
        if run.source_voice_thread_id != thread_id:
            raise PermissionError("run and trusted thread do not match")
        thread = db.execute(
            "SELECT id FROM chat_thread "
            "WHERE id = ? AND user_id = ? LIMIT 1",
            (thread_id, actor_id),
        ).fetchone()
        if thread is None:
            raise PermissionError("thread ownership is unavailable")
        workspace = _existing_thread_workspace(thread_id)
        provenance = _active_episode_action_provenance(
            db,
            message_id=message_id,
            actor_id=actor_id,
            thread_id=thread_id,
            workflow_run_id=workflow_run_id,
        )
        return operation(
            db,
            workspace,
            run,
            actor_id,
            thread_id,
            message_id,
            provenance,
        )
    finally:
        db.close()


def _source_launch_row(
    db: sqlite3.Connection,
    *,
    actor_id: int,
    thread_id: str,
    workflow_run_id: str,
) -> tuple[str, str, dict[str, Any]]:
    locked = db.execute(
        "SELECT run.workspace_id, binding.deck_id, run.deck_plugin_id, "
        "run.deck_plugin_version, run.deck_plugin_binding_id, "
        "run.binding_revision, run.deck_runtime_snapshot_id, "
        "run.runtime_plugin_lock_id, thread.voice_id AS thread_voice_id, "
        "source.id AS source_id, source.metadata AS source_metadata "
        "FROM workflow_runs AS run "
        "JOIN deck_plugin_bindings AS binding "
        "ON binding.deck_plugin_binding_id = run.deck_plugin_binding_id "
        "AND binding.binding_revision = run.binding_revision "
        "AND binding.deck_plugin_id = run.deck_plugin_id "
        "AND binding.deck_plugin_version = run.deck_plugin_version "
        "AND binding.workspace_id = run.workspace_id "
        "JOIN chat_thread AS thread "
        "ON thread.id = run.source_voice_thread_id "
        "AND thread.deck_id = binding.deck_id "
        "JOIN chat_message AS source "
        "ON source.id = run.source_message_id "
        "AND source.thread_id = thread.id AND source.role = 'user' "
        "WHERE run.id = ? AND run.created_by = ? "
        "AND run.source_voice_thread_id = ? AND thread.user_id = ? LIMIT 1",
        (workflow_run_id, str(actor_id), thread_id, actor_id),
    ).fetchone()
    if locked is None:
        raise PermissionError("Dream launch provenance is unavailable")
    raw = locked["source_metadata"] or "{}"
    try:
        metadata = json.loads(raw)
    except (TypeError, ValueError) as error:
        raise PermissionError("Dream launch provenance is unavailable") from error
    if not isinstance(metadata, dict) or not (
        StoryWorkspaceDreamReentryService._source_metadata_matches(  # noqa: SLF001
            raw,
            actor_id=actor_id,
            workspace_id=str(locked["workspace_id"]),
            run_id=workflow_run_id,
            thread_id=thread_id,
            deck_id=str(locked["deck_id"]),
            deck_plugin_id=str(locked["deck_plugin_id"]),
            deck_plugin_version=str(locked["deck_plugin_version"]),
            binding_id=str(locked["deck_plugin_binding_id"]),
            binding_revision=int(locked["binding_revision"]),
            runtime_snapshot_id=str(locked["deck_runtime_snapshot_id"]),
            runtime_lock_id=str(locked["runtime_plugin_lock_id"]),
            thread_agent_id=locked["thread_voice_id"],
        )
    ):
        raise PermissionError("Dream launch provenance is unavailable")
    return str(locked["source_id"]), str(raw), metadata


def _bind_first_episode(
    request: StoryWorkspaceEpisodeBindingToolInput,
) -> dict[str, object]:
    def bind(
        db: sqlite3.Connection,
        workspace: Path,
        _run: WorkflowRun,
        actor_id: int,
        thread_id: str,
        _message_id: str,
        action: dict[str, Any],
    ) -> dict[str, object]:
        if action.get("action") not in {
            "recover_first_episode_binding",
            StoryWorkspaceEpisodeAction.PLAN_EPISODE.value,
        }:
            raise PermissionError("current action cannot bind an Episode")
        service = StoryWorkspaceEpisodeBindingService(workspace)
        project_slug = service.discover_unique_canonical_project_story_slug()
        if project_slug is None:
            raise PermissionError("a unique canonical project is unavailable")
        source_id, raw_metadata, source_metadata = _source_launch_row(
            db,
            actor_id=actor_id,
            thread_id=thread_id,
            workflow_run_id=request.workflow_run_id,
        )
        authority = StoryWorkspaceEpisodeAuthority.parse(
            source_metadata.get("story_workspace_episode_identity"),
            expected_run_id=request.workflow_run_id,
        )
        if authority is not None and authority.story_slug != project_slug:
            raise PermissionError("Episode authority cannot be rebound")
        if authority is None:
            if request.expected_binding_revision != 0:
                raise PermissionError("Episode binding revision changed")
            episode_uid = uuid4().hex
            source_metadata["story_workspace_episode_identity"] = {
                "schema": "story-workspace-episode-authority/v1",
                "workflow_run_id": request.workflow_run_id,
                "episode_uid": episode_uid,
                "story_slug": project_slug,
                "episode_code": "EP01",
            }
            encoded = json.dumps(
                source_metadata,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
                sort_keys=True,
            )
            db.execute("BEGIN IMMEDIATE")
            updated = db.execute(
                "UPDATE chat_message SET metadata = ? "
                "WHERE id = ? AND metadata = ?",
                (encoded, source_id, raw_metadata),
            )
            if updated.rowcount != 1:
                db.rollback()
                raise PermissionError("Episode authority CAS failed")
            db.commit()
        else:
            episode_uid = authority.episode_uid
            if request.expected_binding_revision not in {0, 1}:
                raise PermissionError("Episode binding revision changed")
        binding = service.bind_first_episode(
            StoryWorkspaceEpisodeBindingContext(
                workflow_run_id=request.workflow_run_id,
                trusted_project_story_slug=project_slug,
                locked_context_story_slug=project_slug,
                run_provenance_story_slug=project_slug,
                episode_uid=episode_uid,
            )
        )
        return {
            "run": request.workflow_run_id,
            "episodeId": binding.episode_uid,
            "bindingRevision": binding.revision,
        }

    return _with_authoritative_episode_context(request.workflow_run_id, bind)


def _record_episode_workflow_completion(
    request: StoryWorkspaceEpisodeWorkflowCompletionToolInput,
) -> dict[str, object]:
    def record(
        _db: sqlite3.Connection,
        workspace: Path,
        _run: WorkflowRun,
        _actor_id: int,
        _thread_id: str,
        message_id: str,
        provenance: dict[str, Any],
    ) -> dict[str, object]:
        try:
            action = StoryWorkspaceEpisodeAction(provenance["action"])
        except (KeyError, TypeError, ValueError) as exc:
            raise PermissionError("completion action is unavailable") from exc
        episode_uid = provenance.get("episode_uid")
        input_revision = provenance.get("input_revision")
        expected_facts_revision = provenance.get("expected_facts_revision")
        expected_manifest_revision = provenance.get("expected_manifest_revision")
        expected_workflow_revision = provenance.get("expected_workflow_revision")
        if (
            action is StoryWorkspaceEpisodeAction.NONE_IN_SCOPE
            or not isinstance(episode_uid, str)
            or re.fullmatch(r"[0-9a-f]{32}", episode_uid) is None
            or not isinstance(input_revision, str)
            or re.fullmatch(r"sha256:[0-9a-f]{64}", input_revision) is None
            or not isinstance(expected_facts_revision, int)
            or isinstance(expected_facts_revision, bool)
            or expected_facts_revision < 0
            or not isinstance(expected_manifest_revision, str)
            or re.fullmatch(
                r"sha256:[0-9a-f]{64}", expected_manifest_revision
            )
            is None
            or not isinstance(expected_workflow_revision, str)
            or re.fullmatch(
                r"sha256:[0-9a-f]{64}", expected_workflow_revision
            )
            is None
        ):
            raise PermissionError("completion provenance is unavailable")
        authority_row = _source_launch_row(
            _db,
            actor_id=_actor_id,
            thread_id=_thread_id,
            workflow_run_id=request.workflow_run_id,
        )
        authority = StoryWorkspaceEpisodeAuthority.parse(
            authority_row[2].get("story_workspace_episode_identity"),
            expected_run_id=request.workflow_run_id,
        )
        if authority is None or authority.episode_uid != episode_uid:
            raise PermissionError("Episode authority is unavailable")
        artifact_service = StoryWorkspaceEpisodeArtifactService(workspace)
        surface = artifact_service.read_surface(
            request.workflow_run_id,
            episode_authority=authority,
        )
        service = StoryWorkspaceEpisodeWorkflowFactService(workspace)
        facts = service.read(request.workflow_run_id, episode_uid)
        expected_input = StoryWorkspaceEpisodeNextActionResolver.action_input_revision(
            action,
            surface,
            facts,
        )
        if expected_input != input_revision:
            raise PermissionError("Episode action input revision changed")
        episode_root = (
            workspace
            / "stories"
            / authority.story_slug
            / "episodes"
            / authority.episode_code
        )
        StoryWorkspaceEpisodeCompletionValidator.validate_before_record(
            action=action,
            surface=surface,
            alias_report_present=(
                episode_root / "full-chain-review-report.md"
            ).is_file(),
        )
        if facts.revision != expected_facts_revision:
            replay = next(
                (
                    item
                    for item in facts.completions
                    if item.action is action
                    and item.input_revision == input_revision
                    and item.manifest_revision == surface.manifest_revision
                    and item.message_id == message_id
                ),
                None,
            )
            if replay is None:
                raise PermissionError("Episode workflow revision changed")
            return {
                "run": request.workflow_run_id,
                "episodeId": episode_uid,
                "action": action.value,
                "workflowRevision": facts.revision,
            }
        StoryWorkspaceEpisodeCompletionValidator.validate_transition_ready(
            action=action,
            surface=surface,
            facts=facts,
        )
        updated = service.record_completion(
            workflow_run_id=request.workflow_run_id,
            episode_uid=episode_uid,
            action=action,
            input_revision=input_revision,
            manifest_revision=surface.manifest_revision,
            message_id=message_id,
            expected_revision=expected_facts_revision,
        )
        refreshed_surface = artifact_service.read_surface(
            request.workflow_run_id,
            episode_authority=authority,
        )
        StoryWorkspaceEpisodeCompletionValidator.validate_after_record(
            action=action,
            surface=refreshed_surface,
            facts=updated,
        )
        return {
            "run": request.workflow_run_id,
            "episodeId": episode_uid,
            "action": action.value,
            "workflowRevision": updated.revision,
        }

    return _with_authoritative_episode_context(request.workflow_run_id, record)


def _success_json(payload: dict[str, object]) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def story_workspace_handle_dream_tool(
    name: str,
    arguments: dict[str, Any] | None,
) -> str:
    """Execute one controlled Dream write and return a compact JSON result.

    All validation, authorization, CAS, path, or I/O failures deliberately
    collapse to one public error code.  Detailed exceptions remain server-side
    and no absolute path or frozen provenance reaches the Agent response.
    """

    try:
        if name == "write_dream_run":
            request = StoryWorkspaceDreamRunToolInput.model_validate(arguments or {})
            _require_trusted_workflow_run(request.workflow_run_id)
            result = _with_authoritative_context(
                request.workflow_run_id,
                lambda writer, run: writer.write_run(
                    run,
                    thread_id=os.environ[_TRUSTED_THREAD_ENV],
                    expected_revision=request.expected_revision,
                ),
            )
            return _success_json(
                {
                    "run": result.workflow_run_id,
                    "revision": result.revision,
                    "changedStages": [],
                }
            )
        if name == "write_dream_stage":
            request = StoryWorkspaceDreamStageToolInput.model_validate(arguments or {})
            _require_trusted_workflow_run(request.workflow_run_id)
            result = _with_authoritative_context(
                request.workflow_run_id,
                lambda writer, run: writer.write_stage(
                    run,
                    stage=request.stage,
                    source_files=request.source_files,
                    items=[item.model_dump(by_alias=False) for item in request.items],
                    expected_revision=request.expected_revision,
                ),
            )
            return _success_json(
                {
                    "run": result.workflow_run_id,
                    "stage": result.stage.value,
                    "revision": result.revision,
                    "changedStages": [result.stage.value],
                }
            )
        if name == "bind_first_episode":
            request = StoryWorkspaceEpisodeBindingToolInput.model_validate(
                arguments or {}
            )
            _require_trusted_workflow_run(request.workflow_run_id)
            return _success_json(_bind_first_episode(request))
        if name == "record_episode_workflow_completion":
            request = StoryWorkspaceEpisodeWorkflowCompletionToolInput.model_validate(
                arguments or {}
            )
            _require_trusted_workflow_run(request.workflow_run_id)
            return _success_json(_record_episode_workflow_completion(request))
        raise ValueError("unknown Story Workspace tool")
    except StoryWorkspaceEpisodeCompletionContractError as exc:
        _logger.info(
            "Story Workspace Episode completion contract rejected: %s",
            exc.reason,
        )
        return _success_json(
            {
                "error": "DREAM_WRITE_REJECTED",
                "reason": exc.reason,
                "message": exc.public_message,
            }
        )
    except Exception:  # noqa: BLE001 - public fail-closed seam.
        _logger.warning("Story Workspace Dream MCP write rejected", exc_info=True)
        return _success_json({"error": "DREAM_WRITE_REJECTED"})


__all__ = [
    "STORY_WORKSPACE_DREAM_TOOL_SPECS",
    "StoryWorkspaceToolSpec",
    "story_workspace_allowed_tool_names",
    "story_workspace_handle_dream_tool",
]
