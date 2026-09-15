# [Input] Actual Workflow DTO/client and Service snapshot seam with synthetic credentials.
# [Output] Strict contract, capability and public-to-Service provenance checks without PG/model.
# [Pos] Provider-free Workflow consumer regressions; no duplicate retry/source algorithm.
# [Sync] 2026-09-15: cover null/ten fields, actor/thread binding and no PG mapper for public snapshots.
# [Sync] 2026-09-16: prove the retired Dream SQL resolver is absent from production composition.
from __future__ import annotations

import asyncio
import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from services.admin_data import AdminDataClient, AdminDataConfig, AdminDataError
from services.admin_data.workflow_data import AdminWorkflowData, AdminWorkflowResolution, RESOLVE_WORKFLOW_CONTEXT, WORKFLOW_SCHEMA_REQUIREMENTS, WorkflowContextOutputDTO


def test_production_has_no_legacy_workflow_context_database_resolver():
    backend = Path(__file__).parents[1]
    assert not (backend / "services/story_workspace/dream_thread_binding.py").exists()
    application = (backend / "services/deck/story_workflow_application.py").read_text(encoding="utf-8")
    assert "dream_thread_binding" not in application


def context_value():
    return {"workflow_run_id": "run_" + "a" * 32, "thread_id": "thread-1", "deck_id": "deck-1", "agent_id": None,
        "deck_plugin_id": "plugin-1", "deck_plugin_version": "1.0.1", "deck_plugin_binding_id": "binding-1",
        "binding_revision": 1, "deck_runtime_snapshot_id": "snapshot-1", "runtime_plugin_lock_id": "lock-1"}


def consumer(*, context=None, schemas=None, operation=None):
    config = AdminDataConfig(base_url="https://admin.example", issuer="https://admin.example/api/auth", resource="https://dream.example/api", service_secret="s" * 32, service_client_id="dream-service")
    calls = []
    def handler(request):
        calls.append(request)
        request_id = request.headers["x-request-id"]
        if request.url.path.endswith("/capabilities"):
            data = {"version": "1", "auth": {"issuer": config.issuer, "jwks_uri": config.jwks_uri, "resource": config.resource, "algorithm": "ES256", "clients": {"browser": "dream-browser", "device": "dream-device"}, "scopes": ["dream:read"], "delegations": []},
                "schema_capabilities": [item.model_dump() for item in WORKFLOW_SCHEMA_REQUIREMENTS] if schemas is None else schemas,
                "operations": [operation or RESOLVE_WORKFLOW_CONTEXT.capability.model_dump()]}
        else:
            assert request.headers["authorization"] == "Bearer synthetic-oauth"
            assert request.headers["x-ink-dream-credential"] == "s" * 32
            assert json.loads(request.content) == {"request_id": request_id, "input": {"thread_id": "thread-1"}}
            data = {"context": context}
        return httpx.Response(200, json={"request_id": request_id, "data": data})
    client = AdminDataClient(config, client=httpx.Client(transport=httpx.MockTransport(handler)), operations=(RESOLVE_WORKFLOW_CONTEXT,))
    return AdminWorkflowData(client), calls


@pytest.mark.parametrize("context", [None, context_value()])
def test_actual_read_produces_immutable_actor_thread_snapshot(context):
    data, calls = consumer(context=context)
    snapshot = data.resolve("thread-1", "request-1", access_token="synthetic-oauth", canonical_user_id="42")
    resolved = snapshot.context_for(actor_id="42", thread_id="thread-1")
    assert (resolved.model_dump() if resolved is not None else None) == context
    assert [item.url.path.rsplit("/", 1)[1] for item in calls] == ["capabilities", "workflow-context.resolve"]
    with pytest.raises(FrozenInstanceError):
        snapshot.thread_id = "other"
    if resolved is not None:
        with pytest.raises(ValidationError):
            resolved.binding_revision = 2


