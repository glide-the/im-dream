# [Input] Public Deck Plugin routes, current OAuth actor and fake Registry170-174 provider.
# [Output] Scope/actor propagation, local artifact evidence and public failure-shape coverage.
# [Pos] Provider-free cross-project integration test; no Dream database or alternate business path.
# [Sync] 2026-09-16: replace the legacy SQLite lifecycle fixture with the Admin DTO flow.
from __future__ import annotations

import asyncio
import hashlib
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from routers import deck_plugins
from services.admin_data.deck_plugin_control_data import (
    DeckPluginControlOperationDTO,
    DeckPluginControlPlanDTO,
)
from services.admin_data.request_auth import AdminRequestActor
from services.deck.admin_gateway import DeckPluginAdminService
from services.deck import builtin_plugin as builtin_plugin_module
from services.deck.builtin_plugin import (
    BUILTIN_CLAUDE_PLUGIN_ID,
    BUILTIN_DECK_PLUGIN_ID,
    BUILTIN_DECK_PLUGIN_VERSION,
    BUILTIN_SOURCE_REF,
    builtin_plugin_path,
    plugin_artifact_digest,
)
from services.errors.error_registry import ApiRouteError


def actor() -> AdminRequestActor:
    return AdminRequestActor(
        subject="subject-1",
        canonical_user_id="101",
        client_id="dream-browser",
        scopes=frozenset({"dream:read", "dream:write"}),
        issued_at=1,
        expires_at=4_000_000_000,
        access_token="oauth-access",
    )


def operation(plugin_id: str, version: str | None) -> dict:
    return {
        "operation_id": "op_" + "b" * 32,
        "deck_plugin_id": plugin_id,
        "target_version": version,
        "status": "completed",
        "phase": "ready",
        "progress": 100,
        "message": "Deck Plugin operation completed.",
        "updated_at": datetime.now(UTC),
    }


class FakeControlData:
    def __init__(self) -> None:
        self.calls = []

    def plan(self, command, request_id, *, access_token):
        self.calls.append(("plan", command, request_id, access_token))
        digest = plugin_artifact_digest()
        return DeckPluginControlPlanDTO(
            command=command,
            expected_revision=None,
            deck_plugin_installation_id=None,
            target_version=command.deck_plugin_version,
            source_policy_id=f"{command.source_type}:{command.source}",
            capability_diff={"added": ["story.workspace.propose"], "removed": []},
            requires_runtime_evidence=True,
            runtime_target={
                "runtime_plugin_lock_id": "rpl_" + "a" * 32,
                "deck_plugin_manifest_hash": "sha256:" + "c" * 64,
                "artifact_set_hash": "sha256:" + "d" * 64,
                "entries": [
                    {
                        "claude_code_plugin_id": BUILTIN_CLAUDE_PLUGIN_ID,
                        "resolved_version": BUILTIN_DECK_PLUGIN_VERSION,
                        "source_ref": BUILTIN_SOURCE_REF,
                        "artifact_digest": digest,
                        "required": True,
                    }
                ],
            },
        )

    def apply(self, request, request_id, *, access_token):
        self.calls.append(("apply", request, request_id, access_token))
        return DeckPluginControlOperationDTO.model_validate(
            operation(request.plan.command.deck_plugin_id, request.plan.target_version)
        )


def test_gateway_verifies_server_published_bytes_before_admin_apply():
    data = FakeControlData()
    request_ids = iter(["plan-request", "unused-request"])
    service = DeckPluginAdminService(
        data,
        request_id_factory=lambda: next(request_ids),
    )
    request = deck_plugins.InstallRequest(
        deck_plugin_id=BUILTIN_DECK_PLUGIN_ID,
        deck_plugin_version=BUILTIN_DECK_PLUGIN_VERSION,
        source_type="controlled",
        source=BUILTIN_SOURCE_REF,
        idempotency_key="stable-install-key",
        scope_type="workspace",
        scope_id="workspace-deck-admin",
    )

    result = asyncio.run(service.install(request, actor=actor()))

    assert result.status == "completed"
    assert [call[0] for call in data.calls] == ["plan", "apply"]
    _, apply_input, apply_request_id, access_token = data.calls[1]
    assert apply_request_id == (
        "deck-plugin-install:"
        + hashlib.sha256(b"stable-install-key").hexdigest()
    )
    assert access_token == "oauth-access"
    assert len(apply_input.evidence) == 1
    evidence = apply_input.evidence[0]
    assert evidence.cache_ref == str(builtin_plugin_path().resolve())
    assert evidence.artifact_digest == plugin_artifact_digest()
    assert evidence.materialized_digest == evidence.artifact_digest
    assert evidence.has_manifest is True


