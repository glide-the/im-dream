# [Sync] 2026-10-10: separate saved AI/Image ownership; Responses images stay disabled pending a complete bridge.
# [Input] Synthetic Gateway responses, actual private broker, production Service and temporary Thread files.
# [Output] PNG input/reference/edit and generation/save/reopen contracts plus denial and cancellation evidence.
# [Pos] Provider-free image tool integration tests; no normal service, account, model or database.
# [Sync] 2026-10-10: exercise existing public protocol/Service persistence boundaries with injected providers.
# [Sync] 2026-10-10: assert canonical files/ paths used by actual public preview and editing.
# [Sync] 2026-10-10: connect the uploaded sketch's visual block and same-file edit reference through production helpers.
from __future__ import annotations

import asyncio
import base64
import io
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from urllib.parse import quote

from PIL import Image
import pytest

import tests._sdk_stubs  # noqa: F401 — use the repository-wide deterministic SDK fixture before any Kit import

from libs.claude_agent_kit.server.image_generation_protocol import IMAGE_TOOL_NAME, ImageGenerationRequest, ImageToolInput, request_image as raw_request_image
from libs.claude_agent_kit.server.session_projection_protocol import SessionProjectionBrokerClient
from libs.claude_agent_kit.server.workspace import read_workspace_file_content
from libs.claude_agent_kit.server.workspace_file_sync import save_buffer_to_workspace_files
from libs.claude_agent_kit.messages.build_user_message_content import AttachmentPayload
from claude_agent.context_builder import ClaudeAgentContextBuilder
from services.admin_gateway.config import AdminGatewayConfig
from services.admin_gateway.images import ImageGenerationProvider
from services.admin_gateway.models import GatewayModelCatalogClient
from services.admin_data.errors import AdminDataError
from tests._image_turn_fixtures import ImageDataFixture, select_provider, authorize_execution, request_image
from services.admin_data.agent_turn_persistence import AdminAgentTurnPersistence
from services.admin_data.session_projection_broker import SessionProjectionBroker, SessionProjectionBrokerSettings
from claude_agent.service import ClaudeAgentService, ClaudeAgentRunRequest, _TurnContext, _TurnExecution, _sse_events_to_ui_parts
from claude_agent.thread_pool import AgentRunState
from claude_agent.tool_confirmation_store import ToolConfirmationStore
from libs.claude_agent_kit.types import AgentRunResult, ToolEventPayload


def picture():
    stream = io.BytesIO()
    Image.new("RGB", (8, 8), "blue").save(stream, "PNG")
    return stream.getvalue()


def model(alias="image-a"):
    return {"id": alias, "display_name": "Image", "protocol": "openai", "capabilities": {"chat": False, "image_generation": True, "image_edit": True}, "context_window": None, "max_output_tokens": None, "claude_code_auto_compact_window": None, "claude_code_max_context_tokens": None, "enabled": True, "callable": True, "availability": "included", "required_plan_code": None, "upgrade_hint": None, "image_input_token_reserve_per_image": 100, "image_output_token_reserve_per_image": 100, "endpoint_availability": {"messages": {"callable": False, "entitled": False}, "chat": {"callable": False, "entitled": False}, "images": {"callable": True, "entitled": True, "configured": True, "generation": True, "edit": True}}}


class Response:
    def __init__(self, payload, status=200):
        self.payload, self.status_code = payload, status
        self.headers = {'x-request-id': 'req_00000000000040008000000000000001'}
    def json(self):
        return self.payload
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def iter_content(self, size):
        yield json.dumps(self.payload).encode()


class Transport:
    def __init__(self):
        self.calls = []
        self.catalog = {"object": "list", "data": [model()], "default_model_alias": "image-a"}
        self.result = {"created": 1, "data": [{"b64_json": base64.b64encode(picture()).decode()}]}
        self.status = 200
        self.on_post = None
    def get(self, url, **kwargs):
        return Response(self.catalog)
    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self.on_post:
            self.on_post()
        return Response(self.result, self.status)


