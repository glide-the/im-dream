"""Controlled MCP handlers for Story Workspace Dream runtime writes.

The Claude Agent supplies only the target run, stage payload, and CAS revision.
Actor and Chat-thread identity come exclusively from the host-injected stdio
environment.  Frozen run provenance is loaded from the authoritative
``WorkflowRun`` on every call and is never accepted as a tool argument.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, TypeVar

from pydantic import BaseModel

from models.workflow_run import AuthenticatedActorContext, WorkflowRun
from services.story_workspace.dream_file_service import (
    StoryWorkspaceDreamFileWriter,
    WorkflowRun as DreamFileWorkflowRun,
)
from services.workflow.run_service import WorkflowRunService
from story_workspace.contracts import (
    StoryWorkspaceDreamRunToolInput,
    StoryWorkspaceDreamStageToolInput,
)

from .workspace import get_workspace_root


logger = logging.getLogger(__name__)

_TRUSTED_USER_ENV = "INK_AGENT_USER_ID"
_TRUSTED_THREAD_ENV = "INK_AGENT_THREAD_ID"
_ResultT = TypeVar("_ResultT", bound=BaseModel)


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
}


def allowed_story_workspace_tool_names() -> list[str]:
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
            "SELECT id FROM story_workspace_workspaces WHERE owner_id = ? "
            "ORDER BY created_at ASC, id ASC LIMIT 1",
            (actor_id,),
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


def _success_json(payload: dict[str, object]) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def handle_story_workspace_dream_tool(
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
        raise ValueError("unknown Story Workspace tool")
    except Exception:  # noqa: BLE001 - public fail-closed seam.
        logger.warning("Story Workspace Dream MCP write rejected", exc_info=True)
        return _success_json({"error": "DREAM_WRITE_REJECTED"})


__all__ = [
    "STORY_WORKSPACE_DREAM_TOOL_SPECS",
    "StoryWorkspaceToolSpec",
    "allowed_story_workspace_tool_names",
    "handle_story_workspace_dream_tool",
]
