"""Focused binding persistence, validation, concurrency, and API tests."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import database
from models.deck_plugin import (
    DeckPluginBindingUpdateRequest,
    DeckPluginManifestV1,
    DeckPluginSelectionRequest,
    DeckRuntimePluginLock,
    RuntimePluginLockEntry,
)
from routers import deck_plugin_binding as binding_router
from services.deck_plugin.binding_service import (
    BindingAccessError,
    BindingRevisionConflict,
    BindingSelectionRejected,
    BindingService,
)
from services.deck_plugin.compatibility_service import RuntimeContext
from services.deck_plugin.selection_validation_service import (
    RUNTIME_CONTEXT_UNAVAILABLE,
    SelectionValidationService,
)
from tests.test_deck_plugin_manifest import valid_manifest_data


PLUGIN_ID = "voice-decks.story-dramatize"
VERSION = "3.1.0"
DECK_ID = "deck-binding-test"
WORKSPACE_ID = "workspace-binding-test"
RUNTIME_PLUGIN_ID = "ink-dream-tools@voice-decks"
DIGEST = "sha256:" + "d" * 64


class BindingFixture:
    def __init__(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self.temp_dir.name) / "binding.db"
        self.db = self.connect()
        database.create_tables(self.db)
        self.runtime_updates: dict = {}
        self.manifest = self._seed()
        self.validator = SelectionValidationService(
            self.db,
            runtime_context_resolver=self.runtime_context,
        )
        self.binding = BindingService(
            self.db,
            selection_validator=self.validator,
        )

    def connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=10, check_same_thread=False)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def close(self) -> None:
        self.db.close()
        self.temp_dir.cleanup()

    def _seed(self) -> DeckPluginManifestV1:
        self.db.execute(
            """
            INSERT INTO users (id, email, password_hash)
            VALUES (1, 'owner@example.com', 'hash'),
                   (2, 'other@example.com', 'hash')
            """
        )
        self.db.execute(
            "INSERT INTO decks (id, name, owner_id) VALUES (?, 'Binding Deck', 1)",
            (DECK_ID,),
        )
        self.db.execute(
            """
            INSERT INTO story_workspace_workspaces (id, name, owner_id)
            VALUES (?, 'Binding Workspace', 1)
            """,
            (WORKSPACE_ID,),
        )
        data = valid_manifest_data()
        data["status"] = "published"
        manifest = DeckPluginManifestV1.model_validate(data)
        manifest_hash = "sha256:" + hashlib.sha256(
            manifest.model_dump_json().encode("utf-8")
        ).hexdigest()
        runtime_lock = DeckRuntimePluginLock(
            runtime_plugin_lock_id="rpl_" + "2" * 32,
            deck_plugin_id=PLUGIN_ID,
            deck_plugin_version=VERSION,
            deck_plugin_manifest_hash=manifest_hash,
            claude_code_plugins=[
                RuntimePluginLockEntry(
                    claude_code_plugin_id=RUNTIME_PLUGIN_ID,
                    resolved_version="1.4.2",
                    source_ref="marketplace://voice-decks@2026-08-01",
                    artifact_digest=DIGEST,
                    required=True,
                    capability_bindings=[
                        "workspace.files.read",
                        "story.result.produce",
                    ],
                )
            ],
            created_at=datetime.now(UTC),
            production_ready=False,
            production_readiness_reasons=["non-production test fixture"],
        )
        self.db.execute(
            """
            INSERT INTO deck_plugin_releases (
                id, deck_plugin_id, deck_plugin_version, display_name,
                status, manifest_json, manifest_hash, workflow_definition_ref,
                capabilities_json
            ) VALUES (?, ?, ?, ?, 'published', ?, ?, ?, ?)
            """,
            (
                "dr_" + "3" * 32,
                PLUGIN_ID,
                VERSION,
                manifest.display_name,
                manifest.model_dump_json(),
                manifest_hash,
                manifest.workflow.workflow_definition_ref,
                json.dumps(manifest.capabilities),
            ),
        )
        self.db.execute(
            """
            INSERT INTO deck_runtime_plugin_locks (
                id, deck_plugin_id, deck_plugin_version,
                deck_plugin_manifest_hash, lock_json
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                runtime_lock.runtime_plugin_lock_id,
                PLUGIN_ID,
                VERSION,
                manifest_hash,
                runtime_lock.model_dump_json(),
            ),
        )
        self.db.execute(
            """
            INSERT INTO deck_plugin_installations (
                id, scope_type, scope_id, deck_plugin_id,
                installed_versions_json, default_version, status,
                approved_capabilities_json, source_policy_id
            ) VALUES (?, 'workspace', ?, ?, ?, ?, 'ready', ?, 'policy-default')
            """,
            (
                "dpi_" + "4" * 32,
                WORKSPACE_ID,
                PLUGIN_ID,
                json.dumps([VERSION]),
                VERSION,
                json.dumps(manifest.capabilities),
            ),
        )
        self.db.commit()
        return manifest

    async def runtime_context(
        self,
        _plugin_id: str,
        _version: str,
        _workspace_id: str,
        _actor_id: str,
    ) -> RuntimeContext:
        capabilities = set(self.manifest.capabilities)
        data = {
            "deck_host_compatible": True,
            "claude_agent_compatible": True,
            "story_schema_compatible": True,
            "deck_runtime_config_compatible": True,
            "deck_runtime_snapshot_policy": capabilities,
            "user_and_workspace_grants": capabilities,
            "claude_agent_runtime_supported": capabilities,
            "materialized_runtime_plugin_ids": {RUNTIME_PLUGIN_ID},
            "loadable_runtime_plugin_ids": {RUNTIME_PLUGIN_ID},
        }
        data.update(self.runtime_updates)
        return RuntimeContext(**data)

    @staticmethod
    def request(expected_revision: int) -> DeckPluginBindingUpdateRequest:
        return DeckPluginBindingUpdateRequest(
            deck_plugin_id=PLUGIN_ID,
            deck_plugin_version=VERSION,
            expected_binding_revision=expected_revision,
            apply_to="next_run",
        )


class BindingModelSchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = BindingFixture()

    def tearDown(self) -> None:
        self.fixture.close()

    def test_requests_require_exact_semver_and_next_run(self) -> None:
        valid = BindingFixture.request(0)
        self.assertEqual(valid.deck_plugin_version, VERSION)
        for mutable in ("latest", ">=3.1.0", "3.1.x", "", "3.1"):
            with self.subTest(mutable=mutable), self.assertRaises(ValidationError):
                DeckPluginSelectionRequest(
                    deck_plugin_id=PLUGIN_ID,
                    deck_plugin_version=mutable,
                    apply_to="next_run",
                )
        with self.assertRaises(ValidationError):
            DeckPluginSelectionRequest(
                deck_plugin_id=PLUGIN_ID,
                deck_plugin_version=VERSION,
                apply_to="current_run",
            )

    def test_binding_schema_indexes_constraints_and_initialization_are_idempotent(self) -> None:
        database.create_tables(self.fixture.db)
        table = self.fixture.db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='deck_plugin_bindings'"
        ).fetchone()
        self.assertIsNotNone(table)
        indexes = {
            row["name"]
            for row in self.fixture.db.execute(
                "PRAGMA index_list('deck_plugin_bindings')"
            )
        }
        self.assertTrue(
            {
                "idx_deck_plugin_bindings_active_deck",
                "idx_deck_plugin_bindings_deck_revision",
                "idx_deck_plugin_bindings_workspace",
                "idx_deck_plugin_bindings_release",
            }.issubset(indexes)
        )


class BindingServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.fixture = BindingFixture()

    def tearDown(self) -> None:
        self.fixture.close()

    async def test_first_save_and_subsequent_revisions_are_monotonic_and_auditable(self) -> None:
        first = await self.fixture.binding.save(
            deck_id=DECK_ID,
            actor_id="1",
            request=BindingFixture.request(0),
        )
        second = await self.fixture.binding.save(
            deck_id=DECK_ID,
            actor_id="1",
            request=BindingFixture.request(1),
        )
        self.assertEqual((first.binding_revision, second.binding_revision), (1, 2))
        rows = self.fixture.db.execute(
            "SELECT binding_revision, status FROM deck_plugin_bindings "
            "ORDER BY binding_revision"
        ).fetchall()
        self.assertEqual(
            [(row["binding_revision"], row["status"]) for row in rows],
            [(1, "stale"), (2, "active")],
        )
        state = await self.fixture.binding.get_current_state(
            deck_id=DECK_ID,
            actor_id="1",
        )
        self.assertEqual(state.binding_revision, 2)
        self.assertEqual(state.binding.deck_plugin_binding_id, second.deck_plugin_binding_id)

    async def test_stale_revision_returns_conflict_without_writing(self) -> None:
        await self.fixture.binding.save(
            deck_id=DECK_ID,
            actor_id="1",
            request=BindingFixture.request(0),
        )
        with self.assertRaises(BindingRevisionConflict) as caught:
            await self.fixture.binding.save(
                deck_id=DECK_ID,
                actor_id="1",
                request=BindingFixture.request(0),
            )
        self.assertEqual(caught.exception.current_revision, 1)
        count = self.fixture.db.execute(
            "SELECT COUNT(*) FROM deck_plugin_bindings"
        ).fetchone()[0]
        self.assertEqual(count, 1)

    async def test_selection_validation_covers_authoritative_failure_states(self) -> None:
        passed = await self.fixture.validator.validate(
            deck_plugin_id=PLUGIN_ID,
            deck_plugin_version=VERSION,
            workspace_id=WORKSPACE_ID,
            actor_id="1",
        )
        self.assertTrue(passed.selectable)

        cases = (
            ("disabled", {}, "DECK_PLUGIN_DISABLED"),
            ("upgrade_pending", {}, "DECK_PLUGIN_UPGRADE_PENDING"),
            ("ready", {"deck_host_compatible": False}, "DECK_HOST_INCOMPATIBLE"),
            ("ready", {"user_and_workspace_grants": set()}, "WORKFLOW_PERMISSION_DENIED"),
            ("ready", {"materialized_runtime_plugin_ids": set()}, "RUNTIME_PLUGIN_NOT_READY"),
        )
        for installation_status, context, expected_code in cases:
            with self.subTest(expected_code=expected_code):
                self.fixture.db.execute(
                    "UPDATE deck_plugin_installations SET status = ?",
                    (installation_status,),
                )
                self.fixture.db.commit()
                self.fixture.runtime_updates = context
                result = await self.fixture.validator.validate(
                    deck_plugin_id=PLUGIN_ID,
                    deck_plugin_version=VERSION,
                    workspace_id=WORKSPACE_ID,
                    actor_id="1",
                )
                self.assertFalse(result.selectable)
                self.assertEqual(result.reason_code, expected_code)
        self.fixture.runtime_updates = {}
        self.fixture.db.execute(
            "UPDATE deck_plugin_installations SET status = 'ready'"
        )
        self.fixture.db.execute(
            "UPDATE deck_plugin_releases SET status = 'revoked'"
        )
        self.fixture.db.commit()
        revoked = await self.fixture.validator.validate(
            deck_plugin_id=PLUGIN_ID,
            deck_plugin_version=VERSION,
            workspace_id=WORKSPACE_ID,
            actor_id="1",
        )
        self.assertEqual(revoked.reason_code, "DECK_PLUGIN_UNAVAILABLE")

    async def test_validation_is_side_effect_free_and_default_adapter_fails_closed(self) -> None:
        before = self.fixture.db.execute(
            "SELECT COUNT(*) FROM deck_plugin_bindings"
        ).fetchone()[0]
        result = await self.fixture.validator.validate(
            deck_plugin_id=PLUGIN_ID,
            deck_plugin_version=VERSION,
            workspace_id=WORKSPACE_ID,
            actor_id="1",
        )
        self.assertTrue(result.selectable)
        after = self.fixture.db.execute(
            "SELECT COUNT(*) FROM deck_plugin_bindings"
        ).fetchone()[0]
        self.assertEqual((before, after), (0, 0))
        self.assertIsNone(
            self.fixture.db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='workflow_runs'"
            ).fetchone()
        )

        fail_closed = SelectionValidationService(self.fixture.db)
        unavailable = await fail_closed.validate(
            deck_plugin_id=PLUGIN_ID,
            deck_plugin_version=VERSION,
            workspace_id=WORKSPACE_ID,
            actor_id="1",
        )
        self.assertFalse(unavailable.selectable)
        self.assertEqual(unavailable.reason_code, RUNTIME_CONTEXT_UNAVAILABLE)

    async def test_binding_updates_never_rewrite_historical_workflow_sources(self) -> None:
        self.fixture.db.execute(
            """
            CREATE TABLE workflow_runs (
              id TEXT PRIMARY KEY,
              deck_plugin_binding_id TEXT,
              binding_revision INTEGER,
              deck_plugin_id TEXT,
              deck_plugin_version TEXT,
              runtime_plugin_lock_id TEXT
            )
            """
        )
        frozen = (
            "run-historical",
            "dpb_" + "9" * 32,
            7,
            PLUGIN_ID,
            "2.9.0",
            "rpl_" + "8" * 32,
        )
        self.fixture.db.execute(
            "INSERT INTO workflow_runs VALUES (?, ?, ?, ?, ?, ?)",
            frozen,
        )
        self.fixture.db.commit()
        await self.fixture.binding.save(
            deck_id=DECK_ID,
            actor_id="1",
            request=BindingFixture.request(0),
        )
        actual = tuple(
            self.fixture.db.execute(
                "SELECT * FROM workflow_runs WHERE id = 'run-historical'"
            ).fetchone()
        )
        self.assertEqual(actual, frozen)

    async def test_deck_and_workspace_access_fail_closed_without_existence_leak(self) -> None:
        with self.assertRaises(BindingAccessError) as missing:
            self.fixture.binding.resolve_workspace_access(
                deck_id="missing-deck", actor_id="1"
            )
        with self.assertRaises(BindingAccessError) as unauthorized:
            self.fixture.binding.resolve_workspace_access(
                deck_id=DECK_ID, actor_id="2"
            )
        self.assertEqual(str(missing.exception), str(unauthorized.exception))

    async def test_concurrent_compare_and_swap_allows_only_one_revision(self) -> None:
        await self.fixture.binding.save(
            deck_id=DECK_ID,
            actor_id="1",
            request=BindingFixture.request(0),
        )

        async def resolver(*_args) -> RuntimeContext:
            return await self.fixture.runtime_context(PLUGIN_ID, VERSION, WORKSPACE_ID, "1")

        def worker():
            db = self.fixture.connect()
            try:
                validator = SelectionValidationService(
                    db,
                    runtime_context_resolver=resolver,
                )
                service = BindingService(db, selection_validator=validator)
                return asyncio.run(
                    service.save(
                        deck_id=DECK_ID,
                        actor_id="1",
                        request=BindingFixture.request(1),
                    )
                )
            finally:
                db.close()

        results = await asyncio.gather(
            asyncio.to_thread(worker),
            asyncio.to_thread(worker),
            return_exceptions=True,
        )
        self.assertEqual(
            sum(
                not isinstance(item, Exception)
                and getattr(item, "binding_revision", None) == 2
                for item in results
            ),
            1,
        )
        self.assertEqual(
            sum(isinstance(item, BindingRevisionConflict) for item in results),
            1,
        )
        rows = self.fixture.db.execute(
            "SELECT binding_revision, status FROM deck_plugin_bindings "
            "ORDER BY binding_revision"
        ).fetchall()
        self.assertEqual(
            [(row["binding_revision"], row["status"]) for row in rows],
            [(1, "stale"), (2, "active")],
        )


class BindingRouterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = BindingFixture()
        app = FastAPI()
        app.dependency_overrides[binding_router.get_current_user] = lambda: {
            "user_id": 1,
            "email": "owner@example.com",
            "workspace_id": WORKSPACE_ID,
        }
        app.dependency_overrides[binding_router._binding_db] = lambda: self.fixture.db
        app.dependency_overrides[
            binding_router._selection_service
        ] = lambda: self.fixture.validator
        app.include_router(binding_router.router)
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()
        self.fixture.close()

    def test_four_authenticated_endpoints_and_frozen_success_shapes(self) -> None:
        methods: dict[str, set[str]] = {}
        for route in binding_router.router.routes:
            methods.setdefault(route.path, set()).update(route.methods)
        self.assertEqual(
            methods,
            {
                "/api/voice-decks/{deck_id}/plugin-options": {"GET"},
                "/api/voice-decks/{deck_id}/plugin-binding": {"GET", "PUT"},
                "/api/voice-decks/{deck_id}/plugin-binding/validate": {"POST"},
            },
        )

        current = self.client.get(f"/api/voice-decks/{DECK_ID}/plugin-binding")
        self.assertEqual(current.status_code, 200, current.text)
        self.assertEqual(
            current.json(),
            {
                "deck_id": DECK_ID,
                "binding_revision": 0,
                "applied_to": "next_run",
                "binding": None,
            },
        )
        options = self.client.get(f"/api/voice-decks/{DECK_ID}/plugin-options")
        self.assertEqual(options.status_code, 200, options.text)
        option = options.json()["options"][0]
        self.assertEqual(
            set(option),
            {
                "display_name", "deck_plugin_id", "deck_plugin_version",
                "release_status", "installation_status", "compatibility",
                "runtime_readiness", "selectable", "reason_code", "recovery",
                "capability_summary",
            },
        )
        self.assertTrue(option["selectable"])

        validated = self.client.post(
            f"/api/voice-decks/{DECK_ID}/plugin-binding/validate",
            json={
                "deck_plugin_id": PLUGIN_ID,
                "deck_plugin_version": VERSION,
                "apply_to": "next_run",
            },
        )
        self.assertEqual(validated.status_code, 200, validated.text)
        self.assertTrue(validated.json()["validation"]["selectable"])
        self.assertEqual(
            self.fixture.db.execute(
                "SELECT COUNT(*) FROM deck_plugin_bindings"
            ).fetchone()[0],
            0,
        )

        saved = self.client.put(
            f"/api/voice-decks/{DECK_ID}/plugin-binding",
            json={
                "deck_plugin_id": PLUGIN_ID,
                "deck_plugin_version": VERSION,
                "expected_binding_revision": 0,
                "apply_to": "next_run",
            },
        )
        self.assertEqual(saved.status_code, 200, saved.text)
        payload = saved.json()
        self.assertEqual(
            set(payload),
            {
                "deck_plugin_binding_id", "deck_id", "deck_plugin_id",
                "deck_plugin_version", "binding_revision", "status", "applied_to",
                "selection_validation_summary",
            },
        )
        self.assertEqual(payload["binding_revision"], 1)
        self.assertNotIn("workspace_id", payload)
        self.assertNotIn("creator_id", payload)

    def test_conflict_unselectable_auth_and_sanitized_error_shapes(self) -> None:
        request = {
            "deck_plugin_id": PLUGIN_ID,
            "deck_plugin_version": VERSION,
            "expected_binding_revision": 0,
            "apply_to": "next_run",
        }
        first = self.client.put(
            f"/api/voice-decks/{DECK_ID}/plugin-binding", json=request
        )
        self.assertEqual(first.status_code, 200, first.text)
        conflict = self.client.put(
            f"/api/voice-decks/{DECK_ID}/plugin-binding", json=request
        )
        self.assertEqual(conflict.status_code, 409, conflict.text)
        self.assertEqual(
            conflict.json(),
            {
                "error_code": "BINDING_REVISION_CONFLICT",
                "current_revision": 1,
                "message": (
                    "Binding was modified concurrently. Please refresh and "
                    "confirm your selection."
                ),
            },
        )
        self.fixture.db.execute(
            "UPDATE deck_plugin_installations SET status = 'disabled'"
        )
        self.fixture.db.commit()
        request["expected_binding_revision"] = 1
        rejected = self.client.put(
            f"/api/voice-decks/{DECK_ID}/plugin-binding", json=request
        )
        self.assertEqual(rejected.status_code, 422, rejected.text)
        self.assertEqual(
            set(rejected.json()),
            {"error_code", "message", "validation"},
        )
        self.assertEqual(rejected.json()["error_code"], "DECK_PLUGIN_DISABLED")
        self.assertEqual(
            self.fixture.db.execute(
                "SELECT COUNT(*) FROM deck_plugin_bindings"
            ).fetchone()[0],
            1,
        )

        serialized = json.dumps(rejected.json()).lower()
        for forbidden in ("secret", "prompt", "traceback", "/users/", "command"):
            self.assertNotIn(forbidden, serialized)

        unauthorized_app = FastAPI()
        unauthorized_app.dependency_overrides[
            binding_router.get_current_user
        ] = lambda: {"user_id": 2, "workspace_id": "other-workspace"}
        unauthorized_app.dependency_overrides[
            binding_router._binding_db
        ] = lambda: self.fixture.db
        unauthorized_app.dependency_overrides[
            binding_router._selection_service
        ] = lambda: self.fixture.validator
        unauthorized_app.include_router(binding_router.router)
        with TestClient(unauthorized_app) as client:
            denied = client.get(f"/api/voice-decks/{DECK_ID}/plugin-binding")
        self.assertEqual(denied.status_code, 404)
        self.assertEqual(
            denied.json(),
            {
                "error_code": "DECK_ACCESS_DENIED",
                "message": "Deck not found or permission denied.",
            },
        )

    def test_router_uses_existing_auth_dependency(self) -> None:
        app = FastAPI()
        app.dependency_overrides[binding_router._binding_db] = lambda: self.fixture.db
        app.dependency_overrides[
            binding_router._selection_service
        ] = lambda: self.fixture.validator
        app.include_router(binding_router.router)
        with TestClient(app) as anonymous:
            response = anonymous.get(
                f"/api/voice-decks/{DECK_ID}/plugin-binding"
            )
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
