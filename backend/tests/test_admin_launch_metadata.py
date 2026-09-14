# [Input] Registered launch metadata client/DTOs and the original application source Protocol.
# [Output] Scoped source/claim/finish/receipt technical evidence without endpoint or Runtime claims.
# [Pos] Provider-free harness; production launch wiring/default/prepare/Voice/failure remain SQL.
# [Sync] 2026-09-15: reuse original application fingerprint/IDs and reject unknown writes without resend.
from __future__ import annotations

import asyncio
import copy
from datetime import UTC, datetime
import json
from uuid import uuid4

import httpx
import pytest
from pydantic import ValidationError

from services.admin_data import AdminDataClient, AdminDataConfig, AdminDataError
from services.admin_data.launch_metadata_data import AdminLaunchMetadataData, AdminLaunchSourceRepository, CLAIM_LAUNCH, ENSURE_LAUNCH_SOURCE, FINISH_LAUNCH, LAUNCH_METADATA_OPERATIONS, LaunchClaimInputDTO, LaunchFinishInputDTO, LaunchSourceInputDTO
from services.admin_data.request_auth import AdminRequestActor
from services.admin_data.workflow_data import WORKFLOW_SCHEMA_REQUIREMENTS
from services.story_workspace.dream_launch_application_service import DreamLaunchApplicationService, DreamLaunchSource, _sha256
from story_workspace.contracts import StoryWorkspaceDreamRunContext
from tests.test_story_workspace_dream_launch import ACTOR_ID, DECK_ID, WORKSPACE_ID, DreamLaunchFixture, command

RUN_ID = "run_" + "a" * 32
CLAIM_ID = "dlc_" + "b" * 32
INSTRUCTION = " original Dream instruction \n"


def source_result(value, created=True):
    ids = DreamLaunchApplicationService._deterministic_source_ids(actor_id=ACTOR_ID, workspace_id=value.workspace_id, idempotency_key=value.idempotency_key)
    payload = {"deck_id": value.deck_id, "goal": value.goal}
    if value.agent_id is not None: payload["agent_id"] = value.agent_id
    return {"source": {"thread_id": ids[0], "message_id": ids[1], "message_time": "2026-09-15T00:00:00.123456+00:00", "request_fingerprint": _sha256(payload), "created": created}}


@pytest.fixture
def boundary(monkeypatch):
    import database
    monkeypatch.setattr(database, "get_db", lambda *_a, **_kw: pytest.fail("metadata consumer must not open SQL"))
    config = AdminDataConfig(base_url="https://admin.example", issuer="https://admin.example/api/auth", resource="https://dream.example/api", service_client_id="dream-service", service_secret="s" * 32)
    schemas = [value.model_dump() for value in WORKFLOW_SCHEMA_REQUIREMENTS]
    operations = [value.capability.model_dump() for value in LAUNCH_METADATA_OPERATIONS]
    calls = []
    state = {"result": None, "receipt": None}
    def handler(request):
        rid = request.headers["x-request-id"]
        assert request.headers["x-ink-dream-service"] == config.service_client_id and request.headers["x-ink-dream-credential"] == config.service_secret
        assert "cookie" not in request.headers
        if request.url.path.endswith("/capabilities"):
            value = {"version": "1", "auth": {"issuer": config.issuer, "jwks_uri": config.jwks_uri, "resource": config.resource, "algorithm": "ES256", "clients": {"browser": "dream-browser", "device": "dream-device"}, "scopes": ["dream:read", "dream:write"], "delegations": []}, "schema_capabilities": schemas, "operations": operations}
        else:
            assert request.headers["authorization"] == "Bearer write-token"
            if "/receipts/" in request.url.path:
                assert request.method == "GET" and request.url.path.endswith("/" + rid)
                operation = request.url.params["operation"]
                calls.append(("receipt", rid, operation, None))
                value = state["receipt"]
            else:
                assert request.method == "POST"
                envelope = json.loads(request.content)
                assert set(envelope) == {"request_id", "input"} and envelope["request_id"] == rid
                operation = request.url.path.rsplit("/", 1)[-1]
                calls.append(("execute", rid, operation, envelope["input"]))
                value = state["result"]
                if value is None:
                    value = source_result(LaunchSourceInputDTO(**envelope["input"]), created=len(calls) == 1)
            if isinstance(value, Exception): raise value
            if isinstance(value, tuple):
                status, code = value
                return httpx.Response(status, json={"request_id": rid, "error": {"code": code, "message": "private lease/context"}})
        return httpx.Response(200, json={"request_id": rid, "data": value})
    http = httpx.Client(transport=httpx.MockTransport(handler))
    client = AdminDataClient(config, client=http, operations=LAUNCH_METADATA_OPERATIONS)
    actor = AdminRequestActor("opaque-subject", ACTOR_ID, "dream-browser", frozenset({"dream:read", "dream:write"}), 1, 2, "write-token")
    source_input = LaunchSourceInputDTO(workspace_id=WORKSPACE_ID, deck_id=DECK_ID, agent_id=None, goal="原目标", idempotency_key="launch-key")
    wire = source_result(source_input)["source"]
    source = DreamLaunchSource(wire["thread_id"], wire["message_id"], datetime(2026, 9, 15, tzinfo=UTC), wire["request_fingerprint"], True)
    context = StoryWorkspaceDreamRunContext(workflow_run_id=RUN_ID, thread_id=source.thread_id, deck_id=DECK_ID, agent_id=None,
        deck_plugin_id="plugin-1", deck_plugin_version="1.0.0", deck_plugin_binding_id="binding-1", binding_revision=1,
        deck_runtime_snapshot_id="snapshot-1", runtime_plugin_lock_id="lock-1")
    yield AdminLaunchMetadataData(client, canonical_user_id=ACTOR_ID), client, actor, state, calls, schemas, operations, source_input, source, context
    http.close()


