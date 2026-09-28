# [Input] Consume MCP Server/types, Session retrieval and strict Dream Thread Tool contracts.
# [Output] Provide create_user_mcp_server() with Session retrieval and five Thread Tools.
# [Pos] mcp-server node in libs/claude_agent_kit/server.
# [Sync] 2026-09-28: add wait_threads as a host-authorized long-poll tool result in the current parent turn.
# [Sync] 2026-09-28: expose host-authorized create/list/read/send Thread Tools over the existing broker.
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
from hashlib import sha256

from mcp import types as mcp_types
from mcp.server import Server as McpServer

from .sessions_tool import (
    GET_SESSIONS_RANGE_TOOL_NAME,
    GET_SESSIONS_RANGE_TOOL_SPEC,
    handle_get_sessions_range,
)
from .thread_tool import THREAD_TOOL_SPECS, handle_thread_tool

USER_MCP_TOOL_NAMES: frozenset[str] = frozenset({GET_SESSIONS_RANGE_TOOL_NAME, *THREAD_TOOL_SPECS})


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
        ] + [mcp_types.Tool(name=name, description=description, inputSchema=schema)
             for name, (description, schema) in THREAD_TOOL_SPECS.items()]

    @server.call_tool()  # type: ignore[misc]
    async def call_tool(
        name: str,
        arguments: dict[str, Any] | None,
    ) -> list[mcp_types.TextContent]:
        if name == GET_SESSIONS_RANGE_TOOL_NAME:
            result_text = handle_get_sessions_range(arguments)
        elif name in THREAD_TOOL_SPECS:
            # MCP request identity is transport-owned; a model cannot choose
            # the command key or pass actor/session/process identifiers.
            call_id = sha256(repr(server.request_context.request_id).encode("utf-8")).hexdigest()
            result_text = handle_thread_tool(name, arguments, call_id)
        else:
            raise ValueError(f"Unknown tool: {name!r}")
        return [mcp_types.TextContent(type="text", text=result_text)]

    return server


__all__ = ["USER_MCP_TOOL_NAMES", "create_user_mcp_server"]
