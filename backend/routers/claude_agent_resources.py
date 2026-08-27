# [Input] Consume the process-local Claude Agent diagnostics singleton and dedicated bearer token env.
# [Output] Register a constant-time authenticated, read-only resource diagnostics endpoint.
# [Pos] Internal Admin-to-Dream resource diagnostics route; no user auth, database, or process control.
# [Sync] 2026-08-27: add GET /api/internal/claude-agent/resources with a closed response DTO.

"""Internal read-only Claude Agent resource diagnostics route."""
from __future__ import annotations

import hmac
import os

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from agent_factory import claude_agent_resource_diagnostics
from claude_agent.resource_diagnostics import ClaudeAgentResourceDiagnosticsDTO


router = APIRouter()
_bearer = HTTPBearer(auto_error=False)


def _require_diagnostics_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> None:
    expected = (os.getenv("INK_AGENT_DIAGNOSTICS_TOKEN") or "").strip()
    expected_bytes = expected.encode("utf-8")
    if len(expected_bytes) < 32:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Claude Agent diagnostics authentication is not configured.",
        )
    presented = credentials.credentials if credentials is not None else ""
    if not hmac.compare_digest(presented.encode("utf-8"), expected_bytes):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid diagnostics credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get(
    "/api/internal/claude-agent/resources",
    response_model=ClaudeAgentResourceDiagnosticsDTO,
    dependencies=[Depends(_require_diagnostics_token)],
)
async def get_claude_agent_resources() -> ClaudeAgentResourceDiagnosticsDTO:
    """Return a closed process-level snapshot without business identifiers."""

    return claude_agent_resource_diagnostics.snapshot()
