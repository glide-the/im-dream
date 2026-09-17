# [Input] Strict Admin Registry122-129 DTO operations and mocked shared-artifact verification.
# [Output] Frozen binding/Agent-type public route projections and provider-free failure behavior.
# [Pos] Dream public ingress contract tests; Admin owns ORM, CAS, UOW and database persistence.
# [Sync] 2026-09-16: remove the retired SQLite binding/selection authority and test DTO-only routes.
"""Provider-free Deck Plugin binding and Agent-type route contracts."""

from __future__ import annotations

from datetime import UTC, datetime
import json
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from models.deck_plugin import DeckPluginSelectionRequest
from routers import deck_plugin_binding as binding_router
from services.admin_data.deck_plugin_binding_data import (
    AgentTypeChatDTO,
    AgentTypeRuntimeCandidateDTO,
    AgentTypeRuntimePlanDTO,
    AgentTypeRuntimePreparedDTO,
    AgentTypeVerifiedPluginDTO,
    BindingClearInputDTO,
    BindingHistoryDTO,
    BindingHistoryEntryDTO,
    BindingHistoryInputDTO,
    BindingOptionDTO,
    BindingOptionsDTO,
    BindingResponseDTO,
    BindingSaveInputDTO,
    BindingScopeInputDTO,
    BindingSelectionInputDTO,
    BindingValidationDTO,
)
from services.admin_data.errors import AdminDataError
from services.admin_data.models import (
    BindingRevisionConflictDetailsDTO,
    BindingSelectionRecoveryDTO,
    BindingSelectionRejectedDetailsDTO,
    BindingSelectionSummaryDTO,
)
from services.admin_data.request_auth import AdminRequestActor


PLUGIN_ID = "voice-decks.story-dramatize"
VERSION = "3.1.0"
DECK_ID = "deck-binding-test"
WORKSPACE_ID = "workspace-binding-test"
BINDING_ID = "dpb_" + "1" * 32
RUNTIME_LOCK_ID = "rpl_" + "2" * 32
INSTALLATION_ID = "cpi_test_ready"
DIGEST = "sha256:" + "d" * 64
NOW = datetime(2026, 9, 16, tzinfo=UTC)


def actor_projection(user_id: int, workspace_id: str) -> dict:
    actor = AdminRequestActor(
        subject=f"subject-{user_id}",
        canonical_user_id=str(user_id),
        client_id="dream-browser",
        scopes=frozenset({"dream:read", "dream:write"}),
        issued_at=1,
        expires_at=4_102_444_800,
        access_token=f"fixture-access-{user_id}",
    )
    return {**actor.current_user_projection(), "workspace_id": workspace_id}


def selection_summary(*, selectable: bool = True) -> BindingSelectionSummaryDTO:
    if selectable:
        return BindingSelectionSummaryDTO(
            selectable=True,
            release_status="published",
            installation_status="ready",
            compatibility="passed",
            runtime_readiness="materialized",
            reason_code=None,
            recovery=None,
            capability_summary=["story.result.produce", "workspace.files.read"],
        )
    return BindingSelectionSummaryDTO(
        selectable=False,
        release_status="published",
        installation_status="disabled",
        compatibility="failed",
        runtime_readiness="unknown",
        reason_code="DECK_PLUGIN_DISABLED",
        recovery=BindingSelectionRecoveryDTO(
            owner="deck_plugin_admin",
            action="enable_the_installation_or_select_another_release",
        ),
        capability_summary=[],
    )


def runtime_candidate() -> AgentTypeRuntimeCandidateDTO:
    return AgentTypeRuntimeCandidateDTO(
        deck_plugin_id=PLUGIN_ID,
        deck_plugin_version=VERSION,
        runtime_plugin_lock_id=RUNTIME_LOCK_ID,
        plugin_installation_id=INSTALLATION_ID,
        package_spec="story-runtime@platform-builtin",
        package_name="story-runtime",
        marketplace="platform-builtin",
        resolved_version=VERSION,
        artifact_digest=DIGEST,
        compatibility_json="{}",
    )