@pytest.mark.parametrize("agent", [None, "selected-agent"])
def test_original_application_source_seam_normal_replay_and_conditional_fingerprint(boundary, agent):
    _, client, actor, _, calls, *_ = boundary
    fixture = DreamLaunchFixture()
    service = DreamLaunchApplicationService(source_repository=AdminLaunchSourceRepository(client, actor=actor), workflow=fixture, dispatcher=fixture.dispatcher)
    value = command(**({"agentId": agent} if agent is not None else {}))
    first = asyncio.run(service.launch(value, actor_id=ACTOR_ID, workspace_id=WORKSPACE_ID))
    second = asyncio.run(service.launch(value, actor_id=ACTOR_ID, workspace_id=WORKSPACE_ID))
    assert first == second and len(calls) == 2 and len(fixture.preflight_calls) == 2
    assert all(set(call[3]) == {"workspace_id", "deck_id", "agent_id", "goal", "idempotency_key"} for call in calls)
    payload = {"deck_id": value.deck_id, "goal": value.goal}
    if agent is not None: payload["agent_id"] = agent
    assert fixture.dispatcher.calls[0]["source"].request_fingerprint == _sha256(payload)
    assert "source" not in calls[0][3] and "actor_id" not in calls[0][3]


@pytest.mark.parametrize("patch", [{"thread_id": str(uuid4())}, {"request_fingerprint": "sha256:" + "f" * 64}, {"created": 0}, None])
def test_source_unknown_or_bad_reply_stops_original_usecase_before_pf_run_dispatch(boundary, patch):
    _, client, actor, state, calls, *_ = boundary
    fixture = DreamLaunchFixture()
    service = DreamLaunchApplicationService(source_repository=AdminLaunchSourceRepository(client, actor=actor), workflow=fixture, dispatcher=fixture.dispatcher)
    value = command()
    source_input = LaunchSourceInputDTO(workspace_id=WORKSPACE_ID, **value.model_dump())
    if patch is None:
        state["result"] = httpx.ReadTimeout("private source")
    else:
        wire = source_result(source_input)
        wire["source"].update(patch)
        state["result"] = wire
    with pytest.raises(AdminDataError) as error:
        asyncio.run(service.launch(value, actor_id=ACTOR_ID, workspace_id=WORKSPACE_ID))
    assert error.value.outcome_unknown and error.value.request_id == calls[0][1] and len(calls) == 1
    assert len(fixture.binding_calls) == 1 and not fixture.preflight_calls and not fixture.run_calls and not fixture.dispatcher.calls


def claim_result(source, context, claimed=True):
    common = {"claimed": claimed, "workflow_run_id": RUN_ID, "thread_id": source.thread_id, "message_id": source.message_id}
    if not claimed: return common
    metadata = {"actorId": ACTOR_ID, "workspaceId": WORKSPACE_ID, "workflowRunId": RUN_ID, "threadId": source.thread_id, "dreamContext": context.model_dump(mode="json"), "dispatchStatus": "dispatched", "extraOriginal": {"large": 9_007_199_254_740_993}}
    return {**common, "claim_id": CLAIM_ID, "context": context.model_dump(), "parts_json": json.dumps([{"type": "text", "text": INSTRUCTION}], ensure_ascii=False), "metadata_json": json.dumps(metadata, ensure_ascii=False)}


