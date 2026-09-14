# [Input] Registered fail/envelope DTOs, actual shared client and original Run fixture data.
# [Output] Provider-free full reply, raw text, unknown-write and original receipt evidence.
# [Pos] Transport contract harness; no production launch wiring or normal model acceptance.
# [Sync] 2026-09-15: preserve two independent operations and historical failed replay.
from __future__ import annotations

import copy
import json

import httpx
import pytest
from pydantic import ValidationError

from services.admin_data.client import AdminDataClient
from services.admin_data.config import AdminDataConfig
from services.admin_data.errors import AdminDataError
from services.admin_data.launch_metadata_data import (
    AdminLaunchMetadataData, FAIL_LAUNCH_ENVELOPE, LaunchFailureExpectation,
    LaunchFailureInputDTO, LaunchFailureOutputDTO,
)
from services.admin_data.run_data import AdminRunData, FAIL_RUN, RunFailInputDTO
from services.admin_data.workflow_data import WORKFLOW_SCHEMA_REQUIREMENTS
from tests.test_admin_run_routes import RUN_ID, run

OPERATIONS = (FAIL_RUN, FAIL_LAUNCH_ENVELOPE)
REQUEST_ID = "failure-original-1"
WORKSPACE = "existing-workspace-1"
ERROR = " original\n错误\u0085 "


@pytest.fixture
def boundary(monkeypatch):
    import database
    monkeypatch.setattr(database, "get_db", lambda *_a, **_kw: pytest.fail("failure types must not open SQL"))
    config = AdminDataConfig(base_url="https://admin.example", issuer="https://admin.example/api/auth",
        resource="https://dream.example/api", service_client_id="dream-service", service_secret="s" * 32)
    schemas = [value.model_dump() for value in WORKFLOW_SCHEMA_REQUIREMENTS]
    advertised = [value.capability.model_dump() for value in OPERATIONS]
    calls = []
    state = {"results": {FAIL_RUN.capability.name: {"run": run("failed")},
        FAIL_LAUNCH_ENVELOPE.capability.name: {"updated": True, "workflow_run_id": RUN_ID,
            "thread_id": "original-thread", "message_id": "original-message", "error_code": ERROR}}, "receipt": None}
    def handler(request):
        rid = request.headers["x-request-id"]
        assert request.headers["x-ink-dream-service"] == config.service_client_id
        assert request.headers["x-ink-dream-credential"] == config.service_secret and "cookie" not in request.headers
        if request.url.path.endswith("/capabilities"):
            value = {"version": "1", "auth": {"issuer": config.issuer, "jwks_uri": config.jwks_uri,
                "resource": config.resource, "algorithm": "ES256", "clients": {"browser": "dream-browser", "device": "dream-device"},
                "scopes": ["dream:read", "dream:write"], "delegations": []}, "schema_capabilities": schemas, "operations": advertised}
        else:
            assert request.headers["authorization"] == "Bearer write-token"
            if "/receipts/" in request.url.path:
                assert request.method == "GET" and request.url.path.endswith("/" + rid)
                name = request.url.params["operation"]
                calls.append(("receipt", rid, name, None))
                value = state["receipt"]
            else:
                assert request.method == "POST"
                name = request.url.path.rsplit("/", 1)[-1]
                envelope = json.loads(request.content)
                assert set(envelope) == {"request_id", "input"} and envelope["request_id"] == rid
                calls.append(("execute", rid, name, envelope["input"]))
                value = state["results"][name]
            if isinstance(value, Exception): raise value
            if isinstance(value, tuple):
                status, code = value
                return httpx.Response(status, json={"request_id": rid, "error": {"code": code, "message": "private error/body/token"}})
        return httpx.Response(200, json={"request_id": rid, "data": value})
    http = httpx.Client(transport=httpx.MockTransport(handler))
    client = AdminDataClient(config, client=http, operations=OPERATIONS)
    yield AdminRunData(client, canonical_user_id="42"), AdminLaunchMetadataData(client, canonical_user_id="42"), state, calls, schemas, advertised
    http.close()


def failure_input():
    return RunFailInputDTO(workspace_id=WORKSPACE, workflow_run_id=RUN_ID,
        failed_step=" dream_agent_dispatch\n", error_code=ERROR, reason_code=" terminal\nreason ")


def envelope_input():
    return LaunchFailureInputDTO(workspace_id=WORKSPACE, workflow_run_id=RUN_ID, error_code=ERROR)


def execute(boundary, operation):
    runs, metadata, *_ = boundary
    if operation is FAIL_RUN:
        return runs.fail(failure_input(), REQUEST_ID, access_token="write-token")
    return metadata.execute(operation, envelope_input(), REQUEST_ID, access_token="write-token",
        source=LaunchFailureExpectation("original-thread", "original-message"))


def receipt(boundary, operation):
    runs, metadata, *_ = boundary
    if operation is FAIL_RUN:
        return runs.receipt(operation, failure_input(), REQUEST_ID, access_token="write-token")
    return metadata.receipt(operation, envelope_input(), REQUEST_ID, access_token="write-token",
        source=LaunchFailureExpectation("original-thread", "original-message"))


