# [Input] Authenticated Story Workspace review routes and a strict fake Admin DTO provider.
# [Output] Public response, validation, failure mapping, order and PostgreSQL-closure assertions.
# [Pos] Provider-free Dream route contract; Admin Repository tests own persistence semantics.
# [Sync] 2026-09-15: replace the legacy SQLite review transaction harness with Registry111 route coverage.

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

import database
from routers import story_workspace
from services.admin_data.errors import AdminDataError
from services.admin_data.request_auth import AdminRequestActor
from services.admin_data.story_workspace_review_data import (
    StoryWorkspaceReviewBatchResultDTO,
    StoryWorkspaceReviewCharacterDTO,
    StoryWorkspaceReviewSceneDTO,
    StoryWorkspaceReviewStoryDTO,
    StoryWorkspaceReviewTransitionResultDTO,
)

TIME = "2026-09-15T01:02:03.000Z"


def _story(resource_id: str, action: str) -> StoryWorkspaceReviewStoryDTO:
    return StoryWorkspaceReviewStoryDTO(
        id=resource_id, identifier=resource_id, title="Story", description=None,
        status="archived" if action == "archive" else "published" if action == "confirm" else "draft",
        review_status="confirmed" if action == "confirm" else "rejected" if action == "reject" else "pending",
        review_notes="重写" if action == "reject" else None, type="short",
        character_count=1, scene_count=1, created_at=TIME, updated_at=TIME,
        confirmed_at=TIME if action == "confirm" else None, source_run_id=None,
        source_project_id=None, episode_count=None, artifact_status=None,
        artifact_manifest_revision=None, script_revision=None, artifact_sync_status=None,
        artifact_indexed_at=None, artifact_sync_error_code=None, script_size_bytes=None,
        artifact_available=None, reconcile_version=None,
    )


def _character(resource_id: str, action: str, notes: str | None):
    return StoryWorkspaceReviewCharacterDTO(
        id=resource_id, identifier=resource_id, name="Character", avatar_url=None,
        identity=None, personality=None, background=None, catchphrase=None, tags=[],
        story_count=1, review_status="confirmed" if action == "confirm" else "rejected",
        review_notes=notes if action == "reject" else None,
        status="archived" if action == "archive" else "active", created_at=TIME,
        updated_at=TIME, confirmed_at=TIME if action == "confirm" else None,
        archived_at=TIME if action == "archive" else None,
    )


def _scene(resource_id: str, action: str, notes: str | None):
    return StoryWorkspaceReviewSceneDTO(
        id=resource_id, identifier=resource_id, name="Scene", description=None,
        story_id="story-1", character_count=1, order_index=0,
        review_status="confirmed" if action == "confirm" else "rejected",
        review_notes=notes if action == "reject" else None,
        status="archived" if action == "archive" else "active", created_at=TIME,
        updated_at=TIME, confirmed_at=TIME if action == "confirm" else None,
        archived_at=TIME if action == "archive" else None,
    )


class FakeReviewData:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Any, str, str]] = []
        self.failure: AdminDataError | None = None

    @staticmethod
    def _item(resource_type: str, resource_id: str, action: str, notes: str | None):
        if resource_type == "story":
            item = _story(resource_id, action)
            return item.model_copy(update={"review_notes": notes}) if action == "reject" else item
        if resource_type == "character":
            return _character(resource_id, action, notes)
        return _scene(resource_id, action, notes)

    def transition_recovering(self, input_dto, request_id: str, *, access_token: str):
        self.calls.append(("transition", input_dto, request_id, access_token))
        if self.failure:
            raise self.failure
        return StoryWorkspaceReviewTransitionResultDTO(
            resource_type=input_dto.resource_type,
            item=self._item(input_dto.resource_type, input_dto.resource_id, input_dto.action, input_dto.review_notes),
        )

    def batch_recovering(self, input_dto, request_id: str, *, access_token: str):
        self.calls.append(("batch", input_dto, request_id, access_token))
        if self.failure:
            raise self.failure
        updated_ids = input_dto.ids[:1]
        return StoryWorkspaceReviewBatchResultDTO(
            success=True, action=input_dto.action, resource_type=input_dto.resource_type,
            total_requested=len(input_dto.ids), total_updated=len(updated_ids),
            skipped_ids=input_dto.ids[1:],
            updated_items=[self._item(input_dto.resource_type, value, input_dto.action, input_dto.review_notes) for value in updated_ids],
        )


def _actor() -> AdminRequestActor:
    return AdminRequestActor(
        subject="subject", canonical_user_id="1", client_id="dream-browser",
        scopes=frozenset({"dream:read", "dream:write"}), issued_at=1,
        expires_at=4_102_444_800, access_token="oauth-user",
    )


def _client(fake: FakeReviewData):
    app = FastAPI()
    app.dependency_overrides[story_workspace.get_current_user] = lambda: _actor().current_user_projection()
    app.dependency_overrides[story_workspace._story_review_data] = lambda: fake
    app.include_router(story_workspace.router)
    return TestClient(app)


