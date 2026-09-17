# [Sync] 2026-09-16: validate Registry169 settlement on the shared unknown-write barrier.
# [Sync] 2026-09-15: validate Registry109 strict DTO, exact grant and unknown original receipt recovery.
# [Sync] 2026-09-16: authorize injected managed-MCP loaders with the current persistence grant in tests.
# [Sync] 2026-09-16: verify the Notion adapter receives the exact actor, Thread, Run and current grant.
# [Input] Actual server persistence holder, synthetic DTO transport and explicitly controlled clock/threads.
# [Output] Entity scope, recent Session reads, original-ID recovery and shutdown drain evidence.
# [Pos] Provider-free turn lifecycle tests; no PG/model/real service or alternate SSE implementation.
# [Sync] 2026-09-15: validate Thread/SDK Session scope, native init callbacks and one cross-operation unknown barrier.
# [Sync] 2026-09-15: validate server-only persistence authority and short-lock current snapshots.
# [Sync] 2026-09-15: validate assistant full/partial DTOs, four schemas and shared pending barrier.
# [Sync] 2026-09-15: validate Editor broker ownership beside the existing grant lifecycle.
# [Sync] 2026-09-15: validate Thread SystemConfig uses the same exact draining grant.
# [Sync] 2026-09-15: validate exact UTC recent Session projection and close drain.
# [Sync] 2026-09-15: validate the owner-bound broker provider, renewed grant and arbitrary strict ranges.
# [Sync] 2026-09-15: validate Registry108 activation and shared unknown-write recovery on the exact grant.
# [Sync] 2026-09-16: validate selector-free current WorkflowRun projection through Admin scope/read DTOs.
from __future__ import annotations

import asyncio
from contextlib import nullcontext
import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from threading import Event, Thread
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from services.admin_data import AdminDataClient, AdminDataConfig, AdminDataError
from services.admin_data.chat_data import GET_THREAD, PERSIST_MESSAGE, UPDATE_SESSION
from services.admin_data.delegation import RuntimeGrant
from services.admin_data.delegation_keeper import RuntimeGrantKeeper
from services.admin_data.session_data import (
    LIST_SESSIONS,
    SESSION_LIST_SCHEMA_REQUIREMENTS,
)
from services.admin_data.session_models import SessionListInputDTO
from services.admin_data.session_projection_broker import SessionProjectionBrokerSettings
from services.admin_data.run_data import READ_RUN
from services.admin_data.turn_persistence import AdminTurnPersistence
from services.admin_data.user_message_data import PERSIST_USER_MESSAGE
from services.admin_data.workflow_data import AdminWorkflowResolution
from services.admin_data.workspace_data import WORKSPACE_SCHEMA_REQUIREMENTS
from services.admin_data.system_config_data import GET_THREAD_SYSTEM_CONFIG
from services.admin_data.deck_workspace_plugins_data import (
    RESOLVE_DECK_WORKSPACE_PLUGINS,
)
from services.admin_data.workflow_managed_mcp_scope_data import (
    RESOLVE_WORKFLOW_MANAGED_MCP_SCOPE,
)
from services.admin_data.workflow_runtime_activation_data import (
    ACTIVATE_WORKFLOW_RUNTIME,
    WORKFLOW_RUNTIME_ACTIVATION_SCHEMA_REQUIREMENTS,
)
from services.admin_data.story_workspace_output_data import (
    STORE_STORY_WORKSPACE_OUTPUT,
    STORY_WORKSPACE_OUTPUT_OPERATIONS,
)
from services.admin_data.dream_auto_repair_data import (
    DREAM_AUTO_REPAIR_OPERATIONS,
    SETTLE_DREAM_AUTO_REPAIR,
    DreamAutoRepairIdentityDTO,
)
from story_workspace.contracts import StoryWorkspaceDreamRunContext

NOW = datetime(2026, 9, 15, tzinfo=timezone.utc)
TOKEN = "idg_" + "a" * 43


def grant(run_id=None):
    return RuntimeGrant(TOKEN, "server-persistence", "thread-1", run_id, None,
        ("dream:read", "dream:write"), NOW + timedelta(seconds=100), NOW + timedelta(hours=2))


