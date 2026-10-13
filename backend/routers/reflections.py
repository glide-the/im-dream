#!/usr/bin/env python3
# [Input] Consume reflections_config, typed Admin Reflections/section/Thread reads, workspace libs, and shared auth.
# [Output] Register Reflections endpoints:
#          POST /api/reflections/memory-init      — section memory workspace init
#          GET  /api/reflections/config/{section} — read effective section config
#          PUT  /api/reflections/config/{section} — save user custom section config
#          DELETE /api/reflections/config/{section} — reset to default
#          POST/GET /api/reflections/tasks/*     — create/start/read/results/events
#          GET  /api/reflections/latest          — latest task and terminal results
# [Pos] reflections route node in backend/routers
# [Sync] 2026-06-06: initial implementation — procedural Memory Workspace initialisation
#                    for Reflections page sections (echoes / traits / patterns).
# [Sync] 2026-06-06: add GET/PUT/DELETE /api/reflections/config/{section} for
#                    per-user custom prompt file editing; memory-init now prefers
#                    user config over static default.
# [Sync] 2026-09-15: route public section config, task, event, and result ownership through Admin.
# [Sync] 2026-10-13: read mounted Notion candidates and create immutable task content through additive Admin operations.
# [Sync] 2026-10-13: bind complete source candidates to the original caller key and clear them after task commit.
"""Reflections analysis router.

Endpoints
---------
POST   /api/reflections/memory-init         — write section memory workspace files
GET    /api/reflections/config/{section}    — effective config (user custom or default)
PUT    /api/reflections/config/{section}    — save user's custom prompt files
DELETE /api/reflections/config/{section}    — reset section to static default

Flow (docs/design/memory/reflections-analysis-prd.md §6):

    1. POST /api/claude-agent/threads           → thread_id
    2. POST /api/reflections/memory-init        → memory/ files written (user config if set)
    3. POST /api/claude-agent (SSE, system_prompt with section + memoryPath)
    4. drain SSE → GET /api/claude-agent/threads/{id}/messages → parse text parts
"""
from __future__ import annotations

import json
import hashlib
import asyncio
import logging
from uuid import uuid4
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, ConfigDict, ValidationError

from reflections_agent import (
    get_reflection_event_bus,
    prepare_reflection_event_bus,
    start_reflections_task,
)
from reflections_config import REFLECTIONS_SECTION_CONFIGS, list_sections, get_section_config

from services.admin_data.chat_data import AdminChatData
from services.admin_data.chat_models import ThreadIdInputDTO
from services.admin_data.reflections_config_data import (
    AdminReflectionsSectionConfigData,
    ReflectionsSectionInputDTO,
    ReflectionsSectionSaveInputDTO,
)
from services.admin_data.request_auth import AdminRequestAuth
from services.admin_data.request_auth import AdminRequestActor
from services.admin_data.models import CommittedReceiptDTO, Identifier
from services.admin_data.reflection_task_data import FROZEN_REFLECTION_TASK_CONTRACTS
from services.admin_data.errors import AdminDataError
from services.admin_data.reflection_analysis_content_data import (
    ANALYSIS_CONTENT_CONTRACT_VERSION, AdminReflectionAnalysisContentData,
    ReflectionAnalysisCreateDTO, ReflectionAnalysisSelectionDTO, ReflectionAgentInputDTO,
    require_analysis_content_capability, CREATE_WITH_CONTENT,
)
from services.admin_data.reflection_analysis_content import (
    analysis_content_candidates, freeze_notion_analysis_input, clear_notion_analysis_preparation,
)
from services.admin_data.reflection_task_models import (
    ReflectionEventListInputDTO,
    ReflectionTaskCreateInputDTO,
    ReflectionTaskCreateSnapshotDTO,
    ReflectionTaskDTO,
    ReflectionTaskLatestInputDTO,
    ReflectionTaskLookupDTO, Identifier256,
)
from services.admin_data.reflection_task_runtime import (
    prepare_reflection_memory_workspace,
    prepare_reflection_workspace_directory,
    reflection_workspace_root,
    validate_reflection_workspace_path,
    write_reflection_workspace_text,
)

from .deps import get_admin_request_auth, get_current_user, invoke_admin_operation

logger = logging.getLogger(__name__)

router = APIRouter()

