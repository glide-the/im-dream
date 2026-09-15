# [Input] Public Story guidance route, Registry115 result DTO and fake Admin data/Runtime dispatch providers.
# [Output] Preserved 202/error/replay/dispatch behavior plus production database-import fences.
# [Pos] Provider-free Story Workspace guidance contract test.
# [Sync] 2026-09-15: replace the retired SQLite persistence harness with Admin DTO and Dream Runtime seams.
from __future__ import annotations

import ast
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers import story_workspace
from services.admin_data.errors import AdminDataError
from services.admin_data.story_workspace_guidance_data import (
    StoryWorkspaceGuidanceResultDTO,
)
from services.admin_data.request_auth import AdminRequestActor

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
        return self.delivered


def client(data: FakeGuidanceData, dispatcher: RecordingDispatcher):
    app = FastAPI()
    app.dependency_overrides[story_workspace.get_current_user] = lambda: {
        "user_id": int(ACTOR_ID),
        "_admin_actor": AdminRequestActor(
            "subject", ACTOR_ID, "dream", frozenset({"dream:write"}),
            1, 2, "oauth",
        ),
    }
    app.dependency_overrides[story_workspace._guidance_data] = lambda: data
    app.include_router(story_workspace.router)
    original = story_workspace.build_thread_turn_dispatcher
    story_workspace.build_thread_turn_dispatcher = lambda: dispatcher
    test_client = TestClient(app)
    test_client._guidance_restore = lambda: setattr(  # type: ignore[attr-defined]
        story_workspace, "build_thread_turn_dispatcher", original
    )
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
    assert dispatcher.calls[0][0:3] == (THREAD_ID, ACTOR_ID, "guide_key-1")


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
