# [Input] Consume INK_EDITOR_SESSION_ID, INK_EDITOR_INTERNAL_BASE_URL env vars.
# [Output] Provide EditorToolInput, EDITOR_TOOL_SPECS, allowed_editor_tool_names,
#          get_editor_resource_handler to editor_mcp_server.py.
# [Pos] tool-definition node in libs/claude_agent_kit/server
# [Sync] 2026-05-23: initial implementation — EditorEngine MCP tool handlers.

"""EditorEngine MCP tool definitions.

Each tool reads one resource slice of the live ``EditorState`` snapshot for
the current session by calling the Ink & Memory internal API endpoint:

    GET http://{INK_EDITOR_INTERNAL_BASE_URL}/api/internal/editor-state/{session_id}?resource={resource}

The session_id and base URL are injected into the MCP subprocess environment
by ``agent_runner.py`` at server startup, keeping them invisible to Claude.

Tools
-----
read_cells          → ``cells`` array (TextCell / WidgetCell objects)
read_commentors     → ``commentors`` array (voice annotations)
read_tasks          → ``tasks`` array (in-progress analysis tasks)
read_session        → session metadata (id, selectedState, createdAt)
read_full_state     → complete EditorState snapshot
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_INTERNAL_BASE_URL = "http://127.0.0.1:8765"
_FETCH_TIMEOUT_S = 5.0


@dataclass(frozen=True)
class EditorToolSpec:
    """Server-owned field bundle for one Agent-selectable editor tool."""

    resource: str
    description: str


EDITOR_TOOL_SPECS: dict[str, EditorToolSpec] = {
    "read_cells": EditorToolSpec(
        resource="cells",
        description=(
            "读取当前写作会话的文本和组件单元（cells）数组。"
            "每个 TextCell 包含 id、type='text'、content 字段；"
            "WidgetCell 包含 id、type='widget'、widgetType、data 字段。"
        ),
    ),
    "read_commentors": EditorToolSpec(
        resource="commentors",
        description=(
            "读取当前写作会话的声音注释（commentors）数组。"
            "每条注释包含 id、phrase（高亮短语）、comment、voice 等字段，"
            "以及可选的 chatHistory 和 feedback。"
        ),
    ),
    "read_tasks": EditorToolSpec(
        resource="tasks",
        description=(
            "读取当前写作会话的分析任务（tasks）数组。"
            "每个任务包含 id、type、message、startedAt、completedAt 字段。"
        ),
    ),
    "read_session": EditorToolSpec(
        resource="session",
        description=(
            "读取当前写作会话的元数据：id、selectedState（情绪状态）、createdAt（创建时间戳）。"
        ),
    ),
    "read_full_state": EditorToolSpec(
        resource="full_state",
        description=(
            "读取当前写作会话的完整 EditorState 快照，包含 cells、commentors、tasks、"
            "weightPath、overlappedPhrases、notFoundPhrases、id、selectedState、createdAt。"
            "当需要整体上下文时使用；只需部分数据时请优先使用细粒度工具以减少 token 消耗。"
        ),
    ),
}


class EditorNoInput(BaseModel):
    """No Agent-facing parameters; server env binds session_id."""

    model_config = ConfigDict(extra="forbid")


def allowed_editor_tool_names() -> list[str]:
    """Return fully-qualified allowed tool names for Claude Code options."""
    return [f"mcp__editor__{name}" for name in EDITOR_TOOL_SPECS]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _internal_base_url() -> str:
    return str(
        os.getenv("INK_EDITOR_INTERNAL_BASE_URL", _DEFAULT_INTERNAL_BASE_URL)
    ).rstrip("/")


def _session_id_from_env() -> str:
    return str(os.getenv("INK_EDITOR_SESSION_ID", "")).strip()


async def _fetch_editor_resource(session_id: str, resource: str) -> dict[str, Any]:
    """Call the internal editor-state API and return parsed JSON."""
    base_url = _internal_base_url()
    url = f"{base_url}/api/internal/editor-state/{session_id}"
    params = {"resource": resource}
    try:
        async with httpx.AsyncClient(timeout=_FETCH_TIMEOUT_S) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "EditorEngine: failed to fetch resource=%s session=%s: %s",
            resource,
            session_id,
            exc,
        )
        return {"ok": False, "error": "fetch_failed", "data": None}


# ---------------------------------------------------------------------------
# Public handler
# ---------------------------------------------------------------------------


async def get_editor_resource_handler(tool_name: str) -> str:
    """Fetch editor resource and return compact JSON text to Claude."""
    spec = EDITOR_TOOL_SPECS.get(tool_name)
    if spec is None:
        return json.dumps(
            {"ok": False, "error": f"unknown_tool:{tool_name}", "data": None},
            ensure_ascii=False,
            separators=(",", ":"),
        )

    session_id = _session_id_from_env()
    if not session_id:
        return json.dumps(
            {"ok": False, "error": "editor_session_id_missing", "data": None},
            ensure_ascii=False,
            separators=(",", ":"),
        )

    result = await _fetch_editor_resource(session_id, spec.resource)
    result["tool_intent"] = tool_name
    return json.dumps(result, ensure_ascii=False, separators=(",", ":"))


__all__ = [
    "EDITOR_TOOL_SPECS",
    "EditorNoInput",
    "EditorToolSpec",
    "allowed_editor_tool_names",
    "get_editor_resource_handler",
]
