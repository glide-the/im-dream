# [Input] One bound Session projection provider, strict loopback DTOs and server transport bounds.
# [Output] A turn-local capability broker that stops acceptance and drains dispatched reads on close.
# [Pos] Server-only Session projection transport; child processes receive no identity or Admin credential.
# [Sync] 2026-09-15: add the reusable private broker for Chat Session retrieval.
"""Private loopback broker for bounded Session list projections."""

from __future__ import annotations

from dataclasses import dataclass
import hmac
import logging
import math
import secrets
import socketserver
import threading
from typing import Protocol

from pydantic import TypeAdapter, ValidationError

from libs.claude_agent_kit.server.session_projection_protocol import (
    SESSION_BROKER_CAPABILITY_ENV,
    SESSION_BROKER_HOST,
    SESSION_BROKER_HOST_ENV,
    SESSION_BROKER_MAX_BYTES_ENV,
    SESSION_BROKER_PORT_ENV,
    SESSION_BROKER_TIMEOUT_ENV,
    SessionProjectionErrorDTO,
    SessionProjectionRequestDTO,
    SessionProjectionResponseDTO,
    SessionProjectionResultDTO,
)

from .errors import AdminDataError, configuration_invalid
from .session_models import SessionListInputDTO, SessionListResultDTO


logger = logging.getLogger(__name__)


class SessionProjectionProvider(Protocol):
    """Host provider bound to an identity owner before broker startup."""

    def list_sessions(
        self, input_dto: SessionListInputDTO, request_id: str
    ) -> SessionListResultDTO: ...


@dataclass(frozen=True, slots=True)
class SessionProjectionBrokerSettings:
    timeout_seconds: float
    max_bytes: int

    def __post_init__(self) -> None:
        if (
            not math.isfinite(self.timeout_seconds)
            or self.timeout_seconds <= 0
            or isinstance(self.max_bytes, bool)
            or not isinstance(self.max_bytes, int)
            or self.max_bytes < 1
        ):
            raise configuration_invalid()


class _ThreadingBroker(socketserver.ThreadingTCPServer):
    allow_reuse_address = False
    daemon_threads = True
    block_on_close = True


