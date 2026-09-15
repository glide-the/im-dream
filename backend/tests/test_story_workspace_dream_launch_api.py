# [Input] Public Dream launch request, Admin Runtime port fakes and isolated legacy workflow fixtures.
# [Output] Route, idempotency, frozen replay, dispatch and Admin Runtime boundary verification.
# [Pos] Dream launch business tests; local SQL exists only in the named legacy fixture and fakes.
# [Sync] 2026-09-16: replace production provisioning tests with Registry130-132 Runtime-port coverage.
"""Dream launch REST and production gateway integration tests."""

from __future__ import annotations

import asyncio
import ast
from datetime import UTC, datetime, timedelta
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

import database
from agent_stream_events import NormalizedAgentEvent
from claude_agent.chat_stream_adapter import ChatStreamAdapter
from backend.tests.legacy_database_fixture import LegacyDatabaseModuleFixture
from routers import story_workspace
from services.deck.builtin_plugin import (
    BUILTIN_CLAUDE_PLUGIN_ID,
    BUILTIN_DECK_PLUGIN_ID,
    BUILTIN_DECK_PLUGIN_VERSION,
    seed_builtin_deck_plugin,
)
from services.deck.story_workflow_application import StoryWorkflowRunApplicationService
from services.story_workspace.dream_launch_infrastructure import (
    DreamLaunchFailureRecorder,
    DreamLaunchWorkflowOperationsAdapter,
    DreamLaunchApplicationError,
    DreamLaunchTaskRegistry,
    _decode_json_object,
    build_dream_launch_application_service,
    build_dream_agent_turn_dispatcher,
)
from services.story_workspace.dream_launch_runtime import (
    DreamLaunchRuntimeError,
    PreparedDreamLaunchBinding,
)
from services.admin_data.request_auth import AdminRequestActor, AdminRequestAuth
from services.admin_gateway import GatewayInferenceError
from services.story_workspace.dream_launch_application_service import (
    DreamLaunchIdempotencyConflict,
)
from services.story_workspace.canonical_project_instruction import (
    story_workspace_canonical_project_fallback_slug,
)
from story_workspace.contracts import (
    StoryWorkspaceDreamLaunchCommand,
    StoryWorkspaceDreamRunContext,
)


def test_decode_json_object_accepts_psycopg_native_jsonb_dict() -> None:
    native_jsonb = {"enabled": True, "nullable": None, "items": ["one"]}

    decoded = _decode_json_object(native_jsonb)

    assert decoded == native_jsonb
    assert decoded is not native_jsonb