def holder(*, lose_response=False, lose_operation=None, block=None, thread_patch=None,
    schema_fault=None, assistant_patch=None, session_rows=None, expected_token=TOKEN,
    workflow_context=None, run_patch=None):
    config = AdminDataConfig(base_url="https://admin.example", issuer="https://admin.example/api/auth", resource="https://dream.example/api", service_secret="s" * 32, service_client_id="dream-service")
    calls, receipt_states = [], ["absent", "committed"]
    thread_row = {"id": "thread-1", "user_id": "42", "title": None, "deck_id": None, "voice_id": None,
        "created_at": None, "updated_at": None, "claude_session_id": None, "agent_contract_version": None, **(thread_patch or {})}
    operations = (PERSIST_USER_MESSAGE, GET_THREAD, UPDATE_SESSION, PERSIST_MESSAGE,
        GET_THREAD_SYSTEM_CONFIG, LIST_SESSIONS, RESOLVE_DECK_WORKSPACE_PLUGINS,
        RESOLVE_WORKFLOW_MANAGED_MCP_SCOPE, READ_RUN, ACTIVATE_WORKFLOW_RUNTIME,
        *STORY_WORKSPACE_OUTPUT_OPERATIONS, *DREAM_AUTO_REPAIR_OPERATIONS)
    schema_requirements = {
        item.capability: item
        for item in (
            *WORKSPACE_SCHEMA_REQUIREMENTS,
            *SESSION_LIST_SCHEMA_REQUIREMENTS,
            *WORKFLOW_RUNTIME_ACTIVATION_SCHEMA_REQUIREMENTS,
        )
    }
    schemas = [item.model_dump() for item in schema_requirements.values()]
    if schema_fault == "missing": schemas.pop(len(WORKSPACE_SCHEMA_REQUIREMENTS) - 1)
    elif schema_fault == "duplicate": schemas.append(dict(schemas[0]))
    elif isinstance(schema_fault, int): schemas[schema_fault]["contract_sha256"] = "0" * 64
    def transport(request):
        request_id = request.headers["x-request-id"]
        calls.append(request)
        if request.url.path.endswith("/capabilities"):
            value = {"version": "1", "auth": {"issuer": config.issuer, "jwks_uri": config.jwks_uri, "resource": config.resource, "algorithm": "ES256", "clients": {"browser": "dream-browser", "device": "dream-device"}, "scopes": ["dream:read", "dream:write"], "delegations": []}, "schema_capabilities": schemas, "operations": [item.capability.model_dump() for item in operations]}
        elif "/receipts/" in request.url.path:
            assert request_id == "write-original"
            state = receipt_states.pop(0)
            operation = request.url.params["operation"]
            value = {"status": state, "request_id": request_id, "operation": operation}
            if state == "committed":
                if operation == UPDATE_SESSION.capability.name:
                    value["result"] = {"changed": True}
                elif operation == PERSIST_MESSAGE.capability.name:
                    value["result"] = {"message_id": "message-1"}
                elif operation == STORE_STORY_WORKSPACE_OUTPUT.capability.name:
                    value["result"] = {
                        "story_id": "story-1", "review_status": "pending",
                        "character_ids": [], "scene_ids": [],
                        "chat_thread_id": "thread-1", "deck_id": None,
                        "deck_name": None, "deck_name_zh": None, "deck_name_en": None,
                    }
                elif operation == SETTLE_DREAM_AUTO_REPAIR.capability.name:
                    value["result"] = {
                        "message_id": "dream_repair_" + "c" * 40,
                        "status": "dispatched",
                        "changed": True,
                    }
                elif operation == ACTIVATE_WORKFLOW_RUNTIME.capability.name:
                    value["result"] = {
                        "thread_id": "thread-1",
                        "workflow_run_id": workflow_context.workflow_run_id,
                        "workspace_id": "workspace-1",
                        "runtime_plugin_lock_id": workflow_context.runtime_plugin_lock_id,
                        "runtime_load_receipt_id": "rlr_" + "b" * 32,
                        "agent_session_id": "as_" + "c" * 32,
                        "status": "running",
                        "replayed": False,
                    }
                else:
                    value["result"] = {"message_id": "message-1", "confirmation_preserved": False}
        else:
            assert request.headers["authorization"] == "Bearer " + expected_token
            assert request_id in {"write-original", "broker-request"}
            if block is not None:
                entered, release = block
                entered.set()
                assert release.wait(2), "Owned HTTP fixture did not release"
            name = request.url.path.rsplit("/", 1)[-1]
            input_dto = json.loads(request.content)["input"]
            if name == GET_THREAD.capability.name:
                value = {"thread": thread_row}
            elif name == GET_THREAD_SYSTEM_CONFIG.capability.name:
                assert input_dto == {"thread_id": "thread-1"}
                value = {"config_json": '{"workspace_enabled":true}'}
            elif name == LIST_SESSIONS.capability.name:
                assert set(input_dto) == {"start_date", "end_date", "include_text"}
                value = {"sessions": session_rows or []}
            elif name == RESOLVE_DECK_WORKSPACE_PLUGINS.capability.name:
                assert input_dto == {
                    "thread_id": "thread-1",
                    "profile": "standard",
                }
                value = {
                    "thread_id": "thread-1",
                    "deck_id": "deck-1",
                    "refs": [],
                    "story_workspace_adapter": None,
                }
            elif name == RESOLVE_WORKFLOW_MANAGED_MCP_SCOPE.capability.name:
                assert input_dto == {
                    "thread_id": "thread-1",
                    "workflow_run_id": workflow_context.workflow_run_id,
                }
                value = {
                    **input_dto,
                    "workspace_id": "workspace-1",
                }
            elif name == READ_RUN.capability.name:
                assert input_dto == {
                    "workspace_id": "workspace-1",
                    "workflow_run_id": workflow_context.workflow_run_id,
                }
                value = {
                    "run": {
                        "workflow_run_id": workflow_context.workflow_run_id,
                        "deck_plugin_id": workflow_context.deck_plugin_id,
                        "deck_plugin_version": workflow_context.deck_plugin_version,
                        "workflow_definition_ref": "workflow-1",
                        "deck_runtime_snapshot_id": workflow_context.deck_runtime_snapshot_id,
                        "status": "preflight",
                        "failed_step": None,
                        "error_code": None,
                        "retry_of_run_id": None,
                        "deck_plugin_manifest_hash": "sha256:" + "1" * 64,
                        "deck_plugin_binding_id": workflow_context.deck_plugin_binding_id,
                        "binding_revision": workflow_context.binding_revision,
                        "runtime_plugin_lock_id": workflow_context.runtime_plugin_lock_id,
                        "runtime_load_receipt_id": None,
                        "workflow_preflight_id": "pf_" + "2" * 32,
                        "agent_session_id": None,
                        "source_voice_thread_id": "thread-1",
                        "source_message_id": "message-1",
                        "source_message_time": "2026-09-15T08:00:00Z",
                        "workspace_id": "workspace-1",
                        "idempotency_key": "run-request-1",
                        "input_hash": "sha256:" + "3" * 64,
                        "semantic_fingerprint": "sha256:" + "4" * 64,
                        "status_version": 1,
                        "created_by": "42",
                        "created_at": "2026-09-15T08:00:00Z",
                        "started_at": None,
                        "completed_at": None,
                        **(run_patch or {}),
                    }
                }
            elif name == STORE_STORY_WORKSPACE_OUTPUT.capability.name:
                assert input_dto == {
                    "thread_id": "thread-1",
                    "story": {
                        "title": "标题", "description": None, "type": "short",
                        "content": None, "characters": [], "scenes": [],
                    },
                }
                value = {
                    "story_id": "story-1", "review_status": "pending",
                    "character_ids": [], "scene_ids": [],
                    "chat_thread_id": "thread-1", "deck_id": None,
                    "deck_name": None, "deck_name_zh": None, "deck_name_en": None,
                }
            elif name == SETTLE_DREAM_AUTO_REPAIR.capability.name:
                assert input_dto == {
                    "thread_id": "thread-1",
                    "message_id": "dream_repair_" + "c" * 40,
                    "expected_identity": {
                        "kind": "story-workspace-dream-auto-repair",
                        "schema_version": "story-workspace-dream-auto-repair/v1",
                        "originating_message_id": "message-origin",
                        "originating_turn_id": "turn-origin",
                        "workflow_run_id": workflow_context.workflow_run_id,
                        "repair_attempt": 1,
                        "validation_code": "PROJECT_STORY_SLUG_MISMATCH",
                        "idempotency_key": "dream-auto-repair/v1:" + "b" * 64,
                        "project_cleanup": {
                            "trusted_project_slug": "server-project",
                            "stale_project_slugs": ["workspace-project"],
                        },
                    },
                    "status": "dispatched",
                }
                value = {
                    "message_id": input_dto["message_id"],
                    "status": input_dto["status"],
                    "changed": True,
                }
            elif name == ACTIVATE_WORKFLOW_RUNTIME.capability.name:
                assert input_dto == {
                    "thread_id": "thread-1",
                    "workflow_run_id": workflow_context.workflow_run_id,
                    "remote_session_ref": "sdk-thread",
                    "verified_plugins": [
                        {
                            "package_spec": "ink-dream-story@platform-builtin",
                            "resolved_version": "1.0.0",
                            "artifact_digest": "sha256:" + "a" * 64,
                            "has_manifest": True,
                        }
                    ],
                }
                value = {
                    "thread_id": "thread-1",
                    "workflow_run_id": workflow_context.workflow_run_id,
                    "workspace_id": "workspace-1",
                    "runtime_plugin_lock_id": workflow_context.runtime_plugin_lock_id,
                    "runtime_load_receipt_id": "rlr_" + "b" * 32,
                    "agent_session_id": "as_" + "c" * 32,
                    "status": "running",
                    "replayed": False,
                }
            elif name == UPDATE_SESSION.capability.name:
                thread_row.update(claude_session_id=input_dto["claude_session_id"], agent_contract_version=input_dto["agent_contract_version"])
                value = {"changed": True}
            elif name == PERSIST_MESSAGE.capability.name:
                value = {"message_id": input_dto["message_id"], **(assistant_patch or {})}
            else:
                value = {"message_id": input_dto["message_id"], "confirmation_preserved": False}
            if lose_response or name == lose_operation:
                raise httpx.ReadTimeout("synthetic private body")
        return httpx.Response(200, json={"request_id": request_id, "data": value})
    client = AdminDataClient(config, client=httpx.Client(transport=httpx.MockTransport(transport)), operations=operations)
    client.capabilities("capabilities-1")
    runtime = SimpleNamespace(closed=[], renew=lambda value, request_id: value, receipt=lambda *args: None)
    runtime.close = lambda: runtime.closed.append(True)
    value = AdminTurnPersistence(AdminWorkflowResolution("42", "thread-1", workflow_context), grant(
        workflow_context.workflow_run_id if workflow_context is not None else None
    ), client,
        runtime_client_factory=lambda: runtime, clock=lambda: NOW, request_id_factory=lambda: "write-original",
        session_broker_settings=SessionProjectionBrokerSettings(timeout_seconds=0.5, max_bytes=4096))
    return value, calls, runtime


def persist(value, *, message_id="message-1", text="original"):
    return value.persist_user(actor_id="42", thread_id="thread-1", message_id=message_id,
        parts=[{"type": "text", "text": text}], metadata=None)


def test_known_public_reservation_is_reused_without_another_write():
    value, calls, _ = holder()
    first = persist(value)
    assert persist(value) is first
    assert len(calls) == 2
    with pytest.raises(AdminDataError, match="CHAT_MESSAGE_IDENTITY_CONFLICT"):
        persist(value, text="changed")
    assert len(calls) == 2


@pytest.mark.parametrize("actor,thread", [("43", "thread-1"), ("42", "other")])
def test_holder_rejects_other_actor_or_thread_before_data_access(actor, thread):
    value, calls, _ = holder()
    with pytest.raises(AdminDataError, match="DREAM_DELEGATION_ENTITY_DENIED"):
        value.current_grant(actor_id=actor, thread_id=thread)
    assert len(calls) == 1