def test_builtin_plugin_source_has_no_release_persistence_path():
    source = Path(builtin_plugin_module.__file__).read_text(encoding="utf-8")
    assert "db.execute" not in source
    assert "deck_plugin_releases" not in source
    assert "deck_runtime_plugin_locks" not in source
    assert "seed_builtin_deck_plugin" not in source


class FakeGateway:
    def __init__(self) -> None:
        self.calls = []

    async def list_installations(self, **kwargs):
        self.calls.append(("list", kwargs))
        return {"installations": [], "runtime_plugins": []}

    async def install(self, request, *, actor):
        self.calls.append(("install", request, actor))
        if request.source_type == "local":
            raise ApiRouteError("DECK_PLUGIN_SOURCE_DENIED", status_code=403)
        return operation(request.deck_plugin_id, request.version)

    async def get_version(self, deck_plugin_id, version, **kwargs):
        self.calls.append(("version", deck_plugin_id, version, kwargs))
        return {"deck_plugin_id": deck_plugin_id, "deck_plugin_version": version}

    async def runtime_readiness(self, deck_plugin_id, **kwargs):
        self.calls.append(("readiness", deck_plugin_id, kwargs))
        return {
            "declaration_status": "declared",
            "materialization_status": "materialized",
            "activation_status": "loadable",
        }


def test_public_routes_keep_product_shape_and_pass_oauth_actor_scope():
    gateway = FakeGateway()
    current_actor = actor()
    current_user = {
        "user_id": 101,
        "role": "admin",
        "workspace_id": "workspace-deck-admin",
        "_admin_actor": current_actor,
    }
    app = FastAPI()
    app.dependency_overrides[deck_plugins._deck_plugin_current_user] = (
        lambda: current_user
    )
    app.dependency_overrides[deck_plugins.get_deck_plugin_gateway] = lambda: gateway
    app.include_router(deck_plugins.router)

    with TestClient(app) as client:
        preview = client.get(
            f"/api/deck-plugins/{BUILTIN_DECK_PLUGIN_ID}/versions/"
            f"{BUILTIN_DECK_PLUGIN_VERSION}"
        )
        assert preview.status_code == 200, preview.text

        installed = client.post(
            "/api/deck-plugins/install",
            json={
                "deck_plugin_id": BUILTIN_DECK_PLUGIN_ID,
                "deck_plugin_version": BUILTIN_DECK_PLUGIN_VERSION,
                "source_type": "controlled",
                "source": BUILTIN_SOURCE_REF,
                "idempotency_key": "public-install",
            },
            headers={"Idempotency-Key": "public-install"},
        )
        assert installed.status_code == 202, installed.text
        assert installed.json()["status"] == "completed"

        catalog = client.get("/api/deck-plugins/installations")
        assert catalog.status_code == 200, catalog.text
        assert catalog.json()["permissions"] == {
            "can_manage": True,
            "can_install_local": True,
            "can_force_purge": True,
        }

        readiness = client.get(
            f"/api/deck-plugins/{BUILTIN_DECK_PLUGIN_ID}/runtime-readiness"
        )
        assert readiness.status_code == 200, readiness.text
        assert readiness.json()["activation_status"] == "loadable"

        denied = client.post(
            "/api/deck-plugins/install",
            json={
                "deck_plugin_id": BUILTIN_DECK_PLUGIN_ID,
                "deck_plugin_version": BUILTIN_DECK_PLUGIN_VERSION,
                "source_type": "local",
                "source": "/tmp/untrusted-plugin",
            },
        )
        assert denied.status_code == 403, denied.text
        assert denied.json()["error"]["code"] == "DECK_PLUGIN_SOURCE_DENIED"

    list_call = next(call for call in gateway.calls if call[0] == "list")
    assert list_call[1] == {
        "scope_type": "workspace",
        "scope_id": "workspace-deck-admin",
        "actor": current_actor,
    }
    install_call = next(call for call in gateway.calls if call[0] == "install")
    assert install_call[1].scope_id == "workspace-deck-admin"
    assert install_call[2] is current_actor