class FakeBindingData:
    """Stateful Admin-boundary fake; it contains no database or ORM behavior."""

    def __init__(self, *, denied: bool = False) -> None:
        self.denied = denied
        self.selectable = True
        self.revision = 0
        self.binding: BindingResponseDTO | None = None
        self.entries: list[BindingHistoryEntryDTO] = []
        self.calls: list[str] = []

    def _before(self, name: str, request, access_token: str) -> None:
        self.calls.append(name)
        assert request.deck_id == DECK_ID
        assert request.workspace_id in {WORKSPACE_ID, "other-workspace"}
        assert access_token.startswith("fixture-access-")
        if self.denied:
            raise AdminDataError("DECK_ACCESS_DENIED", 404)

    def _conflict(self, expected: int) -> None:
        if expected != self.revision:
            raise AdminDataError(
                "BINDING_REVISION_CONFLICT",
                409,
                details=BindingRevisionConflictDetailsDTO(
                    current_revision=self.revision
                ),
            )

    def _rejected(self) -> None:
        if not self.selectable:
            raise AdminDataError(
                "SELECTION_NOT_ALLOWED",
                422,
                details=BindingSelectionRejectedDetailsDTO(
                    validation=selection_summary(selectable=False)
                ),
            )

    def current(self, request: BindingScopeInputDTO, _request_id: str, *, access_token: str):
        self._before("current", request, access_token)
        return {
            "deck_id": DECK_ID,
            "binding_revision": self.revision,
            "applied_to": "next_run",
            "binding": self.binding,
        }

    def history(self, request: BindingHistoryInputDTO, _request_id: str, *, access_token: str):
        self._before("history", request, access_token)
        return BindingHistoryDTO(
            deck_id=DECK_ID,
            current_binding_revision=self.revision,
            entries=self.entries[: request.limit],
        )

    def options(self, request: BindingScopeInputDTO, _request_id: str, *, access_token: str):
        self._before("options", request, access_token)
        summary = selection_summary(selectable=self.selectable)
        return BindingOptionsDTO(
            deck_id=DECK_ID,
            applied_to="next_run",
            options=[
                BindingOptionDTO(
                    display_name="Story Dramatize",
                    deck_plugin_id=PLUGIN_ID,
                    deck_plugin_version=VERSION,
                    release_status=summary.release_status,
                    installation_status=summary.installation_status,
                    compatibility=summary.compatibility,
                    runtime_readiness=summary.runtime_readiness,
                    selectable=summary.selectable,
                    reason_code=summary.reason_code,
                    recovery=summary.recovery,
                    capability_summary=summary.capability_summary,
                )
            ],
        )

    def validate(self, request: BindingSelectionInputDTO, _request_id: str, *, access_token: str):
        self._before("validate", request, access_token)
        return BindingValidationDTO(
            deck_id=request.deck_id,
            deck_plugin_id=request.deck_plugin_id,
            deck_plugin_version=request.deck_plugin_version,
            applied_to=request.apply_to,
            validation=selection_summary(selectable=self.selectable),
        )

    def save(self, request: BindingSaveInputDTO, _request_id: str, *, access_token: str):
        self._before("save", request, access_token)
        self._conflict(request.expected_binding_revision)
        self._rejected()
        if (
            self.binding is not None
            and self.binding.deck_plugin_id == request.deck_plugin_id
            and self.binding.deck_plugin_version == request.deck_plugin_version
        ):
            return self.binding
        self.revision += 1
        self.binding = BindingResponseDTO(
            deck_plugin_binding_id=BINDING_ID,
            deck_id=DECK_ID,
            deck_plugin_id=request.deck_plugin_id,
            deck_plugin_version=request.deck_plugin_version,
            binding_revision=self.revision,
            status="active",
            applied_to="next_run",
            selection_validation_summary=selection_summary(),
        )
        self.entries.insert(
            0,
            BindingHistoryEntryDTO(
                deck_plugin_binding_id=BINDING_ID,
                deck_plugin_id=request.deck_plugin_id,
                deck_plugin_version=request.deck_plugin_version,
                binding_revision=self.revision,
                status="active",
                applied_to="next_run",
                created_at=NOW,
                updated_at=NOW,
            ),
        )
        return self.binding

    def clear(self, request: BindingClearInputDTO, _request_id: str, *, access_token: str):
        self._before("clear", request, access_token)
        self._conflict(request.expected_binding_revision)
        self.binding = None
        return AgentTypeChatDTO(
            deck_id=DECK_ID,
            agent_type="chat",
            binding_revision=self.revision,
        )

    def runtime_plan(self, request: BindingScopeInputDTO, _request_id: str, *, access_token: str):
        self._before("runtime_plan", request, access_token)
        return AgentTypeRuntimePlanDTO(
            deck_id=DECK_ID,
            current_binding_revision=self.revision,
            target=runtime_candidate(),
        )

    def runtime_prepare(self, request, _request_id: str, *, access_token: str):
        self._before("runtime_prepare", request, access_token)
        self._conflict(request.expected_binding_revision)
        return AgentTypeRuntimePreparedDTO(
            deck_id=DECK_ID,
            deck_plugin_id=PLUGIN_ID,
            deck_plugin_version=VERSION,
            current_binding_revision=self.revision,
            runtime_ready=True,
        )