def test_full_failed_reply_preserves_historical_terminal_details_and_raw_wire(boundary):
    result = execute(boundary, FAIL_RUN)
    assert len(result) == 28 and result["status"] == "failed"
    assert result["failed_step"] == "original_step" and result["error_code"] == "original_failure"
    assert result["completed_at"] == "2026-09-14T00:00:00.123458Z"
    calls = boundary[3]
    assert calls == [("execute", REQUEST_ID, "workflow-run.fail", failure_input().model_dump())]
    assert calls[0][3]["error_code"] == ERROR and ERROR not in repr(failure_input())


@pytest.mark.parametrize("text", [" ", "\n", "a\u0000b", "界" * 1000, ERROR])
def test_failure_strings_keep_original_truthiness_without_trim_or_new_quota(text):
    value = RunFailInputDTO(workspace_id=WORKSPACE, workflow_run_id=RUN_ID, failed_step=text, error_code=text, reason_code=text)
    assert (value.failed_step, value.error_code, value.reason_code) == (text, text, text)
    assert LaunchFailureInputDTO(workspace_id=WORKSPACE, workflow_run_id=RUN_ID, error_code=text).error_code == text


@pytest.mark.parametrize("field", ["failed_step", "error_code", "reason_code"])
def test_fail_requires_each_original_failure_field(field):
    value = failure_input().model_dump()
    del value[field]
    with pytest.raises(ValidationError): RunFailInputDTO(**value)


@pytest.mark.parametrize("field", ["failed_step", "error_code"])
@pytest.mark.parametrize("value", ["", None, 1, True])
def test_required_failure_text_rejects_empty_or_nonstring(field, value):
    payload = failure_input().model_dump()
    payload[field] = value
    with pytest.raises(ValidationError): RunFailInputDTO(**payload)


def test_nullable_reason_is_explicit():
    value = failure_input().model_dump()
    value["reason_code"] = None
    assert RunFailInputDTO(**value).model_dump()["reason_code"] is None


@pytest.mark.parametrize("field", ["actor_id", "source_message_id", "status", "metadata", "context", "codec_path"])
def test_both_inputs_reject_caller_authority_or_metadata(field):
    for dto, value in [(RunFailInputDTO, failure_input().model_dump()), (LaunchFailureInputDTO, envelope_input().model_dump())]:
        with pytest.raises(ValidationError): dto(**{**value, field: "private"})


@pytest.mark.parametrize("patch", [{"created_by": "43"}, {"workspace_id": "other"}, {"workflow_run_id": "run_" + "2" * 32},
    {"status": "cancelled"}, {"failed_step": None}, {"error_code": None}, {"status_version": False},
    {"completed_at": "2026-09-14T00:00:00.1234587Z"}, {"extra": "private"}])
def test_fail_reply_mismatch_keeps_original_uuid_unknown_without_retry(boundary, patch):
    boundary[2]["results"]["workflow-run.fail"]["run"].update(patch)
    with pytest.raises(AdminDataError) as error: execute(boundary, FAIL_RUN)
    assert (error.value.code, error.value.request_id, error.value.outcome_unknown) == ("ADMIN_RESPONSE_INVALID", REQUEST_ID, True)
    assert len(boundary[3]) == 1


@pytest.mark.parametrize("updated,thread,message", [(True, "  legacy\n", "\u0000原"), (True, "", ""),
    (False, None, None), (False, "original-thread", "original-message"), (False, None, "original-message")])
def test_envelope_preserves_raw_nullable_source_and_false_completion(boundary, updated, thread, message):
    boundary[2]["results"]["dream-launch-failure.envelope"].update(updated=updated, thread_id=thread, message_id=message)
    metadata = boundary[1]
    result = metadata.execute(FAIL_LAUNCH_ENVELOPE, envelope_input(), REQUEST_ID, access_token="write-token",
        source=LaunchFailureExpectation(thread, message))
    assert result.model_dump() == {"updated": updated, "workflow_run_id": RUN_ID, "thread_id": thread, "message_id": message, "error_code": ERROR}
    assert boundary[3] == [("execute", REQUEST_ID, "dream-launch-failure.envelope", envelope_input().model_dump())]


@pytest.mark.parametrize("patch", [{"workflow_run_id": "run_" + "2" * 32}, {"thread_id": "other"}, {"message_id": "other"},
    {"error_code": ERROR.strip()}, {"updated": 1}, {"extra": "private"}, {"message_id": None}])
def test_envelope_reply_mismatch_is_unknown_without_retry(boundary, patch):
    boundary[2]["results"]["dream-launch-failure.envelope"].update(patch)
    with pytest.raises(AdminDataError) as error: execute(boundary, FAIL_LAUNCH_ENVELOPE)
    assert (error.value.code, error.value.request_id, error.value.outcome_unknown) == ("ADMIN_RESPONSE_INVALID", REQUEST_ID, True)
    assert len(boundary[3]) == 1


