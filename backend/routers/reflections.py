#!/usr/bin/env python3
# [Input] Consume reflections_config, database, workspace libs, and shared auth dependency.
# [Output] Register Reflections endpoints:
#          POST /api/reflections/memory-init      — section memory workspace init
#          GET  /api/reflections/config/{section} — read effective section config
#          PUT  /api/reflections/config/{section} — save user custom section config
#          DELETE /api/reflections/config/{section} — reset to default
# [Pos] reflections route node in backend/routers
# [Sync] 2026-06-06: initial implementation — procedural Memory Workspace initialisation
#                    for Reflections page sections (echoes / traits / patterns).
# [Sync] 2026-06-06: add GET/PUT/DELETE /api/reflections/config/{section} for
#                    per-user custom prompt file editing; memory-init now prefers
#                    user config over static default.
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
import logging
import os
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

import database
from reflections_config import REFLECTIONS_SECTION_CONFIGS, list_sections, get_section_config

from .deps import get_current_user

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


# ---------------------------------------------------------------------------
# Workspace helpers
# ---------------------------------------------------------------------------


def _get_workspace_root() -> Path:
    """Return the workspace root (same env var as workspace.py)."""
    import tempfile
    agent_cwd = os.environ.get("AGENT_CWD", "")
    if agent_cwd:
        return Path(agent_cwd)
    return Path(tempfile.gettempdir()) / "ink-agent-workspaces"


def _effective_prompt_files(user_id: int, section: str) -> dict[str, str]:
    """Return the effective prompt_files for *section* for *user_id*.

    Priority:
      1. User's custom config from ``reflections_section_configs`` DB table.
      2. Static default from ``reflections_config.py``.

    Custom config may be partial — only files present in the user config are
    overridden; the rest are filled from the static default.
    """
    static_cfg = get_section_config(section)
    static_files: dict[str, str] = static_cfg.get("prompt_files", {})

    user_files = database.get_reflections_section_config(user_id, section)
    if not user_files:
        return static_files

    # Merge: user overrides static defaults file-by-file.
    merged = dict(static_files)
    for filename, content in user_files.items():
        if filename in _VALID_PROMPT_FILES and isinstance(content, str) and content.strip():
            merged[filename] = content.strip()
    return merged


def _write_section_memory_workspace(thread_id: str, prompt_files: dict[str, str]) -> Path:
    """Write prompt files into the thread workspace memory/ directory.

    Returns the ``memory/`` directory path.
    Raises ``ValueError`` on path traversal.
    """
    workspace_root = _get_workspace_root()
    workspace_path = workspace_root / thread_id

    workspace_abs = workspace_path.resolve()
    root_abs = workspace_root.resolve()
    if not str(workspace_abs).startswith(str(root_abs)):
        raise ValueError(f"thread_id resolves outside workspace root: {thread_id!r}")

    workspace_path.mkdir(parents=True, exist_ok=True)
    memory_dir = workspace_path / "memory"
    memory_dir.mkdir(exist_ok=True)

    written: list[str] = []
    for filename, content in prompt_files.items():
        if filename not in _VALID_PROMPT_FILES:
            continue
        if not isinstance(content, str) or not content.strip():
            continue
        (memory_dir / filename).write_text(content.strip() + "\n", encoding="utf-8")
        written.append(filename)

    logger.debug(
        "_write_section_memory_workspace: wrote %d files for thread=%s", len(written), thread_id
    )

    proc_dir = memory_dir / "procedural"
    proc_dir.mkdir(exist_ok=True)
    state_file = proc_dir / "analysis_state.json"
    if not state_file.exists():
        state_file.write_text(
            json.dumps({"completed": False, "results_count": 0}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    return memory_dir


# ---------------------------------------------------------------------------
# POST /api/reflections/memory-init
# ---------------------------------------------------------------------------


@router.post("/api/reflections/memory-init")
async def reflections_memory_init(
    body: ReflectionsMemoryInitRequest,
    current_user: dict = Depends(get_current_user),
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

    user_id = int(current_user["user_id"])
    thread = database.get_chat_thread(thread_id, user_id)
    if thread is None:
        raise HTTPException(status_code=404, detail={"error": "Thread not found"})

    # Resolve effective config (user custom takes priority).
    user_custom = database.get_reflections_section_config(user_id, section)
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
# GET /api/reflections/config/{section}
# ---------------------------------------------------------------------------


@router.get("/api/reflections/config/{section}")
async def get_section_config_endpoint(
    section: str,
    current_user: dict = Depends(get_current_user),
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

    user_id = int(current_user["user_id"])
    user_custom = database.get_reflections_section_config(user_id, section)
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

    user_id = int(current_user["user_id"])
    database.save_reflections_section_config(user_id, section, filtered)

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
) -> Response:
    """Reset user's custom config for a section back to the static default.

    Returns ``{ "reset": true, "section": "..." }``
    """
    if section not in _VALID_SECTIONS:
        raise HTTPException(
            status_code=400,
            detail={"error": f"Invalid section. Must be one of: {sorted(_VALID_SECTIONS)}"},
        )

    user_id = int(current_user["user_id"])
    database.delete_reflections_section_config(user_id, section)

    return Response(
        content=json.dumps({"reset": True, "section": section}),
        media_type="application/json",
    )
