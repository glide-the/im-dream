# [Input] Runner-owned isolated Admin HTTP/database, fixture OAuth tokens and an existing owned source Thread.
# [Output] Tool creation, public Calendar operations and one real worker/Factory/persistence trigger with a fake SDK runner.
# [Pos] Cross-repository technical probe; the runner owns database, service processes and cleanup.
# [Sync] 2026-09-28: exercise scheduled Chat authority and turn binding through production Dream/Admin ports.
"""Run only against an explicitly owned, migrated isolated Admin database."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import json
import os
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from claude_agent.event_bus import BusProxyQueue
from claude_agent.scheduled_task_coordinator import ScheduledTaskCoordinator
from claude_agent.service import _TurnContext, _TurnExecution
from claude_agent.thread_factory import ClaudeAgentThreadFactory
from claude_agent.tool_confirmation_store import ToolConfirmationStore
from libs.claude_agent_kit.server.session_projection_protocol import ThreadToolCommandResultDTO
from libs.claude_agent_kit.server.thread_tool import handle_thread_tool
from libs.claude_agent_kit.types import AgentRunOptions, AgentRunResult
from routers import claude_agent as routes
from services.admin_data.chat_data import AdminChatData, CHAT_OPERATIONS
from services.admin_data.chat_models import ThreadCreateInputDTO
from services.admin_data.client import AdminDataClient
from services.admin_data.config import AdminDataConfig
from services.admin_data.delegation import AdminDelegationCreator, DelegationCreateInputDTO
from services.admin_data.deck_chat_context_data import DECK_CHAT_CONTEXT_OPERATIONS
from services.admin_data.request_auth import AdminRequestAuth
from services.admin_data.scheduled_task_data import SCHEDULED_TASK_OPERATIONS
from services.admin_data.session_projection_broker import SessionProjectionBroker, SessionProjectionBrokerSettings
from services.admin_data.system_config_data import SYSTEM_CONFIG_OPERATIONS
from services.admin_data.workflow_data import RESOLVE_WORKFLOW_CONTEXT


def required(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError(f"Missing isolated scheduled probe input: {name}")
    return value


async def main() -> None:
    # The runner must verify the actual database identity before creating
    # these credentials. This probe never opens PostgreSQL or creates schema.
    origin = required("SCHEDULE_PROBE_ADMIN_ORIGIN")
    service_id = required("SCHEDULE_PROBE_SERVICE_ID")
    service_secret = required("SCHEDULE_PROBE_SERVICE_SECRET")
    service_token = required("SCHEDULE_PROBE_SERVICE_TOKEN")
    user_token = required("SCHEDULE_PROBE_USER_TOKEN")
    foreign_token = required("SCHEDULE_PROBE_FOREIGN_USER_TOKEN")
    config = AdminDataConfig(
        base_url=origin,
        issuer=f"{origin}/api/auth",
        resource=os.environ.get("SCHEDULE_PROBE_RESOURCE", "http://localhost:8765/api"),
        service_secret=service_secret,
        service_client_id=service_id,
        transport_base_url=origin,
    )
    client = AdminDataClient(
        config,
        operations=(
            *CHAT_OPERATIONS, *SCHEDULED_TASK_OPERATIONS,
            *SYSTEM_CONFIG_OPERATIONS, *DECK_CHAT_CONTEXT_OPERATIONS,
            RESOLVE_WORKFLOW_CONTEXT,
        ),
        service_token_provider=lambda: service_token,
    )
    owner = AdminRequestAuth(config, client=client)
    factory = ClaudeAgentThreadFactory()
    try:
        actor = await asyncio.to_thread(
            owner.authenticate, user_token, str(uuid4()),
            required_scopes=frozenset({"dream:read", "dream:write"}),
        )
        current_user = actor.current_user_projection()
        chat = AdminChatData(client)
        source_thread_id = (await asyncio.to_thread(
            chat.create_thread,
            ThreadCreateInputDTO(deck_id=None, voice_id=None, title="Scheduled HTTP source"),
            str(uuid4()), access_token=user_token,
        )).thread_id
        source_grant = await asyncio.to_thread(
            AdminDelegationCreator(client).create,
            DelegationCreateInputDTO(
                purpose="server-persistence", thread_id=source_thread_id,
                run_id=None, editor_session_id=None, scopes=["dream:read", "dream:write"],
            ),
            access_token=user_token, request_id=str(uuid4()),
        )
        provider = routes._ThreadToolTurnProvider(
            loop=asyncio.get_running_loop(), current_user=current_user,
            chat=chat, owner=owner, source_thread_id=source_thread_id,
            source_message_id=f"scheduled-probe-{uuid4()}",
            turn_persistence=SimpleNamespace(current_grant=lambda **_: source_grant),
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
            future = datetime.now(timezone.utc) + timedelta(days=4)
            rule = {"kind": "once", "local_date": future.date().isoformat(),
                    "local_time": "12:00", "time_zone": "UTC", "selected_offset_minutes": None}
            due_at = (datetime.now(timezone.utc) + timedelta(minutes=1)).replace(second=0, microsecond=0)
            if (due_at - datetime.now(timezone.utc)).total_seconds() < 10:
                due_at += timedelta(minutes=1)
            due_rule = {"kind": "once", "local_date": due_at.date().isoformat(),
                        "local_time": due_at.strftime("%H:%M"), "time_zone": "UTC",
                        "selected_offset_minutes": None}

            def tool(title: str, prompt: str, selected_rule: dict, call_id: str) -> ThreadToolCommandResultDTO:
                raw = json.loads(handle_thread_tool(
                    "create_scheduled_task",
                    {"title": title, "prompt": prompt, "rule": selected_rule}, call_id,
                ))
                assert raw.pop("ok") is True, raw
                return ThreadToolCommandResultDTO.model_validate(raw, strict=True)

            with patch.dict(os.environ, broker.child_env()):
                first = await asyncio.to_thread(tool, "Scheduled HTTP probe", "Write one short answer",
                                                rule, "scheduled-probe-call")
                replay = await asyncio.to_thread(tool, "Scheduled HTTP probe", "Write one short answer",
                                                 rule, "scheduled-probe-call")
                due = await asyncio.to_thread(tool, "Scheduled due probe", "Write a due answer",
                                              due_rule, "scheduled-due-call")
            assert first.scheduled_task is not None
            assert first.scheduled_task == replay.scheduled_task
            assert due.scheduled_task is not None
            task_id = first.scheduled_task["id"]
            due_task_id = due.scheduled_task["id"]
            assert due_task_id != task_id
        finally:
            await asyncio.to_thread(broker.close)

        app = FastAPI()
        app.state.admin_request_auth = owner
        app.include_router(routes.router)

        def public_request(method: str, path: str, *, token: str = user_token, body=None):
            with TestClient(app) as public:
                return public.request(method, path, json=body,
                                      headers={"Authorization": f"Bearer {token}"})

        base = f"/api/claude-agent/scheduled-tasks/{task_id}"
        day_path = ("/api/claude-agent/scheduled-tasks/day"
                    f"?local_date={rule['local_date']}&display_time_zone=UTC")
        forbidden = await asyncio.to_thread(public_request, "GET", base, token=foreign_token)
        assert forbidden.status_code == 200, forbidden.status_code
        assert forbidden.json() == {"task": None}
        foreign_history = await asyncio.to_thread(public_request, "GET", f"{base}/history", token=foreign_token)
        assert foreign_history.status_code == 404, foreign_history.status_code
        day = await asyncio.to_thread(public_request, "GET", day_path)
        assert day.status_code == 200, day.status_code
        assert any(item["id"] == task_id for item in day.json()["tasks"])

        manual_key = str(uuid4())
        run = await asyncio.to_thread(public_request, "POST", f"{base}/run",
                                      body={"manual_request_key": manual_key})
        assert run.status_code == 200, run.status_code
        trigger_id = run.json()["trigger"]["id"]
        same_run = await asyncio.to_thread(public_request, "POST", f"{base}/run",
                                           body={"manual_request_key": manual_key})
        assert same_run.status_code == 200, same_run.status_code
        assert same_run.json()["trigger"]["id"] == trigger_id

        sdk_calls: list[str] = []

        async def assemble_context(request, *, state, bus, runner):
            assert request.user_message_pre_persisted is True
            assert request.scheduled_turn_id is not None
            state.is_context_initialized = True
            state.system_prompt = "Isolated scheduled HTTP probe"
            turn_context = _TurnContext(
                queue=BusProxyQueue(bus), confirmation_store=ToolConfirmationStore(),
            )
            state.turn_context = turn_context
            return _TurnExecution(
                request=request, state=state, runner=runner,
                run_options=AgentRunOptions(
                    thread_id=request.thread_id,
                    user_message=request.message_parts[0]["text"], resume=False,
                ),
                turn_context=turn_context,
            )

        class FakeSDKRunner:
            async def run_streaming(self, options, _callbacks):
                sdk_calls.append(options.thread_id)
                return AgentRunResult(
                    full_text="Scheduled HTTP probe completed",
                    session_id=f"scheduled-probe-session-{uuid4()}",
                    success=True, protocol_completed=True, sdk_terminal_received=True,
                )

        factory._service.assemble_context = assemble_context
        coordinator = ScheduledTaskCoordinator(owner, poll_interval_seconds=0.05)
        with patch.object(routes, "claude_agent_thread_factory", factory), patch(
            "claude_agent.thread_factory.ClaudeAgentRunner", FakeSDKRunner,
        ), patch.object(routes, "_resolve_platform_model_selection", return_value="scheduled-probe-model"):
            coordinator.start()
            try:
                for _ in range(200):
                    history = await asyncio.to_thread(public_request, "GET", f"{base}/history")
                    assert history.status_code == 200, history.status_code
                    matching = [item for item in history.json()["triggers"] if item["id"] == trigger_id]
                    assert len(matching) == 1
                    trigger = matching[0]
                    if trigger["status"] == "succeeded":
                        break
                    if trigger["status"] in ("failed", "state_unknown"):
                        raise AssertionError(f"Scheduled dispatch ended as {trigger['status']}: {trigger['error_code']}")
                    await asyncio.sleep(0.05)
                else:
                    raise AssertionError("Scheduled worker did not settle the manual trigger")
                due_deadline = due_at + timedelta(seconds=30)
                while datetime.now(timezone.utc) < due_deadline:
                    due_history = await asyncio.to_thread(
                        public_request, "GET", f"/api/claude-agent/scheduled-tasks/{due_task_id}/history",
                    )
                    assert due_history.status_code == 200, due_history.status_code
                    scheduled = [item for item in due_history.json()["triggers"]
                                 if item["kind"] == "scheduled"]
                    if scheduled and scheduled[0]["status"] == "succeeded":
                        due_trigger = scheduled[0]
                        break
                    if scheduled and scheduled[0]["status"] in ("failed", "state_unknown"):
                        raise AssertionError(f"Due trigger ended as {scheduled[0]['status']}")
                    await asyncio.sleep(0.2)
                else:
                    raise AssertionError("Scheduled due trigger did not settle after its UTC minute")
            finally:
                await coordinator.stop()
        assert len(sdk_calls) == 2
        assert due_trigger["target_thread_id"] != trigger["target_thread_id"]
        assert due_trigger["target_turn_id"] and due_trigger["final_message_id"]
        assert trigger["target_thread_id"] and trigger["input_message_id"]
        assert trigger["target_turn_id"] and trigger["final_message_id"]

        target = await asyncio.to_thread(
            public_request, "GET",
            f"/api/claude-agent/threads/{trigger['target_thread_id']}/messages",
        )
        assert target.status_code == 200, target.status_code
        messages = target.json().get("messages", [])
        assert any(item["id"] == trigger["input_message_id"] and item["role"] == "user"
                   for item in messages)
        assert any(item["id"] == trigger["final_message_id"] and item["role"] == "assistant"
                   for item in messages)

        # Restart the consumer against the same durable history. No terminal
        # trigger may start a second model call.
        restarted = ScheduledTaskCoordinator(owner, poll_interval_seconds=0.05)
        restarted.start()
        try:
            await asyncio.sleep(0.2)
        finally:
            await restarted.stop()
        assert len(sdk_calls) == 2

        detail = await asyncio.to_thread(public_request, "GET", base)
        assert detail.status_code == 200, detail.status_code
        revision = detail.json()["task"]["revision"]
        edit = await asyncio.to_thread(public_request, "POST", f"{base}/edit", body={
            "expected_revision": revision, "title": "Edited scheduled probe",
            "prompt": "Write an edited answer", "rule": rule,
        })
        assert edit.status_code == 200, edit.status_code
        conflict = await asyncio.to_thread(public_request, "POST", f"{base}/pause",
                                           body={"expected_revision": revision})
        assert conflict.status_code == 409, conflict.status_code
        edited_revision = edit.json()["task"]["revision"]
        paused = await asyncio.to_thread(public_request, "POST", f"{base}/pause",
                                         body={"expected_revision": edited_revision})
        assert paused.status_code == 200 and paused.json()["task"]["status"] == "paused"
        resumed = await asyncio.to_thread(public_request, "POST", f"{base}/resume",
                                          body={"expected_revision": paused.json()["task"]["revision"]})
        assert resumed.status_code == 200 and resumed.json()["task"]["status"] == "active"
        deleted = await asyncio.to_thread(public_request, "POST", f"{base}/delete",
                                          body={"expected_revision": resumed.json()["task"]["revision"]})
        assert deleted.status_code == 200 and deleted.json()["task"]["status"] == "deleted"
        restored = await asyncio.to_thread(public_request, "POST", f"{base}/restore",
                                           body={"expected_revision": deleted.json()["task"]["revision"]})
        assert restored.status_code == 200 and restored.json()["task"]["status"] == "active"
        print(json.dumps({
            "status": "passed", "isolated_admin_http": True,
            "real_tool_broker": True, "public_calendar_routes": True,
            "worker_factory_final_persisted": True, "manual_request_deduplicated": True,
            "due_once_trigger_settled": True,
            "restart_did_not_repeat_model": True, "model_calls": len(sdk_calls),
            "source_thread_id": source_thread_id, "trigger_id": trigger_id, "task_id": task_id,
        }))
    finally:
        await factory.aclose()
        owner.close()


if __name__ == "__main__":
    asyncio.run(main())
