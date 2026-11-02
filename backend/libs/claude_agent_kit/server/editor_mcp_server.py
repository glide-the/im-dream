# [Sync] 2026-10-25: accept an explicit per-server broker context for embedded MCP; default stdio behavior and tool schemas remain unchanged.
# [Input] Existing Editor tool schemas/handlers and an optional turn-owned broker environment.
# [Output] Provide the original write-only Editor MCP server with one broker client per explicit server context.
# [Pos] mcp-server node in libs/claude_agent_kit/server
# [Sync] 2026-05-28: initial implementation — read-only EditorState MCP server.
# [Sync] 2026-05-29: update [Input] header to trace the editor_index.py mapping origin.
# [Sync] 2026-05-29: switch from read-only tools to write-only tools (EDITOR_WRITE_TOOL_SPECS /
#                    handle_editor_write_tool); reading is exclusively via .editor/ virtual
#                    index PreToolUse interception in agent_runner.py.

from __future__ import annotations

from typing import Any, Optional

from mcp import types as mcp_types
from mcp.server import Server as McpServer

from .editor_tool import EDITOR_WRITE_TOOL_SPECS, handle_editor_write_tool
from services.admin_data.editor_runtime import EditorBrokerClient


def create_editor_mcp_server(*, environment=None) -> McpServer:
    """Create the write-only editor MCP server.

    Claude sees this server under the ``editor`` namespace, so the tools
    available in prompts/allowlists are ``mcp__editor__{tool_name}``.

    All tools require human confirmation via the PreToolUse hook before
    execution (registered in ``_ALWAYS_CONFIRM_TOOL_NAMES`` in agent_runner.py).
    """

    server = McpServer("editor")
    context = {} if environment is None else {"client": EditorBrokerClient.from_env(dict(environment))}

    @server.list_tools()  # type: ignore[misc]
    async def list_tools() -> list[mcp_types.Tool]:
        return [
            mcp_types.Tool(
                name=name,
                description=spec.description,
                inputSchema=spec.input_schema,
            )
            for name, spec in EDITOR_WRITE_TOOL_SPECS.items()
        ]

    @server.call_tool()  # type: ignore[misc]
    async def call_tool(
        name: str,
        arguments: Optional[dict[str, Any]],
    ) -> list[mcp_types.TextContent]:
        if name not in EDITOR_WRITE_TOOL_SPECS:
            raise ValueError(f"Unknown tool: {name!r}")
        result_text = handle_editor_write_tool(name, arguments, **context)
        return [mcp_types.TextContent(type="text", text=result_text)]

    return server