@pytest.fixture
def bound(tmp_path):
    transport = Transport()
    (tmp_path / "files").mkdir()
    runtime = SimpleNamespace(allows=lambda scope: scope == "images:create", access_token=lambda: "idg_" + "a" * 43)
    config = AdminGatewayConfig(True, "http://127.0.0.1:39999", "gw_" + "a" * 40)
    provider = ImageGenerationProvider(workspace=str(tmp_path), runtime=runtime, turn_key="turn-1", model_alias="image-a", configuration=config, environment={}, transport=transport)
    broker = SessionProjectionBroker(SimpleNamespace(), settings=SessionProjectionBrokerSettings(timeout_seconds=3, max_bytes=65536))
    broker.start()
    broker.bind_image_generation_provider(provider)
    client = SessionProjectionBrokerClient.from_env(broker.child_env())
    client.fixture_image_provider = provider
    yield provider, transport, broker, client
    provider.close()
    broker.close()


class Persistence(AdminAgentTurnPersistence):
    def __init__(self):
        self.messages = []
        self.image_data = ImageDataFixture()
    def image_turn_data(self, **_):
        return self.image_data
    def persist_user(self, **kwargs):
        self.messages.append({"role": "user", **kwargs})
        return SimpleNamespace(message_id=kwargs["message_id"])
    def persist_assistant(self, **kwargs):
        self.messages.append({"role": "assistant", **kwargs})


def test_uploaded_png_visual_input_and_edit_reference_use_same_file(bound):
    provider, transport, _, client = bound
    original = picture()
    saved = save_buffer_to_workspace_files(provider.workspace, "草图 layout.png", "image/png", original)
    reference = "workspace://" + quote(saved["workspacePath"], safe="/")
    attachment = AttachmentPayload(
        name=saved["fileName"], media_type=saved["mimeType"],
        data=base64.b64encode(original).decode("ascii"), id=reference,
    )
    blocks = ClaudeAgentContextBuilder(context_session_count=0).build_user_message(
        [{"type": "text", "text": "Keep the drawing layout and make the lines red"}],
        attachments=[attachment], include_runtime_context=False,
    )
    assert blocks[0] == {"type": "image", "source": {
        "type": "base64", "media_type": "image/png", "data": attachment.data,
    }}
    assert blocks[1] == {"type": "text", "text": "Reference image for editing: " + reference}
    assert blocks[-1]["text"] == "Keep the drawing layout and make the lines red"
    result = request_image(client, {"prompt": blocks[-1]["text"], "reference_images": [reference]})
    assert len(transport.calls) == 1
    url, call = transport.calls[0]
    assert url.endswith("/v1/images/edits")
    assert call["files"][0][0] == "image[]"
    assert call["files"][0][1][1] == original
    assert result.images[0].uri != reference
    assert (provider.workspace / saved["workspacePath"]).read_bytes() == original
    assert result.images[0].uri.startswith("workspace://files/generated/")


