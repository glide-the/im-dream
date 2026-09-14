# [Input] Actual atomic user-turn consumer, original text projection and synthetic HTTP responses.
# [Output] Lossless raw numeric/title, confirmation result and unknown-write contract checks.
# [Pos] Provider-free atomic user-turn consumer tests; Admin guard/transaction are not copied.
# [Sync] 2026-09-15: pin the actual command and preserve Python business JSON across the envelope.
from __future__ import annotations

import json

import httpx
import pytest
from pydantic import ValidationError

from services.admin_data import AdminDataClient, AdminDataConfig, AdminDataError
from services.admin_data.user_message_data import AdminUserMessageData, PERSIST_USER_MESSAGE, UserMessageInputDTO, user_message_input


def data_client(*, output=None):
    config = AdminDataConfig(base_url="https://admin.example", issuer="https://admin.example/api/auth", resource="https://dream.example/api", service_secret="s" * 32, service_client_id="dream-service")
    calls = []
    def handler(request):
        calls.append(request)
        request_id = request.headers["x-request-id"]
        if request.url.path.endswith("/capabilities"):
            value = {"version": "1", "auth": {"issuer": config.issuer, "jwks_uri": config.jwks_uri, "resource": config.resource, "algorithm": "ES256", "clients": {"browser": "dream-browser", "device": "dream-device"}, "scopes": ["dream:write"], "delegations": []},
                "schema_capabilities": [], "operations": [PERSIST_USER_MESSAGE.capability.model_dump()]}
        else:
            assert request.headers["authorization"] == "Bearer synthetic-delegation"
            if isinstance(output, Exception):
                raise output
            value = output or {"message_id": "message-1", "confirmation_preserved": False}
        return httpx.Response(200, json={"request_id": request_id, "data": value})
    client = AdminDataClient(config, client=httpx.Client(transport=httpx.MockTransport(handler)), operations=(PERSIST_USER_MESSAGE,))
    client.capabilities("capabilities-1")
    return AdminUserMessageData(client), calls


def test_raw_business_numbers_and_untruncated_unicode_title_cross_one_command():
    data, calls = data_client()
    text = "创作🙂" * 60
    parts = [{"type": "text", "text": text, "weight": -0.0, "whole_float": 1.0, "big": 9_007_199_254_740_993}]
    metadata = {"float": 1.0, "zero": -0.0, "big": 9_007_199_254_740_993}
    input_dto = user_message_input("thread-1", "message-1", parts, metadata)
    result = data.persist(input_dto, "persist-original", access_token="synthetic-delegation")
    assert result.message_id == "message-1"
    command = json.loads(calls[-1].content)
    assert command == {"request_id": "persist-original", "input": input_dto.model_dump()}
    assert command["input"]["title_candidate"] == text
    assert '"weight":-0.0' in command["input"]["parts_json"]
    assert '"whole_float":1.0' in command["input"]["parts_json"]
    assert '"big":9007199254740993' in command["input"]["metadata_json"]
    assert len(calls) == 2


def test_attachment_only_title_uses_existing_projection():
    input_dto = user_message_input("thread-1", "message-1", [{"type": "workspace-file", "fileName": "分镜.png", "workspacePath": "boards/分镜.png", "mimeType": "image/png"}], None)
    assert "Workspace file: 分镜.png" in input_dto.title_candidate
    assert "Path: boards/分镜.png" in input_dto.title_candidate
    assert input_dto.metadata_json is None


@pytest.mark.parametrize("field,value", [("parts_json", "{}"), ("parts_json", "[NaN]"), ("parts_json", "bad"), ("metadata_json", "[]"), ("metadata_json", "null")])
def test_raw_json_fields_reject_wrong_shapes(field, value):
    raw = {"thread_id": "thread-1", "message_id": "message-1", "parts_json": "[]", "metadata_json": None, "title_candidate": ""}
    with pytest.raises(ValidationError):
        UserMessageInputDTO(**{**raw, field: value})


def test_nullable_metadata_is_required():
    with pytest.raises(ValidationError):
        UserMessageInputDTO(thread_id="thread-1", message_id="message-1", parts_json="[]", title_candidate="")


@pytest.mark.parametrize("number", [float("nan"), float("inf"), -float("inf")])
def test_non_json_number_is_rejected_before_transport(number):
    with pytest.raises(AdminDataError, match="ADMIN_OPERATION_INPUT_INVALID"):
        user_message_input("thread-1", "message-1", [{"type": "text", "text": "private-content", "weight": number}], None)


def test_preserved_confirmation_result_does_not_trigger_another_write():
    data, calls = data_client(output={"message_id": "message-1", "confirmation_preserved": True})
    result = data.persist(user_message_input("thread-1", "message-1", [], None), "persist-original", access_token="synthetic-delegation")
    assert result.confirmation_preserved is True and len(calls) == 2


def test_wrong_reply_identity_remains_an_unknown_commit():
    data, calls = data_client(output={"message_id": "other", "confirmation_preserved": False})
    with pytest.raises(AdminDataError) as failure:
        data.persist(user_message_input("thread-1", "message-1", [], None), "persist-original", access_token="synthetic-delegation")
    assert failure.value.outcome_unknown and failure.value.request_id == "persist-original"
    assert len(calls) == 2


def test_lost_response_is_not_retried():
    data, calls = data_client(output=httpx.ReadTimeout("synthetic private diagnostic"))
    with pytest.raises(AdminDataError) as failure:
        data.persist(user_message_input("thread-1", "message-1", [], None), "persist-original", access_token="synthetic-delegation")
    assert failure.value.outcome_unknown and failure.value.request_id == "persist-original"
    assert "private" not in str(failure.value) and len(calls) == 2