class SessionProjectionBroker:
    """Own one provider-bound, turn-local Session projection endpoint."""

    def __init__(
        self,
        provider: SessionProjectionProvider,
        *,
        settings: SessionProjectionBrokerSettings,
    ) -> None:
        self._provider = provider
        self._settings = settings
        self._capability = secrets.token_urlsafe(32)
        TypeAdapter(SessionProjectionRequestDTO).validate_python(
            {
                "capability": self._capability,
                "request_id": "capability-check",
                "start_date": "2000-01-01",
                "end_date": "2000-01-01",
                "include_text": False,
            },
            strict=True,
        )
        self._lock = threading.RLock()
        self._action_lock = threading.Lock()
        self._server: _ThreadingBroker | None = None
        self._server_thread: threading.Thread | None = None
        self._closed = False

    @staticmethod
    def _error(
        code: str,
        status_code: int,
        request_id: str | None,
    ) -> bytes:
        return (
            SessionProjectionResponseDTO(
                ok=False,
                error=SessionProjectionErrorDTO(
                    code=code,
                    status_code=status_code,
                    request_id=request_id,
                ),
            ).model_dump_json().encode("utf-8")
            + b"\n"
        )

    def _response(self, raw: bytes) -> bytes:
        request_id: str | None = None
        try:
            request = SessionProjectionRequestDTO.model_validate_json(raw)
            request_id = request.request_id
            if not hmac.compare_digest(request.capability, self._capability):
                raise AdminDataError("SESSION_BROKER_DENIED", 401, request_id)
            with self._action_lock:
                with self._lock:
                    if self._closed:
                        raise AdminDataError(
                            "SESSION_BROKER_UNAVAILABLE", 503, request_id
                        )
                input_dto = SessionListInputDTO(
                    start_date=request.start_date,
                    end_date=request.end_date,
                    include_text=request.include_text,
                )
                result = self._provider.list_sessions(input_dto, request_id)
            if type(result) is not SessionListResultDTO:
                raise AdminDataError("ADMIN_RESPONSE_INVALID", 503, request_id)
            projection = SessionProjectionResultDTO.model_validate(
                result.model_dump(mode="python"), strict=True
            )
            if not request.include_text and any(
                item.text is not None for item in projection.sessions
            ):
                raise AdminDataError("ADMIN_RESPONSE_INVALID", 503, request_id)
            payload = (
                SessionProjectionResponseDTO(ok=True, result=projection)
                .model_dump_json()
                .encode("utf-8")
                + b"\n"
            )
        except (ValidationError, ValueError, TypeError):
            payload = self._error(
                "SESSION_BROKER_INPUT_INVALID", 400, request_id
            )
        except AdminDataError as error:
            payload = self._error(
                error.code,
                error.status_code,
                error.request_id or request_id,
            )
        except Exception:
            logger.error(
                "Session projection provider failed safely; request_id=%s",
                request_id,
            )
            payload = self._error(
                "SESSION_PROJECTION_UNAVAILABLE", 503, request_id
            )
        if len(payload) > self._settings.max_bytes:
            payload = self._error(
                "SESSION_BROKER_RESPONSE_TOO_LARGE", 503, request_id
            )
        return payload if len(payload) <= self._settings.max_bytes else b""

    def start(self) -> None:
        with self._lock:
            if self._closed:
                raise AdminDataError("SESSION_BROKER_UNAVAILABLE", 503)
            if self._server is not None:
                return
            broker = self

            class Handler(socketserver.StreamRequestHandler):
                def handle(self) -> None:
                    self.connection.settimeout(broker._settings.timeout_seconds)
                    raw = self.rfile.readline(broker._settings.max_bytes + 1)
                    if (
                        not raw
                        or len(raw) > broker._settings.max_bytes
                        or not raw.endswith(b"\n")
                    ):
                        payload = broker._error(
                            "SESSION_BROKER_INPUT_INVALID", 400, None
                        )
                    else:
                        payload = broker._response(raw[:-1])
                    if payload and len(payload) <= broker._settings.max_bytes:
                        self.wfile.write(payload)

            server: _ThreadingBroker | None = None
            try:
                server = _ThreadingBroker((SESSION_BROKER_HOST, 0), Handler)
                server_thread = threading.Thread(
                    target=server.serve_forever,
                    name="dream-session-projection-broker",
                    daemon=True,
                )
                self._server = server
                self._server_thread = server_thread
                server_thread.start()
            except BaseException:
                self._server = None
                self._server_thread = None
                if server is not None:
                    server.server_close()
                raise AdminDataError("SESSION_BROKER_UNAVAILABLE", 503) from None

    def child_env(self) -> dict[str, str]:
        with self._lock:
            if self._closed or self._server is None:
                raise AdminDataError("SESSION_BROKER_UNAVAILABLE", 503)
            host, port = self._server.server_address
            if host != SESSION_BROKER_HOST or not isinstance(port, int):
                raise configuration_invalid()
            return {
                SESSION_BROKER_HOST_ENV: host,
                SESSION_BROKER_PORT_ENV: str(port),
                SESSION_BROKER_CAPABILITY_ENV: self._capability,
                SESSION_BROKER_TIMEOUT_ENV: str(self._settings.timeout_seconds),
                SESSION_BROKER_MAX_BYTES_ENV: str(self._settings.max_bytes),
            }

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            server, server_thread = self._server, self._server_thread
        if server is not None:
            server.shutdown()
            server.server_close()
        if (
            server_thread is not None
            and server_thread is not threading.current_thread()
        ):
            server_thread.join()
        # A request that entered the provider before close must finish before
        # the owning grant keeper or Admin HTTP client can be closed.
        with self._action_lock:
            pass


__all__ = [
    "SessionProjectionBroker",
    "SessionProjectionBrokerSettings",
    "SessionProjectionProvider",
]
