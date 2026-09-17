# [Sync] 2026-09-17: align provider-free fake clients with reusable validated capability snapshots.
# [Input] Registry122-132 binding/launch DTO consumer, fake Admin catalog and closed receipt/error outcomes.
# [Output] Exact hashes, current/replay identity binding, one-dispatch recovery and registration evidence.
# [Pos] Provider-free Dream data-boundary test; no PostgreSQL, filesystem or Runtime.
# [Sync] 2026-09-16: verify launch scope/current/replay DTOs and preparation receipt recovery.
from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from services.admin_data.config import AdminDataConfig
from services.admin_data.deck_plugin_binding_data import (
    AdminDeckPluginBindingData,
    AgentTypeRuntimePrepareInputDTO,
    AgentTypeRuntimePreparedDTO,
    AgentTypeVerifiedPluginDTO,
    BindingClearInputDTO,
    BindingHistoryInputDTO,
    BindingSaveInputDTO,
    BindingScopeInputDTO,
    BindingSelectionInputDTO,
    BindingStateDTO,
    BindingResponseDTO,
    DreamLaunchRuntimeBindingDTO,
    DreamLaunchRuntimePlanDTO,
    DreamLaunchRuntimePlanInputDTO,
    DreamLaunchRuntimePrepareInputDTO,
    DreamLaunchRuntimePreparedDTO,
    DreamLaunchRuntimeScopeInputDTO,
    AUTHORIZE_DREAM_LAUNCH_RUNTIME,
    CLEAR_BINDING,
    DECK_PLUGIN_BINDING_OPERATIONS,
    LIST_BINDING_OPTIONS,
    PLAN_AGENT_TYPE_RUNTIME,
    PREPARE_AGENT_TYPE_RUNTIME,
    PLAN_DREAM_LAUNCH_RUNTIME,
    PREPARE_DREAM_LAUNCH_RUNTIME,
    READ_BINDING,
    READ_BINDING_HISTORY,
    SAVE_BINDING,
    VALIDATE_BINDING,
)
from services.admin_data.errors import AdminDataError
from services.admin_data.models import (
    AbsentReceiptDTO,
    BindingRevisionConflictDetailsDTO,
    BindingSelectionRejectedDetailsDTO,
    CommittedReceiptDTO,
    ErrorDTO,
)
from services.admin_data.request_auth import AdminRequestAuth
from services.admin_data.workflow_data import WORKFLOW_SCHEMA_REQUIREMENTS


DECK_ID = "deck-1"
WORKSPACE_ID = "workspace-1"
PLUGIN_ID = "example.story"
VERSION = "1.0.0"
REQUEST_ID = "binding-request"


def scope() -> BindingScopeInputDTO:
    return BindingScopeInputDTO(deck_id=DECK_ID, workspace_id=WORKSPACE_ID)


def selection() -> BindingSelectionInputDTO:
    return BindingSelectionInputDTO(
        **scope().model_dump(),
        deck_plugin_id=PLUGIN_ID,
        deck_plugin_version=VERSION,
        apply_to="next_run",
    )


def saved(**updates) -> BindingResponseDTO:
    return BindingResponseDTO.model_validate({
        "deck_plugin_binding_id": "dpb_" + "a" * 32,
        "deck_id": DECK_ID,
        "deck_plugin_id": PLUGIN_ID,
        "deck_plugin_version": VERSION,
        "binding_revision": 1,
        "status": "active",
        "applied_to": "next_run",
        "selection_validation_summary": {
            "selectable": True,
            "release_status": "published",
            "installation_status": "ready",
            "compatibility": "passed",
            "runtime_readiness": "materialized",
            "reason_code": None,
            "recovery": None,
            "capability_summary": [],
        },
        **updates,
    })


class FakeClient:
    def __init__(self, reply) -> None:
        self.reply = reply
        self.execute_error: AdminDataError | None = None
        self.receipt_reply = None
        self.execute_calls = []
        self.receipt_calls = []

    def capabilities_snapshot(self, request_id):
        return SimpleNamespace(schema_capabilities=list(WORKFLOW_SCHEMA_REQUIREMENTS))

    def execute(self, operation, input_dto, request_id, *, access_token):
        self.execute_calls.append((operation, input_dto, request_id, access_token))
        if self.execute_error is not None:
            raise self.execute_error
        return self.reply

    def receipt(self, operation, request_id, *, access_token):
        self.receipt_calls.append((operation, request_id, access_token))
        return self.receipt_reply or AbsentReceiptDTO(
            status="absent",
            operation=operation.capability.name,
            request_id=request_id,
        )