def test_notion_store_binds_the_current_actor_thread_and_optional_run():
    workflow_context = _dream_context()
    value, calls, _ = holder(workflow_context=workflow_context)

    store = value.notion_connector_store(actor_id="42", thread_id="thread-1")

    assert store._expected_user_id == "42"
    assert store._authority.model_dump() == {
        "thread_id": "thread-1",
        "workflow_run_id": workflow_context.workflow_run_id,
    }
    assert store._access_token == TOKEN
    assert len(calls) == 1

    with pytest.raises(AdminDataError, match="DREAM_DELEGATION_ENTITY_DENIED"):
        value.notion_connector_store(actor_id="43", thread_id="thread-1")
    assert len(calls) == 1


@pytest.mark.parametrize("change", [{"purpose": "gateway-cli", "scopes": ("models:list",)}, {"run_id": "run_" + "a" * 32}, {"thread_id": "other"}, {"scopes": ("dream:write",)}])
def test_server_holder_cannot_accept_wrong_purpose_or_frozen_entities(change):
    value, _, _ = holder()
    with pytest.raises(AdminDataError, match="ADMIN_CONFIGURATION_INVALID"):
        AdminTurnPersistence(AdminWorkflowResolution("42", "thread-1", None), replace(grant(), **change), value._client,
            runtime_client_factory=lambda: None, clock=lambda: NOW,
            session_broker_settings=SessionProjectionBrokerSettings(timeout_seconds=0.5, max_bytes=4096))


def test_unknown_write_keeps_original_id_and_recovers_receipt_without_post_retry():
    value, calls, _ = holder(lose_response=True)
    with pytest.raises(AdminDataError) as lost:
        persist(value)
    assert lost.value.outcome_unknown and lost.value.request_id == "write-original"
    with pytest.raises(AdminDataError, match="ADMIN_WRITE_RESULT_UNKNOWN"):
        persist(value, message_id="other")
    assert len(calls) == 2
    with pytest.raises(AdminDataError, match="ADMIN_WRITE_RESULT_UNKNOWN"):
        persist(value)
    result = persist(value)
    assert result.message_id == "message-1" and persist(value) is result
    assert sum(request.method == "POST" for request in calls) == 1
    assert [request.url.path.rsplit("/", 1)[1] for request in calls[-2:]] == ["write-original", "write-original"]


def test_factory_owned_start_and_close_stop_the_only_renewal_client():
    value, calls, runtime = holder()
    value.start()
    value.start()
    value.close()
    assert value._keeper.diagnostics().stopped and not value._keeper._thread.is_alive()
    assert runtime.closed == [True] and len(calls) == 1
    with pytest.raises(AdminDataError, match="DELEGATION_EXPIRED"):
        persist(value)


def test_close_drains_already_dispatched_writer_without_new_commands():
    entered, release, closed = Event(), Event(), Event()
    value, calls, _ = holder(block=(entered, release))
    errors = []
    def write():
        try:
            persist(value)
        except Exception as error:
            errors.append(error)
    worker = Thread(target=write)
    closer = Thread(target=lambda: (value.close(), closed.set()))
    worker.start()
    try:
        assert entered.wait(1)
        closer.start()
        assert not closed.wait(0.05)
    finally:
        release.set()
        worker.join(2)
        if closer.ident is not None:
            closer.join(2)
    assert closed.is_set() and not errors and len(calls) == 2


def test_current_snapshot_does_not_wait_for_renewal_http():
    entered, release, projected = Event(), Event(), Event()
    now = [NOW + timedelta(seconds=60)]
    def renew(value, request_id):
        entered.set()
        assert release.wait(2)
        return replace(value, expires_at=NOW + timedelta(seconds=200))
    keeper = RuntimeGrantKeeper(grant(), SimpleNamespace(renew=renew), clock=lambda: now[0])
    # Constructed at +60, so the renewal deadline is +80.
    now[0] = NOW + timedelta(seconds=85)
    worker = Thread(target=keeper.tick)
    probe = Thread(target=lambda: (keeper.current("server-persistence"), projected.set()))
    worker.start()
    try:
        assert entered.wait(1)
        probe.start()
        assert projected.wait(1), "Current must read the prior valid snapshot while HTTP is blocked"
    finally:
        release.set()
        worker.join(2)
        if probe.ident is not None:
            probe.join(2)
        keeper.close()
    assert projected.is_set() and keeper.diagnostics().pending_request_id is None


def test_service_reuses_atomic_public_reservation_with_pg_fenced(monkeypatch):
    from claude_agent.service import ClaudeAgentRunRequest, ClaudeAgentService
    import database
    value, calls, _ = holder()
    persist(value)
    monkeypatch.setattr(database, "get_db", lambda: pytest.fail("Public user turn must not use Dream PG"))
    request = ClaudeAgentRunRequest(user_id="42", thread_id="thread-1", message_id="message-1",
        message_parts=[{"type": "text", "text": "original"}], admin_turn_persistence=value)
    service = ClaudeAgentService()
    asyncio.run(service._persist_user_message(SimpleNamespace(request=request)))
    assert len(calls) == 2 and request.message_id == "message-1"


def session(value, session_id="44444444-4444-4444-8444-444444444444"):
    return value.update_session(actor_id="42", thread_id="thread-1", session_id=session_id, contract_version="current")


def test_thread_read_and_session_update_use_exact_server_authority():
    value, calls, _ = holder()
    row = value.thread(actor_id="42", thread_id="thread-1")
    assert row.id == "thread-1" and row.user_id == "42" and row.claude_session_id is None
    first = session(value)
    assert session(value) is first
    row = value.thread(actor_id="42", thread_id="thread-1")
    assert row.claude_session_id == "44444444-4444-4444-8444-444444444444"
    assert row.agent_contract_version == "current"
    posts = [json.loads(request.content)["input"] for request in calls if request.method == "POST"]
    assert posts == [{"thread_id": "thread-1"}, {"thread_id": "thread-1", "claude_session_id": row.claude_session_id, "agent_contract_version": "current"}, {"thread_id": "thread-1"}]
    assert all(request.headers["authorization"] == "Bearer " + TOKEN for request in calls[1:])


def test_workspace_plugin_metadata_uses_current_exact_thread_grant():
    value, calls, _ = holder()
    resolution = value.workspace_plugins(
        actor_id="42",
        thread_id="thread-1",
        profile="standard",
    )
    assert resolution.snapshot.deck_id == "deck-1"
    request = calls[-1]
    assert request.headers["authorization"] == "Bearer " + TOKEN
    assert request.url.path.endswith("/deck-workspace-plugins.resolve")


def test_managed_mcp_scope_uses_current_exact_thread_run_grant():
    context = StoryWorkspaceDreamRunContext(
        workflow_run_id="run_" + "a" * 32,
        thread_id="thread-1",
        deck_id="deck-1",
        deck_plugin_id="ink.dream.story-workflow",
        deck_plugin_version="1.0.0",
        deck_plugin_binding_id="binding-1",
        binding_revision=1,
        deck_runtime_snapshot_id="snapshot-1",
        runtime_plugin_lock_id="lock-1",
    )
    value, calls, _ = holder(workflow_context=context)
    resolution = value.managed_mcp_workspace_scope(
        actor_id="42",
        thread_id="thread-1",
        workflow_run_id=context.workflow_run_id,
    )
    assert resolution.snapshot.workspace_id == "workspace-1"
    request = calls[-1]
    assert request.headers["authorization"] == "Bearer " + TOKEN
    assert request.url.path.endswith("/workflow-managed-mcp-scope.resolve")


