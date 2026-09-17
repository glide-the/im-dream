# [Sync] 2026-09-17: verify confidential service OAuth and separate delegated-user Bearer transport.
# [Input] Registry103 contracts, current-user picture responses and three public read routes.
# [Output] Exact DTO, projection, validation, capability and Dream-DB fence evidence.
# [Pos] Provider-free picture-history consumer/route harness; no PostgreSQL or real account.
# [Sync] 2026-09-15: bind three Dream picture routes to Admin 547e898 Registry103.
from __future__ import annotations

import json
from uuid import UUID

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from routers import pictures as picture_routes
from services.admin_data import AdminDataClient, AdminDataConfig, AdminDataError
from services.admin_data.picture_history_data import (
    LIST_PICTURE_HISTORY,
    PICTURE_HISTORY_OPERATIONS,
    READ_PICTURE_FULL,
    PictureHistoryFullInputDTO,
    PictureHistoryItemDTO,
    PictureHistoryListInputDTO,
)
from services.admin_data.request_auth import AdminRequestAuth
from services.admin_data.workflow_data import WORKFLOW_SCHEMA_REQUIREMENTS
from tests.test_admin_request_auth import Verifier


HEADERS = {"authorization": "Bearer read-token"}
TIME = "2026-09-15T03:02:01.123456+08:00"


def _forbidden(*_args, **_kwargs):
    pytest.fail("Public picture-history routes must not use Dream PostgreSQL")


def _outputs() -> dict:
    return {
        "picture-history.list": {
            "pictures": [
                {
                    "date": "2026-09-15",
                    "base64": "thumbnail-original",
                    "prompt": None,
                    "created_at": TIME,
                },
                {
                    "date": "2026-09-14",
                    "base64": "full-image-fallback",
                    "prompt": "",
                    "created_at": None,
                },
            ]
        },
        "picture-history.full": {"image_base64": "full-image-original"},
    }


@pytest.fixture
def boundary(monkeypatch):
    import database

    for name in (
        "get_db",
        "get_daily_pictures",
        "get_daily_pictures_range",
        "get_daily_picture_full",
    ):
        monkeypatch.setattr(database, name, _forbidden)

    config = AdminDataConfig(
        base_url="https://admin.example",
        issuer="https://admin.example/api/auth",
        resource="https://dream.example/api",
        service_client_id="dream-service",
        service_secret="s" * 32,
    )
    state = {
        "calls": [],
        "outputs": _outputs(),
        "schemas": [item.model_dump() for item in WORKFLOW_SCHEMA_REQUIREMENTS],
        "operations": [
            item.capability.model_dump() for item in PICTURE_HISTORY_OPERATIONS
        ],
    }

    class PictureVerifier(Verifier):
        def verify(self, token, *, required_scopes):
            if token.startswith("idg_"):
                raise AdminDataError("INVALID_ACCESS_TOKEN", 401)
            if token == "write-only-token":
                raise AdminDataError("INSUFFICIENT_SCOPE", 403)
            return super().verify(token, required_scopes=required_scopes)

    def handler(request: httpx.Request) -> httpx.Response:
        request_id = request.headers["x-request-id"]
        UUID(request_id)
        if request.url.path.endswith("/capabilities"):
            value = {
                "version": "1",
                "auth": {
                    "issuer": config.issuer,
                    "jwks_uri": config.jwks_uri,
                    "resource": config.resource,
                    "algorithm": "ES256",
                    "clients": {
                        "browser": "dream-browser",
                        "device": "dream-device",
                    },
                    "scopes": ["dream:read", "dream:write"],
                    "delegations": [],
                },
                "schema_capabilities": state["schemas"],
                "operations": state["operations"],
            }
        elif request.url.path.endswith("/principal"):
            value = {
                "subject": "opaque-ba-subject",
                "canonical_user_id": "42",
                "client_id": "dream-browser",
                "scopes": ["dream:read"],
                "status": "active",
            }
        else:
            operation = request.url.path.rsplit("/", 1)[-1]
            body = json.loads(request.content)
            assert set(body) == {"request_id", "input"}
            assert body["request_id"] == request_id
            assert not {
                "user_id",
                "friend_id",
                "actor_id",
                "subject",
                "sql",
                "table",
                "column",
            } & body["input"].keys()
            assert request.headers["authorization"] == "Bearer read-token"
            assert request.headers["x-ink-dream-service-authorization"] == "Bearer fixture.service.access.token"
            assert "x-ink-dream-credential" not in request.headers
            assert "cookie" not in request.headers
            state["calls"].append((operation, body["input"], request_id))
            output = state["outputs"][operation]
            if isinstance(output, Exception):
                raise output
            value = output
        return httpx.Response(
            200,
            json={"request_id": request_id, "data": value},
        )

    http = httpx.Client(transport=httpx.MockTransport(handler))
    client = AdminDataClient(
        config,
        client=http,
        operations=PICTURE_HISTORY_OPERATIONS,
    )
    app = FastAPI()
    app.state.admin_request_auth = AdminRequestAuth(
        config,
        client=client,
        verifier=PictureVerifier(),
    )
    app.include_router(picture_routes.router)
    with TestClient(app) as browser:
        yield browser, state
    http.close()


