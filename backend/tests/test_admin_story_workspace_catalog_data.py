# [Sync] 2026-09-17: exercise domain gates through the reusable validated capability snapshot.
# [Input] Registry114 typed client with controlled capability, execute, and receipt collaborators.
# [Output] View/resource identity checks, present-field wire DTO, and original-request recovery assertions.
# [Pos] Provider-free Dream catalog consumer test; no FastAPI, PostgreSQL, filesystem, or Runtime process.
# [Sync] 2026-09-15: prove strict DTO consumption and no write retry.
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from services.admin_data.errors import AdminDataError
from services.admin_data.models import AbsentReceiptDTO, CommittedReceiptDTO
from services.admin_data.story_workspace_catalog_data import (
    PATCH_STORY_WORKSPACE_CATALOG, WORKFLOW_SCHEMA_REQUIREMENTS,
    AdminStoryWorkspaceCatalogData, CharacterPatchDTO, PaginationDTO,
    StoryListResultDTO, StoryPatchResultDTO, StoryWorkspaceCatalogPatchInputDTO,
    StoryWorkspaceCatalogPatchResultDTO, StoryWorkspaceCatalogReadInputDTO,
    StoryWorkspaceCatalogReadResultDTO, StoryWorkspaceCatalogWorkspaceInputDTO,
    StoryWorkspaceCatalogWorkspaceResultDTO, StoryWorkspaceCatalogWorkspaceDTO,
)
from services.admin_data.story_workspace_review_data import StoryWorkspaceReviewStoryDTO

TIME = "2026-09-15T01:02:03.000Z"


def story(resource_id="story-1"):
    return StoryWorkspaceReviewStoryDTO(
        id=resource_id, identifier=resource_id, title="Story", description=None,
        status="draft", review_status="pending", review_notes=None, type="short",
        character_count=0, scene_count=0, created_at=TIME, updated_at=TIME,
        confirmed_at=None, source_run_id=None, source_project_id=None, episode_count=None,
        artifact_status=None, artifact_manifest_revision=None, script_revision=None,
        artifact_sync_status=None, artifact_indexed_at=None, artifact_sync_error_code=None,
        script_size_bytes=None, artifact_available=None, reconcile_version=None)


def boundary():
    client = Mock()
    client.capabilities_snapshot.return_value = SimpleNamespace(
        schema_capabilities=list(WORKFLOW_SCHEMA_REQUIREMENTS))
    return AdminStoryWorkspaceCatalogData(client), client


def test_read_checks_view_resource_and_pagination_identity():
    data, client = boundary()
    input_dto = StoryWorkspaceCatalogReadInputDTO.model_validate({
        "view": "story_list", "q": None, "review_status": [], "status": [], "type": [],
        "sort": "updated_at", "order": "desc", "page": 2, "per_page": 10})
    client.execute.return_value = StoryWorkspaceCatalogReadResultDTO(
        root=StoryListResultDTO(view="story_list", data=[story()],
                                pagination=PaginationDTO(page=2, per_page=10, total=1, total_pages=1)))
    assert data.read(input_dto, "read", access_token="oauth").data[0].id == "story-1"
    client.execute.return_value = StoryWorkspaceCatalogReadResultDTO(
        root=StoryListResultDTO(view="story_list", data=[story()],
                                pagination=PaginationDTO(page=1, per_page=10, total=1, total_pages=1)))
    with pytest.raises(AdminDataError) as mismatch:
        data.read(input_dto, "mismatch", access_token="oauth")
    assert mismatch.value.code == "ADMIN_RESPONSE_INVALID"


def test_patch_preserves_explicit_null_and_recovers_only_original_receipt():
    data, client = boundary()
    input_dto = StoryWorkspaceCatalogPatchInputDTO.model_validate({
        "resource_type": "story", "resource_id": "story-1", "patch": {"description": None}})
    assert input_dto.model_dump(mode="json")["patch"] == {"description": None}
    result = StoryWorkspaceCatalogPatchResultDTO(
        root=StoryPatchResultDTO(resource_type="story", item=story()))
    client.execute.side_effect = AdminDataError("ADMIN_TIMEOUT", 504, "original", True)
    client.receipt.return_value = CommittedReceiptDTO[StoryWorkspaceCatalogPatchResultDTO](
        status="committed", operation=PATCH_STORY_WORKSPACE_CATALOG.capability.name,
        request_id="original", result=result)
    assert data.patch_recovering(input_dto, "original", access_token="oauth").item.id == "story-1"
    client.execute.assert_called_once()
    client.receipt.assert_called_once_with(PATCH_STORY_WORKSPACE_CATALOG, "original", access_token="oauth")


def test_absent_receipt_capability_drift_and_closed_patch_fail_closed():
    data, client = boundary()
    input_dto = StoryWorkspaceCatalogPatchInputDTO.model_validate({
        "resource_type": "character", "resource_id": "character-1", "patch": {"identity": None}})
    assert isinstance(input_dto.root.patch, CharacterPatchDTO)
    client.execute.side_effect = AdminDataError("ADMIN_UNAVAILABLE", 503, "original", True)
    client.receipt.return_value = AbsentReceiptDTO(
        status="absent", operation=PATCH_STORY_WORKSPACE_CATALOG.capability.name, request_id="original")
    with pytest.raises(AdminDataError) as absent:
        data.patch_recovering(input_dto, "original", access_token="oauth")
    assert absent.value.code == "ADMIN_WRITE_RESULT_UNKNOWN" and absent.value.outcome_unknown is True

    data, client = boundary()
    client.capabilities_snapshot.return_value = SimpleNamespace(schema_capabilities=[])
    ensure = StoryWorkspaceCatalogWorkspaceInputDTO.model_validate({"action": "ensure"})
    with pytest.raises(AdminDataError) as capability:
        data.workspace_recovering(ensure, "capability", access_token="oauth")
    assert capability.value.code == "ADMIN_CAPABILITY_UNAVAILABLE"
    client.execute.assert_not_called()


def test_workspace_reply_must_match_action_and_patch_identity():
    data, client = boundary()
    input_dto = StoryWorkspaceCatalogWorkspaceInputDTO.model_validate({
        "action": "patch", "workspace_id": "workspace-1", "patch": {"name": "Ink"}})
    client.execute.return_value = StoryWorkspaceCatalogWorkspaceResultDTO(
        action="patch", item=StoryWorkspaceCatalogWorkspaceDTO(
            id="workspace-2", name="Ink", settings={}, created_at=TIME, updated_at=TIME))
    with pytest.raises(AdminDataError) as mismatch:
        data.workspace(input_dto, "workspace", access_token="oauth")
    assert mismatch.value.code == "ADMIN_RESPONSE_INVALID" and mismatch.value.outcome_unknown is True