class BindingModelSchemaTests(unittest.TestCase):
    def test_requests_require_exact_semver_and_next_run(self) -> None:
        valid = DeckPluginSelectionRequest(
            deck_plugin_id=PLUGIN_ID,
            deck_plugin_version=VERSION,
            apply_to="next_run",
        )
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


class BindingRouterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = FakeBindingData()
        app = FastAPI()
        current_user = actor_projection(1, WORKSPACE_ID)
        app.dependency_overrides[binding_router._deck_current_user] = lambda: current_user
        app.dependency_overrides[binding_router._binding_data] = lambda: self.data
        self.runtime_verify_patcher = patch.object(
            binding_router,
            "verify_agent_type_runtime",
            side_effect=lambda candidate: AgentTypeVerifiedPluginDTO(
                plugin_installation_id=candidate.plugin_installation_id,
                package_spec=candidate.package_spec,
                resolved_version=candidate.resolved_version,
                artifact_digest=candidate.artifact_digest,
                has_manifest=True,
            ),
        )
        self.runtime_verify = self.runtime_verify_patcher.start()
        app.include_router(binding_router.router)
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()
        self.runtime_verify_patcher.stop()

    def test_dream_agent_type_uses_plan_local_evidence_prepare_and_binding_save(self) -> None:
        response = self.client.put(
            f"/api/voice-decks/{DECK_ID}/agent-type",
            json={"agent_type": "dream", "expected_binding_revision": 0},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            response.json(),
            {"deck_id": DECK_ID, "agent_type": "dream", "binding_revision": 1},
        )
        self.runtime_verify.assert_called_once()
        self.assertEqual(
            self.data.calls,
            ["runtime_plan", "runtime_prepare", "save"],
        )

    def test_dream_agent_type_rejects_stale_revision_before_local_verification(self) -> None:
        self.data.revision = 1
        response = self.client.put(
            f"/api/voice-decks/{DECK_ID}/agent-type",
            json={"agent_type": "dream", "expected_binding_revision": 0},
        )
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(response.json()["current_revision"], 1)
        self.runtime_verify.assert_not_called()
        self.assertEqual(self.data.calls, ["runtime_plan"])

    def test_dream_agent_type_local_failure_never_prepares_or_saves(self) -> None:
        self.runtime_verify.side_effect = binding_router.AgentTypeRuntimeUnavailable()
        response = self.client.put(
            f"/api/voice-decks/{DECK_ID}/agent-type",
            json={"agent_type": "dream", "expected_binding_revision": 0},
        )
        self.assertEqual(response.status_code, 503, response.text)
        self.assertEqual(response.json()["error_code"], "RUNTIME_PLUGIN_NOT_READY")
        self.assertEqual(self.data.calls, ["runtime_plan"])

    def test_authenticated_endpoints_and_frozen_success_shapes(self) -> None:
        methods: dict[str, set[str]] = {}
        for route in binding_router.router.routes:
            methods.setdefault(route.path, set()).update(route.methods)
        self.assertEqual(
            methods,
            {
                "/api/voice-decks/{deck_id}/agent-type": {"PUT"},
                "/api/voice-decks/{deck_id}/plugin-options": {"GET"},
                "/api/voice-decks/{deck_id}/plugin-binding": {"GET", "PUT"},
                "/api/voice-decks/{deck_id}/plugin-binding/history": {"GET"},
                "/api/voice-decks/{deck_id}/plugin-binding/validate": {"POST"},
            },
        )
        current = self.client.get(f"/api/voice-decks/{DECK_ID}/plugin-binding")
        self.assertEqual(
            current.json(),
            {"deck_id": DECK_ID, "binding_revision": 0, "applied_to": "next_run", "binding": None},
        )
        chat_type = self.client.put(
            f"/api/voice-decks/{DECK_ID}/agent-type",
            json={"agent_type": "chat", "expected_binding_revision": 0},
        )
        self.assertEqual(chat_type.status_code, 200, chat_type.text)
        self.assertEqual(chat_type.json()["agent_type"], "chat")
        options = self.client.get(f"/api/voice-decks/{DECK_ID}/plugin-options")
        self.assertTrue(options.json()["options"][0]["selectable"])
        validated = self.client.post(
            f"/api/voice-decks/{DECK_ID}/plugin-binding/validate",
            json={
                "deck_plugin_id": PLUGIN_ID,
                "deck_plugin_version": VERSION,
                "apply_to": "next_run",
            },
        )
        self.assertTrue(validated.json()["validation"]["selectable"])
        self.assertEqual(self.data.revision, 0)
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
        self.assertEqual(saved.json()["binding_revision"], 1)
        self.assertNotIn("workspace_id", saved.json())
        self.assertNotIn("creator_id", saved.json())
        history = self.client.get(f"/api/voice-decks/{DECK_ID}/plugin-binding/history")
        self.assertEqual(history.json()["current_binding_revision"], 1)
        self.assertEqual(history.json()["entries"][0]["deck_plugin_version"], VERSION)

    def test_conflict_unselectable_and_sanitized_error_shapes(self) -> None:
        request = {
            "deck_plugin_id": PLUGIN_ID,
            "deck_plugin_version": VERSION,
            "expected_binding_revision": 0,
            "apply_to": "next_run",
        }
        first = self.client.put(f"/api/voice-decks/{DECK_ID}/plugin-binding", json=request)
        self.assertEqual(first.status_code, 200, first.text)
        conflict = self.client.put(f"/api/voice-decks/{DECK_ID}/plugin-binding", json=request)
        self.assertEqual(
            conflict.json(),
            {
                "error_code": "BINDING_REVISION_CONFLICT",
                "current_revision": 1,
                "message": "Binding was modified concurrently. Please refresh and confirm your selection.",
            },
        )
        self.data.selectable = False
        request["expected_binding_revision"] = 1
        rejected = self.client.put(f"/api/voice-decks/{DECK_ID}/plugin-binding", json=request)
        self.assertEqual(rejected.status_code, 422, rejected.text)
        self.assertEqual(rejected.json()["error_code"], "DECK_PLUGIN_DISABLED")
        serialized = json.dumps(rejected.json()).lower()
        for forbidden in ("secret", "prompt", "traceback", "/users/", "command"):
            self.assertNotIn(forbidden, serialized)

    def test_access_denied_keeps_the_closed_404_shape(self) -> None:
        app = FastAPI()
        current_user = actor_projection(2, "other-workspace")
        app.dependency_overrides[binding_router._deck_current_user] = lambda: current_user
        app.dependency_overrides[binding_router._binding_data] = lambda: FakeBindingData(denied=True)
        app.include_router(binding_router.router)
        with TestClient(app) as client:
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
        app.include_router(binding_router.router)
        with TestClient(app) as anonymous:
            response = anonymous.get(f"/api/voice-decks/{DECK_ID}/plugin-binding")
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
