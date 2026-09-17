# [Sync] 2026-09-17: verify confidential service OAuth and separate delegated-user Bearer transport.
# [Input] Actual SystemConfig DTO adapter, exact Admin catalog and synthetic HTTP transport.
# [Output] OAuth/idg separation, raw JSON preservation, closed patches and original receipt recovery evidence.
# [Pos] Provider-free Admin SystemConfig consumer tests; no PG, model, filesystem or normal service.
# [Sync] 2026-09-15: cover registered80 SystemConfig production consumer boundary.
from __future__ import annotations

import json
import math

import httpx
import pytest
from pydantic import ValidationError

from services.admin_data import AdminDataClient, AdminDataConfig, AdminDataError
from services.admin_data.models import CommittedReceiptDTO
from services.admin_data.system_config_data import (
    AdminSystemConfigData,
    GET_THREAD_SYSTEM_CONFIG,
    GET_USER_SYSTEM_CONFIG,
    PATCH_USER_SYSTEM_CONFIG,
    SYSTEM_CONFIG_OPERATIONS,
    SystemConfigGetInputDTO,
    SystemConfigPatchInputDTO,
)
from services.admin_data.workflow_data import WORKFLOW_SCHEMA_REQUIREMENTS


def _config() -> AdminDataConfig:
    return AdminDataConfig(
        base_url="https://admin.example",
        issuer="https://admin.example/api/auth",
        resource="https://dream.example/api",
        service_secret="s" * 32,
        service_client_id="dream-service",
    )


def _catalog(config: AdminDataConfig, operations=SYSTEM_CONFIG_OPERATIONS):
    return {
        "version": "1",
        "auth": {
            "issuer": config.issuer,
            "jwks_uri": config.jwks_uri,
            "resource": config.resource,
            "algorithm": "ES256",
            "clients": {"browser": "dream-browser", "device": "dream-device"},
            "scopes": ["dream:read", "dream:write"],
            "delegations": [],
        },
        "schema_capabilities": [item.model_dump() for item in WORKFLOW_SCHEMA_REQUIREMENTS],
        "operations": [item.capability.model_dump() for item in operations],
    }


def _boundary(*, raw='{"theme":"dark"}', patch_failure=None, catalog_operations=SYSTEM_CONFIG_OPERATIONS):
    config = _config()
    calls: list[tuple[str, str, dict | None]] = []

    def handler(request: httpx.Request):
        request_id = request.headers["x-request-id"]
        assert "x-ink-dream-service" not in request.headers and "x-ink-dream-credential" not in request.headers
        if request.headers["authorization"] != "Bearer fixture.service.access.token":
            assert request.headers["x-ink-dream-service-authorization"] == "Bearer fixture.service.access.token"
        if request.url.path.endswith("/capabilities"):
            calls.append(("capabilities", request.headers.get("authorization", ""), None))
            return httpx.Response(200, json={"request_id": request_id, "data": _catalog(config, catalog_operations)})
        if "/receipts/" in request.url.path:
            calls.append(("receipt", request.headers["authorization"], None))
            value = {
                "status": "committed",
                "operation": "user-system-config.patch",
                "request_id": request_id,
                "result": {"success": True},
            }
            return httpx.Response(200, json={"request_id": request_id, "data": value})
        operation = request.url.path.rsplit("/", 1)[1]
        envelope = json.loads(request.content)
        assert set(envelope) == {"request_id", "input"}
        assert envelope["request_id"] == request_id
        calls.append((operation, request.headers["authorization"], envelope["input"]))
        if operation == PATCH_USER_SYSTEM_CONFIG.capability.name and patch_failure is not None:
            raise patch_failure
        if operation == PATCH_USER_SYSTEM_CONFIG.capability.name:
            value = {"success": True}
        else:
            value = {"config_json": raw}
        return httpx.Response(200, json={"request_id": request_id, "data": value})

    http = httpx.Client(transport=httpx.MockTransport(handler))
    client = AdminDataClient(config, client=http, operations=SYSTEM_CONFIG_OPERATIONS)
    return AdminSystemConfigData(client), calls, http


