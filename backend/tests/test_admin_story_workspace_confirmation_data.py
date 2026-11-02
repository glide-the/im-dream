# [Input] Registry121 capability, claim-turn response and claim-bound idg grant.
# [Output] Strict Pydantic grant recovery plus Workflow/Deck/AdminTurnPersistence composition.
# [Pos] Provider-free Dream consumer contract; no PostgreSQL, Runtime or shared-file fixture.
# [Sync] 2026-10-26: validate OAuth pending-message recovery against exact actor/Thread/Run, durable command hashes and terminal ACK.
# [Sync] 2026-09-17: prove confirmation claim uses service OAuth before claim-bound delegation.
from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hashlib
import json
from unittest.mock import Mock

import httpx
import pytest

from services.admin_data import AdminDataClient, AdminDataConfig, AdminDataError
from services.admin_data.deck_chat_context_data import RESOLVE_DECK_CHAT_CONTEXT
from services.admin_data.chat_data import LIST_MESSAGES
from services.admin_data.chat_models import ChatMessageDTO, MessageListResultDTO
from services.admin_data.delegation import RuntimeHttpConfig
from services.admin_data.session_projection_broker import SessionProjectionBrokerSettings
from services.admin_data.story_workspace_confirmation_data import (
    CLAIM_STORY_WORKSPACE_CONFIRMATION_TURN,
    CONFIRMATION_TURN_SCHEMA_REQUIREMENT,
    AdminStoryWorkspaceConfirmationWorkerData,
    AdminStoryWorkspaceConfirmationData,
    StoryWorkspaceConfirmationClaimInputDTO,
)
from services.admin_data.turn_persistence import AdminTurnPersistence
from services.admin_data.workflow_data import (
    RESOLVE_WORKFLOW_CONTEXT,
    WORKFLOW_SCHEMA_REQUIREMENTS,
)


NOW = datetime(2026, 9, 16, 1, 0, tzinfo=UTC)
ACTOR = "42"
THREAD = "thread-confirmation"
RUN = "run_" + "a" * 32
MESSAGE = "dream_confirm_" + "b" * 64
CLAIM = "claim-confirmation-1"
TOKEN = "idg_" + "c" * 43


