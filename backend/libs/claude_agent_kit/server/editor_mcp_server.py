# [Input] Consume EditorNoInput, EDITOR_TOOL_SPECS, get_editor_resource_handler
#         from editor_tool.py.
# [Output] Provide create_editor_mcp_server() for the stdio MCP entrypoint.
# [Pos] mcp-server node in libs/claude_agent_kit/server
# [Sync] 2026-05-23: initial implementation — EditorEngine live-state read tools.

from __future__ import annotations

from typing import Any, Optional

from mcp import types as mcp_types
from mcp.server import Server as McpServer

from .editor_tool import EDITOR_TOOL_SPECS, EditorNoInput, get_editor_resource_handler


def create_editor_mcp_server() -> McpServer:
    """Create the read-only EditorEngine MCP server under the ``editor`` namespace.

    Claude sees this server under the ``editor`` namespace, so the tools
    available in prompts/allowlists are ``mcp__editor__{tool_name}``.
    """

    server = McpServer("editor")
    input_schema = EditorNoInput.model_json_schema()
    shared_description = (
        "\n只读，不修改编辑器状态。不要传任何参数：tool name 就是查询意图；"
        "session_id 和内部 API 地址全部由服务端环境变量绑定。"
        "工具返回 JSON，其中 data 字段是可引用的 EditorState 数据。"
        "如果 ok=false 表示本次无法获取数据，请说明无法读取当前文档状态。"
    )

    @server.list_tools()  # type: ignore[misc]
    async def list_tools() -> list[mcp_types.Tool]:
        return [
            mcp_types.Tool(
                name=name,
                description=f"{spec.description}{shared_description}",
                inputSchema=input_schema,
            )
            for name, spec in EDITOR_TOOL_SPECS.items()
        ]

    @server.call_tool()  # type: ignore[misc]
    async def call_tool(
        name: str,
        arguments: Optional[dict[str, Any]],
    ) -> list[mcp_types.TextContent]:
        if name not in EDITOR_TOOL_SPECS:
            raise ValueError(f"Unknown tool: {name!r}")
        try:
            EditorNoInput.model_validate(arguments or {})
        except Exception as exc:  # noqa: BLE001
            return [
                mcp_types.TextContent(
                    type="text",
                    text=f'{{"ok":false,"error":"invalid_input:{str(exc)[:160]}","data":null}}',
                )
            ]
        result_text = await get_editor_resource_handler(name)
        return [mcp_types.TextContent(type="text", text=result_text)]

    return server


__all__ = ["create_editor_mcp_server"]
