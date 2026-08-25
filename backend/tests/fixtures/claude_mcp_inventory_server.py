#!/usr/bin/env python3
"""Standard-MCP inventory fixture for explicit stdio/SSE acceptance.

[Input] An explicit test-only transport plus loopback host/port and optional bounded pagination mode.
[Output] Deterministic read-only tools, resources, and prompts through the standard MCP Server API.
[Pos] Test fixture only; production policy must select it through an explicit server-owned profile.
[Sync] 2026-08-25: add normal-path stdio and legacy SSE inventory/Chat acceptance target.
[Sync] 2026-08-25: treat an explicit harness interrupt as a clean fixture shutdown receipt.
[Sync] 2026-08-25: add an opt-in two-page standard-MCP inventory for Dream cursor integration tests.
"""

from __future__ import annotations

import argparse

from mcp import types
from mcp.server.fastmcp import FastMCP


def build_server(*, host: str, port: int, paginated: bool = False) -> FastMCP:
    server = FastMCP(
        "ink-dream-mcp-transport-acceptance",
        instructions="Read-only transport acceptance fixture.",
        host=host,
        port=port,
        sse_path="/sse",
        message_path="/messages/",
        log_level="ERROR",
    )

    @server.tool(name="read_transport_status")
    async def read_transport_status() -> str:
        """Return the fixture's deterministic read-only health receipt."""

        return "ink-dream-mcp-transport-ok"

    @server.resource(
        "qa://ink-dream/transport-status",
        name="transport_status",
        description="Deterministic read-only MCP transport status.",
        mime_type="text/plain",
    )
    async def transport_status() -> str:
        return "ink-dream-mcp-resource-ok"

    @server.prompt(
        name="summarize_transport_status",
        description="Ask for a short summary of the read-only transport status.",
    )
    async def summarize_transport_status() -> str:
        return "Summarize the MCP transport status without changing remote state."

    if paginated:
        @server.tool(name="read_transport_version")
        async def read_transport_version() -> str:
            """Return the fixture protocol version without changing state."""

            return "ink-dream-mcp-pagination-v1"

        @server.resource(
            "qa://ink-dream/transport-version",
            name="transport_version",
            description="Deterministic read-only MCP transport version.",
            mime_type="text/plain",
        )
        async def transport_version() -> str:
            return "ink-dream-mcp-pagination-v1"

        @server.prompt(
            name="summarize_transport_version",
            description="Ask for a short summary of the transport version.",
        )
        async def summarize_transport_version() -> str:
            return "Summarize the MCP transport version without changing remote state."

        def request_cursor(request: object) -> str | None:
            params = getattr(request, "params", None)
            return getattr(params, "cursor", None)

        @server._mcp_server.list_tools()
        async def list_tools(request: types.ListToolsRequest) -> types.ListToolsResult:
            if request_cursor(request) is None:
                return types.ListToolsResult(
                    tools=[types.Tool(
                        name="read_transport_status",
                        description="Return the fixture's deterministic read-only health receipt.",
                        inputSchema={"type": "object", "properties": {}},
                    )],
                    nextCursor="tools-page-2",
                )
            if request_cursor(request) == "tools-page-2":
                return types.ListToolsResult(
                    tools=[types.Tool(
                        name="read_transport_version",
                        description="Return the fixture protocol version without changing state.",
                        inputSchema={"type": "object", "properties": {}},
                    )]
                )
            return types.ListToolsResult(tools=[])

        @server._mcp_server.list_resources()
        async def list_resources(
            request: types.ListResourcesRequest,
        ) -> types.ListResourcesResult:
            if request_cursor(request) is None:
                return types.ListResourcesResult(
                    resources=[types.Resource(
                        uri="qa://ink-dream/transport-status",
                        name="transport_status",
                        description="Deterministic read-only MCP transport status.",
                        mimeType="text/plain",
                    )],
                    nextCursor="resources-page-2",
                )
            if request_cursor(request) == "resources-page-2":
                return types.ListResourcesResult(
                    resources=[types.Resource(
                        uri="qa://ink-dream/transport-version",
                        name="transport_version",
                        description="Deterministic read-only MCP transport version.",
                        mimeType="text/plain",
                    )]
                )
            return types.ListResourcesResult(resources=[])

        @server._mcp_server.list_prompts()
        async def list_prompts(
            request: types.ListPromptsRequest,
        ) -> types.ListPromptsResult:
            if request_cursor(request) is None:
                return types.ListPromptsResult(
                    prompts=[types.Prompt(
                        name="summarize_transport_status",
                        description="Ask for a short summary of the read-only transport status.",
                    )],
                    nextCursor="prompts-page-2",
                )
            if request_cursor(request) == "prompts-page-2":
                return types.ListPromptsResult(
                    prompts=[types.Prompt(
                        name="summarize_transport_version",
                        description="Ask for a short summary of the transport version.",
                    )]
                )
            return types.ListPromptsResult(prompts=[])

    return server


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--transport", choices=("stdio", "sse"), required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--paginated", action="store_true")
    args = parser.parse_args()
    if args.host != "127.0.0.1":
        parser.error("fixture host must remain explicit loopback")
    if args.transport == "sse" and not (0 < args.port < 65536):
        parser.error("legacy SSE requires an explicit valid port")

    try:
        build_server(
            host=args.host,
            port=args.port,
            paginated=args.paginated,
        ).run(args.transport)
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
