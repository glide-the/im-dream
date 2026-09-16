# [Input] Registry175-182 strict DTOs, exact capabilities and synthetic Admin receipts.
# [Output] Actor-free commands, contract pins, response binding and unknown-write recovery evidence.
# [Pos] Provider-free Dream consumer contract; no PostgreSQL, filesystem, CLI or user service.
# [Sync] 2026-09-16: replace the retired Dream Marketplace SQL service test with Admin DTO coverage.
from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from services.admin_data.claude_plugin_data import (
    CLAUDE_PLUGIN_OPERATIONS,
    CLAUDE_PLUGIN_SCHEMA_REQUIREMENTS,
    PREPARE_CLAUDE_PLUGIN_INSTALL,
    REPORT_CLAUDE_PLUGIN_INSTALL,
    AdminClaudePluginData,
    ClaudePluginInstallPlanDTO,
    ClaudePluginInstallPrepareInputDTO,
    ClaudePluginInstallReportInputDTO,
    ClaudePluginOperationDTO,
)
from services.admin_data.config import AdminDataConfig
from services.admin_data.errors import AdminDataError
from services.admin_data.models import AbsentReceiptDTO, CommittedReceiptDTO
from services.admin_data.request_auth import AdminRequestAuth


REQUEST_ID = "claude-plugin-request"
OPERATION_ID = "cop_operation"
PACKAGE_SPEC = "demo@market"
NOW = datetime(2026, 9, 16, tzinfo=UTC)


def operation(**changes) -> ClaudePluginOperationDTO:
    values = {
        "id": OPERATION_ID,
        "operation_kind": "install",
        "requested_package_spec": PACKAGE_SPEC,
        "marketplace_entry_id": None,
        "status": "running",
        "phase": "starting",
        "progress": 5,
        "message": "Install execution started",
        "executable": None,
        "argv_json": None,
        "cwd": None,
        "cli_version": None,
        "exit_code": None,
        "evidence_path": None,
        "installation_id": None,
        "error_code": None,
        "error_summary": None,
        "created_at": NOW,
        "updated_at": NOW,
        "finished_at": None,
    }
    values.update(changes)
    return ClaudePluginOperationDTO.model_validate(values)


def plan(**changes) -> ClaudePluginInstallPlanDTO:
    values = {
        "accepted": True,
        "operation_id": OPERATION_ID,
        "package_spec": PACKAGE_SPEC,
        "marketplace_entry_id": None,
        "requested_source_type": "marketplace",
        "marketplace_source": None,
    }
    values.update(changes)
    return ClaudePluginInstallPlanDTO.model_validate(values)


class FakeClient:
    def __init__(self, reply) -> None:
        self.reply = reply
        self.execute_error: AdminDataError | None = None
        self.receipt_reply = None
        self.execute_calls = []
        self.receipt_calls = []
        self.schemas = list(CLAUDE_PLUGIN_SCHEMA_REQUIREMENTS)

    def capabilities(self, request_id):
        return SimpleNamespace(schema_capabilities=self.schemas)

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


def test_registry175_182_hashes_and_request_owner_registration_are_exact():
    assert [item.capability.name for item in CLAUDE_PLUGIN_OPERATIONS] == [
        "claude-plugin.installations.list",
        "claude-plugin.marketplace.list",
        "claude-plugin.install.prepare",
        "claude-plugin.operations.list",
        "claude-plugin.operation.read",
        "claude-plugin.installation.read",
        "claude-plugin.install.report",
        "claude-plugin.installation.uninstall",
    ]
    assert [
        item.capability.contract_sha256 for item in CLAUDE_PLUGIN_OPERATIONS
    ] == [
        "9795d0b9465050b0d9032be3b227a32a70a6a4fca50742e5921006d5b408deeb",
        "b7c05e5e460f36b5f8d8d03d3c595f405d58bf7f862f10e316b6e4b152cdd8bf",
        "02e01bdd5681e2f62eda62ea65e879f693fc72ebbf0f299fca47998e88601fad",
        "3a27f57269a9fb4da02526aaed41655850c53c264bcca49e669c76e6c37663ae",
        "edf3e075cb100ebe56ccd86703f80d08e9c7be952bca48e585484a29516b14b5",
        "690ae2a07b92258c11e36843cac1024f248aa8204410e39a4a2895bc07a8d620",
        "661e28352ec56257282f914091a6b33bc435d1dcdd4c1c7cf44482f2c16b7504",
        "904b5e2796ac17378facb4b3e8d2afb9e4e9cd72dc79a57dbd0cd74b3947d2a3",
    ]
    config = AdminDataConfig(
        base_url="https://admin.example.test",
        issuer="https://admin.example.test/api/auth",
        resource="https://dream.example.test/api",
        service_client_id="dream-service",
        service_secret="s" * 32,
    )
    owner = AdminRequestAuth(config)
    try:
        for item in CLAUDE_PLUGIN_OPERATIONS:
            assert owner.client._operations[item.capability.name] is item
    finally:
        owner.close()


