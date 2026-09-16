"""Contract tests for DECK-014 logical routes and client-safe errors.

[Input] Logical routers plus the canonical client-safe error registry.
[Output] Route contracts and recovery metadata for every registered error code.
[Pos] Backend API surface regression tests.
[Sync] 2026-08-19: include four fail-closed Remote Marketplace error codes.
[Sync] 2026-09-16: retire the pre-Admin Story gateway fixture; focused DTO suites own those routes.
[Sync] 2026-09-16: update Deck Plugin route fakes for current OAuth actor and Registry170-174 scope.
[Sync] 2026-09-16: include the registered unknown-result Claude Plugin error contract.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from routers import deck_plugins, voice_decks
from services.admin_data.request_auth import AdminRequestActor
from services.errors.error_registry import (
    ERROR_REGISTRY,
    ApiRouteError,
    build_error_payload,
)

PLUGIN_ID = "voice-decks.story-dramatize"
VERSION = "3.1.0"
DECK_ID = "deck-api-routes"


class _DeckGateway:
    async def list_installations(self, *, scope_type, scope_id, actor):
        return {"installations": [{"scope_id": scope_id, "status": "ready"}]}

    async def install(self, request, *, actor):
        return {
            "operation_id": "op_" + "3" * 32,
            "deck_plugin_installation_id": "dpi_" + "4" * 32,
            "deck_plugin_id": request.deck_plugin_id,
            "target_version": request.version,
            "status": "installing",
            "capability_diff": {"added": [], "removed": []},
            "runtime_readiness": "materializing",
            "actor_id": actor.canonical_user_id,
        }

    async def get_version(self, deck_plugin_id, version, **_kwargs):
        return {
            "deck_plugin_id": deck_plugin_id,
            "deck_plugin_version": version,
            "manifest": {"schema_version": "deck-plugin/v1"},
            "capabilities": [],
            "compatibility": "passed",
            "release_hash": "sha256:" + "a" * 64,
        }

    async def enable(self, deck_plugin_id, request, *, actor):
        return {"deck_plugin_id": deck_plugin_id, "status": "ready", "actor_id": actor.canonical_user_id}

    async def disable(self, deck_plugin_id, request, *, actor):
        return {
            "deck_plugin_id": deck_plugin_id,
            "status": "disabled",
            "reason": request.reason,
            "revocation_level": request.revocation_level,
            "actor_id": actor.canonical_user_id,
        }

    async def upgrade(self, deck_plugin_id, request, *, actor):
        return {
            "deck_plugin_id": deck_plugin_id,
            "target_version": request.target_version,
            "status": "upgrade_pending",
            "actor_id": actor.canonical_user_id,
        }

    async def rollback(self, deck_plugin_id, request, *, actor):
        return {
            "deck_plugin_id": deck_plugin_id,
            "target_version": request.target_version,
            "status": "ready",
            "actor_id": actor.canonical_user_id,
        }

    async def runtime_readiness(self, deck_plugin_id, *, environment, **_kwargs):
        return {
            "deck_plugin_id": deck_plugin_id,
            "environment": environment,
            "declared": True,
            "materialized": True,
            "loadable": True,
        }

    async def reconcile(self, deck_plugin_id, request, *, actor):
        return {
            "operation_id": "op_" + "5" * 32,
            "deck_plugin_id": deck_plugin_id,
            "environment": request.environment,
            "status": "accepted",
            "actor_id": actor.canonical_user_id,
        }


class _VoiceDeckGateway:
    async def list_options(self, deck_id, *, actor):
        return {
            "deck_id": deck_id,
            "applied_to": "next_run",
            "options": [{
                "deck_plugin_id": PLUGIN_ID,
                "deck_plugin_version": VERSION,
                "selectable": True,
                "reason_code": None,
            }],
        }

    async def get_binding(self, deck_id, *, actor):
        return {"deck_id": deck_id, "binding_revision": 7, "applied_to": "next_run"}

    async def save_binding(self, deck_id, request, *, actor):
        return {
            "deck_id": deck_id,
            "deck_plugin_id": request.deck_plugin_id,
            "deck_plugin_version": request.deck_plugin_version,
            "binding_revision": request.expected_binding_revision + 1,
            "applied_to": request.apply_to,
        }

    async def validate_binding(self, deck_id, request, *, actor):
        return {
            "deck_id": deck_id,
            "deck_plugin_id": request.deck_plugin_id,
            "deck_plugin_version": request.deck_plugin_version,
            "selectable": True,
            "workflow_run_created": False,
        }


def _authenticated_user():
    actor = AdminRequestActor(
        subject="subject-api-routes",
        canonical_user_id="7",
        client_id="dream-browser",
        scopes=frozenset({"dream:read", "dream:write"}),
        issued_at=1,
        expires_at=4_000_000_000,
        access_token="oauth-access",
    )
    return {
        "user_id": 7,
        "workspace_id": "workspace-api-routes",
        "role": "admin",
        "permissions": ["plugin:read", "plugin:admin"],
        "_admin_actor": actor,
    }


class ApiRouteContractTests(unittest.TestCase):
    def setUp(self):
        deck_app = FastAPI()
        deck_app.dependency_overrides[deck_plugins._deck_plugin_current_user] = _authenticated_user
        deck_app.dependency_overrides[deck_plugins.get_deck_plugin_gateway] = _DeckGateway
        deck_app.include_router(deck_plugins.router)
        self.deck_client = TestClient(deck_app)

        voice_app = FastAPI()
        voice_app.dependency_overrides[voice_decks.get_current_user] = _authenticated_user
        voice_app.dependency_overrides[voice_decks.get_voice_deck_gateway] = _VoiceDeckGateway
        voice_app.include_router(voice_decks.router)
        self.voice_client = TestClient(voice_app)

    def tearDown(self):
        self.deck_client.close()
        self.voice_client.close()

    def test_all_nine_admin_routes_and_install_contract(self):
        common = {"scope_type": "workspace", "scope_id": "workspace-api-routes"}
        calls = [
            self.deck_client.get("/api/deck-plugins/installations?scope_id=workspace-api-routes"),
            self.deck_client.post("/api/deck-plugins/install", json={
                **common,
                "deck_plugin_id": PLUGIN_ID,
                "version": VERSION,
                "source": "trusted-marketplace",
                "idempotency_key": "install-1",
            }),
            self.deck_client.get(f"/api/deck-plugins/{PLUGIN_ID}/versions/{VERSION}"),
            self.deck_client.post(f"/api/deck-plugins/{PLUGIN_ID}/enable", json=common),
            self.deck_client.post(f"/api/deck-plugins/{PLUGIN_ID}/disable", json={
                **common, "reason": "maintenance", "revocation_level": "normal"
            }),
            self.deck_client.post(f"/api/deck-plugins/{PLUGIN_ID}/upgrade", json={
                **common, "target_version": "3.2.0"
            }),
            self.deck_client.post(f"/api/deck-plugins/{PLUGIN_ID}/rollback", json={
                **common, "target_version": "3.0.0"
            }),
            self.deck_client.get(
                f"/api/deck-plugins/{PLUGIN_ID}/runtime-readiness?environment=test"
            ),
            self.deck_client.post(f"/api/deck-plugins/{PLUGIN_ID}/reconcile", json={
                **common, "environment": "test"
            }),
        ]
        self.assertEqual([response.status_code for response in calls], [200, 202, 200, 200, 200, 200, 200, 200, 202])
        install = calls[1].json()
        self.assertEqual(
            {"operation_id", "capability_diff", "runtime_readiness"} - set(install),
            set(),
        )

    def test_four_voice_deck_routes_preserve_next_run_and_revision(self):
        selection = {
            "deck_plugin_id": PLUGIN_ID,
            "deck_plugin_version": VERSION,
            "apply_to": "next_run",
        }
        options = self.voice_client.get(f"/api/voice-decks/{DECK_ID}/plugin-options")
        binding = self.voice_client.get(f"/api/voice-decks/{DECK_ID}/plugin-binding")
        saved = self.voice_client.put(f"/api/voice-decks/{DECK_ID}/plugin-binding", json={
            **selection, "expected_binding_revision": 7
        })
        validated = self.voice_client.post(
            f"/api/voice-decks/{DECK_ID}/plugin-binding/validate", json=selection
        )
        self.assertEqual([item.status_code for item in (options, binding, saved, validated)], [200] * 4)
        self.assertEqual(saved.json()["binding_revision"], 8)
        self.assertEqual(saved.json()["applied_to"], "next_run")
        self.assertFalse(validated.json()["workflow_run_created"])

class ErrorRegistryTests(unittest.TestCase):
    def test_registry_has_all_56_canonical_codes_with_recovery(self):
        # 27 legacy codes + 16 Claude Code plugin pipeline codes
        # (deck-integration-delta, 2026-08-02) + 1 guidance code
        # (WORKFLOW_RUN_NOT_GUIDABLE, dream-surface Task 3, 2026-08-04)
        # + 4 Remote Marketplace fail-closed codes (2026-08-19).
        self.assertGreaterEqual(len(ERROR_REGISTRY), 25)
        self.assertEqual(len(ERROR_REGISTRY), 57)
        story_index_codes = {
            "story_index_row_missing",
            "story_index_schema_unavailable",
            "story_index_database_unavailable",
            "story_index_write_failed",
            "story_index_conflict",
            "story_index_invalid_artifact",
            "story_index_revision_conflict",
            "artifact_missing",
        }
        for code, metadata in ERROR_REGISTRY.items():
            if code not in story_index_codes:
                self.assertRegex(code, r"^[A-Z][A-Z0-9_]+$")
            self.assertTrue(metadata["phase"])
            self.assertTrue(metadata["meaning"])
            self.assertTrue(metadata["recovery"])
            response_error = build_error_payload(code)["error"]
            self.assertEqual(response_error["code"], code)
            self.assertEqual(response_error["phase"], metadata["phase"])
            self.assertEqual(response_error["recovery_action"], metadata["recovery"])

    def test_safe_payload_never_echoes_internal_details(self):
        payload = build_error_payload(
            "RUNTIME_PLUGIN_NOT_READY",
            operation_id="op_safe",
            failed_check="runtime_plugin_ready",
        )
        serialized = str(payload).lower()
        for forbidden in ("traceback", "/users/", "prompt", "secret", "api-key"):
            self.assertNotIn(forbidden, serialized)
        self.assertEqual(payload["error"]["operation_id"], "op_safe")

    def test_unknown_errors_collapse_to_safe_public_code(self):
        payload = build_error_payload("INTERNAL_/Users/name_SECRET")
        self.assertEqual(payload["error"]["code"], "AGENT_EXECUTION_FAILED")
        self.assertNotIn("Users", str(payload))

    def test_router_known_error_uses_nested_safe_envelope(self):
        class DeniedGateway(_DeckGateway):
            async def get_version(self, deck_plugin_id, version, **_kwargs):
                raise ApiRouteError(
                    "WORKFLOW_PERMISSION_DENIED",
                    status_code=403,
                    operation_id="op_public",
                )

        app = FastAPI()
        app.dependency_overrides[deck_plugins._deck_plugin_current_user] = _authenticated_user
        app.dependency_overrides[deck_plugins.get_deck_plugin_gateway] = DeniedGateway
        app.include_router(deck_plugins.router)
        with TestClient(app) as client:
            response = client.get(f"/api/deck-plugins/{PLUGIN_ID}/versions/{VERSION}")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "WORKFLOW_PERMISSION_DENIED")
        self.assertEqual(response.json()["error"]["operation_id"], "op_public")

    def test_router_hides_unexpected_exception_and_enforces_admin_permission(self):
        class ExplodingGateway(_DeckGateway):
            async def get_version(self, deck_plugin_id, version, **_kwargs):
                raise RuntimeError("/Users/private prompt secret api-key")

        app = FastAPI()
        app.dependency_overrides[deck_plugins._deck_plugin_current_user] = lambda: {
            "user_id": 8,
            "role": "user",
            "permissions": [],
            "workspace_id": "workspace-api-routes",
            "_admin_actor": AdminRequestActor(
                subject="subject-api-routes-user",
                canonical_user_id="8",
                client_id="dream-browser",
                scopes=frozenset({"dream:read"}),
                issued_at=1,
                expires_at=4_000_000_000,
                access_token="oauth-access",
            ),
        }
        app.dependency_overrides[deck_plugins.get_deck_plugin_gateway] = ExplodingGateway
        app.include_router(deck_plugins.router)
        with TestClient(app) as client:
            denied = client.get("/api/deck-plugins/installations")
            hidden = client.get(f"/api/deck-plugins/{PLUGIN_ID}/versions/{VERSION}")
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(denied.json()["error"]["code"], "WORKFLOW_PERMISSION_DENIED")
        self.assertEqual(hidden.status_code, 503)
        self.assertEqual(hidden.json()["error"]["code"], "DECK_RUNTIME_CONFIG_UNAVAILABLE")
        self.assertNotIn("private", hidden.text.lower())
        self.assertNotIn("secret", hidden.text.lower())


if __name__ == "__main__":
    unittest.main()