def test_current_run_projection_uses_scope_then_run_dtos_with_exact_grant():
    context = _dream_context()
    value, calls, _ = holder(workflow_context=context)

    run = value._session_projection_provider.current_workflow_run("broker-request")

    assert run.workflow_run_id == context.workflow_run_id
    assert run.workspace_id == "workspace-1"
    assert run.created_by == "42"
    assert run.source_voice_thread_id == "thread-1"
    commands = [request for request in calls if request.method == "POST"]
    assert [request.url.path.rsplit("/", 1)[-1] for request in commands] == [
        RESOLVE_WORKFLOW_MANAGED_MCP_SCOPE.capability.name,
        READ_RUN.capability.name,
    ]
    assert all(
        request.headers["authorization"] == "Bearer " + TOKEN
        for request in commands
    )


def test_current_run_projection_rejects_non_dream_turn_before_io():
    value, calls, _ = holder()
    before = len(calls)

    with pytest.raises(AdminDataError, match="STORY_WORKSPACE_PROJECTION_DENIED"):
        value._session_projection_provider.current_workflow_run("broker-request")

    assert len(calls) == before


@pytest.mark.parametrize(
    "actor,thread",
    [("43", "thread-1"), ("42", "other")],
)
def test_current_run_projection_rejects_other_owner_before_io(actor, thread):
    context = _dream_context()
    value, calls, _ = holder(workflow_context=context)
    before = len(calls)

    with pytest.raises(AdminDataError, match="DREAM_DELEGATION_ENTITY_DENIED"):
        value._project_current_workflow_run(
            actor_id=actor,
            thread_id=thread,
            request_id="broker-request",
        )

    assert len(calls) == before


@pytest.mark.parametrize(
    "run_patch",
    [
        {"source_voice_thread_id": "other"},
        {"deck_plugin_version": "2.0.0"},
        {"workspace_id": "other-workspace"},
        {"created_by": "43"},
    ],
)
def test_current_run_projection_rejects_admin_entity_drift(run_patch):
    context = _dream_context()
    value, _calls, _ = holder(
        workflow_context=context,
        run_patch=run_patch,
    )

    with pytest.raises(AdminDataError, match="ADMIN_RESPONSE_INVALID"):
        value._session_projection_provider.current_workflow_run("broker-request")


def test_current_run_projection_uses_the_keeper_current_renewed_token():
    context = _dream_context()
    renewed_token = "idg_" + "b" * 43
    value, calls, _ = holder(
        workflow_context=context,
        expected_token=renewed_token,
    )
    value._keeper = SimpleNamespace(
        current=lambda purpose: replace(
            grant(context.workflow_run_id), token=renewed_token
        )
    )

    run = value._session_projection_provider.current_workflow_run("broker-request")

    assert run.workflow_run_id == context.workflow_run_id
    commands = [request for request in calls if request.method == "POST"]
    assert all(
        request.headers["authorization"] == "Bearer " + renewed_token
        for request in commands
    )


def _dream_context():
    return StoryWorkspaceDreamRunContext(
        workflow_run_id="run_" + "a" * 32,
        thread_id="thread-1",
        deck_id="deck-1",
        deck_plugin_id="ink.dream.story-workflow",
        deck_plugin_version="1.0.0",
        deck_plugin_binding_id="binding-1",
        binding_revision=1,
        deck_runtime_snapshot_id="snapshot-1",
        runtime_plugin_lock_id="rpl_" + "d" * 32,
    )


def _repair_identity(context):
    return DreamAutoRepairIdentityDTO(
        kind="story-workspace-dream-auto-repair",
        schema_version="story-workspace-dream-auto-repair/v1",
        originating_message_id="message-origin",
        originating_turn_id="turn-origin",
        workflow_run_id=context.workflow_run_id,
        repair_attempt=1,
        validation_code="PROJECT_STORY_SLUG_MISMATCH",
        idempotency_key="dream-auto-repair/v1:" + "b" * 64,
        project_cleanup={
            "trusted_project_slug": "server-project",
            "stale_project_slugs": ["workspace-project"],
        },
    )


def _settle_auto_repair(value):
    context = value._resolution.context
    return value.settle_dream_auto_repair(
        actor_id="42",
        thread_id="thread-1",
        message_id="dream_repair_" + "c" * 40,
        expected_identity=_repair_identity(context),
        status="dispatched",
    )


def _activate_runtime(value):
    context = value._resolution.context
    return value.activate_workflow_runtime(
        actor_id="42",
        thread_id="thread-1",
        workflow_run_id=context.workflow_run_id,
        remote_session_ref="sdk-thread",
        verified_plugins=[
            {
                "package_spec": "ink-dream-story@platform-builtin",
                "resolved_version": "1.0.0",
                "artifact_digest": "sha256:" + "a" * 64,
                "has_manifest": True,
            }
        ],
    )


def _store_story_output(value):
    return value.store_story_workspace_output(
        actor_id="42",
        thread_id="thread-1",
        story={
            "title": "标题", "description": None, "type": "short",
            "content": None, "characters": [], "scenes": [],
        },
    )


def test_story_output_uses_exact_thread_grant_and_strict_dto():
    value, calls, _ = holder()
    result = _store_story_output(value)
    assert result.story_id == "story-1"
    request = calls[-1]
    assert request.headers["authorization"] == "Bearer " + TOKEN
    assert request.url.path.endswith("/story-workspace-output.store")
    with pytest.raises(AdminDataError, match="ADMIN_OPERATION_INPUT_INVALID"):
        value.store_story_workspace_output(
            actor_id="42", thread_id="thread-1",
            story={"title": "标题", "workspace_id": "caller"},
        )
    for order_index in (-2_147_483_649, 2_147_483_648):
        with pytest.raises(AdminDataError, match="ADMIN_OPERATION_INPUT_INVALID"):
            value.store_story_workspace_output(
                actor_id="42",
                thread_id="thread-1",
                story={
                    "title": "标题", "description": None, "type": "short",
                    "content": None, "characters": [],
                    "scenes": [{
                        "name": "场景", "description": None,
                        "order_index": order_index,
                    }],
                },
            )


def test_unknown_story_output_recovers_original_receipt_without_post_retry():
    value, calls, _ = holder(lose_operation=STORE_STORY_WORKSPACE_OUTPUT.capability.name)
    with pytest.raises(AdminDataError) as lost:
        _store_story_output(value)
    assert lost.value.outcome_unknown
    with pytest.raises(AdminDataError, match="ADMIN_WRITE_RESULT_UNKNOWN"):
        persist(value)
    with pytest.raises(AdminDataError, match="ADMIN_WRITE_RESULT_UNKNOWN"):
        _store_story_output(value)
    recovered = _store_story_output(value)
    assert recovered.chat_thread_id == "thread-1"
    assert sum(
        request.method == "POST"
        and request.url.path.endswith(STORE_STORY_WORKSPACE_OUTPUT.capability.name)
        for request in calls
    ) == 1


def test_auto_repair_settlement_uses_exact_thread_run_grant_and_dto():
    context = _dream_context()
    value, calls, _ = holder(workflow_context=context)

    result = _settle_auto_repair(value)

    assert result.changed is True
    request = calls[-1]
    assert request.headers["authorization"] == "Bearer " + TOKEN
    assert request.url.path.endswith("/dream-auto-repair.settle")
    with pytest.raises(AdminDataError, match="DREAM_DELEGATION_ENTITY_DENIED"):
        value.settle_dream_auto_repair(
            actor_id="42",
            thread_id="thread-1",
            message_id="dream_repair_" + "c" * 40,
            expected_identity=_repair_identity(context).model_copy(
                update={"workflow_run_id": "run_" + "f" * 32}
            ),
            status="dispatched",
        )


def test_auto_repair_terminal_state_advances_cached_user_replay():
    context = _dream_context()
    value, calls, _ = holder(workflow_context=context)
    message_id = "dream_repair_" + "c" * 40
    identity = _repair_identity(context)
    metadata = {
        "kind": identity.kind,
        "schemaVersion": identity.schema_version,
        "originatingMessageId": identity.originating_message_id,
        "originatingTurnId": identity.originating_turn_id,
        "workflowRunId": identity.workflow_run_id,
        "repairAttempt": identity.repair_attempt,
        "validationCode": identity.validation_code,
        "idempotencyKey": identity.idempotency_key,
        "dispatch_status": "dispatching",
        "projectCleanup": {
            "trustedProjectSlug": "server-project",
            "staleProjectSlugs": ["workspace-project"],
        },
    }
    value.persist_user(
        actor_id="42",
        thread_id="thread-1",
        message_id=message_id,
        parts=[{"type": "text", "text": "repair"}],
        metadata=metadata,
    )
    _settle_auto_repair(value)
    terminal = {**metadata, "dispatch_status": "dispatched"}
    before = len(calls)

    replay = value.persist_user(
        actor_id="42",
        thread_id="thread-1",
        message_id=message_id,
        parts=[{"type": "text", "text": "repair"}],
        metadata=terminal,
    )

    assert replay.message_id == message_id
    assert len(calls) == before


