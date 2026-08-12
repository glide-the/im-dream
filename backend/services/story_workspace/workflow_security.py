"""Server-owned Story Workspace workflow security configuration."""

from __future__ import annotations

import os

try:
    from services.errors.error_registry import ApiRouteError
except ModuleNotFoundError:  # Support package imports from repository root.
    from backend.services.errors.error_registry import ApiRouteError


_DEVELOPMENT_ENVIRONMENTS = {"development", "dev", "test", "testing"}
_DEV_TOKEN_SECRET = "ink-dream-development-workflow-token-secret-v1"


def story_workspace_workflow_token_secret() -> str:
    """Return the server-owned Workflow token secret for application services."""

    explicit = os.getenv("INK_WORKFLOW_TOKEN_SECRET") or os.getenv("JWT_SECRET")
    if explicit and len(explicit.encode("utf-8")) >= 32:
        return explicit
    environment = os.getenv("INK_ENVIRONMENT", "unknown").strip().lower()
    if environment in _DEVELOPMENT_ENVIRONMENTS:
        return _DEV_TOKEN_SECRET
    raise ApiRouteError("DECK_RUNTIME_CONFIG_UNAVAILABLE", status_code=503)


__all__ = ["story_workspace_workflow_token_secret"]
