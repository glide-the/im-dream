# [Input] Runner-owned Admin HTTP route, signed fixture tokens and one isolated source Thread.
# [Output] Dream Tool creation, target completion, public result reads and production Factory source delivery.
# [Pos] Cross-repository technical probe invoked only by the Admin disposable PostgreSQL runner.
# [Sync] 2026-09-28: start the production claim-next loop after target final commit; no test-side claim or dispatch.
# [Sync] 2026-09-28: verify exact source-claim Workflow/Thread/config reads before result settlement.
# [Sync] 2026-09-28: verify Dream's exact operation/DTO client against Admin's real Route Handler.
# [Sync] 2026-09-28: exercise source-Thread Deck context and reject a different owned Deck.
# [Sync] 2026-09-28: fake SDK Factory exposes owner completion before result settlement.
# [Sync] 2026-09-28: read pending/delivered results through the real public FastAPI route and Admin OAuth principal.
# [Sync] 2026-09-28: run the production Thread Tool broker/provider to create and read the target before source delivery.
# [Sync] 2026-09-28: retain production ThreadFactory/EventBus/assistant persistence for source resume, faking only context and Runner execution.
"""Exercise the Dream client over isolated Admin HTTP without starting a model."""

from __future__ import annotations

import json
import os
import asyncio
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from claude_agent.event_bus import BusProxyQueue
from claude_agent.service import _TurnContext, _TurnExecution
from claude_agent.task_result_coordinator import TaskResultCoordinator
from claude_agent.thread_factory import ClaudeAgentThreadFactory
from claude_agent.tool_confirmation_store import ToolConfirmationStore
from libs.claude_agent_kit.types import AgentRunOptions, AgentRunResult
from routers import claude_agent as routes
from libs.claude_agent_kit.server.session_projection_protocol import ThreadToolCommandResultDTO
from libs.claude_agent_kit.server.thread_tool import handle_thread_tool
from services.admin_data.chat_data import (
    AdminChatData, CHAT_OPERATIONS,
)
from services.admin_data.chat_models import (
    MessagePersistInputDTO,
    ThreadIdInputDTO,
    ThreadSessionInputDTO,
)
from services.admin_data.client import AdminDataClient
from services.admin_data.deck_chat_context_data import (
    AdminDeckChatContextData, DeckChatContextInputDTO, RESOLVE_DECK_CHAT_CONTEXT,
)
from services.admin_data.config import AdminDataConfig
from services.admin_data.delegation import RuntimeHttpConfig
from services.admin_data.session_projection_broker import (
    SessionProjectionBroker, SessionProjectionBrokerSettings,
)
from services.admin_data.system_config_data import GET_THREAD_SYSTEM_CONFIG
from services.admin_data.task_session_result_data import (
    TASK_RESULT_OPERATIONS, AdminTaskResultWorkerData,
)
from services.admin_data.workflow_data import RESOLVE_WORKFLOW_CONTEXT
from services.admin_data.errors import AdminDataError
from services.admin_data.request_auth import AdminRequestAuth


