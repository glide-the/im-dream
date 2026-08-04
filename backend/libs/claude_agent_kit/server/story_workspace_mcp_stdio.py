"""stdio entrypoint for the Story Workspace MCP namespace."""

from __future__ import annotations

import asyncio

from mcp.server.stdio import stdio_server

from .story_workspace_mcp_server import create_story_workspace_mcp_server


async def main() -> None:
    """Run the server without writing application logs to stdout."""

    server = create_story_workspace_mcp_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
