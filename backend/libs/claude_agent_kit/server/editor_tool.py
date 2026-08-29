# [Input] Session context comes from MCP tool call arguments passed by the Claude agent;
#         the trusted actor comes from the server-owned INK_AGENT_USER_ID projection.
#         The runner verifies the live Editor session before execution, while every DB
#         read/write also scopes by actor and session.
# [Output] Provide EDITOR_WRITE_TOOL_SPECS, allowed_editor_tool_names,
#          handle_editor_write_tool to the editor MCP server.
# [Pos] tool-definition node in libs/claude_agent_kit/server
# [Sync] 2026-05-28: initial implementation — 5 read-only EditorState tools.
# [Sync] 2026-05-29: import EDITOR_RESOURCES and get_editor_resource_data from
#                    editor_index.py and use them as the unified mapping source in
#                    all handler functions — eliminates hardcoded field-name strings.
# [Sync] 2026-05-29: _load_editor_state reads from INK_EDITOR_STATE_JSON (session-inline
#                    JSON env var) as primary source, falls back to INK_EDITOR_STATE_FILE;
#                    eliminates mandatory tempfile creation in the normal execution path.
# [Sync] 2026-05-29: remove all read-only tools (list_segments, read_segment,
#                    read_session_meta, list_comments, read_comment); add 4 write tools
#                    (write_segment, delete_segment, insert_widget, reply_to_comment).
#                    _load_editor_state replaced by _load_session_context +
#                    _load_editor_state_from_db — data source is the database via
#                    INK_AGENT_SESSION_ID / INK_AGENT_USER_ID, not file IPC or env JSON.
# [Sync] 2026-05-29: remove _load_session_context / os.getenv; session_id now arrives via
#                    MCP tool call arguments (agent reads it from <workspace_context> prompt).
#                    DB helpers use session_id-only queries (no user_id — trusted subprocess).
# [Sync] 2026-06-01: add switch_editor context-switching tool (no-op MCP handler; actual
#                    state switch performed by PostToolUse hook in agent_runner.py).
# [Sync] 2026-06-09: switch_editor remains a no-op MCP handler; product
#                    permission policy treats context switching as low-sensitivity
#                    because it does not modify document content.
# [Sync] 2026-08-29: bind DB access to the server-owned actor, distinguish
#                    unavailable persistence from missing sessions/cells, and perform
#                    at most one fresh reload before a target-not-found failure.

