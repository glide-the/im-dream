# [Sync] 2026-09-17: exercise domain gates through the reusable validated capability snapshot.
# [Input] Registry169 Pydantic contracts and controlled Admin client collaborators.
# [Output] Exact DTO/hash, capability, response-identity and receipt validation evidence.
# [Pos] Provider-free Dream consumer tests; no PostgreSQL, Runtime or filesystem.
# [Sync] 2026-09-16: pin the automatic-repair DTO boundary.
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from services.admin_data.dream_auto_repair_data import (
    SETTLE_DREAM_AUTO_REPAIR,
    AdminDreamAutoRepairData,
    DreamAutoRepairIdentityDTO,
    DreamAutoRepairSettleInputDTO,
    DreamAutoRepairSettleOutputDTO,
)
from services.admin_data.errors import AdminDataError
from services.admin_data.models import CommittedReceiptDTO
from services.admin_data.workflow_data import WORKFLOW_SCHEMA_REQUIREMENTS


def identity() -> DreamAutoRepairIdentityDTO:
    return DreamAutoRepairIdentityDTO(
        kind="story-workspace-dream-auto-repair",
        schema_version="story-workspace-dream-auto-repair/v1",
        originating_message_id="message-origin",
        originating_turn_id="turn-origin",
        workflow_run_id="run_" + "a" * 32,
        repair_attempt=1,
        validation_code="PROJECT_STORY_SLUG_MISMATCH",
        idempotency_key="dream-auto-repair/v1:" + "b" * 64,
        project_cleanup={
            "trusted_project_slug": "server-project",
            "stale_project_slugs": ["workspace-project"],
        },
    )


def input_dto() -> DreamAutoRepairSettleInputDTO:
    return DreamAutoRepairSettleInputDTO(
        thread_id="thread-1",
        message_id="dream_repair_" + "c" * 40,
        expected_identity=identity(),
        status="dispatched",
    )


def boundary():
    client = Mock()
    client.capabilities_snapshot.return_value = SimpleNamespace(
        schema_capabilities=list(WORKFLOW_SCHEMA_REQUIREMENTS)
    )
    return AdminDreamAutoRepairData(client), client


def test_registry169_contract_and_strict_identity_are_pinned():
    assert SETTLE_DREAM_AUTO_REPAIR.capability.model_dump() == {
        "name": "dream-auto-repair.settle",
        "kind": "write",
        "user_scope": "dream:write",
        "background_scope": None,
        "input_schema_version": 1,
        "output_schema_version": 1,
        "contract_sha256": (
            "155adcb6995b63e090cbc2906383ba4b"
            "78525c1f268a430ad6f2ba449b66b159"
        ),
    }
    with pytest.raises(ValidationError):
        DreamAutoRepairIdentityDTO.model_validate({
            **identity().model_dump(),
            "user_id": "42",
        })
    with pytest.raises(ValidationError):
        DreamAutoRepairIdentityDTO.model_validate({
            **identity().model_dump(),
            "project_cleanup": {
                "trusted_project_slug": "same-project",
                "stale_project_slugs": ["same-project"],
            },
        })


def test_settle_executes_once_and_validates_exact_message_status():
    data, client = boundary()
    dto = input_dto()
    client.execute.return_value = DreamAutoRepairSettleOutputDTO(
        message_id=dto.message_id,
        status=dto.status,
        changed=True,
    )

    result = data.settle(dto, "original", access_token="turn-grant")

    assert result.changed is True
    client.execute.assert_called_once_with(
        SETTLE_DREAM_AUTO_REPAIR,
        dto,
        "original",
        access_token="turn-grant",
    )
    client.receipt.assert_not_called()


def test_capability_drift_stops_before_write():
    data, client = boundary()
    client.capabilities_snapshot.return_value = SimpleNamespace(schema_capabilities=[])

    with pytest.raises(AdminDataError) as error:
        data.settle(input_dto(), "original", access_token="turn-grant")

    assert error.value.code == "ADMIN_CAPABILITY_UNAVAILABLE"
    client.execute.assert_not_called()


def test_committed_receipt_must_match_original_message_and_status():
    data, client = boundary()
    dto = input_dto()
    client.receipt.return_value = CommittedReceiptDTO[
        DreamAutoRepairSettleOutputDTO
    ](
        status="committed",
        operation=SETTLE_DREAM_AUTO_REPAIR.capability.name,
        request_id="original",
        result=DreamAutoRepairSettleOutputDTO(
            message_id="another-message",
            status="dispatched",
            changed=True,
        ),
    )

    with pytest.raises(AdminDataError) as error:
        data.receipt(dto, "original", access_token="turn-grant")

    assert error.value.code == "ADMIN_RESPONSE_INVALID"
    assert error.value.outcome_unknown is True