def test_unknown_auto_repair_blocks_other_writes_then_recovers_original_only():
    context = _dream_context()
    value, calls, _ = holder(
        workflow_context=context,
        lose_operation=SETTLE_DREAM_AUTO_REPAIR.capability.name,
    )
    with pytest.raises(AdminDataError) as lost:
        _settle_auto_repair(value)
    assert lost.value.outcome_unknown is True
    before = len(calls)
    with pytest.raises(AdminDataError, match="ADMIN_WRITE_RESULT_UNKNOWN"):
        persist(value)
    assert len(calls) == before
    with pytest.raises(AdminDataError, match="ADMIN_WRITE_RESULT_UNKNOWN"):
        _settle_auto_repair(value)
    recovered = _settle_auto_repair(value)
    assert recovered.message_id == "dream_repair_" + "c" * 40
    assert sum(
        request.method == "POST"
        and request.url.path.endswith(
            SETTLE_DREAM_AUTO_REPAIR.capability.name
        )
        for request in calls
    ) == 1


def test_runtime_activation_uses_exact_thread_run_grant_and_strict_dto():
    context = _dream_context()
    value, calls, _ = holder(workflow_context=context)
    result = _activate_runtime(value)
    assert result.workflow_run_id == context.workflow_run_id
    assert result.runtime_plugin_lock_id == context.runtime_plugin_lock_id
    request = calls[-1]
    assert request.headers["authorization"] == "Bearer " + TOKEN
    assert request.url.path.endswith("/workflow-runtime.activate")
    with pytest.raises(AdminDataError, match="DREAM_RUNTIME_INIT_INVALID"):
        value.activate_workflow_runtime(
            actor_id="42",
            thread_id="thread-1",
            workflow_run_id=context.workflow_run_id,
            remote_session_ref="sdk-thread",
            verified_plugins=[{"path": "/caller-controlled"}],
        )


def test_runtime_activation_requires_exact_local_placement_capability_before_post():
    context = _dream_context()
    capability = next(
        item
        for item in WORKFLOW_RUNTIME_ACTIVATION_SCHEMA_REQUIREMENTS
        if item.capability == "dream.runtime.local-placement.v1"
    )
    ordered = {
        item.capability: item
        for item in (
            *WORKSPACE_SCHEMA_REQUIREMENTS,
            *SESSION_LIST_SCHEMA_REQUIREMENTS,
            *WORKFLOW_RUNTIME_ACTIVATION_SCHEMA_REQUIREMENTS,
        )
    }
    schema_index = list(ordered).index(capability.capability)
    value, calls, _ = holder(
        workflow_context=context,
        schema_fault=schema_index,
    )
    with pytest.raises(AdminDataError, match="ADMIN_CAPABILITY_UNAVAILABLE"):
        _activate_runtime(value)
    assert all(
        request.method == "GET"
        and request.url.path.endswith("/capabilities")
        for request in calls
    )


def test_unknown_runtime_activation_recovers_original_receipt_without_post_retry():
    context = _dream_context()
    value, calls, _ = holder(
        workflow_context=context,
        lose_operation=ACTIVATE_WORKFLOW_RUNTIME.capability.name,
    )
    with pytest.raises(AdminDataError) as lost:
        _activate_runtime(value)
    assert lost.value.outcome_unknown
    with pytest.raises(AdminDataError, match="ADMIN_WRITE_RESULT_UNKNOWN"):
        persist(value)
    with pytest.raises(AdminDataError, match="ADMIN_WRITE_RESULT_UNKNOWN"):
        _activate_runtime(value)
    recovered = _activate_runtime(value)
    assert recovered.workflow_run_id == context.workflow_run_id
    assert sum(
        request.method == "POST"
        and request.url.path.endswith(ACTIVATE_WORKFLOW_RUNTIME.capability.name)
        for request in calls
    ) == 1


def test_mutable_session_identity_only_reuses_the_most_recent_confirmation():
    value, calls, _ = holder()
    session(value, "A")
    session(value, "B")
    session(value, "A")
    session(value, "A")
    assert [json.loads(request.content)["input"]["claude_session_id"] for request in calls[1:]] == ["A", "B", "A"]
    assert value.thread(actor_id="42", thread_id="thread-1").claude_session_id == "A"


@pytest.mark.parametrize("patch", [{"id": "other"}, {"user_id": "43"}])
def test_thread_read_rejects_reply_entity_mismatch(patch):
    value, calls, _ = holder(thread_patch=patch)
    with pytest.raises(AdminDataError) as error:
        value.thread(actor_id="42", thread_id="thread-1")
    assert error.value.code == "ADMIN_RESPONSE_INVALID" and not error.value.outcome_unknown
    assert len(calls) == 2


@pytest.mark.parametrize("operation", ["thread", "session"])
@pytest.mark.parametrize("actor,thread", [("43", "thread-1"), ("42", "other")])
def test_thread_and_session_reject_other_entities_before_io(operation, actor, thread):
    value, calls, _ = holder()
    with pytest.raises(AdminDataError, match="DREAM_DELEGATION_ENTITY_DENIED"):
        if operation == "thread":
            value.thread(actor_id=actor, thread_id=thread)
        else:
            value.update_session(actor_id=actor, thread_id=thread, session_id="A", contract_version="current")
    assert len(calls) == 1


def test_unknown_session_blocks_other_writes_including_known_user_and_recovers_original_receipt():
    value, calls, _ = holder(lose_operation=UPDATE_SESSION.capability.name)
    persist(value)
    with pytest.raises(AdminDataError) as lost:
        session(value)
    assert lost.value.outcome_unknown and lost.value.request_id == "write-original"
    for write in (lambda: persist(value), lambda: persist(value, message_id="other"), lambda: session(value, "B")):
        with pytest.raises(AdminDataError, match="ADMIN_WRITE_RESULT_UNKNOWN") as blocked:
            write()
        assert blocked.value.request_id == "write-original" and blocked.value.outcome_unknown
    assert len(calls) == 3
    with pytest.raises(AdminDataError, match="ADMIN_WRITE_RESULT_UNKNOWN"):
        session(value)
    recovered = session(value)
    assert recovered.changed is True and session(value) is recovered
    assert persist(value).message_id == "message-1"
    assert sum(request.method == "POST" and request.url.path.endswith(UPDATE_SESSION.capability.name) for request in calls) == 1
    assert [request.url.params["operation"] for request in calls[-2:]] == [UPDATE_SESSION.capability.name] * 2


def test_unknown_user_blocks_session_write_without_dispatch():
    value, calls, _ = holder(lose_operation=PERSIST_USER_MESSAGE.capability.name)
    with pytest.raises(AdminDataError):
        persist(value)
    with pytest.raises(AdminDataError, match="ADMIN_WRITE_RESULT_UNKNOWN"):
        session(value)
    assert len(calls) == 2


def test_close_drains_an_already_dispatched_thread_read():
    entered, release, closed = Event(), Event(), Event()
    value, calls, _ = holder(block=(entered, release))
    rows, errors = [], []
    def read():
        try:
            rows.append(value.thread(actor_id="42", thread_id="thread-1"))
        except Exception as error:
            errors.append(error)
    worker = Thread(target=read)
    closer = Thread(target=lambda: (value.close(), closed.set()))
    worker.start()
    try:
        assert entered.wait(1)
        closer.start()
        assert not closed.wait(0.05)
    finally:
        release.set()
        worker.join(2)
        if closer.ident is not None:
            closer.join(2)
    assert closed.is_set() and not errors and rows[0].id == "thread-1" and len(calls) == 2


