# [Input] Actual FastAPI Session router, Admin DTO transport and explicit synthetic OAuth verifier.
# [Output] Reusable provider-free Session boundary with precise business fixtures and request receipts.
# [Pos] Named validation fixture; no shadow production entry, database, model or user service.
# [Sync] 2026-09-15: replace direct database mocks with the production authentication/operation path.
from __future__ import annotations

import json

import httpx
from fastapi import FastAPI

from routers.sessions import router
from services.admin_data import AdminDataClient, AdminDataConfig, AdminDataError, OAuthPrincipalClaims
from services.admin_data.request_auth import AdminRequestAuth
from services.admin_data.session_data import SESSION_OPERATIONS


def editor_state(session_id="session-1"):
    return {"id": session_id, "cells": [{"id": "text-1", "type": "text", "content": "正文 hello"}],
        "commentors": [], "tasks": [], "weightPath": [], "overlappedPhrases": [], "notFoundPhrases": []}


def full_session(session_id="session-1"):
    return {"id": session_id, "name": None, "editor_state": editor_state(session_id), "labels": ["日记"],
        "created_at": "2026-08-30T16:30:00.123456Z", "updated_at": "2026-08-31T02:00:00.654321Z"}


def preview_session(session_id="session-1"):
    return {key: value for key, value in full_session(session_id).items() if key != "editor_state"} | {"first_line": "正文 hello", "text": None}


class SessionVerifier:
    def verify(self, token, *, required_scopes):
        if token == "invalid-token":
            raise AdminDataError("INVALID_ACCESS_TOKEN", 401)
        scopes = frozenset({"dream:read"} if token == "read-only" else {"dream:read", "dream:write"})
        if not required_scopes <= scopes:
            raise AdminDataError("INSUFFICIENT_SCOPE", 403)
        return OAuthPrincipalClaims("session-ba-subject", "dream-browser", scopes, "fixture-jti", 100, 400)


def build_session_boundary(*, user_id="42"):
    config = AdminDataConfig(base_url="https://admin.example", issuer="https://admin.example/api/auth",
        resource="https://dream.example/api", service_client_id="dream-service", service_secret="s" * 32)
    calls, outputs = [], {
        "session.save": {"session": full_session()}, "session.get": {"session": full_session()},
        "session.batch": {"sessions": [full_session()]}, "session.list": {"sessions": [preview_session()]},
        "session.text-list": {"sessions": [{key: value for key, value in preview_session().items() if key not in {"labels", "first_line"}} | {"text": "正文 hello"}]},
        "session.delete": {"deleted": True},
    }
    def handler(request):
        request_id = request.headers["x-request-id"]
        if request.url.path.endswith("/capabilities"):
            value = {"version": "1", "auth": {"issuer": config.issuer, "jwks_uri": config.jwks_uri,
                "resource": config.resource, "algorithm": "ES256", "clients": {"browser": "dream-browser", "device": "dream-device"},
                "scopes": ["dream:read", "dream:write"], "delegations": []}, "schema_capabilities": [],
                "operations": [item.capability.model_dump() for item in SESSION_OPERATIONS]}
        elif request.url.path.endswith("/principal"):
            scopes = ["dream:read"] if request.headers["authorization"] == "Bearer read-only" else ["dream:read", "dream:write"]
            value = {"subject": "session-ba-subject", "canonical_user_id": user_id, "client_id": "dream-browser", "scopes": scopes, "status": "active"}
        else:
            name = request.url.path.rsplit("/", 1)[-1]
            body = json.loads(request.content)
            assert body["request_id"] == request_id and set(body) == {"request_id", "input"}
            assert not {"user_id", "actor_id", "canonical_user_id"} & body["input"].keys()
            assert request.headers["authorization"] == "Bearer write-token" or request.headers["authorization"] == "Bearer read-only"
            assert request.headers["x-ink-dream-credential"] == "s" * 32 and "cookie" not in request.headers
            calls.append((name, body["input"], request_id))
            value = outputs[name]
            if isinstance(value, Exception):
                raise value
            if isinstance(value, tuple):
                return httpx.Response(value[0], json={"request_id": request_id, "error": {"code": value[1], "message": "synthetic private error"}})
        return httpx.Response(200, json={"request_id": request_id, "data": value})
    client = AdminDataClient(config, client=httpx.Client(transport=httpx.MockTransport(handler)), operations=SESSION_OPERATIONS)
    app = FastAPI()
    app.state.admin_request_auth = AdminRequestAuth(config, client=client, verifier=SessionVerifier())
    app.include_router(router)
    return app, calls, outputs