def test_plain_list_uses_null_bounds_and_preserves_empty_prompt_projection(boundary):
    browser, state = boundary
    response = browser.get("/api/pictures?limit=2", headers=HEADERS)
    assert response.status_code == 200
    assert response.json() == {
        "pictures": [
            {
                "date": "2026-09-15",
                "base64": "thumbnail-original",
                "prompt": "",
                "created_at": TIME,
            },
            {
                "date": "2026-09-14",
                "base64": "full-image-fallback",
                "prompt": "",
                "created_at": None,
            },
        ]
    }
    assert state["calls"][0][:2] == (
        LIST_PICTURE_HISTORY.capability.name,
        {"start_date": None, "end_date": None, "limit": 2},
    )


def test_range_uses_same_operation_inclusive_bounds_and_retains_null_prompt(boundary):
    browser, state = boundary
    response = browser.get(
        "/api/pictures/range?start_date=2026-09-14&end_date=2026-09-15&limit=0",
        headers=HEADERS,
    )
    assert response.status_code == 200
    assert response.json()["pictures"][0]["prompt"] is None
    assert response.json()["pictures"][0]["created_at"] == TIME
    assert state["calls"][0][:2] == (
        LIST_PICTURE_HISTORY.capability.name,
        {
            "start_date": "2026-09-14",
            "end_date": "2026-09-15",
            "limit": 0,
        },
    )


def test_range_normalizes_blank_dates_to_null(boundary):
    browser, state = boundary
    response = browser.get(
        "/api/pictures/range?start_date=%20%20&end_date=&limit=30",
        headers=HEADERS,
    )
    assert response.status_code == 200
    assert state["calls"][0][1] == {
        "start_date": None,
        "end_date": None,
        "limit": 30,
    }


@pytest.mark.parametrize(
    "url",
    [
        "/api/pictures/range?start_date=2026-02-30",
        "/api/pictures/range?start_date=2026-W37-1",
        "/api/pictures/range?end_date=2026-09-15T00:00:00",
        "/api/pictures/not-a-date/full",
        "/api/pictures/2026-02-30/full",
        "/api/pictures/2026-W37-1/full",
    ],
)
def test_invalid_dates_keep_fixed_public_400_before_domain_read(boundary, url):
    browser, state = boundary
    response = browser.get(url, headers=HEADERS)
    assert response.status_code == 400
    assert response.json() == {
        "detail": "Invalid date format, expected YYYY-MM-DD"
    }
    assert state["calls"] == []


@pytest.mark.parametrize(
    "url",
    [
        "/api/pictures?limit=-1",
        "/api/pictures?limit=9007199254740992",
        "/api/pictures?limit=NaN",
        "/api/pictures/range?limit=-1",
    ],
)
def test_invalid_limit_fails_before_domain_read(boundary, url):
    browser, state = boundary
    response = browser.get(url, headers=HEADERS)
    assert response.status_code == 422
    assert state["calls"] == []


def test_full_picture_preserves_response_and_falsey_absence_404(boundary):
    browser, state = boundary
    response = browser.get("/api/pictures/2026-09-15/full", headers=HEADERS)
    assert response.status_code == 200
    assert response.json() == {"image_base64": "full-image-original"}
    assert state["calls"][0][:2] == (
        READ_PICTURE_FULL.capability.name,
        {"date": "2026-09-15"},
    )

    for value in (None, ""):
        state["outputs"]["picture-history.full"] = {"image_base64": value}
        missing = browser.get("/api/pictures/2026-09-15/full", headers=HEADERS)
        assert missing.status_code == 404
        assert missing.json() == {
            "detail": "Picture not found for this date"
        }


def test_entity_grant_token_is_rejected_before_domain_read(boundary):
    browser, state = boundary
    response = browser.get(
        "/api/pictures",
        headers={"authorization": "Bearer idg_synthetic"},
    )
    assert response.status_code == 401
    assert state["calls"] == []


