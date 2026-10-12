# [Sync] 2026-10-10: verify Gateway identity survives the original tool event and message history.
# [Sync] 2026-10-10: separate saved AI/Image ownership; native result publication and explicit Images execution share exact turn identity, with real acceptance pending.
# [Input] Public Chat/model/workspace routers, real Factory/Service/broker, and injected Admin/SDK/provider boundaries.
# [Output] Isolated HTTP journey for create, model rejection, image generation/edit, persistence and reopen.
# [Pos] Provider-free public-entry E2E; no real account, CLI, PostgreSQL or upstream model acceptance.
# [Sync] 2026-10-10: close the missing catalog-to-send-to-history regression boundary.
# [Sync] 2026-10-10: exercise uploaded PNG visual input, canonical files/ reference and public preview.
# [Sync] 2026-10-11: expose controlled SDK wait and ordinary tool callbacks to the existing public browser journey.
from __future__ import annotations

import asyncio
import base64
from contextlib import nullcontext
import io
import json
from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image
import pytest

import tests._sdk_stubs  # noqa: F401 — deterministic SDK boundary
from claude_agent.service import ClaudeAgentService
from claude_agent.thread_factory import ClaudeAgentThreadFactory
from claude_mcp.runtime_snapshot import ManagedMcpRuntimeSnapshot
from libs.claude_agent_kit.server.image_generation_protocol import IMAGE_TOOL_NAME, IMAGE_SELECTION_TOOL_NAME, request_image, request_image_selection
from libs.claude_agent_kit.server.session_projection_protocol import SessionProjectionBrokerClient
from libs.claude_agent_kit.types import AgentRunResult, ToolEventPayload
from routers import claude_agent as chat_route, gateway_models as models_route, workspace as workspace_route
from services.admin_data.agent_turn_persistence import AdminAgentTurnPersistence
from services.admin_data.chat_models import (
    ChatMessageDTO, ChatThreadDTO, MessageListResultDTO, MessagePageResultDTO, MessagePersistResultDTO,
    ThreadCreateResultDTO, ThreadIdInputDTO, ThreadResultDTO,
)
from services.admin_data.gateway_runtime import AdminGatewayRuntime
from services.admin_data.request_auth import AdminRequestActor, AdminRequestAuth
from services.admin_data.session_projection_broker import SessionProjectionBroker, SessionProjectionBrokerSettings
from services.admin_data.system_config_data import SystemConfigGetInputDTO
from services.admin_data.workflow_data import AdminWorkflowResolution
from services.admin_gateway.config import AdminGatewayConfig
from services.admin_gateway.models import GatewayModelCatalogClient
from services.admin_gateway import images as image_module
from tests._image_turn_fixtures import ImageDataFixture


def _png() -> bytes:
    stream = io.BytesIO()
    Image.new("RGB", (8, 8), "blue").save(stream, "PNG")
    return stream.getvalue()


def _catalog_model(alias, *, chat=True, callable=True, images=False, native=False):
    return {
        "id": alias, "display_name": alias, "protocol": "openai",
        "capabilities": {"chat": chat, "tools": chat, "vision": chat,
                         "image_generation": images, "image_edit": images, "responses_image_generation": native, "responses_image_edit": native},
        "context_window": None, "max_output_tokens": None,
        "claude_code_auto_compact_window": None, "claude_code_max_context_tokens": None,
        "enabled": True, "callable": True, "availability": "included",
        "required_plan_code": None, "upgrade_hint": None,
        "image_input_token_reserve_per_image": 100 if (images or native) else None,
        "image_output_token_reserve_per_image": 100 if (images or native) else None,
        "endpoint_availability": {
            "messages": {"callable": callable and chat, "entitled": callable and chat},
            "chat": {"callable": callable and chat, "entitled": callable and chat},
            "images": {"callable": images, "entitled": images, "configured": images,
                       "generation": images, "edit": images},
            "responses_image": {"generation": native, "edit": native, "configured": native, "entitled": chat and callable, "callable": native and callable},
        },
    }