@pytest.mark.parametrize("claimed", [False, True])
def test_claim_issued_context_and_raw_envelope_without_runtime(boundary, claimed):
    data, _, _, state, calls, *_, source_input, source, context = boundary
    value = state["result"] = claim_result(source, context, claimed)
    dto = LaunchClaimInputDTO(workspace_id=WORKSPACE_ID, workflow_run_id=RUN_ID, instruction_text=INSTRUCTION)
    result = data.execute(CLAIM_LAUNCH, dto, str(uuid4()), access_token="write-token", source=source, context=context)
    assert result.model_dump() == value and result.root.claimed is claimed and len(calls) == 1
    assert calls[0][3] == {"workspace_id": WORKSPACE_ID, "workflow_run_id": RUN_ID, "instruction_text": INSTRUCTION}
    assert INSTRUCTION not in repr(result)


@pytest.mark.parametrize("patch", [{"claimed": 1}, {"thread_id": str(uuid4())}, {"workflow_run_id": "run_" + "c" * 32}, {"claim_id": "private-invalid"}, {"parts_json": "private-invalid"}, {"parts_json": "[]"}, {"metadata_json": "[]"}, {"extra": "private"}])
def test_bad_claim_reply_unknown_without_resend(boundary, patch):
    data, _, _, state, calls, *_, source_input, source, context = boundary
    state["result"] = {**claim_result(source, context), **patch}
    with pytest.raises(AdminDataError) as error:
        data.execute(CLAIM_LAUNCH, LaunchClaimInputDTO(workspace_id=WORKSPACE_ID, workflow_run_id=RUN_ID, instruction_text=INSTRUCTION), str(uuid4()), access_token="write-token", source=source, context=context)
    assert error.value.code == "ADMIN_RESPONSE_INVALID" and error.value.outcome_unknown and len(calls) == 1 and "private" not in str(error.value)


@pytest.mark.parametrize("field,value", [("actorId", "other"), ("workspaceId", "other"), ("dispatchStatus", "dispatching"), ("dispatchClaimId", CLAIM_ID), ("dreamContext", {}), ("threadId", "other")])
def test_runtime_metadata_binding_mismatch_rejected(boundary, field, value):
    data, _, _, state, calls, *_, source_input, source, context = boundary
    result = state["result"] = claim_result(source, context)
    metadata = json.loads(result["metadata_json"])
    metadata[field] = value
    result["metadata_json"] = json.dumps(metadata)
    with pytest.raises(AdminDataError):
        data.execute(CLAIM_LAUNCH, LaunchClaimInputDTO(workspace_id=WORKSPACE_ID, workflow_run_id=RUN_ID, instruction_text=INSTRUCTION), str(uuid4()), access_token="write-token", source=source, context=context)
    assert len(calls) == 1


@pytest.mark.parametrize("mutation", ["context-value", "nonfinite-exponent"])
def test_full_context_value_and_finite_raw_json_required(boundary, mutation):
    data, _, _, state, calls, *_, source_input, source, context = boundary
    result = state["result"] = claim_result(source, context)
    if mutation == "context-value":
        result["context"]["deck_plugin_version"] = "another-version"
    else:
        result["metadata_json"] = result["metadata_json"].replace("9007199254740993", "1e999")
    with pytest.raises(AdminDataError) as error:
        data.execute(CLAIM_LAUNCH, LaunchClaimInputDTO(workspace_id=WORKSPACE_ID, workflow_run_id=RUN_ID, instruction_text=INSTRUCTION), str(uuid4()), access_token="write-token", source=source, context=context)
    assert error.value.code == "ADMIN_RESPONSE_INVALID" and error.value.outcome_unknown and len(calls) == 1


@pytest.mark.parametrize("field", ["agent_id", "binding_revision", "deck_plugin_version"])
def test_ten_context_fields_required_and_original_bound(boundary, field):
    data, _, _, state, calls, *_, source_input, source, context = boundary
    result = state["result"] = claim_result(source, context)
    result["context"].pop(field)
    with pytest.raises(AdminDataError):
        data.execute(CLAIM_LAUNCH, LaunchClaimInputDTO(workspace_id=WORKSPACE_ID, workflow_run_id=RUN_ID, instruction_text=INSTRUCTION), str(uuid4()), access_token="write-token", source=source, context=context)
    assert len(calls) == 1


