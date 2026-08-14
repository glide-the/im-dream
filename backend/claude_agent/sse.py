"""Shared Server-Sent Events encoding and HTTP response policy.

The public Claude Agent protocol keeps its event discriminator inside the JSON
payload (``data: {"type": ...}``) for backwards compatibility.  This module
owns only framing and transport headers; SDK message normalization stays in the
runner/service layers.
"""
from __future__ import annotations

import json
from collections.abc import AsyncIterable, Iterable
from typing import Any

from fastapi.responses import StreamingResponse


SSE_RESPONSE_HEADERS: dict[str, str] = {
    "Cache-Control": "no-cache, no-transform",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


def encode_json_sse(event_type: str, data: dict[str, Any]) -> str:
    """Encode one backwards-compatible JSON SSE frame.

    ``json.dumps`` escapes embedded newlines, so arbitrary Unicode, quotes and
    multiline text remain one valid SSE ``data`` field.  ``ensure_ascii=False``
    keeps captured raw frames readable without changing JSON semantics.
    """

    payload = json.dumps(
        {"type": event_type, **data},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return f"data: {payload}\n\n"


def streaming_sse_response(
    content: AsyncIterable[str | bytes] | Iterable[str | bytes],
) -> StreamingResponse:
    """Return a non-buffered UTF-8 SSE response with the shared header policy."""

    return StreamingResponse(
        content,
        media_type="text/event-stream",
        headers=dict(SSE_RESPONSE_HEADERS),
    )