def test_launch_runtime_boundary_has_no_database_client_or_provisioning_class() -> None:
    service_root = Path(__file__).parents[1] / "services" / "story_workspace"
    runtime_source = (service_root / "dream_launch_runtime.py").read_text()
    runtime_tree = ast.parse(runtime_source)
    imported_roots = {
        alias.name.split(".")[0]
        for node in ast.walk(runtime_tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    called_attributes = {
        node.func.attr
        for node in ast.walk(runtime_tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert imported_roots.isdisjoint({"database", "psycopg", "sqlalchemy", "drizzle"})
    assert called_attributes.isdisjoint({"execute", "cursor", "commit", "rollback"})

    infrastructure_tree = ast.parse(
        (service_root / "dream_launch_infrastructure.py").read_text()
    )
    assert "DreamRuntimeProvisioningService" not in {
        node.name for node in ast.walk(infrastructure_tree) if isinstance(node, ast.ClassDef)
    }


ACTOR_ID = "71"
OTHER_ACTOR_ID = "72"
WORKSPACE_ID = "workspace-dream-launch-api"
OTHER_WORKSPACE_ID = "workspace-dream-launch-api-other"
DECK_ID = "deck-dream-launch-api"
ALTERNATE_DECK_ID = "deck-dream-launch-api-alternate"


def test_launch_prepare_ends_read_transaction_before_admin_runtime_call() -> None:
    class TrackingDb:
        in_transaction = False

        def execute(self, _statement, _params=()):
            self.in_transaction = True
            return SimpleNamespace(fetchone=lambda: None)

        def rollback(self):
            self.in_transaction = False

    db = TrackingDb()

    class RuntimePort:
        async def authorize(self, **_kwargs):
            assert db.in_transaction is False

        async def prepare(self, **_kwargs):
            assert db.in_transaction is False
            return PreparedDreamLaunchBinding(
                deck_plugin_id=BUILTIN_DECK_PLUGIN_ID,
                deck_plugin_version=BUILTIN_DECK_PLUGIN_VERSION,
                deck_plugin_binding_id="dpb_" + "1" * 32,
                binding_revision=1,
            )

    operations = DreamLaunchWorkflowOperationsAdapter.__new__(
        DreamLaunchWorkflowOperationsAdapter
    )
    operations.db = db
    operations._runtime_port = RuntimePort()
    operations._platform_model_resolver = lambda *_args: "dream-balanced"
    binding = asyncio.run(
        operations.prepare(
            launch_command(),
            actor_id=ACTOR_ID,
            workspace_id=WORKSPACE_ID,
        )
    )

    assert binding.binding_revision == 1


def test_launch_ends_preflight_read_transaction_before_run_create() -> None:
    class TrackingDb:
        in_transaction = False

        def rollback(self):
            self.in_transaction = False

    db = TrackingDb()

    class CleanBoundaryRunService:
        async def create_run(self, *_args, **_kwargs):
            assert db.in_transaction is False
            return "created"

    operations = DreamLaunchWorkflowOperationsAdapter.__new__(
        DreamLaunchWorkflowOperationsAdapter
    )
    operations.db = db
    operations._run_service = CleanBoundaryRunService()
    operations._actor_context = SimpleNamespace(
        actor_id=ACTOR_ID,
        workspace_id=WORKSPACE_ID,
    )
    # psycopg opens a transaction for the final preflight SELECT.
    db.in_transaction = True
    created = asyncio.run(
        operations.create_run(
            preflight_id="wpf_" + "1" * 32,
            preflight_token="pft-token",
            idempotency_key="dream-api-launch-clean-boundary",
            source_thread_id="thread-clean-boundary",
            source_message_id="message-clean-boundary",
            source_message_time=datetime(2026, 8, 1, 9, 0, tzinfo=UTC),
            actor_id=ACTOR_ID,
            workspace_id=WORKSPACE_ID,
        )
    )

    assert created == "created"


def launch_command(**overrides: object) -> StoryWorkspaceDreamLaunchCommand:
    payload: dict[str, object] = {
        "deckId": DECK_ID,
        "goal": "创作一个雨夜车站重逢的短篇故事",
        "idempotencyKey": "dream-api-launch-1",
    }
    payload.update(overrides)
    return StoryWorkspaceDreamLaunchCommand.model_validate(payload)


class ApiGateway:
    def __init__(self) -> None:
        self.calls: list[tuple[StoryWorkspaceDreamLaunchCommand, dict[str, str], object]] = []

    async def start_dream_run(
        self,
        request: StoryWorkspaceDreamLaunchCommand,
        *,
        actor: dict[str, str],
        runtime_port,
    ) -> StoryWorkspaceDreamRunContext:
        self.calls.append((request, actor, runtime_port))
        return StoryWorkspaceDreamRunContext(
            workflow_run_id="run_" + "1" * 32,
            thread_id="thread-dream-api",
            deck_id=request.deck_id,
            deck_plugin_id=BUILTIN_DECK_PLUGIN_ID,
            deck_plugin_version=BUILTIN_DECK_PLUGIN_VERSION,
            deck_plugin_binding_id="dpb_" + "2" * 32,
            binding_revision=1,
            deck_runtime_snapshot_id="drs_" + "3" * 32,
            runtime_plugin_lock_id="rpl_" + "4" * 32,
        )


class StoryWorkspaceDreamLaunchApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.gateway = ApiGateway()
        self.app = FastAPI()
        self.owner = AdminRequestAuth.__new__(AdminRequestAuth)
        self.owner.client = object()
        self.admin_actor = AdminRequestActor(
            "subject", ACTOR_ID, "dream-browser", frozenset({"dream:read", "dream:write"}),
            1, 4_102_444_800, "test-access-token",
        )
        self.app.dependency_overrides[
            story_workspace._story_workflow_current_user
        ] = lambda: {
            "user_id": int(ACTOR_ID),
            "workspace_id": WORKSPACE_ID,
            "_admin_actor": self.admin_actor,
        }
        self.app.dependency_overrides[story_workspace.get_admin_request_auth] = (
            lambda: self.owner
        )
        self.app.dependency_overrides[
            story_workspace.get_dream_launch_endpoint_service
        ] = lambda: self.gateway
        self.app.include_router(story_workspace.router)

    def test_start_uses_canonical_request_and_returns_camel_case_context(self) -> None:
        with TestClient(self.app) as client:
            response = client.post(
                "/api/story-workspace/dream-runs/start",
                json={
                    "deckId": DECK_ID,
                    "goal": "创作一个雨夜车站重逢的短篇故事",
                    "idempotencyKey": "dream-api-launch-1",
                },
            )

        self.assertEqual(response.status_code, 201, response.text)
        payload = response.json()
        self.assertEqual(payload["status"], "accepted")
        self.assertEqual(payload["workflowRunId"], "run_" + "1" * 32)
        self.assertEqual(payload["threadId"], "thread-dream-api")
        self.assertEqual(payload["deckPluginBindingId"], "dpb_" + "2" * 32)
        self.assertFalse(any("_" in key for key in payload))
        request, actor, runtime_port = self.gateway.calls[0]
        self.assertEqual(request.deck_id, DECK_ID)
        self.assertEqual(
            actor,
            {"actor_id": ACTOR_ID, "workspace_id": WORKSPACE_ID},
        )
        self.assertEqual(runtime_port._access_token, "test-access-token")

    def test_start_rejects_client_provenance_fields(self) -> None:
        forbidden = (
            {"threadId": "client-thread"},
            {"workflowRunId": "run_" + "9" * 32},
            {"bindingRevision": 999},
            {"sourceMessageId": "client-message"},
        )
        with TestClient(self.app) as client:
            for extra in forbidden:
                with self.subTest(extra=extra):
                    response = client.post(
                        "/api/story-workspace/dream-runs/start",
                        json={
                            "deckId": DECK_ID,
                            "goal": "目标",
                            "idempotencyKey": "dream-api-strict",
                            **extra,
                        },
                    )
                    self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(self.gateway.calls, [])

    def test_start_rejects_snake_case_launch_fields(self) -> None:
        with TestClient(self.app) as client:
            response = client.post(
                "/api/story-workspace/dream-runs/start",
                json={
                    "deck_id": DECK_ID,
                    "goal": "目标",
                    "idempotency_key": "dream-api-snake-case",
                },
            )

        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(self.gateway.calls, [])

    def test_start_rejects_launch_field_surrounding_or_blank_whitespace(self) -> None:
        invalid_fields = (
            ("deckId", f" {DECK_ID}"),
            ("deckId", f"{DECK_ID} "),
            ("goal", " /drama-forge:drama-init"),
            ("goal", "/drama-forge:drama-init\n"),
            ("goal", "   "),
            ("idempotencyKey", " dream-api-whitespace"),
            ("idempotencyKey", "dream-api-whitespace "),
        )
        with TestClient(self.app) as client:
            for field, value in invalid_fields:
                with self.subTest(field=field, value=value):
                    payload = {
                        "deckId": DECK_ID,
                        "goal": "/drama-forge:drama-init",
                        "idempotencyKey": "dream-api-whitespace",
                    }
                    payload[field] = value
                    response = client.post(
                        "/api/story-workspace/dream-runs/start",
                        json=payload,
                    )
                    self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(self.gateway.calls, [])


def seed_launch_runtime_fixture(db) -> None:
    """Prepare legacy workflow reads without exercising a Dream provisioning path."""

    seed_builtin_deck_plugin(db)
    lock_row = db.execute(
        "SELECT id, lock_json FROM deck_runtime_plugin_locks "
        "WHERE deck_plugin_id = ? AND deck_plugin_version = ?",
        (BUILTIN_DECK_PLUGIN_ID, BUILTIN_DECK_PLUGIN_VERSION),
    ).fetchone()
    runtime_lock = json.loads(lock_row["lock_json"])
    required = next(
        entry for entry in runtime_lock["claude_code_plugins"] if entry["required"]
    )
    now = datetime.now(UTC).isoformat()
    with db:
        db.execute(
            "INSERT INTO deck_plugin_installations ("
            "id, scope_type, scope_id, deck_plugin_id, installed_versions_json, "
            "default_version, status, approved_capabilities_json, source_policy_id, revision) "
            "VALUES (?, 'workspace', ?, ?, ?, ?, 'ready', ?, 'test:admin-runtime-port', 1)",
            (
                "dpi_" + "4" * 32,
                WORKSPACE_ID,
                BUILTIN_DECK_PLUGIN_ID,
                json.dumps([BUILTIN_DECK_PLUGIN_VERSION]),
                BUILTIN_DECK_PLUGIN_VERSION,
                json.dumps(["story.workspace.propose"]),
            ),
        )
        db.execute(
            "INSERT INTO deck_plugin_bindings ("
            "deck_plugin_binding_id, deck_id, workspace_id, creator_id, deck_plugin_id, "
            "deck_plugin_version, binding_revision, status, applied_to) "
            "VALUES (?, ?, ?, ?, ?, ?, 1, 'active', 'next_run')",
            (
                "dpb_" + "2" * 32,
                DECK_ID,
                WORKSPACE_ID,
                ACTOR_ID,
                BUILTIN_DECK_PLUGIN_ID,
                BUILTIN_DECK_PLUGIN_VERSION,
            ),
        )
        db.execute(
            "INSERT INTO runtime_plugin_materializations ("
            "runtime_materialization_id, runtime_environment_id, runtime_pool_id, runtime_node_id, "
            "claude_code_plugin_id, resolved_version, artifact_digest, materialized_digest, "
            "artifact_set_hash, policy_revision, declaration_status, materialization_status, "
            "activation_status, materialization_key, attempt_id, attempt_count, verification_status, "
            "retention_state, cache_ref, created_at, updated_at) "
            "VALUES (?, 'fixture-local', 'fixture-local', 'fixture-node', ?, ?, ?, ?, ?, "
            "'fixture/v1', 'declared', 'materialized', 'loadable', ?, ?, 1, 'verified', "
            "'shared_artifact', 'fixture://admin-owned', ?, ?)",
            (
                "rm_" + "3" * 32,
                required["claude_code_plugin_id"],
                required["resolved_version"],
                required["artifact_digest"],
                required["artifact_digest"],
                "sha256:" + "7" * 64,
                "sha256:" + "8" * 64,
                "rpa_" + "9" * 32,
                now,
                now,
            ),
        )


class FakeDreamLaunchRuntime:
    """Provider-free Admin Runtime port used by the isolated workflow harness."""

    def __init__(self, db, calls: list[dict[str, object]]) -> None:
        self.db = db
        self.calls = calls

    async def authorize(self, *, deck_id, workspace_id, agent_id) -> None:
        self.calls.append({
            "operation": "scope",
            "deck_id": deck_id,
            "workspace_id": workspace_id,
            "agent_id": agent_id,
        })
        row = self.db.execute(
            "SELECT deck.id FROM decks AS deck "
            "JOIN story_workspace_workspaces AS workspace "
            "ON workspace.id = ? AND workspace.owner_id = deck.owner_id "
            "WHERE deck.id = ? AND deck.enabled = 1",
            (workspace_id, deck_id),
        ).fetchone()
        if row is None:
            raise DreamLaunchRuntimeError("DECK_ACCESS_DENIED", 404)
        if agent_id is not None:
            voice = self.db.execute(
                "SELECT id FROM voices WHERE id = ? AND deck_id = ? AND enabled = 1",
                (agent_id, deck_id),
            ).fetchone()
            if voice is None:
                raise DreamLaunchRuntimeError("AGENT_ACCESS_DENIED", 404)

    async def prepare(
        self,
        *,
        deck_id,
        workspace_id,
        agent_id,
        existing_run,
    ) -> PreparedDreamLaunchBinding:
        mode = "replay" if existing_run is not None else "current"
        self.calls.append({
            "operation": "prepare",
            "mode": mode,
            "deck_id": deck_id,
            "workspace_id": workspace_id,
            "agent_id": agent_id,
        })
        row = existing_run
        if row is None:
            row = self.db.execute(
                "SELECT * FROM deck_plugin_bindings "
                "WHERE deck_id = ? AND workspace_id = ? AND status = 'active'",
                (deck_id, workspace_id),
            ).fetchone()
        if row is None:
            raise DreamLaunchRuntimeError("WORKFLOW_SELECTION_REQUIRED", 409)
        return PreparedDreamLaunchBinding(
            deck_plugin_id=str(row["deck_plugin_id"]),
            deck_plugin_version=str(row["deck_plugin_version"]),
            deck_plugin_binding_id=str(row["deck_plugin_binding_id"]),
            binding_revision=int(row["binding_revision"]),
        )


class RecordingTurnDispatcher:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []
        self.failures_remaining = 0

    def __call__(self, **values: object) -> bool:
        self.calls.append(values)
        if self.failures_remaining:
            self.failures_remaining -= 1
            raise RuntimeError("turn dispatch unavailable")
        return True


class DeferredMetadataPersistenceTurnDispatcher:
    """Model the Agent service persisting its accepted request a tick later."""

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []
        self.tasks: list[asyncio.Task[None]] = []

    def __call__(self, **values: object) -> asyncio.Task[None]:
        self.calls.append(values)
        message_id = str(values["message_id"])
        metadata = json.loads(json.dumps(values["metadata"]))

        async def persist_later() -> None:
            await asyncio.sleep(0)
            db = database.get_db()
            try:
                with db:
                    db.execute(
                        "UPDATE chat_message SET metadata = ? WHERE id = ?",
                        (json.dumps(metadata, sort_keys=True), message_id),
                    )
            finally:
                db.close()

        task = asyncio.create_task(persist_later())
        self.tasks.append(task)
        return task


class StoryWorkspaceDreamLaunchProductionTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_fixture = LegacyDatabaseModuleFixture(
            database,
            Path(self.temp_dir.name) / "dream-launch.db",
        )
        self.database_fixture.start(initialize_legacy_schema=True)
        self.environment = patch.dict(
            os.environ,
            {
                "INK_WORKFLOW_TOKEN_SECRET": (
                    "ink-dream-development-workflow-token-secret-v1"
                ),
                "INK_DECK_HOST_COMPATIBLE": "1",
                "INK_CLAUDE_AGENT_CONTRACT_COMPATIBLE": "1",
                "INK_STORY_SCHEMA_COMPATIBLE": "1",
                "INK_DECK_RUNTIME_CONFIG_COMPATIBLE": "1",
            },
            clear=False,
        )
        self.environment.start()
        db = database.get_db()
        try:
            with db:
                db.execute(
                    "INSERT INTO users (id, email, password_hash) VALUES (?, ?, 'hash')",
                    (int(ACTOR_ID), "dream-launch@example.test"),
                )
                db.execute(
                    "INSERT INTO users (id, email, password_hash) VALUES (?, ?, 'hash')",
                    (int(OTHER_ACTOR_ID), "dream-launch-other@example.test"),
                )
                db.execute(
                    "INSERT INTO story_workspace_workspaces (id, name, owner_id) "
                    "VALUES (?, 'Dream', ?), (?, 'Other', ?)",
                    (
                        WORKSPACE_ID,
                        int(ACTOR_ID),
                        OTHER_WORKSPACE_ID,
                        int(OTHER_ACTOR_ID),
                    ),
                )
                db.execute(
                    "INSERT INTO decks (id, name, owner_id, enabled) "
                    "VALUES (?, 'Dream Deck', ?, 1)",
                    (DECK_ID, int(ACTOR_ID)),
                )
                db.execute(
                    "INSERT INTO decks (id, name, owner_id, enabled) "
                    "VALUES (?, 'Alternate Dream Deck', ?, 1)",
                    (ALTERNATE_DECK_ID, int(ACTOR_ID)),
                )
            seed_launch_runtime_fixture(db)
        finally:
            db.close()
        self.turn_dispatcher = RecordingTurnDispatcher()
        self.runtime_port_calls: list[dict[str, object]] = []

    async def asyncTearDown(self) -> None:
        self.environment.stop()
        self.database_fixture.stop()
        self.temp_dir.cleanup()

    def make_launch_service(
        self,
        db,
        actor: dict[str, str],
        *,
        dispatch_before_claim=None,
        model_resolver=lambda _actor_id, _client_alias=None: "dream-balanced",
    ):
        application = StoryWorkflowRunApplicationService()
        options = {}
        if dispatch_before_claim is not None:
            options["dispatch_before_claim"] = dispatch_before_claim
        return build_dream_launch_application_service(
            db,
            preflight_service=application._preflight_service(db, actor),
            token_secret="ink-dream-development-workflow-token-secret-v1",
            runtime_port=FakeDreamLaunchRuntime(db, self.runtime_port_calls),
            turn_dispatcher=self.turn_dispatcher,
            platform_model_resolver=model_resolver,
            **options,
        )

    async def test_model_eligibility_failures_prevent_run_and_source_creation(self):
        db = database.get_db()
        try:
            selected_actor = {
                "actor_id": ACTOR_ID,
                "workspace_id": WORKSPACE_ID,
            }
            for error_code, status_code in [
                ("GATEWAY_AUTH_REQUIRED", 401),
                ("SUBSCRIPTION_TOKEN_ALLOWANCE_EXHAUSTED", 402),
                ("GATEWAY_MODEL_NOT_AVAILABLE", 403),
                ("GATEWAY_MODEL_SELECTION_STALE", 409),
                ("GATEWAY_RATE_LIMITED", 429),
                ("GATEWAY_UPSTREAM_ERROR", 502),
                ("GATEWAY_UNAVAILABLE", 503),
            ]:
                with self.subTest(status_code=status_code):
                    def unavailable(_actor_id, _client_alias=None):
                        raise GatewayInferenceError(error_code, status_code)

                    service = self.make_launch_service(
                        db,
                        selected_actor,
                        model_resolver=unavailable,
                    )
                    with self.assertRaises(DreamLaunchApplicationError) as captured:
                        await service.launch(
                            launch_command(),
                            actor_id=selected_actor["actor_id"],
                            workspace_id=selected_actor["workspace_id"],
                        )
                    self.assertEqual(
                        (captured.exception.code, captured.exception.status_code),
                        (error_code, status_code),
                    )
                    self.assertEqual(
                        db.execute("SELECT COUNT(*) AS count FROM workflow_runs").fetchone()["count"],
                        0,
                    )
                    self.assertEqual(
                        db.execute("SELECT COUNT(*) AS count FROM chat_message").fetchone()["count"],
                        0,
                    )
                    self.assertEqual(self.turn_dispatcher.calls, [])
        finally:
            db.close()

    async def test_unselected_chat_deck_cannot_enter_dream_launch(self):
        db = database.get_db()
        try:
            actor = {"actor_id": ACTOR_ID, "workspace_id": WORKSPACE_ID}
            command = launch_command().model_copy(update={"deck_id": ALTERNATE_DECK_ID})
            with self.assertRaises(DreamLaunchApplicationError) as captured:
                await self.make_launch_service(db, actor).launch(
                    command,
                    actor_id=ACTOR_ID,
                    workspace_id=WORKSPACE_ID,
                )
            self.assertEqual(
                (captured.exception.code, captured.exception.status_code),
                ("WORKFLOW_SELECTION_REQUIRED", 409),
            )
            self.assertEqual(
                db.execute("SELECT COUNT(*) FROM workflow_runs").fetchone()[0],
                0,
            )
        finally:
            db.close()

    async def test_default_dispatcher_reports_safe_terminal_stream_error(self):
        failures: list[dict[str, str]] = []

        class Factory:
            async def run_streaming(self, _request):
                yield ChatStreamAdapter.encode(
                    NormalizedAgentEvent.create(
                        "error",
                        {
                            "errorText": (
                                "[GATEWAY_UNAVAILABLE] upstream unavailable"
                            )
                        },
                    )
                )
                yield ChatStreamAdapter.encode(
                    NormalizedAgentEvent.create(
                        "finish", {"finishReason": "error"}
                    )
                )

        async def record_failure(**values):
            failures.append(values)

        dispatcher = build_dream_agent_turn_dispatcher(
            factory=Factory(),
            request_factory=lambda **values: values,
            failure_handler=record_failure,
        )
        context = StoryWorkspaceDreamRunContext(
            workflow_run_id="run_" + "1" * 32,
            thread_id="thread-dream-error",
            deck_id=DECK_ID,
            deck_plugin_id=BUILTIN_DECK_PLUGIN_ID,
            deck_plugin_version=BUILTIN_DECK_PLUGIN_VERSION,
            deck_plugin_binding_id="dpb_" + "2" * 32,
            binding_revision=1,
            deck_runtime_snapshot_id="drs_" + "3" * 32,
            runtime_plugin_lock_id="rpl_" + "4" * 32,
        )
        task = dispatcher(
            actor_id=ACTOR_ID,
            thread_id=context.thread_id,
            message_id="dream-launch-error-message",
            parts=[{"type": "text", "text": "launch"}],
            metadata={},
            context=context,
            system_prompt=None,
        )
        await task
        self.assertEqual(
            failures,
            [{
                "workflow_run_id": context.workflow_run_id,
                "actor_id": ACTOR_ID,
                "message_id": "dream-launch-error-message",
                "error_code": "GATEWAY_UNAVAILABLE",
            }],
        )

    async def test_launch_registry_cancels_and_awaits_owned_turn_drain(self):
        turn_started = asyncio.Event()
        failure_started = asyncio.Event()
        release_failure = asyncio.Event()
        failures: list[dict[str, str]] = []

        class BlockingFactory:
            async def run_streaming(self, _request):
                turn_started.set()
                await asyncio.Event().wait()
                yield  # pragma: no cover - cancellation is the contract

        async def record_failure(**values):
            failures.append(values)
            failure_started.set()
            await release_failure.wait()

        registry = DreamLaunchTaskRegistry()
        dispatcher = build_dream_agent_turn_dispatcher(
            factory=BlockingFactory(),
            request_factory=lambda **values: values,
            failure_handler=record_failure,
            task_registry=registry,
        )
        context = StoryWorkspaceDreamRunContext(
            workflow_run_id="run_" + "5" * 32,
            thread_id="thread-dream-cancel",
            deck_id=DECK_ID,
            deck_plugin_id=BUILTIN_DECK_PLUGIN_ID,
            deck_plugin_version=BUILTIN_DECK_PLUGIN_VERSION,
            deck_plugin_binding_id="dpb_" + "6" * 32,
            binding_revision=1,
            deck_runtime_snapshot_id="drs_" + "7" * 32,
            runtime_plugin_lock_id="rpl_" + "8" * 32,
        )
        dispatcher(
            actor_id=ACTOR_ID,
            thread_id=context.thread_id,
            message_id="dream-launch-cancel-message",
            parts=[{"type": "text", "text": "launch"}],
            metadata={},
            context=context,
            system_prompt=None,
        )
        await turn_started.wait()

        close_task = asyncio.create_task(registry.aclose())
        await failure_started.wait()
        self.assertFalse(close_task.done())
        self.assertEqual(registry.diagnostics()["launch_owned_tasks"], 1)
        release_failure.set()
        await close_task

        self.assertEqual(
            failures,
            [{
                "workflow_run_id": context.workflow_run_id,
                "actor_id": ACTOR_ID,
                "message_id": "dream-launch-cancel-message",
                "error_code": "DREAM_AGENT_DISPATCH_CANCELLED",
            }],
        )
        self.assertEqual(
            registry.diagnostics(),
            {"launch_owned_tasks": 0, "launch_running_tasks": 0},
        )

    async def test_closed_launch_registry_rejects_before_turn_creation(self):
        factory_called = False

        class Factory:
            async def run_streaming(self, _request):
                nonlocal factory_called
                factory_called = True
                yield ChatStreamAdapter.encode(
                    NormalizedAgentEvent.create(
                        "finish", {"finishReason": "stop"}
                    )
                )

        registry = DreamLaunchTaskRegistry()
        await registry.aclose()
        dispatcher = build_dream_agent_turn_dispatcher(
            factory=Factory(),
            request_factory=lambda **values: values,
            task_registry=registry,
        )
        context = StoryWorkspaceDreamRunContext(
            workflow_run_id="run_" + "9" * 32,
            thread_id="thread-dream-closed",
            deck_id=DECK_ID,
            deck_plugin_id=BUILTIN_DECK_PLUGIN_ID,
            deck_plugin_version=BUILTIN_DECK_PLUGIN_VERSION,
            deck_plugin_binding_id="dpb_" + "a" * 32,
            binding_revision=1,
            deck_runtime_snapshot_id="drs_" + "b" * 32,
            runtime_plugin_lock_id="rpl_" + "c" * 32,
        )

        with self.assertRaisesRegex(RuntimeError, "registry is closed"):
            dispatcher(
                actor_id=ACTOR_ID,
                thread_id=context.thread_id,
                message_id="dream-launch-closed-message",
                parts=[{"type": "text", "text": "launch"}],
                metadata={},
                context=context,
                system_prompt=None,
            )

        self.assertFalse(factory_called)
        self.assertEqual(
            registry.diagnostics(),
            {"launch_owned_tasks": 0, "launch_running_tasks": 0},
        )

    async def test_terminal_dispatch_error_marks_run_and_source_failed(self):
        selected_actor = {
            "actor_id": ACTOR_ID,
            "workspace_id": WORKSPACE_ID,
        }
        db = database.get_db()
        try:
            service = self.make_launch_service(db, selected_actor)
            context = await service.launch(
                launch_command(),
                actor_id=selected_actor["actor_id"],
                workspace_id=selected_actor["workspace_id"],
            )
            message_id = self.turn_dispatcher.calls[0]["message_id"]
            await DreamLaunchFailureRecorder(
                "ink-dream-development-workflow-token-secret-v1"
            ).record(
                workflow_run_id=context.workflow_run_id,
                actor_id=ACTOR_ID,
                message_id=str(message_id),
                error_code="GATEWAY_UNAVAILABLE",
            )
        finally:
            db.close()

        read_db = database.get_db()
        try:
            run = read_db.execute(
                "SELECT status, failed_step, error_code FROM workflow_runs WHERE id = ?",
                (context.workflow_run_id,),
            ).fetchone()
            source = read_db.execute(
                "SELECT metadata FROM chat_message WHERE id = ?",
                (message_id,),
            ).fetchone()
            metadata = json.loads(source["metadata"])
            self.assertEqual(
                (run["status"], run["failed_step"], run["error_code"]),
                ("failed", "dream_agent_dispatch", "GATEWAY_UNAVAILABLE"),
            )
            self.assertEqual(metadata["dispatchStatus"], "failed")
            self.assertEqual(metadata["dispatchErrorCode"], "GATEWAY_UNAVAILABLE")
        finally:
            read_db.close()

    async def start(
        self,
        command: StoryWorkspaceDreamLaunchCommand,
        actor=None,
        *,
        dispatch_before_claim=None,
    ):
        selected_actor = actor or {
            "actor_id": ACTOR_ID,
            "workspace_id": WORKSPACE_ID,
        }
        db = database.get_db()
        try:
            return await self.make_launch_service(
                db,
                selected_actor,
                dispatch_before_claim=dispatch_before_claim,
            ).launch(
                command,
                actor_id=selected_actor["actor_id"],
                workspace_id=selected_actor["workspace_id"],
            )
        finally:
            db.close()

    async def test_admin_prepared_binding_creates_authoritative_run_and_dispatches(self) -> None:
        context = await self.start(launch_command())

        self.assertEqual(context.deck_id, DECK_ID)
        self.assertEqual(context.deck_plugin_id, BUILTIN_DECK_PLUGIN_ID)
        self.assertEqual(BUILTIN_CLAUDE_PLUGIN_ID, "ink-dream-story@platform-builtin")
        db = database.get_db()
        try:
            materialization = db.execute(
                "SELECT * FROM runtime_plugin_materializations"
            ).fetchone()
            deck_installation = db.execute(
                "SELECT * FROM deck_plugin_installations WHERE scope_id = ?",
                (WORKSPACE_ID,),
            ).fetchone()
            binding = db.execute(
                "SELECT * FROM deck_plugin_bindings WHERE deck_id = ? AND status = 'active'",
                (DECK_ID,),
            ).fetchone()
            adapter_refs = db.execute(
                "SELECT COUNT(*) FROM deck_claude_plugin_refs WHERE deck_id = ?",
                (DECK_ID,),
            ).fetchone()[0]
            source = db.execute(
                "SELECT message.*, thread.deck_id, thread.user_id "
                "FROM chat_message AS message JOIN chat_thread AS thread "
                "ON thread.id = message.thread_id"
            ).fetchone()
            run = db.execute(
                "SELECT * FROM workflow_runs WHERE id = ?",
                (context.workflow_run_id,),
            ).fetchone()
        finally:
            db.close()

        self.assertEqual(deck_installation["status"], "ready")
        self.assertEqual(binding["deck_plugin_id"], BUILTIN_DECK_PLUGIN_ID)
        self.assertEqual(adapter_refs, 0)
        self.assertEqual(source["deck_id"], DECK_ID)
        self.assertEqual(str(source["user_id"]), ACTOR_ID)
        self.assertEqual(run["source_voice_thread_id"], context.thread_id)
        self.assertEqual(run["source_message_id"], source["id"])
        self.assertIsNotNone(run["source_message_time"])

        self.assertEqual(len(self.turn_dispatcher.calls), 1)
        dispatch = self.turn_dispatcher.calls[0]
        self.assertFalse(dispatch["resume"])
        self.assertEqual(dispatch["context"], context)
        launch_text = dispatch["parts"][0]["text"]
        project_slug = story_workspace_canonical_project_fallback_slug(
            launch_command().goal
        )
        self.assertIn("首次 Dream 的最小工作台初始化", launch_text)
        self.assertIn(
            f"服务器已分配 project_id/project_slug：{project_slug}", launch_text
        )
        self.assertIn("assets/characters/lead-a.md", launch_text)
        self.assertIn("assets/characters/lead-b.md", launch_text)
        self.assertIn("assets/scenes/terminal.md", launch_text)
        self.assertIn(f"stories/{project_slug}/project.yaml", launch_text)
        self.assertIn(
            f"stories/{project_slug}/episodes/EP01/storyboard.yaml", launch_text
        )
        self.assertIn("宿主会在 root turn 成功结束后自动同步", launch_text)
        self.assertIn(
            "不要调用 Agent、WebFetch、WebSearch、AskUserQuestion 或 Dream MCP",
            launch_text,
        )
        self.assertIn("五类工作台文件写完后立即结束", launch_text)

    async def test_launch_runtime_port_receives_current_plan_before_workflow_writes(self) -> None:
        await self.start(launch_command())

        self.assertEqual(
            [call["operation"] for call in self.runtime_port_calls],
            ["scope", "prepare"],
        )
        self.assertEqual(self.runtime_port_calls[1]["mode"], "current")

    async def test_replay_uses_admin_runtime_port_without_local_materialization_write(self) -> None:
        first = await self.start(launch_command())
        db = database.get_db()
        try:
            db.execute("DELETE FROM runtime_plugin_materializations")
            db.commit()
        finally:
            db.close()

        replay = await self.start(launch_command())

        self.assertEqual(replay, first)
        db = database.get_db()
        try:
            self.assertIsNone(
                db.execute("SELECT 1 FROM runtime_plugin_materializations").fetchone()
            )
        finally:
            db.close()
        prepare_modes = [
            call["mode"]
            for call in self.runtime_port_calls
            if call["operation"] == "prepare"
        ]
        self.assertEqual(prepare_modes, ["current", "replay"])

    async def test_replay_and_conflict_preserve_single_source_run_and_dispatch(self) -> None:
        first = await self.start(launch_command())
        second = await self.start(launch_command())
        self.assertEqual(second, first)

        with self.assertRaises(DreamLaunchIdempotencyConflict):
            await self.start(launch_command(goal="不同的故事目标"))

        db = database.get_db()
        try:
            counts = {
                table: db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in (
                    "chat_thread",
                    "chat_message",
                    "workflow_runs",
                    "deck_plugin_bindings",
                    "deck_plugin_installations",
                    "runtime_plugin_materializations",
                )
            }
            metadata = json.loads(
                db.execute("SELECT metadata FROM chat_message").fetchone()[0]
            )
        finally:
            db.close()
        self.assertTrue(all(value == 1 for value in counts.values()), counts)
        self.assertEqual(len(self.turn_dispatcher.calls), 1)
        self.assertEqual(metadata["dispatchStatus"], "dispatched")
        self.assertEqual(metadata["workflowRunId"], first.workflow_run_id)

    async def test_same_key_changed_deck_is_an_idempotency_conflict(self) -> None:
        await self.start(launch_command())

        with self.assertRaises(DreamLaunchIdempotencyConflict):
            await self.start(launch_command(deckId=ALTERNATE_DECK_ID))

        db = database.get_db()
        try:
            alternate_bindings = db.execute(
                "SELECT COUNT(*) FROM deck_plugin_bindings WHERE deck_id = ?",
                (ALTERNATE_DECK_ID,),
            ).fetchone()[0]
        finally:
            db.close()
        self.assertEqual(alternate_bindings, 0)

    async def test_replay_uses_frozen_binding_after_active_revision_drifts(self) -> None:
        first = await self.start(launch_command())
        replacement_binding_id = "dpb_" + "8" * 32
        db = database.get_db()
        try:
            current = db.execute(
                "SELECT * FROM deck_plugin_bindings "
                "WHERE deck_id = ? AND status = 'active'",
                (DECK_ID,),
            ).fetchone()
            with db:
                db.execute(
                    "UPDATE deck_plugin_bindings SET status = 'stale' "
                    "WHERE deck_plugin_binding_id = ?",
                    (current["deck_plugin_binding_id"],),
                )
                db.execute(
                    "INSERT INTO deck_plugin_bindings ("
                    "deck_plugin_binding_id, deck_id, workspace_id, creator_id, "
                    "deck_plugin_id, deck_plugin_version, binding_revision, "
                    "status, applied_to) "
                    "VALUES (?, ?, ?, ?, ?, ?, 2, 'active', 'next_run')",
                    (
                        replacement_binding_id,
                        DECK_ID,
                        WORKSPACE_ID,
                        ACTOR_ID,
                        BUILTIN_DECK_PLUGIN_ID,
                        BUILTIN_DECK_PLUGIN_VERSION,
                    ),
                )
        finally:
            db.close()

        replayed = await self.start(launch_command())

        self.assertEqual(replayed, first)
        self.assertEqual(replayed.binding_revision, 1)
        db = database.get_db()
        try:
            active = db.execute(
                "SELECT deck_plugin_binding_id, binding_revision "
                "FROM deck_plugin_bindings WHERE deck_id = ? AND status = 'active'",
                (DECK_ID,),
            ).fetchone()
        finally:
            db.close()
        self.assertEqual(active["deck_plugin_binding_id"], replacement_binding_id)
        self.assertEqual(active["binding_revision"], 2)
        self.assertEqual(len(self.turn_dispatcher.calls), 1)

    @unittest.skip(
        "legacy SQLite cannot model PostgreSQL row-lock concurrency; covered by owned-PG contracts"
    )
    async def test_concurrent_pending_replay_claims_one_agent_turn(self) -> None:
        self.turn_dispatcher.failures_remaining = 1
        with self.assertRaisesRegex(RuntimeError, "turn dispatch unavailable"):
            await self.start(launch_command())

        self.turn_dispatcher = RecordingTurnDispatcher()
        before_claim = threading.Barrier(2)

        def replay():
            return asyncio.run(
                self.start(
                    launch_command(),
                    dispatch_before_claim=lambda: before_claim.wait(timeout=5),
                )
            )

        first, second = await asyncio.gather(
            asyncio.to_thread(replay),
            asyncio.to_thread(replay),
        )

        self.assertEqual(first, second)
        self.assertEqual(len(self.turn_dispatcher.calls), 1)

    async def test_fresh_dispatch_claim_is_not_duplicated(self) -> None:
        self.turn_dispatcher.failures_remaining = 1
        with self.assertRaisesRegex(RuntimeError, "turn dispatch unavailable"):
            await self.start(launch_command())

        self.turn_dispatcher = RecordingTurnDispatcher()
        self._set_dispatch_claim(datetime.now(UTC))

        await self.start(launch_command())

        self.assertEqual(self.turn_dispatcher.calls, [])
        metadata = self._read_source_metadata()
        self.assertEqual(metadata["dispatchStatus"], "dispatching")
        self.assertEqual(metadata["dispatchClaimId"], "claim-from-another-worker")

    async def test_stale_dispatch_claim_is_recovered(self) -> None:
        self.turn_dispatcher.failures_remaining = 1
        with self.assertRaisesRegex(RuntimeError, "turn dispatch unavailable"):
            await self.start(launch_command())

        self.turn_dispatcher = RecordingTurnDispatcher()
        self._set_dispatch_claim(datetime.now(UTC) - timedelta(minutes=10))

        await self.start(launch_command())

        self.assertEqual(len(self.turn_dispatcher.calls), 1)
        metadata = self._read_source_metadata()
        self.assertEqual(metadata["dispatchStatus"], "dispatched")
        self.assertNotIn("dispatchClaimId", metadata)
        self.assertNotIn("dispatchClaimedAt", metadata)

    async def test_agent_metadata_persistence_cannot_restore_dispatch_claim(
        self,
    ) -> None:
        deferred_dispatcher = DeferredMetadataPersistenceTurnDispatcher()
        self.turn_dispatcher = deferred_dispatcher

        await self.start(launch_command())
        await asyncio.gather(*deferred_dispatcher.tasks)

        metadata = self._read_source_metadata()
        self.assertEqual(metadata["dispatchStatus"], "dispatched")
        self.assertNotIn("dispatchClaimId", metadata)
        self.assertNotIn("dispatchClaimedAt", metadata)

    async def test_missing_current_binding_fails_before_source_creation(self) -> None:
        db = database.get_db()
        try:
            with db:
                db.execute(
                    "UPDATE deck_plugin_bindings SET status = 'stale' "
                    "WHERE deck_id = ? AND status = 'active'",
                    (DECK_ID,),
                )
        finally:
            db.close()

        with self.assertRaises(DreamLaunchApplicationError) as captured:
            await self.start(launch_command(idempotencyKey="dream-api-no-binding"))

        self.assertEqual(
            (captured.exception.code, captured.exception.status_code),
            ("WORKFLOW_SELECTION_REQUIRED", 409),
        )
        db = database.get_db()
        try:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM chat_message").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM workflow_runs").fetchone()[0], 0)
        finally:
            db.close()

    async def test_slash_command_remains_the_unmodified_launch_text_prefix(self) -> None:
        goal = "/drama-forge:drama-init"

        await self.start(launch_command(goal=goal))

        launch_text = self.turn_dispatcher.calls[0]["parts"][0]["text"]
        self.assertTrue(launch_text.startswith(goal))
        self.assertIn("首次 Dream 的最小工作台初始化", launch_text)
        self.assertIn(
            "不要调用 Agent、WebFetch、WebSearch、AskUserQuestion 或 Dream MCP",
            launch_text,
        )

    async def test_launch_assigns_canonical_project_identity_before_storyboard(self) -> None:
        command = launch_command()
        await self.start(command)

        launch_text = self.turn_dispatcher.calls[0]["parts"][0]["text"]
        project_slug = story_workspace_canonical_project_fallback_slug(command.goal)
        self.assertIn(
            f"服务器已分配 project_id/project_slug：{project_slug}", launch_text
        )
        self.assertIn("必须原样使用", launch_text)
        self.assertIn("不要计算、查询或验证哈希", launch_text)
        self.assertIn(f"stories/{project_slug}/project.yaml", launch_text)
        self.assertIn(
            f"project_id 与 project_slug 都严格等于 {project_slug}", launch_text
        )
        self.assertIn(
            f"stories/{project_slug}/episodes/EP01/storyboard.yaml", launch_text
        )
        self.assertNotIn("mcp__", launch_text)
        self.assertNotIn("expectedBindingRevision", launch_text)

    async def test_dispatch_exception_leaves_pending_envelope_replayable(self) -> None:
        self.turn_dispatcher.failures_remaining = 1

        with self.assertRaisesRegex(RuntimeError, "turn dispatch unavailable"):
            await self.start(launch_command())
        db = database.get_db()
        try:
            pending = json.loads(
                db.execute("SELECT metadata FROM chat_message").fetchone()[0]
            )
        finally:
            db.close()
        self.assertEqual(pending["dispatchStatus"], "pending")

        replayed = await self.start(launch_command())
        db = database.get_db()
        try:
            dispatched = json.loads(
                db.execute("SELECT metadata FROM chat_message").fetchone()[0]
            )
            run_count = db.execute("SELECT COUNT(*) FROM workflow_runs").fetchone()[0]
        finally:
            db.close()
        self.assertEqual(dispatched["dispatchStatus"], "dispatched")
        self.assertEqual(dispatched["workflowRunId"], replayed.workflow_run_id)
        self.assertEqual(run_count, 1)
        self.assertEqual(len(self.turn_dispatcher.calls), 2)

    def _set_dispatch_claim(self, claimed_at: datetime) -> None:
        db = database.get_db()
        try:
            row = db.execute("SELECT id, metadata FROM chat_message").fetchone()
            metadata = json.loads(row["metadata"])
            metadata.update({
                "dispatchStatus": "dispatching",
                "dispatchClaimId": "claim-from-another-worker",
                "dispatchClaimedAt": claimed_at.isoformat(),
            })
            with db:
                db.execute(
                    "UPDATE chat_message SET metadata = ? WHERE id = ?",
                    (json.dumps(metadata, sort_keys=True), row["id"]),
                )
        finally:
            db.close()

    @staticmethod
    def _read_source_metadata() -> dict[str, object]:
        db = database.get_db()
        try:
            return json.loads(
                db.execute("SELECT metadata FROM chat_message").fetchone()[0]
            )
        finally:
            db.close()

    async def test_cross_actor_deck_launch_is_denied_before_source_creation(self) -> None:
        with self.assertRaises(DreamLaunchApplicationError) as captured:
            await self.start(
                launch_command(),
                actor={
                    "actor_id": OTHER_ACTOR_ID,
                    "workspace_id": OTHER_WORKSPACE_ID,
                },
            )
        self.assertEqual(
            (captured.exception.code, captured.exception.status_code),
            ("DECK_ACCESS_DENIED", 404),
        )

        db = database.get_db()
        try:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM chat_thread").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM chat_message").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM workflow_runs").fetchone()[0], 0)
        finally:
            db.close()

    async def test_admin_runtime_scope_failure_is_mapped_before_source_creation(self) -> None:
        class DeniedRuntime(FakeDreamLaunchRuntime):
            async def authorize(self, **_values) -> None:
                raise DreamLaunchRuntimeError("AGENT_ACCESS_DENIED", 404)

        actor = {"actor_id": ACTOR_ID, "workspace_id": WORKSPACE_ID}
        db = database.get_db()
        try:
            application = StoryWorkflowRunApplicationService()
            service = build_dream_launch_application_service(
                db,
                preflight_service=application._preflight_service(db, actor),
                token_secret="ink-dream-development-workflow-token-secret-v1",
                runtime_port=DeniedRuntime(db, self.runtime_port_calls),
                turn_dispatcher=self.turn_dispatcher,
            )
            with self.assertRaises(DreamLaunchApplicationError) as captured:
                await service.launch(
                    launch_command(agentId="voice-denied"),
                    actor_id=ACTOR_ID,
                    workspace_id=WORKSPACE_ID,
                )
        finally:
            db.close()

        self.assertEqual(
            (captured.exception.code, captured.exception.status_code),
            ("AGENT_ACCESS_DENIED", 404),
        )
        read_db = database.get_db()
        try:
            self.assertEqual(read_db.execute("SELECT COUNT(*) FROM chat_message").fetchone()[0], 0)
            self.assertEqual(read_db.execute("SELECT COUNT(*) FROM workflow_runs").fetchone()[0], 0)
        finally:
            read_db.close()