def test_registry122_132_hashes_and_actor_free_inputs_are_exact():
    assert [item.capability.name for item in DECK_PLUGIN_BINDING_OPERATIONS] == [
        "deck-plugin-binding.current",
        "deck-plugin-binding.history",
        "deck-plugin-binding.options",
        "deck-plugin-binding.validate",
        "deck-plugin-binding.save",
        "deck-plugin-binding.clear",
        "deck-agent-type.runtime-plan",
        "deck-agent-type.runtime-prepare",
        "dream-launch.runtime-scope",
        "dream-launch.runtime-plan",
        "dream-launch.runtime-prepare",
    ]
    assert [item.capability.contract_sha256 for item in DECK_PLUGIN_BINDING_OPERATIONS] == [
        "4b66af7888ed17e16f7e7aa38aded821ad3ecfe148663001dd6c4a66c714fb93",
        "568bb2ad097382510919eb230e20b1e7d5e6e2dfd9c66c83384cbf3e52ede0e8",
        "aca3a55ce01d9e7754d5cd9be07320cb4240d3d26928c8ff24ba3ea9675fa770",
        "55fc0175170183fc1d5fc5162ef6be15bb863ef43261902c8edda5614bbcdb70",
        "cf91b567af3ae207d0c009947d98fb0dcb2335d3abcbf7e8194f95a02ceeddb2",
        "9a89ec380e280fc64b67b9725a68edf3244df0f76e41df8db5fd89b3e3fd44fc",
        "87a3f0497e3927aa8c8048e6bc79de1b042631f096f85184568201dce378e5f7",
        "9cc1a08d15e0279ed977bb5b7ee25a5ab270cf32a4f67ded719c23e33d000716",
        "67dbe0a6eb7ddfd9bd1fa668e38f143add53201b725b19506af976319bba2b92",
        "efd986cef6f891202c4d3ceb889d7491e8227dc097eeb009202a2be92549e9a6",
        "d9c2faeb03b86cf562286f283e5bfcd3098e1da81c1b628c2e9aaa5a7b897882",
    ]
    with pytest.raises(ValidationError):
        BindingScopeInputDTO.model_validate({
            **scope().model_dump(),
            "actor_id": "42",
        })

    for invalid in (
        {"mode": "current", "workflow_run_id": "run_" + "1" * 32, "thread_id": "thread"},
        {"mode": "replay", "workflow_run_id": None, "thread_id": None},
        {"mode": "replay", "workflow_run_id": "run_" + "1" * 32, "thread_id": None},
    ):
        with pytest.raises(ValidationError):
            DreamLaunchRuntimePlanInputDTO.model_validate({
                **scope().model_dump(), "agent_id": None, **invalid,
            })
    with pytest.raises(ValidationError):
        BindingSelectionInputDTO.model_validate({
            **selection().model_dump(),
            "ready": True,
        })
    with pytest.raises(ValidationError):
        AgentTypeRuntimePrepareInputDTO.model_validate({
            **scope().model_dump(),
            "expected_binding_revision": 0,
            "verified_plugin": {
                "plugin_installation_id": "cpi_example",
                "package_spec": "example.runtime",
                "resolved_version": VERSION,
                "artifact_digest": "sha256:" + "a" * 64,
                "has_manifest": True,
                "artifact_path": "/caller/path",
            },
        })


def test_reads_bind_deck_and_selection_identity_to_the_original_input():
    valid = BindingStateDTO(
        deck_id=DECK_ID,
        binding_revision=0,
        applied_to="next_run",
        binding=None,
    )
    client = FakeClient(valid)
    data = AdminDeckPluginBindingData(client)
    assert data.current(scope(), REQUEST_ID, access_token="oauth") is valid
    assert client.execute_calls == [(READ_BINDING, scope(), REQUEST_ID, "oauth")]

    client.reply = valid.model_copy(update={"deck_id": "deck-other"})
    with pytest.raises(AdminDataError) as mismatch:
        data.current(scope(), REQUEST_ID, access_token="oauth")
    assert mismatch.value.code == "ADMIN_RESPONSE_INVALID"
    assert not mismatch.value.outcome_unknown


def test_history_uses_strict_limit_and_selection_mismatch_fails_closed():
    with pytest.raises(ValidationError):
        BindingHistoryInputDTO(**scope().model_dump(), limit=101)
    client = FakeClient(SimpleNamespace(
        deck_id=DECK_ID,
        deck_plugin_id="other.plugin",
        deck_plugin_version=VERSION,
        applied_to="next_run",
    ))
    data = AdminDeckPluginBindingData(client)
    with pytest.raises(AdminDataError) as mismatch:
        data.validate(selection(), REQUEST_ID, access_token="oauth")
    assert mismatch.value.code == "ADMIN_RESPONSE_INVALID"
    assert client.execute_calls[0][0] is VALIDATE_BINDING


