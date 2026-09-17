# [Input] Explicit broker settings, strict projections and synthetic loopback peers/providers.
# [Output] Capability, framing, timeout, close and in-flight drain contract evidence.
# [Pos] Provider-free Session projection transport tests; no PG, Admin service or model.
# [Sync] 2026-09-15: cover the private Chat Session broker boundary.
# [Sync] 2026-09-16: cover the selector-free current WorkflowRun projection on the same capability.
from __future__ import annotations

import json
import socket
import socketserver
from datetime import datetime, timezone
from threading import Event, Thread

import pytest

from models.workflow_run import RunStatus, WorkflowRun

from libs.claude_agent_kit.server.session_projection_protocol import (
    SESSION_BROKER_CAPABILITY_ENV,
    SESSION_BROKER_HOST,
    SESSION_BROKER_HOST_ENV,
    SESSION_BROKER_MAX_BYTES_ENV,
    SESSION_BROKER_PORT_ENV,
    SESSION_BROKER_TIMEOUT_ENV,
    SessionProjectionBrokerClient,
    SessionProjectionProtocolError,
)
from services.admin_data.session_models import SessionListResultDTO
from services.admin_data.session_projection_broker import (
    SessionProjectionBroker,
    SessionProjectionBrokerSettings,
)


def _result(*, include_text: bool = False, size: int = 1) -> SessionListResultDTO:
    return SessionListResultDTO.model_validate(
        {
            "sessions": [
                {
                    "id": f"session-{index}",
                    "name": "标题",
                    "labels": ["成长"],
                    "created_at": "2026-09-14T08:00:00Z",
                    "updated_at": "2026-09-15T09:00:00Z",
                    "first_line": "第一行" * size,
                    "text": "完整正文" if include_text else None,
                }
                for index in range(1)
            ]
        },
        strict=True,
    )


class _Provider:
    def __init__(self, *, block: tuple[Event, Event] | None = None, size: int = 1):
        self.calls = []
        self.block = block
        self.size = size

    def list_sessions(self, input_dto, request_id):
        self.calls.append((input_dto, request_id))
        if self.block is not None:
            entered, release = self.block
            entered.set()
            assert release.wait(2)
        return _result(include_text=input_dto.include_text, size=self.size)