def test_full_generate_display_save_reopen_edit(bound):
    provider, transport, broker, client = bound
    owner = Persistence()
    args = {"prompt": "A blue image", "reference_images": []}
    async def scenario():
        queue = asyncio.Queue()
        ctx = _TurnContext(queue, ToolConfirmationStore(), image_provider=provider)
        service = ClaudeAgentService()
        class Runner:
            async def run_streaming(self, opts, callbacks):
                await callbacks.on_tool_event(ToolEventPayload(type="tool_use", tool_call_id="sdk-call-1", tool_name=IMAGE_TOOL_NAME, input=args))
                result = await asyncio.to_thread(request_image, client, args)
                await callbacks.on_tool_event(ToolEventPayload(type="tool_result", tool_call_id="sdk-call-1", tool_name=IMAGE_TOOL_NAME, output=result.model_dump_json()))
                await callbacks.on_text_delta("Here is the image.")
                await callbacks.on_text_done("Here is the image.")
                return AgentRunResult("Here is the image.", None, True, protocol_completed=True)
        request = ClaudeAgentRunRequest(user_id="7", thread_id="image-thread", message_id="message-1", model="ai-model", message_parts=[{"type": "text", "text": "Create an image"}], admin_turn_persistence=owner)
        execution = _TurnExecution(request=request, state=AgentRunState(session_id="image-thread"), runner=Runner(), run_options=SimpleNamespace(user_message=[], model="ai-model"), turn_context=ctx)
        service._store_story_workspace_output = AsyncMock(return_value=None)
        await service.execute_session(execution)
        frames = []
        while not queue.empty():
            frames.append(queue.get_nowait())
        return ctx, frames
    ctx, frames = asyncio.run(scenario())
    saved = owner.messages[-1]
    assert saved["role"] == "assistant"
    final = saved["history_final_text"]
    assert final.startswith("Here is the image.") and "![Generated image](workspace://files/generated/" in final
    uri = ctx.image_results[0].uri
    relative = uri.removeprefix("workspace://")
    # Reopen consumes persisted parts, not a fresh inference call.
    reopened = json.loads(json.dumps(saved["parts"]))
    assert uri in reopened[saved["metadata"]["finalPartIndex"]]["text"]
    content = read_workspace_file_content(provider.workspace, relative, reject_symlinks=True, require_regular_file=True)
    assert content.content == picture() and len(transport.calls) == 1
    assert any(getattr(frame, "type", None) == "text-delta" and uri in frame.data.get("delta", "") for frame in frames)
    # A new turn gets its own Host binding; edit reads the original file and keeps it.
    edit = ImageGenerationProvider(workspace=str(provider.workspace), runtime=provider.runtime, turn_key="turn-2", model_alias="image-a", configuration=provider.configuration, environment={}, transport=transport)
    broker.bind_image_generation_provider(edit)
    client.fixture_image_provider = edit
    try:
        result = request_image(client, {"prompt": "Make it red", "reference_images": [uri]})
        url, call = transport.calls[-1]
        assert url.endswith("/v1/images/edits") and call["files"][0][0] == "image[]"
        assert call["files"][0][1][1] == picture()
        assert result.images[0].uri != uri and (provider.workspace / relative).exists()
        assert call["headers"]["Idempotency-Key"] != transport.calls[0][1]["headers"]["Idempotency-Key"]
        assert "output_format" not in call["data"]
    finally:
        edit.close()


@pytest.mark.parametrize("uri", ["workspace://files/../secret.png", "workspace://files/%2e%2e/secret.png", "workspace://files/.claude/key.png", "workspace://files/missing.png", "https://example.com/a.png", "workspace://files//etc/a.png"])
def test_reference_denial_does_not_dispatch(bound, uri):
    _, transport, _, client = bound
    with pytest.raises(Exception):
        request_image(client, {"prompt": "edit", "reference_images": [uri]})
    assert transport.calls == []


def test_symlink_reference_and_generated_directory_denied(bound, tmp_path):
    provider, transport, _, client = bound
    outside = tmp_path.parent / "image-outside-20261010.png"
    outside.write_bytes(picture())
    try:
        (tmp_path / "files" / "reference.png").symlink_to(outside)
        with pytest.raises(Exception):
            request_image(client, {"prompt": "edit", "reference_images": ["workspace://files/reference.png"]})
        assert not transport.calls
        (tmp_path / "files" / "generated").symlink_to(tmp_path.parent, target_is_directory=True)
        with pytest.raises(Exception):
            request_image(client, {"prompt": "create"})
        assert not provider._published
    finally:
        outside.unlink()


def test_symlink_files_namespace_denied_during_publication(bound, tmp_path):
    provider, _, _, client = bound
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / "files").rmdir()
    (tmp_path / "files").symlink_to(outside, target_is_directory=True)
    with pytest.raises(Exception):
        request_image(client, {"prompt": "create"})
    assert not provider._published and not list(outside.iterdir())


