# [Input] Actual typed profile/request-auth owner and the production FastAPI dependency.
# [Output] Provider-free claim/identity/profile/scope and public-boundary regression checks.
# [Pos] Technical authentication contracts; no real users, PostgreSQL or model calls.
# [Sync] 2026-09-14: exercise strict profile wire schemas and explicit request actor propagation.
from __future__ import annotations

import json

import httpx
import pytest
from fastapi import Depends, FastAPI, Request
from fastapi.testclient import TestClient
from pydantic import ValidationError

from routers.deps import get_current_user
from services.admin_data import AdminDataClient, AdminDataConfig, AdminDataError, OAuthPrincipalClaims
from services.admin_data.profile_data import CURRENT_PROFILE, ProfileInputDTO, UserProfileDTO
from services.admin_data.request_auth import AdminRequestAuth


@pytest.fixture
def config():
    return AdminDataConfig(base_url="https://admin.example", issuer="https://admin.example/api/auth", resource="https://dream.example/api", service_secret="s" * 32, service_client_id="dream-service")


def profile_value():
    return {"id": "42", "email": "member@example.com", "display_name": None, "avatar_url": None, "role": "user", "created_at": "2026-09-14T00:00:00.123456Z", "updated_at": None, "auth_providers": ["credential", "google"]}


class Verifier:
    def verify(self, token, *, required_scopes):
        if token == "expired-token":
            raise AdminDataError("INVALID_ACCESS_TOKEN", 401)
        scopes = frozenset({"dream:read"} if token == "read-token" else {"dream:read", "dream:write"})
        if not required_scopes <= scopes:
            raise AdminDataError("INSUFFICIENT_SCOPE", 403)
        return OAuthPrincipalClaims("opaque-ba-subject", "dream-browser", scopes, "token-id", 100, 400)


def owner(config, *, principal_patch=None, profile_patch=None, fail_capabilities_once=False):
    calls = []
    def handler(request):
        calls.append(request)
        request_id = request.headers["x-request-id"]
        if request.url.path.endswith("/capabilities"):
            if fail_capabilities_once and sum(item.url.path.endswith("/capabilities") for item in calls) == 1:
                return httpx.Response(503, json={"request_id": request_id, "error": {"code": "ADMIN_UNAVAILABLE", "message": "safe"}})
            value = {"version": "1", "auth": {"issuer": config.issuer, "jwks_uri": config.jwks_uri, "algorithm": "ES256", "resource": config.resource, "clients": {"browser": "dream-browser", "device": "dream-device"}, "scopes": ["dream:read", "dream:write"], "delegations": []}, "schema_capabilities": [], "operations": [CURRENT_PROFILE.capability.model_dump()]}
        elif request.url.path.endswith("/principal"):
            token = request.headers["authorization"].removeprefix("Bearer ")
            value = {"subject": "opaque-ba-subject", "canonical_user_id": "42", "client_id": "dream-browser", "scopes": ["dream:read"] if token == "read-token" else ["dream:read", "dream:write"], "status": "active", **(principal_patch or {})}
        elif request.url.path.endswith("/operations/user-profile.current"):
            assert json.loads(request.content) == {"request_id": request_id, "input": {}}
            value = {"user": {**profile_value(), **(profile_patch or {})}}
        else:
            raise AssertionError("Unexpected domain request")
        return httpx.Response(200, json={"request_id": request_id, "data": value})
    client = AdminDataClient(config, client=httpx.Client(transport=httpx.MockTransport(handler)), operations=(CURRENT_PROFILE,))
    return AdminRequestAuth(config, client=client, verifier=Verifier()), calls


def test_actor_maps_opaque_subject_via_principal_and_profile_preserves_public_response(config):
    auth_owner, calls = owner(config)
    actor = auth_owner.authenticate("synthetic-admin-token", "request-1", required_scopes=frozenset({"dream:read"}))
    assert actor.canonical_user_id == "42" and actor.subject == "opaque-ba-subject"
    assert "synthetic-admin-token" not in repr(actor)
    assert actor.current_user_projection()["user_id"] == 42
    assert actor.current_user_projection()["_admin_actor"] is actor
    assert auth_owner.current_profile(actor, "profile-1").dream_public_profile() == {"id": 42, "email": "member@example.com", "display_name": None, "avatar_url": None, "role": "user", "created_at": "2026-09-14T00:00:00.123456Z"}
    auth_owner.authenticate("synthetic-admin-token", "request-2", required_scopes=frozenset({"dream:read"}))
    assert sum(item.url.path.endswith("/capabilities") for item in calls) == 1
    assert sum(item.url.path.endswith("/principal") for item in calls) == 2


