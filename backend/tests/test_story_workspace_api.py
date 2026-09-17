# [Input] Authenticated Story Workspace routes and a strict fake Registry114 Admin catalog provider.
# [Output] Public pagination/detail/patch/error behavior plus a source-level no-PostgreSQL route fence.
# [Pos] Provider-free Story Workspace API contract; Admin integration owns ORM and transaction verification.
# [Sync] 2026-09-15: replace the legacy SQLite router fixture with Admin DTO consumer coverage.
from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers import story_workspace
from services.admin_data.errors import AdminDataError
from services.admin_data.request_auth import AdminRequestActor
from services.admin_data.story_workspace_catalog_data import (
    CharacterDetailResultDTO, CharacterListResultDTO, PaginationDTO,
    SceneDetailResultDTO, SceneListResultDTO, StoryDetailResultDTO, StoryListResultDTO,
    StoryWorkspaceCatalogCharacterDetailDTO, StoryWorkspaceCatalogPatchResultDTO,
    StoryWorkspaceCatalogRelatedCharacterDTO, StoryWorkspaceCatalogSceneDetailDTO,
    StoryWorkspaceCatalogStoryDetailDTO, StoryWorkspaceCatalogWorkspaceDTO,
    StoryWorkspaceCatalogWorkspaceResultDTO,
)
from services.admin_data.story_workspace_review_data import (
    StoryWorkspaceReviewCharacterDTO, StoryWorkspaceReviewSceneDTO,
    StoryWorkspaceReviewStoryDTO,
)

TIME = "2026-09-15T01:02:03.000Z"


def _story(resource_id: str = "story-1", *, title: str = "午夜咖啡馆"):
    return StoryWorkspaceReviewStoryDTO(
        id=resource_id, identifier=resource_id, title=title, description="雨夜故事",
        status="draft", review_status="pending", review_notes=None, type="short",
        character_count=1, scene_count=1, created_at=TIME, updated_at=TIME,
        confirmed_at=None, source_run_id=None, source_project_id=None,
        episode_count=None, artifact_status=None, artifact_manifest_revision=None,
        script_revision=None, artifact_sync_status=None, artifact_indexed_at=None,
        artifact_sync_error_code=None, script_size_bytes=None,
        artifact_available=None, reconcile_version=None,
    )


def _character(resource_id: str = "character-1"):
    return StoryWorkspaceReviewCharacterDTO(
        id=resource_id, identifier=resource_id, name="林小雨", avatar_url=None,
        identity="咖啡师", personality="温柔", background="雨城", catchphrase=None,
        tags=["温柔"], story_count=1, review_status="pending", review_notes=None,
        status="active", created_at=TIME, updated_at=TIME, confirmed_at=None, archived_at=None,
    )


def _scene(resource_id: str = "scene-1"):
    return StoryWorkspaceReviewSceneDTO(
        id=resource_id, identifier=resource_id, name="开场·雨夜", description="雨中的咖啡馆",
        story_id="story-1", character_count=1, order_index=1, review_status="pending",
        review_notes=None, status="active", created_at=TIME, updated_at=TIME,
        confirmed_at=None, archived_at=None,
    )


def _workspace(name: str = "Writer One"):
    return StoryWorkspaceCatalogWorkspaceDTO(
        id="workspace-1", name=name, settings={"theme": "ink"},
        created_at=TIME, updated_at=TIME,
    )


