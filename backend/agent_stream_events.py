"""Protocol-neutral events shared without importing the ``claude_agent`` package.

This module deliberately lives at the backend root.  Dream tools are imported
while the Claude runner package is still initializing, so a neutral model must
not trigger ``claude_agent.__init__`` and recursively import the runner.

It does not replace ``ClaudeAgentRunner._process_message``.  SDK message
classification, tool policy, usage aggregation, error handling, cancellation,
and business callbacks remain owned by the runner; this model begins only after
those callbacks cross into the service/EventBus boundary.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping


_WIRE_VERSION = 1
TRANSPORT_KEEPALIVE = "transport-keepalive"


@dataclass(frozen=True, slots=True)
class NormalizedAgentEvent:
    """One validated, protocol-neutral Agent event."""

    type: str
    data: Mapping[str, Any]

    def __post_init__(self) -> None:
        event_type = self.type.strip() if isinstance(self.type, str) else ""
        if not event_type:
            raise ValueError("normalized Agent event type must be non-empty")
        payload = dict(self.data)
        json.dumps(
            {"type": event_type, **payload},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        object.__setattr__(self, "type", event_type)
        object.__setattr__(self, "data", payload)

    @classmethod
    def create(
        cls,
        event_type: str,
        data: Mapping[str, Any] | None = None,
    ) -> "NormalizedAgentEvent":
        return cls(event_type, data or {})

    @classmethod
    def keepalive(cls) -> "NormalizedAgentEvent":
        return cls(TRANSPORT_KEEPALIVE, {})

    @property
    def is_keepalive(self) -> bool:
        return self.type == TRANSPORT_KEEPALIVE

    def payload(self) -> dict[str, Any]:
        return {"type": self.type, **dict(self.data)}

    def to_wire_json(self) -> str:
        """Serialize for Redis/internal persistence, not browser SSE."""

        return json.dumps(
            {"version": _WIRE_VERSION, "type": self.type, "data": dict(self.data)},
            ensure_ascii=False,
            separators=(",", ":"),
        )

    @classmethod
    def from_wire_json(cls, raw: str) -> "NormalizedAgentEvent":
        try:
            value = json.loads(raw)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid normalized Agent event wire payload") from exc
        if not isinstance(value, dict) or value.get("version") != _WIRE_VERSION:
            raise ValueError("unsupported normalized Agent event wire payload")
        data = value.get("data")
        if not isinstance(data, dict):
            raise ValueError("normalized Agent event data must be an object")
        return cls.create(str(value.get("type") or ""), data)


def normalized_event_from_legacy_chat_frame(raw: str) -> NormalizedAgentEvent:
    """Decode a pre-separation Chat SSE frame for rolling-upgrade replay only."""

    if raw.lstrip().startswith(":"):
        return NormalizedAgentEvent.keepalive()
    data_lines: list[str] = []
    for line in raw.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if not line or line.startswith(":"):
            continue
        field, separator, value = line.partition(":")
        if field != "data":
            continue
        if separator and value.startswith(" "):
            value = value[1:]
        data_lines.append(value)
    if not data_lines:
        raise ValueError("legacy Chat SSE frame has no data field")
    try:
        payload = json.loads("\n".join(data_lines))
    except (TypeError, ValueError) as exc:
        raise ValueError("legacy Chat SSE frame has invalid JSON") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("type"), str):
        raise ValueError("legacy Chat SSE frame has no event type")
    return NormalizedAgentEvent.create(
        payload["type"],
        {key: value for key, value in payload.items() if key != "type"},
    )


def coerce_normalized_event(value: object) -> NormalizedAgentEvent:
    """Normalize EventBus input while retaining rolling-upgrade compatibility."""

    if isinstance(value, NormalizedAgentEvent):
        return value
    if isinstance(value, str):
        return normalized_event_from_legacy_chat_frame(value)
    if isinstance(value, Mapping):
        event_type = value.get("type")
        if isinstance(event_type, str):
            return NormalizedAgentEvent.create(
                event_type,
                {key: item for key, item in value.items() if key != "type"},
            )
    raise TypeError("EventBus accepts only NormalizedAgentEvent values")
