# [Input] Exact Admin Editor capabilities, purpose grants, bearer HTTP and a loopback turn broker.
# [Output] Session binding, credential isolation, cache refresh and original-ID recovery evidence.
# [Pos] Provider-free Editor runtime contract; no PostgreSQL, model, CLI or normal service process.
# [Sync] 2026-09-15: validate public Editor migration and the private stdio credential boundary.
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import socket

import httpx
import pytest

import services.admin_data.editor_runtime as editor_runtime_module
from services.admin_data import AdminDataClient, AdminDataConfig, AdminDataError
from services.admin_data.delegation import (
    AdminDelegationCreator,
    DELEGATION_CAPABILITIES,
    RUNTIME_SCHEMA_REQUIREMENTS,
    RuntimeGrant,
    RuntimeHttpConfig,
)
from services.admin_data.editor_runtime import (
    AdminEditorHttpClient,
    AdminEditorRuntime,
    EditorBrokerClient,
    EditorLoadInputDTO,
    EditorLoadOutputDTO,
    EditorReplaceInputDTO,
    EditorReplaceOutputDTO,
    EDITOR_BROKER_ENV_NAMES,
    EDITOR_RUNTIME_CAPABILITIES,
)
from services.admin_data.models import AbsentReceiptDTO, CommittedReceiptDTO
from services.admin_data.workflow_data import AdminWorkflowResolution

NOW = datetime(2026, 9, 15, tzinfo=timezone.utc)
TOKEN = "idg_" + "a" * 43
TIMESTAMP = "2026-09-15T00:00:00.123456Z"


def state(session_id: str, text: str = "original") -> dict:
    return {
        "id": session_id,
        "cells": [{"id": "cell-1", "type": "text", "content": text}],
        "commentors": [],
        "tasks": [],
        "weightPath": [],
        "overlappedPhrases": [],
        "notFoundPhrases": [],
    }


def grant(session_id: str, token_letter: str = "a") -> RuntimeGrant:
    return RuntimeGrant(
        "idg_" + token_letter * 43,
        "editor-stdio",
        "thread-1",
        None,
        session_id,
        ("editor:read", "editor:write"),
        NOW + timedelta(hours=2),
        NOW + timedelta(hours=4),
    )


def envelope(request: httpx.Request, value: dict) -> httpx.Response:
    return httpx.Response(
        200,
        json={"data": value, "request_id": request.headers["x-request-id"]},
    )


def capabilities(config: AdminDataConfig, operations=EDITOR_RUNTIME_CAPABILITIES) -> dict:
    return {
        "version": "1",
        "auth": {
            "issuer": config.issuer,
            "jwks_uri": config.jwks_uri,
            "algorithm": "ES256",
            "resource": config.resource,
            "clients": {"browser": "browser", "device": "device"},
            "scopes": ["dream:read", "dream:write"],
            "delegations": [item.model_dump() for item in DELEGATION_CAPABILITIES],
        },
        "schema_capabilities": [item.model_dump() for item in RUNTIME_SCHEMA_REQUIREMENTS],
        "operations": [item.model_dump() for item in operations],
    }


@pytest.fixture
def config() -> AdminDataConfig:
    return AdminDataConfig(
        base_url="https://admin.example",
        issuer="https://admin.example/api/auth",
        resource="https://dream.example/api",
        service_secret="s" * 32,
        service_client_id="dream-server",
    )


