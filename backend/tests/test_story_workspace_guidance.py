# [Input] Public Story guidance route, Registry115 result DTO and exact Admin turn-owner composition.
# [Output] Preserved 202/error/replay/dispatch behavior plus complete production database fences.
# [Pos] Provider-free Story Workspace guidance contract test.
# [Sync] 2026-09-16: require OAuth model selection and gateway-cli owner injection before Runtime scheduling.
# [Sync] 2026-09-16: require Workflow/Deck/persistence owner injection before Runtime scheduling.
# [Sync] 2026-09-15: replace the retired SQLite persistence harness with Admin DTO and Dream Runtime seams.
from __future__ import annotations

import asyncio
import ast
from pathlib import Path
import re
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from routers import story_workspace
from services.story_workspace import guidance_service
from services.admin_data.deck_chat_context_data import (
    AdminDeckChatContextResolution,
    DeckChatContextOutputDTO,
)
from services.admin_data.errors import AdminDataError
from services.admin_data.story_workspace_guidance_data import (
    StoryWorkspaceGuidanceResultDTO,
)
from services.admin_data.request_auth import AdminRequestActor
from services.admin_data.workflow_data import AdminWorkflowResolution
from story_workspace.contracts import StoryWorkspaceDreamRunContext

RUN_ID = "run_" + "a" * 32
ACTOR_ID = "42"
THREAD_ID = "thread-guidance"


def accepted(*, replayed: bool = False) -> StoryWorkspaceGuidanceResultDTO:
    metadata = {
        "kind": "story-workspace-guidance",
        "story_workspace_run_id": RUN_ID,
        "actor": ACTOR_ID,
        "request_id": "guidance-original",
        "idempotency_key": "key-1",
        "command_kind": "free-text",
        "step_id": None,
        "text_summary": "第二集节奏放慢",
        "review_action": "guide",
        "command_fingerprint": "sha256:" + "b" * 64,
    }
    return StoryWorkspaceGuidanceResultDTO.model_validate({
        "message_id": "guide_key-1",
        "story_workspace_run_id": RUN_ID,
        "review_action": "guide",
        "status": "accepted",
        "replayed": replayed,
        "request_id": "guidance-original",
        "dispatch": None if replayed else {
            "thread_id": THREAD_ID,
            "message_id": "guide_key-1",
            "parts": [{
                "type": "text",
                "text": f"[story-workspace guidance · run {RUN_ID}] 第二集节奏放慢",
            }],
            "metadata": metadata,
        },
    })


class FakeGuidanceData:
    def __init__(self, result=None, error: AdminDataError | None = None) -> None:
        self.result = result or accepted()
        self.error = error
        self.calls = []

    def submit_recovering(self, input_dto, request_id, *, access_token):
        self.calls.append((input_dto, request_id, access_token))
        if self.error is not None:
            raise self.error
        return self.result


class RecordingDispatcher:
    def __init__(self, delivered: bool = True) -> None:
        self.delivered = delivered
        self.calls = []

    def __call__(self, *args):
        self.calls.append(args)
        args[0].close()
        return self.delivered


class FakePersistence:
    def __init__(self) -> None:
        self.close_calls = 0

    def close(self) -> None:
        self.close_calls += 1


class FakeGateway:
    def __init__(self) -> None:
        self.close_calls = 0

    def close(self) -> None:
        self.close_calls += 1


class FakeTurnOwner:
    def __init__(self) -> None:
        self.persistence = FakePersistence()
        self.gateway = FakeGateway()

    def close(self) -> None:
        try:
            self.gateway.close()
        finally:
            self.persistence.close()


class FakeRequestAuth:
    pass


def turn_context() -> StoryWorkspaceDreamRunContext:
    return StoryWorkspaceDreamRunContext(
        workflow_run_id=RUN_ID,
        thread_id=THREAD_ID,
        deck_id="deck-guidance",
        agent_id=None,
        deck_plugin_id="ink.dream.story-workflow",
        deck_plugin_version="1.0.0",
        deck_plugin_binding_id="dpb_" + "b" * 32,
        binding_revision=1,
        deck_runtime_snapshot_id="drs_" + "c" * 32,
        runtime_plugin_lock_id="rpl_" + "d" * 32,
    )


def deck_resolution() -> AdminDeckChatContextResolution:
    return AdminDeckChatContextResolution(
        canonical_user_id=ACTOR_ID,
        deck_id="deck-guidance",
        voice_id=None,
        snapshot=DeckChatContextOutputDTO.model_validate({
            "deck": {
                "id": "deck-guidance",
                "name": "Guidance Deck",
                "name_zh": None,
                "name_en": None,
                "description": None,
                "description_zh": None,
                "description_en": None,
                "enabled": True,
            },
            "voices": [],
            "plugin_refs": [],
        }),
    )