class Response:
    status_code = 200
    def __init__(self, payload):
        self.payload = payload
        self.headers = {'x-request-id': 'req_' + uuid4().hex}
    def json(self): return self.payload
    def __enter__(self): return self
    def __exit__(self, *_): pass
    def iter_content(self, _): yield json.dumps(self.payload).encode()


class ProviderTransport:
    def __init__(self): self.calls, self.gateway_request_ids, self.native_calls = [], [], []
    def get(self, _url, **_kwargs):
        return Response({"object": "list", "data": [
            _catalog_model("available-text"), _catalog_model("available-native", native=True), _catalog_model("locked-text", callable=False),
            _catalog_model("image-only", chat=False, images=True),
        ], "default_model_alias": "available-text"})
    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        response = Response({"created": 1, "data": [{"b64_json": base64.b64encode(_png()).decode()}]})
        self.gateway_request_ids.append(response.headers["x-request-id"])
        return response


class AdminChatFixture:
    def __init__(self): self.threads, self.messages = {}, []
    def create_thread(self, dto, _request_id, *, access_token):
        assert access_token == "test-oauth-token"
        identity = str(uuid4())
        self.threads[identity] = ChatThreadDTO(
            id=identity, user_id="7", title=dto.title, deck_id=dto.deck_id, voice_id=dto.voice_id,
            created_at="2026-10-10T00:00:00Z", updated_at="2026-10-10T00:00:00Z",
            claude_session_id=None, agent_contract_version=None,
        )
        return ThreadCreateResultDTO(thread_id=identity, deck_id=dto.deck_id, voice_id=dto.voice_id)
    def get_thread(self, dto, _request_id, *, access_token):
        assert access_token == "test-oauth-token"
        return ThreadResultDTO(thread=self.threads.get(dto.thread_id))
    def message_page(self, dto, _request_id, *, access_token):
        assert access_token == "test-oauth-token"
        messages = [ChatMessageDTO.model_validate({key: value for key, value in item.items() if key != "thread_id"})
                    for item in self.messages if item["thread_id"] == dto.thread_id]
        return MessagePageResultDTO(messages=messages, has_more=False,
                                   latest_message_id=messages[-1].id if messages else None)
    def list_messages(self, dto, request_id, *, access_token):
        return MessageListResultDTO(messages=self.message_page(dto, request_id, access_token=access_token).messages)


class Persistence(AdminAgentTurnPersistence):
    def __init__(self, fixture, config):
        self.fixture, self.config = fixture, config
        self.image_data = ImageDataFixture()
        self.broker = SessionProjectionBroker(SimpleNamespace(), settings=SessionProjectionBrokerSettings(timeout_seconds=3, max_bytes=65536))
        self.broker.start()
    def start(self): pass
    def image_turn_data(self, **_): return self.image_data
    def close(self): self.broker.close()
    def system_config(self, **_): return self.config
    def recent_sessions(self, **_): return []
    def session_projection_child_env(self): return self.broker.child_env()
    def current_grant(self, **_): return SimpleNamespace(token="idg_" + "a" * 43, run_id=None)
    def bind_thread_tool_provider(self, _provider): pass
    def refresh_thread_tool_authorization(self, _actor): pass
    def bind_image_generation_provider(self, provider):
        self.fixture.current_image_provider=provider
        self.broker.bind_image_generation_provider(provider)
    def thread(self, *, thread_id, **_): return self.fixture.threads.get(thread_id)
    def notion_connector_store(self, **_): raise RuntimeError("No connector in this isolated fixture")
    def persist_user(self, **kwargs): return self._save("user", kwargs)
    def persist_assistant(self, **kwargs): return self._save("assistant", kwargs)
    def _save(self, role, value):
        record = {
            "id": value["message_id"], "thread_id": value["thread_id"], "role": role,
            "parts": value["parts"], "metadata": value.get("metadata"),
            "metadata_decode_error": False, "created_at": "2026-10-10T00:00:00Z",
            "history_final_text": value.get("history_final_text"),
            "history_process_available": value.get("history_process_available", False),
            "history_projection_version": value.get("history_projection_version"),
        }
        # Admin persistence is idempotent for the same Thread/message identity.
        # The injected storage boundary must not append a duplicate receipt.
        existing = next((index for index, item in enumerate(self.fixture.messages)
                         if item["id"] == record["id"] and item["thread_id"] == record["thread_id"]), None)
        if existing is None: self.fixture.messages.append(record)
        else: self.fixture.messages[existing] = record
        return MessagePersistResultDTO(message_id=value["message_id"])


