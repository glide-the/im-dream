# [Input] OAuth-owned delegation creator, public Editor bearer routes and a private turn-local stdio bridge.
# [Output] Exact Editor load/replace consumers and a bounded broker that never projects OAuth, service or DB credentials.
# [Pos] Public Chat Editor runtime owner; Admin remains the only identity, ownership and persistence authority.
# [Sync] 2026-09-15: migrate Editor stdio persistence to exact Admin operations with original-ID recovery.
"""Turn-owned Editor transport between the stdio MCP child and Admin."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import hmac
import json
import math
import secrets
import socket
import socketserver
import threading
from typing import Annotated, Callable, Literal
from uuid import uuid4

import httpx
from pydantic import Field, TypeAdapter, ValidationError, field_validator, model_validator

from .client import AdminDataClient
from .delegation import (
    AdminDelegationCreator,
    AdminRuntimeClient,
    DelegationCreateInputDTO,
    DelegationToken,
    RuntimeGrant,
    RuntimeHttpConfig,
)
from .delegation_keeper import RuntimeGrantKeeper, RuntimeRenewalSettings
from .editor_models import EditorStateDTO
from .chat_models import validate_timestamp_text
from .errors import AdminDataError, configuration_invalid, invalid_response, unavailable
from .http_transport import request_admin_dto
from .models import (
    AbsentReceiptDTO,
    CommittedReceiptDTO,
    Identifier,
    OperationCapabilityDTO,
    RequestDTO,
    StrictDTO,
)
from .workflow_data import AdminWorkflowResolution

EDITOR_LOAD = OperationCapabilityDTO(
    name="editor-state.load",
    kind="read",
    user_scope="editor:read",
    background_scope=None,
    input_schema_version=1,
    output_schema_version=1,
    contract_sha256="1555a622d0030dc2242ee86825fd949f4ea8b0fbe77e28528b19c72804c40335",
)
EDITOR_REPLACE = OperationCapabilityDTO(
    name="editor-state.replace",
    kind="write",
    user_scope="editor:write",
    background_scope=None,
    input_schema_version=1,
    output_schema_version=1,
    contract_sha256="bb37ffff488c49a6e8b69f58a16eb1a4eb454f1d6f014a1b91832c001811a4f6",
)
EDITOR_RUNTIME_CAPABILITIES = (EDITOR_LOAD, EDITOR_REPLACE)

EDITOR_BROKER_HOST_ENV = "INK_EDITOR_BROKER_HOST"
EDITOR_BROKER_PORT_ENV = "INK_EDITOR_BROKER_PORT"
EDITOR_BROKER_CAPABILITY_ENV = "INK_EDITOR_BROKER_CAPABILITY"
EDITOR_BROKER_TIMEOUT_ENV = "INK_EDITOR_BROKER_TIMEOUT_SECONDS"
EDITOR_BROKER_MAX_BYTES_ENV = "INK_EDITOR_BROKER_MAX_BYTES"
EDITOR_BROKER_ENV_NAMES = (
    EDITOR_BROKER_HOST_ENV,
    EDITOR_BROKER_PORT_ENV,
    EDITOR_BROKER_CAPABILITY_ENV,
    EDITOR_BROKER_TIMEOUT_ENV,
    EDITOR_BROKER_MAX_BYTES_ENV,
)
_LOOPBACK_HOST = "127.0.0.1"
_BROKER_CAPABILITY = Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{43}$")]


class EditorLoadInputDTO(StrictDTO):
    session_id: Annotated[str, Field(min_length=1)]


class EditorLoadOutputDTO(StrictDTO):
    session_id: Annotated[str, Field(min_length=1)]
    editor_state: EditorStateDTO | None
    updated_at: str | None

    @field_validator("updated_at")
    @classmethod
    def validate_updated_at(cls, value: str | None) -> str | None:
        if value is not None:
            from .chat_models import validate_timestamp_text

            validate_timestamp_text(value)
        return value

    @model_validator(mode="after")
    def validate_state_identity(self):
        if self.editor_state is not None and self.editor_state.id != self.session_id:
            raise ValueError("Editor state ID does not match Session")
        if (self.editor_state is None) != (self.updated_at is None):
            raise ValueError("Editor missing state and timestamp must agree")
        return self


class EditorReplaceInputDTO(EditorLoadInputDTO):
    editor_state: EditorStateDTO

    @model_validator(mode="after")
    def validate_state_identity(self):
        if self.editor_state.id != self.session_id:
            raise ValueError("Editor state ID does not match Session")
        return self


class EditorReplaceOutputDTO(StrictDTO):
    saved: Literal[True]
    session_id: Annotated[str, Field(min_length=1)]
    updated_at: str

    _timestamp = field_validator("updated_at")(validate_timestamp_text)


class _EditorRequestDTO(RequestDTO):
    input: EditorLoadInputDTO | EditorReplaceInputDTO


class _BrokerRequestDTO(StrictDTO):
    capability: _BROKER_CAPABILITY = Field(repr=False)
    operation: Literal["editor-state.load", "editor-state.replace"]
    request_id: Identifier
    input: EditorLoadInputDTO | EditorReplaceInputDTO

    @model_validator(mode="after")
    def validate_operation_input(self):
        expected = EditorLoadInputDTO if self.operation == "editor-state.load" else EditorReplaceInputDTO
        if type(self.input) is not expected:
            raise ValueError("Editor broker operation/input mismatch")
        return self


class _BrokerErrorDTO(StrictDTO):
    code: str
    status_code: int
    request_id: str | None
    outcome_unknown: bool


class _BrokerResponseDTO(StrictDTO):
    ok: bool
    result: EditorLoadOutputDTO | EditorReplaceOutputDTO | None = None
    error: _BrokerErrorDTO | None = None

    @model_validator(mode="after")
    def validate_shape(self):
        if self.ok == (self.result is None) or self.ok == (self.error is not None):
            raise ValueError("Editor broker response shape is invalid")
        return self


class AdminEditorHttpClient:
    """Bearer-only public Editor client; it has no service or OAuth credential."""

    def __init__(self, config: RuntimeHttpConfig, *, client: httpx.Client | None = None):
        self._config = config
        self._owns_client = client is None
        self._http = client or httpx.Client(
            timeout=config.timeout_seconds,
            follow_redirects=False,
            trust_env=False,
        )

    def close(self) -> None:
        if self._owns_client:
            self._http.close()

    @staticmethod
    def _grant(grant: RuntimeGrant, session_id: str) -> None:
        if (
            grant.purpose != "editor-stdio"
            or grant.editor_session_id != session_id
            or grant.run_id is not None
            or frozenset(grant.scopes) != frozenset({"editor:read", "editor:write"})
        ):
            raise configuration_invalid()

    def _request(self, method: Literal["GET", "POST"], path: str, grant: RuntimeGrant,
        request_id: str, output_type, *, body: RequestDTO | None = None,
        params: dict[str, str] | None = None, write: bool = False):
        TypeAdapter(DelegationToken).validate_python(grant.token)
        return request_admin_dto(
            self._http,
            method=method,
            url=self._config.base_url + path,
            request_id=request_id,
            output_type=output_type,
            headers={
                "accept": "application/json",
                "x-request-id": request_id,
                "authorization": "Bearer " + grant.token,
            },
            timeout_seconds=self._config.timeout_seconds,
            max_response_bytes=self._config.max_response_bytes,
            input_dto=body,
            params=params,
            write=write,
        )

    def load(self, grant: RuntimeGrant, input_dto: EditorLoadInputDTO,
        request_id: str) -> EditorLoadOutputDTO:
        self._grant(grant, input_dto.session_id)
        body = _EditorRequestDTO(request_id=request_id, input=input_dto)
        result = self._request(
            "POST",
            "/api/dream/v1/editor/operations/editor-state.load",
            grant,
            request_id,
            EditorLoadOutputDTO,
            body=body,
        )
        if result.session_id != input_dto.session_id:
            raise invalid_response(request_id)
        return result

    def replace(self, grant: RuntimeGrant, input_dto: EditorReplaceInputDTO,
        request_id: str) -> EditorReplaceOutputDTO:
        self._grant(grant, input_dto.session_id)
        body = _EditorRequestDTO(request_id=request_id, input=input_dto)
        result = self._request(
            "POST",
            "/api/dream/v1/editor/operations/editor-state.replace",
            grant,
            request_id,
            EditorReplaceOutputDTO,
            body=body,
            write=True,
        )
        if result.session_id != input_dto.session_id:
            raise invalid_response(request_id, write=True)
        return result

    def receipt(self, grant: RuntimeGrant, request_id: str):
        if grant.editor_session_id is None:
            raise configuration_invalid()
        self._grant(grant, grant.editor_session_id)
        result = self._request(
            "GET",
            "/api/dream/v1/editor/receipts/" + request_id,
            grant,
            request_id,
            CommittedReceiptDTO[EditorReplaceOutputDTO] | AbsentReceiptDTO,
            params={"operation": "editor-state.replace"},
        )
        if result.operation != "editor-state.replace" or result.request_id != request_id:
            raise invalid_response(request_id)
        if isinstance(result, CommittedReceiptDTO) and result.result.session_id != grant.editor_session_id:
            raise invalid_response(request_id)
        return result


@dataclass
class _SessionGrant:
    grant: RuntimeGrant
    keeper: RuntimeGrantKeeper | None = None


@dataclass(frozen=True)
class _PendingReplace:
    input_dto: EditorReplaceInputDTO
    request_id: str


class _ThreadingBroker(socketserver.ThreadingTCPServer):
    allow_reuse_address = False
    daemon_threads = True
    block_on_close = True


class AdminEditorRuntime:
    """Own one turn's Editor grants, public HTTP clients and private broker."""

    def __init__(
        self,
        resolution: AdminWorkflowResolution,
        *,
        actor_id: str,
        access_token: str,
        delegation_creator: AdminDelegationCreator,
        runtime_http_config: RuntimeHttpConfig,
        initial_session_id: str | None = None,
        initial_request_id: str | None = None,
        clock: Callable[[], datetime] | None = None,
        request_id_factory: Callable[[], str] | None = None,
        renewal_settings: RuntimeRenewalSettings | None = None,
        runtime_client_factory: Callable[[], AdminRuntimeClient] | None = None,
        editor_client_factory: Callable[[], AdminEditorHttpClient] | None = None,
    ):
        resolution.context_for(actor_id=actor_id, thread_id=resolution.thread_id)
        if not access_token:
            raise configuration_invalid()
        self._resolution = resolution
        self._actor_id = actor_id
        self._access_token = access_token
        self._delegation_creator = delegation_creator
        self._http_config = runtime_http_config
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._request_id_factory = request_id_factory or (lambda: str(uuid4()))
        self._renewal_settings = renewal_settings
        self._runtime_client_factory = runtime_client_factory or (
            lambda: AdminRuntimeClient(runtime_http_config)
        )
        self._editor_client_factory = editor_client_factory or (
            lambda: AdminEditorHttpClient(runtime_http_config)
        )
        self._sessions: dict[str, _SessionGrant] = {}
        self._cache: dict[str, dict] = {}
        self._known_replaces: dict[str, tuple[EditorReplaceInputDTO, EditorReplaceOutputDTO]] = {}
        self._pending: _PendingReplace | None = None
        self._lock = threading.RLock()
        self._action_lock = threading.Lock()
        self._closed = False
        self._started = False
        self._runtime_client: AdminRuntimeClient | None = None
        self._editor_client: AdminEditorHttpClient | None = None
        self._server: _ThreadingBroker | None = None
        self._server_thread: threading.Thread | None = None
        self._broker_capability = secrets.token_urlsafe(32)
        TypeAdapter(_BROKER_CAPABILITY).validate_python(self._broker_capability)
        if initial_session_id:
            self._create_grant(initial_session_id, initial_request_id or self._request_id_factory())

    def _create_grant(self, session_id: str, request_id: str) -> _SessionGrant:
        requested = DelegationCreateInputDTO(
            purpose="editor-stdio",
            thread_id=self._resolution.thread_id,
            run_id=None,
            editor_session_id=session_id,
            scopes=["editor:read", "editor:write"],
        )
        grant = self._delegation_creator.create(
            requested,
            access_token=self._access_token,
            request_id=request_id,
            required_operations=EDITOR_RUNTIME_CAPABILITIES,
        )
        bound = _SessionGrant(grant)
        self._sessions[session_id] = bound
        return bound

    def _current_grant(self, session_id: str) -> RuntimeGrant:
        with self._lock:
            if self._closed:
                raise AdminDataError("DELEGATION_EXPIRED", 401)
            bound = self._sessions.get(session_id)
            if bound is None:
                bound = self._create_grant(session_id, self._request_id_factory())
                if self._started:
                    if self._runtime_client is None:
                        raise configuration_invalid()
                    keeper = RuntimeGrantKeeper(
                        bound.grant,
                        self._runtime_client,
                        clock=self._clock,
                        settings=self._renewal_settings,
                    )
                    try:
                        keeper.start()
                    except Exception:
                        keeper.close()
                        self._sessions.pop(session_id, None)
                        raise AdminDataError("EDITOR_RUNTIME_UNAVAILABLE", 503) from None
                    bound.keeper = keeper
            keeper = bound.keeper
            grant = bound.grant
        if keeper is not None:
            return keeper.current("editor-stdio")
        if self._clock() >= grant.expires_at:
            raise AdminDataError("DELEGATION_EXPIRED", 401)
        return grant

    def _editor(self) -> AdminEditorHttpClient:
        with self._lock:
            if self._closed or not self._started or self._editor_client is None:
                raise AdminDataError("EDITOR_RUNTIME_UNAVAILABLE", 503)
            return self._editor_client

    def load(self, input_dto: EditorLoadInputDTO, request_id: str) -> EditorLoadOutputDTO:
        with self._action_lock:
            # A failed switch must not expose an older successful load for the
            # same Session to the host PostToolUse callback.
            with self._lock:
                self._cache.pop(input_dto.session_id, None)
            grant = self._current_grant(input_dto.session_id)
            result = self._editor().load(grant, input_dto, request_id)
            with self._lock:
                if result.editor_state is None:
                    self._cache.pop(input_dto.session_id, None)
                else:
                    self._cache[input_dto.session_id] = result.editor_state.model_dump(
                        mode="python", exclude_unset=True
                    )
            return result

    def replace(self, input_dto: EditorReplaceInputDTO, request_id: str) -> EditorReplaceOutputDTO:
        with self._action_lock:
            known = self._known_replaces.get(request_id)
            if known is not None:
                if known[0] != input_dto:
                    raise AdminDataError("ADMIN_REQUEST_ID_CONFLICT", 409, request_id)
                return known[1]
            pending = self._pending
            if pending is not None:
                if pending.input_dto != input_dto or pending.request_id != request_id:
                    raise AdminDataError("ADMIN_WRITE_RESULT_UNKNOWN", 503, pending.request_id, True)
                grant = self._current_grant(pending.input_dto.session_id)
                try:
                    receipt = self._editor().receipt(grant, pending.request_id)
                except AdminDataError as error:
                    raise AdminDataError(error.code, error.status_code, pending.request_id, True) from None
                if not isinstance(receipt, CommittedReceiptDTO):
                    raise AdminDataError("ADMIN_WRITE_RESULT_UNKNOWN", 503, pending.request_id, True)
                result = receipt.result
                return self._confirm_replace(pending, result)
            grant = self._current_grant(input_dto.session_id)
            editor = self._editor()
            pending = _PendingReplace(input_dto, request_id)
            self._pending = pending
            try:
                result = editor.replace(grant, input_dto, request_id)
            except AdminDataError as error:
                if not error.outcome_unknown:
                    self._pending = None
                raise
            except Exception:
                raise AdminDataError("ADMIN_UNAVAILABLE", 503, request_id, True) from None
            return self._confirm_replace(pending, result)

    def _confirm_replace(self, pending: _PendingReplace,
        result: EditorReplaceOutputDTO) -> EditorReplaceOutputDTO:
        if result.session_id != pending.input_dto.session_id:
            raise invalid_response(pending.request_id, write=True)
        self._known_replaces[pending.request_id] = (pending.input_dto, result)
        with self._lock:
            self._cache[result.session_id] = pending.input_dto.editor_state.model_dump(
                mode="python", exclude_unset=True
            )
        self._pending = None
        return result

    def cached_state(self, session_id: str) -> dict | None:
        with self._lock:
            value = self._cache.get(session_id)
            return deepcopy(value) if value is not None else None

    def _broker_response(self, raw: bytes) -> bytes:
        request_id: str | None = None
        try:
            request = _BrokerRequestDTO.model_validate_json(raw)
            request_id = request.request_id
            if not hmac.compare_digest(request.capability, self._broker_capability):
                raise AdminDataError("EDITOR_BROKER_DENIED", 401, request.request_id)
            if request.operation == "editor-state.load":
                result = self.load(request.input, request.request_id)
            else:
                result = self.replace(request.input, request.request_id)
            response = _BrokerResponseDTO(ok=True, result=result)
        except (ValidationError, ValueError, TypeError):
            response = _BrokerResponseDTO(
                ok=False,
                error=_BrokerErrorDTO(
                    code="EDITOR_BROKER_INPUT_INVALID",
                    status_code=400,
                    request_id=request_id,
                    outcome_unknown=False,
                ),
            )
        except AdminDataError as error:
            response = _BrokerResponseDTO(
                ok=False,
                error=_BrokerErrorDTO(
                    code=error.code,
                    status_code=error.status_code,
                    request_id=error.request_id or request_id,
                    outcome_unknown=error.outcome_unknown,
                ),
            )
        return response.model_dump_json(exclude_none=True).encode("utf-8") + b"\n"

    def start(self) -> None:
        with self._lock:
            if self._closed:
                raise AdminDataError("DELEGATION_EXPIRED", 401)
            if self._started:
                return
            runtime_client = self._runtime_client_factory()
            editor_client = self._editor_client_factory()
            runtime = self

            class Handler(socketserver.StreamRequestHandler):
                def handle(self) -> None:
                    self.connection.settimeout(runtime._http_config.timeout_seconds)
                    raw = self.rfile.readline(runtime._http_config.max_response_bytes + 1)
                    if not raw or len(raw) > runtime._http_config.max_response_bytes or not raw.endswith(b"\n"):
                        payload = _BrokerResponseDTO(
                            ok=False,
                            error=_BrokerErrorDTO(
                                code="EDITOR_BROKER_INPUT_INVALID",
                                status_code=400,
                                request_id=None,
                                outcome_unknown=False,
                            ),
                        ).model_dump_json(exclude_none=True).encode("utf-8") + b"\n"
                    else:
                        payload = runtime._broker_response(raw[:-1])
                    self.wfile.write(payload)

            server: _ThreadingBroker | None = None
            started_keepers: list[RuntimeGrantKeeper] = []
            try:
                server = _ThreadingBroker((_LOOPBACK_HOST, 0), Handler)
                server_thread = threading.Thread(
                    target=server.serve_forever,
                    name="dream-editor-runtime-broker",
                    daemon=True,
                )
                self._runtime_client = runtime_client
                self._editor_client = editor_client
                self._server = server
                self._server_thread = server_thread
                self._started = True
                for bound in self._sessions.values():
                    bound.keeper = RuntimeGrantKeeper(
                        bound.grant,
                        runtime_client,
                        clock=self._clock,
                        settings=self._renewal_settings,
                    )
                    started_keepers.append(bound.keeper)
                    bound.keeper.start()
                server_thread.start()
            except BaseException:
                self._started = False
                self._runtime_client = None
                self._editor_client = None
                self._server = None
                self._server_thread = None
                for keeper in started_keepers:
                    keeper.close()
                if server is not None:
                    server.server_close()
                editor_client.close()
                runtime_client.close()
                raise

    def child_env(self) -> dict[str, str]:
        with self._lock:
            if not self._started or self._server is None or self._closed:
                raise AdminDataError("EDITOR_RUNTIME_UNAVAILABLE", 503)
            host, port = self._server.server_address
            if host != _LOOPBACK_HOST or not isinstance(port, int):
                raise configuration_invalid()
            return {
                EDITOR_BROKER_HOST_ENV: host,
                EDITOR_BROKER_PORT_ENV: str(port),
                EDITOR_BROKER_CAPABILITY_ENV: self._broker_capability,
                EDITOR_BROKER_TIMEOUT_ENV: str(self._http_config.timeout_seconds),
                EDITOR_BROKER_MAX_BYTES_ENV: str(self._http_config.max_response_bytes),
            }

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            server, server_thread = self._server, self._server_thread
            keepers = [bound.keeper for bound in self._sessions.values() if bound.keeper is not None]
            runtime_client, editor_client = self._runtime_client, self._editor_client
        if server is not None:
            server.shutdown()
            server.server_close()
        if server_thread is not None and server_thread is not threading.current_thread():
            server_thread.join()
        with self._action_lock:
            pass
        for keeper in keepers:
            keeper.close()
        if editor_client is not None:
            editor_client.close()
        if runtime_client is not None:
            runtime_client.close()