"""EditorEngine write MCP tool handlers.

Implements the four write tools described in
``docs/design/claude-agent/edit-point/mcp-tools.md`` §2.1:

  write_segment       — replace a cell's full text (requires confirmation)
  delete_segment      — remove a cell entirely (irreversible, requires confirmation)
  insert_widget       — insert a new widget cell (requires confirmation)
  reply_to_comment    — append an agent reply to a comment thread (requires confirmation)

Session context flows through the MCP protocol itself:

  1. ``agent_runner.py`` injects ``session_id`` into the ``<workspace_context>`` prompt block.
  2. Claude reads ``session_id`` from the prompt and includes it as a required argument in
     every write tool call.
  3. Each write handler receives ``session_id`` from ``arguments`` and uses it to load/save
     ``editor_state`` directly from the database — no env-var or file IPC needed.

Reading document content is handled exclusively by the ``.editor/`` virtual index
PreToolUse interception mechanism in ``agent_runner.py`` (see
``docs/design/claude-agent/edit-point/workspace-adapter.md``).
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)

_EDITOR_ACTOR_ENV = "INK_AGENT_USER_ID"
_EDITOR_TARGET_LOAD_ATTEMPTS = 2


class EditorStateUnavailable(RuntimeError):
    """The trusted Editor persistence boundary could not be read safely."""

# ---------------------------------------------------------------------------
# Tool spec registry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EditorToolSpec:
    """Server-owned field bundle for one Agent-selectable editor tool."""

    description: str
    # JSON Schema for the input object.
    input_schema: dict[str, Any]


# ---------------------------------------------------------------------------
# Context-switch tool name constant (used by editor_runner.py PostToolUse hook)
# ---------------------------------------------------------------------------

SWITCH_EDITOR_TOOL_NAME = "switch_editor"

# ``editor_session_id`` is a required system argument in every write tool.
# Claude reads it from the ``<workspace_context>`` prompt block (the "Editor Session ID"
# field, which is the user_sessions.id from /api/sessions) and must include it with
# every call.  This ID is distinct from the workspace directory name and the Claude
# thread / conversation ID.
_EDITOR_SESSION_ID_PROPERTY = {
    "editor_session_id": {
        "type": "string",
        "description": (
            "Editor session ID from the <workspace_context> block "
            "(user_sessions.id from /api/sessions). "
            "Required for all write operations — pass the exact value shown in your prompt."
        ),
    }
}

EDITOR_WRITE_TOOL_SPECS: dict[str, EditorToolSpec] = {
    "write_segment": EditorToolSpec(
        description=(
            "替换指定文本片段的完整内容。此操作会修改用户的创作内容，必须经用户确认后执行。"
        ),
        input_schema={
            "type": "object",
            "properties": {
                **_EDITOR_SESSION_ID_PROPERTY,
                "cellId": {
                    "type": "string",
                    "description": "要修改的文本片段 ID",
                },
                "text": {
                    "type": "string",
                    "description": "新的完整文本内容（替换整个片段，而非追加）",
                },
                "reason": {
                    "type": "string",
                    "description": "说明此次修改的意图，将展示给用户以便决策",
                },
            },
            "required": ["editor_session_id", "cellId", "text", "reason"],
        },
    ),
    "delete_segment": EditorToolSpec(
        description="删除指定片段。此操作不可逆，必须经用户确认。",
        input_schema={
            "type": "object",
            "properties": {
                **_EDITOR_SESSION_ID_PROPERTY,
                "cellId": {
                    "type": "string",
                    "description": "要删除的片段 ID",
                },
                "reason": {
                    "type": "string",
                    "description": "删除原因，将展示给用户以便决策",
                },
            },
            "required": ["editor_session_id", "cellId", "reason"],
        },
    ),
    "insert_widget": EditorToolSpec(
        description=(
            "在指定位置插入一个新的组件片段（如 chat、image 等）。必须经用户确认后执行。"
        ),
        input_schema={
            "type": "object",
            "properties": {
                **_EDITOR_SESSION_ID_PROPERTY,
                "widgetType": {
                    "type": "string",
                    "description": "组件类型，如 'chat'、'image'",
                },
                "data": {
                    "type": "object",
                    "description": "组件数据，结构取决于 widgetType",
                },
                "afterCellId": {
                    "type": "string",
                    "description": "在此片段 ID 之后插入；留空则追加至文档末尾",
                },
                "reason": {
                    "type": "string",
                    "description": "插入理由，将展示给用户以便决策",
                },
            },
            "required": ["editor_session_id", "widgetType", "reason"],
        },
    ),
    "reply_to_comment": EditorToolSpec(
        description=(
            "向指定评论的对话历史追加一条 Agent 回复消息。必须经用户确认后执行。"
        ),
        input_schema={
            "type": "object",
            "properties": {
                **_EDITOR_SESSION_ID_PROPERTY,
                "commentId": {
                    "type": "string",
                    "description": "目标评论 ID",
                },
                "content": {
                    "type": "string",
                    "description": "回复内容",
                },
                "reason": {
                    "type": "string",
                    "description": "回复理由，将展示给用户以便决策",
                },
            },
            "required": ["editor_session_id", "commentId", "content", "reason"],
        },
    ),
    # Context-switch tool: the MCP handler is intentionally a no-op.
    # The actual editor_state switch is performed by the PostToolUse hook in
    # agent_runner.py, which loads the new state from the database and updates
    # the AgentRunState flyweight so subsequent .editor/ reads reflect the new
    # document context. Runner PreToolUse policy treats this as low-sensitivity
    # because it does not modify document content.
    SWITCH_EDITOR_TOOL_NAME: EditorToolSpec(
        description=(
            "切换当前对话的工作空间上下文至指定会话。调用成功后，智能体通过 .editor/ 路径读取的"
            "内容将来自新的目标会话文档。此操作不修改任何文档内容；状态切换在服务端由 PostToolUse"
            "钩子异步完成，无需前端确认。"
        ),
        input_schema={
            "type": "object",
            "properties": {
                "editor_session_id": {
                    "type": "string",
                    "description": (
                        "要切换到的目标会话 ID（user_sessions.id from /api/sessions）。"
                        "切换后智能体将在该会话的文档上下文中继续工作。"
                    ),
                },
            },
            "required": ["editor_session_id"],
        },
    ),
}


def allowed_editor_tool_names() -> list[str]:
    """Return the list of ``mcp__editor__*`` tool names for use in allowlists."""
    return [f"mcp__editor__{name}" for name in EDITOR_WRITE_TOOL_SPECS]


# ---------------------------------------------------------------------------
# Database helpers (trusted actor + session scope)
# ---------------------------------------------------------------------------


def _trusted_editor_user_id() -> int | None:
    """Return the server-projected actor ID, or ``None`` when unavailable."""

    raw = str(os.getenv(_EDITOR_ACTOR_ENV) or "").strip()
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _decode_editor_state(raw: Any) -> dict[str, Any]:
    """Decode one persisted EditorState without accepting non-object payloads."""

    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, ValueError) as exc:
        raise EditorStateUnavailable() from exc
    if not isinstance(data, dict):
        raise EditorStateUnavailable()
    return data


def _load_editor_state_from_db(
    editor_session_id: str,
    user_id: int,
) -> dict[str, Any] | None:
    """Load actor-owned ``editor_state`` for *editor_session_id*.

    *editor_session_id* is the ``user_sessions.id`` from ``/api/sessions`` —
    NOT the workspace directory name or the Claude thread ID.

    ``None`` means no row exists for this actor/session pair. Persistence or
    decoding failures raise :class:`EditorStateUnavailable` so callers never
    misreport capability failures as ``cell_not_found``.
    """
    if not editor_session_id or user_id <= 0:
        return None
    try:
        import database  # noqa: PLC0415 — runtime import, backend only

        db = database.get_db()
        try:
            row = db.execute(
                """SELECT editor_state_json FROM user_sessions
                   WHERE user_id = %s AND id = %s""",
                (user_id, editor_session_id),
            ).fetchone()
            if row is None:
                return None
            return _decode_editor_state(row["editor_state_json"])
        finally:
            db.close()
    except Exception:  # noqa: BLE001
        logger.warning(
            "Editor state load failed safely; editor_session_id=%r",
            editor_session_id,
        )
        raise EditorStateUnavailable() from None


def _save_editor_state_to_db(
    editor_session_id: str,
    user_id: int,
    editor_state: dict[str, Any],
) -> bool:
    """Persist the mutated ``editor_state`` back to the database.

    Returns ``True`` on success, ``False`` on failure.
    """
    if not editor_session_id or user_id <= 0:
        return False
    try:
        import database  # noqa: PLC0415

        db = database.get_db()
        try:
            cursor = db.execute(
                """UPDATE user_sessions
                   SET editor_state_json = %s, updated_at = CURRENT_TIMESTAMP
                   WHERE user_id = %s AND id = %s""",
                (
                    json.dumps(editor_state, ensure_ascii=False),
                    user_id,
                    editor_session_id,
                ),
            )
            if cursor.rowcount != 1:
                db.rollback()
                return False
            db.commit()
            return True
        finally:
            db.close()
    except Exception:  # noqa: BLE001
        logger.warning(
            "Editor state save failed safely; editor_session_id=%r",
            editor_session_id,
        )
        return False


def load_editor_state_from_db(
    editor_session_id: str,
    user_id: int,
) -> dict[str, Any] | None:
    """Public actor-scoped loader used by the ``switch_editor`` hook.

    Used by :mod:`agent_runner` PostToolUse hook to load the new context
    after a ``switch_editor`` tool call completes.
    """
    return _load_editor_state_from_db(editor_session_id, user_id)


def _load_target_state(
    editor_session_id: str,
    user_id: int,
    target_exists: Any,
) -> tuple[dict[str, Any] | None, bool]:
    """Load state and perform exactly one fresh reload when a target is absent."""

    state: dict[str, Any] | None = None
    for attempt in range(_EDITOR_TARGET_LOAD_ATTEMPTS):
        state = _load_editor_state_from_db(editor_session_id, user_id)
        if state is None or target_exists(state):
            return state, attempt > 0
    return state, True


# ---------------------------------------------------------------------------
# Tool dispatch
# ---------------------------------------------------------------------------


def handle_editor_write_tool(
    tool_name: str,
    arguments: Optional[dict[str, Any]],
) -> str:
    """Dispatch to the correct write handler and return a JSON string result.

    ``editor_session_id`` is extracted from *arguments* — the Claude agent reads it
    from the ``<workspace_context>`` prompt block (the "Editor Session ID" field,
    which is the ``user_sessions.id`` from ``/api/sessions``) and includes it in
    every write tool call.  It is distinct from the workspace directory name and
    the Claude thread / conversation ID.
    """
    args = arguments or {}

    # switch_editor is a context-switch tool whose MCP handler is intentionally a
    # no-op; the actual state update is performed by the PostToolUse hook in
    # agent_runner.py.  It does not carry the standard editor_session_id validation
    # block (the session_id represents the *target*, not the current session).
    if tool_name == SWITCH_EDITOR_TOOL_NAME:
        return _switch_editor(str(args.get("editor_session_id") or "").strip())

    user_id = _trusted_editor_user_id()
    if user_id is None:
        return json.dumps({"ok": False, "error": "editor_context_unavailable"})

    # editor_session_id comes from the agent context (prompt), not from env vars.
    editor_session_id: str = str(args.get("editor_session_id") or "").strip()
    if not editor_session_id:
        return json.dumps({"ok": False, "error": "editor_session_id_required"})

    if tool_name == "write_segment":
        return _write_segment(
            editor_session_id,
            args.get("cellId", ""),
            args.get("text", ""),
            args.get("reason", ""),
            user_id=user_id,
        )
    if tool_name == "delete_segment":
        return _delete_segment(
            editor_session_id,
            args.get("cellId", ""),
            args.get("reason", ""),
            user_id=user_id,
        )
    if tool_name == "insert_widget":
        return _insert_widget(
            editor_session_id,
            args.get("widgetType", ""),
            args.get("data") or {},
            args.get("afterCellId", ""),
            args.get("reason", ""),
            user_id=user_id,
        )
    if tool_name == "reply_to_comment":
        return _reply_to_comment(
            editor_session_id,
            args.get("commentId", ""),
            args.get("content", ""),
            args.get("reason", ""),
            user_id=user_id,
        )

    return json.dumps({"ok": False, "error": f"unknown_tool:{tool_name}"})


# ---------------------------------------------------------------------------
# Write handlers
# ---------------------------------------------------------------------------


def _write_segment(
    editor_session_id: str,
    cell_id: str,
    text: str,
    reason: str,
    *,
    user_id: int,
) -> str:
    """Replace a text cell's content in the database."""
    if not cell_id:
        return json.dumps({"ok": False, "error": "cellId_required"})
    if text is None:
        return json.dumps({"ok": False, "error": "text_required"})

    try:
        state, recovered = _load_target_state(
            editor_session_id,
            user_id,
            lambda value: any(
                cell.get("id") == cell_id for cell in (value.get("cells") or [])
            ),
        )
    except EditorStateUnavailable:
        return json.dumps({"ok": False, "error": "editor_state_unavailable"})
    if state is None:
        return json.dumps({"ok": False, "error": "editor_session_not_found"})
    cells: list[dict[str, Any]] = state.get("cells") or []

    found = False
    for cell in cells:
        if cell.get("id") == cell_id:
            if cell.get("type") != "text":
                return json.dumps({
                    "ok": False,
                    "error": "cell_not_text_type",
                    "cellId": cell_id,
                    "type": cell.get("type"),
                })
            cell["content"] = text
            found = True
            break

    if not found:
        return json.dumps({"ok": False, "error": "cell_not_found", "cellId": cell_id})

    if not _save_editor_state_to_db(editor_session_id, user_id, state):
        return json.dumps({"ok": False, "error": "save_failed"})

    return json.dumps({
        "ok": True,
        "cellId": cell_id,
        "reason": reason,
        "recovered": recovered,
    }, ensure_ascii=False)


