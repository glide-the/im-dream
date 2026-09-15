# [Input] Authenticated launch command, Admin actor/client and request-scoped Runtime port.
# [Output] Public launch context or closed route error while retaining Dream workflow execution.
# [Pos] Dream HTTP application boundary; creates no authentication or database authority.
# [Sync] 2026-09-16: compose launch only from Admin DTO clients; remove Dream database ownership.
"""HTTP application boundary for starting one Dream run."""

from __future__ import annotations

from typing import Any

try:
    from services.errors.error_registry import ApiRouteError
    from services.admin_data.client import AdminDataClient
    from services.admin_data.errors import AdminDataError
    from services.admin_data.request_auth import AdminRequestActor
    from services.story_workspace.dream_launch_infrastructure import (
        DreamLaunchApplicationError,
        DreamLaunchRuntimePort,
        DreamLaunchTaskRegistry,
        build_dream_launch_application_service,
    )
    from services.story_workspace.dream_launch_application_service import (
        DreamLaunchIdempotencyConflict,
        DreamLaunchProvenanceError,
    )
    from story_workspace.contracts import (
        StoryWorkspaceDreamLaunchCommand,
        StoryWorkspaceDreamRunContext,
    )
except ModuleNotFoundError:  # Support package imports from repository root.
    from backend.services.errors.error_registry import ApiRouteError
    from backend.services.admin_data.client import AdminDataClient
    from backend.services.admin_data.errors import AdminDataError
    from backend.services.admin_data.request_auth import AdminRequestActor
    from backend.services.story_workspace.dream_launch_infrastructure import (
        DreamLaunchApplicationError,
        DreamLaunchRuntimePort,
        DreamLaunchTaskRegistry,
        build_dream_launch_application_service,
    )
    from backend.services.story_workspace.dream_launch_application_service import (
        DreamLaunchIdempotencyConflict,
        DreamLaunchProvenanceError,
    )
    from backend.story_workspace.contracts import (
        StoryWorkspaceDreamLaunchCommand,
        StoryWorkspaceDreamRunContext,
    )


class DreamLaunchEndpointService:
    """Authenticate-adjacent application boundary used only by the launch route."""

    def __init__(
        self,
        *,
        task_registry: DreamLaunchTaskRegistry | None = None,
    ) -> None:
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
        admin_client: AdminDataClient,
        admin_actor: AdminRequestActor,
        runtime_port: DreamLaunchRuntimePort,
    ) -> StoryWorkspaceDreamRunContext:
        try:
            service = build_dream_launch_application_service(
                admin_client,
                actor=admin_actor,
                workspace_id=actor["workspace_id"],
                runtime_port=runtime_port,
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
        except AdminDataError as exc:
            raise ApiRouteError(exc.code, status_code=exc.status_code) from exc
        except PermissionError as exc:
            raise ApiRouteError("WORKFLOW_PERMISSION_DENIED", status_code=403) from exc


_DREAM_LAUNCH_ENDPOINT_SERVICE = DreamLaunchEndpointService()


def get_dream_launch_endpoint_service() -> DreamLaunchEndpointService:
    return _DREAM_LAUNCH_ENDPOINT_SERVICE


__all__ = [
    "DreamLaunchEndpointService",
    "get_dream_launch_endpoint_service",
]