_VALID_SECTIONS = frozenset(list_sections())

# Filenames accepted in user-supplied prompt_files (whitelist).
_VALID_PROMPT_FILES = frozenset({
    "WORKFLOW.md",
    "MEMORY_QUERY_PROMPT.md",
    "MEMORY_Distiller_PROMPT.md",
    "MEMORY_ANSWER_PROMPT.md",
    "DEFAULT_UPDATE_MEMORY_PROMPT.md",
})

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class ReflectionsMemoryInitRequest(BaseModel):
    threadId: str
    section: str


class SectionConfigUpdateRequest(BaseModel):
    prompt_files: dict[str, str]


class ReflectionsTaskCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    sections: Optional[list[str]] = None
    session_ids: Optional[list[str]] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    language: Optional[str] = None
    auto_start: bool = True
    analysis_content: Optional["ReflectionsAnalysisContentRequest"] = None
    request_key: Optional[Identifier] = None


class ReflectionsAnalysisContentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    include_notion: bool = False
    connector_id: Optional[Identifier256] = None
    deck_id: Optional[Identifier256] = None
    agent_id: Optional[Identifier256] = None
    snapshot_version: Optional[Identifier256] = None


ReflectionsTaskCreateRequest.model_rebuild()


def _normalize_reflections_language(language: Optional[str]) -> str:
    """Normalize frontend UI language codes to the Reflections prompt contract."""
    code = (language or "en").strip().lower()
    if code.startswith("zh"):
        return "zh"
    return "en"


def _language_label(language: str) -> str:
    return "Simplified Chinese" if language == "zh" else "English"


def _validated_reflection_input(factory, **values):
    try:
        return factory(**values)
    except ValidationError:
        raise HTTPException(
            status_code=422, detail={"error": "Invalid Reflections request"}
        ) from None


# ---------------------------------------------------------------------------
# Workspace helpers
# ---------------------------------------------------------------------------


def _get_workspace_root() -> Path:
    """Return the shared, explicitly configured Agent workspace root."""
    return reflection_workspace_root()


def _write_section_memory_workspace(thread_id: str, prompt_files: dict[str, str]) -> Path:
    """Write prompt files into the thread workspace memory/ directory.

    Returns the ``memory/`` directory path.
    Raises ``ValueError`` on path traversal.
    """
    workspace_root = _get_workspace_root()
    memory_dir = prepare_reflection_memory_workspace(
        identifier=thread_id,
        advertised_path=str(workspace_root / thread_id / "memory"),
    )

    written: list[str] = []
    for filename, content in prompt_files.items():
        if filename not in _VALID_PROMPT_FILES:
            continue
        if not isinstance(content, str) or not content.strip():
            continue
        write_reflection_workspace_text(
            memory_dir / filename, content.strip() + "\n"
        )
        written.append(filename)

    logger.debug(
        "_write_section_memory_workspace: wrote %d files for thread=%s", len(written), thread_id
    )

    proc_dir = prepare_reflection_workspace_directory(memory_dir / "procedural")
    state_file = proc_dir / "analysis_state.json"
    validate_reflection_workspace_path(state_file)
    if not state_file.exists():
        write_reflection_workspace_text(
            state_file,
            json.dumps({"completed": False, "results_count": 0}, ensure_ascii=False, indent=2),
        )

    return memory_dir


# ---------------------------------------------------------------------------
# POST /api/reflections/memory-init
# ---------------------------------------------------------------------------


