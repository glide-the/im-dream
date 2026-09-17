# [Input] Actual retired FastAPI paths with synthetic sensitive bodies and explicit authority config.
# [Output] 410 endpoint migration, no signing/DB/HTTP/cookie action and safe invalid-config failure.
# [Pos] Provider-free public issuer-retirement contracts; actual Admin OAuth remains separately owned.
# [Sync] 2026-09-16: fence the FastAPI application and deploy projections from obsolete Dream session-cookie authority.
# [Sync] 2026-09-14: test legacy paths through production routers without forwarding credentials.

import re
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import auth
import database
from routers import auth as auth_routes, device_oauth, oauth
from services.admin_data.retired_auth import retired_authentication

CONFIG = {"INK_ADMIN_DREAM_BASE_URL": "https://admin.example", "INK_ADMIN_AUTH_ISSUER": "https://admin.example/api/auth", "INK_DREAM_API_RESOURCE": "https://dream.example/api"}
PATHS = [("POST", "/api/register"), ("POST", "/api/login"), ("POST", "/auth/logout"),
    ("GET", "/oauth/google/login"), ("GET", "/oauth/google/callback"),
    ("POST", "/oauth/device/code"), ("GET", "/oauth/device/verify"),
    ("POST", "/oauth/device/verify"), ("POST", "/oauth/token")]


def forbidden(*args, **kwargs):
    raise AssertionError("Retired authentication cannot sign, query, persist or forward")


@pytest.mark.parametrize("method,path", PATHS)
def test_public_paths_retire_without_touching_credentials_or_other_authorities(monkeypatch, method, path):
    for key, value in CONFIG.items(): monkeypatch.setenv(key, value)
    monkeypatch.setenv("INK_ADMIN_DREAM_SERVICE_SECRET", "synthetic-global-service-secret")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "synthetic-global-google-secret")
    for name in ("get_db", "create_user", "get_user_by_email", "create_refresh_token", "revoke_user_refresh_tokens"):
        monkeypatch.setattr(database, name, forbidden)
    for name in ("create_access_token", "create_refresh_token_value", "hash_password", "verify_password"):
        monkeypatch.setattr(auth, name, forbidden)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    app = FastAPI()
    for router in (auth_routes.router, oauth.router, device_oauth.router): app.include_router(router)
    with TestClient(app) as client:
        response = client.request(method, path + "?code=synthetic-code&return_to=https://other.example",
            content=b'{"password":"synthetic-password","refresh_token":"synthetic-refresh"}',
            headers={"Content-Type": "application/json", "Authorization": "Bearer synthetic-token", "Cookie": "refresh_token=synthetic-cookie", "X-Ink-Dream-Credential": "synthetic-browser-service"})
    assert response.status_code == 410 and response.headers["cache-control"] == "no-store"
    assert "set-cookie" not in response.headers and "location" not in response.headers and "x-new-access-token" not in response.headers
    assert "synthetic" not in response.text and "other.example" not in response.text
    assert response.json()["authentication"] == {
        "issuer": "https://admin.example/api/auth", "authorization_endpoint": "https://admin.example/api/auth/oauth2/authorize",
        "token_endpoint": "https://admin.example/api/auth/oauth2/token", "device_authorization_endpoint": "https://admin.example/api/auth/device/code",
        "revocation_endpoint": "https://admin.example/api/auth/oauth2/revoke", "jwks_uri": "https://admin.example/api/auth/jwks",
        "verification_uri": "https://admin.example/auth/device", "resource": "https://dream.example/api",
    }


@pytest.mark.parametrize("patch", [{"INK_ADMIN_DREAM_BASE_URL": ""}, {"INK_ADMIN_DREAM_BASE_URL": "http://remote.example"},
    {"INK_ADMIN_DREAM_BASE_URL": "https://admin.example/other"}, {"INK_ADMIN_AUTH_ISSUER": "https://another.example/api/auth"},
    {"INK_DREAM_API_RESOURCE": ""}, {"INK_DREAM_API_RESOURCE": "invalid\nresource"}])
def test_missing_invalid_authority_fails_closed_without_guessing(patch):
    response = retired_authentication({**CONFIG, **patch})
    assert response.status_code == 503 and b"authentication" in response.body
    assert b"https://" not in response.body and b"token_endpoint" not in response.body


