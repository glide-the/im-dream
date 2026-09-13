"""Trusted MCP Apps result identity transport contracts.

[Input] Turn-local managed Server registry, SDK tool events, complete CallToolResult, and saved Chat parts.
[Output] Live SSE, persistence, public refresh, rejection, and Runner preservation assertions.
[Pos] Provider-free result-identity tests; no database, MCP network, Browser, or schema writes.
[Sync] 2026-09-06: add McpAppsToolResultProjectionV1 producer/transport/consumer coverage.
[Sync] 2026-09-06: use the official descriptor-owned UI binding and data-only CallToolResult shape.
[Sync] 2026-09-13: cover original Runtime SDK wire shapes, correlation and error fallback through history DTO.
"""

from __future__ import annotations

import asyncio
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest


BACKEND = Path(__file__).resolve().parents[2]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import tests._sdk_stubs  # noqa: E402,F401 - install SDK stubs before production imports
from claude_agent.service import (  # noqa: E402
    ClaudeAgentService,
    _TurnContext,
    _build_mcp_apps_tool_result_projection,
    _managed_mcp_tool_binding,
    _sse_events_to_ui_parts,
)
from claude_agent.tool_confirmation_store import ToolConfirmationStore  # noqa: E402
from libs.claude_agent_kit.server import agent_runner as runner_module  # noqa: E402
from libs.claude_agent_kit.types import (  # noqa: E402
    AgentStreamingCallbacks,
    ToolEventPayload,
)
from routers.claude_agent import PublicChatMessageDto  # noqa: E402


SERVER_REF = "official-basic"
REGISTERED_TOOL = "mcp__official-basic__get-time"
UPSTREAM_TOOL = "get-time"
TOOL_CALL_ID = "opaque-call-id"
TOOL_INPUT = {"timezone": "UTC"}
DESCRIPTOR_BINDINGS = {
    SERVER_REF: {UPSTREAM_TOOL: "ui://get-time/mcp-app.html"}
}


def call_tool_result() -> dict:
    return {
        "content": [{"type": "text", "text": "2026-09-06T00:00:00Z"}],
        "structuredContent": {"time": "2026-09-06T00:00:00Z"},
        "extensionResult": {"supported": True},
    }


async def emit_result(
    *,
    managed_keys: tuple[str, ...] = (SERVER_REF,),
    descriptor_bindings: dict[str, dict[str, str]] | None = None,
    result: dict | None = None,
    normalized_output: object = "ordinary-output",
    result_tool_name: str = REGISTERED_TOOL,
    is_error: bool = False,
):
    queue: asyncio.Queue = asyncio.Queue()
    context = _TurnContext(
        queue=queue,
        confirmation_store=ToolConfirmationStore(),
        managed_mcp_server_keys=managed_keys,
        managed_mcp_app_resource_bindings=deepcopy(
            DESCRIPTOR_BINDINGS
            if descriptor_bindings is None
            else descriptor_bindings
        ),
        managed_mcp_workspace_scope="workspace-1",
    )
    callback = ClaudeAgentService._make_tool_event_cb(queue, context)
    await callback(ToolEventPayload(
        type="tool_input_available",
        tool_name=REGISTERED_TOOL,
        tool_call_id=TOOL_CALL_ID,
        input=deepcopy(TOOL_INPUT),
    ))
    while not queue.empty():
        queue.get_nowait()
    await callback(ToolEventPayload(
        type="tool_result",
        tool_name=result_tool_name,
        tool_call_id=TOOL_CALL_ID,
        output=deepcopy(normalized_output),
        call_tool_result=deepcopy(result or call_tool_result()),
        is_error=is_error,
    ))
    return queue.get_nowait().payload(), context