def test_thread_system_config_read_uses_exact_grant_and_close_drains_it():
    entered, release, closed = Event(), Event(), Event()
    value, calls, _ = holder(block=(entered, release))
    configs, errors = [], []

    def read():
        try:
            configs.append(
                value.system_config(actor_id="42", thread_id="thread-1")
            )
        except Exception as error:
            errors.append(error)

    worker = Thread(target=read)
    closer = Thread(target=lambda: (value.close(), closed.set()))
    worker.start()
    try:
        assert entered.wait(1)
        closer.start()
        assert not closed.wait(0.05)
    finally:
        release.set()
        worker.join(2)
        if closer.ident is not None:
            closer.join(2)

    assert closed.is_set() and not errors
    assert configs == [{"workspace_enabled": True}]
    assert len(calls) == 2
    request = calls[-1]
    assert request.headers["authorization"] == "Bearer " + TOKEN
    assert request.url.path.endswith(GET_THREAD_SYSTEM_CONFIG.capability.name)


def test_recent_sessions_use_exact_utc_window_order_and_current_grant():
    session_rows = [
        {
            "id": "session-new",
            "name": "新篇",
            "labels": ["中文", "journal"],
            "created_at": "2026-09-14T08:00:00Z",
            "updated_at": "2026-09-15T09:00:00Z",
            "first_line": "第一行",
            "text": None,
        },
        {
            "id": "session-old",
            "name": None,
            "labels": [],
            "created_at": "2026-09-13T08:00:00Z",
            "updated_at": "2026-09-14T09:00:00Z",
            "first_line": "older",
            "text": None,
        },
    ]
    value, calls, _ = holder(session_rows=session_rows)

    result = value.recent_sessions(actor_id="42", thread_id="thread-1")

    assert isinstance(result, tuple)
    assert [item.id for item in result] == ["session-new", "session-old"]
    request = calls[-1]
    assert request.headers["authorization"] == "Bearer " + TOKEN
    assert request.url.path.endswith(LIST_SESSIONS.capability.name)
    assert json.loads(request.content)["input"] == {
        "start_date": "2026-09-13",
        "end_date": "2026-09-15",
        "include_text": False,
    }


def test_recent_sessions_use_the_keeper_current_renewed_token():
    renewed_token = "idg_" + "b" * 43
    value, calls, _ = holder(expected_token=renewed_token)
    value._keeper = SimpleNamespace(
        current=lambda purpose: replace(grant(), token=renewed_token)
    )

    assert value.recent_sessions(actor_id="42", thread_id="thread-1") == ()
    assert calls[-1].headers["authorization"] == "Bearer " + renewed_token


def test_session_projection_provider_uses_arbitrary_range_text_and_renewed_grant():
    renewed_token = "idg_" + "b" * 43
    value, calls, _ = holder(
        expected_token=renewed_token,
        session_rows=[{
            "id": "session-text",
            "name": "全文",
            "labels": ["中文"],
            "created_at": "2026-01-01T08:00:00Z",
            "updated_at": "2026-08-31T09:00:00Z",
            "first_line": "第一行",
            "text": "完整正文",
        }],
    )
    value._keeper = SimpleNamespace(
        current=lambda purpose: replace(grant(), token=renewed_token)
    )

    result = value._session_projection_provider.list_sessions(
        SessionListInputDTO(
            start_date="2026-01-01",
            end_date="2026-08-31",
            include_text=True,
        ),
        "broker-request",
    )

    assert result.sessions[0].text == "完整正文"
    request = calls[-1]
    assert request.headers["authorization"] == "Bearer " + renewed_token
    assert request.headers["x-request-id"] == "broker-request"
    assert json.loads(request.content)["input"] == {
        "start_date": "2026-01-01",
        "end_date": "2026-08-31",
        "include_text": True,
    }


@pytest.mark.parametrize("actor,thread", [("43", "thread-1"), ("42", "other")])
def test_session_projection_owner_rejects_actor_or_thread_mismatch_before_io(
    actor, thread
):
    value, calls, _ = holder()
    before = len(calls)

    with pytest.raises(AdminDataError, match="DREAM_DELEGATION_ENTITY_DENIED"):
        value._project_sessions(
            actor_id=actor,
            thread_id=thread,
            input_dto=SessionListInputDTO(
                start_date="2026-01-01",
                end_date="2026-08-31",
                include_text=False,
            ),
            request_id="broker-request",
        )

    assert len(calls) == before


@pytest.mark.parametrize("actor,thread", [("43", "thread-1"), ("42", "other")])
def test_recent_sessions_reject_other_entities_before_io(actor, thread):
    value, calls, _ = holder()
    before = len(calls)

    with pytest.raises(AdminDataError, match="DREAM_DELEGATION_ENTITY_DENIED"):
        value.recent_sessions(actor_id=actor, thread_id=thread)

    assert len(calls) == before


@pytest.mark.parametrize(
    "schema_index",
    [len(WORKSPACE_SCHEMA_REQUIREMENTS), len(WORKSPACE_SCHEMA_REQUIREMENTS) + 1],
    ids=["runtime-delegation", "runtime-purpose"],
)
def test_recent_sessions_require_exact_runtime_schemas_before_command(schema_index):
    value, calls, _ = holder(schema_fault=schema_index)
    before = len(calls)

    with pytest.raises(AdminDataError) as error:
        value.recent_sessions(actor_id="42", thread_id="thread-1")

    assert error.value.code == "ADMIN_CAPABILITY_UNAVAILABLE"
    assert len(calls) == before


def test_recent_sessions_reject_text_when_include_text_is_false():
    value, calls, _ = holder(
        session_rows=[{
            "id": "session-leak",
            "name": "Title",
            "labels": [],
            "created_at": "2026-09-15T08:00:00Z",
            "updated_at": "2026-09-15T09:00:00Z",
            "first_line": "preview",
            "text": "full text",
        }]
    )

    with pytest.raises(AdminDataError) as error:
        value.recent_sessions(actor_id="42", thread_id="thread-1")

    assert error.value.code == "ADMIN_RESPONSE_INVALID"
    assert calls[-1].url.path.endswith(LIST_SESSIONS.capability.name)


def test_close_drains_an_already_dispatched_recent_sessions_read():
    entered, release, closed = Event(), Event(), Event()
    value, calls, _ = holder(block=(entered, release))
    rows, errors = [], []

    def read():
        try:
            rows.append(value.recent_sessions(actor_id="42", thread_id="thread-1"))
        except Exception as error:
            errors.append(error)

    worker = Thread(target=read)
    closer = Thread(target=lambda: (value.close(), closed.set()))
    worker.start()
    try:
        assert entered.wait(1)
        closer.start()
        assert not closed.wait(0.05)
    finally:
        release.set()
        worker.join(2)
        if closer.ident is not None:
            closer.join(2)

    assert closed.is_set() and not errors and rows == [()]
    assert calls[-1].url.path.endswith(LIST_SESSIONS.capability.name)


