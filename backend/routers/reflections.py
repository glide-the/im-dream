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
import asyncio
import logging
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
from services.admin_data.errors import AdminDataError
from services.admin_data.reflection_task_models import (
    ReflectionEventListInputDTO,
    ReflectionTaskCreateInputDTO,
    ReflectionTaskCreateSnapshotDTO,
    ReflectionTaskDTO,
    ReflectionTaskLatestInputDTO,
    ReflectionTaskLookupDTO,
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
    created = await invoke_admin_operation(
        current_user,
        data.create,
        create_input,
    )
    task = created.task
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
        content=json.dumps(_task_response(task), ensure_ascii=False),
        media_type="application/json",
        status_code=202,
    )


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
        content=json.dumps(_task_response(started.task), ensure_ascii=False),
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
        content=json.dumps(_task_response(result.task, result.results), ensure_ascii=False),
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
            {"task": _task_response(result.task) if result.task else None,
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