def test_unknown_save_reads_only_the_original_receipt_and_never_resends():
    command = BindingSaveInputDTO(
        **selection().model_dump(),
        expected_binding_revision=0,
    )
    client = FakeClient(saved())
    client.execute_error = AdminDataError(
        "ADMIN_TIMEOUT", 504, REQUEST_ID, True
    )
    client.receipt_reply = CommittedReceiptDTO[BindingResponseDTO](
        status="committed",
        operation=SAVE_BINDING.capability.name,
        request_id=REQUEST_ID,
        result=saved(),
    )
    data = AdminDeckPluginBindingData(client)
    assert data.save(command, REQUEST_ID, access_token="oauth") == saved()
    assert len(client.execute_calls) == 1
    assert client.receipt_calls == [(SAVE_BINDING, REQUEST_ID, "oauth")]


def test_absent_or_mismatched_save_receipt_remains_unknown():
    command = BindingSaveInputDTO(
        **selection().model_dump(),
        expected_binding_revision=0,
    )
    client = FakeClient(saved())
    client.execute_error = AdminDataError(
        "ADMIN_UNAVAILABLE", 503, REQUEST_ID, True
    )
    data = AdminDeckPluginBindingData(client)
    with pytest.raises(AdminDataError) as absent:
        data.save(command, REQUEST_ID, access_token="oauth")
    assert absent.value.code == "ADMIN_WRITE_RESULT_UNKNOWN"
    assert absent.value.outcome_unknown

    client.receipt_reply = CommittedReceiptDTO[BindingResponseDTO](
        status="committed",
        operation=SAVE_BINDING.capability.name,
        request_id=REQUEST_ID,
        result=saved(deck_id="deck-other"),
    )
    with pytest.raises(AdminDataError) as mismatched:
        data.save(command, REQUEST_ID, access_token="oauth")
    assert mismatched.value.code == "ADMIN_RESPONSE_INVALID"
    assert mismatched.value.outcome_unknown


def test_unknown_runtime_prepare_reads_only_its_original_receipt():
    evidence = AgentTypeVerifiedPluginDTO(
        plugin_installation_id="cpi_" + "a" * 32,
        package_spec="example.runtime",
        resolved_version=VERSION,
        artifact_digest="sha256:" + "b" * 64,
        has_manifest=True,
    )
    command = AgentTypeRuntimePrepareInputDTO(
        **scope().model_dump(),
        expected_binding_revision=0,
        verified_plugin=evidence,
    )
    prepared = AgentTypeRuntimePreparedDTO(
        deck_id=DECK_ID,
        deck_plugin_id=PLUGIN_ID,
        deck_plugin_version=VERSION,
        current_binding_revision=0,
        runtime_ready=True,
    )
    client = FakeClient(prepared)
    client.execute_error = AdminDataError(
        "ADMIN_TIMEOUT", 504, REQUEST_ID, True
    )
    client.receipt_reply = CommittedReceiptDTO[AgentTypeRuntimePreparedDTO](
        status="committed",
        operation=PREPARE_AGENT_TYPE_RUNTIME.capability.name,
        request_id=REQUEST_ID,
        result=prepared,
    )
    data = AdminDeckPluginBindingData(client)
    assert data.runtime_prepare(
        command, REQUEST_ID, access_token="oauth"
    ) == prepared
    assert len(client.execute_calls) == 1
    assert client.receipt_calls == [
        (PREPARE_AGENT_TYPE_RUNTIME, REQUEST_ID, "oauth")
    ]


def test_launch_plan_binds_mode_scope_and_frozen_run_identity():
    run_id = "run_" + "c" * 32
    binding = DreamLaunchRuntimeBindingDTO(
        deck_plugin_binding_id="dpb_" + "d" * 32,
        deck_plugin_id=PLUGIN_ID,
        deck_plugin_version=VERSION,
        binding_revision=3,
    )
    target = {
        "deck_plugin_id": PLUGIN_ID,
        "deck_plugin_version": VERSION,
        "runtime_plugin_lock_id": "rpl_" + "e" * 32,
        "plugin_installation_id": "cpi_" + "f" * 32,
        "package_spec": "example.runtime",
        "package_name": "runtime",
        "marketplace": "platform-builtin",
        "resolved_version": VERSION,
        "artifact_digest": "sha256:" + "a" * 64,
        "compatibility_json": "{}",
    }
    command = DreamLaunchRuntimePlanInputDTO(
        **scope().model_dump(), agent_id=None, mode="replay",
        workflow_run_id=run_id, thread_id="thread-replay",
    )
    result = DreamLaunchRuntimePlanDTO(
        **command.model_dump(), binding=binding, target=target,
    )
    client = FakeClient(result)
    data = AdminDeckPluginBindingData(client)
    assert data.launch_runtime_plan(command, REQUEST_ID, access_token="oauth") is result
    assert client.execute_calls == [(PLAN_DREAM_LAUNCH_RUNTIME, command, REQUEST_ID, "oauth")]

    client.reply = result.model_copy(update={"thread_id": "thread-other"})
    with pytest.raises(AdminDataError) as mismatch:
        data.launch_runtime_plan(command, REQUEST_ID, access_token="oauth")
    assert mismatch.value.code == "ADMIN_RESPONSE_INVALID"