@pytest.mark.parametrize("patch", [{"subject": "different-subject"}, {"client_id": "different-client"}, {"scopes": ["dream:read"]}, {"status": "disabled"}])
def test_principal_must_match_verified_claims(config, patch):
    auth_owner, _ = owner(config, principal_patch=patch)
    with pytest.raises(AdminDataError, match="ADMIN_RESPONSE_INVALID"):
        auth_owner.authenticate("synthetic-admin-token", "request-1", required_scopes=frozenset({"dream:read"}))


def test_profile_cannot_change_authenticated_canonical_identity(config):
    auth_owner, _ = owner(config, profile_patch={"id": "43"})
    actor = auth_owner.authenticate("read-token", "request-1", required_scopes=frozenset({"dream:read"}))
    with pytest.raises(AdminDataError, match="ADMIN_RESPONSE_INVALID"):
        auth_owner.current_profile(actor, "profile-1")


def test_failed_capability_initialization_can_recover_without_caching_identity(config):
    auth_owner, calls = owner(config, fail_capabilities_once=True)
    with pytest.raises(AdminDataError, match="ADMIN_UNAVAILABLE"):
        auth_owner.authenticate("read-token", "request-1", required_scopes=frozenset({"dream:read"}))
    auth_owner.authenticate("read-token", "request-2", required_scopes=frozenset({"dream:read"}))
    assert len(calls) == 3


@pytest.mark.parametrize("field,value", [("id", 42), ("id", "9223372036854775808"), ("email", "invalid-email"), ("email", ".member@example.com"), ("created_at", "2026-02-29T00:00:00Z"), ("created_at", "2026-09-14T00:00:00"), ("auth_providers", ["password"]), ("password_hash", "synthetic")])
def test_profile_output_is_a_closed_strict_domain_dto(field, value):
    with pytest.raises(ValidationError):
        UserProfileDTO.model_validate({**profile_value(), field: value})


def test_profile_input_cannot_choose_a_user():
    with pytest.raises(ValidationError):
        ProfileInputDTO.model_validate({"user_id": "43"})


def app_client(config):
    auth_owner, calls = owner(config)
    app = FastAPI()
    app.state.admin_request_auth = auth_owner
    @app.api_route("/boundary", methods=["GET", "POST"])
    async def boundary(request: Request, user=Depends(get_current_user)):
        assert request.state.admin_request_actor is user["_admin_actor"]
        return {"user_id": user["user_id"]}
    return TestClient(app), calls


@pytest.mark.parametrize("method,token,status", [("GET", "read-token", 200), ("POST", "read-token", 403), ("POST", "write-token", 200), ("GET", "expired-token", 401)])
def test_public_dependency_checks_method_scope_and_propagates_explicit_actor(config, method, token, status):
    client, calls = app_client(config)
    response = client.request(method, "/boundary", headers={"authorization": "Bearer " + token})
    assert response.status_code == status
    assert "x-new-access-token" not in response.headers and "set-cookie" not in response.headers
    if status != 200:
        assert not calls


def test_public_dependency_rejects_cookie_and_query_tokens(config):
    client, calls = app_client(config)
    client.cookies.set("access_token", "read-token")
    client.cookies.set("token", "read-token")
    response = client.get("/boundary?token=read-token")
    assert response.status_code == 401 and not calls


@pytest.mark.parametrize("path", ["/api/me", "/auth/me"])
def test_public_profile_routes_use_admin_without_dream_database(config, monkeypatch, path):
    import database
    from routers.auth import router
    def forbidden(*args, **kwargs):
        raise AssertionError("Profile production route must not read Dream PG")
    monkeypatch.setattr(database, "get_user_by_id", forbidden)
    app = FastAPI()
    app.state.admin_request_auth, _ = owner(config)
    app.include_router(router)
    response = TestClient(app).get(path, headers={"authorization": "Bearer read-token"})
    assert response.status_code == 200
    assert response.json() == {"id": 42, "email": "member@example.com", "display_name": None, "avatar_url": None, "role": "user", "created_at": "2026-09-14T00:00:00.123456Z"}


def test_file_auth_dependencies_share_the_same_admin_authority():
    from routers.storage import _require_storage_auth
    from routers.workspace import _require_workspace_auth
    assert _require_storage_auth is get_current_user
    assert _require_workspace_auth is get_current_user