class FakeCatalogData:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Any, str, str]] = []
        self.failure: AdminDataError | None = None

    def _begin(self, name: str, input_dto, request_id: str, access_token: str):
        self.calls.append((name, input_dto, request_id, access_token))
        if self.failure:
            raise self.failure

    def workspace_recovering(self, input_dto, request_id: str, *, access_token: str):
        self._begin("workspace", input_dto, request_id, access_token)
        root = input_dto.root
        return StoryWorkspaceCatalogWorkspaceResultDTO(
            action=root.action, item=_workspace("Ink Room" if root.action == "patch" else "Writer One"))

    def read(self, input_dto, request_id: str, *, access_token: str):
        self._begin("read", input_dto, request_id, access_token)
        root = input_dto.root
        page = PaginationDTO(page=getattr(root, "page", 1), per_page=getattr(root, "per_page", 20), total=1, total_pages=1)
        if root.view == "story_list":
            return StoryListResultDTO(view=root.view, data=[_story()], pagination=page)
        if root.view == "character_list":
            return CharacterListResultDTO(view=root.view, data=[_character()], pagination=page)
        if root.view == "scene_list":
            return SceneListResultDTO(view=root.view, data=[_scene()], pagination=page)
        if root.view == "story_detail":
            item = StoryWorkspaceCatalogStoryDetailDTO(
                **_story(root.resource_id).model_dump(),
                characters=[StoryWorkspaceCatalogRelatedCharacterDTO(
                    **_character().model_dump(), role_type="主角")], scenes=[_scene()])
            return StoryDetailResultDTO(view=root.view, item=item)
        if root.view == "character_detail":
            item = StoryWorkspaceCatalogCharacterDetailDTO(
                **_character(root.resource_id).model_dump(), stories=[_story()])
            return CharacterDetailResultDTO(view=root.view, item=item)
        item = StoryWorkspaceCatalogSceneDetailDTO(
            **_scene(root.resource_id).model_dump(), story=_story(), characters=[_character()])
        return SceneDetailResultDTO(view=root.view, item=item)

    def patch_recovering(self, input_dto, request_id: str, *, access_token: str):
        self._begin("patch", input_dto, request_id, access_token)
        root = input_dto.root
        if root.resource_type == "story":
            item = _story(root.resource_id, title=root.patch.title or "午夜咖啡馆")
        elif root.resource_type == "character":
            item = _character(root.resource_id).model_copy(update=root.patch.model_dump())
        else:
            item = _scene(root.resource_id).model_copy(update=root.patch.model_dump())
        return StoryWorkspaceCatalogPatchResultDTO.model_validate(
            {"resource_type": root.resource_type, "item": item.model_dump()}).root


def _actor() -> AdminRequestActor:
    return AdminRequestActor(
        subject="subject", canonical_user_id="1", client_id="dream-browser",
        scopes=frozenset({"dream:read", "dream:write"}), issued_at=1,
        expires_at=4_102_444_800, access_token="oauth-user")


def _client(fake: FakeCatalogData, *, authenticated: bool = True):
    app = FastAPI()
    if authenticated:
        app.dependency_overrides[story_workspace.get_current_user] = lambda: _actor().current_user_projection()
    app.dependency_overrides[story_workspace._story_catalog_data] = lambda: fake
    app.include_router(story_workspace.router)
    return TestClient(app)


def test_workspace_ensure_and_patch_use_admin_write_recovery():
    fake = FakeCatalogData()
    with _client(fake) as client:
        first = client.get("/api/story-workspace/workspace")
        patched = client.patch("/api/story-workspace/workspace/workspace-1", json={
            "name": "Ink Room", "settings": {"theme": "paper"}})
    assert first.status_code == 200 and first.json()["id"] == "workspace-1"
    assert "owner_id" not in first.json()
    assert patched.status_code == 200 and patched.json()["name"] == "Ink Room"
    assert fake.calls[0][1].root.action == "ensure"
    assert fake.calls[1][1].root.patch.model_dump() == {"name": "Ink Room", "settings": {"theme": "paper"}}
    assert all(call[3] == "oauth-user" for call in fake.calls)


def test_lists_preserve_query_pagination_and_public_projection():
    fake = FakeCatalogData()
    with _client(fake) as client:
        story = client.get("/api/story-workspace/stories", params={
            "q": "咖啡", "status": "draft", "type": "short,outline",
            "review_status": "pending,rejected", "sort": "title", "order": "asc",
            "page": 2, "per_page": 1})
        character = client.get("/api/story-workspace/characters", params={"review_status": "pending"})
        scene = client.get("/api/story-workspace/scenes", params={"story_id": "story-1"})
    assert story.json()["pagination"] == {"page": 2, "per_page": 1, "total": 1, "total_pages": 1}
    request = fake.calls[0][1].root
    assert request.status == ["draft"] and request.type == ["short", "outline"]
    assert request.review_status == ["pending", "rejected"] and request.sort == "title"
    assert character.json()["data"][0]["tags"] == ["温柔"]
    assert scene.json()["data"][0]["story_id"] == "story-1"
    for forbidden in ("content", "source_thread_ref", "artifact_source_type", "author_id"):
        assert forbidden not in story.json()["data"][0]


def test_detail_relations_are_preserved_as_safe_dtos():
    fake = FakeCatalogData()
    with _client(fake) as client:
        story = client.get("/api/story-workspace/stories/story-1").json()
        character = client.get("/api/story-workspace/characters/character-1").json()
        scene = client.get("/api/story-workspace/scenes/scene-1").json()
    assert story["characters"][0]["role_type"] == "主角" and story["scenes"][0]["id"] == "scene-1"
    assert character["stories"][0]["id"] == "story-1"
    assert scene["story"]["id"] == "story-1" and scene["characters"][0]["id"] == "character-1"


