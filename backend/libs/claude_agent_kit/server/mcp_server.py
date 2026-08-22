# [Input] Consume MCP Server/types and the current Ink sessions_tool contract.
# [Output] Provide create_user_mcp_server() with only get_sessions_range.
# [Pos] mcp-server node in libs/claude_agent_kit/server.
# [Sync] 2026-08-22: remove the unmigrated Pawkeyland touch-animation schema,
#                    dictionary materialization, imports, and handler from Ink's user MCP.

"""MCP server factory for the current Ink ``user`` namespace.

The user stdio process is retained for the core ``get_sessions_range`` Chat
history capability. Pawkeyland's touch-animation surface is intentionally not
registered: Ink has no animation layer, and exposing the schema would add
irrelevant startup/context work to every Claude turn.
"""
from __future__ import annotations

from typing import Any

from mcp import types as mcp_types
from mcp.server import Server as McpServer

from .sessions_tool import (
    GET_SESSIONS_RANGE_TOOL_NAME,
    GET_SESSIONS_RANGE_TOOL_SPEC,
    handle_get_sessions_range,
)

USER_MCP_TOOL_NAMES: frozenset[str] = frozenset({GET_SESSIONS_RANGE_TOOL_NAME})


def create_user_mcp_server() -> McpServer:
    """Create the external stdio server for Ink's current user tools."""

    server = McpServer("user")

    @server.list_tools()  # type: ignore[misc]
    async def list_tools() -> list[mcp_types.Tool]:
        return [
            mcp_types.Tool(
                name=GET_SESSIONS_RANGE_TOOL_NAME,
                description=GET_SESSIONS_RANGE_TOOL_SPEC.description,
                inputSchema=GET_SESSIONS_RANGE_TOOL_SPEC.input_schema,
            )
        ]

    @server.call_tool()  # type: ignore[misc]
    async def call_tool(
        name: str,
        arguments: dict[str, Any] | None,
    ) -> list[mcp_types.TextContent]:
        if name != GET_SESSIONS_RANGE_TOOL_NAME:
            raise ValueError(f"Unknown tool: {name!r}")
        result_text = handle_get_sessions_range(arguments)
        return [mcp_types.TextContent(type="text", text=result_text)]

    return server


__all__ = ["USER_MCP_TOOL_NAMES", "create_user_mcp_server"]