def required(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError(f"Missing isolated probe input: {name}")
    return value


async def main() -> None:
    transport = required("TASK_RESULT_PROBE_ADMIN_ORIGIN")
    service_id = required("TASK_RESULT_PROBE_SERVICE_ID")
    service_secret = required("TASK_RESULT_PROBE_SERVICE_SECRET")
    service_token = required("TASK_RESULT_PROBE_SERVICE_TOKEN")
    user_token = required("TASK_RESULT_PROBE_USER_TOKEN")
    foreign_user_token = required("TASK_RESULT_PROBE_FOREIGN_USER_TOKEN")
    source_thread_id = required("TASK_RESULT_PROBE_SOURCE_THREAD_ID")
    deck_id = required("TASK_RESULT_PROBE_DECK_ID")
    voice_id = required("TASK_RESULT_PROBE_VOICE_ID")
    foreign_deck_id = required("TASK_RESULT_PROBE_FOREIGN_DECK_ID")
    config = AdminDataConfig(
        base_url="http://localhost:3000",
        issuer="http://localhost:3000/api/auth",
        resource="http://localhost:8765/api",
        service_secret=service_secret,
        service_client_id=service_id,
        transport_base_url=transport,
    )
    client = AdminDataClient(
        config, operations=(
            *CHAT_OPERATIONS, *TASK_RESULT_OPERATIONS, RESOLVE_WORKFLOW_CONTEXT,
            GET_THREAD_SYSTEM_CONFIG,
            RESOLVE_DECK_CHAT_CONTEXT,
        ),
        service_token_provider=lambda: service_token,
    )
    request_auth = AdminRequestAuth(config, client=client)
    try:
        actor = await asyncio.to_thread(
            request_auth.authenticate, user_token, f"dream-http-auth-{uuid4()}",
            required_scopes=frozenset({"dream:read", "dream:write"}),
        )
        current_user = actor.current_user_projection()
        chat = AdminChatData(client)
        target_done = asyncio.Event()
        target_launches: list[str] = []

        async def fake_target_stream(body, *, current_user, chat, owner):
            assert body.resume is False
            assert body.message["role"] == "user"
            target_launches.append(body.thread_id)

            async def frames():
                await routes._chat_invoke(
                    current_user, chat.update_session,
                    ThreadSessionInputDTO(
                        thread_id=body.thread_id,
                        claude_session_id=f"dream-http-target-session-{uuid4()}",
                        agent_contract_version="route-fixture",
                    ),
                )
                await routes._chat_invoke(
                    current_user, chat.persist_message,
                    MessagePersistInputDTO(
                        thread_id=body.thread_id,
                        message_id=f"dream-http-target-final-{uuid4()}",
                        role="assistant",
                        parts=[{"type": "text", "text": "Dream HTTP target result"}],
                        metadata={
                            "turnId": f"dream-http-target-turn-{uuid4()}",
                            "turnStatus": "completed", "finalPartIndex": 0,
                        },
                        history_final_text="Dream HTTP target result",
                        history_process_available=False,
                        history_projection_version=1,
                    ),
                )
                target_done.set()
                yield "fake-target-terminal-frame"

            return SimpleNamespace(body_iterator=frames())

        provider = routes._ThreadToolTurnProvider(
            loop=asyncio.get_running_loop(), current_user=current_user,
            chat=chat, owner=request_auth,
            source_thread_id=source_thread_id,
            source_message_id=f"dream-http-source-message-{uuid4()}",
            timeout_seconds=10, model_alias="dream-balanced",
        )
        broker = SessionProjectionBroker(
            SimpleNamespace(), settings=SessionProjectionBrokerSettings(
                timeout_seconds=10, max_bytes=1_048_576,
            ),
        )
        broker.bind_thread_tool_provider(provider)
        broker.start()
        try:
            def invoke_tool(name: str, arguments: dict[str, str], call_id: str):
                result = json.loads(handle_thread_tool(name, arguments, call_id))
                assert result.pop("ok") is True, result
                return ThreadToolCommandResultDTO.model_validate(result, strict=True)

            with patch.dict(os.environ, broker.child_env()), patch.object(
                routes, "claude_agent_stream", side_effect=fake_target_stream,
            ):
                created = await asyncio.to_thread(
                    invoke_tool, "create_thread",
                    {"title": "Dream HTTP task", "prompt": "Finish HTTP task"},
                    "dream-http-create",
                )
                assert created.status == "starting"
                await asyncio.wait_for(target_done.wait(), timeout=10)
                replay = await asyncio.to_thread(
                    invoke_tool, "create_thread",
                    {"title": "Dream HTTP task", "prompt": "Finish HTTP task"},
                    "dream-http-create",
                )
                assert replay.thread_id == created.thread_id
                read = await asyncio.to_thread(
                    invoke_tool, "read_thread",
                    {"thread_id": created.thread_id}, "dream-http-get",
                )
                assert read.status == "idle"
                assert read.messages and read.messages[-1].text == "Dream HTTP target result"
                links = await routes._chat_invoke(
                    current_user,
                    chat.list_task_session_links,
                    ThreadIdInputDTO(thread_id=source_thread_id),
                )
                created_relation = next(
                    item for item in links.created if item.thread_id == created.thread_id
                )
                created_task_id = created_relation.task_id
                with patch.object(
                    routes, "claude_agent_stream",
                    side_effect=HTTPException(
                        status_code=503,
                        detail={"error_code": "TASK_SESSION_RUNTIME_UNAVAILABLE"},
                    ),
                ):
                    failed = await asyncio.to_thread(
                        invoke_tool, "create_thread",
                        {"title": "Dream HTTP failed task", "prompt": "Do not complete"},
                        "dream-http-create-failed",
                    )
                assert failed.status == "failed"
                assert failed.error_code == "TASK_SESSION_RUNTIME_UNAVAILABLE"
                failed_read = await asyncio.to_thread(
                    invoke_tool, "read_thread",
                    {"thread_id": failed.thread_id}, "dream-http-get-failed",
                )
                assert failed_read.status == "failed"
            assert len(target_launches) == 1
        finally:
            await asyncio.to_thread(broker.close)

        public_app = FastAPI()
        public_app.state.admin_request_auth = request_auth
        public_app.include_router(routes.router)
        result_path = f"/api/claude-agent/threads/{source_thread_id}/task-results"
        with TestClient(public_app) as public_client:
            assert public_client.get(result_path).status_code == 401
            assert public_client.get(
                result_path, headers={"Authorization": f"Bearer {foreign_user_token}"},
            ).status_code == 404
            pending = public_client.get(
                result_path, headers={"Authorization": f"Bearer {user_token}"},
            )
            assert pending.status_code == 200, pending.status_code
            pending_results = pending.json()["results"]
            assert len(pending_results) == 1
            assert pending_results[0]["task_id"] == created_task_id
            assert pending_results[0]["status"] == "pending"
            assert pending_results[0]["final_text"] == "Dream HTTP target result"
            notification_id = pending_results[0]["notification_id"]
        worker = AdminTaskResultWorkerData(
            client, runtime_http_config=RuntimeHttpConfig(transport),
            session_broker_settings=SessionProjectionBrokerSettings(
                timeout_seconds=5, max_bytes=1_048_576,
            ),
        )
        factory = ClaudeAgentThreadFactory()
        source_claim = None
        sdk_requests: list[AgentRunOptions] = []

        async def assemble_source(request, *, state, bus, runner):
            assert source_claim is not None
            assert request.thread_id == source_thread_id
            assert request.resume is True
            assert request.user_message_pre_persisted is True
            assert request.message_id == source_claim.source_input_message_id
            assert request.task_result_turn_id == source_claim.result.source_turn_id
            assert request.admin_deck_chat_context is not None
            assert request.system_prompt and "Dream HTTP Voice" in request.system_prompt
            state.is_context_initialized = True
            state.system_prompt = "Dream HTTP source context"
            turn_context = _TurnContext(
                queue=BusProxyQueue(bus), confirmation_store=ToolConfirmationStore(),
            )
            state.turn_context = turn_context
            return _TurnExecution(
                request=request, state=state, runner=runner,
                run_options=AgentRunOptions(
                    thread_id=source_claim.source_session_id,
                    user_message=source_claim.source_input_text,
                    resume=True, require_existing_session=True,
                ),
                turn_context=turn_context,
            )

        class FakeSDKRunner:
            async def run_streaming(self, options, _callbacks):
                assert source_claim is not None
                assert options.thread_id == source_claim.source_session_id
                assert options.resume is True
                assert options.require_existing_session is True
                sdk_requests.append(options)
                return AgentRunResult(
                    full_text="Dream HTTP client delivered",
                    session_id=None,
                    success=True,
                    protocol_completed=True,
                    sdk_terminal_received=True,
                )

        factory._service.assemble_context = assemble_source

        async def inspect_and_prepare(claim):
            nonlocal source_claim
            assert claim.result.notification_id == notification_id
            assert claim.result.status == "dispatching"
            assert claim.result.source_thread_id == source_thread_id
            assert claim.source_session_id == "dream-http-source-session"
            assert claim.source_input_message_id == claim.result.source_input_message_id
            assert claim.persistence_grant.thread_id == source_thread_id
            assert claim.gateway_grant.thread_id == source_thread_id
            deck_reader = AdminDeckChatContextData(client, canonical_user_id=claim.actor_id)
            source_deck = await asyncio.to_thread(
                deck_reader.resolve,
                DeckChatContextInputDTO(deck_id=deck_id, voice_id=voice_id),
                f"dream-http-deck-{uuid4()}",
                access_token=claim.persistence_grant.token,
            )
            assert source_deck.snapshot.deck.id == deck_id
            for selected_deck, selected_voice in (
                (foreign_deck_id, None), (deck_id, None),
            ):
                try:
                    await asyncio.to_thread(
                        deck_reader.resolve,
                        DeckChatContextInputDTO(
                            deck_id=selected_deck, voice_id=selected_voice,
                        ),
                        f"dream-http-denied-{uuid4()}",
                        access_token=claim.persistence_grant.token,
                    )
                except AdminDataError as error:
                    assert error.status_code == 403
                else:
                    raise AssertionError("Source claim changed its bound Deck or Voice")
            owner = await asyncio.to_thread(
                worker.turn_owner, claim, f"dream-http-owner-{uuid4()}",
            )
            try:
                assert owner.workflow.thread_id == source_thread_id
                assert await asyncio.to_thread(
                    owner.persistence.thread,
                    actor_id=claim.actor_id, thread_id=source_thread_id,
                ) is not None
                assert isinstance(await asyncio.to_thread(
                    owner.persistence.system_config,
                    actor_id=claim.actor_id, thread_id=source_thread_id,
                ), dict)
            finally:
                await asyncio.to_thread(owner.persistence.close)
                await asyncio.to_thread(owner.gateway_runtime.close)
            source_claim = claim
            return await coordinator._prepare_request(claim)

        coordinator = TaskResultCoordinator(
            worker, factory, poll_interval_s=0.05,
            request_preparer=inspect_and_prepare,
        )
        with patch("claude_agent.task_result_coordinator.resolve_platform_model",
                   return_value=SimpleNamespace(
                       model_alias="probe-model", claude_code_runtime_env=lambda: {},
                   )), patch("claude_agent.thread_factory.ClaudeAgentRunner", FakeSDKRunner):
            coordinator.start()
            try:
                for _ in range(100):
                    with TestClient(public_app) as public_client:
                        observed = public_client.get(
                            result_path,
                            headers={"Authorization": f"Bearer {user_token}"},
                        )
                    assert observed.status_code == 200, observed.status_code
                    current = observed.json()["results"]
                    assert len(current) == 1
                    if current[0]["status"] == "delivered":
                        break
                    if current[0]["status"] in {"failed", "state_unknown"}:
                        raise AssertionError(f"Source dispatch ended as {current[0]['status']}")
                    await asyncio.sleep(0.05)
                else:
                    raise AssertionError("Automatic source dispatch did not settle")
            finally:
                await coordinator.stop()
                await factory.aclose()
        assert len(sdk_requests) == 1
        with TestClient(public_app) as public_client:
            delivered = public_client.get(
                result_path, headers={"Authorization": f"Bearer {user_token}"},
            )
            assert delivered.status_code == 200, delivered.status_code
            delivered_results = delivered.json()["results"]
            assert len(delivered_results) == 1
            assert delivered_results[0]["notification_id"] == notification_id
            assert delivered_results[0]["status"] == "delivered"
            assert delivered_results[0]["source_final_message_id"]
            assert public_client.get(
                result_path, headers={"Authorization": f"Bearer {user_token}"},
            ).json()["results"] == delivered_results
        assert len(sdk_requests) == 1
        print(json.dumps({
            "status": "passed", "dream_http_client": True,
            "public_route_authenticated": True,
            "public_route_owner_denial": True,
            "public_route_pending_delivered": True,
            "source_owner_reads": True,
            "source_deck_bound": True,
            "source_input_persisted": True, "source_final_persisted": True,
            "coordinator_dispatched": True,
            "coordinator_claimed_automatically": True,
            "source_factory_production": True,
            "tool_created_target": True,
            "target_launch_once": True,
            "thread_tool_read_saved_result": True,
            "failed_target_has_no_result": True,
        }))
    finally:
        request_auth.close()
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