@pytest.mark.asyncio
async def test_live_sse_and_persistence_keep_complete_result_and_trusted_identity():
    live, context = await emit_result()

    assert live["type"] == "tool-output-available"
    assert live["output"] == call_tool_result()
    projection = live["mcpAppResult"]
    assert projection == {
        "version": 1,
        "serverRef": SERVER_REF,
        "toolName": UPSTREAM_TOOL,
        "toolCallId": TOOL_CALL_ID,
        "input": TOOL_INPUT,
        "workspaceScope": "workspace-1",
        "resourceUri": "ui://get-time/mcp-app.html",
        "result": call_tool_result(),
    }
    assert projection["result"]["extensionResult"] == {"supported": True}

    parts = _sse_events_to_ui_parts(context.collected_parts)
    assert len(parts) == 1
    assert parts[0]["toolName"] == REGISTERED_TOOL
    assert parts[0]["output"] == call_tool_result()
    assert parts[0]["mcpAppResult"] == projection


@pytest.mark.asyncio
async def test_public_dto_refresh_preserves_valid_projection_losslessly():
    _, context = await emit_result()
    saved_parts = _sse_events_to_ui_parts(context.collected_parts)
    public = PublicChatMessageDto.from_storage({
        "id": "message-1",
        "role": "assistant",
        "parts": saved_parts,
        "metadata": {},
    }).model_dump(mode="json")

    part = public["parts"][0]
    assert part["toolCallId"] == TOOL_CALL_ID
    assert part["input"] == TOOL_INPUT
    assert part["output"] == call_tool_result()
    assert part["mcpAppResult"]["result"] == call_tool_result()
    assert set(part["mcpAppResult"]) == {
        "version", "serverRef", "toolName", "toolCallId", "input", "workspaceScope",
        "resourceUri", "result",
    }


def test_public_dto_recovers_existing_data_only_result_from_fresh_descriptor():
    public = PublicChatMessageDto.from_storage(
        {
            "id": "message-before-fix",
            "role": "assistant",
            "parts": [{
                "type": "tool-invocation",
                "toolName": REGISTERED_TOOL,
                "toolCallId": TOOL_CALL_ID,
                "state": "output-available",
                "input": TOOL_INPUT,
                "output": call_tool_result(),
                "dynamic": True,
            }],
            "metadata": {},
        },
        mcp_app_resource_bindings=DESCRIPTOR_BINDINGS,
    ).model_dump(mode="json")

    projection = public["parts"][0]["mcpAppResult"]
    assert projection["serverRef"] == SERVER_REF
    assert projection["toolName"] == UPSTREAM_TOOL
    assert projection["workspaceScope"] is None
    assert projection["resourceUri"] == "ui://get-time/mcp-app.html"
    assert projection["result"] == call_tool_result()


def test_public_dto_does_not_probe_an_ordinary_saved_mcp_result():
    public = PublicChatMessageDto.from_storage(
        {
            "id": "ordinary-message",
            "role": "assistant",
            "parts": [{
                "type": "tool-invocation",
                "toolName": "mcp__ordinary__read-status",
                "toolCallId": TOOL_CALL_ID,
                "state": "output-available",
                "input": {},
                "output": call_tool_result(),
            }],
            "metadata": {},
        },
        mcp_app_resource_bindings=DESCRIPTOR_BINDINGS,
    ).model_dump(mode="json")

    assert "mcpAppResult" not in public["parts"][0]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("managed_keys", "result_tool_name"),
    [
        ((), REGISTERED_TOOL),
        (("stale-server",), REGISTERED_TOOL),
        ((SERVER_REF, SERVER_REF), REGISTERED_TOOL),
        ((SERVER_REF,), "mcp__other-server__get-time"),
    ],
)
async def test_missing_stale_ambiguous_or_conflicting_binding_drops_only_projection(
    managed_keys, result_tool_name
):
    live, context = await emit_result(
        managed_keys=managed_keys,
        result_tool_name=result_tool_name,
    )

    assert "mcpAppResult" not in live
    assert live["output"] == "ordinary-output"
    part = _sse_events_to_ui_parts(context.collected_parts)[0]
    assert "mcpAppResult" not in part
    assert part["output"] == "ordinary-output"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mutate",
    [
        lambda result: result.pop("content"),
        lambda result: result.update(
            {"headers": {"Authorization": "Bearer secret"}}
        ),
        lambda result: result.update({"isError": True}),
    ],
)
async def test_malformed_mismatch_or_sensitive_result_drops_only_apps_projection(mutate):
    result = call_tool_result()
    mutate(result)
    live, context = await emit_result(result=result)

    assert "mcpAppResult" not in live
    assert live["output"] == "ordinary-output"
    part = _sse_events_to_ui_parts(context.collected_parts)[0]
    assert part["output"] == "ordinary-output"
    assert "mcpAppResult" not in part


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "descriptor_bindings",
    [
        {},
        {SERVER_REF: {UPSTREAM_TOOL: "https://not-ui.invalid/app"}},
        {SERVER_REF: {"other-tool": "ui://get-time/mcp-app.html"}},
    ],
)
async def test_missing_or_invalid_descriptor_binding_drops_only_projection(
    descriptor_bindings,
):
    live, context = await emit_result(descriptor_bindings=descriptor_bindings)

    assert "mcpAppResult" not in live
    assert live["output"] == "ordinary-output"
    part = _sse_events_to_ui_parts(context.collected_parts)[0]
    assert part["output"] == "ordinary-output"
    assert "mcpAppResult" not in part


