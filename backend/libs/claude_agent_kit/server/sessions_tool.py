# [Input] Reads INK_AGENT_USER_ID from env (injected via mcp_env in AgentRunOptions).
#         Calls database.list_sessions_in_range directly (trusted subprocess context).
# [Output] Provide GET_SESSIONS_RANGE_TOOL_SPEC, handle_get_sessions_range for the
#          user MCP server (mcp__user__get_sessions_range).
# [Pos] tool-definition node in libs/claude_agent_kit/server
# [Sync] 2026-05-31: initial implementation — Agent cross-session retrieval tool.

"""MCP tool handler for ``get_sessions_range``.

Allows the Claude Agent to query journal sessions beyond the 3-day window
that is statically injected into the system prompt.

The tool runs inside the ``user`` MCP stdio subprocess.  The current user's
``user_id`` is read from the ``INK_AGENT_USER_ID`` environment variable, which
is injected into the MCP subprocess environment by the agent runner.

Session context flows via env var:

    ClaudeAgentService.assemble_context
      → run_options.mcp_env["INK_AGENT_USER_ID"] = str(request.user_id)

    agent_runner._user_mcp_stdio_config(extra_env=mcp_env)
      → McpStdioServerConfig.env["INK_AGENT_USER_ID"] = ...

    sessions_tool.handle_get_sessions_range()
      → os.getenv("INK_AGENT_USER_ID")
      → database.list_sessions_in_range(user_id, start_date, end_date)
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool spec
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SessionsToolSpec:
    """Server-owned field bundle for the get_sessions_range tool."""

    description: str
    input_schema: dict[str, Any]


GET_SESSIONS_RANGE_TOOL_NAME = "get_sessions_range"

GET_SESSIONS_RANGE_TOOL_SPEC = SessionsToolSpec(
    description=(
        "按日期范围检索用户的历史日记 session，用于发现三天前的内容。\n"
        "返回匹配 session 的 id、title、labels 和 excerpt，供 Agent 根据主题定位相关笔记。\n"
        "仅在用户提到可能早于近期条目的主题或事件时调用此工具。"
    ),
    input_schema={
        "type": "object",
        "properties": {
            "start_date": {
                "type": "string",
                "description": "查询起始日期（含），格式 YYYY-MM-DD",
            },
            "end_date": {
                "type": "string",
                "description": "查询截止日期（含），格式 YYYY-MM-DD",
            },
        },
        "required": ["start_date", "end_date"],
    },
)


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------


def handle_get_sessions_range(arguments: dict[str, Any] | None) -> str:
    """Query sessions in [start_date, end_date] for the current user.

    ``user_id`` is read from ``INK_AGENT_USER_ID`` env var (trusted subprocess).
    Returns a JSON string with a ``sessions`` list; each item contains:
    ``id``, ``name``, ``labels``, ``date``, ``excerpt``.
    """
    args = arguments or {}
    start_date: str = str(args.get("start_date") or "").strip()
    end_date: str = str(args.get("end_date") or "").strip()

    if not start_date or not end_date:
        return json.dumps({
            "ok": False,
            "error": "start_date_and_end_date_required",
            "detail": "Both start_date and end_date must be provided in YYYY-MM-DD format.",
        })

    raw_user_id = os.getenv("INK_AGENT_USER_ID", "").strip()
    if not raw_user_id:
        return json.dumps({
            "ok": False,
            "error": "user_context_unavailable",
            "detail": "INK_AGENT_USER_ID is not set in the MCP subprocess environment.",
        })

    try:
        user_id = int(raw_user_id)
    except ValueError:
        return json.dumps({
            "ok": False,
            "error": "invalid_user_id",
            "detail": f"INK_AGENT_USER_ID is not a valid integer: {raw_user_id!r}",
        })

    try:
        import database  # noqa: PLC0415 — runtime import, backend only

        rows = database.list_sessions_in_range(user_id, start_date, end_date)
    except Exception:  # noqa: BLE001
        logger.warning(
            "get_sessions_range: DB query failed; user_id=%s start=%s end=%s",
            user_id,
            start_date,
            end_date,
            exc_info=True,
        )
        return json.dumps({"ok": False, "error": "db_query_failed"})

    sessions = []
    for row in rows or []:
        raw_date = str(row.get("updated_at") or row.get("created_at") or "")[:10]
        sessions.append({
            "sessionId": row.get("id", ""),
            "name": row.get("name") or "Untitled",
            "labels": row.get("labels") or [],
            "date": raw_date,
            "excerpt": row.get("first_line") or "",
        })

    return json.dumps({"ok": True, "sessions": sessions}, ensure_ascii=False)
