# [Input] Turn-local loopback environment and the Session list wire projection.
# [Output] Strict broker DTOs and a synchronous child client with no Admin or database dependency.
# [Pos] Neutral user-MCP Session projection protocol shared by the host broker and stdio child.
# [Sync] 2026-09-15: define the bounded private Session broker protocol.
"""Strict private protocol for retrieving Session projections over loopback."""

from __future__ import annotations

from datetime import date, datetime
import json
import math
import re
import socket
from typing import Annotated
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator


SESSION_BROKER_HOST_ENV = "INK_SESSION_BROKER_HOST"
SESSION_BROKER_PORT_ENV = "INK_SESSION_BROKER_PORT"
SESSION_BROKER_CAPABILITY_ENV = "INK_SESSION_BROKER_CAPABILITY"
SESSION_BROKER_TIMEOUT_ENV = "INK_SESSION_BROKER_TIMEOUT_SECONDS"
SESSION_BROKER_MAX_BYTES_ENV = "INK_SESSION_BROKER_MAX_BYTES"
SESSION_RETRIEVAL_MODE_ENV = "INK_AGENT_SESSION_RETRIEVAL_MODE"
SESSION_FUZZY_MIN_SCORE_ENV = "INK_AGENT_SESSION_FUZZY_MIN_SCORE"
SESSION_BROKER_ENV_NAMES = (
    SESSION_BROKER_HOST_ENV,
    SESSION_BROKER_PORT_ENV,
    SESSION_BROKER_CAPABILITY_ENV,
    SESSION_BROKER_TIMEOUT_ENV,
    SESSION_BROKER_MAX_BYTES_ENV,
)
SESSION_USER_MCP_ENV_NAMES = (
    *SESSION_BROKER_ENV_NAMES,
    SESSION_RETRIEVAL_MODE_ENV,
    SESSION_FUZZY_MIN_SCORE_ENV,
)
SESSION_BROKER_HOST = "127.0.0.1"

_Capability = Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{43}$")]
_Identifier = Annotated[
    str,
    Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    ),
]
_DateText = Annotated[str, Field(pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")]


class SessionProjectionProtocolError(Exception):
    """Safe child-side failure without host, credential or response details."""

    def __init__(self, code: str, status_code: int, request_id: str | None = None):
        super().__init__(code)
        self.code = code
        self.status_code = status_code
        self.request_id = request_id


class _StrictDTO(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        frozen=True,
        hide_input_in_errors=True,
        allow_inf_nan=False,
    )


def _validate_date(value: str) -> str:
    date.fromisoformat(value)
    return value


def _validate_timestamp(value: str | None) -> str | None:
    if value is None:
        return None
    if re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}"
        r"(?::[0-9]{2}(?:\.[0-9]+)?)?(?:Z|[+-][0-9]{2}:[0-9]{2})",
        value,
    ) is None:
        raise ValueError("Timestamp must include a timezone")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Timestamp must include a timezone")
    return value


class SessionProjectionRequestDTO(_StrictDTO):
    capability: _Capability = Field(repr=False)
    request_id: _Identifier
    start_date: _DateText
    end_date: _DateText
    include_text: bool
    _dates = field_validator("start_date", "end_date")(_validate_date)

    @model_validator(mode="after")
    def validate_range(self):
        if self.start_date > self.end_date:
            raise ValueError("Session date range is reversed")
        return self


class SessionProjectionDTO(_StrictDTO):
    id: Annotated[str, Field(min_length=1)]
    name: str | None
    labels: list[str]
    created_at: str | None
    updated_at: str | None
    first_line: str
    text: str | None
    _timestamps = field_validator("created_at", "updated_at")(_validate_timestamp)


class SessionProjectionResultDTO(_StrictDTO):
    sessions: list[SessionProjectionDTO]


class SessionProjectionErrorDTO(_StrictDTO):
    code: Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[A-Z0-9_]+$")]
    status_code: int = Field(ge=400, le=599)
    request_id: _Identifier | None


class SessionProjectionResponseDTO(_StrictDTO):
    ok: bool
    result: SessionProjectionResultDTO | None = None
    error: SessionProjectionErrorDTO | None = None

    @model_validator(mode="after")
    def validate_shape(self):
        if self.ok == (self.result is None) or self.ok == (self.error is not None):
            raise ValueError("Session broker response shape is invalid")
        return self


