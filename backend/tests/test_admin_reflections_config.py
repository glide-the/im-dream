# [Input] Actual Reflections section DTO consumer, synthetic Admin catalog and controlled raw replies.
# [Output] Exact contract, raw JSON, OAuth, closed input and no-retry evidence.
# [Pos] Provider-free registered83 consumer tests; no PostgreSQL, filesystem or normal account.
# [Sync] 2026-09-15: cover the three published Reflections section-config operations.
from __future__ import annotations

import json

import httpx
import pytest
from pydantic import ValidationError

from services.admin_data import AdminDataClient, AdminDataConfig, AdminDataError
from services.admin_data.reflections_config_data import (
    AdminReflectionsSectionConfigData,
    DELETE_REFLECTIONS_SECTION_CONFIG,
    GET_REFLECTIONS_SECTION_CONFIG,
    REFLECTIONS_SECTION_CONFIG_OPERATIONS,
    SAVE_REFLECTIONS_SECTION_CONFIG,
    ReflectionsSectionInputDTO,
    ReflectionsSectionSaveInputDTO,
)
from services.admin_data.workflow_data import WORKFLOW_SCHEMA_REQUIREMENTS


TOKEN = "oauth-reflections-token"


def _boundary(*, get_json: str | None = '{"WORKFLOW.md":"custom"}', lose: str | None = None, operations=REFLECTIONS_SECTION_CONFIG_OPERATIONS):
    config = AdminDataConfig(
        base_url="https://admin.example",
        issuer="https://admin.example/api/auth",
        resource="https://dream.example/api",
        service_secret="s" * 32,
        service_client_id="dream-service",
    )
    calls: list[httpx.Request] = []

    def transport(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        request_id = request.headers["x-request-id"]
        if request.url.path.endswith("/capabilities"):
            value = {
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
        else:
            assert request.headers["authorization"] == "Bearer " + TOKEN
            name = request.url.path.rsplit("/", 1)[-1]
            body = json.loads(request.content)
            assert set(body) == {"request_id", "input"}
            if name == GET_REFLECTIONS_SECTION_CONFIG.capability.name:
                value = {"prompt_files_json": get_json}
            elif name == SAVE_REFLECTIONS_SECTION_CONFIG.capability.name:
                assert json.loads(body["input"]["prompt_files_json"]) == {"WORKFLOW.md": "custom"}
                value = {"saved": True}
            else:
                value = {"deleted": False}
            if name == lose:
                raise httpx.ReadTimeout("synthetic response loss")
        return httpx.Response(200, json={"request_id": request_id, "data": value})

    http = httpx.Client(transport=httpx.MockTransport(transport))
    client = AdminDataClient(config, client=http, operations=operations)
    return AdminReflectionsSectionConfigData(client), calls, http


def test_exact_operation_descriptors_and_schema_gate() -> None:
    assert [item.capability.contract_sha256 for item in REFLECTIONS_SECTION_CONFIG_OPERATIONS] == [
        "2e1057f1cdd9248c2dbd603057310399e7ea5a51c90c601405ebb86868ccb640",
        "dc2ba4ee442618b4fd39d75b8ddf9ca834b25913d85e4bee0cba76d20b4b047f",
        "8b03792f711e79c1d12343a93980da91d7675d280f9713ab454e6369b2b45967",
    ]
    assert [item.capability.user_scope for item in REFLECTIONS_SECTION_CONFIG_OPERATIONS] == [
        "dream:read", "dream:write", "dream:write"
    ]


def test_get_preserves_raw_python_numeric_categories_and_unknown_keys() -> None:
    raw = '{"large":9007199254740993,"float":1.0,"negative":-0.0,"unknown":{"文字":"Ω"}}'
    data, calls, http = _boundary(get_json=raw)
    try:
        result = data.get(ReflectionsSectionInputDTO(section="echoes"), "get-1", access_token=TOKEN)
    finally:
        http.close()
    assert result["large"] == 9_007_199_254_740_993
    assert isinstance(result["float"], float) and result["float"] == 1.0
    assert json.dumps(result["negative"]) == "-0.0"
    assert result["unknown"] == {"文字": "Ω"}
    assert [item.method for item in calls] == ["GET", "POST"]


@pytest.mark.parametrize("raw", [None, "{}"])
def test_get_preserves_absent_and_empty_object(raw) -> None:
    data, _, http = _boundary(get_json=raw)
    try:
        result = data.get(ReflectionsSectionInputDTO(section="traits"), "get-2", access_token=TOKEN)
    finally:
        http.close()
    if raw is None:
        assert result is None
    else:
        assert result == {}


@pytest.mark.parametrize("raw", ["not-json", "[]", "1"])
def test_invalid_get_reply_fails_closed(raw: str) -> None:
    data, _, http = _boundary(get_json=raw)
    try:
        with pytest.raises(AdminDataError) as captured:
            data.get(ReflectionsSectionInputDTO(section="patterns"), "bad-get", access_token=TOKEN)
    finally:
        http.close()
    assert captured.value.code == "ADMIN_RESPONSE_INVALID"


def test_save_and_delete_keep_closed_wire_and_original_results() -> None:
    data, calls, http = _boundary()
    try:
        saved = data.save(
            ReflectionsSectionSaveInputDTO(
                section="echoes",
                prompt_files_json=json.dumps({"WORKFLOW.md": "custom"}, ensure_ascii=False),
            ),
            "save-1",
            access_token=TOKEN,
        )
        deleted = data.delete(
            ReflectionsSectionInputDTO(section="echoes"),
            "delete-1",
            access_token=TOKEN,
        )
    finally:
        http.close()
    assert saved.saved is True and deleted.deleted is False
    assert [item.url.path.rsplit("/", 1)[-1] for item in calls if item.method == "POST"] == [
        SAVE_REFLECTIONS_SECTION_CONFIG.capability.name,
        DELETE_REFLECTIONS_SECTION_CONFIG.capability.name,
    ]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"section": "other", "prompt_files_json": '{"WORKFLOW.md":"custom"}'},
        {"section": "echoes", "prompt_files_json": "{}"},
        {"section": "echoes", "prompt_files_json": '{"unknown":"custom"}'},
        {"section": "echoes", "prompt_files_json": '{"WORKFLOW.md":" custom "}'},
        {"section": "echoes", "prompt_files_json": '{"WORKFLOW.md":1}'},
        {"section": "echoes", "prompt_files_json": '{"WORKFLOW.md":"custom"}', "actor_id": "7"},
    ],
)
def test_save_input_is_closed_and_postfiltered(kwargs) -> None:
    with pytest.raises(ValidationError):
        ReflectionsSectionSaveInputDTO(**kwargs)


def test_unknown_save_is_not_retried() -> None:
    data, calls, http = _boundary(lose=SAVE_REFLECTIONS_SECTION_CONFIG.capability.name)
    try:
        with pytest.raises(AdminDataError) as captured:
            data.save(
                ReflectionsSectionSaveInputDTO(
                    section="echoes",
                    prompt_files_json='{"WORKFLOW.md":"custom"}',
                ),
                "save-unknown",
                access_token=TOKEN,
            )
    finally:
        http.close()
    assert captured.value.request_id == "save-unknown" and captured.value.outcome_unknown
    assert sum(item.method == "POST" for item in calls) == 1


def test_missing_registered_operation_stops_after_capability_read() -> None:
    data, calls, http = _boundary(operations=REFLECTIONS_SECTION_CONFIG_OPERATIONS[:2])
    try:
        with pytest.raises(AdminDataError, match="ADMIN_CAPABILITY_UNAVAILABLE"):
            data.delete(
                ReflectionsSectionInputDTO(section="echoes"),
                "missing-delete",
                access_token=TOKEN,
            )
    finally:
        http.close()
    assert [item.method for item in calls] == ["GET"]
