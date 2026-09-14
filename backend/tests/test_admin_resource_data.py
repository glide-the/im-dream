# [Input] Production AdminResourceData/client/provider with pinned contracts and injected HTTP.
# [Output] Resource state/LKG, wire identity, capability failure and unknown-write recovery evidence.
# [Pos] Provider-free resource domain tests; no PG, real account or model access.
# [Sync] 2026-09-14: exercise actual production adapters after the composition root cutover.

from __future__ import annotations

from datetime import datetime, timezone
import json
from uuid import UUID

import httpx
import pytest
from pydantic import ValidationError

import tests._sdk_stubs  # noqa: F401
from claude_agent.admission import AgentAdmissionConfig
from claude_agent.resource_policy import ClaudeAgentResourcePolicyProvider
from services.admin_data import AdminDataClient, AdminDataConfig, AdminDataError
from services.admin_data.resource_data import (
    AdminResourceData, RESOURCE_OPERATIONS, RESOURCE_POLICY_READ,
    ResourceObserverPublishInputDTO,
)
from tests.test_claude_agent_resource_postgres_sink import _snapshot


@pytest.fixture
def config():
    return AdminDataConfig(base_url="https://admin.example", issuer="https://admin.example/api/auth", resource="https://dream.example/api", service_secret="s" * 32, service_client_id="dream-web")


def adapter(config, handler):
    def transport(request):
        if request.url.path.endswith("/capabilities"):
            return httpx.Response(200, json={"request_id": request.headers["x-request-id"], "data": {
                "version": "1", "auth": {"issuer": config.issuer, "jwks_uri": config.jwks_uri, "algorithm": "ES256", "resource": config.resource, "clients": {"browser": "dream-browser", "device": "dream-device"}, "scopes": ["dream:read"], "delegations": []},
                "schema_capabilities": [], "operations": [operation.capability.model_dump() for operation in RESOURCE_OPERATIONS],
            }})
        return handler(request)
    return AdminResourceData(AdminDataClient(config, client=httpx.Client(transport=httpx.MockTransport(transport)), operations=RESOURCE_OPERATIONS))


POLICY = {"schemaVersion": 1, "revision": 7, "maxConcurrentRuns": 3, "runMemoryBudgetMib": 768, "memoryReserveMib": 256, "retryAfterSeconds": 120, "claudeCodeEffortLevel": "high"}


@pytest.mark.parametrize("status,expected", [("configured", "applied"), ("not_configured", "not_configured"), ("invalid", "invalid")])
def test_production_reader_preserves_policy_states_and_exact_wire(config, status, expected):
    seen = []
    def handler(request):
        seen.append(request)
        assert request.url.path.endswith("/operations/resource-policy.read")
        body = json.loads(request.content)
        assert body == {"request_id": request.headers["x-request-id"], "input": {}}
        assert "authorization" not in request.headers
        assert request.headers["X-Ink-Dream-Service"] == config.service_client_id
        assert request.headers["X-Ink-Dream-Credential"] == config.service_secret
        return httpx.Response(200, json={"request_id": body["request_id"], "data": {"status": status, "value": POLICY if status == "configured" else None, "updated_at": "2026-09-14T00:00:00Z" if status == "configured" else None}})
    fallback = AgentAdmissionConfig(2, 640, 192, 90)
    result = ClaudeAgentResourcePolicyProvider(adapter(config, handler).read_policy).load(fallback)
    assert result.status == expected and len(seen) == 1
    if status == "configured":
        assert result.config == AgentAdmissionConfig(3, 768, 256, 120)
        assert result.revision == 7 and result.claude_code_effort_level == "high"
    else:
        assert result.config is fallback and result.revision is None


