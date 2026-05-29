# [Input] Consume EDITOR_READ_TOOL_SPECS, handle_editor_read_tool from editor_tool.py.
#         editor_tool.py in turn derives field names from editor_index.EDITOR_RESOURCES,
#         making editor_index.py the ultimate source of the virtual index mapping rules.
# [Output] Provide create_editor_mcp_server() for the stdio MCP entrypoint.
# [Pos] mcp-server node in libs/claude_agent_kit/server
# [Sync] 2026-05-28: initial implementation — read-only EditorState MCP server.
# [Sync] 2026-05-29: update [Input] header to trace the editor_index.py mapping origin.

from __future__ import annotations

from typing import Any, Optional

from mcp import types as mcp_types
from mcp.server import Server as McpServer

from .editor_tool import EDITOR_READ_TOOL_SPECS, handle_editor_read_tool


def create_editor_mcp_server() -> McpServer:
    """Create the read-only editor MCP server.

    Claude sees this server under the ``editor`` namespace, so the tools
    available in prompts/allowlists are ``mcp__editor__{tool_name}``.
    """

    server = McpServer("editor")

    @server.list_tools()  # type: ignore[misc]
    async def list_tools() -> list[mcp_types.Tool]:
        return [
            mcp_types.Tool(
                name=name,
                description=spec.description,
                inputSchema=spec.input_schema,
            )
            for name, spec in EDITOR_READ_TOOL_SPECS.items()
        ]

    @server.call_tool()  # type: ignore[misc]
    async def call_tool(
        name: str,
        arguments: Optional[dict[str, Any]],
    ) -> list[mcp_types.TextContent]:
        if name not in EDITOR_READ_TOOL_SPECS:
            raise ValueError(f"Unknown tool: {name!r}")
        result_text = handle_editor_read_tool(name, arguments)
        return [mcp_types.TextContent(type="text", text=result_text)]

    return server
