# [Input] Public Dream launch request and strict Admin DTO persistence fakes.
# [Output] Route, new/replay workflow, dispatch, failure and no-PostgreSQL boundary evidence.
# [Pos] Provider-free launch business tests; all persistence crosses Admin operation DTOs.
# [Sync] 2026-09-16: replace legacy local-database launch fixtures with Admin-owned contract tests.
"""Dream launch REST and production composition tests."""

from __future__ import annotations

import ast
import asyncio
from datetime import UTC, datetime
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from routers import story_workspace
from services.admin_data.launch_metadata_data import (
    CLAIM_LAUNCH,
    ENSURE_LAUNCH_SOURCE,
    FAIL_LAUNCH_ENVELOPE,
    FINISH_LAUNCH,
    LOOKUP_LAUNCH_REPLAY,
    LaunchClaimOutputDTO,
    LaunchSourceOutputDTO,
)
from services.admin_data.request_auth import AdminRequestActor, AdminRequestAuth
from services.admin_data.run_data import CREATE_RUN, FAIL_RUN
from services.story_workspace.dream_launch_application_service import (
    DreamLaunchApplicationService,
    DreamLaunchSource,
)
from services.story_workspace.dream_launch_infrastructure import (
    DreamLaunchEnvelopeDispatcher,
    DreamLaunchFailureRecorder,
    DreamLaunchTaskRegistry,
    _decode_json_object,
    build_dream_launch_application_service,
)
from services.story_workspace.dream_launch_runtime import PreparedDreamLaunchBinding
from story_workspace.contracts import StoryWorkspaceDreamLaunchCommand, StoryWorkspaceDreamRunContext

ACTOR_ID = "71"
WORKSPACE_ID = "workspace-dream-launch-api"
DECK_ID = "deck-dream-launch-api"
PLUGIN_ID = "plugin-dream"
PLUGIN_VERSION = "1.0.0"
BINDING_ID = "dpb_" + "1" * 32
PREFLIGHT_ID = "pf_" + "2" * 32
RUN_ID = "run_" + "3" * 32
SNAPSHOT_ID = "drs_" + "4" * 32
LOCK_ID = "rpl_" + "5" * 32
CLAIM_ID = "dlc_" + "6" * 32
SOURCE_TIME = "2026-09-16T01:02:03.123456+00:00"


def actor() -> AdminRequestActor:
    return AdminRequestActor("subject", ACTOR_ID, "dream-browser",
        frozenset({"dream:read", "dream:write"}), 1, 4_102_444_800, "test-access-token")


def launch_command(**overrides: object) -> StoryWorkspaceDreamLaunchCommand:
    payload: dict[str, object] = {"deckId": DECK_ID, "goal": "创作一个雨夜车站重逢的短篇故事",
        "idempotencyKey": "dream-api-launch-1"}
    payload.update(overrides)
    return StoryWorkspaceDreamLaunchCommand.model_validate(payload)


def context(*, agent_id: str | None = None, thread_id: str = "thread-dream-api") -> StoryWorkspaceDreamRunContext:
    return StoryWorkspaceDreamRunContext(workflow_run_id=RUN_ID, thread_id=thread_id, deck_id=DECK_ID,
        agent_id=agent_id, deck_plugin_id=PLUGIN_ID, deck_plugin_version=PLUGIN_VERSION,
        deck_plugin_binding_id=BINDING_ID, binding_revision=1,
        deck_runtime_snapshot_id=SNAPSHOT_ID, runtime_plugin_lock_id=LOCK_ID)


def test_decode_json_object_accepts_native_jsonb_dict() -> None:
    native = {"enabled": True, "nullable": None, "items": ["one"]}
    decoded = _decode_json_object(native)
    assert decoded == native and decoded is not native


def test_launch_production_modules_have_no_database_or_sql_execution() -> None:
    service_root = Path(__file__).parents[1] / "services" / "story_workspace"
    for name in ("dream_launch_runtime.py", "dream_launch_infrastructure.py", "dream_launch_endpoint_service.py"):
        source = (service_root / name).read_text()
        tree = ast.parse(source)
        imported = {alias.name.split(".")[0] for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom)) for alias in node.names}
        called = {node.func.attr for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)}
        assert imported.isdisjoint({"database", "psycopg", "sqlalchemy", "drizzle"})
        assert called.isdisjoint({"execute", "cursor", "commit", "rollback"})
        assert all(token not in source for token in ("SELECT ", "INSERT ", "UPDATE ", "DELETE "))


class ApiGateway:
    def __init__(self) -> None:
        self.calls = []

    async def start_dream_run(self, request, *, actor, admin_client, admin_actor, runtime_port):
        self.calls.append((request, actor, admin_client, admin_actor, runtime_port))
        return context()


class StoryWorkspaceDreamLaunchApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.gateway = ApiGateway()
        self.app = FastAPI()
        self.owner = AdminRequestAuth.__new__(AdminRequestAuth)
        self.owner.client = object()
        self.admin_actor = actor()
        self.app.dependency_overrides[story_workspace._story_workflow_current_user] = lambda: {
            "user_id": int(ACTOR_ID), "workspace_id": WORKSPACE_ID, "_admin_actor": self.admin_actor}
        self.app.dependency_overrides[story_workspace.get_admin_request_auth] = lambda: self.owner
        self.app.dependency_overrides[story_workspace.get_dream_launch_endpoint_service] = lambda: self.gateway
        self.app.include_router(story_workspace.router)

    def test_start_passes_same_admin_actor_client_and_returns_camel_case_context(self) -> None:
        with TestClient(self.app) as client:
            response = client.post("/api/story-workspace/dream-runs/start", json=launch_command().model_dump(by_alias=True))
        self.assertEqual(response.status_code, 201, response.text)
        payload = response.json()
        self.assertEqual(payload["status"], "accepted")
        self.assertEqual(payload["workflowRunId"], RUN_ID)
        self.assertFalse(any("_" in key for key in payload))
        request, route_actor, admin_client, admin_actor, runtime_port = self.gateway.calls[0]
        self.assertEqual(request.deck_id, DECK_ID)
        self.assertEqual(route_actor, {"actor_id": ACTOR_ID, "workspace_id": WORKSPACE_ID})
        self.assertIs(admin_client, self.owner.client)
        self.assertIs(admin_actor, self.admin_actor)
        self.assertEqual(runtime_port._access_token, "test-access-token")

    def test_start_rejects_client_persistence_provenance(self) -> None:
        forbidden = ({"threadId": "client-thread"}, {"workflowRunId": "run_" + "9" * 32},
            {"bindingRevision": 999}, {"sourceMessageId": "client-message"})
        with TestClient(self.app) as client:
            for extra in forbidden:
                response = client.post("/api/story-workspace/dream-runs/start",
                    json={"deckId": DECK_ID, "goal": "目标", "idempotencyKey": "dream-api-strict", **extra})
                self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(self.gateway.calls, [])

    def test_start_rejects_snake_case_and_boundary_whitespace(self) -> None:
        with TestClient(self.app) as client:
            snake = client.post("/api/story-workspace/dream-runs/start",
                json={"deck_id": DECK_ID, "goal": "目标", "idempotency_key": "key"})
            spaced = client.post("/api/story-workspace/dream-runs/start",
                json={"deckId": DECK_ID, "goal": " 目标", "idempotencyKey": "key"})
        self.assertEqual(snake.status_code, 422)
        self.assertEqual(spaced.status_code, 422)
        self.assertEqual(self.gateway.calls, [])


class FakeRuntime:
    def __init__(self):
        self.calls = []

    async def authorize(self, **values):
        self.calls.append(("authorize", values))

    async def prepare(self, **values):
        self.calls.append(("prepare", values))
        return PreparedDreamLaunchBinding(PLUGIN_ID, PLUGIN_VERSION, BINDING_ID, 1)


class FakeLaunchData:
    def __init__(self, replay=None, *, claim=True):
        self.replay = replay
        self.claim = claim
        self.calls = []

    def execute(self, operation, input_dto, request_id, **kwargs):
        assert operation is LOOKUP_LAUNCH_REPLAY
        self.calls.append(("lookup", input_dto.model_dump()))
        return SimpleNamespace(replay=self.replay)

    def execute_recovering(self, operation, input_dto, request_id, **kwargs):
        self.calls.append((operation.capability.name, input_dto.model_dump()))
        if operation is ENSURE_LAUNCH_SOURCE:
            expected = kwargs["source"]
            return LaunchSourceOutputDTO(source={"thread_id": expected.thread_id, "message_id": expected.message_id,
                "message_time": SOURCE_TIME, "request_fingerprint": expected.request_fingerprint, "created": True})
        if operation is CLAIM_LAUNCH:
            source = kwargs["source"]
            run_context = kwargs["context"]
            if not self.claim:
                return LaunchClaimOutputDTO.model_validate({"claimed": False, "workflow_run_id": RUN_ID,
                    "thread_id": source.thread_id, "message_id": source.message_id})
            metadata = {"actorId": ACTOR_ID, "workspaceId": WORKSPACE_ID, "workflowRunId": RUN_ID,
                "threadId": source.thread_id, "dreamContext": run_context.model_dump(mode="json"),
                "dispatchStatus": "dispatched"}
            return LaunchClaimOutputDTO.model_validate({"claimed": True, "workflow_run_id": RUN_ID,
                "thread_id": source.thread_id, "message_id": source.message_id, "claim_id": CLAIM_ID,
                "context": run_context.model_dump(), "parts_json": json.dumps([{"type": "text", "text": input_dto.instruction_text}]),
                "metadata_json": json.dumps(metadata)})
        if operation is FINISH_LAUNCH:
            return SimpleNamespace(finished=True)
        if operation is FAIL_LAUNCH_ENVELOPE:
            return SimpleNamespace(updated=True)
        raise AssertionError(operation)


