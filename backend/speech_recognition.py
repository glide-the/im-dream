"""Deferred speech-recognition compatibility boundary.

The legacy implementation embedded a third-party credential and exposed an
unauthenticated WebSocket. ASR Gateway integration is outside the current
Token-only release, so this module intentionally performs no provider call and
stores no credential. A future ASR project must add its own threat model,
server-side secret provider, canonical-user authentication, limits and audit.
"""

from fastapi import WebSocket


DEFERRED_ASR_CLOSE_CODE = 1008


async def init_speech_recognition(websocket: WebSocket) -> None:
    """Fail closed without accepting audio or contacting a provider."""

    await websocket.close(
        code=DEFERRED_ASR_CLOSE_CODE,
        reason="Speech recognition is not enabled",
    )
