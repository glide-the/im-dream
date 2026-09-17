# [Sync] 2026-09-17: align provider-free fake clients with reusable validated capability snapshots.
# [Input] Registry175-184 strict DTOs, exact capabilities and synthetic Admin receipts.
# [Output] Actor/Deck-free commands, user/service contract pins and unknown-write recovery evidence.
# [Pos] Provider-free Dream consumer contract; no PostgreSQL, filesystem, CLI or user service.
# [Sync] 2026-09-16: add service-only builtin coordination without a PostgreSQL fallback.
from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from services.admin_data.claude_plugin_data import (
    CLAUDE_PLUGIN_OPERATIONS,
    CLAUDE_PLUGIN_SCHEMA_REQUIREMENTS,
    ENSURE_BUILTIN_CLAUDE_PLUGIN,
    PREPARE_CLAUDE_PLUGIN_INSTALL,
    REPORT_BUILTIN_CLAUDE_PLUGIN,
    REPORT_CLAUDE_PLUGIN_INSTALL,
    AdminClaudePluginData,
    AdminClaudePluginBuiltinData,
    ClaudePluginBuiltinEnsureInputDTO,
    ClaudePluginBuiltinEnsureOutputDTO,
    ClaudePluginBuiltinReportOutputDTO,
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

    def capabilities_snapshot(self, request_id):
        return SimpleNamespace(schema_capabilities=self.schemas)

    def execute(
        self, operation_value, input_dto, request_id, *, access_token=None
    ):
        self.execute_calls.append(
            (operation_value, input_dto, request_id, access_token)
        )
        if self.execute_error is not None:
            raise self.execute_error
        return self.reply

    def receipt(self, operation_value, request_id, *, access_token=None):
        self.receipt_calls.append((operation_value, request_id, access_token))
        return self.receipt_reply or AbsentReceiptDTO(
            status="absent",
            operation=operation_value.capability.name,
            request_id=request_id,
        )


def test_registry175_184_hashes_and_request_owner_registration_are_exact():
    assert [item.capability.name for item in CLAUDE_PLUGIN_OPERATIONS] == [
        "claude-plugin.installations.list",
        "claude-plugin.marketplace.list",
        "claude-plugin.install.prepare",
        "claude-plugin.operations.list",
        "claude-plugin.operation.read",
        "claude-plugin.installation.read",
        "claude-plugin.install.report",
        "claude-plugin.installation.uninstall",
        "claude-plugin.builtin.ensure",
        "claude-plugin.builtin.report",
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
        "74220704d8852909375ea70015af93b04bfb894e8e11a345ad2d8ef91539b5cf",
        "77d2c856d3712d4861caff95553db35676539768c82e58d5ab3a29a1dc916aea",
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
    assert ENSURE_BUILTIN_CLAUDE_PLUGIN.capability.user_scope is None
    assert REPORT_BUILTIN_CLAUDE_PLUGIN.capability.user_scope is None
    assert {
        ENSURE_BUILTIN_CLAUDE_PLUGIN.capability.background_scope,
        REPORT_BUILTIN_CLAUDE_PLUGIN.capability.background_scope,
    } == {"plugins:catalog"}


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


@pytest.mark.parametrize(
    "payload",
    [
        {"package_spec": "ink-dream-story@platform-builtin", "deck_id": "deck"},
        {"package_spec": "ink-dream-story@platform-builtin", "actor_id": "42"},
        {"package_spec": "ink-dream-story@platform-builtin", "sql": "select 1"},
    ],
)
def test_builtin_ensure_rejects_external_authority_and_query_selectors(payload):
    with pytest.raises(ValidationError):
        ClaudePluginBuiltinEnsureInputDTO.model_validate(payload)


def test_builtin_ensure_binds_ready_or_install_response_to_package_spec():
    request = ClaudePluginBuiltinEnsureInputDTO(
        package_spec="ink-dream-story@platform-builtin"
    )
    ready = ClaudePluginBuiltinEnsureOutputDTO(
        action="ready",
        package_spec=request.package_spec,
        installation_id="cpi_ready",
        refs_created=2,
    )
    client = FakeClient(ready)
    data = AdminClaudePluginBuiltinData(client)
    assert data.ensure(request, REQUEST_ID) == ready
    assert client.execute_calls == [
        (ENSURE_BUILTIN_CLAUDE_PLUGIN, request, REQUEST_ID, None)
    ]

    client.reply = ready.model_copy(update={"package_spec": "other@market"})
    with pytest.raises(AdminDataError) as mismatch:
        data.ensure(request, REQUEST_ID)
    assert mismatch.value.code == "ADMIN_WRITE_RESULT_UNKNOWN"
    assert mismatch.value.outcome_unknown


def test_builtin_report_recovers_original_service_receipt_without_oauth():
    request = ClaudePluginInstallReportInputDTO(
        event="begin", operation_id=OPERATION_ID
    )
    expected = ClaudePluginBuiltinReportOutputDTO(
        operation=operation(), refs_created=0
    )
    client = FakeClient(expected)
    client.execute_error = AdminDataError(
        "ADMIN_UPSTREAM_UNAVAILABLE", 503, REQUEST_ID, True
    )
    client.receipt_reply = CommittedReceiptDTO[
        ClaudePluginBuiltinReportOutputDTO
    ](
        status="committed",
        operation=REPORT_BUILTIN_CLAUDE_PLUGIN.capability.name,
        request_id=REQUEST_ID,
        result=expected,
    )
    data = AdminClaudePluginBuiltinData(client)

    assert data.report(request, REQUEST_ID) == expected
    assert client.execute_calls == [
        (REPORT_BUILTIN_CLAUDE_PLUGIN, request, REQUEST_ID, None)
    ]
    assert client.receipt_calls == [
        (REPORT_BUILTIN_CLAUDE_PLUGIN, REQUEST_ID, None)
    ]


@pytest.mark.parametrize(
    "payload",
    [
        {"action": "ready", "package_spec": "demo@market"},
        {"action": "install", "plan": plan(), "refs_created": 0},
    ],
)
def test_builtin_ensure_response_has_one_exact_action_shape(payload):
    with pytest.raises(ValidationError):
        ClaudePluginBuiltinEnsureOutputDTO.model_validate(payload)