def test_controlled_patches_keep_present_fields_and_reject_authority_fields():
    fake = FakeCatalogData()
    with _client(fake) as client:
        story = client.patch("/api/story-workspace/stories/story-1", json={
            "title": "新标题", "description": None, "type": "script"})
        character = client.patch("/api/story-workspace/characters/character-1", json={
            "identity": "夜班咖啡师", "tags": ["温柔", "敏锐"]})
        scene = client.patch("/api/story-workspace/scenes/scene-1", json={
            "description": "雨更大了", "order_index": 3})
        assert client.patch("/api/story-workspace/stories/story-1", json={}).status_code == 400
        for body in ({"author_id": 2}, {"review_status": "confirmed"}, {"sql": "select 1"}):
            assert client.patch("/api/story-workspace/stories/story-1", json=body).status_code == 422
    assert story.json()["title"] == "新标题" and character.json()["tags"] == ["温柔", "敏锐"]
    assert scene.json()["order_index"] == 3
    assert fake.calls[0][1].root.patch.model_dump() == {
        "title": "新标题", "description": None, "type": "script"}


def test_query_not_found_and_unknown_write_fail_closed():
    fake = FakeCatalogData()
    with _client(fake) as client:
        assert client.get("/api/story-workspace/stories", params={"sort": "title; DROP TABLE users"}).status_code == 400
        assert client.get("/api/story-workspace/stories", params={"order": "sideways"}).status_code == 400
        assert client.get("/api/story-workspace/stories", params={"per_page": 101}).status_code == 422
        fake.failure = AdminDataError("STORY_WORKSPACE_CATALOG_NOT_FOUND", 404, "upstream", False)
        assert client.get("/api/story-workspace/stories/missing").status_code == 404
        fake.failure = AdminDataError("ADMIN_TIMEOUT", 504, "original", True)
        unknown = client.patch("/api/story-workspace/stories/story-1", json={"title": "Maybe"})
    assert unknown.status_code == 504
    assert unknown.json()["detail"] == {
        "error_code": "ADMIN_TIMEOUT", "request_id": "original", "outcome_unknown": True}


def test_catalog_routes_require_authentication():
    with _client(FakeCatalogData(), authenticated=False) as client:
        assert client.get("/api/story-workspace/stories").status_code == 401


def test_catalog_route_source_has_no_dream_database_path():
    source_path = Path(story_workspace.__file__)
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    route_names = {
        "get_workspace", "patch_workspace", "list_stories", "get_story", "patch_story",
        "list_characters", "get_character", "patch_character", "list_scenes", "get_scene",
        "patch_scene", "_patch_catalog_resource"}
    functions = {node.name: node for node in ast.walk(tree)
                 if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in route_names}
    assert set(functions) == route_names
    forbidden = {"_story_db", "database", "get_db", "execute", "executemany", "commit", "rollback",
                 "StoryWorkspacePublicStoryRepository", "_owned_row", "_patch_owned_row", "_paginate_query"}
    for name, node in functions.items():
        symbols = {item.id for item in ast.walk(node) if isinstance(item, ast.Name)}
        symbols |= {item.attr for item in ast.walk(node) if isinstance(item, ast.Attribute)}
        assert not symbols & forbidden, name
    module_symbols = {node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    assert not module_symbols & {"_story_db", "_owned_row", "_patch_owned_row", "_paginate_query"}


def test_router_preserves_catalog_paths():
    methods_by_path: dict[str, set[str]] = {}
    for route in story_workspace.router.routes:
        methods_by_path.setdefault(route.path, set()).update(route.methods)
    expected = {
        "/api/story-workspace/workspace": {"GET"},
        "/api/story-workspace/workspace/{workspace_id}": {"PATCH"},
        "/api/story-workspace/stories": {"GET"},
        "/api/story-workspace/stories/{story_id}": {"GET", "PATCH"},
        "/api/story-workspace/characters": {"GET"},
        "/api/story-workspace/characters/{character_id}": {"GET", "PATCH"},
        "/api/story-workspace/scenes": {"GET"},
        "/api/story-workspace/scenes/{scene_id}": {"GET", "PATCH"}}
    for path, methods in expected.items():
        assert methods_by_path[path] == methods