def test_public_native_init_is_the_next_turn_resume_identity_with_thread_pg_fenced(monkeypatch, tmp_path):
    import re
    import claude_agent.service as service_module
    from claude_agent.service import ClaudeAgentRunRequest, ClaudeAgentService
    from claude_agent.thread_pool import AgentRunState
    from claude_agent_sdk.types import SystemMessage
    from tests.test_claude_agent_service import _FakeBus, _FakeContextBuilder
    value, calls, _ = holder()
    builder = _FakeContextBuilder()
    service = ClaudeAgentService(context_builder=builder, platform_model_resolver=lambda *_: "dream-balanced",
        managed_mcp_runtime_snapshot_loader=SimpleNamespace(
            load=AsyncMock(return_value={}),
            authorize=lambda _authorization: nullcontext(),
        ))
    request = ClaudeAgentRunRequest(user_id="42", thread_id="thread-1", resume=True,
        admin_workflow_resolution=AdminWorkflowResolution("42", "thread-1", None), admin_turn_persistence=value)
    monkeypatch.setattr(service_module, "get_or_create_workspace", lambda *_args, **_kwargs: tmp_path.resolve())
    new_id = "44444444-4444-4444-8444-444444444444"
    async def scenario():
        state = AgentRunState(session_id=request.thread_id)
        fresh = await service.assemble_context(request, state=state, bus=_FakeBus(), runner=Mock())
        assert fresh.run_options.thread_id is None
        await service._persist_sdk_session_from_message(fresh, SimpleNamespace(data={"session_id": new_id}))
        await service._persist_sdk_session_from_message(fresh, SystemMessage(subtype="error", data={"session_id": new_id}))
        assert not any(item.url.path.endswith(UPDATE_SESSION.capability.name) for item in calls)
        await service._persist_sdk_session_from_message(fresh, SystemMessage(subtype="init", data={"session_id": new_id}))
        project = tmp_path / ".claude-home" / "projects" / re.sub(r"[^a-zA-Z0-9]", "-", str(tmp_path.resolve()))
        project.mkdir(parents=True)
        (project / f"{new_id}.jsonl").write_text(json.dumps({"type": "user", "uuid": "fixture", "sessionId": new_id,
            "message": {"role": "user", "content": "fixture"}}) + "\n")
        resumed = await service.assemble_context(request, state=state, bus=_FakeBus(), runner=Mock())
        assert resumed.run_options.resume and resumed.run_options.thread_id == new_id
        assert resumed.request.thread_id == "thread-1" and resumed.request.admin_turn_persistence is value
        await service._persist_sdk_session_from_message(resumed, SystemMessage(subtype="init", data={"session_id": new_id}))
    value.start()
    try:
        asyncio.run(scenario())
    finally:
        value.close()
    assert len(builder.system_prompt_calls) == 1
    assert sum(item.url.path.endswith(LIST_SESSIONS.capability.name) for item in calls) == 1
    assert sum(item.url.path.endswith(UPDATE_SESSION.capability.name) for item in calls) == 1


@pytest.mark.parametrize("lose_session", [False, True])
def test_public_native_init_persists_before_original_cancel_terminal_with_pg_fenced(monkeypatch, lose_session):
    import claude_agent.service as service_module
    from claude_agent.service import ClaudeAgentRunRequest, ClaudeAgentService
    from claude_agent.thread_pool import AgentRunState
    from claude_agent.tool_confirmation_store import ToolConfirmationStore
    from claude_agent_sdk.types import SystemMessage
    value, calls, _ = holder(lose_operation=UPDATE_SESSION.capability.name if lose_session else None)
    service = ClaudeAgentService(dream_artifact_turn_hook=Mock())
    # Inject partial persistence while executing the real service callbacks,
    # cancellation and SSE path through the bound Admin owner.
    partial = AsyncMock()
    monkeypatch.setattr(service, "_persist_partial_assistant", partial)
    async def scenario():
        queue = asyncio.Queue()
        request = ClaudeAgentRunRequest(user_id="42", thread_id="thread-1", message_id="message-1",
            message_parts=[{"type": "text", "text": "original"}], admin_turn_persistence=value)
        class CancelRunner:
            async def run_streaming(self, opts, callbacks):
                await callbacks.on_message(SystemMessage(subtype="init", data={"session_id": "A"}))
                await callbacks.on_text_delta("partial")
                raise asyncio.CancelledError()
        execution = service_module._TurnExecution(request=request, state=AgentRunState(session_id="thread-1"),
            runner=CancelRunner(), run_options=Mock(), turn_context=service_module._TurnContext(queue=queue, confirmation_store=ToolConfirmationStore()),
            dream_artifact_turn_ticket=Mock())
        with pytest.raises(asyncio.CancelledError):
            await service.execute_session(execution)
        frames = []
        while not queue.empty():
            frames.append(queue.get_nowait())
        assert frames[-1] is None
        assert frames[-2].payload() == {"type": "finish", "finishReason": "stop", "cancelled": True}
        metadata = next(frame for frame in frames if frame is not None and frame.type == "message-metadata")
        assert metadata.data["turnId"]
    asyncio.run(scenario())
    partial.assert_awaited_once()
    assert partial.await_args.kwargs["turn_status"] == "cancelled"
    assert [item.url.path.rsplit("/", 1)[-1] for item in calls[1:]] == [PERSIST_USER_MESSAGE.capability.name, UPDATE_SESSION.capability.name]
    if lose_session:
        with pytest.raises(AdminDataError, match="ADMIN_WRITE_RESULT_UNKNOWN"):
            session(value, "B")
        assert len(calls) == 3


@pytest.mark.parametrize("cancel", [False, True])
@pytest.mark.parametrize("active_editor", [False, True])
def test_original_factory_keeps_grant_on_disconnect_and_drains_it_on_terminal(
    monkeypatch, cancel, active_editor
):
    import claude_agent.thread_factory as factory_module
    from claude_agent.service import ClaudeAgentRunRequest
    from claude_agent.stream_events import NormalizedAgentEvent
    from claude_agent.thread_factory import ClaudeAgentThreadFactory
    value, _, runtime = holder()
    editor_runtime = SimpleNamespace(start_calls=0, close_calls=0)
    editor_runtime.start = lambda: setattr(
        editor_runtime, "start_calls", editor_runtime.start_calls + 1
    )
    editor_runtime.close = lambda: setattr(
        editor_runtime, "close_calls", editor_runtime.close_calls + 1
    )
    monkeypatch.setattr(factory_module, "ClaudeAgentRunner", lambda: SimpleNamespace())

    async def scenario():
        finish = asyncio.Event()
        released = []
        admission = SimpleNamespace(try_acquire=lambda session_id: SimpleNamespace(release=lambda: released.append(session_id)))
        factory = ClaudeAgentThreadFactory(dream_observer=SimpleNamespace(), admission_controller=admission)
        class Service:
            async def assemble_context(self, request, *, state, bus, runner):
                assert value._keeper is not None
                assert editor_runtime.start_calls == int(active_editor)
                state.system_prompt = "explicit-fake-context"
                return SimpleNamespace(dream_context=None, bus=bus)
            async def execute_session(self, execution):
                await execution.bus.publish(NormalizedAgentEvent.create("message-metadata", {"sessionId": "thread-1"}))
                await finish.wait()
                await execution.bus.publish_terminal(NormalizedAgentEvent.create("finish", {"finishReason": "stop"}))
            async def mark_auto_repair_failed(self, request):
                pass
        factory._service = Service()
        request = ClaudeAgentRunRequest(
            user_id="42",
            thread_id="thread-1",
            admin_turn_persistence=value,
            admin_editor_runtime=editor_runtime,
            editor_state={"id": "editor-1"} if active_editor else None,
        )
        stream = factory.run_streaming(request)
        try:
            first = await asyncio.wait_for(anext(stream), 1)
            assert "message-metadata" in first
            state = factory._pool.get("thread-1")
            task = state.bg_task
            await stream.aclose()
            assert factory.session_snapshot("thread-1")["lifecycle"] == "running"
            assert value.current_grant(actor_id="42", thread_id="thread-1").token == TOKEN
            assert editor_runtime.close_calls == 0
            assert not released
            if cancel:
                result = await factory.stop_thread("thread-1")
                assert result["running"] is False
            else:
                finish.set()
                await asyncio.wait_for(task, 1)
            assert released == ["thread-1"]
        finally:
            finish.set()
            await stream.aclose()
            await factory.aclose()
        assert runtime.closed == [True] and not value._keeper._thread.is_alive()
        assert editor_runtime.start_calls == int(active_editor)
        assert editor_runtime.close_calls == 1
    asyncio.run(scenario())
def assistant_write(value, **changes):
    args = {"actor_id": "42", "thread_id": "thread-1", "message_id": "message-1",
        "parts": [{"type": "text", "text": "  原结果\n"}],
        "metadata": {"turnId": "turn-original", "turnStatus": "completed", "finalPartIndex": 0,
            "durationMs": 1250, "usage": {"inputTokens": 3, "outputTokens": 2, "totalTokens": 5}},
        "history_final_text": "  原结果\n", "history_process_available": False, "history_projection_version": 1}
    return value.persist_assistant(**{**args, **changes})