@pytest.mark.asyncio
async def test_call_result_ui_metadata_cannot_override_descriptor_binding():
    result = call_tool_result()
    result["_meta"] = {
        "ui": {"resourceUri": "ui://attacker/other.html"},
        "serverRef": "attacker-server",
    }
    live, _context = await emit_result(result=result)

    assert live["mcpAppResult"]["resourceUri"] == (
        "ui://get-time/mcp-app.html"
    )
    assert live["mcpAppResult"]["result"] == result


def test_persistence_and_public_projection_reject_tampering_without_touching_output():
    result = call_tool_result()
    projection = _build_mcp_apps_tool_result_projection(
        managed_server_keys=(SERVER_REF,),
        managed_app_resource_bindings=DESCRIPTOR_BINDINGS,
        managed_workspace_scope="workspace-1",
        registered_tool_name=REGISTERED_TOOL,
        tool_call_id=TOOL_CALL_ID,
        tool_input=TOOL_INPUT,
        call_tool_result=result,
        is_error=False,
    )
    assert projection is not None
    projection["toolCallId"] = "mismatched-call"
    events = [
        {
            "type": "tool-input-available",
            "toolCallId": TOOL_CALL_ID,
            "toolName": REGISTERED_TOOL,
            "input": TOOL_INPUT,
        },
        {
            "type": "tool-output-available",
            "toolCallId": TOOL_CALL_ID,
            "output": result,
            "isError": False,
            "mcpAppResult": projection,
        },
    ]
    part = _sse_events_to_ui_parts(events)[0]
    assert part["output"] == result
    assert "mcpAppResult" not in part

    public_source = dict(part)
    public_source["mcpAppResult"] = {
        **projection,
        "toolCallId": TOOL_CALL_ID,
        "version": 2,
    }
    public = PublicChatMessageDto.from_storage({
        "id": "message-tampered",
        "role": "assistant",
        "parts": [public_source],
        "metadata": {},
    })
    assert public.parts[0]["output"] == result
    assert "mcpAppResult" not in public.parts[0]


def test_tool_call_id_is_only_correlation_not_owner_authorization():
    first = _build_mcp_apps_tool_result_projection(
        managed_server_keys=(SERVER_REF,),
        managed_app_resource_bindings=DESCRIPTOR_BINDINGS,
        managed_workspace_scope=None,
        registered_tool_name=REGISTERED_TOOL,
        tool_call_id="arbitrary-opaque-id",
        tool_input=TOOL_INPUT,
        call_tool_result=call_tool_result(),
        is_error=False,
    )
    missing_owner = _build_mcp_apps_tool_result_projection(
        managed_server_keys=(),
        managed_app_resource_bindings=DESCRIPTOR_BINDINGS,
        managed_workspace_scope=None,
        registered_tool_name=REGISTERED_TOOL,
        tool_call_id="arbitrary-opaque-id",
        tool_input=TOOL_INPUT,
        call_tool_result=call_tool_result(),
        is_error=False,
    )
    assert first is not None
    assert first["toolCallId"] == "arbitrary-opaque-id"
    assert missing_owner is None
    assert _managed_mcp_tool_binding(REGISTERED_TOOL, ()) is None