@router.post("/api/reflections/memory-init")
async def reflections_memory_init(
    body: ReflectionsMemoryInitRequest,
    current_user: dict = Depends(get_current_user),
    owner: AdminRequestAuth = Depends(get_admin_request_auth),
) -> Response:
    """Initialise the procedural memory workspace for a Reflections section analysis.

    Writes section prompt files from the effective config (user custom if set,
    else static default from ``reflections_config.py``) into the thread workspace.

    Returns ``{ "initialised": true, "section": "...", "threadId": "...",
                "memoryPath": "...", "usedCustomConfig": bool }``
    """
    thread_id = body.threadId
    section = body.section

    if not thread_id or not thread_id.strip():
        raise HTTPException(status_code=400, detail={"error": "threadId is required"})

    if section not in _VALID_SECTIONS:
        raise HTTPException(
            status_code=400,
            detail={"error": f"Invalid section '{section}'. Must be one of: {sorted(_VALID_SECTIONS)}"},
        )

    thread = await invoke_admin_operation(
        current_user,
        AdminChatData(owner.client).get_thread,
        ThreadIdInputDTO(thread_id=thread_id),
    )
    if thread.thread is None:
        raise HTTPException(status_code=404, detail={"error": "Thread not found"})

    # Resolve effective config (user custom takes priority).
    user_custom = await invoke_admin_operation(
        current_user,
        AdminReflectionsSectionConfigData(owner.client).get,
        ReflectionsSectionInputDTO(section=section),
    )
    static_cfg = get_section_config(section)
    static_files: dict[str, str] = static_cfg.get("prompt_files", {})

    used_custom = bool(user_custom)
    if user_custom:
        prompt_files = dict(static_files)
        for fname, content in user_custom.items():
            if fname in _VALID_PROMPT_FILES and isinstance(content, str) and content.strip():
                prompt_files[fname] = content.strip()
    else:
        prompt_files = static_files

    try:
        memory_dir = _write_section_memory_workspace(thread_id, prompt_files)
    except AdminDataError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"error_code": exc.code, "outcome_unknown": exc.outcome_unknown},
        ) from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"error": str(exc)}) from exc
    except Exception as exc:
        logger.exception(
            "reflections_memory_init: unexpected error for section=%s thread=%s",
            section, thread_id,
        )
        raise HTTPException(status_code=500, detail={"error": "Memory workspace init failed"}) from exc

    return Response(
        content=json.dumps({
            "initialised": True,
            "section": section,
            "threadId": thread_id,
            "memoryPath": str(memory_dir),
            "usedCustomConfig": used_custom,
        }),
        media_type="application/json",
    )


# ---------------------------------------------------------------------------
# Reflections-agent async task endpoints
# ---------------------------------------------------------------------------


def _task_response(task: ReflectionTaskDTO, results=None) -> dict[str, Any]:
    payload = task.model_dump(mode="json")
    if results is not None:
        payload["results"] = [item.model_dump(mode="json") for item in results]
    return payload


async def _content_task_response(task, current_user, owner, results=None):
    payload = _task_response(task, results)
    if task.agent_contract_version == ANALYSIS_CONTENT_CONTRACT_VERSION:
        summary = await invoke_admin_operation(current_user,
            AdminReflectionAnalysisContentData(owner.client).summary,
            ReflectionTaskLookupDTO(task_id=task.task_id))
        payload["input_snapshot"]["analysis_content"] = summary.analysis_content.model_dump(mode="json") if summary.analysis_content else None
    return payload


@router.get("/api/reflections/analysis-content")
async def get_reflections_analysis_content(
    current_user: dict = Depends(get_current_user),
    owner: AdminRequestAuth = Depends(get_admin_request_auth),
):
    from .notion import _connector_facade, _http_error
    from notion.errors import NotionConnectorNotFoundError, NotionAuthRequiredError, NotionCredentialError
    try:
        require_analysis_content_capability(owner.client, "reflections-content-candidates")
        available = True
    except AdminDataError as exc:
        if exc.code != "ADMIN_CAPABILITY_UNAVAILABLE":
            raise _http_error(exc) from None
        available = False
    try:
        candidates = await asyncio.to_thread(analysis_content_candidates, _connector_facade(current_user, owner))
    except NotionConnectorNotFoundError:
        candidates = {"status": "disconnected", "page_count": 0, "snapshot_version": None}
    except (NotionAuthRequiredError, NotionCredentialError):
        candidates = {"status": "auth_required", "page_count": 0, "snapshot_version": None}
    except AdminDataError as exc:
        if exc.code != "NOTION_ANALYSIS_SCOPE_CHANGED":
            raise _http_error(exc) from None
        candidates = {"status": "scope_changed", "page_count": 0, "snapshot_version": None}
    except Exception as exc:
        raise _http_error(exc) from None
    return {**candidates, "selection_available": available}


def _reflections_data(owner: AdminRequestAuth):
    try:
        return owner.reflections_data()
    except AdminDataError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"error_code": exc.code, "outcome_unknown": exc.outcome_unknown},
        ) from None