class SessionProjectionBrokerClient:
    """Synchronous stdio-child client for one private Session broker."""

    def __init__(
        self,
        host: str,
        port: int,
        capability: str,
        *,
        timeout_seconds: float,
        max_response_bytes: int,
    ) -> None:
        try:
            SessionProjectionRequestDTO(
                capability=capability,
                request_id="configuration-check",
                start_date="2000-01-01",
                end_date="2000-01-01",
                include_text=False,
            )
        except ValidationError:
            raise SessionProjectionProtocolError(
                "SESSION_BROKER_CONFIGURATION_INVALID", 503
            ) from None
        if (
            host != SESSION_BROKER_HOST
            or isinstance(port, bool)
            or not isinstance(port, int)
            or not 1 <= port <= 65535
            or not math.isfinite(timeout_seconds)
            or timeout_seconds <= 0
            or isinstance(max_response_bytes, bool)
            or not isinstance(max_response_bytes, int)
            or max_response_bytes < 1
        ):
            raise SessionProjectionProtocolError(
                "SESSION_BROKER_CONFIGURATION_INVALID", 503
            )
        self._host = host
        self._port = port
        self._capability = capability
        self._timeout_seconds = timeout_seconds
        self._max_response_bytes = max_response_bytes

    @classmethod
    def from_env(cls, values: dict[str, str]) -> "SessionProjectionBrokerClient":
        try:
            return cls(
                values.get(SESSION_BROKER_HOST_ENV, ""),
                int(values.get(SESSION_BROKER_PORT_ENV, "")),
                values.get(SESSION_BROKER_CAPABILITY_ENV, ""),
                timeout_seconds=float(values.get(SESSION_BROKER_TIMEOUT_ENV, "")),
                max_response_bytes=int(values.get(SESSION_BROKER_MAX_BYTES_ENV, "")),
            )
        except (TypeError, ValueError):
            raise SessionProjectionProtocolError(
                "SESSION_BROKER_CONFIGURATION_INVALID", 503
            ) from None

    def list_sessions(
        self,
        *,
        start_date: str,
        end_date: str,
        include_text: bool,
        request_id: str | None = None,
    ) -> SessionProjectionResultDTO:
        resolved_request_id = request_id or str(uuid4())
        try:
            request = SessionProjectionRequestDTO(
                capability=self._capability,
                request_id=resolved_request_id,
                start_date=start_date,
                end_date=end_date,
                include_text=include_text,
            )
        except ValidationError:
            raise SessionProjectionProtocolError(
                "SESSION_BROKER_INPUT_INVALID", 400, resolved_request_id
            ) from None
        try:
            encoded = request.model_dump_json().encode("utf-8") + b"\n"
            with socket.create_connection(
                (self._host, self._port), timeout=self._timeout_seconds
            ) as connection:
                connection.settimeout(self._timeout_seconds)
                connection.sendall(encoded)
                reader = connection.makefile("rb")
                raw = reader.readline(self._max_response_bytes + 1)
        except (OSError, TimeoutError):
            raise SessionProjectionProtocolError(
                "SESSION_BROKER_UNAVAILABLE", 503, resolved_request_id
            ) from None
        if (
            not raw
            or len(raw) > self._max_response_bytes
            or not raw.endswith(b"\n")
        ):
            raise SessionProjectionProtocolError(
                "SESSION_BROKER_RESPONSE_INVALID", 503, resolved_request_id
            )
        try:
            response = SessionProjectionResponseDTO.model_validate_json(raw[:-1])
        except (ValidationError, ValueError, TypeError, json.JSONDecodeError):
            raise SessionProjectionProtocolError(
                "SESSION_BROKER_RESPONSE_INVALID", 503, resolved_request_id
            ) from None
        if not response.ok:
            error = response.error
            if error is None:
                raise SessionProjectionProtocolError(
                    "SESSION_BROKER_RESPONSE_INVALID", 503, resolved_request_id
                )
            raise SessionProjectionProtocolError(
                error.code,
                error.status_code,
                error.request_id or resolved_request_id,
            )
        result = response.result
        if result is None or (
            not include_text and any(item.text is not None for item in result.sessions)
        ):
            raise SessionProjectionProtocolError(
                "SESSION_BROKER_RESPONSE_INVALID", 503, resolved_request_id
            )
        return result


__all__ = [
    "SESSION_BROKER_CAPABILITY_ENV",
    "SESSION_BROKER_ENV_NAMES",
    "SESSION_BROKER_HOST",
    "SESSION_BROKER_HOST_ENV",
    "SESSION_BROKER_MAX_BYTES_ENV",
    "SESSION_BROKER_PORT_ENV",
    "SESSION_BROKER_TIMEOUT_ENV",
    "SESSION_FUZZY_MIN_SCORE_ENV",
    "SESSION_RETRIEVAL_MODE_ENV",
    "SESSION_USER_MCP_ENV_NAMES",
    "SessionProjectionBrokerClient",
    "SessionProjectionDTO",
    "SessionProjectionErrorDTO",
    "SessionProjectionProtocolError",
    "SessionProjectionRequestDTO",
    "SessionProjectionResponseDTO",
    "SessionProjectionResultDTO",
]
