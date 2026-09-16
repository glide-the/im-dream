# [Input] Registry121 capability, claim-turn response and claim-bound idg grant.
# [Output] Strict Pydantic grant recovery plus Workflow/Deck/AdminTurnPersistence composition.
# [Pos] Provider-free Dream consumer contract; no PostgreSQL, Runtime or shared-file fixture.
# [Sync] 2026-09-17: prove confirmation claim uses service OAuth before claim-bound delegation.
from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hashlib
import json

import httpx
import pytest

from services.admin_data import AdminDataClient, AdminDataConfig, AdminDataError
from services.admin_data.deck_chat_context_data import RESOLVE_DECK_CHAT_CONTEXT
from services.admin_data.delegation import RuntimeHttpConfig
from services.admin_data.session_projection_broker import SessionProjectionBrokerSettings
from services.admin_data.story_workspace_confirmation_data import (
    CLAIM_STORY_WORKSPACE_CONFIRMATION_TURN,
    CONFIRMATION_TURN_SCHEMA_REQUIREMENT,
    AdminStoryWorkspaceConfirmationWorkerData,
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
        "capabilities",
        "workflow-context.resolve",
        "capabilities",
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