@pytest.mark.parametrize("payload", [{"data": []}, {"data": [{"b64_json": "@@@"}]}, {"data": [{"b64_json": base64.b64encode(b"not an image").decode()}]}])
def test_invalid_result_no_file_or_retry(bound, payload):
    provider, transport, _, client = bound
    transport.result = payload
    with pytest.raises(Exception):
        request_image(client, {"prompt": "create"})
    assert len(transport.calls) == 1 and not provider._published
    assert not (provider.workspace / "files" / "generated").exists()


def test_cancel_late_return_no_publication(bound):
    provider, transport, _, client = bound
    transport.on_post = provider.close
    with pytest.raises(Exception):
        request_image(client, {"prompt": "create"})
    assert len(transport.calls) == 1 and not (provider.workspace / "files" / "generated").exists()


def test_catalog_images_never_become_text_default(bound):
    provider, transport, _, _ = bound
    catalog_client = GatewayModelCatalogClient(access_token=provider.runtime.access_token(), configuration=provider.configuration, transport=transport)
    catalog = catalog_client.fetch_catalog()
    assert catalog.default_model_alias is None and catalog.default_image_model_alias == "image-a"
    assert catalog.models[0].callable is False and catalog.models[0].image_callable
    assert catalog_client.list_models() == []


def test_unregistered_conflicting_or_forged_result_not_promoted(bound):
    provider, _, _, client = bound
    result = request_image(client, {"prompt": "create"})
    assert provider.consume_result(result.model_dump(), {"prompt": "wrong"}) is None
    async def scenario():
        ctx = _TurnContext(asyncio.Queue(), ToolConfirmationStore(), image_provider=provider)
        cb = ClaudeAgentService._make_tool_event_cb(ctx.queue, ctx)
        await cb(ToolEventPayload(type="tool_result", tool_call_id="unknown", tool_name=IMAGE_TOOL_NAME, output=result.model_dump_json()))
        assert ctx.image_results == []
        await cb(ToolEventPayload(type="tool_use", tool_call_id="right", tool_name=IMAGE_TOOL_NAME, input={"prompt": "create", "reference_images": []}))
        await cb(ToolEventPayload(type="tool_result", tool_call_id="right", tool_name="external", output=result.model_dump_json()))
        assert ctx.image_results == []
        await cb(ToolEventPayload(type="tool_result", tool_call_id="right", tool_name=IMAGE_TOOL_NAME, output=result.model_dump_json()))
        assert len(ctx.image_results) == 1
        await cb(ToolEventPayload(type="tool_result", tool_call_id="right", tool_name=IMAGE_TOOL_NAME, output=result.model_dump_json()))
        assert len(ctx.image_results) == 1
        await ClaudeAgentService._complete_image_results(ctx)
        await ClaudeAgentService._complete_image_results(ctx)
        assert sum(uri["text"].count(result.images[0].uri) for uri in _sse_events_to_ui_parts(ctx.collected_parts) if uri["type"] == "text") == 1
    asyncio.run(scenario())


def test_tool_contract_disallows_auth_and_other_thread_selectors():
    for argument in ({"prompt": "x", "model": "image"}, {"prompt": "x", "thread_id": "other"}, {"prompt": "x", "api_key": "secret"}, {"prompt": " "}):
        with pytest.raises(Exception):
            ImageToolInput.model_validate(argument)


def test_real_stdio_mcp_discovery_and_generation(bound):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from libs.claude_agent_kit.server.agent_runner import _user_mcp_stdio_config
    provider, transport, broker, _ = bound
    config = _user_mcp_stdio_config(broker.child_env(), module_name="libs.claude_agent_kit.server.image_gen_stdio")
    wire = config if isinstance(config, dict) else vars(config)  # repository SDK fixture uses an attribute object
    async def scenario():
        async with stdio_client(StdioServerParameters(command=wire['command'], args=wire['args'], env=wire['env'])) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                await session.initialize()
                listed = await session.list_tools()
                assert [tool.name for tool in listed.tools] == ['select_image_operation', 'imagegen']
                assert listed.tools[0].inputSchema['additionalProperties'] is False
                args = {'prompt': 'create', 'reference_images': []}
                select_provider(provider, args)
                provider.authorize_tool(IMAGE_TOOL_NAME, 'actual-mcp-call', args)
                denied_meta = await session.call_tool('imagegen', args)
                assert denied_meta.isError
                assert not transport.calls
                result = await session.call_tool('imagegen', args, meta={'claudecode/toolUseId': 'actual-mcp-call'})
                assert not result.isError
                output = json.loads(result.content[0].text)
                assert output['kind'] == 'image-generation-result'
                assert 'b64_json' not in result.content[0].text
                denied = await session.call_tool('imagegen', {'prompt': 'edit', 'reference_images': ['workspace://files/../outside.png']})
                assert denied.isError
    asyncio.run(scenario())
    assert len(transport.calls) == 1