def test_unknown_launch_prepare_recovers_only_its_exact_receipt():
    binding = DreamLaunchRuntimeBindingDTO(
        deck_plugin_binding_id="dpb_" + "b" * 32,
        deck_plugin_id=PLUGIN_ID,
        deck_plugin_version=VERSION,
        binding_revision=2,
    )
    evidence = AgentTypeVerifiedPluginDTO(
        plugin_installation_id="cpi_" + "a" * 32,
        package_spec="example.runtime",
        resolved_version=VERSION,
        artifact_digest="sha256:" + "b" * 64,
        has_manifest=True,
    )
    command = DreamLaunchRuntimePrepareInputDTO(
        **scope().model_dump(), agent_id=None, mode="current",
        workflow_run_id=None, thread_id=None, expected_binding_revision=2,
        verified_plugin=evidence,
    )
    prepared = DreamLaunchRuntimePreparedDTO(
        **command.model_dump(exclude={"expected_binding_revision", "verified_plugin"}),
        binding=binding,
        runtime_ready=True,
    )
    client = FakeClient(prepared)
    client.execute_error = AdminDataError("ADMIN_TIMEOUT", 504, REQUEST_ID, True)
    client.receipt_reply = CommittedReceiptDTO[DreamLaunchRuntimePreparedDTO](
        status="committed", operation=PREPARE_DREAM_LAUNCH_RUNTIME.capability.name,
        request_id=REQUEST_ID, result=prepared,
    )
    data = AdminDeckPluginBindingData(client)
    assert data.launch_runtime_prepare(command, REQUEST_ID, access_token="oauth") == prepared
    assert client.receipt_calls == [(PREPARE_DREAM_LAUNCH_RUNTIME, REQUEST_ID, "oauth")]


def test_error_details_are_owned_by_their_codes():
    conflict = ErrorDTO.model_validate({
        "code": "BINDING_REVISION_CONFLICT",
        "message": "closed",
        "details": {"current_revision": 2},
    })
    assert isinstance(conflict.details, BindingRevisionConflictDetailsDTO)
    rejected = ErrorDTO.model_validate({
        "code": "SELECTION_NOT_ALLOWED",
        "message": "closed",
        "details": {
            "validation": {
                "selectable": False,
                "release_status": "published",
                "installation_status": "disabled",
                "compatibility": "failed",
                "runtime_readiness": "unknown",
                "reason_code": "DECK_PLUGIN_DISABLED",
                "recovery": {
                    "owner": "deck_plugin_admin",
                    "action": "enable_the_installation",
                },
                "capability_summary": [],
            }
        },
    })
    assert isinstance(rejected.details, BindingSelectionRejectedDetailsDTO)
    with pytest.raises(ValidationError):
        ErrorDTO.model_validate({
            "code": "OTHER_ERROR",
            "message": "closed",
            "details": {"current_revision": 2},
        })


def test_production_request_owner_registers_all_eleven_operations():
    config = AdminDataConfig(
        base_url="https://admin.example",
        issuer="https://admin.example/api/auth",
        resource="https://dream.example/api",
        service_client_id="dream-service",
        service_secret="s" * 32,
    )
    owner = AdminRequestAuth(config)
    try:
        for operation in DECK_PLUGIN_BINDING_OPERATIONS:
            assert owner.client._operations[operation.capability.name] is operation
    finally:
        owner.close()


def test_eleven_operation_kinds_match_read_and_write_scope():
    assert {
        READ_BINDING.capability.kind,
        READ_BINDING_HISTORY.capability.kind,
        LIST_BINDING_OPTIONS.capability.kind,
        VALIDATE_BINDING.capability.kind,
        PLAN_AGENT_TYPE_RUNTIME.capability.kind,
        AUTHORIZE_DREAM_LAUNCH_RUNTIME.capability.kind,
        PLAN_DREAM_LAUNCH_RUNTIME.capability.kind,
    } == {"read"}
    for operation in (
        SAVE_BINDING,
        CLEAR_BINDING,
        PREPARE_AGENT_TYPE_RUNTIME,
        PREPARE_DREAM_LAUNCH_RUNTIME,
    ):
        assert operation.capability.kind == "write"
        assert operation.capability.user_scope == "dream:write"