@pytest.mark.parametrize("failure", ["timeout", "scope", "extra", "bool-version", "unsafe-memory"])
def test_resource_failures_retain_effective_fallback(config, failure):
    def handler(request):
        request_id = request.headers["x-request-id"]
        if failure == "timeout": raise httpx.ReadTimeout("private endpoint", request=request)
        if failure == "scope": return httpx.Response(403, json={"request_id": request_id, "error": {"code": "SCOPE_DENIED", "message": "private detail"}})
        value = dict(POLICY)
        if failure == "bool-version": value["schemaVersion"] = True
        if failure == "unsafe-memory": value["runMemoryBudgetMib"] = 8_589_934_591
        result = {"status": "configured", "value": value, "updated_at": "2026-09-14T00:00:00Z"}
        if failure == "extra": result["row_id"] = 17
        return httpx.Response(200, json={"request_id": request_id, "data": result})
    fallback = AgentAdmissionConfig(2, 640, 192, 90)
    loaded = ClaudeAgentResourcePolicyProvider(adapter(config, handler).read_policy).load(fallback)
    assert loaded.status == "unavailable" and loaded.config is fallback


def observer_input(started=0):
    snapshot = _snapshot(started=started)
    return ResourceObserverPublishInputDTO(instance_id=UUID("11dda993-ff18-4294-af40-8f4af39fd853"), process_started_at=datetime(2026, 9, 14, tzinfo=timezone.utc), sampled_at=snapshot.sample.sampled_at, snapshot=snapshot)


def test_unknown_write_waits_for_original_receipt_before_later_snapshot(config):
    seen = []; committed = False
    def handler(request):
        seen.append(request)
        request_id = request.headers["x-request-id"]
        if "/receipts/" in request.url.path:
            assert request.url.path.endswith("/receipts/write-1")
            assert request.url.params["operation"] == "resource-observer.publish"
            data = {"status": "committed" if committed else "absent", "operation": "resource-observer.publish", "request_id": "write-1"}
            if committed: data["result"] = {"accepted": True, "heartbeat_at": "2026-09-14T00:00:01Z", "sampled_at": None}
            return httpx.Response(200, json={"request_id": request_id, "data": data})
        body = json.loads(request.content)
        assert body["input"]["sampled_at"] == body["input"]["snapshot"]["sample"]["sampled_at"]
        if request_id == "write-1": raise httpx.ReadTimeout("commit unknown", request=request)
        return httpx.Response(200, json={"request_id": request_id, "data": {"accepted": True, "heartbeat_at": "2026-09-14T00:00:02Z", "sampled_at": None}})
    data = adapter(config, handler)
    with pytest.raises(AdminDataError) as first:
        data.publish_observer("write-1", observer_input(1))
    assert first.value.outcome_unknown
    with pytest.raises(AdminDataError) as unresolved:
        data.publish_observer("write-2", observer_input(2))
    assert unresolved.value.request_id == "write-1" and unresolved.value.outcome_unknown
    assert len(seen) == 2
    committed = True
    data.publish_observer("write-3", observer_input(3))
    assert [request.headers["x-request-id"] for request in seen] == ["write-1", "write-1", "write-1", "write-3"]


def test_changed_capability_never_sends_resource_operation(config):
    seen = []
    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={"request_id": request.headers["x-request-id"], "data": {"version": "1", "auth": {"issuer": config.issuer, "jwks_uri": config.jwks_uri, "algorithm": "ES256", "resource": config.resource, "clients": {"browser": "dream-browser", "device": "dream-device"}, "scopes": [], "delegations": []}, "schema_capabilities": [], "operations": [RESOURCE_POLICY_READ.capability.model_copy(update={"contract_sha256": "b" * 64}).model_dump()]}})
    data = AdminResourceData(AdminDataClient(config, client=httpx.Client(transport=httpx.MockTransport(handler)), operations=RESOURCE_OPERATIONS))
    loaded = ClaudeAgentResourcePolicyProvider(data.read_policy).load(AgentAdmissionConfig(1, 512, 128, 60))
    assert loaded.status == "unavailable" and len(seen) == 1


def test_observer_input_rejects_mismatched_sample_and_naive_time():
    value = observer_input()
    for update in ({"sampled_at": datetime(2026, 9, 14, tzinfo=timezone.utc)}, {"process_started_at": datetime(2026, 9, 14)}):
        with pytest.raises(ValidationError):
            ResourceObserverPublishInputDTO.model_validate({**value.model_dump(), **update})