def test_editor_grant_requires_both_exact_published_operations(config):
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if request.url.path.endswith("/capabilities"):
            return envelope(request, capabilities(config))
        assert request.url.path == "/api/internal/dream/v1/runtime-delegations"
        body = json.loads(request.content)
        return envelope(
            request,
            {
                **body["input"],
                "token": TOKEN,
                "expires_at": (NOW + timedelta(hours=2)).isoformat(),
                "maximum_expires_at": (NOW + timedelta(hours=4)).isoformat(),
            },
        )

    client = AdminDataClient(
        config,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    creator = AdminDelegationCreator(client, clock=lambda: NOW)
    runtime = AdminEditorRuntime(
        AdminWorkflowResolution("42", "thread-1", None),
        actor_id="42",
        access_token="user-oauth",
        delegation_creator=creator,
        runtime_http_config=RuntimeHttpConfig.from_server_config(config),
        initial_session_id="session-1",
        initial_request_id="grant-1",
    )
    assert len(calls) == 2
    body = json.loads(calls[-1].content)
    assert body["input"] == {
        "purpose": "editor-stdio",
        "thread_id": "thread-1",
        "run_id": None,
        "editor_session_id": "session-1",
        "scopes": ["editor:read", "editor:write"],
    }
    assert calls[-1].headers["authorization"] == "Bearer user-oauth"
    runtime.close()

    broken = list(EDITOR_RUNTIME_CAPABILITIES)
    broken[0] = broken[0].model_copy(update={"contract_sha256": "b" * 64})
    calls.clear()
    bad_client = AdminDataClient(
        config,
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: (
                    calls.append(request)
                    or envelope(request, capabilities(config, tuple(broken)))
                )
            )
        ),
    )
    with pytest.raises(AdminDataError) as error:
        AdminEditorRuntime(
            AdminWorkflowResolution("42", "thread-1", None),
            actor_id="42",
            access_token="user-oauth",
            delegation_creator=AdminDelegationCreator(bad_client, clock=lambda: NOW),
            runtime_http_config=RuntimeHttpConfig.from_server_config(config),
            initial_session_id="session-1",
            initial_request_id="grant-2",
        )
    assert error.value.code == "ADMIN_CAPABILITY_UNAVAILABLE" and len(calls) == 1


def test_public_editor_client_uses_only_exact_bearer_paths_and_closed_dtos():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.headers["authorization"] == "Bearer " + TOKEN
        assert not any(
            name in request.headers
            for name in (
                "cookie",
                "x-api-key",
                "x-ink-dream-service",
                "x-ink-dream-credential",
            )
        )
        if request.url.path.endswith("editor-state.load"):
            assert json.loads(request.content) == {
                "request_id": "load-1",
                "input": {"session_id": "session-1"},
            }
            return envelope(
                request,
                {
                    "session_id": "session-1",
                    "editor_state": state("session-1"),
                    "updated_at": TIMESTAMP,
                },
            )
        if request.url.path.endswith("editor-state.replace"):
            assert json.loads(request.content)["input"]["editor_state"]["cells"][0]["content"] == "changed"
            return envelope(
                request,
                {"saved": True, "session_id": "session-1", "updated_at": TIMESTAMP},
            )
        assert request.url.path == "/api/dream/v1/editor/receipts/write-1"
        assert dict(request.url.params) == {"operation": "editor-state.replace"}
        return envelope(
            request,
            {
                "status": "committed",
                "operation": "editor-state.replace",
                "request_id": "write-1",
                "result": {"saved": True, "session_id": "session-1", "updated_at": TIMESTAMP},
            },
        )

    http = httpx.Client(
        transport=httpx.MockTransport(handler),
        headers={"x-api-key": "ambient"},
        cookies={"admin-session": "ambient"},
        auth=("ambient", "password"),
    )
    client = AdminEditorHttpClient(
        RuntimeHttpConfig("https://admin.example"),
        client=http,
    )
    bound = grant("session-1")
    assert client.load(bound, EditorLoadInputDTO(session_id="session-1"), "load-1").editor_state is not None
    changed = EditorReplaceInputDTO(
        session_id="session-1",
        editor_state=state("session-1", "changed"),
    )
    assert client.replace(bound, changed, "write-1").saved
    assert isinstance(client.receipt(bound, "write-1"), CommittedReceiptDTO)
    assert [request.url.path for request in requests] == [
        "/api/dream/v1/editor/operations/editor-state.load",
        "/api/dream/v1/editor/operations/editor-state.replace",
        "/api/dream/v1/editor/receipts/write-1",
    ]

    wrong = grant("session-2", "b")
    with pytest.raises(AdminDataError) as error:
        client.load(wrong, EditorLoadInputDTO(session_id="session-1"), "load-2")
    assert error.value.code == "ADMIN_CONFIGURATION_INVALID" and len(requests) == 3