def _reflections_worker(owner: AdminRequestAuth):
    try:
        return owner.reflections_worker_data()
    except AdminDataError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"error_code": exc.code, "outcome_unknown": exc.outcome_unknown},
        ) from None


async def _start_worker(task_id: str, owner: AdminRequestAuth) -> None:
    try:
        await start_reflections_task(
            task_id,
            worker=_reflections_worker(owner),
            client=owner.client,
            session_broker_settings=owner.session_broker_settings,
            runtime_http_config=owner.runtime_http_config,
        )
    except AdminDataError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"error_code": exc.code, "request_id": exc.request_id,
                    "outcome_unknown": exc.outcome_unknown},
        ) from None


@router.post("/api/reflections/tasks", status_code=202)
async def create_reflections_task_endpoint(
    body: ReflectionsTaskCreateRequest,
    current_user: dict = Depends(get_current_user),
    owner: AdminRequestAuth = Depends(get_admin_request_auth),
) -> Response:
    """Create and start a backend Reflections-agent async task."""
    requested_sections = body.sections or list(list_sections())
    invalid = [section for section in requested_sections if section not in _VALID_SECTIONS]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail={"error": f"Invalid sections: {invalid}. Must be one of: {sorted(_VALID_SECTIONS)}"},
        )

    language = _normalize_reflections_language(body.language)
    data = _reflections_data(owner)
    input_snapshot = _validated_reflection_input(
        ReflectionTaskCreateSnapshotDTO,
        session_ids=body.session_ids or [],
        start_date=body.start_date,
        end_date=body.end_date,
        language=language,
        language_label=_language_label(language),
    )
    create_input = _validated_reflection_input(
        ReflectionTaskCreateInputDTO,
        sections=requested_sections,
        input_snapshot=input_snapshot,
    )
    selection = body.analysis_content
    extended_selection = bool(selection and (selection.include_notion or selection.agent_id or selection.deck_id))
    recovered = None
    if body.request_key:
        operation = CREATE_WITH_CONTENT if extended_selection else FROZEN_REFLECTION_TASK_CONTRACTS.operation("reflection-task.create")
        actor = current_user.get("_admin_actor")
        if not isinstance(actor, AdminRequestActor):
            raise HTTPException(503, detail={"error_code": "ADMIN_CONFIGURATION_INVALID"})
        try:
            if extended_selection:
                require_analysis_content_capability(owner.client, body.request_key)
            receipt = await asyncio.to_thread(owner.client.receipt, operation, body.request_key, access_token=actor.access_token)
            if isinstance(receipt, CommittedReceiptDTO):
                recovered = receipt.result
                actual = recovered.task.input_snapshot
                if recovered.task.sections != requested_sections or any(getattr(actual, field) != getattr(input_snapshot, field) for field in type(input_snapshot).model_fields):
                    raise AdminDataError("REFLECTION_SUBMISSION_CONFLICT", 409)
                if extended_selection:
                    summary = (await invoke_admin_operation(current_user, AdminReflectionAnalysisContentData(owner.client).summary,
                        ReflectionTaskLookupDTO(task_id=recovered.task.task_id))).analysis_content
                    if (summary is None or bool(summary.notion) != selection.include_notion
                        or (summary.agent.agent_id if summary.agent else None) != selection.agent_id
                        or (summary.agent.deck_id if summary.agent else None) != selection.deck_id
                        or (summary.notion.snapshot_version if summary.notion else None) != (selection.snapshot_version if selection.include_notion else None)
                        or (summary.notion.connector_id if summary.notion else None) != (selection.connector_id if selection.include_notion else None)
                        or summary.diary_session_ids != body.session_ids):
                        raise AdminDataError("REFLECTION_SUBMISSION_CONFLICT", 409)
        except AdminDataError as exc:
            raise HTTPException(exc.status_code, detail={"error_code": exc.code, "outcome_unknown": exc.outcome_unknown}) from None
    if recovered is not None:
        created = recovered
    elif extended_selection:
        from .notion import _connector_facade, _http_error
        try:
            require_analysis_content_capability(owner.client, "reflections-content-create")
            if bool(selection.deck_id) != bool(selection.agent_id):
                raise AdminDataError("REFLECTION_AGENT_SELECTION_INVALID", 422)
            notion = await freeze_notion_analysis_input(
                _connector_facade(current_user, owner), selection.snapshot_version, selection.connector_id,
                request_key=body.request_key,
                request_fingerprint=hashlib.sha256(json.dumps(body.model_dump(mode="json"), sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
            ) if selection.include_notion else None
        except Exception as exc:
            # No task creation has been invoked in this source-read phase.
            # A failed read is a definite rejection, not an unknown write outcome.
            error = _http_error(exc)
            detail = dict(error.detail) if isinstance(error.detail, dict) else {"error_code": error.detail}
            raise HTTPException(error.status_code, detail={**detail, "outcome_unknown": False}, headers=error.headers) from None
        extended = ReflectionAnalysisCreateDTO(**create_input.model_dump(), analysis_content=ReflectionAnalysisSelectionDTO(
            diary_session_ids=body.session_ids, notion=notion, agent=ReflectionAgentInputDTO(deck_id=selection.deck_id, agent_id=selection.agent_id) if selection.agent_id else None))
        created = await invoke_admin_operation(current_user, AdminReflectionAnalysisContentData(owner.client).create, extended, request_id=body.request_key)
    else:
        created = await invoke_admin_operation(current_user, data.create, create_input, request_id=body.request_key)
    clear_notion_analysis_preparation(current_user["user_id"], body.request_key)
    task = created.task
    try:
        await prepare_reflection_event_bus(
            task.task_id, worker=_reflections_worker(owner)
        )
        if body.auto_start:
            started = await invoke_admin_operation(
                current_user,
                data.start,
                ReflectionTaskLookupDTO(task_id=task.task_id),
            )
            task = started.task
            if not started.terminal or started.report_missing:
                await _start_worker(task.task_id, owner)
        return Response(
            content=json.dumps(await _content_task_response(task, current_user, owner), ensure_ascii=False),
            media_type="application/json",
            status_code=202,
        )
    except HTTPException as exc:
        detail = dict(exc.detail) if isinstance(exc.detail, dict) else {"error_code": "REFLECTION_TASK_SETUP_FAILED"}
        raise HTTPException(exc.status_code, detail={**detail, "creation_committed": True, "task_id": task.task_id}) from None
    except Exception:
        logger.exception("Reflections post-create setup failed task_id=%s", task.task_id)
        raise HTTPException(503, detail={"error_code": "REFLECTION_TASK_SETUP_FAILED", "creation_committed": True, "task_id": task.task_id}) from None


@router.post("/api/reflections/tasks/{task_id}/start", status_code=202)
async def start_reflections_task_endpoint(
    task_id: str,
    current_user: dict = Depends(get_current_user),
    owner: AdminRequestAuth = Depends(get_admin_request_auth),
) -> Response:
    """Start a previously-created Reflections task.

    This endpoint lets the frontend establish its SSE subscription before the
    task begins, which makes task/section events visible as a live stream
    rather than only as replayed completed events.
    """
    data = _reflections_data(owner)
    started = await invoke_admin_operation(
        current_user,
        data.start,
        _validated_reflection_input(ReflectionTaskLookupDTO, task_id=task_id),
    )
    if not started.terminal or started.report_missing:
        await _start_worker(task_id, owner)
    return Response(
        content=json.dumps(await _content_task_response(started.task, current_user, owner), ensure_ascii=False),
        media_type="application/json",
        status_code=202,
    )


@router.get("/api/reflections/tasks/{task_id}")
async def get_reflections_task_endpoint(
    task_id: str,
    current_user: dict = Depends(get_current_user),
    owner: AdminRequestAuth = Depends(get_admin_request_auth),
) -> Response:
    """Return the persisted status snapshot for a Reflections-agent task."""
    result = await invoke_admin_operation(
        current_user,
        _reflections_data(owner).get,
        _validated_reflection_input(ReflectionTaskLookupDTO, task_id=task_id),
    )
    return Response(
        content=json.dumps(await _content_task_response(result.task, current_user, owner, result.results), ensure_ascii=False),
        media_type="application/json",
    )


@router.get("/api/reflections/tasks/{task_id}/results")
async def get_reflections_task_results_endpoint(
    task_id: str,
    current_user: dict = Depends(get_current_user),
    owner: AdminRequestAuth = Depends(get_admin_request_auth),
) -> Response:
    """Return structured Reflections results for one task."""
    result = await invoke_admin_operation(
        current_user,
        _reflections_data(owner).get,
        _validated_reflection_input(ReflectionTaskLookupDTO, task_id=task_id),
    )
    return Response(
        content=json.dumps(
            {"task_id": task_id,
             "results": [item.model_dump(mode="json") for item in result.results]},
            ensure_ascii=False,
        ),
        media_type="application/json",
    )


@router.post("/api/reflections/tasks/{task_id}/report")
async def ensure_reflections_report_endpoint(
    task_id: str,
    current_user: dict = Depends(get_current_user),
    owner: AdminRequestAuth = Depends(get_admin_request_auth),
):
    """Recover the original task-linked report after an authorized terminal lookup."""
    lookup = _validated_reflection_input(ReflectionTaskLookupDTO, task_id=task_id)
    started = await invoke_admin_operation(current_user, _reflections_data(owner).start, lookup)
    if not started.terminal:
        raise HTTPException(409, detail={"error_code": "REFLECTION_TASK_NOT_TERMINAL"})
    try:
        report = await asyncio.to_thread(_reflections_worker(owner).ensure_report, lookup, str(uuid4()))
    except AdminDataError as exc:
        raise HTTPException(exc.status_code, detail={"error_code": exc.code, "outcome_unknown": exc.outcome_unknown}) from None
    return report.model_dump(mode="json")


@router.get("/api/reflections/latest")
async def get_latest_reflections_endpoint(
    current_user: dict = Depends(get_current_user),
    owner: AdminRequestAuth = Depends(get_admin_request_auth),
) -> Response:
    """Return the latest Reflections task and latest completed results for the user."""
    result = await invoke_admin_operation(
        current_user,
        _reflections_data(owner).latest,
        ReflectionTaskLatestInputDTO(),
    )
    return Response(
        content=json.dumps(
            {"task": await _content_task_response(result.task, current_user, owner) if result.task else None,
             "results": [item.model_dump(mode="json") for item in result.results]},
            ensure_ascii=False,
        ),
        media_type="application/json",
    )


@router.get("/api/reflections/tasks/{task_id}/events")
async def stream_reflections_task_events_endpoint(
    task_id: str,
    current_user: dict = Depends(get_current_user),
    owner: AdminRequestAuth = Depends(get_admin_request_auth),
    last_event_id: Optional[str] = Header(default=None, alias="Last-Event-ID"),
) -> StreamingResponse:
    """Subscribe to Reflections task events.

    The stream first reads authorized Admin history, then emits newer events
    from the process-local bus without repeating a sequence.
    """
    bus = await get_reflection_event_bus(task_id)
    token = await bus.subscribe(last_event_id) if bus is not None else None
    try:
        history = await invoke_admin_operation(
            current_user,
            _reflections_data(owner).events,
            _validated_reflection_input(
                ReflectionEventListInputDTO,
                task_id=task_id, after_event_id=last_event_id
            ),
        )
    except BaseException:
        if bus is not None and token is not None:
            await bus.unsubscribe(token)
        raise

    async def _stream():
        try:
            yield (
                "event: reflection.stream.connected\n"
                f"data: {json.dumps({'id': 'stream-connected', 'task_id': task_id, 'type': 'reflection.stream.connected', 'sequence': 0, 'created_at': None, 'payload': {}}, ensure_ascii=False)}\n\n"
            )
            maximum = 0
            for event in history.events:
                maximum = max(maximum, event.sequence)
                payload = event.model_dump(mode="json")
                yield (
                    f"event: {event.type}\n"
                    f"id: {event.id}\n"
                    f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                )
            if bus is None or token is None:
                return
            async for event in bus.read(token):
                if event.sequence > maximum:
                    yield event.to_sse_frame()
        finally:
            if bus is not None and token is not None:
                await bus.unsubscribe(token)

    return StreamingResponse(_stream(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# GET /api/reflections/config/{section}
# ---------------------------------------------------------------------------


@router.get("/api/reflections/config/{section}")
async def get_section_config_endpoint(
    section: str,
    current_user: dict = Depends(get_current_user),
    owner: AdminRequestAuth = Depends(get_admin_request_auth),
) -> Response:
    """Return the effective section config for the current user.

    Response:
    ```json
    {
      "section": "echoes",
      "display_name": "Recurring Themes",
      "display_name_zh": "回响",
      "usedCustomConfig": false,
      "prompt_files": {
        "WORKFLOW.md": "...",
        "MEMORY_QUERY_PROMPT.md": "...",
        ...
      }
    }
    ```
    """
    if section not in _VALID_SECTIONS:
        raise HTTPException(
            status_code=400,
            detail={"error": f"Invalid section. Must be one of: {sorted(_VALID_SECTIONS)}"},
        )

    user_custom = await invoke_admin_operation(
        current_user,
        AdminReflectionsSectionConfigData(owner.client).get,
        ReflectionsSectionInputDTO(section=section),
    )
    static_cfg = get_section_config(section)
    static_files: dict[str, str] = static_cfg.get("prompt_files", {})

    if user_custom:
        effective_files = dict(static_files)
        for fname, content in user_custom.items():
            if fname in _VALID_PROMPT_FILES and isinstance(content, str) and content.strip():
                effective_files[fname] = content.strip()
    else:
        effective_files = static_files

    return Response(
        content=json.dumps({
            "section": section,
            "display_name": static_cfg.get("display_name", section),
            "display_name_zh": static_cfg.get("display_name_zh", section),
            "usedCustomConfig": bool(user_custom),
            "prompt_files": effective_files,
        }, ensure_ascii=False),
        media_type="application/json",
    )


# ---------------------------------------------------------------------------
# PUT /api/reflections/config/{section}
# ---------------------------------------------------------------------------


@router.put("/api/reflections/config/{section}")
async def update_section_config_endpoint(
    section: str,
    body: SectionConfigUpdateRequest,
    current_user: dict = Depends(get_current_user),
    owner: AdminRequestAuth = Depends(get_admin_request_auth),
) -> Response:
    """Save user's custom prompt files for a section.

    Only filenames in the whitelist (WORKFLOW.md, MEMORY_QUERY_PROMPT.md, etc.)
    are accepted. Unknown keys are silently dropped.

    Body: ``{ "prompt_files": { "WORKFLOW.md": "...", ... } }``

    Returns ``{ "saved": true, "section": "...", "updatedFiles": [...] }``
    """
    if section not in _VALID_SECTIONS:
        raise HTTPException(
            status_code=400,
            detail={"error": f"Invalid section. Must be one of: {sorted(_VALID_SECTIONS)}"},
        )

    if not body.prompt_files or not isinstance(body.prompt_files, dict):
        raise HTTPException(status_code=400, detail={"error": "prompt_files must be a non-empty dict"})

    filtered = {
        fname: content.strip()
        for fname, content in body.prompt_files.items()
        if fname in _VALID_PROMPT_FILES
        and isinstance(content, str)
        and content.strip()
    }
    if not filtered:
        raise HTTPException(
            status_code=400,
            detail={"error": f"No valid prompt file names. Accepted: {sorted(_VALID_PROMPT_FILES)}"},
        )

    await invoke_admin_operation(
        current_user,
        AdminReflectionsSectionConfigData(owner.client).save,
        ReflectionsSectionSaveInputDTO(
            section=section,
            prompt_files_json=json.dumps(filtered, ensure_ascii=False),
        ),
    )

    return Response(
        content=json.dumps({
            "saved": True,
            "section": section,
            "updatedFiles": sorted(filtered.keys()),
        }),
        media_type="application/json",
    )


# ---------------------------------------------------------------------------
# DELETE /api/reflections/config/{section}
# ---------------------------------------------------------------------------


@router.delete("/api/reflections/config/{section}")
async def reset_section_config_endpoint(
    section: str,
    current_user: dict = Depends(get_current_user),
    owner: AdminRequestAuth = Depends(get_admin_request_auth),
) -> Response:
    """Reset user's custom config for a section back to the static default.

    Returns ``{ "reset": true, "section": "..." }``
    """
    if section not in _VALID_SECTIONS:
        raise HTTPException(
            status_code=400,
            detail={"error": f"Invalid section. Must be one of: {sorted(_VALID_SECTIONS)}"},
        )

    await invoke_admin_operation(
        current_user,
        AdminReflectionsSectionConfigData(owner.client).delete,
        ReflectionsSectionInputDTO(section=section),
    )

    return Response(
        content=json.dumps({"reset": True, "section": section}),
        media_type="application/json",
    )