@pytest.mark.parametrize("field", ["updated", "workflow_run_id", "thread_id", "message_id", "error_code"])
def test_envelope_requires_all_five_reply_fields(field):
    value = {"updated": False, "workflow_run_id": RUN_ID, "thread_id": None, "message_id": None, "error_code": ERROR}
    del value[field]
    with pytest.raises(ValidationError): LaunchFailureOutputDTO(**value)


@pytest.mark.parametrize("operation", OPERATIONS, ids=lambda value: value.capability.name)
@pytest.mark.parametrize("error", [(401, "TOKEN_INVALID"), (403, "DELEGATION_ENTITY_DENIED"), (404, "WORKFLOW_RUN_NOT_FOUND"),
    (409, "ILLEGAL_RUN_TRANSITION"), (409, "DREAM_LAUNCH_FAILURE_NOT_READY"), (503, "DREAM_DATA_SCHEMA_NOT_READY")])
def test_operation_errors_preserve_status_and_redact_upstream_text(boundary, operation, error):
    boundary[2]["results"][operation.capability.name] = error
    with pytest.raises(AdminDataError) as result: execute(boundary, operation)
    assert (result.value.status_code, result.value.code, result.value.request_id) == (*error, REQUEST_ID)
    assert "private" not in str(result.value) and len(boundary[3]) == 1


@pytest.mark.parametrize("operation", OPERATIONS, ids=lambda value: value.capability.name)
@pytest.mark.parametrize("status", ["absent", "committed"])
def test_unknown_operation_recovers_only_original_receipt_without_resend(boundary, operation, status):
    original = copy.deepcopy(boundary[2]["results"][operation.capability.name])
    boundary[2]["results"][operation.capability.name] = httpx.ReadTimeout("private token")
    with pytest.raises(AdminDataError) as error: execute(boundary, operation)
    assert error.value.request_id == REQUEST_ID and error.value.outcome_unknown
    result = {"status": status, "operation": operation.capability.name, "request_id": REQUEST_ID}
    if status == "committed": result["result"] = original
    boundary[2]["receipt"] = result
    recovered = receipt(boundary, operation)
    assert recovered.status == status
    assert boundary[3] == [("execute", REQUEST_ID, operation.capability.name,
        failure_input().model_dump() if operation is FAIL_RUN else envelope_input().model_dump()),
        ("receipt", REQUEST_ID, operation.capability.name, None)]


@pytest.mark.parametrize("operation", OPERATIONS, ids=lambda value: value.capability.name)
def test_committed_receipt_rechecks_historical_reply_binding(boundary, operation):
    result = copy.deepcopy(boundary[2]["results"][operation.capability.name])
    if operation is FAIL_RUN: result["run"]["created_by"] = "43"
    else: result["message_id"] = "other"
    boundary[2]["receipt"] = {"status": "committed", "operation": operation.capability.name, "request_id": REQUEST_ID, "result": result}
    with pytest.raises(AdminDataError) as error: receipt(boundary, operation)
    assert error.value.code == "ADMIN_RESPONSE_INVALID" and len(boundary[3]) == 1


@pytest.mark.parametrize("operation", OPERATIONS, ids=lambda value: value.capability.name)
@pytest.mark.parametrize("drift", ["identity", "unified", "operation", "hash"])
def test_exact_capabilities_fail_before_domain_io(boundary, operation, drift):
    if drift in {"identity", "unified"}: boundary[4][0 if drift == "identity" else 1]["contract_sha256"] = "0" * 64
    elif drift == "operation": boundary[5][:] = [value for value in boundary[5] if value["name"] != operation.capability.name]
    else: next(value for value in boundary[5] if value["name"] == operation.capability.name)["contract_sha256"] = "0" * 64
    with pytest.raises(AdminDataError): execute(boundary, operation)
    assert boundary[3] == []


def test_updated_reply_cannot_confirm_missing_source(boundary):
    boundary[2]["results"]["dream-launch-failure.envelope"].update(thread_id=None, message_id=None)
    with pytest.raises(AdminDataError) as error:
        boundary[1].execute(FAIL_LAUNCH_ENVELOPE, envelope_input(), REQUEST_ID, access_token="write-token",
            source=LaunchFailureExpectation(None, None))
    assert error.value.outcome_unknown and len(boundary[3]) == 1


@pytest.mark.parametrize("operation", OPERATIONS, ids=lambda value: value.capability.name)
@pytest.mark.parametrize("patch", [{"status": "in_progress"}, {"operation": "another-operation"},
    {"request_id": "another-original"}, {"extra": "private"}])
def test_malformed_original_receipt_never_resends_write(boundary, operation, patch):
    boundary[2]["receipt"] = {"status": "committed", "operation": operation.capability.name, "request_id": REQUEST_ID,
        "result": boundary[2]["results"][operation.capability.name], **patch}
    with pytest.raises(AdminDataError) as error: receipt(boundary, operation)
    assert error.value.code == "ADMIN_RESPONSE_INVALID" and len(boundary[3]) == 1