def test_single_routes_preserve_public_shapes_without_dream_database(monkeypatch):
    fake = FakeReviewData()
    monkeypatch.setattr(database, "get_db", lambda: (_ for _ in ()).throw(AssertionError("Dream PostgreSQL path used")))
    with _client(fake) as client:
        cases = [
            ("stories/story-1/confirm", "confirmed", "published"),
            ("stories/story-2/reject", "rejected", "draft"),
            ("stories/story-3/archive", "pending", "archived"),
            ("characters/character-1/confirm", "confirmed", "active"),
            ("characters/character-2/reject", "rejected", "active"),
            ("scenes/scene-1/confirm", "confirmed", "active"),
            ("scenes/scene-2/reject", "rejected", "active"),
        ]
        for path, review_status, status in cases:
            body = {"review_notes": "重写"} if path.endswith("reject") else {}
            response = client.post(f"/api/story-workspace/{path}", json=body)
            assert response.status_code == 200, response.text
            assert response.json()["review_status"] == review_status
            assert response.json()["status"] == status
    assert all(call[3] == "oauth-user" for call in fake.calls)
    assert fake.calls[0][1].resource_id == "story-1"


def test_story_result_keeps_safe_projection_and_reject_notes_limit():
    fake = FakeReviewData()
    notes = "改" * 2_000
    with _client(fake) as client:
        response = client.post("/api/story-workspace/stories/story-2/reject", json={"review_notes": notes})
        assert response.status_code == 200
        assert response.json()["review_notes"] == notes
        for forbidden in ("content", "source_thread_ref", "artifact_source_type", "reviewed_script_revision"):
            assert forbidden not in response.json()
        too_long = client.post("/api/story-workspace/stories/story-4/reject", json={"review_notes": "x" * 2_001})
        assert too_long.status_code == 422
    assert len(fake.calls) == 1


def test_batch_preserves_request_order_accounting_and_supports_archive():
    fake = FakeReviewData()
    with _client(fake) as client:
        response = client.post("/api/story-workspace/batch", json={
            "action": "confirm", "resource_type": "story", "ids": ["story-1", "story-2", "story-3"]})
        assert response.status_code == 200, response.text
        assert response.json()["total_requested"] == 3
        assert response.json()["total_updated"] == 1
        assert response.json()["skipped_ids"] == ["story-2", "story-3"]
        assert [item["id"] for item in response.json()["updated_items"]] == ["story-1"]
        archived = client.post("/api/story-workspace/batch", json={
            "action": "archive", "resource_type": "scene", "ids": ["scene-1", "scene-2"]})
        assert archived.status_code == 200
        assert archived.json()["updated_items"][0]["status"] == "archived"


def test_validation_rejects_invalid_batch_before_admin_call():
    fake = FakeReviewData()
    invalid = [
        {"action": "publish", "resource_type": "story", "ids": ["story-1"]},
        {"action": "confirm", "resource_type": "episode", "ids": ["story-1"]},
        {"action": "confirm", "resource_type": "story", "ids": []},
        {"action": "confirm", "resource_type": "story", "ids": ["same", "same"]},
        {"action": "confirm", "resource_type": "story", "ids": [f"id-{index}" for index in range(101)]},
    ]
    with _client(fake) as client:
        for payload in invalid:
            assert client.post("/api/story-workspace/batch", json=payload).status_code == 422
    assert fake.calls == []


def test_admin_errors_keep_original_status_and_unknown_state():
    fake = FakeReviewData()
    with _client(fake) as client:
        fake.failure = AdminDataError("STORY_WORKSPACE_REVIEW_NOT_FOUND", 404, "upstream", False)
        assert client.post("/api/story-workspace/stories/missing/confirm", json={}).status_code == 404
        fake.failure = AdminDataError("STORY_WORKSPACE_REVIEW_STATE_INVALID", 409, "upstream", False)
        invalid = client.post("/api/story-workspace/stories/confirmed/confirm", json={})
        assert invalid.status_code == 400
        assert invalid.json() == {"detail": "Item is not in pending review status"}
        fake.failure = AdminDataError("STORY_WORKSPACE_REVIEW_STATE_CHANGED", 409, "upstream", False)
        conflict = client.post("/api/story-workspace/batch", json={
            "action": "confirm", "resource_type": "story", "ids": ["story-1"]})
        assert conflict.status_code == 409
        fake.failure = AdminDataError("ADMIN_TIMEOUT", 504, "original", True)
        unknown = client.post("/api/story-workspace/stories/story-1/confirm", json={})
        assert unknown.status_code == 504
        assert unknown.json()["detail"]["outcome_unknown"] is True


def test_anonymous_request_still_requires_admin_authentication():
    app = FastAPI()
    app.dependency_overrides[story_workspace._story_review_data] = lambda: FakeReviewData()
    app.include_router(story_workspace.router)
    with TestClient(app) as client:
        response = client.post("/api/story-workspace/stories/story-1/confirm", json={})
    assert response.status_code == 401


def test_review_routes_have_no_dream_database_or_legacy_transaction_helper():
    source_path = Path(story_workspace.__file__)
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    route_names = {
        "confirm_story", "reject_story", "archive_story", "confirm_character",
        "reject_character", "confirm_scene", "reject_scene", "batch_review",
        "_transition_story_review",
    }
    functions = {
        node.name: node for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in route_names
    }
    assert set(functions) == route_names
    forbidden = {"_story_db", "database", "get_db", "execute", "executemany", "commit", "rollback"}
    for name, node in functions.items():
        used = {item.id for item in ast.walk(node) if isinstance(item, ast.Name)}
        attributes = {item.attr for item in ast.walk(node) if isinstance(item, ast.Attribute)}
        assert not ((used | attributes) & forbidden), name
    production_symbols = {
        node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert not production_symbols & {
        "_owned_review_row", "_transition_pending_review", "_archive_story",
        "_batch_review", "_audit_review_action",
    }