class GatewayRuntime(AdminGatewayRuntime):
    def __init__(self): pass
    def start(self): pass
    def close(self): pass
    def allows(self, scope): return scope in {"images:create", "messages:create"}
    def access_token(self): return "idg_" + "a" * 43


class Owner(AdminRequestAuth):
    def __init__(self, fixture, config):
        self.client, self.fixture, self.config = object(), fixture, config
    @property
    def session_broker_settings(self): return SimpleNamespace(timeout_seconds=3)
    def workflow_context(self, actor, thread_id, _): return AdminWorkflowResolution(actor.canonical_user_id, thread_id, None)
    def turn_persistence(self, *_): return Persistence(self.fixture, self.config)
    def gateway_runtime(self, *_): return GatewayRuntime()
    def editor_runtime(self, *_, **__): return None


class SnapshotLoader:
    def authorize(self, _): return nullcontext()
    async def load(self, *_): return ManagedMcpRuntimeSnapshot()


def build_public_journey_app(monkeypatch, tmp_path):
    import claude_agent.thread_factory as factory_module
    monkeypatch.setenv("AGENT_CWD", str(tmp_path / "im-public-image-journey"))
    fixture, transport = AdminChatFixture(), ProviderTransport()
    configuration = AdminGatewayConfig(True, "http://127.0.0.1:39999", "gw_" + "a" * 40)
    catalog_factory = lambda *, access_token: GatewayModelCatalogClient(access_token=access_token, configuration=configuration, transport=transport)
    monkeypatch.setattr(chat_route, "GatewayModelCatalogClient", catalog_factory)
    monkeypatch.setattr(models_route, "GatewayModelCatalogClient", catalog_factory)
    config = {"workspace_enabled": True, "model": "locked-text", "image_model": "image-only"}
    owner = Owner(fixture, config)
    actor = AdminRequestActor("fixture-subject", "7", "dream-browser", frozenset({"dream:read", "dream:write", "models:list"}), 1, 9999999999, "test-oauth-token")
    user = {"user_id": 7, "_admin_actor": actor}
    async def invoke(_user, _operation, dto, **_):
        if isinstance(dto, SystemConfigGetInputDTO): return config
        if isinstance(dto, ThreadIdInputDTO): return dto.thread_id in fixture.threads
        raise AssertionError(type(dto))
    monkeypatch.setattr(chat_route, "invoke_admin_operation", invoke)
    monkeypatch.setattr(workspace_route, "invoke_admin_operation", invoke)
    provider_class = image_module.ImageGenerationProvider
    monkeypatch.setattr(image_module, "ImageGenerationProvider", lambda **kwargs: provider_class(**kwargs, configuration=configuration, transport=transport, environment={}))
    class Storage:
        async def download(self, key):
            assert key == "isolated-sketch.png"
            return _png()
        async def get_metadata(self, key):
            assert key == "isolated-sketch.png"
            return SimpleNamespace(content_type="image/png")
    monkeypatch.setattr(chat_route, "server_file_storage", Storage())
    runner_calls = []
    class Runner:
        async def run_streaming(self, options, callbacks):
            runner_calls.append(options)
            message_text = ' '.join(block.get('text','') for block in options.user_message if isinstance(block,dict) and block.get('type')=='text').replace(r'image\_gen', 'image_gen')
            if 'Run the ordinary fixture tool' in message_text:
                await callbacks.on_tool_event(ToolEventPayload(type='tool_use',tool_call_id='ordinary-'+str(len(runner_calls)),tool_name='Read',input={'file_path':'fixture.txt'}))
                await callbacks.on_tool_event(ToolEventPayload(type='tool_result',tool_call_id='ordinary-'+str(len(runner_calls)),tool_name='Read',output='Ordinary fixture tool result'))
                await callbacks.on_text_delta('The ordinary tool completed.')
                await callbacks.on_text_done('The ordinary tool completed.')
                return AgentRunResult('The ordinary tool completed.',None,True,protocol_completed=True)
            args = {"prompt": "A blue image", "reference_images": []}
            references = [block["text"].removeprefix("Reference image for editing: ")
                          for block in options.user_message if isinstance(block, dict)
                          and block.get("type") == "text"
                          and block.get("text", "").startswith("Reference image for editing: ")]
            if references:
                args["reference_images"] = references

            client = SessionProjectionBrokerClient.from_env(options.image_generation_broker_env)
            selection_id = 'selection-' + str(len(runner_calls))
            message_text = ' '.join(block.get('text','') for block in options.user_message if isinstance(block,dict) and block.get('type')=='text')
            # The real composer serializes its Markdown underscore escape. This
            # deterministic SDK seam recognizes the same visible tool name.
            message_text = message_text.replace(r'image\_gen', 'image_gen')
            explicit = 'Use image_gen to' in message_text
            no_operation = 'Explain what image_gen does' in message_text or 'Describe this image' in message_text
            choice = dict(args, operation='none' if no_operation else ('image_gen_' if explicit else 'native_') + ('edit' if references else 'generate'))
            await asyncio.to_thread(options.image_tool_authorizer, IMAGE_SELECTION_TOOL_NAME, selection_id, choice)
            await asyncio.to_thread(request_image_selection, client, choice, selection_id)
            if no_operation:
                text='image_gen is an explicit image tool.' if not references else 'The current image was received for discussion.'
                await callbacks.on_text_delta(text);await callbacks.on_text_done(text)
                return AgentRunResult(text,None,True,protocol_completed=True)
            call_id = 'call-' + str(len(runner_calls))
            if not explicit:
                import hashlib
                from services.admin_data.image_turn_data import NativeImageSummaryDTO
                if options.model != 'available-native':
                    await callbacks.on_error(RuntimeError('AI_MODEL_IMAGE_OPERATION_UNAVAILABLE: Choose an AI model with the required image capability, or send a new explicit image_gen request.'))
                    return AgentRunResult('',None,False,protocol_completed=False)
                payload=_png();gateway_id='req_'+uuid4().hex;response_id='resp_'+uuid4().hex
                image_call='ig_'+uuid4().hex;operation='edit' if references else 'generate'
                transport.native_calls.append({'operation':operation,'model':options.model,'gatewayRequestId':gateway_id,'callId':image_call})
                provider=fixture.current_image_provider
                provider._image_turn_data.native_summary=NativeImageSummaryDTO(gatewayRequestId=gateway_id,responseId=response_id,providerHttpRequestId='fixture-upstream',configuredImageModel=None,reportedImageModel=None,usageKnown=False,usageUnknownReason='responses_image_usage_not_reported',imageCalls=[{'callId':image_call,'outputIndex':0,'status':'completed','operation':operation,'reportedAction':operation,'format':'png','byteLength':len(payload),'sha256':hashlib.sha256(payload).hexdigest()}])
                await callbacks.on_tool_event(ToolEventPayload(type='tool_use_start',tool_call_id=image_call,tool_name='image_generation',provider_executed=True,input={'gatewayRequestId':gateway_id}))
                await callbacks.on_tool_event(ToolEventPayload(type='tool_result',tool_call_id=image_call,tool_name='image_generation',provider_executed=True,output={'type':'image_generation_tool_result','tool_use_id':image_call,'gateway_request_id':gateway_id,'response_id':response_id,'content':[{'type':'image','source':{'type':'base64','media_type':'image/png','data':base64.b64encode(payload).decode()}}]}))
                await callbacks.on_text_delta('Here is the image.')
                await callbacks.on_text_done('Here is the image.')
                return AgentRunResult('Here is the image.',None,True,protocol_completed=True)
            await asyncio.to_thread(options.image_tool_authorizer, IMAGE_TOOL_NAME, call_id, args)
            await callbacks.on_tool_event(ToolEventPayload(type="tool_use", tool_call_id=call_id, tool_name=IMAGE_TOOL_NAME, input=args))
            if getattr(transport, 'hold_image', False):
                await asyncio.Event().wait()
            client = SessionProjectionBrokerClient.from_env(options.image_generation_broker_env)
            result = await asyncio.to_thread(request_image, client, args, call_id)
            await callbacks.on_tool_event(ToolEventPayload(type="tool_result", tool_call_id="call-" + str(len(runner_calls)), tool_name=IMAGE_TOOL_NAME, output=result.model_dump_json()))
            await callbacks.on_text_delta("Here is the image.")
            await callbacks.on_text_done("Here is the image.")
            return AgentRunResult("Here is the image.", None, True, protocol_completed=True)
        async def close(self): pass
    monkeypatch.setattr(factory_module, "ClaudeAgentRunner", Runner)
    factory = ClaudeAgentThreadFactory()
    factory._service = ClaudeAgentService(managed_mcp_runtime_snapshot_loader=SnapshotLoader())
    monkeypatch.setattr(chat_route, "claude_agent_thread_factory", factory)
    app = FastAPI()
    app.state.admin_request_auth = owner
    app.dependency_overrides[chat_route.get_current_user] = lambda: user
    app.dependency_overrides[chat_route.get_admin_chat_data] = lambda: fixture
    app.dependency_overrides[chat_route.get_admin_request_auth] = lambda: owner
    for router in (chat_route.router, models_route.router, workspace_route.router): app.include_router(router)
    return app, fixture, config, transport, runner_calls, factory


