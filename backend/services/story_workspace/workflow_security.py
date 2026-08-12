"""Server-owned Story Workspace workflow security configuration."""

from __future__ import annotations

import os

try:
    from services.errors.error_registry import ApiRouteError
except ModuleNotFoundError:  # Support package imports from repository root.
    from backend.services.errors.error_registry import ApiRouteError


def story_workspace_workflow_token_secret() -> str:
    """Return the server-owned Workflow token secret for application services."""

    explicit = os.getenv("INK_WORKFLOW_TOKEN_SECRET") or os.getenv("JWT_SECRET")
    if explicit and len(explicit.encode("utf-8")) >= 32:
        return explicit
    raise ApiRouteError("DECK_RUNTIME_CONFIG_UNAVAILABLE", status_code=503)


__all__ = ["story_workspace_workflow_token_secret"]