@pytest.mark.parametrize("value", [
    {
        "session_id": "other-session",
        "editor_state": None,
        "updated_at": None,
    },
    {
        "session_id": "session-1",
        "editor_state": state("other-session"),
        "updated_at": TIMESTAMP,
    },
    {
        "session_id": "session-1",
        "editor_state": state("session-1"),
        "updated_at": None,
    },
    {
        "session_id": "session-1",
        "editor_state": state("session-1"),
        "updated_at": TIMESTAMP,
        "database_row": "must stay private",
    },
])
def test_public_editor_client_rejects_foreign_or_corrupt_load_results(value):
    client = AdminEditorHttpClient(
        RuntimeHttpConfig("https://admin.example"),
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: envelope(request, value)
            )
        ),
    )
    with pytest.raises(AdminDataError) as error:
        client.load(
            grant("session-1"),
            EditorLoadInputDTO(session_id="session-1"),
            "load-corrupt",
        )
    assert error.value.code == "ADMIN_RESPONSE_INVALID"


class _Creator:
    def __init__(self, *, fail_once: bool = False):
        self.calls: list[tuple] = []
        self.fail_once = fail_once

    def create(self, requested, *, access_token, request_id, required_operations):
        self.calls.append((requested, access_token, request_id, required_operations))
        if self.fail_once:
            self.fail_once = False
            raise AdminDataError("ENTITY_NOT_FOUND", 404, request_id)
        letter = chr(ord("a") + len(self.calls) - 1)
        return grant(requested.editor_session_id, letter)


class _RuntimeClient:
    def __init__(self):
        self.closed = False

    def renew(self, _grant, _request_id):
        raise AssertionError("Long-lived fixture grant must not renew")

    def close(self):
        self.closed = True


class _EditorClient:
    def __init__(self, states: dict[str, dict], *, unknown_once: bool = False):
        self.states = deepcopy(states)
        self.unknown_once = unknown_once
        self.load_error_sessions: set[str] = set()
        self.replace_calls: list[tuple[EditorReplaceInputDTO, str]] = []
        self.load_calls: list[str] = []
        self.receipt_calls: list[str] = []
        self.receipts: list[AbsentReceiptDTO | CommittedReceiptDTO] = []
        self.closed = False

    def load(self, _grant, input_dto, _request_id):
        self.load_calls.append(input_dto.session_id)
        if input_dto.session_id in self.load_error_sessions:
            raise AdminDataError("ENTITY_NOT_FOUND", 404, _request_id)
        value = self.states.get(input_dto.session_id)
        return EditorLoadOutputDTO(
            session_id=input_dto.session_id,
            editor_state=value,
            updated_at=TIMESTAMP if value is not None else None,
        )

    def replace(self, _grant, input_dto, request_id):
        self.replace_calls.append((input_dto, request_id))
        if self.unknown_once:
            self.unknown_once = False
            raise AdminDataError("ADMIN_TIMEOUT", 504, request_id, True)
        self.states[input_dto.session_id] = input_dto.editor_state.model_dump(
            mode="python", exclude_unset=True
        )
        return EditorReplaceOutputDTO(
            saved=True,
            session_id=input_dto.session_id,
            updated_at=TIMESTAMP,
        )

    def receipt(self, _grant, request_id):
        self.receipt_calls.append(request_id)
        return self.receipts.pop(0)

    def close(self):
        self.closed = True


def runtime_fixture(*, creator=None, editor=None, initial_session_id=None):
    creator = creator or _Creator()
    runtime_client = _RuntimeClient()
    editor = editor or _EditorClient({"session-1": state("session-1")})
    owner = AdminEditorRuntime(
        AdminWorkflowResolution("42", "thread-1", None),
        actor_id="42",
        access_token="user-oauth",
        delegation_creator=creator,
        runtime_http_config=RuntimeHttpConfig(
            "https://admin.example", timeout_seconds=1, max_response_bytes=1_048_576
        ),
        clock=lambda: NOW,
        request_id_factory=iter(("grant-a", "grant-b", "grant-c")).__next__,
        runtime_client_factory=lambda: runtime_client,
        editor_client_factory=lambda: editor,
        initial_session_id=initial_session_id,
    )
    return owner, creator, runtime_client, editor