def test_assistant_uses_original_complete_history_DTO_and_current_grant():
    value, calls, _ = holder()
    result = assistant_write(value)
    request = next(item for item in calls if item.url.path.endswith(PERSIST_MESSAGE.capability.name))
    body = json.loads(request.content)
    assert result.message_id == "message-1"
    assert request.headers["authorization"] == "Bearer " + TOKEN
    assert set(body["input"]) == {"thread_id", "message_id", "role", "parts", "metadata", "history_final_text", "history_process_available", "history_projection_version"}
    assert body["input"]["role"] == "assistant" and body["input"]["history_final_text"] == "  原结果\n"
    assert body["input"]["metadata"]["usage"]["totalTokens"] == 5
    assert TOKEN not in request.content.decode() and value._pending is None


@pytest.mark.parametrize("actor,thread", [("43", "thread-1"), ("42", "another-thread")])
def test_assistant_rejects_wrong_actor_or_thread_before_io(actor, thread):
    value, calls, _ = holder()
    before = len(calls)
    with pytest.raises(AdminDataError): assistant_write(value, actor_id=actor, thread_id=thread)
    assert len(calls) == before


@pytest.mark.parametrize("fault", ["missing", "duplicate", 0, 1, 2, 3])
def test_assistant_requires_four_exact_schemas_before_command(fault):
    value, calls, _ = holder(schema_fault=fault)
    before = len(calls)
    with pytest.raises(AdminDataError) as error: assistant_write(value)
    assert error.value.code == "ADMIN_CAPABILITY_UNAVAILABLE"
    assert value._pending is None
    assert all(item.method == "GET" and item.url.path.endswith("/capabilities") for item in calls[before:])


@pytest.mark.parametrize("patch", [{"message_id": "another-message"}, {"message_id": None}, {"extra": "private"}])
def test_assistant_bad_reply_retains_original_pending_identity(patch):
    value, calls, _ = holder(assistant_patch=patch)
    with pytest.raises(AdminDataError) as error: assistant_write(value)
    assert error.value.code == "ADMIN_RESPONSE_INVALID" and error.value.outcome_unknown
    assert value._pending.operation is PERSIST_MESSAGE and value._pending.request_id == "write-original"
    assert sum(item.url.path.endswith(PERSIST_MESSAGE.capability.name) for item in calls) == 1


def test_unknown_assistant_blocks_user_session_and_new_assistant_then_only_recovers_original():
    value, calls, _ = holder(lose_operation=PERSIST_MESSAGE.capability.name)
    with pytest.raises(AdminDataError) as error: assistant_write(value)
    assert error.value.request_id == "write-original" and error.value.outcome_unknown
    before = len(calls)
    for method in [lambda: value.persist_user(actor_id="42", thread_id="thread-1", message_id="user-other", parts=[{"type":"text","text":"user"}], metadata=None),
        lambda: value.update_session(actor_id="42", thread_id="thread-1", session_id="native", contract_version="v1"),
        lambda: assistant_write(value, message_id="another-message")]:
        with pytest.raises(AdminDataError) as result: method()
        assert result.value.request_id == "write-original" and result.value.outcome_unknown
    assert len(calls) == before
    with pytest.raises(AdminDataError): assistant_write(value)  # Original absent does not resend.
    result = assistant_write(value)
    assert result.message_id == "message-1" and value._pending is None
    assert sum(item.url.path.endswith(PERSIST_MESSAGE.capability.name) for item in calls) == 1
    reads = [item for item in calls if "/receipts/" in item.url.path]
    assert len(reads) == 2 and all(item.method == "GET" and item.url.path.endswith("write-original") and item.url.params["operation"] == PERSIST_MESSAGE.capability.name for item in reads)


@pytest.mark.parametrize("operation", [PERSIST_USER_MESSAGE, UPDATE_SESSION], ids=lambda item:item.capability.name)
def test_unknown_existing_writer_blocks_assistant_before_io(operation):
    value, calls, _ = holder(lose_operation=operation.capability.name)
    with pytest.raises(AdminDataError):
        if operation is PERSIST_USER_MESSAGE:
            value.persist_user(actor_id="42", thread_id="thread-1", message_id="user-1", parts=[{"type":"text","text":"user"}], metadata=None)
        else:
            value.update_session(actor_id="42", thread_id="thread-1", session_id="native", contract_version="v1")
    before = len(calls)
    with pytest.raises(AdminDataError) as error: assistant_write(value)
    assert error.value.outcome_unknown and len(calls) == before


@pytest.mark.parametrize("outcome", ["completed", "cancelled", "error"])
def test_public_execute_session_persists_original_assistant_parts_with_SQL_fenced(monkeypatch, outcome):
    import database
    import claude_agent.service as service_module
    from claude_agent.service import ClaudeAgentRunRequest, ClaudeAgentService
    from claude_agent.thread_pool import AgentRunState
    from claude_agent.tool_confirmation_store import ToolConfirmationStore
    from libs.claude_agent_kit.types import AgentRunResult
    from tests.test_claude_agent_service import _FakeContextBuilder
    value, calls, _ = holder()
    monkeypatch.setattr(database, "save_chat_message", lambda *_a, **_kw: pytest.fail("Public assistant must not write SQL"))
    monkeypatch.setattr(database, "get_db", lambda *_a, **_kw: pytest.fail("Public turn persistence must not open SQL"))
    class Runner:
        async def run_streaming(self, opts, callbacks):
            await callbacks.on_text_delta("原文结果")
            if outcome == "cancelled": raise asyncio.CancelledError
            await callbacks.on_text_done("原文结果")
            return AgentRunResult(full_text="原文结果", session_id=None, success=outcome=="completed",
                error="synthetic failure" if outcome=="error" else None,
                usage={"input_tokens":3,"output_tokens":2}, duration_ms=1250)
    service = ClaudeAgentService(context_builder=_FakeContextBuilder(), platform_model_resolver=lambda *_:"dream-balanced",
        managed_mcp_runtime_snapshot_loader=SimpleNamespace(
            load=AsyncMock(return_value={}),
            authorize=lambda _authorization: nullcontext(),
        ))
    async def scenario():
        request = ClaudeAgentRunRequest(user_id="42",thread_id="thread-1",message_id="user-1",
            message_parts=[{"type":"text","text":"用户文本"}],model="dream-balanced",admin_turn_persistence=value,
            admin_workflow_resolution=AdminWorkflowResolution("42","thread-1",None))
        execution = service_module._TurnExecution(request=request,state=AgentRunState(session_id="thread-1"),runner=Runner(),run_options=Mock(),
            turn_context=service_module._TurnContext(queue=asyncio.Queue(),confirmation_store=ToolConfirmationStore()))
        if outcome == "cancelled":
            with pytest.raises(asyncio.CancelledError): await service.execute_session(execution)
        else: await service.execute_session(execution)
        return execution
    execution = asyncio.run(scenario())
    assistant = [item for item in calls if item.url.path.endswith(PERSIST_MESSAGE.capability.name)]
    assert len(assistant)==1
    dto = json.loads(assistant[0].content)["input"]
    assert dto["parts"]==[{"type":"text","text":"原文结果"}] and dto["metadata"]["turnStatus"]==outcome
    assert dto["metadata"]["chatModel"]=={"provider":"gateway","model":"dream-balanced"}
    assert dto["metadata"]["turnId"]==execution.state.current_turn_id
    assert dto["message_id"] not in {execution.request.message_id, execution.state.current_turn_id}
    if outcome=="completed":
        assert (dto["history_final_text"],dto["history_process_available"],dto["history_projection_version"])==("原文结果",False,1)
        assert dto["metadata"]["durationMs"]==1250 and dto["metadata"]["usage"]["totalTokens"]==5
    else:
        assert dto["metadata"]["is_partial"] is True
        assert (dto["history_final_text"],dto["history_process_available"],dto["history_projection_version"])==(None,False,None)
# [Sync] 2026-09-17: verify turn domains reuse the prevalidated capability snapshot without duplicate discovery I/O.