def _delete_segment(
    editor_session_id: str,
    cell_id: str,
    reason: str,
    *,
    user_id: int,
) -> str:
    """Remove a cell from the document."""
    if not cell_id:
        return json.dumps({"ok": False, "error": "cellId_required"})

    try:
        state, recovered = _load_target_state(
            editor_session_id,
            user_id,
            lambda value: any(
                cell.get("id") == cell_id for cell in (value.get("cells") or [])
            ),
        )
    except EditorStateUnavailable:
        return json.dumps({"ok": False, "error": "editor_state_unavailable"})
    if state is None:
        return json.dumps({"ok": False, "error": "editor_session_not_found"})
    cells: list[dict[str, Any]] = state.get("cells") or []

    original_len = len(cells)
    state["cells"] = [c for c in cells if c.get("id") != cell_id]

    if len(state["cells"]) == original_len:
        return json.dumps({"ok": False, "error": "cell_not_found", "cellId": cell_id})

    if not _save_editor_state_to_db(editor_session_id, user_id, state):
        return json.dumps({"ok": False, "error": "save_failed"})

    return json.dumps({
        "ok": True,
        "cellId": cell_id,
        "reason": reason,
        "recovered": recovered,
    }, ensure_ascii=False)


def _insert_widget(
    editor_session_id: str,
    widget_type: str,
    data: dict[str, Any],
    after_cell_id: str,
    reason: str,
    *,
    user_id: int,
) -> str:
    """Insert a new widget cell after the specified cell (or at the end)."""
    if not widget_type:
        return json.dumps({"ok": False, "error": "widgetType_required"})

    try:
        state, recovered = _load_target_state(
            editor_session_id,
            user_id,
            lambda value: (
                not after_cell_id
                or any(
                    cell.get("id") == after_cell_id
                    for cell in (value.get("cells") or [])
                )
            ),
        )
    except EditorStateUnavailable:
        return json.dumps({"ok": False, "error": "editor_state_unavailable"})
    if state is None:
        return json.dumps({"ok": False, "error": "editor_session_not_found"})
    cells: list[dict[str, Any]] = state.get("cells") or []

    new_cell: dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "type": "widget",
        "widgetType": widget_type,
        "data": data or {},
    }

    if after_cell_id:
        insert_idx = next(
            (i + 1 for i, c in enumerate(cells) if c.get("id") == after_cell_id),
            None,
        )
        if insert_idx is None:
            return json.dumps({
                "ok": False,
                "error": "after_cell_not_found",
                "afterCellId": after_cell_id,
            })
        cells.insert(insert_idx, new_cell)
    else:
        cells.append(new_cell)

    state["cells"] = cells

    if not _save_editor_state_to_db(editor_session_id, user_id, state):
        return json.dumps({"ok": False, "error": "save_failed"})

    return json.dumps({
        "ok": True,
        "cellId": new_cell["id"],
        "widgetType": widget_type,
        "reason": reason,
        "recovered": recovered,
    }, ensure_ascii=False)