@pytest.mark.parametrize(
    "payload",
    [
        {"source_kind": "package", "package_spec": PACKAGE_SPEC},
        {
            "source_kind": "package",
            "package_spec": PACKAGE_SPEC,
            "source_type": None,
            "actor_id": "42",
        },
        {
            "source_kind": "marketplace_entry",
            "marketplace_entry_id": "cpme_demo",
            "user_id": "42",
        },
        {
            "source_kind": "marketplace_entry",
            "marketplace_entry_id": "cpme_demo",
            "sql": "select 1",
        },
    ],
)
def test_prepare_input_has_one_closed_source_shape(payload):
    with pytest.raises(ValidationError):
        ClaudePluginInstallPrepareInputDTO.model_validate(payload)


@pytest.mark.parametrize(
    "payload",
    [
        {"event": "begin", "operation_id": OPERATION_ID, "phase": "verify"},
        {
            "event": "progress",
            "operation_id": OPERATION_ID,
            "phase": "verify",
            "progress": 20,
            "message": "wrong progress",
        },
        {
            "event": "fail",
            "operation_id": OPERATION_ID,
            "error_code": "CLAUDE_PLUGIN_INSTALL_FAILED",
            "error_summary": "failed",
        },
        {
            "event": "complete",
            "operation_id": OPERATION_ID,
            "installation": None,
            "evidence_path": "/evidence.json",
        },
    ],
)
def test_report_input_has_one_closed_lifecycle_shape(payload):
    with pytest.raises(ValidationError):
        ClaudePluginInstallReportInputDTO.model_validate(payload)


def test_prepare_binds_marketplace_entry_and_rejects_reply_substitution():
    request = ClaudePluginInstallPrepareInputDTO(
        source_kind="marketplace_entry", marketplace_entry_id="cpme_demo"
    )
    expected = plan(
        marketplace_entry_id="cpme_demo", requested_source_type="marketplace"
    )
    client = FakeClient(expected)
    data = AdminClaudePluginData(client)
    assert data.prepare(request, REQUEST_ID, access_token="oauth") == expected
    assert client.execute_calls == [
        (PREPARE_CLAUDE_PLUGIN_INSTALL, request, REQUEST_ID, "oauth")
    ]

    client.reply = expected.model_copy(
        update={"marketplace_entry_id": "cpme_other"}
    )
    with pytest.raises(AdminDataError) as mismatch:
        data.prepare(request, REQUEST_ID, access_token="oauth")
    assert mismatch.value.code == "ADMIN_WRITE_RESULT_UNKNOWN"
    assert mismatch.value.outcome_unknown


def test_report_recovers_only_the_original_committed_receipt():
    request = ClaudePluginInstallReportInputDTO(
        event="begin", operation_id=OPERATION_ID
    )
    expected = operation()
    client = FakeClient(expected)
    client.execute_error = AdminDataError(
        "ADMIN_UPSTREAM_UNAVAILABLE", 503, REQUEST_ID, True
    )
    client.receipt_reply = CommittedReceiptDTO[ClaudePluginOperationDTO](
        status="committed",
        operation=REPORT_CLAUDE_PLUGIN_INSTALL.capability.name,
        request_id=REQUEST_ID,
        result=expected,
    )
    data = AdminClaudePluginData(client)

    assert data.report(request, REQUEST_ID, access_token="oauth") == expected
    assert len(client.execute_calls) == 1
    assert client.receipt_calls == [
        (REPORT_CLAUDE_PLUGIN_INSTALL, REQUEST_ID, "oauth")
    ]

    client.receipt_reply = None
    with pytest.raises(AdminDataError) as unknown:
        data.report(request, REQUEST_ID, access_token="oauth")
    assert unknown.value.code == "ADMIN_WRITE_RESULT_UNKNOWN"
    assert unknown.value.outcome_unknown
    assert len(client.execute_calls) == 2


@pytest.mark.parametrize("damage", ["missing", "hash", "duplicate"])
def test_exact_schema_capabilities_are_required_before_dispatch(damage):
    client = FakeClient(operation())
    if damage == "missing":
        client.schemas.pop()
    elif damage == "hash":
        client.schemas[-1] = client.schemas[-1].model_copy(
            update={"contract_sha256": "b" * 64}
        )
    else:
        client.schemas.append(client.schemas[-1])
    data = AdminClaudePluginData(client)

    with pytest.raises(AdminDataError) as unavailable:
        data.report(
            ClaudePluginInstallReportInputDTO(
                event="begin", operation_id=OPERATION_ID
            ),
            REQUEST_ID,
            access_token="oauth",
        )
    assert unavailable.value.code == "ADMIN_CAPABILITY_UNAVAILABLE"
    assert not client.execute_calls