def test_completed_result_retained_on_cancel_partial(bound):
    provider, _, _, client = bound
    owner = Persistence()
    async def scenario():
        ctx = _TurnContext(asyncio.Queue(), ToolConfirmationStore(), image_provider=provider)
        service = ClaudeAgentService()
        class Runner:
            async def run_streaming(self, opts, callbacks):
                await callbacks.on_tool_event(ToolEventPayload(type='tool_use', tool_name=IMAGE_TOOL_NAME, tool_call_id='completed-before-stop', input={'prompt': 'create', 'reference_images': []}))
                result = await asyncio.to_thread(request_image, client, {'prompt': 'create'})
                await callbacks.on_tool_event(ToolEventPayload(type='tool_result', tool_name=IMAGE_TOOL_NAME, tool_call_id='completed-before-stop', output=result.model_dump_json()))
                raise asyncio.CancelledError()
        execution = _TurnExecution(request=ClaudeAgentRunRequest(user_id='7', thread_id='image-thread', message_id='cancel-message', model='ai-model', message_parts=[{'type': 'text', 'text': 'create'}], admin_turn_persistence=owner), state=AgentRunState(session_id='image-thread'), runner=Runner(), run_options=SimpleNamespace(user_message=[], model="ai-model"), turn_context=ctx)
        service.mark_auto_repair_failed = AsyncMock()
        with pytest.raises(asyncio.CancelledError):
            await service.execute_session(execution)
        return ctx
    ctx = asyncio.run(scenario())
    saved = owner.messages[-1]
    assert saved['metadata']['is_partial'] and saved['metadata']['turnStatus'] == 'cancelled'
    assert any(part.get('type') == 'text' and ctx.image_results[0].uri in part.get('text', '') for part in saved['parts'])
    assert provider._closed


@pytest.mark.parametrize('case', ['bytes', 'pixels', 'response', 'scope', 'stale-model', 'no-image-capability', 'gateway-rejection', 'duplicate-call'])
def test_capacity_authorization_selection_failure_no_auto_retry(bound, case):
    provider, transport, _, client = bound
    if case == 'bytes': provider.max_bytes = 1
    elif case == 'pixels': provider.max_pixels = 1
    elif case == 'response': provider.max_response_bytes = 1
    elif case == 'scope': provider.runtime.allows = lambda _: False
    elif case == 'stale-model':
        transport.catalog['data'] = [model('image-b')]
    elif case == 'no-image-capability':
        transport.catalog['data'][0]['endpoint_availability']['images']['callable'] = False
        transport.catalog['default_model_alias'] = None
    elif case == 'gateway-rejection': transport.status = 402
    elif case == 'duplicate-call':
        request = ImageGenerationRequest(capability=broker_capability(bound), request_id='duplicate', prompt='create', reference_images=[], source_call_id='duplicate-call')
        authorize_execution(provider, {"prompt": "create", "reference_images": []}, call_id="duplicate-call")
        provider.generate(request)
        with pytest.raises(AdminDataError): provider.generate(request)
        assert len(transport.calls) == 1
        return
    with pytest.raises(Exception): request_image(client, {'prompt': 'create'})
    assert len(transport.calls) <= 1 and not provider._published
    assert not (provider.workspace / 'files' / 'generated').exists()