def exact_turn_owner() -> guidance_service.StoryWorkspaceGuidanceTurnOwner:
    return guidance_service.StoryWorkspaceGuidanceTurnOwner(
        workflow=AdminWorkflowResolution(ACTOR_ID, THREAD_ID, turn_context()),
        persistence=FakePersistence(),  # type: ignore[arg-type]
        gateway=FakeGateway(),  # type: ignore[arg-type]
        deck=deck_resolution(),
        model_alias="dream-balanced",
    )


def client(data: FakeGuidanceData, dispatcher: RecordingDispatcher):
    app = FastAPI()
    app.dependency_overrides[story_workspace.get_current_user] = lambda: {
        "user_id": int(ACTOR_ID),
        "_admin_actor": AdminRequestActor(
            "subject", ACTOR_ID, "dream", frozenset({"dream:write"}),
            1, 2, "oauth",
        ),
    }
    app.dependency_overrides[story_workspace.get_admin_request_auth] = (
        lambda: FakeRequestAuth()
    )
    app.dependency_overrides[story_workspace._guidance_data] = lambda: data
    app.include_router(story_workspace.router)
    original_dispatcher = story_workspace.build_thread_turn_dispatcher
    original_prepare = story_workspace.prepare_guidance_turn_owner
    prepared = []
    owners = []

    async def prepare(**kwargs):
        prepared.append(kwargs)
        owner = FakeTurnOwner()
        owners.append(owner)
        return owner

    story_workspace.prepare_guidance_turn_owner = prepare
    story_workspace.build_thread_turn_dispatcher = lambda: dispatcher
    test_client = TestClient(app)
    test_client._guidance_prepared = prepared  # type: ignore[attr-defined]
    test_client._guidance_owners = owners  # type: ignore[attr-defined]

    def restore():
        story_workspace.build_thread_turn_dispatcher = original_dispatcher
        story_workspace.prepare_guidance_turn_owner = original_prepare

    test_client._guidance_restore = restore  # type: ignore[attr-defined]
    return test_client


def post(test_client: TestClient, **patch):
    body = {
        "kind": "free-text",
        "text": "第二集节奏放慢",
        "step_id": None,
        "idempotency_key": "key-1",
        "actor": ACTOR_ID,
        **patch,
    }
    return test_client.post(f"/api/story-workspace/runs/{RUN_ID}/guidance", json=body)


def close(test_client: TestClient):
    test_client.close()
    test_client._guidance_restore()  # type: ignore[attr-defined]


def test_new_guidance_returns_202_and_dispatches_only_after_admin_persistence():
    data, dispatcher = FakeGuidanceData(), RecordingDispatcher()
    test_client = client(data, dispatcher)
    try:
        response = post(test_client)
    finally:
        close(test_client)
    assert response.status_code == 202
    assert response.json() == {
        "message_id": "guide_key-1",
        "story_workspace_run_id": RUN_ID,
        "review_action": "guide",
        "status": "accepted",
        "replayed": False,
        "request_id": "guidance-original",
        "dispatched": True,
    }
    input_dto = data.calls[0][0]
    assert input_dto.model_dump(mode="json") == {
        "workflow_run_id": RUN_ID,
        "kind": "free-text",
        "text": "第二集节奏放慢",
        "step_id": None,
        "idempotency_key": "key-1",
    }
    assert len(dispatcher.calls) == 1
    assert dispatcher.calls[0][1:3] == (RUN_ID, "guide_key-1")
    assert dispatcher.calls[0][0].persistence.close_calls == 1
    prepared = test_client._guidance_prepared  # type: ignore[attr-defined]
    assert len(prepared) == 1
    assert prepared[0]["thread_id"] == THREAD_ID
    assert prepared[0]["workflow_run_id"] == RUN_ID
    assert prepared[0]["actor"].canonical_user_id == ACTOR_ID


def test_replay_and_runtime_deferral_preserve_public_202_semantics():
    for result, delivered, expected, calls in [
        (accepted(replayed=True), True, False, 0),
        (accepted(), False, False, 1),
    ]:
        data, dispatcher = FakeGuidanceData(result), RecordingDispatcher(delivered)
        test_client = client(data, dispatcher)
        try:
            response = post(test_client)
        finally:
            close(test_client)
        assert response.status_code == 202
        assert response.json()["dispatched"] is expected
        assert len(dispatcher.calls) == calls
        prepared = test_client._guidance_prepared  # type: ignore[attr-defined]
        assert len(prepared) == calls
        owners = test_client._guidance_owners  # type: ignore[attr-defined]
        assert all(owner.persistence.close_calls == 1 for owner in owners)


