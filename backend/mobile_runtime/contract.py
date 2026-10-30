# [Input] Native bridge dictionaries using the shared mobile v1 envelope.
# [Output] Strict request parsing plus correlated generation-aware response dictionaries.
# [Pos] Embedded-Python mirror of mobile/shared/bridge/contract.json.
# [Sync] 2026-10-25: remove native authentication methods and callback from the platform protocol.
# [Sync] 2026-10-24: add page-generation and pull-stream protocol fields.

"""Strict v1 request envelope shared with the native mobile hosts."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping

MOBILE_BRIDGE_VERSION = "1.0"
MOBILE_BRIDGE_METHODS = frozenset(
    {
        "app.getInfo",
        "runtime.getCapabilities",
        "runtime.request",
        "runtime.response.read",
        "runtime.cancel",
        "lifecycle.getState",
        "file.pick",
        "file.save",
        "share.open",
        "external.open",
    }
)
MOBILE_BRIDGE_EVENTS = frozenset(
    {
        "lifecycle.changed",
        "network.changed",
        "runtime.changed",
    }
)
_REQUEST_ID = re.compile(r"^[A-Za-z0-9_-]{1,96}$")


class MobileBridgeProtocolError(ValueError):
    """A request failed before any platform or business operation ran."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class BridgeRequest:
    request_id: str
    page_generation: str
    method: str
    params: Mapping[str, Any]

    @classmethod
    def parse(cls, value: object) -> "BridgeRequest":
        if not isinstance(value, Mapping):
            raise MobileBridgeProtocolError("BAD_REQUEST", "Bridge request must be an object.")
        if value.get("version") != MOBILE_BRIDGE_VERSION:
            raise MobileBridgeProtocolError("PROTOCOL_MISMATCH", "Bridge protocol version is unsupported.")
        request_id = value.get("id")
        if not isinstance(request_id, str) or _REQUEST_ID.fullmatch(request_id) is None:
            raise MobileBridgeProtocolError("BAD_REQUEST", "Bridge request identifier is invalid.")
        page_generation = value.get("pageGeneration")
        if not isinstance(page_generation, str) or _REQUEST_ID.fullmatch(page_generation) is None:
            raise MobileBridgeProtocolError("BAD_REQUEST", "Bridge page generation is invalid.")
        method = value.get("method")
        if not isinstance(method, str) or method not in MOBILE_BRIDGE_METHODS:
            raise MobileBridgeProtocolError("FORBIDDEN", "Bridge method is not allowlisted.")
        params = value.get("params")
        if not isinstance(params, Mapping):
            raise MobileBridgeProtocolError("BAD_REQUEST", "Bridge params must be an object.")
        return cls(request_id=request_id, page_generation=page_generation, method=method, params=dict(params))

    def success(self, result: object) -> dict[str, object]:
        return {
            "version": MOBILE_BRIDGE_VERSION,
            "id": self.request_id,
            "pageGeneration": self.page_generation,
            "ok": True,
            "result": result,
        }

    def failure(self, code: str, message: str) -> dict[str, object]:
        return {
            "version": MOBILE_BRIDGE_VERSION,
            "id": self.request_id,
            "pageGeneration": self.page_generation,
            "ok": False,
            "error": {"code": code, "message": message},
        }