def _run(**overrides) -> WorkflowRun:
    values = {
        "workflow_run_id": "run_" + "a" * 32,
        "deck_plugin_id": "plugin-1",
        "deck_plugin_version": "1.0.0",
        "workflow_definition_ref": "workflow-1",
        "deck_runtime_snapshot_id": "snapshot-1",
        "status": RunStatus.PREFLIGHT,
        "deck_plugin_manifest_hash": "sha256:" + "1" * 64,
        "deck_plugin_binding_id": "binding-1",
        "binding_revision": 1,
        "runtime_plugin_lock_id": "lock-1",
        "workflow_preflight_id": "pf_" + "2" * 32,
        "source_voice_thread_id": "thread-1",
        "workspace_id": "workspace-1",
        "idempotency_key": "run-request-1",
        "input_hash": "sha256:" + "3" * 64,
        "semantic_fingerprint": "sha256:" + "4" * 64,
        "status_version": 1,
        "created_by": "42",
        "created_at": datetime(2026, 9, 16, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return WorkflowRun.model_validate(values)


class _RunProvider:
    def __init__(self, run: WorkflowRun | None = None):
        self.run = run or _run()
        self.calls: list[str] = []

    def current_workflow_run(self, request_id: str) -> WorkflowRun:
        self.calls.append(request_id)
        return self.run


def _started(
    *,
    timeout: float = 0.5,
    max_bytes: int = 4096,
    provider=None,
    run_provider=None,
):
    provider = provider or _Provider()
    broker = SessionProjectionBroker(
        provider,
        settings=SessionProjectionBrokerSettings(
            timeout_seconds=timeout, max_bytes=max_bytes
        ),
        workflow_run_provider=run_provider,
    )
    broker.start()
    return broker, provider


def _client(env: dict[str, str]) -> SessionProjectionBrokerClient:
    return SessionProjectionBrokerClient.from_env(env)


def test_child_env_is_exact_loopback_tuple_with_256_bit_capability():
    broker, _provider = _started()
    try:
        env = broker.child_env()
        assert set(env) == {
            SESSION_BROKER_HOST_ENV,
            SESSION_BROKER_PORT_ENV,
            SESSION_BROKER_CAPABILITY_ENV,
            SESSION_BROKER_TIMEOUT_ENV,
            SESSION_BROKER_MAX_BYTES_ENV,
        }
        assert env[SESSION_BROKER_HOST_ENV] == SESSION_BROKER_HOST
        assert len(env[SESSION_BROKER_CAPABILITY_ENV]) == 43
        assert _client(env).list_sessions(
            start_date="2026-09-01", end_date="2026-09-15", include_text=False
        ).sessions[0].text is None
        assert _client(env).list_sessions(
            start_date="2026-09-01", end_date="2026-09-15", include_text=True
        ).sessions[0].text == "完整正文"
    finally:
        broker.close()


def test_current_workflow_run_uses_same_capability_without_entity_selector():
    run_provider = _RunProvider()
    broker, _provider = _started(run_provider=run_provider)
    try:
        result = _client(broker.child_env()).current_workflow_run(
            request_id="run-projection"
        )
        assert result == run_provider.run
        assert run_provider.calls == ["run-projection"]
    finally:
        broker.close()


def test_current_workflow_run_is_denied_when_owner_has_no_run_provider():
    broker, _provider = _started()
    try:
        with pytest.raises(
            SessionProjectionProtocolError,
            match="STORY_WORKSPACE_PROJECTION_DENIED",
        ):
            _client(broker.child_env()).current_workflow_run(
                request_id="ordinary-turn"
            )
    finally:
        broker.close()


def test_current_workflow_run_rejects_wrong_capability():
    run_provider = _RunProvider()
    broker, _provider = _started(run_provider=run_provider)
    try:
        env = broker.child_env()
        env[SESSION_BROKER_CAPABILITY_ENV] = "b" * 43
        with pytest.raises(
            SessionProjectionProtocolError,
            match="SESSION_BROKER_DENIED",
        ):
            _client(env).current_workflow_run(request_id="wrong-capability")
        assert run_provider.calls == []
    finally:
        broker.close()


@pytest.mark.parametrize(
    "forbidden",
    [
        {"actor_id": "42"},
        {"thread_id": "thread-1"},
        {"workspace_id": "workspace-1"},
        {"workflow_run_id": "run_" + "a" * 32},
        {"sql": "select 1"},
        {"admin_bearer": "secret"},
    ],
)
def test_current_run_request_rejects_identity_entity_sql_and_credentials(forbidden):
    run_provider = _RunProvider()
    broker, _provider = _started(run_provider=run_provider)
    try:
        env = broker.child_env()
        payload = {
            "capability": env[SESSION_BROKER_CAPABILITY_ENV],
            "request_id": "forbidden-run-field",
            "operation": "workflow-run.current",
            **forbidden,
        }
        with socket.create_connection(
            (env[SESSION_BROKER_HOST_ENV], int(env[SESSION_BROKER_PORT_ENV])),
            timeout=0.5,
        ) as connection:
            connection.sendall(json.dumps(payload).encode("utf-8") + b"\n")
            response = connection.makefile("rb").readline(4097)
        body = json.loads(response)
        assert body["error"]["code"] == "SESSION_BROKER_INPUT_INVALID"
        assert run_provider.calls == []
    finally:
        broker.close()


@pytest.mark.parametrize("mode", ["missing", "wrong"])
def test_missing_or_wrong_capability_is_denied(mode):
    broker, _provider = _started()
    try:
        env = broker.child_env()
        env[SESSION_BROKER_CAPABILITY_ENV] = "b" * 43 if mode == "wrong" else ""
        expected = (
            "SESSION_BROKER_DENIED"
            if mode == "wrong"
            else "SESSION_BROKER_CONFIGURATION_INVALID"
        )
        with pytest.raises(SessionProjectionProtocolError, match=expected):
            _client(env).list_sessions(
                start_date="2026-09-01",
                end_date="2026-09-15",
                include_text=False,
            )
    finally:
        broker.close()


@pytest.mark.parametrize(
    "payload",
    [b"not-json\n", b'{"capability":"bad"}\n', b"x" * 257],
)
def test_malformed_or_oversized_request_is_rejected(payload):
    broker, provider = _started(max_bytes=256)
    try:
        env = broker.child_env()
        with socket.create_connection(
            (env[SESSION_BROKER_HOST_ENV], int(env[SESSION_BROKER_PORT_ENV])),
            timeout=0.5,
        ) as connection:
            connection.sendall(payload)
            response = connection.makefile("rb").readline(257)
        body = json.loads(response)
        assert body["ok"] is False
        assert body["error"]["code"] == "SESSION_BROKER_INPUT_INVALID"
        assert provider.calls == []
    finally:
        broker.close()


@pytest.mark.parametrize(
    "forbidden",
    [
        {"actor_id": "42"},
        {"thread_id": "thread-1"},
        {"task_id": "task-1"},
        {"sql": "select 1"},
        {"admin_bearer": "secret"},
    ],
)
def test_request_rejects_identity_task_sql_and_admin_credential_fields(forbidden):
    broker, provider = _started()
    try:
        env = broker.child_env()
        payload = {
            "capability": env[SESSION_BROKER_CAPABILITY_ENV],
            "request_id": "forbidden-field",
            "start_date": "2026-09-01",
            "end_date": "2026-09-15",
            "include_text": False,
            **forbidden,
        }
        with socket.create_connection(
            (env[SESSION_BROKER_HOST_ENV], int(env[SESSION_BROKER_PORT_ENV])),
            timeout=0.5,
        ) as connection:
            connection.sendall(json.dumps(payload).encode("utf-8") + b"\n")
            response = connection.makefile("rb").readline(4097)
        body = json.loads(response)
        assert body["error"]["code"] == "SESSION_BROKER_INPUT_INVALID"
        assert provider.calls == []
    finally:
        broker.close()


def test_oversized_provider_response_fails_without_partial_projection():
    broker, _provider = _started(max_bytes=256, provider=_Provider(size=200))
    try:
        with pytest.raises(
            SessionProjectionProtocolError, match="SESSION_BROKER_RESPONSE_TOO_LARGE"
        ):
            _client(broker.child_env()).list_sessions(
                start_date="2026-09-01",
                end_date="2026-09-15",
                include_text=False,
            )
    finally:
        broker.close()


def test_client_rejects_malformed_and_oversized_responses():
    class Peer(socketserver.ThreadingTCPServer):
        allow_reuse_address = False

    class Handler(socketserver.StreamRequestHandler):
        def handle(self):
            self.rfile.readline()
            self.wfile.write(self.server.payload)

    for payload in (b"not-json\n", b"x" * 257):
        server = Peer((SESSION_BROKER_HOST, 0), Handler)
        server.payload = payload
        worker = Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            client = SessionProjectionBrokerClient(
                SESSION_BROKER_HOST,
                server.server_address[1],
                "a" * 43,
                timeout_seconds=0.5,
                max_response_bytes=256,
            )
            with pytest.raises(
                SessionProjectionProtocolError, match="SESSION_BROKER_RESPONSE_INVALID"
            ):
                client.list_sessions(
                    start_date="2026-09-01",
                    end_date="2026-09-15",
                    include_text=False,
                )
        finally:
            server.shutdown()
            server.server_close()
            worker.join(1)


def test_timeout_and_closed_broker_fail_explicitly():
    entered, release = Event(), Event()
    broker, _provider = _started(
        timeout=0.05, provider=_Provider(block=(entered, release))
    )
    env = broker.child_env()
    try:
        with pytest.raises(
            SessionProjectionProtocolError, match="SESSION_BROKER_UNAVAILABLE"
        ):
            _client(env).list_sessions(
                start_date="2026-09-01",
                end_date="2026-09-15",
                include_text=False,
            )
        assert entered.wait(1)
    finally:
        release.set()
        broker.close()
    with pytest.raises(SessionProjectionProtocolError, match="SESSION_BROKER_UNAVAILABLE"):
        _client(env).list_sessions(
            start_date="2026-09-01", end_date="2026-09-15", include_text=False
        )


def test_close_stops_acceptance_and_drains_in_flight_provider_call():
    entered, release, client_done, close_done = Event(), Event(), Event(), Event()
    broker, _provider = _started(provider=_Provider(block=(entered, release)))
    env = broker.child_env()
    errors = []

    def request():
        try:
            _client(env).list_sessions(
                start_date="2026-09-01",
                end_date="2026-09-15",
                include_text=False,
            )
        except Exception as error:
            errors.append(error)
        finally:
            client_done.set()

    requester = Thread(target=request)
    closer = Thread(target=lambda: (broker.close(), close_done.set()))
    requester.start()
    try:
        assert entered.wait(1)
        closer.start()
        assert not close_done.wait(0.05)
    finally:
        release.set()
        requester.join(2)
        closer.join(2)
    assert client_done.is_set() and close_done.is_set() and errors == []
    with pytest.raises(Exception):
        broker.child_env()