@pytest.mark.parametrize(
    "headers,status",
    [
        ({}, 401),
        ({"authorization": "Bearer write-only-token"}, 403),
    ],
)
def test_missing_oauth_or_read_scope_fails_before_domain_read(
    boundary,
    headers,
    status,
):
    browser, state = boundary
    response = browser.get("/api/pictures", headers=headers)
    assert response.status_code == status
    assert state["calls"] == []


@pytest.mark.parametrize(
    "mutation",
    ["missing-schema", "schema-hash", "duplicate-schema", "operation-hash", "missing-operation"],
)
def test_exact_capability_gate_blocks_picture_domain_read(boundary, mutation):
    browser, state = boundary
    if mutation == "missing-schema":
        state["schemas"].clear()
    elif mutation == "schema-hash":
        state["schemas"][0]["contract_sha256"] = "0" * 64
    elif mutation == "duplicate-schema":
        state["schemas"].append(state["schemas"][0].copy())
    elif mutation == "operation-hash":
        state["operations"][0]["contract_sha256"] = "0" * 64
    else:
        state["operations"].pop(0)
    response = browser.get("/api/pictures", headers=HEADERS)
    assert response.status_code == 503
    assert response.json()["detail"]["outcome_unknown"] is False
    assert state["calls"] == []


@pytest.mark.parametrize(
    "operation,value,url",
    [
        (
            "picture-history.list",
            {
                "pictures": [
                    {
                        "date": "2026-09-15",
                        "base64": False,
                        "prompt": "private unexpected value",
                        "created_at": TIME,
                    }
                ]
            },
            "/api/pictures",
        ),
        (
            "picture-history.list",
            {
                "pictures": [
                    {
                        "date": "2026-09-15",
                        "base64": "image",
                        "prompt": None,
                        "created_at": "2026-09-15 03:02:01",
                    }
                ]
            },
            "/api/pictures/range",
        ),
        (
            "picture-history.full",
            {"image_base64": False},
            "/api/pictures/2026-09-15/full",
        ),
    ],
)
def test_malformed_admin_output_fails_closed_without_private_echo(
    boundary,
    operation,
    value,
    url,
):
    browser, state = boundary
    state["outputs"][operation] = value
    response = browser.get(url, headers=HEADERS)
    assert response.status_code == 503
    assert response.json()["detail"]["error_code"] == "ADMIN_RESPONSE_INVALID"
    assert response.json()["detail"]["outcome_unknown"] is False
    assert "private unexpected value" not in response.text
    assert len(state["calls"]) == 1


def test_admin_transport_failure_is_explicit_and_never_uses_database(boundary):
    browser, state = boundary
    state["outputs"]["picture-history.list"] = httpx.ReadTimeout(
        "private picture response"
    )
    response = browser.get("/api/pictures", headers=HEADERS)
    assert response.status_code == 504
    assert response.json()["detail"]["error_code"] == "ADMIN_TIMEOUT"
    assert response.json()["detail"]["outcome_unknown"] is False
    assert "private picture response" not in response.text
    assert len(state["calls"]) == 1


def test_registry103_dtos_are_closed_strict_and_use_exact_hashes():
    assert LIST_PICTURE_HISTORY.capability.contract_sha256 == (
        "d03993f15860caadba56b6788a4c1b1d0fa086e949f1831b6e805a2eabee028d"
    )
    assert READ_PICTURE_FULL.capability.contract_sha256 == (
        "e35e76d3425641660da361f2671f0004042a3600b2f3d4072386233c0d90efa3"
    )
    with pytest.raises(ValidationError):
        PictureHistoryListInputDTO(
            start_date=None,
            end_date=None,
            limit=True,
        )
    with pytest.raises(ValidationError):
        PictureHistoryListInputDTO(
            start_date=None,
            end_date=None,
            limit=-1,
        )
    with pytest.raises(ValidationError):
        PictureHistoryFullInputDTO.model_validate(
            {"date": "2026-09-15", "user_id": "42"}
        )
    with pytest.raises(ValidationError):
        PictureHistoryItemDTO(
            date="2026-09-15",
            base64="image",
            prompt=None,
            created_at="2026-09-15 03:02:01",
        )


def test_production_request_owner_registers_both_registry103_operations():
    config = AdminDataConfig(
        base_url="https://admin.example",
        issuer="https://admin.example/api/auth",
        resource="https://dream.example/api",
        service_client_id="dream-service",
        service_secret="s" * 32,
    )
    owner = AdminRequestAuth(config)
    try:
        registered = owner.client._operations
        assert registered[LIST_PICTURE_HISTORY.capability.name] is LIST_PICTURE_HISTORY
        assert registered[READ_PICTURE_FULL.capability.name] is READ_PICTURE_FULL
    finally:
        owner.close()
