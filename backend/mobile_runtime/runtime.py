# [Input] Strict mobile bridge requests and platform qualification facts.
# [Output] Capability responses or stable unavailable errors without service side effects.
# [Pos] Minimal embedded-Python composition seam; production server and Claude CLI remain outside this module.
# [Sync] 2026-10-24: expose only Python-owned methods; the native host composes public capabilities.

"""Minimal embedded-Python composition seam for the v1 mobile bridge."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .contract import BridgeRequest


class MobileRuntimeUnavailable(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(slots=True)
class MobileRuntime:
    """Answer qualified runtime facts without starting the server or CLI graph."""

    platform: Literal["ios", "android"]

    def handle(self, raw_request: object) -> dict[str, object]:
        request = BridgeRequest.parse(raw_request)
        if request.method in {"runtime.request", "runtime.response.read", "runtime.cancel"}:
            return request.failure(
                "CAPABILITY_UNAVAILABLE",
                "The qualified local Dream transport is unavailable for this mobile target.",
            )
        return request.failure("FORBIDDEN", "The method is owned by the native host.")