@pytest.mark.asyncio
async def test_error_result_remains_ordinary_on_live_and_persisted_paths():
    result = call_tool_result()
    result["isError"] = True
    live, context = await emit_result(
        result=result,
        normalized_output=result,
        is_error=True,
    )
    assert live["isError"] is True
    assert live["output"] == result
    assert "mcpAppResult" not in live
    part = _sse_events_to_ui_parts(context.collected_parts)[0]
    assert part["state"] == "output-error"
    assert part["output"] == result
    assert "mcpAppResult" not in part

    forged_projection = {
        "version": 1,
        "serverRef": SERVER_REF,
        "toolName": UPSTREAM_TOOL,
        "toolCallId": TOOL_CALL_ID,
        "input": TOOL_INPUT,
        "workspaceScope": "workspace-1",
        "resourceUri": "ui://get-time/mcp-app.html",
        "result": result,
    }
    public = PublicChatMessageDto.from_storage({
        "id": "message-error",
        "role": "assistant",
        "parts": [{
            "type": "dynamic-tool",
            "toolName": REGISTERED_TOOL,
            "toolCallId": TOOL_CALL_ID,
            "state": "output-error",
            "input": TOOL_INPUT,
            "output": result,
            "mcpAppResult": forged_projection,
        }],
        "metadata": {},
    })
    assert public.parts[0]["output"] == result
    assert "mcpAppResult" not in public.parts[0]


@pytest.mark.asyncio
async def test_runner_preserves_full_unambiguous_call_tool_result_beside_legacy_output():
    result = call_tool_result()
    message = runner_module.UserMessage(content=[{
        "type": "tool_result",
        "tool_use_id": TOOL_CALL_ID,
        "content": [{"type": "text", "text": '{"ordinary":true}'}],
        "is_error": False,
    }])
    message.tool_use_result = deepcopy(result)
    captured: list[ToolEventPayload] = []
    callbacks = AgentStreamingCallbacks(
        on_text_delta=lambda _delta: None,
        on_tool_event=lambda payload: captured.append(payload),
    )
    runner = runner_module.ClaudeAgentRunner(sdk_client=SimpleNamespace())

    await runner._process_message(
        message,
        callbacks,
        pending_tool_calls={
            TOOL_CALL_ID: {"tool_name": REGISTERED_TOOL, "input": TOOL_INPUT}
        },
        emitted_tool_input_ids=set(),
        on_text_accumulate=lambda _text: None,
    )

    assert len(captured) == 1
    assert captured[0].output == {"ordinary": True}
    assert captured[0].call_tool_result == result


@pytest.mark.asyncio
async def test_runner_does_not_attach_one_complete_result_to_ambiguous_blocks():
    message = runner_module.UserMessage(content=[
        {"type": "tool_result", "tool_use_id": "call-1", "content": "one"},
        {"type": "tool_result", "tool_use_id": "call-2", "content": "two"},
    ])
    message.tool_use_result = call_tool_result()
    captured: list[ToolEventPayload] = []
    callbacks = AgentStreamingCallbacks(
        on_text_delta=lambda _delta: None,
        on_tool_event=lambda payload: captured.append(payload),
    )
    runner = runner_module.ClaudeAgentRunner(sdk_client=SimpleNamespace())
    await runner._process_message(
        message,
        callbacks,
        pending_tool_calls={},
        emitted_tool_input_ids=set(),
        on_text_accumulate=lambda _text: None,
    )
    assert len(captured) == 2
    assert all(payload.call_tool_result is None for payload in captured)