def test_business_errors_keep_the_existing_public_codes_and_unknown_state():
    cases = [
        (AdminDataError("IDEMPOTENCY_CONFLICT", 409), 409, "IDEMPOTENCY_CONFLICT"),
        (AdminDataError("WORKFLOW_RUN_NOT_GUIDABLE", 409), 409, "WORKFLOW_RUN_NOT_GUIDABLE"),
        (AdminDataError("WORKFLOW_RUN_NOT_FOUND", 404), 404, "AGENT_EXECUTION_FAILED"),
    ]
    for error, status, expected in cases:
        test_client = client(FakeGuidanceData(error=error), RecordingDispatcher())
        try:
            response = post(test_client)
        finally:
            close(test_client)
        assert response.status_code == status
        assert response.json()["error"]["code"] == expected

    unknown = AdminDataError("ADMIN_WRITE_RESULT_UNKNOWN", 503, "original", True)
    test_client = client(FakeGuidanceData(error=unknown), RecordingDispatcher())
    try:
        response = post(test_client)
    finally:
        close(test_client)
    assert response.status_code == 503
    assert response.json()["detail"] == {
        "error_code": "ADMIN_WRITE_RESULT_UNKNOWN",
        "request_id": "original",
        "outcome_unknown": True,
    }


def test_actor_and_body_validation_happen_before_admin_persistence():
    data, dispatcher = FakeGuidanceData(), RecordingDispatcher()
    test_client = client(data, dispatcher)
    try:
        mismatch = post(test_client, actor="43")
        invalid = post(test_client, text=None)
    finally:
        close(test_client)
    assert mismatch.status_code == 403
    assert mismatch.json()["error"]["code"] == "WORKFLOW_PERMISSION_DENIED"
    assert invalid.status_code == 422
    assert data.calls == []
    assert dispatcher.calls == []


def test_prepare_turn_owner_uses_exact_workflow_deck_and_persistence_dtos(monkeypatch):
    workflow = AdminWorkflowResolution(ACTOR_ID, THREAD_ID, turn_context())
    persistence = FakePersistence()

    class RequestAuth:
        client = object()

        def __init__(self):
            self.workflow_calls = []
            self.persistence_calls = []
            self.gateway_calls = []

        def workflow_context(self, actor, thread_id, request_id):
            self.workflow_calls.append((actor, thread_id, request_id))
            return workflow

        def turn_persistence(self, actor, resolution, request_id):
            self.persistence_calls.append((actor, resolution, request_id))
            return persistence

        def gateway_runtime(self, actor, resolution, request_id):
            self.gateway_calls.append((actor, resolution, request_id))
            return gateway

    class DeckData:
        def __init__(self, client, *, canonical_user_id):
            assert client is request_auth.client
            assert canonical_user_id == ACTOR_ID

        def resolve(self, input_dto, request_id, *, access_token):
            assert input_dto.model_dump(mode="json") == {
                "deck_id": "deck-guidance",
                "voice_id": None,
            }
            assert request_id
            assert access_token == "oauth"
            return deck_resolution()

    request_auth = RequestAuth()
    gateway = FakeGateway()
    actor = AdminRequestActor(
        "subject",
        ACTOR_ID,
        "dream",
        frozenset({"dream:read", "dream:write"}),
        1,
        2,
        "oauth",
    )
    monkeypatch.setattr(guidance_service, "AdminDeckChatContextData", DeckData)
    monkeypatch.setattr(
        guidance_service,
        "resolve_platform_model_alias",
        lambda *_args, **_kwargs: "dream-balanced",
    )
    owner = asyncio.run(guidance_service.prepare_guidance_turn_owner(
        request_auth=request_auth,  # type: ignore[arg-type]
        actor=actor,
        thread_id=THREAD_ID,
        workflow_run_id=RUN_ID,
    ))
    assert owner.workflow is workflow
    assert owner.persistence is persistence
    assert owner.gateway is gateway
    assert owner.deck == deck_resolution()
    assert owner.model_alias == "dream-balanced"
    assert request_auth.workflow_calls[0][0:2] == (actor, THREAD_ID)
    assert request_auth.persistence_calls[0][0:2] == (actor, workflow)
    assert request_auth.gateway_calls[0][0:2] == (actor, workflow)


def test_dispatcher_closes_unused_owner_when_thread_is_running(monkeypatch):
    owner = exact_turn_owner()
    factory = SimpleNamespace(
        session_snapshot=lambda thread_id: {
            "lifecycle": "running",
            "thread_id": thread_id,
        }
    )
    monkeypatch.setattr(
        "agent_factory.claude_agent_thread_factory",
        factory,
    )
    delivered = guidance_service.build_thread_turn_dispatcher()(
        owner,
        RUN_ID,
        "guide_key-1",
        [{"type": "text", "text": "guide"}],
        {"kind": "story-workspace-guidance"},
    )
    assert delivered is False
    assert owner.persistence.close_calls == 1  # type: ignore[attr-defined]
    assert owner.gateway.close_calls == 1  # type: ignore[attr-defined]