def test_user_and_thread_reads_use_separate_bearers_and_closed_inputs():
    raw = '{"large":9007199254740993,"float":1.0,"negative":-0.0,"文字":"Ω","unknown":{"kept":true}}'
    data, calls, http = _boundary(raw=raw)
    try:
        user = data.get_user(SystemConfigGetInputDTO(), "user-read", access_token="oauth-user")
        thread = data.get_thread(
            GET_THREAD_SYSTEM_CONFIG.input_dto(thread_id="thread-1"),
            "thread-read",
            access_token="idg_" + "a" * 43,
        )
    finally:
        http.close()
    assert user == thread and user["large"] == 9_007_199_254_740_993
    assert type(user["float"]) is float and user["float"] == 1.0
    assert math.copysign(1.0, user["negative"]) == -1.0
    assert user["文字"] == "Ω" and user["unknown"] == {"kept": True}
    domain = [item for item in calls if item[0] != "capabilities"]
    assert domain == [
        ("user-system-config.get", "Bearer oauth-user", {}),
        ("thread-system-config.get", "Bearer idg_" + "a" * 43, {"thread_id": "thread-1"}),
    ]


@pytest.mark.parametrize("raw", ["[]", "null", '"text"', "broken", '{"n":NaN}', '{"n":Infinity}', '{"n":1e999}', '{"nested":[1e999]}'])
def test_corrupt_or_nonobject_config_fails_closed(raw):
    data, calls, http = _boundary(raw=raw)
    try:
        with pytest.raises(AdminDataError, match="ADMIN_RESPONSE_INVALID"):
            data.get_user(SystemConfigGetInputDTO(), "bad-read", access_token="oauth-user")
    finally:
        http.close()
    assert sum(name == "user-system-config.get" for name, _, _ in calls) == 1


def test_patch_serializes_only_present_normalized_fields():
    data, calls, http = _boundary()
    patch = SystemConfigPatchInputDTO(
        model="dream-balanced",
        provider="gateway",
        system_prompt="正文😀",
        workspace_enabled=False,
        sandbox_network_allowed_domains=["raw.githubusercontent.com", "*.npmjs.org"],
        sandbox_fs_allowed_write_paths=["/", "/data/out"],
        env_vars={"API_TIMEOUT_MS": "120000"},
    )
    try:
        result = data.patch_user(patch, "patch-1", access_token="oauth-user")
    finally:
        http.close()
    assert result.success is True
    sent = next(payload for name, _, payload in calls if name == "user-system-config.patch")
    assert sent == patch.model_dump(mode="json")
    assert "theme" not in sent and "actor_id" not in sent and "config_json" not in sent


@pytest.mark.parametrize("value", [
    {"actor_id": "42"},
    {"model": "dream-balanced"},
    {"provider": "gateway"},
    {"theme": None},
    {"sandbox_fs_allowed_write_paths": ["/data/"]},
    {"sandbox_network_allowed_domains": ["github.com", "github.com"]},
    {"env_vars": {"CLAUDE_CODE_TMPDIR": "/private/tmp"}},
])
def test_patch_dto_rejects_extra_null_unpaired_or_unmanaged_values(value):
    with pytest.raises(ValidationError):
        SystemConfigPatchInputDTO(**value)


def test_unknown_patch_uses_original_receipt_without_post_retry():
    data, calls, http = _boundary(patch_failure=httpx.ReadTimeout("private upstream body"))
    try:
        with pytest.raises(AdminDataError) as lost:
            data.patch_user(SystemConfigPatchInputDTO(theme="dark"), "original-patch", access_token="oauth-user")
        assert lost.value.outcome_unknown and lost.value.request_id == "original-patch"
        receipt = data.patch_receipt("original-patch", access_token="oauth-user")
    finally:
        http.close()
    assert isinstance(receipt, CommittedReceiptDTO) and receipt.result.success is True
    assert sum(name == "user-system-config.patch" for name, _, _ in calls) == 1
    assert sum(name == "receipt" for name, _, _ in calls) == 1


def test_missing_exact_operation_stops_before_domain_request():
    data, calls, http = _boundary(catalog_operations=(GET_USER_SYSTEM_CONFIG, PATCH_USER_SYSTEM_CONFIG))
    try:
        with pytest.raises(AdminDataError, match="ADMIN_CAPABILITY_UNAVAILABLE"):
            data.get_thread(GET_THREAD_SYSTEM_CONFIG.input_dto(thread_id="thread-1"), "missing-op", access_token="idg_" + "a" * 43)
    finally:
        http.close()
    assert [name for name, _, _ in calls] == ["capabilities"]