@pytest.mark.asyncio
@pytest.mark.parametrize("wire_form", ["array", "text", "text-envelope", "complete-envelope"])
@pytest.mark.parametrize("is_error", [False, True])
async def test_original_runtime_wire_result_reaches_live_saved_and_public_app(wire_form, is_error):
    # Original Runtime emits processed content, optionally with mcpMeta.
    # The SDK value, not the normalized model block, owns this adaptation.
    raw_content = [{"type": "text", "text": '{"time":"fixture-time"}'}]
    expected = {"content": deepcopy(raw_content)}
    raw_result = deepcopy(raw_content)
    if wire_form == "text":
        raw_result = raw_content[0]["text"]
    elif wire_form in {"text-envelope", "complete-envelope"}:
        expected.update({"structuredContent": {"time": "fixture-time"}, "extensionResult": {"supported": True}})
        raw_result = deepcopy(expected)
        if wire_form == "text-envelope":
            raw_result["content"] = raw_content[0]["text"]
    message = runner_module.UserMessage(content=[{
        "type": "tool_result", "tool_use_id": TOOL_CALL_ID,
        "content": [{"type": "text", "text": '{"model_block":"not-sdk-wire"}'}], "is_error": is_error,
    }])
    message.tool_use_result = deepcopy(raw_result)
    queue: asyncio.Queue = asyncio.Queue()
    context = _TurnContext(
        queue=queue, confirmation_store=ToolConfirmationStore(),
        managed_mcp_server_keys=(SERVER_REF,),
        managed_mcp_app_resource_bindings=deepcopy(DESCRIPTOR_BINDINGS),
    )
    callback = ClaudeAgentService._make_tool_event_cb(queue, context)
    await callback(ToolEventPayload(
        type="tool_input_available", tool_name=REGISTERED_TOOL,
        tool_call_id=TOOL_CALL_ID, input=deepcopy(TOOL_INPUT),
    ))
    while not queue.empty():
        queue.get_nowait()
    runner = runner_module.ClaudeAgentRunner(sdk_client=SimpleNamespace())
    await runner._process_message(
        message,
        AgentStreamingCallbacks(on_text_delta=lambda _text: None, on_tool_event=callback),
        pending_tool_calls={TOOL_CALL_ID: {"tool_name": REGISTERED_TOOL, "input": TOOL_INPUT}},
        emitted_tool_input_ids=set(), on_text_accumulate=lambda _text: None,
    )
    live = queue.get_nowait().payload()
    public = PublicChatMessageDto.from_storage({
        "id": "original-runtime-wire", "role": "assistant",
        "parts": _sse_events_to_ui_parts(context.collected_parts), "metadata": {},
    }).model_dump(mode="json")
    if is_error:
        assert live["isError"] is True
        assert live["output"] == {"model_block": "not-sdk-wire"}
        assert "mcpAppResult" not in live
        assert public["parts"][0]["state"] == "output-error"
        assert "mcpAppResult" not in public["parts"][0]
        assert message.tool_use_result == raw_result
        return
    assert live["output"] == expected
    assert live["mcpAppResult"]["resourceUri"] == DESCRIPTOR_BINDINGS[SERVER_REF][UPSTREAM_TOOL]
    assert live["mcpAppResult"]["result"] == expected
    assert public["parts"][0]["output"] == expected
    assert public["parts"][0]["mcpAppResult"] == live["mcpAppResult"]
    assert message.tool_use_result == raw_result


@pytest.mark.asyncio
@pytest.mark.parametrize("registered_name,block_count", [("Read", 1), (None, 1), (REGISTERED_TOOL, 2)])
@pytest.mark.parametrize("raw_result", ["raw-text", [{"type": "text", "text": "raw-array"}]])
async def test_wire_content_needs_single_correlated_mcp_call(registered_name, block_count, raw_result):
    message = runner_module.UserMessage(content=[{
        "type": "tool_result", "tool_use_id": f"call-{index}", "content": "ordinary",
    } for index in range(block_count)])
    message.tool_use_result = deepcopy(raw_result)
    captured = []
    runner = runner_module.ClaudeAgentRunner(sdk_client=SimpleNamespace())
    await runner._process_message(
        message, AgentStreamingCallbacks(on_text_delta=lambda _text: None, on_tool_event=captured.append),
        pending_tool_calls={"call-0": {"tool_name": registered_name}} if registered_name else {},
        emitted_tool_input_ids=set(), on_text_accumulate=lambda _text: None,
    )
    assert len(captured) == block_count
    assert all(payload.call_tool_result is None for payload in captured)
    assert all(payload.output == "ordinary" for payload in captured)