@pytest.fixture
def public_journey(monkeypatch, tmp_path):
    app, fixture, config, transport, runner_calls, factory = build_public_journey_app(monkeypatch, tmp_path)
    with TestClient(app) as client:
        yield client, fixture, config, transport, runner_calls
        client.portal.call(factory.aclose)


def test_public_create_catalog_reject_generate_reopen_access_edit(public_journey):
    client, fixture, config, transport, runner_calls = public_journey
    created = client.post("/api/claude-agent/threads", json={"title": "Isolated image journey"})
    assert created.status_code == 200
    thread_id = created.json()["thread_id"]
    catalog = client.get("/api/gateway/models")
    assert catalog.status_code == 200
    assert [model["modelAlias"] for model in catalog.json()["data"]] == ["available-text", "available-native", "locked-text", "image-only"]
    def send(text, *, material=False):
        return client.post("/api/claude-agent", json={"thread_id": thread_id, "model": config["model"],
            "message": {"id": str(uuid4()), "role": "user", "parts": [{"type": "text", "text": text}]}, "resume": True,
            "attachments": ([{"type":"file", "url":"/api/storage/file/isolated-sketch.png", "storageKey":"isolated-sketch.png", "filename":"previous-image.png", "mediaType":"image/png", "size":len(_png())}] if material else [])})
    rejected = send("Use image_gen to generate an image")
    assert rejected.status_code == 409 and rejected.json()["detail"]["error_code"] == "GATEWAY_MODEL_SELECTION_STALE"
    assert not runner_calls and not fixture.messages and not transport.calls
    config["model"] = "available-text"  # injected saved-config boundary, never a real account mutation
    generated = send("Use image_gen to generate an image")
    assert generated.status_code == 200 and "text/event-stream" in generated.headers["content-type"]
    frames = [json.loads(line[6:]) for line in generated.text.splitlines() if line.startswith("data: ")]
    assert not [event for event in frames if event["type"] == "error"], frames
    assert any(event["type"] == "tool-output-available" for event in frames)
    assert any(event["type"] == "finish" for event in frames)
    history = client.get(f"/api/claude-agent/threads/{thread_id}/messages")
    assert history.status_code == 200
    emitted = next(event for event in frames if event["type"] == "tool-output-available")
    result = json.loads(emitted["output"])
    assert result["gatewayRequestId"] == transport.gateway_request_ids[0]
    assert result["gatewayRequestId"] != result["requestId"]
    stored_tool = next(part for part in history.json()["messages"][-1]["parts"] if part.get("type") == "tool-invocation")
    assert stored_tool["toolCallId"] == emitted["toolCallId"]
    assert json.loads(stored_tool["output"]) == result
    assert sum(message["role"] == "user" for message in history.json()["messages"]) == 1
    assert len(runner_calls) == 1
    final = history.json()["messages"][-1]["parts"][-1]["text"]
    uri = final.split("(")[-1].split(")")[0]
    assert uri.startswith("workspace://files/generated/")
    path = uri.removeprefix("workspace://")
    viewed = client.get("/api/workspace/files/content", params={"sessionId": thread_id, "path": path})
    assert viewed.status_code == 200 and viewed.content == _png()
    assert len(transport.calls) == 1 and transport.calls[0][0].endswith("/v1/images/generations")
    state = client.get(f"/api/claude-agent/threads/{thread_id}/status")
    assert state.status_code == 200 and state.json()["running"] is False
    edited = send("Use image_gen to edit the previous image", material=True)
    assert edited.status_code == 200 and '"type":"error"' not in edited.text
    assert len(transport.calls) == 2 and transport.calls[-1][0].endswith("/v1/images/edits")
    assert transport.calls[-1][1]["files"][0][1][1] == _png()
    reopened = client.get(f"/api/claude-agent/threads/{thread_id}/messages")
    assert reopened.status_code == 200
    messages = reopened.json()["messages"]
    assert sum(message["role"] == "user" for message in messages) == 2
    assert len(runner_calls) == 2
    assert any(uri in part.get("text", "") for message in messages for part in message["parts"])
    assert client.get("/api/workspace/files/content", params={"sessionId": "foreign-thread", "path": path}).status_code == 404


