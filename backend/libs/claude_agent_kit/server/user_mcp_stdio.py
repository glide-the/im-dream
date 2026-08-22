# [Input] Consume create_user_mcp_server from mcp_server.py and MCP stdio transport.
# [Output] Run the Ink session-retrieval MCP namespace as a standalone stdio server.
# [Pos] stdio-mcp-entrypoint node in libs/claude_agent_kit/server
# [Sync] 2026-05-09: expose touch_animation over independent stdio MCP to avoid SDK stdin control-channel conflicts.
# [Sync] 2026-08-22: narrow the retained stdio process to get_sessions_range;
#                    Pawkeyland touch animation is not an Ink capability.

"""Standalone stdio MCP entrypoint for Ink's ``user`` tool namespace.

The Claude Code Python SDK's in-process ``type="sdk"`` MCP bridge shares the
same CLI stdin stream used for prompt input and SDK control responses. The runner
uses a single user prompt that is expected to reach EOF, so the embedded bridge
can later fail when it tries to write MCP/control responses to an already closed
transport.

Running the user MCP server as a normal stdio child process keeps the prompt
stream and tool protocol separate. Claude sees the existing core tool name
``mcp__user__get_sessions_range``.
"""
from __future__ import annotations

import asyncio

from mcp.server.stdio import stdio_server

from .mcp_server import create_user_mcp_server


async def main() -> None:
    """Start the user MCP server on stdin/stdout."""

    server = create_user_mcp_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
