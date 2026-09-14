# [Input] Actual typed Chat consumers and exact Admin DTO candidates with injected transport.
# [Output] Named-wire, microsecond/nullable/JSON/final-projection and original-receipt checks without PG.
# [Pos] Provider-free technical contracts for the pending Thread/message production cutover.
# [Sync] 2026-09-14: reuse legacy projection function and validate all 14 typed operation schemas.

from __future__ import annotations

import json

import httpx
import pytest
from pydantic import ValidationError

from chat_message_projection import validate_chat_history_final_projection
from services.admin_data import AdminDataClient, AdminDataConfig, AdminDataError
from services.admin_data import chat_data as data
from services.admin_data import chat_models as dto


@pytest.fixture
def config():
    return AdminDataConfig(base_url="https://admin.example", issuer="https://admin.example/api/auth", resource="https://dream.example/api", service_secret="s" * 32, service_client_id="dream-web")


def client(config, handler):
    def transport(request):
        if request.url.path.endswith("/capabilities"):
            return httpx.Response(200, json={"request_id": request.headers["x-request-id"], "data": {
                "version": "1", "auth": {"issuer": config.issuer, "jwks_uri": config.jwks_uri, "algorithm": "ES256", "resource": config.resource, "clients": {"browser": "dream-browser", "device": "dream-device"}, "scopes": ["dream:read", "dream:write"], "delegations": []},
                "schema_capabilities": [], "operations": [operation.capability.model_dump() for operation in data.CHAT_OPERATIONS],
            }})
        return handler(request)
    result = AdminDataClient(config, client=httpx.Client(transport=httpx.MockTransport(transport)), operations=data.CHAT_OPERATIONS)
    result.capabilities("bootstrap")
    return result


CASES = [
    (data.CREATE_THREAD, "create_thread", {"deck_id": None, "voice_id": None, "title": None}, {"thread_id": "owned-thread", "deck_id": None, "voice_id": None}),
    (data.GET_THREAD, "get_thread", {"thread_id": "owned-thread"}, {"thread": None}),
    (data.LIST_THREADS, "list_threads", {"deck_id": None, "limit": None, "offset": 0}, {"threads": []}),
    (data.SEARCH_THREADS, "search_threads", {"deck_id": None}, {"threads": []}),
    (data.DELETE_THREAD, "delete_thread", {"thread_id": "owned-thread"}, {"changed": False}),
    (data.BIND_DECK, "bind_deck", {"thread_id": "owned-thread", "deck_id": "owned-deck"}, {"changed": False}),
    (data.SELECT_VOICE, "select_voice", {"thread_id": "owned-thread", "deck_id": "owned-deck", "voice_id": "owned-voice", "expected_voice_id": None}, {"changed": False}),
    (data.UPDATE_TITLE, "update_title", {"thread_id": "owned-thread", "title": ""}, {"changed": False}),
    (data.UPDATE_SESSION, "update_session", {"thread_id": "owned-thread", "claude_session_id": "current-transcript", "agent_contract_version": "current-contract"}, {"changed": False}),
    (data.PERSIST_MESSAGE, "persist_message", {"thread_id": "owned-thread", "message_id": "message-1", "role": "user", "parts": [], "metadata": None, "history_final_text": None, "history_process_available": False, "history_projection_version": None}, {"message_id": "message-1"}),
    (data.LIST_MESSAGES, "list_messages", {"thread_id": "owned-thread"}, {"messages": []}),
    (data.MESSAGE_PAGE, "message_page", {"thread_id": "owned-thread", "limit": 50, "before": {"id": "cursor-message", "created_at": "2026-09-14T00:00:00.000001Z"}}, {"messages": [], "has_more": False, "latest_message_id": None}),
    (data.PROCESS_DETAIL, "process_detail", {"thread_id": "owned-thread", "message_id": "message-1"}, {"message": None}),
    (data.LATEST_MESSAGE, "latest_message", {"thread_id": "owned-thread"}, {"message_id": None}),
]


@pytest.mark.parametrize("operation,method,input_value,output", CASES, ids=[case[0].capability.name for case in CASES])
def test_all_named_chat_consumers_use_exact_dto_and_explicit_actor(config, operation, method, input_value, output):
    seen = []
    def handler(request):
        seen.append(request)
        assert request.url.path.endswith("/operations/" + operation.capability.name)
        assert request.headers["authorization"] == "Bearer admin-actor-token"
        assert request.headers["X-Ink-Dream-Service"] == config.service_client_id
        assert json.loads(request.content) == {"request_id": "chat-request-1", "input": input_value}
        return httpx.Response(200, json={"request_id": "chat-request-1", "data": output})
    consumer = data.AdminChatData(client(config, handler))
    result = getattr(consumer, method)(operation.input_dto.model_validate(input_value), "chat-request-1", access_token="admin-actor-token")
    assert result.model_dump() == output and len(seen) == 1


@pytest.mark.parametrize("operation,method,input_value,output", CASES, ids=[case[0].capability.name for case in CASES])
def test_actor_id_override_is_not_a_domain_input(operation, method, input_value, output):
    with pytest.raises(ValidationError):
        operation.input_dto.model_validate({**input_value, "user_id": "42"})


