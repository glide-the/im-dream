"""Compatibility import for the protocol-neutral Agent event model.

The implementation is outside this package so Dream adapters can import it
while the Claude runner is initializing without creating a package cycle.
"""

from agent_stream_events import (
    TRANSPORT_KEEPALIVE,
    NormalizedAgentEvent,
    coerce_normalized_event,
    normalized_event_from_legacy_chat_frame,
)

__all__ = [
    "TRANSPORT_KEEPALIVE",
    "NormalizedAgentEvent",
    "coerce_normalized_event",
    "normalized_event_from_legacy_chat_frame",
]