def test_retired_path_ignores_even_malformed_password_body(monkeypatch):
    for key, value in CONFIG.items(): monkeypatch.setenv(key, value)
    app = FastAPI(); app.include_router(auth_routes.router)
    with TestClient(app) as client:
        response = client.post("/api/login", content=b'{"password":', headers={"Content-Type": "application/json"})
    assert response.status_code == 410


def test_migration_owner_reads_only_public_authority_configuration():
    class PublicConfig(dict):
        def get(self, key, default=None):
            assert key in CONFIG
            return super().get(key, default)
    assert retired_authentication(PublicConfig(CONFIG)).status_code == 410


def test_fastapi_and_current_deployments_have_no_local_session_cookie_authority():
    root = Path(__file__).resolve().parents[2]
    retired_secrets = (
        "GOOGLE_CLIENT_SECRET",
        "JWT_SECRET",
        "JWT_SECRET_KEY",
        "SESSION_SECRET_KEY",
        "OAUTH_TOKEN_ENCRYPTION_KEY",
        "AUTH_TOKEN_ENCRYPTION_KEY",
    )
    retired_cookie_policy = ("COOKIE_SECURE", "COOKIE_SAMESITE")
    next_only = ("INK_DREAM_BFF_COOKIE_SECRET",)

    server = (root / "backend/server.py").read_text(encoding="utf-8")
    assert "from starlette.middleware.sessions import SessionMiddleware" not in server
    assert re.search(r"app\.add_middleware\(\s*SessionMiddleware", server) is None
    for name in (*retired_secrets, *retired_cookie_policy, *next_only):
        assert f'"{name}"' in server
        assert f'os.environ.get("{name}")' not in server
    assert "os.environ.pop(key, None)" in server

    workflow_security = (
        root / "backend/services/story_workspace/workflow_security.py"
    ).read_text(encoding="utf-8")
    assert 'os.getenv("JWT_SECRET")' not in workflow_security

    for path in (
        root / "docker-compose.yml",
        root / "deploy/remote-ssh/docker-compose.yml",
    ):
        text = path.read_text(encoding="utf-8")
        for name in (*retired_secrets, *retired_cookie_policy, *next_only):
            assert re.search(rf"^\s+{name}: \"\"$", text, re.MULTILINE), path

    setup_env = (root / "deploy/setup-env.sh").read_text(encoding="utf-8")
    for name in retired_secrets:
        assert not re.search(rf"^{name}\s+ink-", setup_env, re.MULTILINE)
    assert re.search(
        r"^INK_ADMIN_DREAM_SERVICE_SECRET\s+\$\{ADMIN_SERVICE_SECRET_NAME\}$",
        setup_env,
        re.MULTILINE,
    )
    assert re.search(
        r"^INK_DREAM_BFF_COOKIE_SECRET\s+\$\{BFF_COOKIE_SECRET_NAME\}$",
        setup_env,
        re.MULTILINE,
    )
    assert "CLOUD_FRONTEND_SECRET_REFS=${FRONTEND_SECRET_REFS}" in setup_env
    assert "gcloud secrets add-iam-policy-binding" in setup_env
    assert "gcloud projects add-iam-policy-binding" not in setup_env

    for path in (root / "deploy/google-cloud/deploy.sh",):
        text = path.read_text(encoding="utf-8")
        assert "BACKEND_COOKIE_SECURE" not in text
        assert "BACKEND_COOKIE_SAMESITE" not in text
        assert "sanitize_secret_refs" in text
        assert "validate_frontend_secret_refs" in text
        assert "--clear-secrets" in text
        assert '--set-secrets="${frontend_secret_refs}"' in text
        assert '--service-account="${FRONTEND_SA_EMAIL}"' in text
        for name in (*retired_secrets, *next_only):
            assert name in text

    retired_cloud_sync = (
        root / "deploy/google-cloud/sync-data.sh"
    ).read_text(encoding="utf-8")
    assert "retired Dream SQLite command refused" in retired_cloud_sync
    assert "gsutil" not in retired_cloud_sync
    assert "gcloud run" not in retired_cloud_sync
    assert "sqlite3" not in retired_cloud_sync
    assert "ink-and-memory.db" not in retired_cloud_sync

    assert "INK_DREAM_BFF_COOKIE_SECRET" in (
        root / "deploy/autodl-ssh/prepare-env.sh"
    ).read_text(encoding="utf-8")
    assert "DREAM_BFF_COOKIE_SECRET" in (
        root / "deploy/remote-ssh/prepare-env.sh"
    ).read_text(encoding="utf-8")