def test_loopback_broker_switches_exact_grants_refreshes_cache_and_closes():
    owner, creator, runtime_client, editor = runtime_fixture()
    owner.start()
    env = owner.child_env()
    assert set(env) == set(EDITOR_BROKER_ENV_NAMES)
    assert not any(
        marker in env
        for marker in (
            "DATABASE_URL",
            "INK_AGENT_USER_ID",
            "ADMIN_DATA_SERVICE_SECRET",
            "ADMIN_OAUTH_ACCESS_TOKEN",
        )
    )
    client = EditorBrokerClient.from_env(env)
    assert client.load("session-1")["cells"][0]["content"] == "original"
    client.replace("session-1", state("session-1", "changed"))
    assert owner.cached_state("session-1")["cells"][0]["content"] == "changed"
    editor.states["session-2"] = state("session-2", "second")
    assert client.load("session-2")["cells"][0]["content"] == "second"
    assert [call[0].editor_session_id for call in creator.calls] == [
        "session-1",
        "session-2",
    ]
    assert all(call[1] == "user-oauth" and call[3] == EDITOR_RUNTIME_CAPABILITIES for call in creator.calls)

    editor.load_error_sessions.add("session-2")
    with pytest.raises(AdminDataError) as error:
        client.load("session-2")
    assert error.value.code == "ENTITY_NOT_FOUND"
    assert owner.cached_state("session-2") is None

    denied = EditorBrokerClient(
        env["INK_EDITOR_BROKER_HOST"],
        int(env["INK_EDITOR_BROKER_PORT"]),
        "z" * 43,
        timeout_seconds=1,
        max_response_bytes=1_048_576,
    )
    with pytest.raises(AdminDataError) as error:
        denied.load("session-1")
    assert error.value.code == "EDITOR_BROKER_DENIED"

    owner.close()
    assert runtime_client.closed and editor.closed
    with pytest.raises(AdminDataError) as error:
        client.load("session-1")
    assert error.value.code == "ADMIN_UNAVAILABLE"


def test_start_failure_closes_the_failing_keeper_and_owned_clients(monkeypatch):
    keepers = []

    class FailingKeeper:
        def __init__(self, *_args, **_kwargs):
            self.closed = False
            keepers.append(self)

        def start(self):
            raise RuntimeError("fixture start failure")

        def close(self):
            self.closed = True

    monkeypatch.setattr(editor_runtime_module, "RuntimeGrantKeeper", FailingKeeper)
    owner, _, runtime_client, editor = runtime_fixture(initial_session_id="session-1")
    with pytest.raises(RuntimeError, match="fixture start failure"):
        owner.start()
    assert len(keepers) == 1 and keepers[0].closed
    assert runtime_client.closed and editor.closed
    with pytest.raises(AdminDataError) as error:
        owner.child_env()
    assert error.value.code == "EDITOR_RUNTIME_UNAVAILABLE"
    owner.close()


def test_new_session_keeper_failure_is_closed_and_does_not_bind_session(monkeypatch):
    keepers = []

    class FailingKeeper:
        def __init__(self, *_args, **_kwargs):
            self.closed = False
            keepers.append(self)

        def start(self):
            raise RuntimeError("fixture new-session keeper failure")

        def close(self):
            self.closed = True

    owner, creator, _, _ = runtime_fixture()
    owner.start()
    monkeypatch.setattr(editor_runtime_module, "RuntimeGrantKeeper", FailingKeeper)
    client = EditorBrokerClient.from_env(owner.child_env())
    with pytest.raises(AdminDataError) as error:
        client.load("session-2")
    assert error.value.code == "EDITOR_RUNTIME_UNAVAILABLE"
    assert len(keepers) == 1 and keepers[0].closed
    assert "session-2" not in owner._sessions
    assert creator.calls[0][0].editor_session_id == "session-2"
    owner.close()