@pytest.mark.parametrize("accepted,finished", [(False, False), (False, True), (True, False), (True, True)])
def test_finish_only_issued_claim_boolean_with_stale_false_preserved(boundary, accepted, finished):
    data, _, _, state, calls, *_, source_input, source, context = boundary
    state["result"] = {"finished": finished, "workflow_run_id": RUN_ID, "thread_id": source.thread_id, "message_id": source.message_id}
    dto = LaunchFinishInputDTO(workspace_id=WORKSPACE_ID, workflow_run_id=RUN_ID, claim_id=CLAIM_ID, accepted=accepted)
    result = data.execute(FINISH_LAUNCH, dto, str(uuid4()), access_token="write-token", source=source)
    assert result.finished is finished and calls[0][3] == dto.model_dump()


@pytest.mark.parametrize("operation", LAUNCH_METADATA_OPERATIONS)
@pytest.mark.parametrize("status", ["absent", "committed"])
def test_explicit_same_uuid_generic_receipt_after_unknown_without_resend(boundary, operation, status):
    data, _, _, state, calls, *_, source_input, source, context = boundary
    dto, value = source_input, source_result(source_input)
    if operation is CLAIM_LAUNCH:
        dto = LaunchClaimInputDTO(workspace_id=WORKSPACE_ID, workflow_run_id=RUN_ID, instruction_text=INSTRUCTION)
        value = claim_result(source, context)
    elif operation is FINISH_LAUNCH:
        dto = LaunchFinishInputDTO(workspace_id=WORKSPACE_ID, workflow_run_id=RUN_ID, claim_id=CLAIM_ID, accepted=True)
        value = {"finished": True, "workflow_run_id": RUN_ID, "thread_id": source.thread_id, "message_id": source.message_id}
    rid = str(uuid4())
    state["result"] = httpx.ReadTimeout("private goal")
    with pytest.raises(AdminDataError) as error:
        data.execute(operation, dto, rid, access_token="write-token", source=source, context=context)
    assert error.value.request_id == rid and error.value.outcome_unknown and len(calls) == 1
    state["receipt"] = {"status": status, "operation": operation.capability.name, "request_id": rid, **({"result": value} if status == "committed" else {})}
    result = data.receipt(operation, dto, rid, access_token="write-token", source=source, context=context)
    assert result.status == status and len(calls) == 2 and calls[-1][:3] == ("receipt", rid, operation.capability.name)


def test_claim_stale_receipt_safe_409_no_reclaim(boundary):
    data, _, _, state, calls, *_, source_input, source, context = boundary
    state["receipt"] = (409, "DREAM_LAUNCH_CLAIM_STALE")
    with pytest.raises(AdminDataError) as error:
        data.receipt(CLAIM_LAUNCH, LaunchClaimInputDTO(workspace_id=WORKSPACE_ID, workflow_run_id=RUN_ID, instruction_text=INSTRUCTION), str(uuid4()), access_token="write-token", source=source, context=context)
    assert error.value.code == "DREAM_LAUNCH_CLAIM_STALE" and not error.value.outcome_unknown and len(calls) == 1


@pytest.mark.parametrize("mutation", ["schema-missing", "schema-hash", "duplicate", "operation-hash"])
def test_actual_schema_and_operation_gate_before_source_write(boundary, mutation):
    data, _, _, _, calls, schemas, operations, source_input, source, _ = boundary
    if mutation == "schema-missing": schemas.pop()
    elif mutation == "schema-hash": schemas[-1]["contract_sha256"] = "0" * 64
    elif mutation == "duplicate": schemas.append(copy.copy(schemas[0]))
    else: operations[0]["contract_sha256"] = "0" * 64
    with pytest.raises(AdminDataError): data.execute(ENSURE_LAUNCH_SOURCE, source_input, str(uuid4()), access_token="write-token", source=source)
    assert not calls


@pytest.mark.parametrize("patch", [{"goal": " goal "}, {"workspace_id": "workspace\x1c"}, {"agent_id": " agent "}, {"goal": "😀" * 12001}, {"deck_id": "😀" * 256}, {"idempotency_key": "😀"}])
def test_original_boundary_and_codepoint_constraints(boundary, patch):
    source_input = boundary[-3]
    with pytest.raises(ValidationError): LaunchSourceInputDTO(**{**source_input.model_dump(), **patch})


def test_server_actor_scope_and_actor_override_denied_before_http(boundary):
    _, client, actor, _, calls, *_, source_input, source, _ = boundary
    with pytest.raises(AdminDataError): AdminLaunchSourceRepository(client, actor={})
    adapter = AdminLaunchSourceRepository(client, actor=actor)
    with pytest.raises(AdminDataError):
        asyncio.run(adapter.ensure_source(actor_id="other", **source_input.model_dump(), thread_id=source.thread_id, message_id=source.message_id, request_fingerprint=source.request_fingerprint))
    assert not calls