def broker_capability(bound):
    return bound[2].child_env()['INK_SESSION_BROKER_CAPABILITY']


def test_explicit_image_selection_ignores_catalog_default_and_other_candidates(bound):
    _, transport, _, client = bound
    transport.catalog['data'].append(model('image-b'))
    transport.catalog['default_model_alias'] = 'image-b'
    request_image(client, {'prompt': 'create'})
    assert transport.calls[0][1]['json']['model'] == 'image-a'


def test_missing_image_selection_never_uses_env_or_catalog_default(bound):
    selected, transport, _, _ = bound
    provider = ImageGenerationProvider(workspace=str(selected.workspace), runtime=selected.runtime,
        turn_key='unselected', configuration=selected.configuration,
        environment={'INK_IMAGE_MODEL_ALIAS': 'image-a'}, transport=transport)
    try:
        authorize_execution(provider, {'prompt': 'create', 'reference_images': []}, call_id='unselected-call')
        with pytest.raises(AdminDataError, match='IMAGE_MODEL_NOT_SELECTED'):
            provider.generate(ImageGenerationRequest(capability=broker_capability(bound), request_id='no-model', prompt='create', reference_images=[], source_call_id='unselected-call'))
        assert not transport.calls
    finally:
        provider.close()


def test_existing_markdown_image_deduplicates_but_code_and_links_do_not(bound):
    provider, _, _, client = bound
    result = request_image(client, {'prompt': 'create'})
    from claude_agent.service import _image_final_text
    uri = result.images[0].uri
    ctx = _TurnContext(asyncio.Queue(), ToolConfirmationStore(), image_results=result.images)
    for final, count in [(f'![Image]({uri})', 1), (f'[Image]({uri})', 2), (f'`![Image]({uri})`', 2), (f'```md\n![Image]({uri})\n```', 2)]:
        ctx.collected_parts = [{'type': 'text-start'}, {'type': 'text-delta', 'delta': final}, {'type': 'text-end'}]
        assert _image_final_text(ctx, '').count(uri) == count


def test_partial_model_text_without_text_done_keeps_one_final(bound):
    # SDK normally sends text-done. Inject its absence to cover a stop after a delta.
    provider, _, _, client = bound
    result = request_image(client, {'prompt': 'create'})
    async def scenario():
        ctx = _TurnContext(asyncio.Queue(), ToolConfirmationStore(), image_provider=provider, image_results=result.images)
        await ClaudeAgentService._make_text_delta_cb(ctx.queue, ctx)('Here is the image.')
        await ClaudeAgentService._complete_image_results(ctx)
        return _sse_events_to_ui_parts(ctx.collected_parts)
    parts = asyncio.run(scenario())
    assert len(parts) == 1 and parts[0]['text'].startswith('Here is the image.')
    assert result.images[0].uri in parts[0]['text']


def test_cancel_at_publish_entry_retains_cancelled_error(bound):
    provider, _, _, _ = bound
    provider.close()
    request = ImageGenerationRequest(capability=broker_capability(bound), request_id='cancel-publish', prompt='create', reference_images=[])
    with pytest.raises(AdminDataError) as error:
        provider._publish(request, [(picture(), 'png', 'image/png')], 'req_00000000000040008000000000000001')
    assert error.value.code == 'IMAGE_CANCELLED'
    assert not (provider.workspace / 'files' / 'generated').exists()


def test_uploaded_image_keeps_visual_bytes_and_thread_reference():
    from claude_agent.context_builder import ClaudeAgentContextBuilder
    from libs.claude_agent_kit.messages.build_user_message_content import AttachmentPayload

    uri = "workspace://files/attachments/reference%20image.png"
    attachment = AttachmentPayload(name="reference image.png", media_type="image/png", data=base64.b64encode(picture()).decode(), id=uri)
    blocks = ClaudeAgentContextBuilder().build_user_message(
        [{"type": "text", "text": "Edit this image"}], attachments=[attachment], include_runtime_context=False,
    )
    image_index = next(i for i, block in enumerate(blocks) if block.get("type") == "image")
    assert blocks[image_index]["source"]["data"] == attachment.data
    assert blocks[image_index + 1]["type"] == "text"
    assert uri in blocks[image_index + 1]["text"]
    assert all(attachment.data not in block.get("text", "") for block in blocks)