class EditorBrokerClient:
    """Child-side closed client; only the private local broker is reachable."""

    def __init__(self, host: str, port: int, capability: str, *, timeout_seconds: float,
        max_response_bytes: int):
        TypeAdapter(_BROKER_CAPABILITY).validate_python(capability)
        if (
            host != _LOOPBACK_HOST
            or isinstance(port, bool)
            or not isinstance(port, int)
            or not 1 <= port <= 65535
            or not math.isfinite(timeout_seconds)
            or timeout_seconds <= 0
            or isinstance(max_response_bytes, bool)
            or not isinstance(max_response_bytes, int)
            or max_response_bytes < 1
        ):
            raise configuration_invalid()
        self._host = host
        self._port = port
        self._capability = capability
        self._timeout_seconds = timeout_seconds
        self._max_response_bytes = max_response_bytes
        self._pending: _PendingReplace | None = None
        self._lock = threading.Lock()

    @classmethod
    def from_env(cls, values: dict[str, str]) -> "EditorBrokerClient":
        try:
            return cls(
                values.get(EDITOR_BROKER_HOST_ENV, ""),
                int(values.get(EDITOR_BROKER_PORT_ENV, "")),
                values.get(EDITOR_BROKER_CAPABILITY_ENV, ""),
                timeout_seconds=float(values.get(EDITOR_BROKER_TIMEOUT_ENV, "")),
                max_response_bytes=int(values.get(EDITOR_BROKER_MAX_BYTES_ENV, "")),
            )
        except (TypeError, ValueError):
            raise configuration_invalid() from None

    def _call(self, operation: Literal["editor-state.load", "editor-state.replace"],
        input_dto: EditorLoadInputDTO | EditorReplaceInputDTO, request_id: str, *, write: bool):
        request = _BrokerRequestDTO(
            capability=self._capability,
            operation=operation,
            request_id=request_id,
            input=input_dto,
        )
        sent = False
        try:
            with socket.create_connection(
                (self._host, self._port), timeout=self._timeout_seconds
            ) as connection:
                connection.settimeout(self._timeout_seconds)
                connection.sendall(request.model_dump_json().encode("utf-8") + b"\n")
                sent = True
                reader = connection.makefile("rb")
                raw = reader.readline(self._max_response_bytes + 1)
            if not raw or len(raw) > self._max_response_bytes or not raw.endswith(b"\n"):
                raise invalid_response(request_id, write=write)
            response = _BrokerResponseDTO.model_validate_json(raw[:-1])
        except AdminDataError:
            raise
        except (OSError, TimeoutError):
            raise unavailable(request_id, write=write and sent) from None
        except (ValidationError, ValueError, TypeError):
            raise invalid_response(request_id, write=write) from None
        if not response.ok:
            error = response.error
            if error is None:
                raise invalid_response(request_id, write=write)
            raise AdminDataError(
                error.code,
                error.status_code,
                error.request_id or request_id,
                error.outcome_unknown,
            )
        if response.result is None:
            raise invalid_response(request_id, write=write)
        return response.result

    def load(self, session_id: str) -> dict | None:
        self._recover_pending()
        request_id = str(uuid4())
        result = self._call(
            "editor-state.load",
            EditorLoadInputDTO(session_id=session_id),
            request_id,
            write=False,
        )
        if type(result) is not EditorLoadOutputDTO or result.session_id != session_id:
            raise invalid_response(request_id)
        return (
            result.editor_state.model_dump(mode="python", exclude_unset=True)
            if result.editor_state is not None
            else None
        )

    def _recover_pending(self) -> None:
        """Resolve an earlier uncertain replace before any later state read."""

        with self._lock:
            pending = self._pending
            if pending is None:
                return
            try:
                result = self._call(
                    "editor-state.replace",
                    pending.input_dto,
                    pending.request_id,
                    write=True,
                )
            except AdminDataError as error:
                # The first replace may have committed. A later broker/connect
                # failure cannot turn that earlier outcome into a definite one.
                raise AdminDataError(
                    error.code,
                    error.status_code,
                    pending.request_id,
                    True,
                ) from None
            if (
                type(result) is not EditorReplaceOutputDTO
                or result.session_id != pending.input_dto.session_id
            ):
                raise invalid_response(pending.request_id, write=True)
            self._pending = None

    def replace(self, session_id: str, editor_state: dict) -> None:
        input_dto = EditorReplaceInputDTO(
            session_id=session_id,
            editor_state=EditorStateDTO.model_validate(editor_state),
        )
        with self._lock:
            pending = self._pending
            recovering = pending is not None
            if pending is not None and pending.input_dto != input_dto:
                raise AdminDataError("ADMIN_WRITE_RESULT_UNKNOWN", 503, pending.request_id, True)
            if pending is None:
                pending = _PendingReplace(input_dto, str(uuid4()))
                self._pending = pending
            try:
                result = self._call(
                    "editor-state.replace",
                    pending.input_dto,
                    pending.request_id,
                    write=True,
                )
            except AdminDataError as error:
                if recovering:
                    raise AdminDataError(
                        error.code,
                        error.status_code,
                        pending.request_id,
                        True,
                    ) from None
                if not error.outcome_unknown:
                    self._pending = None
                raise
            if type(result) is not EditorReplaceOutputDTO or result.session_id != session_id:
                raise invalid_response(pending.request_id, write=True)
            self._pending = None
