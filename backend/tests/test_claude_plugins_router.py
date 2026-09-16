# [Input] Public Claude Plugin routes, authenticated actor and typed fake Admin consumer.
# [Output] Preserved HTTP shapes, actor-free DTO dispatch and background execution handoff evidence.
# [Pos] Provider-free route contract; Dream PostgreSQL access is fenced.
# [Sync] 2026-09-16: migrate catalog/install/operation/installation routes to Registry175-182.
from __future__ import annotations

from datetime import UTC, datetime
from unittest import mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import routers.claude_plugins as claude_plugins
from services.admin_data.claude_plugin_data import (
    ClaudePluginInstallPlanDTO,
    ClaudePluginInstallationDetailDTO,
    ClaudePluginInstallationDTO,
    ClaudePluginInstallationsListDTO,
    ClaudePluginMarketplaceListDTO,
    ClaudePluginOperationDTO,
    ClaudePluginOperationsListDTO,
)
from services.admin_data.errors import AdminDataError
from services.admin_data.request_auth import AdminRequestActor


HEADERS = {"authorization": "Bearer synthetic"}
NOW = datetime(2026, 9, 16, tzinfo=UTC)


def operation(**changes) -> ClaudePluginOperationDTO:
    values = {
        "id": "cop_operation",
        "operation_kind": "install",
        "requested_package_spec": "demo@market",
        "marketplace_entry_id": None,
        "status": "queued",
        "phase": "queued",
        "progress": 0,
        "message": "Queued for real claude plugin install",
        "executable": None,
        "argv_json": None,
        "cwd": None,
        "cli_version": None,
        "exit_code": None,
        "evidence_path": None,
        "installation_id": None,
        "error_code": None,
        "error_summary": None,
        "created_at": NOW,
        "updated_at": NOW,
        "finished_at": None,
    }
    values.update(changes)
    return ClaudePluginOperationDTO.model_validate(values)


def installation(**changes) -> ClaudePluginInstallationDTO:
    values = {
        "id": "cpi_installation",
        "requested_package_spec": "demo@market",
        "marketplace_entry_id": None,
        "package_name": "demo",
        "marketplace": "market",
        "requested_version": None,
        "resolved_version": "1.0.0",
        "source_type": "marketplace",
        "artifact_digest": "sha256:" + "a" * 64,
        "artifact_path": "/shared/plugins/demo",
        "claude_cli_version": "2.1.220",
        "cli_git_commit_sha": None,
        "manifest_json": '{"name":"demo"}',
        "component_inventory_json": '{"skills":[]}',
        "compatibility_json": "{}",
        "status": "ready",
        "operation_id": "cop_operation",
        "error_code": None,
        "error_summary": None,
        "file_count": 3,
        "created_at": NOW,
        "updated_at": NOW,
        "installed_at": NOW,
    }
    values.update(changes)
    return ClaudePluginInstallationDTO.model_validate(values)


class FakeData:
    def __init__(self) -> None:
        self.calls = []
        self.error: AdminDataError | None = None
        self.plan = ClaudePluginInstallPlanDTO(
            accepted=True,
            operation_id="cop_operation",
            package_spec="demo@market",
            marketplace_entry_id=None,
            requested_source_type="marketplace",
            marketplace_source=None,
        )

    def _return(self, name, input_dto, request_id, access_token, value):
        self.calls.append(
            (name, input_dto.model_dump(mode="json"), request_id, access_token)
        )
        if self.error is not None:
            raise self.error
        return value

    def list_installations(self, input_dto, request_id, *, access_token):
        item = installation().model_dump()
        item["deck_ref_count"] = 2
        return self._return(
            "list_installations",
            input_dto,
            request_id,
            access_token,
            ClaudePluginInstallationsListDTO(
                installations=[item],
                permissions={"can_manage_shared_plugins": True},
            ),
        )

    def list_marketplace(self, input_dto, request_id, *, access_token):
        return self._return(
            "list_marketplace",
            input_dto,
            request_id,
            access_token,
            ClaudePluginMarketplaceListDTO(
                entries=[],
                scope="platform-global",
                permissions={"can_install_shared_plugins": True},
            ),
        )

    def prepare(self, input_dto, request_id, *, access_token):
        return self._return(
            "prepare", input_dto, request_id, access_token, self.plan
        )

    def list_operations(self, input_dto, request_id, *, access_token):
        return self._return(
            "list_operations",
            input_dto,
            request_id,
            access_token,
            ClaudePluginOperationsListDTO(operations=[operation()]),
        )

    def read_operation(self, input_dto, request_id, *, access_token):
        return self._return(
            "read_operation",
            input_dto,
            request_id,
            access_token,
            operation(id=input_dto.operation_id),
        )

    def read_installation(self, input_dto, request_id, *, access_token):
        detail = installation(id=input_dto.installation_id).model_dump()
        detail["deck_refs"] = []
        return self._return(
            "read_installation",
            input_dto,
            request_id,
            access_token,
            ClaudePluginInstallationDetailDTO.model_validate(detail),
        )

    def uninstall(self, input_dto, request_id, *, access_token):
        return self._return(
            "uninstall",
            input_dto,
            request_id,
            access_token,
            installation(id=input_dto.installation_id, status="uninstalled"),
        )


