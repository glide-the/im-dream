# [Input] Actual Deck Plugin/binding routes and shared OAuth/default/profile/Admin-operation fixture.
# [Output] Default/role provenance, permission/error and original text Workspace technical evidence.
# [Pos] Provider-free ingress harness; remaining local Plugin installation provider uses explicit test DI.
# [Sync] 2026-09-16: exercise binding reads through the typed Admin DTO client.
from __future__ import annotations

import httpx
import pytest

from routers import deck_plugin_binding, deck_plugins
from routers.story_workspace import _story_workflow_current_user
from services.admin_data.request_auth import AdminRequestActor
from tests.test_admin_default_workspace import boundary, READ, WRITE

BINDING = "/api/voice-decks/deck-1/plugin-binding"
PLUGINS = "/api/deck-plugins/installations"


@pytest.fixture
def deck_boundary(boundary):
    browser, state, calls, schemas, operations, data = boundary
    state["profile"]["user"]["role"] = "admin"
    domain_calls = []

    class PluginProvider:
        async def list_installations(self, *, scope_id):
            domain_calls.append(("plugins", {"scope_id": scope_id}))
            return {"installations": []}

    app = browser.app
    app.include_router(deck_plugin_binding.router)
    app.include_router(deck_plugins.router)
    app.dependency_overrides[deck_plugins.get_deck_plugin_gateway] = lambda: PluginProvider()
    assert not any(resolver in app.dependency_overrides for resolver in (_story_workflow_current_user, deck_plugin_binding._deck_current_user, deck_plugins._deck_plugin_current_user))
    return browser, state, calls, schemas, operations, data, domain_calls


@pytest.mark.parametrize("path,expected", [(BINDING, ["workspace-default.ensure", "deck-plugin-binding.current"]), (PLUGINS, ["workspace-default.ensure", "user-profile.current"])])
def test_actual_public_resolver_default_role_then_business_provider(deck_boundary, path, expected):
    browser, _state, calls, *_rest, domain_calls = deck_boundary
    response = browser.get(path, headers=WRITE)
    assert response.status_code == 200 and [item[0] for item in calls] == expected
    if path == BINDING:
        assert domain_calls == []
        assert calls[1][2] == {"deck_id": "deck-1", "workspace_id": "existing-workspace-1"}
        assert response.json() == {"deck_id": "deck-1", "binding_revision": 0, "applied_to": "next_run", "binding": None}
    else:
        assert len(domain_calls) == 1
        assert domain_calls[0][1] == {"scope_id": "existing-workspace-1"}
        assert response.json()["permissions"] == {"can_manage": True, "can_install_local": True, "can_force_purge": True}


@pytest.mark.parametrize("path", [BINDING, PLUGINS])
def test_original_legacy_workspace_text_reaches_existing_domain_unchanged(deck_boundary, path):
    browser, state, calls, *_rest, domain_calls = deck_boundary
    state["default"] = {"workspace_id": "  非UUID工作区\n"}
    response = browser.get(path, headers=WRITE)
    assert response.status_code == 200
    target = calls[1][2] if path == BINDING else domain_calls[0][1]
    assert state["default"]["workspace_id"] in target.values()


@pytest.mark.parametrize("path", [BINDING, PLUGINS])
def test_existing_server_workspace_keeps_original_read_scope_branch(deck_boundary, monkeypatch, path):
    project = AdminRequestActor.current_user_projection
    monkeypatch.setattr(AdminRequestActor, "current_user_projection", lambda self: {**project(self), "workspace_id": "existing-workspace-1"})
    browser, _state, calls, *_rest, domain_calls = deck_boundary
    response = browser.get(path, headers=READ)
    assert response.status_code == 200
    assert len(domain_calls) == (1 if path == PLUGINS else 0)
    assert [item[0] for item in calls] == (["user-profile.current"] if path == PLUGINS else ["deck-plugin-binding.current"])


