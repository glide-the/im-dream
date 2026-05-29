# [Input] Consume editor_state injected by the runner via INK_EDITOR_STATE_JSON env var
#         (session-inline JSON, no tempfile).  Falls back to INK_EDITOR_STATE_FILE for
#         legacy / large-state callers.
#         Consume EDITOR_RESOURCES and get_editor_resource_data from editor_index.py
#         as the unified source of EditorState field-name mapping.
# [Output] Provide EDITOR_READ_TOOL_SPECS, allowed_editor_tool_names,
#          handle_editor_read_tool to the editor MCP server.
# [Pos] tool-definition node in libs/claude_agent_kit/server
# [Sync] 2026-05-28: initial implementation — 5 read-only EditorState tools.
# [Sync] 2026-05-29: import EDITOR_RESOURCES and get_editor_resource_data from
#                    editor_index.py and use them as the unified mapping source in
#                    all handler functions — eliminates hardcoded field-name strings.
# [Sync] 2026-05-29: _load_editor_state reads from INK_EDITOR_STATE_JSON (session-inline
#                    JSON env var) as primary source, falls back to INK_EDITOR_STATE_FILE;
#                    eliminates mandatory tempfile creation in the normal execution path.

"""EditorEngine read-only MCP tool handlers.

Implements the five read tools described in
``docs/design/claude-agent/edit-point/mcp-tools.md`` §2.1:

  list_segments       — list all cells with id, type, preview, length
  read_segment        — full content of one cell by cellId
  read_session_meta   — session id, createdAt, selectedState
  list_comments       — summaries of all applied commentors
  read_comment        — full comment with conversation history

The editor MCP server subprocess reads ``editor_state`` from a JSON file
whose path is passed via the ``INK_EDITOR_STATE_FILE`` environment variable.
This file is written by ``agent_runner.py`` at the start of each ``run_streaming``
call and cleaned up at the end.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Optional

from .editor_index import EDITOR_RESOURCES, get_editor_resource_data

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Unified field-name constants derived from EDITOR_RESOURCES (editor_index.py).
# Using these constants instead of hardcoded strings ensures that any rename
# in the virtual index adapter's mapping is automatically reflected here.
# ---------------------------------------------------------------------------

# Simple direct-field resources (non-special mapping values).
_CELLS_FIELD: str = EDITOR_RESOURCES["cells"]        # "cells"
_COMMENTORS_FIELD: str = EDITOR_RESOURCES["commentors"]  # "commentors"
_TASKS_FIELD: str = EDITOR_RESOURCES["tasks"]        # "tasks"
# Session and full_state use special mappings ("__session__", "__full__");
# those are extracted via get_editor_resource_data().
_SESSION_VIRTUAL_PATH = ".editor/session.json"

# ---------------------------------------------------------------------------
# Tool spec registry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EditorToolSpec:
    """Server-owned field bundle for one Agent-selectable editor tool."""

    description: str
    # JSON Schema for the input object.
    input_schema: dict[str, Any]


EDITOR_READ_TOOL_SPECS: dict[str, EditorToolSpec] = {
    "list_segments": EditorToolSpec(
        description=(
            "列出当前会话中所有文档片段，包含每个片段的 ID、类型和内容摘要（前 100 字符）。"
            "用于了解文档结构后再选择性读取或修改。"
        ),
        input_schema={"type": "object", "properties": {}, "required": []},
    ),
    "read_segment": EditorToolSpec(
        description="读取指定片段的完整内容。文本片段返回完整文本，组件片段返回其 data 结构。",
        input_schema={
            "type": "object",
            "properties": {
                "cellId": {
                    "type": "string",
                    "description": "片段的唯一 ID，从 list_segments 获取",
                },
            },
            "required": ["cellId"],
        },
    ),
    "read_session_meta": EditorToolSpec(
        description="读取当前编辑会话的元数据：ID、创建时间、今日情感状态。",
        input_schema={"type": "object", "properties": {}, "required": []},
    ),
    "list_comments": EditorToolSpec(
        description="列出当前会话所有已应用评论的摘要（id、phrase、voice、appliedAt）。",
        input_schema={
            "type": "object",
            "properties": {
                "filter": {
                    "type": "string",
                    "enum": ["all", "starred", "killed", "pending"],
                    "description": "按反馈状态过滤，默认 all",
                },
            },
            "required": [],
        },
    ),
    "read_comment": EditorToolSpec(
        description="读取指定评论的完整内容，包括锚定短语、评论文本和对话历史。",
        input_schema={
            "type": "object",
            "properties": {
                "commentId": {
                    "type": "string",
                    "description": "评论的唯一 ID",
                },
            },
            "required": ["commentId"],
        },
    ),
}


def allowed_editor_tool_names() -> list[str]:
    """Return the list of ``mcp__editor__*`` tool names for use in allowlists."""
    return [f"mcp__editor__{name}" for name in EDITOR_READ_TOOL_SPECS]


# ---------------------------------------------------------------------------
# State loader
# ---------------------------------------------------------------------------


def _load_editor_state() -> dict[str, Any]:
    """Load the editor_state dict for the current MCP session.

    Primary path — ``INK_EDITOR_STATE_JSON``:
        The runner serialises the session's ``editor_state`` directly into the
        subprocess environment as a JSON string.  No tempfile is created or read.

    Fallback path — ``INK_EDITOR_STATE_FILE``:
        Legacy / large-state callers that still write a tempfile and pass its path.
        Supported for backward compatibility; prefer the JSON env var in new code.

    Returns an empty dict when neither variable is set or the data cannot be parsed.
    Errors are logged at WARNING level so tools can return graceful "no data" responses.
    """
    # Primary: session-inline JSON from the runner (no disk I/O).
    state_json = os.getenv("INK_EDITOR_STATE_JSON", "").strip()
    if state_json:
        try:
            data = json.loads(state_json)
            if isinstance(data, dict):
                return data
            logger.warning("INK_EDITOR_STATE_JSON is not a JSON object; ignoring.")
        except Exception:  # noqa: BLE001
            logger.warning("Failed to parse INK_EDITOR_STATE_JSON", exc_info=True)

    # Fallback: file-based IPC (legacy or large-state).
    state_file = os.getenv("INK_EDITOR_STATE_FILE", "").strip()
    if state_file:
        try:
            with open(state_file, encoding="utf-8") as fh:
                data = json.load(fh)
            if not isinstance(data, dict):
                logger.warning("INK_EDITOR_STATE_FILE content is not a JSON object; ignoring.")
                return {}
            return data
        except Exception:  # noqa: BLE001
            logger.warning("Failed to read INK_EDITOR_STATE_FILE %r", state_file, exc_info=True)
            return {}

    logger.warning(
        "Neither INK_EDITOR_STATE_JSON nor INK_EDITOR_STATE_FILE is set; "
        "editor tools will return empty state."
    )
    return {}


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------


def _preview(text: str, max_len: int = 100) -> str:
    """Return a truncated preview of *text*."""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "…"


def handle_editor_read_tool(
    tool_name: str,
    arguments: Optional[dict[str, Any]],
) -> str:
    """Dispatch to the correct read handler and return a JSON string result."""
    args = arguments or {}
    state = _load_editor_state()

    if tool_name == "list_segments":
        return _list_segments(state)
    if tool_name == "read_segment":
        return _read_segment(state, args.get("cellId", ""))
    if tool_name == "read_session_meta":
        return _read_session_meta(state)
    if tool_name == "list_comments":
        return _list_comments(state, args.get("filter", "all"))
    if tool_name == "read_comment":
        return _read_comment(state, args.get("commentId", ""))

    return json.dumps({"ok": False, "error": f"unknown_tool:{tool_name}"})


def _list_segments(state: dict[str, Any]) -> str:
    # Use EDITOR_RESOURCES["cells"] as the unified field name source.
    cells: list[dict[str, Any]] = state.get(_CELLS_FIELD) or []
    segments = []
    for cell in cells:
        cell_id = cell.get("id", "")
        cell_type = cell.get("type", "")
        if cell_type == "text":
            content = cell.get("content", "") or ""
            segments.append({
                "id": cell_id,
                "type": cell_type,
                "preview": _preview(content),
                "length": len(content),
            })
        else:
            widget_type = cell.get("widgetType") or cell.get("widget_type") or ""
            entry: dict[str, Any] = {"id": cell_id, "type": cell_type}
            if widget_type:
                entry["widgetType"] = widget_type
            voice_id = (cell.get("data") or {}).get("voiceId")
            if voice_id:
                entry["voiceId"] = voice_id
            segments.append(entry)

    return json.dumps({
        "ok": True,
        "sessionId": state.get("id"),
        "totalSegments": len(segments),
        "segments": segments,
    }, ensure_ascii=False)


def _read_segment(state: dict[str, Any], cell_id: str) -> str:
    if not cell_id:
        return json.dumps({"ok": False, "error": "cellId_required"})
    # Use EDITOR_RESOURCES["cells"] as the unified field name source.
    cells: list[dict[str, Any]] = state.get(_CELLS_FIELD) or []
    for cell in cells:
        if cell.get("id") == cell_id:
            return json.dumps({"ok": True, "cell": cell}, ensure_ascii=False)
    return json.dumps({"ok": False, "error": "cell_not_found", "cellId": cell_id})


def _read_session_meta(state: dict[str, Any]) -> str:
    # Delegate to get_editor_resource_data for the __session__ special mapping,
    # keeping session field extraction consistent with the virtual index adapter.
    session = get_editor_resource_data(_SESSION_VIRTUAL_PATH, state)
    return json.dumps({"ok": True, **session}, ensure_ascii=False)


def _list_comments(state: dict[str, Any], filter_val: str) -> str:
    # Use EDITOR_RESOURCES["commentors"] as the unified field name source.
    commentors: list[dict[str, Any]] = state.get(_COMMENTORS_FIELD) or []
    valid_filters = {"all", "starred", "killed", "pending"}
    if filter_val not in valid_filters:
        filter_val = "all"

    summaries = []
    for c in commentors:
        feedback = c.get("feedback", "pending")
        if filter_val != "all" and feedback != filter_val:
            continue
        summaries.append({
            "id": c.get("id"),
            "phrase": c.get("phrase"),
            "voiceId": c.get("voiceId"),
            "appliedAt": c.get("appliedAt"),
            "feedback": feedback,
        })

    return json.dumps({
        "ok": True,
        "filter": filter_val,
        "totalComments": len(summaries),
        "comments": summaries,
    }, ensure_ascii=False)


def _read_comment(state: dict[str, Any], comment_id: str) -> str:
    if not comment_id:
        return json.dumps({"ok": False, "error": "commentId_required"})
    # Use EDITOR_RESOURCES["commentors"] as the unified field name source.
    commentors: list[dict[str, Any]] = state.get(_COMMENTORS_FIELD) or []
    for c in commentors:
        if c.get("id") == comment_id:
            return json.dumps({"ok": True, "comment": c}, ensure_ascii=False)
    return json.dumps({"ok": False, "error": "comment_not_found", "commentId": comment_id})
