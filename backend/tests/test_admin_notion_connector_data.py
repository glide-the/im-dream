# [Input] Registry148-168 Dream DTO consumer and synthetic client outcomes.
# [Output] Verify capability pinning, strict inputs, and user/background original-receipt recovery.
# [Pos] Provider-free Admin Notion data-client contract tests.
# [Sync] 2026-09-16: add deterministic DTO and unknown-write coverage.
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.admin_data.errors import AdminDataError
from services.admin_data.models import CommittedReceiptDTO
from services.admin_data.notion_connector_data import (
    DELETE_NOTION_CONNECTOR,
    LIST_NOTION_CONNECTORS,
    NOTION_CONNECTOR_OPERATIONS,
    NOTION_CONNECTOR_SCHEMA_REQUIREMENTS,
    SAVE_NOTION_SYNC_SNAPSHOT,
    AdminNotionConnectorData,
    NotionConnectorDeleteInputDTO,
    NotionConnectorDeleteOutputDTO,
    NotionConnectorListInputDTO,
    NotionSnapshotOutputDTO,
    NotionSyncSnapshotSaveInputDTO,
)


CONNECTOR_ID = "123e4567-e89b-42d3-a456-426614174000"


class _UnknownWriteClient:
    def __init__(self, result) -> None:
        self.result = result
        self.user_receipts: list[tuple] = []
        self.background_receipts: list[tuple] = []

    def supports(self, operations, requirements) -> bool:
        return (
            operations is NOTION_CONNECTOR_OPERATIONS
            and requirements is NOTION_CONNECTOR_SCHEMA_REQUIREMENTS
        )

    def capabilities(self, _request_id):
        raise AssertionError("ready catalog must not refresh")

    def execute(self, *_args, **_kwargs):
        raise AdminDataError("ADMIN_TIMEOUT", 504, outcome_unknown=True)

    def receipt(self, operation, request_id, *, access_token):
        self.user_receipts.append((operation, request_id, access_token))
        return CommittedReceiptDTO(
            status="committed",
            operation=operation.capability.name,
            request_id=request_id,
            result=self.result,
        )

    def background_receipt(self, operation, request_id, *, connector_id):
        self.background_receipts.append((operation, request_id, connector_id))
        return CommittedReceiptDTO(
            status="committed",
            operation=operation.capability.name,
            request_id=request_id,
            result=self.result,
        )


def test_registry_contains_exact_user_and_background_authorities() -> None:
    assert len(NOTION_CONNECTOR_OPERATIONS) == 21
    assert len({item.capability.name for item in NOTION_CONNECTOR_OPERATIONS}) == 21
    user = [item for item in NOTION_CONNECTOR_OPERATIONS if item.capability.user_scope]
    background = [
        item
        for item in NOTION_CONNECTOR_OPERATIONS
        if item.capability.background_scope
    ]
    assert len(user) == 16 and len(background) == 5
    assert all(item.capability.background_scope == "connectors:sync" for item in background)
    assert {
        item.capability for item in NOTION_CONNECTOR_SCHEMA_REQUIREMENTS
    } == {"identity.better-auth.v1", "dream.schema.unified.v1"}


def test_user_unknown_write_recovers_only_original_oauth_receipt() -> None:
    client = _UnknownWriteClient(NotionConnectorDeleteOutputDTO(deleted=True))
    data = AdminNotionConnectorData(client)  # type: ignore[arg-type]
    result = data.execute(
        DELETE_NOTION_CONNECTOR,
        NotionConnectorDeleteInputDTO(
            authority=None,
            connector_id=CONNECTOR_ID,
        ),
        "request-user",
        access_token="oauth-token",
    )
    assert result.deleted is True
    assert client.user_receipts == [
        (DELETE_NOTION_CONNECTOR, "request-user", "oauth-token")
    ]
    assert client.background_receipts == []


def test_background_unknown_write_requires_original_connector_selector() -> None:
    client = _UnknownWriteClient(NotionSnapshotOutputDTO(snapshot={}))
    data = AdminNotionConnectorData(client)  # type: ignore[arg-type]
    result = data.execute(
        SAVE_NOTION_SYNC_SNAPSHOT,
        NotionSyncSnapshotSaveInputDTO(
            connector_id=CONNECTOR_ID,
            workspace_id=CONNECTOR_ID,
            snapshot={},
            synced_resources=[],
        ),
        "request-background",
        access_token=None,
        background_connector_id=CONNECTOR_ID,
    )
    assert result.snapshot == {}
    assert client.background_receipts == [
        (SAVE_NOTION_SYNC_SNAPSHOT, "request-background", CONNECTOR_ID)
    ]
    assert client.user_receipts == []


def test_read_unknown_result_is_never_converted_to_a_receipt_lookup() -> None:
    client = _UnknownWriteClient(NotionConnectorDeleteOutputDTO(deleted=True))
    data = AdminNotionConnectorData(client)  # type: ignore[arg-type]
    with pytest.raises(AdminDataError) as captured:
        data.execute(
            LIST_NOTION_CONNECTORS,
            NotionConnectorListInputDTO(authority=None),
            "request-read",
            access_token="oauth-token",
        )
    assert captured.value.outcome_unknown is True
    assert client.user_receipts == [] and client.background_receipts == []
