# [Sync] 2026-09-17: align provider-free fake clients with reusable validated capability snapshots.
# [Input] Registry170-174 strict DTOs, fake Admin catalog and closed receipt outcomes.
# [Output] Exact capability pins, actor-free commands and one-dispatch recovery evidence.
# [Pos] Provider-free Dream contract test; no PostgreSQL, filesystem or Runtime.
# [Sync] 2026-09-17: pin plan to Admin's dream:write authorization requirement.
# [Sync] 2026-09-16: lock the Admin Deck Plugin control consumer contract.
from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from services.admin_data.config import AdminDataConfig
from services.admin_data.deck_plugin_control_data import (
    APPLY_DECK_PLUGIN_CONTROL,
    DECK_PLUGIN_CONTROL_OPERATIONS,
    DECK_PLUGIN_CONTROL_SCHEMA_REQUIREMENTS,
    PLAN_DECK_PLUGIN_CONTROL,
    AdminDeckPluginControlData,
    DeckPluginControlApplyInputDTO,
    DeckPluginControlCommandDTO,
    DeckPluginControlOperationDTO,
    DeckPluginControlPlanDTO,
)
from services.admin_data.errors import AdminDataError
from services.admin_data.models import AbsentReceiptDTO, CommittedReceiptDTO
from services.admin_data.request_auth import AdminRequestAuth

REQUEST_ID = "deck-plugin-control-request"
PLUGIN_ID = "example.story"
VERSION = "1.0.0"


def command() -> DeckPluginControlCommandDTO:
    return DeckPluginControlCommandDTO(
        action="enable",
        scope_type="workspace",
        scope_id="workspace-1",
        deck_plugin_id=PLUGIN_ID,
    )


def plan() -> DeckPluginControlPlanDTO:
    return DeckPluginControlPlanDTO(
        command=command(),
        expected_revision=2,
        deck_plugin_installation_id="dpi_" + "a" * 32,
        target_version=VERSION,
        source_policy_id="controlled:builtin://example",
        capability_diff={"added": [], "removed": []},
        requires_runtime_evidence=False,
        runtime_target=None,
    )


def operation() -> DeckPluginControlOperationDTO:
    return DeckPluginControlOperationDTO(
        operation_id="op_" + "b" * 32,
        deck_plugin_id=PLUGIN_ID,
        target_version=VERSION,
        status="completed",
        phase="ready",
        progress=100,
        message="Deck Plugin enable completed.",
        updated_at=datetime.now(UTC),
    )


class FakeClient:
    def __init__(self, reply) -> None:
        self.reply = reply
        self.execute_error: AdminDataError | None = None
        self.receipt_reply = None
        self.execute_calls = []
        self.receipt_calls = []

    def capabilities_snapshot(self, request_id):
        return SimpleNamespace(
            schema_capabilities=list(DECK_PLUGIN_CONTROL_SCHEMA_REQUIREMENTS)
        )

    def execute(self, operation_value, input_dto, request_id, *, access_token):
        self.execute_calls.append(
            (operation_value, input_dto, request_id, access_token)
        )
        if self.execute_error is not None:
            raise self.execute_error
        return self.reply

    def receipt(self, operation_value, request_id, *, access_token):
        self.receipt_calls.append((operation_value, request_id, access_token))
        return self.receipt_reply or AbsentReceiptDTO(
            status="absent",
            operation=operation_value.capability.name,
            request_id=request_id,
        )