def test_unknown_replace_reuses_original_id_and_checks_receipt_without_resend():
    editor = _EditorClient(
        {"session-1": state("session-1")},
        unknown_once=True,
    )
    owner, _, _, _ = runtime_fixture(editor=editor)
    owner.start()
    client = EditorBrokerClient.from_env(owner.child_env())
    changed = state("session-1", "changed after uncertain response")
    with pytest.raises(AdminDataError) as error:
        client.replace("session-1", changed)
    assert error.value.outcome_unknown
    original_id = editor.replace_calls[0][1]
    editor.receipts = [
        AbsentReceiptDTO(
            status="absent",
            operation="editor-state.replace",
            request_id=original_id,
        ),
        CommittedReceiptDTO[EditorReplaceOutputDTO](
            status="committed",
            operation="editor-state.replace",
            request_id=original_id,
            result=EditorReplaceOutputDTO(
                saved=True,
                session_id="session-1",
                updated_at=TIMESTAMP,
            ),
        ),
    ]
    with pytest.raises(AdminDataError) as error:
        client.replace("session-1", changed)
    assert error.value.outcome_unknown and error.value.request_id == original_id
    client.replace("session-1", changed)
    assert len(editor.replace_calls) == 1
    assert editor.receipt_calls == [original_id, original_id]
    assert owner.cached_state("session-1")["cells"][0]["content"] == "changed after uncertain response"
    owner.close()


def test_next_load_recovers_an_unknown_replace_before_reading_new_state():
    editor = _EditorClient(
        {"session-1": state("session-1")},
        unknown_once=True,
    )
    owner, _, _, _ = runtime_fixture(editor=editor)
    owner.start()
    client = EditorBrokerClient.from_env(owner.child_env())
    changed = state("session-1", "committed while response was lost")
    with pytest.raises(AdminDataError):
        client.replace("session-1", changed)
    original_id = editor.replace_calls[0][1]
    editor.states["session-1"] = deepcopy(changed)
    editor.receipts = [
        CommittedReceiptDTO[EditorReplaceOutputDTO](
            status="committed",
            operation="editor-state.replace",
            request_id=original_id,
            result=EditorReplaceOutputDTO(
                saved=True,
                session_id="session-1",
                updated_at=TIMESTAMP,
            ),
        )
    ]
    assert client.load("session-1")["cells"][0]["content"] == "committed while response was lost"
    assert editor.receipt_calls == [original_id]
    assert editor.load_calls == ["session-1"]
    assert len(editor.replace_calls) == 1
    owner.close()


def test_grant_failure_before_post_does_not_create_unknown_write_barrier():
    creator = _Creator(fail_once=True)
    editor = _EditorClient({"session-1": state("session-1")})
    owner, _, _, _ = runtime_fixture(creator=creator, editor=editor)
    owner.start()
    changed = EditorReplaceInputDTO(
        session_id="session-1",
        editor_state=state("session-1", "changed"),
    )
    with pytest.raises(AdminDataError) as error:
        owner.replace(changed, "write-before-grant")
    assert error.value.code == "ENTITY_NOT_FOUND"
    assert owner._pending is None and not editor.replace_calls
    owner.replace(changed, "write-after-grant")
    assert [item[1] for item in editor.replace_calls] == ["write-after-grant"]
    owner.close()


def test_broker_rejects_malformed_payload_without_calling_editor():
    owner, creator, _, editor = runtime_fixture()
    owner.start()
    env = owner.child_env()
    with socket.create_connection(
        (env["INK_EDITOR_BROKER_HOST"], int(env["INK_EDITOR_BROKER_PORT"])),
        timeout=1,
    ) as connection:
        connection.sendall(b'{"operation":"editor-state.load","input":{}}\n')
        response = json.loads(connection.makefile("rb").readline())
    assert response == {
        "ok": False,
        "error": {
            "code": "EDITOR_BROKER_INPUT_INVALID",
            "status_code": 400,
            "outcome_unknown": False,
        },
    }
    assert not creator.calls and not editor.replace_calls
    owner.close()