@pytest.mark.parametrize("field,value", [("binding_revision", 0), ("binding_revision", True), ("binding_revision", 9_007_199_254_740_992), ("binding_revision", 1.0), ("workflow_run_id", "run-invalid"), ("thread_id", "x" * 256), ("agent_id", ""), ("deck_plugin_id", " ")])
def test_context_preserves_strict_original_bounds(field, value):
    with pytest.raises(ValidationError):
        WorkflowContextOutputDTO(context={**context_value(), field: value})


def test_nullable_context_and_agent_remain_required():
    with pytest.raises(ValidationError):
        WorkflowContextOutputDTO.model_validate({})
    context = context_value()
    del context["agent_id"]
    with pytest.raises(ValidationError):
        WorkflowContextOutputDTO(context=context)


@pytest.mark.parametrize("actor_id,thread_id", [("43", "thread-1"), ("42", "other")])
def test_snapshot_rejects_mismatched_service_request(actor_id, thread_id):
    snapshot = AdminWorkflowResolution("42", "thread-1", None)
    with pytest.raises(AdminDataError, match="DREAM_DELEGATION_ENTITY_DENIED"):
        snapshot.context_for(actor_id=actor_id, thread_id=thread_id)


def test_response_context_cannot_select_another_thread():
    data, _ = consumer(context={**context_value(), "thread_id": "other"})
    with pytest.raises(AdminDataError, match="ADMIN_RESPONSE_INVALID"):
        data.resolve("thread-1", "request-1", access_token="synthetic-oauth", canonical_user_id="42")


@pytest.mark.parametrize("schemas", [[], [item.model_dump() for item in WORKFLOW_SCHEMA_REQUIREMENTS[:1]], [*([item.model_dump() for item in WORKFLOW_SCHEMA_REQUIREMENTS]), WORKFLOW_SCHEMA_REQUIREMENTS[0].model_dump()]])
def test_missing_or_duplicate_physical_schema_stops_before_read(schemas):
    data, calls = consumer(schemas=schemas)
    with pytest.raises(AdminDataError, match="ADMIN_CAPABILITY_UNAVAILABLE"):
        data.resolve("thread-1", "request-1", access_token="synthetic-oauth", canonical_user_id="42")
    assert len(calls) == 1


def test_operation_digest_drift_stops_before_read():
    data, calls = consumer(operation={**RESOLVE_WORKFLOW_CONTEXT.capability.model_dump(), "contract_sha256": "0" * 64})
    with pytest.raises(AdminDataError, match="ADMIN_CAPABILITY_UNAVAILABLE"):
        data.resolve("thread-1", "request-1", access_token="synthetic-oauth", canonical_user_id="42")
    assert len(calls) == 1


@pytest.mark.parametrize("context", [None, context_value()])
def test_service_uses_public_snapshot_without_calling_pg_mapper(context):
    from claude_agent.service import ClaudeAgentRunRequest, ClaudeAgentService
    data, _ = consumer(context=context)
    resolution = data.resolve("thread-1", "request-1", access_token="synthetic-oauth", canonical_user_id="42")
    class ForbiddenMapper:
        def resolve(self, **kwargs):
            pytest.fail("Public snapshot must not query the legacy PG mapper")
    service = ClaudeAgentService(dream_context_mapper=ForbiddenMapper())
    request = ClaudeAgentRunRequest(user_id="42", thread_id="thread-1", admin_workflow_resolution=resolution)
    resolved = asyncio.run(service._resolve_dream_context(request))
    assert resolved is resolution.context


def test_service_rejects_snapshot_for_a_different_actor_without_pg():
    from claude_agent.service import ClaudeAgentRunRequest, ClaudeAgentService
    class ForbiddenMapper:
        def resolve(self, **kwargs):
            pytest.fail("Wrong snapshot must not fall back to PG")
    service = ClaudeAgentService(dream_context_mapper=ForbiddenMapper())
    request = ClaudeAgentRunRequest(user_id="43", thread_id="thread-1", admin_workflow_resolution=AdminWorkflowResolution("42", "thread-1", None))
    with pytest.raises(AdminDataError, match="DREAM_DELEGATION_ENTITY_DENIED"):
        asyncio.run(service._resolve_dream_context(request))