def test_dispatcher_injects_exact_owner_and_closes_after_the_turn(monkeypatch):
    owner = exact_turn_owner()

    class Factory:
        def __init__(self):
            self.requests = []

        def session_snapshot(self, thread_id):
            assert thread_id == THREAD_ID
            return None

        def run_streaming(self, request):
            self.requests.append(request)

            async def stream():
                if False:
                    yield ""

            return stream()

    factory = Factory()
    monkeypatch.setattr(
        "agent_factory.claude_agent_thread_factory",
        factory,
    )
    async def scenario():
        delivered = guidance_service.build_thread_turn_dispatcher()(
            owner,
            RUN_ID,
            "guide_key-1",
            [{"type": "text", "text": "guide"}],
            {"kind": "story-workspace-guidance"},
        )
        assert delivered is True
        await asyncio.sleep(0)
        await asyncio.sleep(0)

    asyncio.run(scenario())
    assert len(factory.requests) == 1
    request = factory.requests[0]
    assert request.admin_workflow_resolution is owner.workflow
    assert request.admin_turn_persistence is owner.persistence
    assert request.admin_gateway_runtime is owner.gateway
    assert request.admin_deck_chat_context is owner.deck
    assert request.thread_id == THREAD_ID
    assert request.user_id == ACTOR_ID
    assert owner.persistence.close_calls == 1  # type: ignore[attr-defined]
    assert owner.gateway.close_calls == 1  # type: ignore[attr-defined]


def test_dispatcher_closes_owner_when_runtime_request_setup_fails(monkeypatch):
    owner = exact_turn_owner()
    factory = SimpleNamespace(session_snapshot=lambda _thread_id: None)
    monkeypatch.setattr(
        "agent_factory.claude_agent_thread_factory",
        factory,
    )

    factory.session_snapshot = lambda _thread_id: (_ for _ in ()).throw(
        RuntimeError("runtime unavailable")
    )
    with pytest.raises(RuntimeError, match="runtime unavailable"):
        guidance_service.build_thread_turn_dispatcher()(
            owner,
            RUN_ID,
            "guide_key-1",
            [{"type": "text", "text": "guide"}],
            {"kind": "story-workspace-guidance"},
        )
    assert owner.persistence.close_calls == 1  # type: ignore[attr-defined]
    assert owner.gateway.close_calls == 1  # type: ignore[attr-defined]


def test_turn_owner_rejects_a_different_run_before_runtime():
    owner = exact_turn_owner()
    with pytest.raises(AdminDataError, match="ADMIN_RESPONSE_INVALID"):
        owner.context_for(workflow_run_id="run_" + "f" * 32)


def test_guidance_production_seams_have_no_database_import_or_call():
    root = Path(__file__).resolve().parents[2]
    guidance = ast.parse((root / "backend/services/story_workspace/guidance_service.py").read_text())
    forbidden_imports = [
        node for node in ast.walk(guidance)
        if isinstance(node, ast.Import) and any(alias.name == "database" for alias in node.names)
        or isinstance(node, ast.ImportFrom) and node.module == "database"
    ]
    assert forbidden_imports == []
    assert all(
        not (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "database"
        )
        for node in ast.walk(guidance)
    )

    service = ast.parse(
        (root / "backend/claude_agent/service.py").read_text()
    )
    assert all(
        not (
            isinstance(node, ast.Import)
            and any(alias.name in {"database", "backend.database"} for alias in node.names)
        )
        and not (
            isinstance(node, ast.ImportFrom)
            and node.module in {"database", "backend.database"}
        )
        for node in ast.walk(service)
    )
    sql_start = re.compile(
        r"^\s*(?:SELECT\b[\s\S]*\bFROM\b|INSERT\s+INTO\b|"
        r"UPDATE\b[\s\S]*\bSET\b|DELETE\s+FROM\b|"
        r"WITH\b[\s\S]*\b(?:SELECT|INSERT|UPDATE|DELETE)\b)",
        re.IGNORECASE,
    )
    assert all(
        not (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and sql_start.search(node.value)
        )
        for node in ast.walk(service)
    )

    application_source = (
        root / "backend/services/deck/story_workflow_application.py"
    ).read_text()
    assert "StoryWorkspaceGuidanceService" not in application_source
    assert "def submit_guidance(" not in application_source

    router_tree = ast.parse((root / "backend/routers/story_workspace.py").read_text())
    route = next(
        node for node in ast.walk(router_tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "submit_run_guidance"
    )
    assert all(
        not isinstance(node, ast.Name) or node.id != "database"
        for node in ast.walk(route)
    )