def canonical(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def dispatch_value() -> dict:
    command = {
        "storyWorkspaceRunId": RUN,
        "threadId": THREAD,
        "baseRevisions": {"characters": 1, "scenes": 1, "storyboards": 1},
        "edits": [],
        "idempotencyKey": "swc_claim-turn",
    }
    fingerprint = "sha256:" + hashlib.sha256(
        canonical({"actor": ACTOR, "command": command}).encode()
    ).hexdigest()
    expected_message = "dream_confirm_" + hashlib.sha256(
        canonical({
            "actor": ACTOR,
            "storyWorkspaceRunId": RUN,
            "idempotencyKey": "swc_claim-turn",
        }).encode()
    ).hexdigest()
    assert expected_message != MESSAGE
    metadata = {
        "kind": "story-workspace-dream-confirmation",
        "actor": ACTOR,
        "story_workspace_run_id": RUN,
        "thread_id": THREAD,
        "base_revisions": command["baseRevisions"],
        "edit_count": 0,
        "command_fingerprint": fingerprint,
        "idempotency_key": "swc_claim-turn",
        "request_id": "request-submit",
        "dispatch_status": "dispatching",
        "dispatch_claim_id": CLAIM,
        "dispatch_claim_lease_until": NOW.timestamp() + 120,
    }
    return {
        "thread_id": THREAD,
        "actor_id": ACTOR,
        "message_id": expected_message,
        "parts_json": canonical([{
            "type": "text",
            "text": canonical({
                "kind": "story-workspace-dream-confirmation",
                "instruction": "continue",
                "command": command,
            }),
        }]),
        "metadata_json": canonical(metadata),
    }


def worker(*, include_claim_capability: bool = True):
    config = AdminDataConfig(
        base_url="https://admin.example",
        issuer="https://admin.example/api/auth",
        resource="https://dream.example/api",
        service_secret="s" * 32,
        service_client_id="dream-service",
    )
    calls = []
    dispatch = dispatch_value()
    schemas = [item.model_dump() for item in WORKFLOW_SCHEMA_REQUIREMENTS]
    if include_claim_capability:
        schemas.append(CONFIRMATION_TURN_SCHEMA_REQUIREMENT.model_dump())

    def handler(request: httpx.Request):
        calls.append(request)
        request_id = request.headers["x-request-id"]
        if request.url.path.endswith("/capabilities"):
            data = {
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
                "schema_capabilities": schemas,
                "operations": [
                    CLAIM_STORY_WORKSPACE_CONFIRMATION_TURN.capability.model_dump(),
                    RESOLVE_WORKFLOW_CONTEXT.capability.model_dump(),
                    RESOLVE_DECK_CHAT_CONTEXT.capability.model_dump(),
                ],
            }
        elif request.url.path.endswith("story-workspace-confirmation.claim-turn"):
            assert request.headers["authorization"] == "Bearer fixture.service.access.token"
            assert "x-ink-dream-service-authorization" not in request.headers
            data = {
                "dispatch": dispatch,
                "authority": {
                    "token": TOKEN,
                    "expires_at": (NOW + timedelta(minutes=5)).isoformat(),
                    "maximum_expires_at": (NOW + timedelta(minutes=30)).isoformat(),
                    "purpose": "server-persistence",
                    "thread_id": THREAD,
                    "run_id": RUN,
                    "editor_session_id": None,
                    "scopes": ["dream:read", "dream:write"],
                },
            }
        elif request.url.path.endswith("workflow-context.resolve"):
            assert request.headers["authorization"] == "Bearer " + TOKEN
            data = {"context": {
                "workflow_run_id": RUN,
                "thread_id": THREAD,
                "deck_id": "deck-1",
                "agent_id": None,
                "deck_plugin_id": "plugin-1",
                "deck_plugin_version": "1.0.0",
                "deck_plugin_binding_id": "binding-1",
                "binding_revision": 1,
                "deck_runtime_snapshot_id": "snapshot-1",
                "runtime_plugin_lock_id": "lock-1",
            }}
        else:
            assert request.url.path.endswith("deck-chat-context.resolve")
            assert request.headers["authorization"] == "Bearer " + TOKEN
            data = {
                "deck": {
                    "id": "deck-1", "name": "Story", "name_zh": None,
                    "name_en": None, "description": None,
                    "description_zh": None, "description_en": None,
                    "enabled": True,
                },
                "voices": [],
                "plugin_refs": [],
            }
        return httpx.Response(200, json={"request_id": request_id, "data": data})

    client = AdminDataClient(
        config,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        operations=(
            CLAIM_STORY_WORKSPACE_CONFIRMATION_TURN,
            RESOLVE_WORKFLOW_CONTEXT,
            RESOLVE_DECK_CHAT_CONTEXT,
        ),
    )
    return AdminStoryWorkspaceConfirmationWorkerData(
        client,
        runtime_http_config=RuntimeHttpConfig.from_server_config(config),
        session_broker_settings=SessionProjectionBrokerSettings(
            timeout_seconds=10.0,
            max_bytes=1_048_576,
        ),
        clock=lambda: NOW,
    ), calls, dispatch


def test_claim_turn_builds_one_exact_admin_turn_owner() -> None:
    consumer, calls, dispatch = worker()
    claim = consumer.claim_turn(
        StoryWorkspaceConfirmationClaimInputDTO(
            message_id=dispatch["message_id"],
            claim_id=CLAIM,
        ),
        "request-claim",
    )
    assert claim is not None
    assert claim.grant.token == TOKEN
    owner = consumer.turn_owner(claim, "request-owner")
    assert isinstance(owner.persistence, AdminTurnPersistence)
    assert owner.workflow.context is not None
    assert owner.workflow.context.workflow_run_id == RUN
    assert owner.deck.deck_id == "deck-1"
    assert [request.url.path.rsplit("/", 1)[-1] for request in calls] == [
        "capabilities",
        "story-workspace-confirmation.claim-turn",
        "workflow-context.resolve",
        "deck-chat-context.resolve",
    ]


def test_claim_turn_fails_closed_without_exact_schema_capability() -> None:
    consumer, calls, dispatch = worker(include_claim_capability=False)
    with pytest.raises(AdminDataError, match="ADMIN_CAPABILITY_UNAVAILABLE"):
        consumer.claim_turn(
            StoryWorkspaceConfirmationClaimInputDTO(
                message_id=dispatch["message_id"],
                claim_id=CLAIM,
            ),
            "request-claim",
        )
    assert [request.url.path.rsplit("/", 1)[-1] for request in calls] == [
        "capabilities"
    ]
# [Sync] 2026-09-17: verify confirmation owner composition reuses one validated capability snapshot.


def pending_message():
    value = dispatch_value()
    metadata = json.loads(value["metadata_json"])
    return ChatMessageDTO(
        id=value["message_id"], role="user", parts=json.loads(value["parts_json"]),
        metadata=metadata, metadata_decode_error=False, created_at=None,
        history_final_text=None, history_process_available=False, history_projection_version=None,
    )


def confirmation_reader(messages):
    client = Mock()
    client.execute.return_value = MessageListResultDTO(messages=messages)
    return AdminStoryWorkspaceConfirmationData(client, canonical_user_id=ACTOR), client


def test_pending_read_uses_original_oauth_chat_operation_and_stored_command():
    message = pending_message()
    consumer, client = confirmation_reader([message])
    result = consumer.pending_dispatch(RUN, THREAD, "read-pending", access_token="user-oauth")
    operation, input_dto, request_id = client.execute.call_args.args
    assert operation is LIST_MESSAGES
    assert input_dto.thread_id == THREAD
    assert request_id == "read-pending"
    assert client.execute.call_args.kwargs == {"access_token": "user-oauth"}
    assert result.message_id == message.id
    assert result.thread_id == THREAD
    assert result.actor_id == ACTOR
    assert json.loads(result.parts_json) == message.parts
    assert json.loads(result.metadata_json) == message.metadata
    assert client.execute.call_count == 1


@pytest.mark.parametrize("change", ["actor", "thread", "parts", "message", "role", "decode", "claim"])
def test_pending_read_rejects_mismatched_or_malformed_confirmation(change):
    value = pending_message().model_dump()
    if change == "actor":
        value["metadata"]["actor"] = "43"
    elif change == "thread":
        value["metadata"]["thread_id"] = "another-thread"
    elif change == "parts":
        value["parts"][0]["text"] = "{}"
    elif change == "message":
        value["id"] = MESSAGE
    elif change == "role":
        value["role"] = "assistant"
    elif change == "decode":
        value["metadata_decode_error"] = True
    elif change == "claim":
        value["metadata"].pop("dispatch_claim_id")
    consumer, _ = confirmation_reader([ChatMessageDTO.model_validate(value)])
    with pytest.raises(AdminDataError) as raised:
        consumer.pending_dispatch(RUN, THREAD, "read-pending", access_token="user-oauth")
    assert raised.value.outcome_unknown is False


def test_pending_read_rejects_ambiguous_commands_and_keeps_other_runs_scoped():
    message = pending_message()
    consumer, _ = confirmation_reader([message, message])
    with pytest.raises(AdminDataError):
        consumer.pending_dispatch(RUN, THREAD, "read-pending", access_token="user-oauth")
    consumer, _ = confirmation_reader([message])
    assert consumer.pending_dispatch("run_" + "d" * 32, THREAD, "read-other", access_token="user-oauth") is None


def test_pending_read_never_replays_an_acknowledged_confirmation():
    message = pending_message()
    message.metadata.update(dispatch_status="dispatched", dispatch_ack_claim_sha256="sha256:" + "d" * 64)
    message.metadata.pop("dispatch_claim_id")
    message.metadata.pop("dispatch_claim_lease_until")
    consumer, _ = confirmation_reader([message])
    assert consumer.pending_dispatch(RUN, THREAD, "read-pending", access_token="user-oauth") is None


def test_pending_read_preserves_admin_denial_without_service_fallback():
    consumer, client = confirmation_reader([])
    client.execute.side_effect = AdminDataError("ADMIN_FORBIDDEN", 403, "read-pending")
    with pytest.raises(AdminDataError, match="ADMIN_FORBIDDEN"):
        consumer.pending_dispatch(RUN, THREAD, "read-pending", access_token="user-oauth")
    assert client.execute.call_count == 1