def test_text_only_turn_keeps_original_multi_part_final_event():
    owner = Persistence()

    async def scenario():
        queue = asyncio.Queue()
        ctx = _TurnContext(queue, ToolConfirmationStore())
        service = ClaudeAgentService()

        class Runner:
            async def run_streaming(self, opts, callbacks):
                for text in ("First reply.", "Second reply."):
                    await callbacks.on_text_delta(text)
                    await callbacks.on_text_done(text)
                return AgentRunResult("First reply.Second reply.", None, True, protocol_completed=True)

        request = ClaudeAgentRunRequest(user_id="7", thread_id="text-thread", message_id="text-message", message_parts=[{"type": "text", "text": "Continue"}], admin_turn_persistence=owner)
        execution = _TurnExecution(request=request, state=AgentRunState(session_id="text-thread"), runner=Runner(), run_options=SimpleNamespace(user_message=[], model="ai-model"), turn_context=ctx)
        service._store_story_workspace_output = AsyncMock(return_value=None)
        await service.execute_session(execution)
        frames = []
        while not queue.empty():
            frames.append(queue.get_nowait())
        return frames

    frames = asyncio.run(scenario())
    final = next(frame for frame in frames if frame.type == "message-final")
    assert final.data["text"] == "First reply.Second reply."
    assert [part["text"] for part in owner.messages[-1]["parts"] if part["type"] == "text"] == ["First reply.", "Second reply."]


def test_published_file_with_late_tool_receipt_is_not_promoted_after_close(bound):
    provider, _, _, client = bound
    arguments = {"prompt": "create", "reference_images": []}
    result = request_image(client, arguments)

    async def scenario():
        ctx = _TurnContext(asyncio.Queue(), ToolConfirmationStore(), image_provider=provider)
        cb = ClaudeAgentService._make_tool_event_cb(ctx.queue, ctx)
        await cb(ToolEventPayload(type="tool_use", tool_call_id="late-image", tool_name=IMAGE_TOOL_NAME, input=arguments))
        provider.close()
        await cb(ToolEventPayload(type="tool_result", tool_call_id="late-image", tool_name=IMAGE_TOOL_NAME, output=result.model_dump_json()))
        await ClaudeAgentService._complete_image_results(ctx)
        assert not ctx.image_results
        assert not any(part.get("type") == "text" for part in _sse_events_to_ui_parts(ctx.collected_parts))

    asyncio.run(scenario())
    assert (provider.workspace / result.images[0].uri.removeprefix("workspace://")).is_file()


def test_reference_capacity_stops_reading_at_first_aggregate_overflow(bound):
    provider, transport, _, _ = bound
    data = picture()
    (provider.workspace / "files" / "reference.png").write_bytes(data)
    (provider.workspace / "files" / "reference2.png").write_bytes(data)
    references = ["workspace://files/reference.png", "workspace://files/reference2.png"]
    authorize_execution(provider, {"prompt": "edit", "reference_images": references}, call_id="overflow-call")
    provider.max_bytes = len(data)
    request = ImageGenerationRequest(capability=broker_capability(bound), request_id="reference-overflow", prompt="edit", reference_images=references, source_call_id="overflow-call")
    with pytest.raises(AdminDataError) as error:
        provider.generate(request)
    assert error.value.code == "IMAGE_SIZE_EXCEEDED"
    assert transport.calls == []