def _reply_to_comment(
    editor_session_id: str,
    comment_id: str,
    content: str,
    reason: str,
    *,
    user_id: int,
) -> str:
    """Append an agent reply to a comment's conversation history."""
    if not comment_id:
        return json.dumps({"ok": False, "error": "commentId_required"})
    if not content:
        return json.dumps({"ok": False, "error": "content_required"})

    try:
        state, recovered = _load_target_state(
            editor_session_id,
            user_id,
            lambda value: any(
                item.get("id") == comment_id
                for item in (value.get("commentors") or [])
            ),
        )
    except EditorStateUnavailable:
        return json.dumps({"ok": False, "error": "editor_state_unavailable"})
    if state is None:
        return json.dumps({"ok": False, "error": "editor_session_not_found"})
    commentors: list[dict[str, Any]] = state.get("commentors") or []

    found = False
    for commentor in commentors:
        if commentor.get("id") == comment_id:
            conversation: list[dict[str, Any]] = commentor.setdefault("conversation", [])
            conversation.append({"role": "agent", "content": content})
            found = True
            break

    if not found:
        return json.dumps({
            "ok": False,
            "error": "comment_not_found",
            "commentId": comment_id,
        })

    if not _save_editor_state_to_db(editor_session_id, user_id, state):
        return json.dumps({"ok": False, "error": "save_failed"})

    return json.dumps({
        "ok": True,
        "commentId": comment_id,
        "reason": reason,
        "recovered": recovered,
    }, ensure_ascii=False)


def _switch_editor(editor_session_id: str) -> str:
    """No-op MCP handler for the ``switch_editor`` context-switch tool.

    The actual editor_state switch is performed by the PostToolUse hook in
    ``agent_runner.py``, which fires *after* this handler returns.  This
    handler exists only to satisfy the MCP tool protocol: it returns a
    success acknowledgement so Claude can observe that the call completed.
    """
    return json.dumps({"ok": True, "switched": True, "editor_session_id": editor_session_id})