def boundary(monkeypatch):
    import database

    monkeypatch.setattr(
        database,
        "get_db",
        lambda: pytest.fail("Claude Plugin public routes must not use Dream PG"),
    )
    actor = AdminRequestActor(
        subject="opaque-subject",
        canonical_user_id="42",
        client_id="dream-browser",
        scopes=frozenset({"dream:read", "dream:write"}),
        issued_at=1,
        expires_at=999,
        access_token="delegated-oauth",
    )
    data = FakeData()
    app = FastAPI()
    app.include_router(claude_plugins.router)
    app.dependency_overrides[claude_plugins.get_current_user] = (
        actor.current_user_projection
    )
    app.dependency_overrides[claude_plugins._plugin_data] = lambda: data
    return TestClient(app), data, actor


def test_reads_delegate_closed_dtos_without_authority_selectors(monkeypatch):
    client, data, _ = boundary(monkeypatch)
    with client:
        assert client.get(
            "/api/claude-plugins/installations", headers=HEADERS
        ).json()["installations"][0]["deck_ref_count"] == 2
        assert client.get(
            "/api/claude-plugins/marketplace", headers=HEADERS
        ).json()["scope"] == "platform-global"
        assert len(
            client.get(
                "/api/claude-plugins/operations?limit=999", headers=HEADERS
            ).json()["operations"]
        ) == 1
        assert client.get(
            "/api/claude-plugins/operations/cop_selected", headers=HEADERS
        ).json()["id"] == "cop_selected"
        assert client.get(
            "/api/claude-plugins/installations/cpi_selected", headers=HEADERS
        ).json()["id"] == "cpi_selected"

    assert [item[0] for item in data.calls] == [
        "list_installations",
        "list_marketplace",
        "list_operations",
        "read_operation",
        "read_installation",
    ]
    assert data.calls[2][1] == {"limit": 100}
    assert all(
        not {"actor_id", "user_id", "sql", "table", "column"} & set(call[1])
        for call in data.calls
    )
    assert all(call[3] == "delegated-oauth" for call in data.calls)


def test_install_prepares_in_admin_then_hands_plan_to_dream_executor(monkeypatch):
    client, data, actor = boundary(monkeypatch)
    with mock.patch.object(claude_plugins, "_run_install") as run_install:
        with client:
            response = client.post(
                "/api/claude-plugins/install",
                headers=HEADERS,
                json={"package_spec": "demo@market"},
            )

    assert response.status_code == 202
    assert response.json() == {
        "accepted": True,
        "operation_id": "cop_operation",
        "package_spec": "demo@market",
        "marketplace_entry_id": None,
    }
    assert data.calls[0][0:2] == (
        "prepare",
        {
            "source_kind": "package",
            "package_spec": "demo@market",
            "source_type": None,
        },
    )
    run_install.assert_called_once_with(data.plan, data, actor)


def test_marketplace_install_uses_only_entry_id_from_the_browser(monkeypatch):
    client, data, _ = boundary(monkeypatch)
    data.plan = data.plan.model_copy(
        update={
            "marketplace_entry_id": "cpme_demo",
            "requested_source_type": "marketplace",
        }
    )
    with mock.patch.object(claude_plugins, "_run_install"):
        with client:
            response = client.post(
                "/api/claude-plugins/install",
                headers=HEADERS,
                json={"marketplace_entry_id": "cpme_demo"},
            )
    assert response.status_code == 202
    assert data.calls[0][1] == {
        "source_kind": "marketplace_entry",
        "marketplace_entry_id": "cpme_demo",
    }


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"package_spec": "demo@market", "marketplace_entry_id": "cpme_demo"},
        {"package_spec": "bad"},
        {"package_spec": "demo@market", "user_id": "42"},
        {
            "marketplace_entry_id": "cpme_demo",
            "source_type": "marketplace",
        },
    ],
)
def test_invalid_install_inputs_fail_before_admin_dispatch(monkeypatch, body):
    client, data, _ = boundary(monkeypatch)
    with client:
        response = client.post(
            "/api/claude-plugins/install", headers=HEADERS, json=body
        )
    assert response.status_code == 422
    assert not data.calls


def test_uninstall_delegates_one_typed_identifier(monkeypatch):
    client, data, _ = boundary(monkeypatch)
    with client:
        response = client.post(
            "/api/claude-plugins/installations/cpi_selected/uninstall",
            headers=HEADERS,
        )
    assert response.status_code == 200
    assert response.json()["status"] == "uninstalled"
    assert data.calls[0][0:2] == (
        "uninstall",
        {"installation_id": "cpi_selected"},
    )


def test_admin_failures_preserve_safe_status_and_unknown_outcome(monkeypatch):
    client, data, _ = boundary(monkeypatch)
    data.error = AdminDataError(
        "ADMIN_WRITE_RESULT_UNKNOWN", 503, "original-request", True
    )
    with client:
        response = client.post(
            "/api/claude-plugins/installations/cpi_selected/uninstall",
            headers=HEADERS,
        )
    assert response.status_code == 503
    assert response.json()["error"] == {
        "code": "CLAUDE_PLUGIN_OPERATION_RESULT_UNKNOWN",
        "phase": "persistence",
        "message": "The plugin operation result could not be confirmed.",
        "recovery_action": (
            "Refresh the operation status before deciding whether to retry."
        ),
        "operation_id": "original-request",
        "request_id": "original-request",
        "outcome_unknown": True,
    }