class FakePreflightData:
    def __init__(self):
        self.calls = []

    def execute_recovering(self, input_dto, request_id, **kwargs):
        self.calls.append(("execute", input_dto.model_dump()))
        return self._result(token="pft-secret")

    def read(self, input_dto, request_id, **kwargs):
        self.calls.append(("read", input_dto.model_dump()))
        return self._result(token=None)

    @staticmethod
    def _result(*, token):
        return {"workflow_preflight_id": PREFLIGHT_ID, "deck_id": DECK_ID, "binding_revision": 1,
            "deck_plugin_id": PLUGIN_ID, "deck_plugin_version": PLUGIN_VERSION,
            "runtime_plugin_lock_id": LOCK_ID, "deck_runtime_profile_id": "profile",
            "deck_runtime_snapshot_id": SNAPSHOT_ID, "deck_runtime_snapshot_summary_hash": "sha256:" + "7" * 64,
            "input_hash": "sha256:" + "8" * 64, "status": "passed", "error_code": None, "failed_check": None,
            "expires_at": "2026-09-16T02:02:03.123456+00:00", "preflight_token": token,
            "created_by": ACTOR_ID, "created_at": SOURCE_TIME}


class FakeRunData:
    def __init__(self):
        self.calls = []

    def write_recovering(self, operation, input_dto, request_id, **kwargs):
        self.calls.append((operation.capability.name, input_dto.model_dump()))
        return self._result(input_dto.source_voice_thread_id, input_dto.source_message_id, input_dto.source_message_time)

    def read(self, input_dto, request_id, **kwargs):
        self.calls.append(("read", input_dto.model_dump()))
        return self._result(self.thread_id, self.message_id, SOURCE_TIME)

    def _result(self, thread_id, message_id, message_time):
        return {"workflow_run_id": RUN_ID, "workflow_preflight_id": PREFLIGHT_ID,
            "source_voice_thread_id": thread_id, "source_message_id": message_id,
            "source_message_time": datetime.fromisoformat(message_time), "created_by": ACTOR_ID,
            "workspace_id": WORKSPACE_ID, "deck_plugin_id": PLUGIN_ID, "deck_plugin_version": PLUGIN_VERSION,
            "deck_plugin_binding_id": BINDING_ID, "binding_revision": 1,
            "deck_runtime_snapshot_id": SNAPSHOT_ID, "runtime_plugin_lock_id": LOCK_ID}


def wire_fakes(service, launch, preflight, runs):
    service._source_repository._data = launch
    service._workflow._launch = launch
    service._workflow._preflight = preflight
    service._workflow._runs = runs
    service._dispatcher._launch = launch


@pytest.mark.asyncio
async def test_new_launch_uses_lookup_source_preflight_run_and_dispatch_admin_operations(monkeypatch):
    monkeypatch.setattr("database.get_db", lambda: pytest.fail("launch must not open Dream PostgreSQL"))
    runtime = FakeRuntime()
    launch = FakeLaunchData(claim=False)
    preflight = FakePreflightData()
    runs = FakeRunData()
    turns = []
    service = build_dream_launch_application_service(object(), actor=actor(), workspace_id=WORKSPACE_ID,
        runtime_port=runtime, turn_dispatcher=lambda **values: turns.append(values), platform_model_resolver=lambda *_: "model")
    wire_fakes(service, launch, preflight, runs)
    result = await service.launch(launch_command(), actor_id=ACTOR_ID, workspace_id=WORKSPACE_ID)
    assert result.workflow_run_id == RUN_ID
    assert [name for name, _ in launch.calls] == ["lookup", ENSURE_LAUNCH_SOURCE.capability.name, CLAIM_LAUNCH.capability.name]
    assert preflight.calls[0][0] == "execute"
    assert runs.calls[0][0] == CREATE_RUN.capability.name
    assert [name for name, _ in runtime.calls] == ["authorize", "prepare"]
    assert runtime.calls[1][1]["existing_run"] is None
    assert turns == []