def test_existing_server_role_is_preserved_without_profile_fallback(deck_boundary, monkeypatch):
    project = AdminRequestActor.current_user_projection
    monkeypatch.setattr(AdminRequestActor, "current_user_projection", lambda self: {**project(self), "workspace_id": "existing-workspace-1", "role": "admin"})
    browser, state, calls, *_rest, domain_calls = deck_boundary
    state["profile"] = (503, "ADMIN_UNAVAILABLE")
    response = browser.get(PLUGINS, headers=READ)
    assert response.status_code == 200 and calls == [] and len(domain_calls) == 1


def test_admin_profile_user_role_does_not_gain_plugin_permissions(deck_boundary):
    browser, state, calls, *_rest, domain_calls = deck_boundary
    state["profile"]["user"]["role"] = "user"
    response = browser.get(PLUGINS, headers=WRITE)
    assert response.status_code == 403 and domain_calls == []
    assert [item[0] for item in calls] == ["workspace-default.ensure", "user-profile.current"]


@pytest.mark.parametrize("result,status", [({"user": {}}, 503), ({"user": None}, 503), ((403, "INSUFFICIENT_SCOPE"), 403), ((503, "ADMIN_UNAVAILABLE"), 503), (httpx.ReadTimeout("synthetic private profile text"), 504)])
def test_profile_failure_stops_instead_of_defaulting_role(deck_boundary, result, status):
    browser, state, calls, *_rest, domain_calls = deck_boundary
    state["profile"] = result
    response = browser.get(PLUGINS, headers=WRITE)
    assert response.status_code == status and domain_calls == []
    assert [item[0] for item in calls] == ["workspace-default.ensure", "user-profile.current"]
    assert "private profile" not in response.text


def test_profile_actor_id_mismatch_is_rejected(deck_boundary):
    browser, state, calls, *_rest, domain_calls = deck_boundary
    state["profile"]["user"]["id"] = "43"
    response = browser.get(PLUGINS, headers=WRITE)
    assert response.status_code == 503 and response.json()["detail"]["error_code"] == "ADMIN_RESPONSE_INVALID"
    assert domain_calls == [] and response.json()["detail"]["request_id"] == calls[1][1]


@pytest.mark.parametrize("fault", ["missing", "hash"])
def test_profile_capability_mismatch_does_not_invent_user_role(deck_boundary, fault):
    browser, _state, calls, _schemas, operations, _data, domain_calls = deck_boundary
    spec = next(item for item in operations if item["name"] == "user-profile.current")
    if fault == "missing": operations.remove(spec)
    else: spec["contract_sha256"] = "0" * 64
    response = browser.get(PLUGINS, headers=WRITE)
    assert response.status_code == 503 and domain_calls == []
    assert [item[0] for item in calls] == ["workspace-default.ensure"]


@pytest.mark.parametrize("path", [BINDING, PLUGINS])
@pytest.mark.parametrize("headers,status", [({}, 401), (READ, 403), ({"authorization": "Bearer idg_" + "a" * 43}, 401)])
def test_missing_or_wrong_oauth_default_scope_stops_public_resolver(deck_boundary, path, headers, status):
    browser, _state, calls, *_rest, domain_calls = deck_boundary
    response = browser.get(path, headers=headers)
    assert response.status_code == status and calls == [] and domain_calls == []


def test_write_only_plugin_install_cannot_read_role_without_scope(deck_boundary):
    browser, _state, calls, *_rest, domain_calls = deck_boundary
    response = browser.post("/api/deck-plugins/install", headers={"authorization": "Bearer write-only-token"}, json={"deck_plugin_id": "plugin-1", "version": "1.0.0", "source": "controlled://plugin-1", "idempotency_key": "explicit-key"})
    assert response.status_code == 403 and response.json()["detail"]["error_code"] == "INSUFFICIENT_SCOPE"
    assert [item[0] for item in calls] == ["workspace-default.ensure"] and domain_calls == []


@pytest.mark.parametrize("path", [BINDING, PLUGINS])
def test_unknown_default_stops_before_profile_or_remaining_business_provider(deck_boundary, path):
    browser, state, calls, *_rest, domain_calls = deck_boundary
    state["default"] = httpx.ReadTimeout("synthetic private default text")
    response = browser.get(path, headers=WRITE)
    assert response.status_code == 504 and response.json()["detail"]["outcome_unknown"] is True
    assert [item[0] for item in calls] == ["workspace-default.ensure"] and domain_calls == []
