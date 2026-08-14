"""HTTP application boundary for starting one Dream run."""

from __future__ import annotations

from typing import Any, Callable

import database

try:
    from services.errors.error_registry import ApiRouteError
    from services.story_workspace.dream_launch_infrastructure import (
        DreamLaunchApplicationError,
        DreamLaunchTaskRegistry,
        build_dream_launch_application_service,
    )
    from services.story_workspace.dream_launch_application_service import (
        DreamLaunchIdempotencyConflict,
        DreamLaunchProvenanceError,
    )
    from services.story_workspace.preflight_builder import (
        StoryWorkspacePreflightServiceBuilder,
    )
    from services.story_workspace.workflow_security import (
        story_workspace_workflow_token_secret,
    )
    from services.workflow.run_service import WorkflowRunError
    from story_workspace.contracts import (
        StoryWorkspaceDreamLaunchCommand,
        StoryWorkspaceDreamRunContext,
    )
except ModuleNotFoundError:  # Support package imports from repository root.
    from backend.services.errors.error_registry import ApiRouteError
    from backend.services.story_workspace.dream_launch_infrastructure import (
        DreamLaunchApplicationError,
        DreamLaunchTaskRegistry,
        build_dream_launch_application_service,
    )
    from backend.services.story_workspace.dream_launch_application_service import (
        DreamLaunchIdempotencyConflict,
        DreamLaunchProvenanceError,
    )
    from backend.services.story_workspace.preflight_builder import (
        StoryWorkspacePreflightServiceBuilder,
    )
    from backend.services.story_workspace.workflow_security import (
        story_workspace_workflow_token_secret,
    )
    from backend.services.workflow.run_service import WorkflowRunError
    from backend.story_workspace.contracts import (
        StoryWorkspaceDreamLaunchCommand,
        StoryWorkspaceDreamRunContext,
    )


class DreamLaunchEndpointService:
    """Authenticate-adjacent application boundary used only by the launch route."""

    def __init__(
        self,
        *,
        db_factory: Callable[[], Any] = database.get_db,
        task_registry: DreamLaunchTaskRegistry | None = None,
    ) -> None:
        self._db_factory = db_factory
        self._task_registry = task_registry or DreamLaunchTaskRegistry()

    def start(self) -> None:
        self._task_registry.start()

    async def aclose(self) -> None:
        await self._task_registry.aclose()

    def diagnostics(self) -> dict[str, int]:
        return self._task_registry.diagnostics()

    async def start_dream_run(
        self,
        request: StoryWorkspaceDreamLaunchCommand,
        *,
        actor: dict[str, str],
    ) -> StoryWorkspaceDreamRunContext:
        db = self._db_factory()
        try:
            token_secret = story_workspace_workflow_token_secret()
            preflight_service = StoryWorkspacePreflightServiceBuilder(
                db,
                actor,
                token_secret=token_secret,
            ).build()
            service = build_dream_launch_application_service(
                db,
                preflight_service=preflight_service,
                token_secret=token_secret,
                launch_task_registry=self._task_registry,
            )
            return await service.launch(
                request,
                actor_id=actor["actor_id"],
                workspace_id=actor["workspace_id"],
            )
        except DreamLaunchIdempotencyConflict as exc:
            raise ApiRouteError("IDEMPOTENCY_CONFLICT", status_code=409) from exc
        except DreamLaunchProvenanceError as exc:
            raise ApiRouteError("DECK_RUNTIME_CONFIG_INVALID", status_code=409) from exc
        except DreamLaunchApplicationError as exc:
            raise ApiRouteError(exc.code, status_code=exc.status_code) from exc
        except WorkflowRunError as exc:
            self._raise_run_error(exc)
        except PermissionError as exc:
            raise ApiRouteError("WORKFLOW_PERMISSION_DENIED", status_code=403) from exc
        finally:
            db.close()

    @staticmethod
    def _raise_run_error(exc: WorkflowRunError) -> None:
        mapping = {
            "IDEMPOTENCY_CONFLICT": ("IDEMPOTENCY_CONFLICT", 409),
            "ILLEGAL_RUN_TRANSITION": ("WORKFLOW_STEP_FAILED", 409),
            "WORKFLOW_RUN_NOT_FOUND": ("AGENT_EXECUTION_FAILED", 404),
            "PREFLIGHT_NOT_FOUND_OR_NOT_AUTHORIZED": (
                "WORKFLOW_PERMISSION_DENIED",
                404,
            ),
            "PREFLIGHT_TOKEN_INVALID": ("WORKFLOW_PERMISSION_DENIED", 409),
            "PREFLIGHT_TOKEN_EXPIRED": ("DECK_RUNTIME_CONFIG_UNAVAILABLE", 409),
            "PREFLIGHT_TOKEN_REPLAYED": ("IDEMPOTENCY_CONFLICT", 409),
            "RETRY_SOURCE_MISMATCH": ("CONFIG_VERSION_DRIFT", 409),
        }
        code, status = mapping.get(exc.code, ("AGENT_EXECUTION_FAILED", 422))
        raise ApiRouteError(code, status_code=status) from exc


_DREAM_LAUNCH_ENDPOINT_SERVICE = DreamLaunchEndpointService()


def get_dream_launch_endpoint_service() -> DreamLaunchEndpointService:
    return _DREAM_LAUNCH_ENDPOINT_SERVICE


__all__ = [
    "DreamLaunchEndpointService",
    "get_dream_launch_endpoint_service",
]