@pytest.mark.asyncio
async def test_replay_reads_frozen_preflight_and_run_without_model_or_new_writes():
    ids = DreamLaunchApplicationService._deterministic_source_ids(
        actor_id=ACTOR_ID, workspace_id=WORKSPACE_ID, idempotency_key=launch_command().idempotency_key)
    replay = SimpleNamespace(workflow_run_id=RUN_ID, workflow_preflight_id=PREFLIGHT_ID,
        thread_id=ids[0], message_id=ids[1])
    runtime = FakeRuntime()
    launch = FakeLaunchData(replay=replay, claim=False)
    preflight = FakePreflightData()
    runs = FakeRunData()
    runs.thread_id, runs.message_id = ids
    service = build_dream_launch_application_service(object(), actor=actor(), workspace_id=WORKSPACE_ID,
        runtime_port=runtime, turn_dispatcher=lambda **_values: True,
        platform_model_resolver=lambda *_: pytest.fail("replay must not resolve a current model"))
    wire_fakes(service, launch, preflight, runs)
    result = await service.launch(launch_command(), actor_id=ACTOR_ID, workspace_id=WORKSPACE_ID)
    assert result.workflow_run_id == RUN_ID
    assert preflight.calls == [("read", {"workflow_preflight_id": PREFLIGHT_ID})]
    assert runs.calls == [("read", {"workspace_id": WORKSPACE_ID, "workflow_run_id": RUN_ID})]
    assert runtime.calls[1][1]["existing_run"] == {"id": RUN_ID, "source_voice_thread_id": ids[0]}


@pytest.mark.asyncio
async def test_claim_dispatches_dream_turn_then_finishes_in_admin():
    source = DreamLaunchSource("11111111-1111-5111-8111-111111111111",
        "22222222-2222-5222-8222-222222222222", datetime.now(UTC), "sha256:" + "a" * 64, True)
    launch = FakeLaunchData(claim=True)
    turns = []
    dispatcher = DreamLaunchEnvelopeDispatcher(object(), actor=actor(), workspace_id=WORKSPACE_ID,
        turn_dispatcher=lambda **values: turns.append(values) or True)
    dispatcher._launch = launch
    assert await dispatcher(actor_id=ACTOR_ID, goal="目标", source=source, context=context(thread_id=source.thread_id))
    assert [name for name, _ in launch.calls] == [CLAIM_LAUNCH.capability.name, FINISH_LAUNCH.capability.name]
    assert turns[0]["parts"][0]["text"].startswith("目标")
    assert turns[0]["metadata"]["dispatchStatus"] == "dispatched"


@pytest.mark.asyncio
async def test_agent_voice_prompt_is_loaded_through_owned_deck_detail():
    source = DreamLaunchSource("11111111-1111-5111-8111-111111111111",
        "22222222-2222-5222-8222-222222222222", datetime.now(UTC), "sha256:" + "a" * 64, True)
    launch = FakeLaunchData(claim=True)
    turns = []
    dispatcher = DreamLaunchEnvelopeDispatcher(object(), actor=actor(), workspace_id=WORKSPACE_ID,
        turn_dispatcher=lambda **values: turns.append(values) or True)
    dispatcher._launch = launch
    dispatcher._decks = SimpleNamespace(detail=lambda *_args, **_kwargs: {"voices": [
        {"id": "voice", "deck_id": DECK_ID, "enabled": True, "system_prompt": "prompt"}]})
    assert await dispatcher(actor_id=ACTOR_ID, goal="目标", source=source,
        context=context(agent_id="voice", thread_id=source.thread_id))
    assert turns[0]["system_prompt"] == "prompt"


@pytest.mark.asyncio
async def test_terminal_failure_updates_run_before_launch_envelope():
    calls = []
    recorder = DreamLaunchFailureRecorder(object(), actor=actor(), workspace_id=WORKSPACE_ID)
    recorder._runs = SimpleNamespace(write_recovering=lambda operation, input_dto, request_id, **kwargs:
        calls.append((operation, input_dto)) or {"status": "failed"})
    recorder._launch = SimpleNamespace(execute_recovering=lambda operation, input_dto, request_id, **kwargs:
        calls.append((operation, input_dto)) or SimpleNamespace(updated=True))
    await recorder.record(workflow_run_id=RUN_ID, actor_id=ACTOR_ID, thread_id="thread",
        message_id="message", error_code="DREAM_AGENT_DISPATCH_FAILED")
    assert [item[0] for item in calls] == [FAIL_RUN, FAIL_LAUNCH_ENVELOPE]


@pytest.mark.asyncio
async def test_task_registry_cancels_and_awaits_owned_turns():
    registry = DreamLaunchTaskRegistry()
    started = asyncio.Event()
    cancelled = asyncio.Event()

    async def work():
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    registry.create_task(work, name="owned-launch")
    await started.wait()
    assert registry.diagnostics()["launch_running_tasks"] == 1
    await registry.aclose()
    assert cancelled.is_set()
    assert registry.diagnostics() == {"launch_owned_tasks": 0, "launch_running_tasks": 0}