def test_registry170_174_hashes_commands_and_registration_are_exact():
    assert [item.capability.name for item in DECK_PLUGIN_CONTROL_OPERATIONS] == [
        "deck-plugin-control.list",
        "deck-plugin-control.version",
        "deck-plugin-control.readiness",
        "deck-plugin-control.plan",
        "deck-plugin-control.apply",
    ]
    assert [
        item.capability.contract_sha256 for item in DECK_PLUGIN_CONTROL_OPERATIONS
    ] == [
        "580809db8126d3f45cc233a7a4c32f38cfd19daa6cb5ccd2154cbec10ba359b2",
        "8fb594490a7766bc81aa273c2aee17e4616d22d0f0c724c718f5797d435ca589",
        "8c41de9052a5036d48f52a0945174d654b0442dd43159953978310cca0fc5fa3",
        "2e11a56d2e3efb491762cfc5559bd7a2cf1f2aee527632243424a62ef0e38df8",
        "fba707edfdad4ed88f82b8325d2cfd90a7f52f9ad24a34e07e05021c0978573e",
    ]
    assert [
        item.capability.user_scope for item in DECK_PLUGIN_CONTROL_OPERATIONS
    ] == ["dream:read", "dream:read", "dream:read", "dream:write", "dream:write"]
    for rejected in (
        {**command().model_dump(), "actor_id": "42"},
        {**command().model_dump(), "database": "dream"},
        {**command().model_dump(), "target_version": VERSION},
    ):
        with pytest.raises(ValidationError):
            DeckPluginControlCommandDTO.model_validate(rejected)
    install = DeckPluginControlCommandDTO(
        action="install",
        scope_type="workspace",
        scope_id="workspace-1",
        deck_plugin_id=PLUGIN_ID,
        deck_plugin_version=VERSION,
        source_type="controlled",
        source="builtin://example",
    )
    assert install.model_dump(mode="json") == {
        "action": "install",
        "scope_type": "workspace",
        "scope_id": "workspace-1",
        "deck_plugin_id": PLUGIN_ID,
        "deck_plugin_version": VERSION,
        "source_type": "controlled",
        "source": "builtin://example",
    }

    config = AdminDataConfig(
        base_url="https://admin.example.test",
        issuer="https://admin.example.test/api/auth",
        resource="https://dream.example.test/api",
        service_client_id="dream",
        service_secret="s" * 32,
        timeout_seconds=1,
        max_response_bytes=1024 * 1024,
    )
    owner = AdminRequestAuth(config)
    try:
        for item in DECK_PLUGIN_CONTROL_OPERATIONS:
            assert owner.client._operations[item.capability.name] is item
    finally:
        owner.close()


def test_plan_binds_the_returned_command_to_the_original_input():
    client = FakeClient(plan())
    data = AdminDeckPluginControlData(client)
    assert data.plan(command(), REQUEST_ID, access_token="oauth") == plan()
    assert client.execute_calls == [
        (PLAN_DECK_PLUGIN_CONTROL, command(), REQUEST_ID, "oauth")
    ]

    client.reply = plan().model_copy(
        update={
            "command": command().model_copy(update={"scope_id": "workspace-other"})
        }
    )
    with pytest.raises(AdminDataError) as mismatch:
        data.plan(command(), REQUEST_ID, access_token="oauth")
    assert mismatch.value.code == "ADMIN_RESPONSE_INVALID"


def test_apply_recovers_only_the_original_committed_receipt():
    request = DeckPluginControlApplyInputDTO(plan=plan(), evidence=[])
    expected = operation()
    client = FakeClient(expected)
    client.execute_error = AdminDataError(
        "ADMIN_UPSTREAM_UNAVAILABLE", 503, REQUEST_ID, True
    )
    client.receipt_reply = CommittedReceiptDTO[DeckPluginControlOperationDTO](
        status="committed",
        operation=APPLY_DECK_PLUGIN_CONTROL.capability.name,
        request_id=REQUEST_ID,
        result=expected,
    )
    data = AdminDeckPluginControlData(client)

    assert data.apply(request, REQUEST_ID, access_token="oauth") == expected
    assert len(client.execute_calls) == 1
    assert client.receipt_calls == [
        (APPLY_DECK_PLUGIN_CONTROL, REQUEST_ID, "oauth")
    ]

    client.receipt_reply = None
    with pytest.raises(AdminDataError) as unknown:
        data.apply(request, REQUEST_ID, access_token="oauth")
    assert unknown.value.code == "ADMIN_WRITE_RESULT_UNKNOWN"
    assert unknown.value.outcome_unknown
    assert len(client.execute_calls) == 2
