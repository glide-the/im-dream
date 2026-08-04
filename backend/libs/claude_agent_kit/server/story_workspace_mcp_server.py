"""Write-only Story Workspace MCP server."""

from __future__ import annotations

from typing import Any, Optional

from mcp import types as mcp_types
from mcp.server import Server as McpServer

from .story_workspace_tool import (
    STORY_WORKSPACE_DREAM_TOOL_SPECS,
    story_workspace_handle_dream_tool,
)


def story_workspace_create_mcp_server() -> McpServer:
    """Create the local controlled Dream-write MCP namespace."""

    server = McpServer("story_workspace")

    @server.list_tools()  # type: ignore[misc]
    async def list_tools() -> list[mcp_types.Tool]:
        return [
            mcp_types.Tool(
                name=name,
                description=spec.description,
                inputSchema=spec.input_schema,
                annotations=mcp_types.ToolAnnotations(
                    readOnlyHint=False,
                    destructiveHint=False,
                    idempotentHint=False,
                    openWorldHint=False,
                ),
            )
            for name, spec in STORY_WORKSPACE_DREAM_TOOL_SPECS.items()
        ]

    @server.call_tool()  # type: ignore[misc]
    async def call_tool(
        name: str,
        arguments: Optional[dict[str, Any]],
    ) -> list[mcp_types.TextContent]:
        if name not in STORY_WORKSPACE_DREAM_TOOL_SPECS:
            raise ValueError("Unknown Story Workspace tool")
        result_text = story_workspace_handle_dream_tool(name, arguments)
        return [mcp_types.TextContent(type="text", text=result_text)]

    return server


__all__ = ["story_workspace_create_mcp_server"]