def thread_value():
    return {"id": "owned-thread", "user_id": "9223372036854775807", "title": None, "deck_id": None, "voice_id": None, "claude_session_id": None, "agent_contract_version": None, "created_at": "2026-09-14T00:00:00.123456Z", "updated_at": None}


def test_microsecond_timestamps_and_nulls_are_preserved_without_date_conversion():
    value = thread_value()
    parsed = dto.ThreadResultDTO.model_validate({"thread": value})
    assert parsed.model_dump()["thread"] == value
    cursor = dto.MessageBeforeDTO(id="cursor", created_at=value["created_at"])
    assert cursor.created_at == "2026-09-14T00:00:00.123456Z"
    assert dto.MessageBeforeDTO(id="cursor", created_at=None).created_at is None


@pytest.mark.parametrize("field,value", [("user_id", 42), ("user_id", "9223372036854775808"), ("created_at", "2026-09-14T00:00:00"), ("created_at", "2026-02-29T00:00:00Z"), ("updated_at", "2026-09-14T00:00:00+24:00")])
def test_thread_decimal_and_time_contract_is_strict(field, value):
    record = thread_value(); record[field] = value
    with pytest.raises(ValidationError):
        dto.ChatThreadDTO.model_validate(record)


def projected_message_input():
    return {"thread_id": "owned-thread", "message_id": "message-1", "role": "assistant", "parts": [{"type": "reasoning", "text": "process"}, {"type": "text", "text": "final"}], "metadata": {"turnStatus": "completed", "turnId": "turn-1", "finalPartIndex": 1}, "history_final_text": "final", "history_process_available": True, "history_projection_version": 1}


def test_projection_dto_calls_the_same_production_validator_as_legacy_persistence():
    import database
    assert database._validate_chat_history_final_projection is validate_chat_history_final_projection
    assert dto.MessagePersistInputDTO.model_validate(projected_message_input()).history_final_text == "final"


@pytest.mark.parametrize("mutation", [
    lambda value: value.update(history_projection_version=True),
    lambda value: value.update(history_final_text="different"),
    lambda value: value.update(history_process_available=False),
    lambda value: value["metadata"].update(finalPartIndex=True),
    lambda value: value["metadata"].update(turnStatus="failed"),
    lambda value: value["parts"].append({"type": "text", "text": "extra"}),
])
def test_projection_validation_retains_existing_failure_conditions(mutation):
    value = projected_message_input(); mutation(value)
    with pytest.raises(ValidationError):
        dto.MessagePersistInputDTO.model_validate(value)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), object()])
def test_chat_json_cannot_canonicalize_non_json_values(value):
    record = dict(CASES[9][2]); record["parts"] = [value]
    with pytest.raises(ValidationError):
        dto.MessagePersistInputDTO.model_validate(record)


@pytest.mark.parametrize("status", [403, 409, 503])
def test_chat_denied_conflict_unavailable_preserve_status_without_retry(config, status):
    seen = []
    def handler(request):
        seen.append(request)
        return httpx.Response(status, json={"request_id": "original-write", "error": {"code": "CHAT_DOMAIN_FAILURE", "message": "private content"}})
    consumer = data.AdminChatData(client(config, handler))
    with pytest.raises(AdminDataError) as failure:
        consumer.persist_message(dto.MessagePersistInputDTO.model_validate(CASES[9][2]), "original-write", access_token="admin-actor-token")
    assert failure.value.status_code == status and len(seen) == 1
    assert "private content" not in str(failure.value)


def test_unknown_chat_write_only_recovers_original_receipt(config):
    seen = []
    def handler(request):
        seen.append(request)
        if "/operations/" in request.url.path:
            raise httpx.ReadTimeout("private endpoint", request=request)
        assert request.url.path.endswith("/receipts/original-write")
        assert request.url.params["operation"] == "chat-message.persist"
        return httpx.Response(200, json={"request_id": "original-write", "data": {"status": "committed", "operation": "chat-message.persist", "request_id": "original-write", "result": {"message_id": "message-1"}}})
    transport = client(config, handler)
    with pytest.raises(AdminDataError) as failure:
        data.AdminChatData(transport).persist_message(dto.MessagePersistInputDTO.model_validate(CASES[9][2]), "original-write", access_token="entity-limited-grant")
    assert failure.value.outcome_unknown
    receipt = transport.receipt(data.PERSIST_MESSAGE, "original-write", access_token="entity-limited-grant")
    assert receipt.result.message_id == "message-1" and len(seen) == 2


def test_persist_result_must_match_the_explicit_message_identity(config):
    transport = client(config, lambda _: httpx.Response(200, json={"request_id": "original-write", "data": {"message_id": "different-message"}}))
    with pytest.raises(AdminDataError) as failure:
        data.AdminChatData(transport).persist_message(dto.MessagePersistInputDTO.model_validate(CASES[9][2]), "original-write", access_token="admin-actor-token")
    assert failure.value.outcome_unknown and failure.value.code == "ADMIN_RESPONSE_INVALID"
