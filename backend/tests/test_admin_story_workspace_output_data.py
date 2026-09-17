# [Input] Registry109 typed client with controlled execute, receipt and capability collaborators.
# [Output] One-shot write, original committed recovery and closed unknown-result behavior.
# [Pos] Provider-free Dream consumer tests; no FastAPI route, PostgreSQL or Runtime process.
# [Sync] 2026-09-15: recover only the original Story output request without POST retry.
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from services.admin_data.errors import AdminDataError
from services.admin_data.models import AbsentReceiptDTO, CommittedReceiptDTO
from services.admin_data.story_workspace_output_data import (
    STORE_STORY_WORKSPACE_OUTPUT,
    WORKFLOW_SCHEMA_REQUIREMENTS,
    AdminStoryWorkspaceOutputData,
    StoryWorkspaceOutputInputDTO,
    StoryWorkspaceOutputResultDTO,
)


def input_dto() -> StoryWorkspaceOutputInputDTO:
    return StoryWorkspaceOutputInputDTO(
        thread_id="thread-1",
        story={
            "title": "标题",
            "description": None,
            "type": "short",
            "content": None,
            "characters": [],
            "scenes": [],
        },
    )


def output_dto(thread_id: str = "thread-1") -> StoryWorkspaceOutputResultDTO:
    return StoryWorkspaceOutputResultDTO(
        story_id="story-1",
        review_status="pending",
        character_ids=[],
        scene_ids=[],
        chat_thread_id=thread_id,
        deck_id=None,
        deck_name=None,
        deck_name_zh=None,
        deck_name_en=None,
    )


def boundary():
    client = Mock()
    client.capabilities.return_value = SimpleNamespace(
        schema_capabilities=list(WORKFLOW_SCHEMA_REQUIREMENTS)
    )
    return AdminStoryWorkspaceOutputData(client), client


def test_success_executes_once_without_receipt_lookup():
    data, client = boundary()
    client.execute.return_value = output_dto()

    result = data.store_recovering(
        input_dto(), "original", access_token="oauth-user"
    )

    assert result.story_id == "story-1"
    client.execute.assert_called_once()
    client.receipt.assert_not_called()


def test_unknown_response_recovers_original_committed_result_without_post_retry():
    data, client = boundary()
    client.execute.side_effect = AdminDataError(
        "ADMIN_UNAVAILABLE", 503, "original", True
    )
    client.receipt.return_value = CommittedReceiptDTO[
        StoryWorkspaceOutputResultDTO
    ](
        status="committed",
        operation=STORE_STORY_WORKSPACE_OUTPUT.capability.name,
        request_id="original",
        result=output_dto(),
    )

    result = data.store_recovering(
        input_dto(), "original", access_token="oauth-user"
    )

    assert result.chat_thread_id == "thread-1"
    client.execute.assert_called_once()
    client.receipt.assert_called_once_with(
        STORE_STORY_WORKSPACE_OUTPUT,
        "original",
        access_token="oauth-user",
    )


def test_absent_original_receipt_keeps_the_write_outcome_unknown():
    data, client = boundary()
    client.execute.side_effect = AdminDataError(
        "ADMIN_UNAVAILABLE", 503, "original", True
    )
    client.receipt.return_value = AbsentReceiptDTO(
        status="absent",
        operation=STORE_STORY_WORKSPACE_OUTPUT.capability.name,
        request_id="original",
    )

    with pytest.raises(AdminDataError) as error:
        data.store_recovering(
            input_dto(), "original", access_token="oauth-user"
        )

    assert error.value.code == "ADMIN_WRITE_RESULT_UNKNOWN"
    assert error.value.outcome_unknown is True
    client.execute.assert_called_once()


def test_capability_drift_stops_before_domain_write():
    data, client = boundary()
    client.capabilities.return_value = SimpleNamespace(schema_capabilities=[])

    with pytest.raises(AdminDataError) as error:
        data.store_recovering(
            input_dto(), "original", access_token="oauth-user"
        )

    assert error.value.code == "ADMIN_CAPABILITY_UNAVAILABLE"
    assert error.value.outcome_unknown is False
    client.execute.assert_not_called()
    client.receipt.assert_not_called()


def test_receipt_transport_failure_keeps_original_request_unknown():
    data, client = boundary()
    client.execute.side_effect = AdminDataError(
        "ADMIN_UNAVAILABLE", 503, "untrusted-upstream-id", True
    )
    client.receipt.side_effect = AdminDataError(
        "ADMIN_UNAVAILABLE", 503, "receipt-upstream-id", False
    )

    with pytest.raises(AdminDataError) as error:
        data.store_recovering(
            input_dto(), "original", access_token="oauth-user"
        )

    assert error.value.code == "ADMIN_UNAVAILABLE"
    assert error.value.request_id == "original"
    assert error.value.outcome_unknown is True
    client.receipt.assert_called_once_with(
        STORE_STORY_WORKSPACE_OUTPUT,
        "original",
        access_token="oauth-user",
    )


def test_invalid_committed_thread_stays_unknown_and_nonunknown_error_skips_receipt():
    data, client = boundary()
    client.execute.side_effect = AdminDataError(
        "ADMIN_UNAVAILABLE", 503, "original", True
    )
    client.receipt.return_value = CommittedReceiptDTO[
        StoryWorkspaceOutputResultDTO
    ](
        status="committed",
        operation=STORE_STORY_WORKSPACE_OUTPUT.capability.name,
        request_id="original",
        result=output_dto("thread-2"),
    )
    with pytest.raises(AdminDataError) as invalid:
        data.store_recovering(
            input_dto(), "original", access_token="oauth-user"
        )
    assert invalid.value.code == "ADMIN_RESPONSE_INVALID"
    assert invalid.value.outcome_unknown is True

    client.reset_mock()
    client.capabilities.return_value = SimpleNamespace(
        schema_capabilities=list(WORKFLOW_SCHEMA_REQUIREMENTS)
    )
    client.execute.side_effect = AdminDataError(
        "ADMIN_OPERATION_INPUT_INVALID", 400, "original", False
    )
    with pytest.raises(AdminDataError) as rejected:
        data.store_recovering(
            input_dto(), "original", access_token="oauth-user"
        )
    assert rejected.value.code == "ADMIN_OPERATION_INPUT_INVALID"
    client.receipt.assert_not_called()
