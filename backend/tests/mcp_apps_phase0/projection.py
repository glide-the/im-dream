# [Input] One bounded Apps-aware tool result envelope containing only non-sensitive fixture data.
# [Output] Existing Chat tool-invocation part preserving routing, call identity, input, and full result.
# [Pos] Phase 0 PoC helper; demonstrates schema compatibility without becoming production code.
# [Sync] 2026-09-04: add strict test-only Apps projection and sensitive-key rejection.

from __future__ import annotations

from copy import deepcopy
from typing import Any


_SENSITIVE_KEYS = {
    "authorization",
    "cookie",
    "credential",
    "credentials",
    "env",
    "headers",
    "password",
    "refresh_token",
    "secret",
    "stdio_command",
    "token",
    "upstream_url",
    "url",
}


def _reject_sensitive_keys(value: Any, *, path: str = "root") -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized = str(key).strip().lower().replace("-", "_")
            if normalized in _SENSITIVE_KEYS:
                raise ValueError(f"sensitive Apps projection key rejected at {path}.{key}")
            _reject_sensitive_keys(nested, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _reject_sensitive_keys(nested, path=f"{path}[{index}]")


def build_phase0_chat_part(
    *,
    server_ref: str,
    tool_name: str,
    tool_call_id: str,
    tool_input: dict[str, Any],
    tool_result: dict[str, Any],
) -> dict[str, Any]:
    """Build one test-only projection into the existing JSON ``parts`` column."""

    identifiers = (server_ref, tool_name, tool_call_id)
    if any(not isinstance(value, str) or not value.strip() for value in identifiers):
        raise ValueError("Apps projection identifiers must be non-empty strings")
    envelope = {
        "type": "tool-invocation",
        "toolInvocation": {
            "serverRef": server_ref,
            "toolName": tool_name,
            "toolCallId": tool_call_id,
            "input": deepcopy(tool_input),
            "result": deepcopy(tool_result),
        },
    }
    _reject_sensitive_keys(envelope)
    return envelope