@pytest.mark.parametrize("replacement", ["directory", "symlink"])
def test_reference_root_replacement_denied_before_images_dispatch(bound, replacement):
    provider, transport, _, _ = bound
    workspace = provider.workspace
    original = workspace.with_name(workspace.name + "-image-original")
    outside = workspace.with_name(workspace.name + "-image-replacement")
    (workspace / "files" / "reference.png").write_bytes(picture())
    authorize_execution(provider, {"prompt": "edit", "reference_images": ["workspace://files/reference.png"]}, call_id="root-call")
    workspace.rename(original)
    try:
        if replacement == "symlink":
            outside.mkdir()
            (outside / "reference.png").write_bytes(picture())
            workspace.symlink_to(outside, target_is_directory=True)
        else:
            workspace.mkdir()
            (workspace / "reference.png").write_bytes(picture())
        request = ImageGenerationRequest(capability=broker_capability(bound), request_id="replaced-root", prompt="edit", reference_images=["workspace://files/reference.png"], source_call_id="root-call")
        with pytest.raises(AdminDataError) as error:
            provider.generate(request)
        assert error.value.code == "IMAGE_REFERENCE_UNAVAILABLE"
        assert transport.calls == []
    finally:
        if workspace.is_symlink():
            workspace.unlink()
        elif workspace.exists():
            (workspace / "reference.png").unlink()
            workspace.rmdir()
        if outside.exists():
            (outside / "reference.png").unlink()
            outside.rmdir()
        original.rename(workspace)


def test_actual_gateway_identity_is_preserved_in_result_and_cannot_be_substituted(bound):
    provider, transport, _, client = bound
    result = request_image(client, {"prompt": "create"})
    assert result.gatewayRequestId == "req_00000000000040008000000000000001"
    assert result.requestId != result.gatewayRequestId
    changed = result.model_dump()
    changed["gatewayRequestId"] = "req_00000000000040008000000000000002"
    assert provider.consume_result(changed, {"prompt": "create", "reference_images": []}) is None
    assert provider.consume_result(result.model_dump(), {"prompt": "create", "reference_images": []}) is not None


@pytest.mark.parametrize("header", [None, "upstream-not-a-gateway-id", "private\nheader", "00000000-0000-4000-8000-000000000001", "req_short"])
def test_missing_or_invalid_gateway_identity_does_not_publish(bound, header):
    provider, transport, _, client = bound
    original = transport.post
    def post(*args, **kwargs):
        response = original(*args, **kwargs)
        response.headers = {"x-request-id": header} if header is not None else {}
        return response
    transport.post = post
    with pytest.raises(Exception, match="IMAGE_GATEWAY_RESPONSE_INVALID"):
        request_image(client, {"prompt": "create"})
    assert len(transport.calls) == 1 and not provider._published


def test_owned_image_http_cancel_closes_socket_before_headers(tmp_path):
    """Use the production HTTP client against a named provider-free fixture."""
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    received, disconnected = threading.Event(), threading.Event()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            self.rfile.read(int(self.headers.get("Content-Length", "0")))
            received.set()
            self.connection.settimeout(3)
            if self.connection.recv(1) == b"":
                disconnected.set()

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True, name="image-cancel-fixture")
    server_thread.start()
    config = AdminGatewayConfig(True, f"http://127.0.0.1:{server.server_port}", "gw_" + "a" * 40)
    provider = ImageGenerationProvider(workspace=str(tmp_path), runtime=SimpleNamespace(), turn_key="cancel-http", configuration=config, environment={})
    errors = []

    def send():
        try:
            provider._post_image(config.base_url + "/v1/images/generations", {}, {"json": {"prompt": "fixture"}})
        except AdminDataError as error:
            errors.append(error.code)

    worker = threading.Thread(target=send, name="image-cancel-owned-http")
    try:
        worker.start()
        assert received.wait(3), "fixture did not receive original POST"
        provider.close()
        worker.join(3)
        assert not worker.is_alive(), "cancel did not release headers wait"
        assert disconnected.wait(3), "original HTTP socket remained open"
        assert errors == ["IMAGE_CANCELLED"]
        assert provider._http_task is None
        with pytest.raises(AdminDataError, match="IMAGE_CANCELLED"):
            provider._post_image(config.base_url, {}, {"json": {}})
    finally:
        provider.close()
        server.shutdown()
        server.server_close()
        worker.join(3)
