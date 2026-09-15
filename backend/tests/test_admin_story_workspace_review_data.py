# [Input] Registry111 typed client with controlled capability, execute and receipt collaborators.
# [Output] Reply identity/order checks and original-request unknown-write recovery assertions.
# [Pos] Provider-free Dream review consumer test; no FastAPI, PostgreSQL, filesystem or Runtime process.
# [Sync] 2026-09-15: prove strict DTO consumption and no write retry.
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from services.admin_data.errors import AdminDataError
from services.admin_data.models import AbsentReceiptDTO, CommittedReceiptDTO
from services.admin_data.story_workspace_review_data import (
    TRANSITION_STORY_WORKSPACE_REVIEW,
    WORKFLOW_SCHEMA_REQUIREMENTS,
    AdminStoryWorkspaceReviewData,
    StoryWorkspaceReviewBatchInputDTO,
    StoryWorkspaceReviewBatchResultDTO,
    StoryWorkspaceReviewStoryDTO,
    StoryWorkspaceReviewTransitionInputDTO,
    StoryWorkspaceReviewTransitionResultDTO,
)

TIME = "2026-09-15T01:02:03.000Z"


def story(resource_id="story-1"):
    return StoryWorkspaceReviewStoryDTO(
        id=resource_id, identifier=resource_id, title="Story", description=None,
        status="published", review_status="confirmed", review_notes=None, type="short",
        character_count=0, scene_count=0, created_at=TIME, updated_at=TIME,
        confirmed_at=TIME, source_run_id=None, source_project_id=None, episode_count=None,
        artifact_status=None, artifact_manifest_revision=None, script_revision=None,
        artifact_sync_status=None, artifact_indexed_at=None, artifact_sync_error_code=None,
        script_size_bytes=None, artifact_available=None, reconcile_version=None,
    )


def boundary():
    client = Mock()
    client.capabilities.return_value = SimpleNamespace(
        schema_capabilities=list(WORKFLOW_SCHEMA_REQUIREMENTS)
    )
    return AdminStoryWorkspaceReviewData(client), client


def transition_input():
    return StoryWorkspaceReviewTransitionInputDTO(
        resource_type="story", resource_id="story-1", action="confirm", review_notes=None
    )


def transition_result(resource_id="story-1"):
    return StoryWorkspaceReviewTransitionResultDTO(resource_type="story", item=story(resource_id))


def test_transition_executes_once_and_checks_resource_identity():
    data, client = boundary()
    client.execute.return_value = transition_result()
    result = data.transition_recovering(transition_input(), "original", access_token="oauth")
    assert result.item.id == "story-1"
    client.execute.assert_called_once()
    client.receipt.assert_not_called()

    client.execute.return_value = transition_result("story-2")
    with pytest.raises(AdminDataError) as mismatch:
        data.transition(transition_input(), "mismatch", access_token="oauth")
    assert mismatch.value.code == "ADMIN_RESPONSE_INVALID"


def test_batch_checks_exact_order_partition_and_accounting():
    data, client = boundary()
    input_dto = StoryWorkspaceReviewBatchInputDTO(
        resource_type="story", ids=["story-1", "story-2"], action="confirm", review_notes=None
    )
    client.execute.return_value = StoryWorkspaceReviewBatchResultDTO(
        success=True, action="confirm", resource_type="story", total_requested=2,
        total_updated=1, skipped_ids=["story-2"], updated_items=[story("story-1")],
    )
    assert data.batch(input_dto, "batch", access_token="oauth").skipped_ids == ["story-2"]

    client.execute.return_value = StoryWorkspaceReviewBatchResultDTO(
        success=True, action="confirm", resource_type="story", total_requested=2,
        total_updated=1, skipped_ids=["story-1"], updated_items=[story("story-2")],
    )
    assert data.batch(input_dto, "valid-second", access_token="oauth").updated_items[0].id == "story-2"
    client.execute.return_value = StoryWorkspaceReviewBatchResultDTO(
        success=True, action="confirm", resource_type="story", total_requested=2,
        total_updated=1, skipped_ids=["story-2"], updated_items=[story("foreign")],
    )
    with pytest.raises(AdminDataError) as invalid:
        data.batch(input_dto, "invalid", access_token="oauth")
    assert invalid.value.code == "ADMIN_RESPONSE_INVALID"


def test_unknown_write_reads_only_original_committed_receipt():
    data, client = boundary()
    client.execute.side_effect = AdminDataError("ADMIN_TIMEOUT", 504, "upstream", True)
    client.receipt.return_value = CommittedReceiptDTO[StoryWorkspaceReviewTransitionResultDTO](
        status="committed", operation=TRANSITION_STORY_WORKSPACE_REVIEW.capability.name,
        request_id="original", result=transition_result(),
    )
    result = data.transition_recovering(transition_input(), "original", access_token="oauth")
    assert result.item.id == "story-1"
    client.execute.assert_called_once()
    client.receipt.assert_called_once_with(
        TRANSITION_STORY_WORKSPACE_REVIEW, "original", access_token="oauth"
    )


def test_absent_receipt_and_capability_drift_fail_closed():
    data, client = boundary()
    client.execute.side_effect = AdminDataError("ADMIN_UNAVAILABLE", 503, "original", True)
    client.receipt.return_value = AbsentReceiptDTO(
        status="absent", operation=TRANSITION_STORY_WORKSPACE_REVIEW.capability.name,
        request_id="original",
    )
    with pytest.raises(AdminDataError) as absent:
        data.transition_recovering(transition_input(), "original", access_token="oauth")
    assert absent.value.code == "ADMIN_WRITE_RESULT_UNKNOWN"
    assert absent.value.outcome_unknown is True

    data, client = boundary()
    client.capabilities.return_value = SimpleNamespace(schema_capabilities=[])
    with pytest.raises(AdminDataError) as capability:
        data.transition_recovering(transition_input(), "capability", access_token="oauth")
    assert capability.value.code == "ADMIN_CAPABILITY_UNAVAILABLE"
    client.execute.assert_not_called()
