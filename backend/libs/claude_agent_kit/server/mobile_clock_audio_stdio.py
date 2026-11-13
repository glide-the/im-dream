# [Input] Backend-owned mobile audio MCP factory and the existing stdio transport.
# [Output] Opt-in audio metadata tools; no credentials or audio execution.
# [Pos] mobile_clock_audio stdio entrypoint, also adapted by the iOS MCP bridge.
from __future__ import annotations

import asyncio
import os

from mcp.server.stdio import stdio_server

from .editor_mcp_server import create_mobile_clock_audio_mcp_server


async def main() -> None:
    server = create_mobile_clock_audio_mcp_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    os.environ.clear()
    asyncio.run(main())