def test_public_uploaded_png_visual_reference_edit_and_preview(public_journey):
    client, fixture, config, transport, runner_calls = public_journey
    config["model"] = "available-text"
    created = client.post("/api/claude-agent/threads", json={"title": "Isolated uploaded sketch journey"})
    assert created.status_code == 200
    thread_id = created.json()["thread_id"]
    edited = client.post("/api/claude-agent", json={
        "thread_id": thread_id, "model": config["model"], "resume": True,
        "message": {"id": str(uuid4()), "role": "user", "parts": [{"type": "text", "text": "Use image_gen to edit this sketch"}]},
        "attachments": [{"type": "file", "url": "/api/storage/file/isolated-sketch.png", "storageKey": "isolated-sketch.png",
                         "filename": "sketch.png", "mediaType": "image/png", "size": len(_png())}],
    })
    assert edited.status_code == 200 and '"type":"error"' not in edited.text
    blocks = runner_calls[0].user_message
    visual = next(block for block in blocks if block.get("type") == "image")
    assert base64.b64decode(visual["source"]["data"]) == _png()
    reference = next(block["text"].removeprefix("Reference image for editing: ") for block in blocks
                     if block.get("type") == "text" and block.get("text", "").startswith("Reference image for editing: "))
    assert reference.startswith("workspace://files/") and not reference.startswith("workspace://files/files/")
    viewed = client.get("/api/workspace/files/content", params={"sessionId": thread_id, "path": reference.removeprefix("workspace://")})
    assert viewed.status_code == 200 and viewed.content == _png()
    assert len(transport.calls) == 1 and transport.calls[0][0].endswith("/v1/images/edits")
    assert transport.calls[0][1]["files"][0][1][1] == viewed.content
    history = client.get(f"/api/claude-agent/threads/{thread_id}/messages")
    assert history.status_code == 200 and len(history.json()["messages"]) == 2
    assert len(runner_calls) == 1
