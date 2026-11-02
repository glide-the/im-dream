# [Sync] 2026-10-25: accept an explicit per-server broker context for embedded MCP; default stdio behavior and tool schemas remain unchanged.
# [Sync] 2026-10-10: bind image operation/model ownership and preserve real call identity through original authorization, files and history.
# [Sync] 2026-10-10: separate saved AI/Image ownership; validate native Responses results through the Gateway bridge.
# [Input] Existing turn-local broker tuple; model supplies only prompt and reference_images.
# [Output] imagegen MCP calls with JSON file references or redacted tool errors.
# [Pos] Independent stdio MCP entrypoint for internal image_gen; no Admin/Provider credentials.
# [Sync] 2026-10-10: expose generation/editing through the original CLI MCP transport.
from __future__ import annotations

import asyncio
import os
import json
import re
from .image_generation_protocol import ImageToolInput, ImageSelectionInput, request_image, request_image_selection
from .session_projection_protocol import SESSION_BROKER_ENV_NAMES, SessionProjectionBrokerClient, SessionProjectionProtocolError


def create_image_gen_server(*, environment=None):
    from mcp.server import Server
    from mcp.types import Tool, TextContent
    server = Server("image_gen")

    @server.list_tools()
    async def list_tools():
        return [Tool(name="select_image_operation", description="Before executing any image generation or editing, select the operation intended by the current user message. Ordinary image requests select native_generate or native_edit for the AI model's Responses capability. Select image_gen_generate or image_gen_edit only when the user explicitly requests execution of image_gen; discussing, quoting or asking about its purpose selects none. Uploads and sketches alone do not request an operation. For ambiguous requests select unclear and explain what input is missing. Use only current message reference image URIs. This step records a decision, never generates an image or changes the selected models. After a native selection, continue the conversation to receive the server image result; do not call imagegen. Never fallback or execute both routes.", inputSchema=ImageSelectionInput.model_json_schema()),
            Tool(name="imagegen", description="Execute only after select_image_operation has selected image_gen_generate or image_gen_edit for the user's explicit image_gen request. Use the same prompt and current reference_images. The server uses the separately saved Image model; do not choose a model. Return resulting images inline using Markdown image syntax. Editing creates new files and retains originals.", inputSchema=ImageToolInput.model_json_schema())]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        try:
            if name not in {"imagegen", "select_image_operation"}:
                raise ValueError("Unknown tool")
            meta = server.request_context.meta
            values = meta.model_dump() if hasattr(meta, "model_dump") else meta
            source_id = values.get("claudecode/toolUseId") if isinstance(values, dict) else None
            if not isinstance(source_id, str) or re.fullmatch(r"[A-Za-z0-9._:-]{1,200}", source_id) is None:
                raise SessionProjectionProtocolError("IMAGE_CALL_ID_REQUIRED", 403)
            client = SessionProjectionBrokerClient.from_env(dict(os.environ if environment is None else environment))
            if name == "select_image_operation":
                input_dto = ImageSelectionInput.model_validate(arguments)
                selected = await asyncio.to_thread(request_image_selection, client, input_dto.model_dump(), source_id)
                return [TextContent(type="text", text=json.dumps(selected))]
            input_dto = ImageToolInput.model_validate(arguments)
            result = await asyncio.to_thread(request_image, client, input_dto.model_dump(), source_id)
            return [TextContent(type="text", text=result.model_dump_json())]
        except SessionProjectionProtocolError as error:
            # Use MCP isError; never echo Provider body, prompt, path or credentials.
            from mcp.types import CallToolResult
            return CallToolResult(isError=True, content=[TextContent(type="text", text={
                "IMAGE_MODEL_NOT_SELECTED": "No Image model is selected. Open Settings, choose an available Image model, then send a new explicit image_gen request.",
                "AI_MODEL_IMAGE_OPERATION_UNAVAILABLE": "The selected AI model cannot perform this image operation. Open Settings and select an AI model with the required available image capability, or choose an Image model and send a new explicit image_gen request. No image operation was started.",
                "IMAGE_MODEL_SELECTION_STALE": "The saved Image model is no longer available. Open Settings and choose another Image model before retrying.",
                "IMAGE_MODEL_OPERATION_UNSUPPORTED": "The selected Image model does not support this operation. Choose an Image model with the required generation or editing capability in Settings.",
                "IMAGE_MODEL_UNAVAILABLE": "No available image model. Check the Image model configuration and access.",
                "IMAGE_REFERENCE_UNAVAILABLE": "The reference image is unavailable. Add an accessible image to the current message before sending a new request.",
                "IMAGE_REFERENCE_DENIED": "Add the conversation image to the current message before editing.",
                "IMAGE_TURN_CONFIGURATION_UNAVAILABLE": "Image operations are not ready on the server. Keep the saved model choices and retry after the image capability is available.",
                "IMAGE_TURN_OUTCOME_UNKNOWN": "The image decision could not be confirmed. Check this conversation before sending a new request; the operation was not repeated.",
                "IMAGE_TURN_SELECTION_MISMATCH": "This tool does not match the selected image operation. Check this conversation and send a new explicit image_gen request if that is your intended action.",
                "IMAGE_CALL_NOT_AUTHORIZED": "The image tool call could not be matched to this conversation. It was not executed. Check this conversation before sending a new request.",
                "IMAGE_SCOPE_REQUIRED": "Image access is not enabled for this account.",
                "IMAGE_CANCELLED": "Image generation was stopped. Completed images are retained.",
                "IMAGE_FILE_SAVE_FAILED": "The generated image could not be saved.",
                "IMAGE_RESULT_INVALID": "The image service returned an invalid result.",
                "IMAGE_GATEWAY_RESPONSE_INVALID": "The image service response has no valid Gateway request identity. The request was not repeated; check the Gateway request history before starting a new request.",
                "IMAGE_DECODE_INVALID": "The image cannot be used for this operation. Add a PNG, JPEG or WebP image to the current message.",
                "IMAGE_REQUEST_OUTCOME_UNKNOWN": "The connection failed. Completion and charges are unknown; the request was not repeated.",
            }.get(error.code, "The image request failed.") + f" ({error.code})")])
        except Exception:
            from mcp.types import CallToolResult
            return CallToolResult(isError=True, content=[TextContent(type="text", text="IMAGE_INPUT_OR_RESULT_INVALID")])
    return server


async def main():
    from mcp.server.stdio import stdio_server
    server = create_image_gen_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    projected = {key: os.environ[key] for key in SESSION_BROKER_ENV_NAMES if os.environ.get(key)}
    os.environ.clear()
    os.environ.update(projected)
    asyncio.run(main())
