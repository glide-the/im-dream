#!/usr/bin/env python3
# [Sync] 2026-09-16: remove the unused legacy Run application factory; public Run routes stay on Admin DTOs.
# [Sync] 2026-09-16: compose Guidance Agent turns with the exact Workflow/Deck/Admin persistence owner.
# [Sync] 2026-09-16: inject one Admin DTO client/actor into the database-free launch composition.
# [Sync] 2026-09-16: route confirmation fact/submit through Registry120 with current actor and Run DTOs.
# [Sync] 2026-09-16: route Story Workspace Artifact authority/index access through Registry185-191 DTOs.
# [Input] Authenticated users, strict Admin Story Workspace DTO consumers, workflow services, and REST requests.
# [Output] Publish user-scoped Story Workspace product, workflow, artifact, review, and catalog routes.
# [Pos] Story Workspace baseline FastAPI router in backend/routers.
# [Sync] 2026-09-15: read Preflight through Admin OAuth without default Workspace or Dream SQL.
# [Sync] 2026-09-15: execute Preflight through Admin; existing default Workspace lookup remains pending.
# [Sync] 2026-09-15: consume full Run read/create/retry domains while retaining default Workspace SQL.
# [Sync] 2026-09-15: replace Workflow ingress default SQL with OAuth-write Admin ensure; internal agent-output stays separate.
# [Sync] 2026-09-15: cancel Run through Admin with the original reason/model/errors; Agent cancel remains owned by its service.
# [Sync] 2026-09-15: reuse the shared default Workspace resolver with Deck Plugin and binding ingress.
# [Sync] 2026-09-15: route Story/Character/Scene review through Registry111 and remove those Dream SQL transactions.
# [Sync] 2026-09-15: route catalog browse/edit through Registry114 DTO/ORM and remove this router's Dream SQL.
# [Sync] 2026-09-15: persist Guidance through Registry115 and retain only same-Thread Runtime dispatch in Dream.
# [Sync] 2026-09-16: route confirmation facts and persistence through Registry120 DTO clients.
# [Sync] 2026-09-02: expose a body-free Episode index and explicit registry-member reads.

"""Authenticated, user-scoped REST API for the Story Workspace baseline."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional, Protocol

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from story_workspace.contracts import (
    STORY_WORKSPACE_REVIEW_NOTES_MAX_LENGTH,
    StoryWorkspaceAgentStoryPayload,
    StoryWorkspaceBatchAction,
    StoryWorkspaceCharacterPatch,
    StoryWorkspaceDreamConfirmationCommand,
    StoryWorkspaceDreamLaunchAccepted,
    StoryWorkspaceDreamLaunchCommand,
    StoryWorkspaceGuidanceCommandPayload,
    StoryWorkspaceResourceType,
    StoryWorkspaceScenePatch,
    StoryWorkspaceStoryPatch,
    StoryWorkspaceStoryIndexReconcileCommand,
    StoryWorkspaceWorkspacePatch,
)
from .deps import SafeRequestValidationRoute, get_admin_request_auth, get_current_user, invoke_admin_operation, resolve_admin_default_workspace
from services.admin_data.errors import AdminDataError
from services.admin_data.preflight_data import AdminPreflightData, PreflightExecutionInputDTO, PreflightInputDTO
from services.admin_data.request_auth import AdminRequestActor, AdminRequestAuth
from services.admin_data.run_data import AdminRunData, RunCancelInputDTO, RunCreateInputDTO, RunLookupInputDTO, RunRetryInputDTO
from services.admin_data.story_workspace_output_data import (
    AdminStoryWorkspaceOutputData,
    StoryWorkspaceOutputInputDTO,
)
from services.admin_data.story_workspace_review_data import (
    AdminStoryWorkspaceReviewData,
    StoryWorkspaceReviewBatchInputDTO,
    StoryWorkspaceReviewTransitionInputDTO,
)
from services.admin_data.story_workspace_catalog_data import (
    AdminStoryWorkspaceCatalogData,
    StoryWorkspaceCatalogPatchInputDTO,
    StoryWorkspaceCatalogReadInputDTO,
    StoryWorkspaceCatalogWorkspaceInputDTO,
)
from services.admin_data.story_workspace_guidance_data import (
    AdminStoryWorkspaceGuidanceData,
    StoryWorkspaceGuidanceInputDTO,
)
from services.admin_data.story_workspace_confirmation_data import (
    AdminStoryWorkspaceConfirmationData,
)
from services.admin_data.story_workspace_artifact_data import (
    AdminStoryWorkspaceArtifactData,
)
from services.admin_data.deck_plugin_binding_data import AdminDeckPluginBindingData
from services.story_workspace.guidance_service import (
    build_thread_turn_dispatcher,
    prepare_guidance_turn_owner,
)
from services.story_workspace.dream_launch_runtime import AdminDreamLaunchRuntime

try:
    from services.errors.error_registry import ApiRouteError, WORKFLOW_RUN_ROUTE_ERRORS, build_error_payload, workflow_run_route_error
    from services.deck.story_workflow_application import (
        get_dream_artifact_application_service,
        get_dream_confirmation_application_service,
    )
    from services.story_workspace.dream_launch_endpoint_service import (
        get_dream_launch_endpoint_service,
    )
except ModuleNotFoundError:
    from backend.services.errors.error_registry import ApiRouteError, WORKFLOW_RUN_ROUTE_ERRORS, build_error_payload, workflow_run_route_error
    from backend.services.deck.story_workflow_application import (
        get_dream_artifact_application_service,
        get_dream_confirmation_application_service,
    )
    from backend.services.story_workspace.dream_launch_endpoint_service import (
        get_dream_launch_endpoint_service,
    )


router = APIRouter(prefix="/api/story-workspace", tags=["story-workspace"])
logger = logging.getLogger(__name__)
_STORY_INDEX_ROUTE_ERROR_STATUSES: dict[str, frozenset[int]] = {
    "WORKFLOW_PERMISSION_DENIED": frozenset({403, 404}),
    "artifact_missing": frozenset({404}),
    "story_index_revision_conflict": frozenset({409}),
    "story_index_conflict": frozenset({409}),
    "story_index_invalid_artifact": frozenset({422}),
    "story_index_schema_unavailable": frozenset({503}),
    "story_index_database_unavailable": frozenset({503}),
    "story_index_write_failed": frozenset({503}),
}

class _ReviewActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_notes: Optional[str] = Field(
        default=None,
        max_length=STORY_WORKSPACE_REVIEW_NOTES_MAX_LENGTH,
    )


class _BatchReviewRequest(_ReviewActionRequest):
    action: StoryWorkspaceBatchAction
    ids: list[str] = Field(min_length=1, max_length=100)
    resource_type: StoryWorkspaceResourceType

    @field_validator("ids")
    @classmethod
    def validate_ids(cls, ids: list[str]) -> list[str]:
        normalized = [resource_id.strip() for resource_id in ids]
        if any(not resource_id for resource_id in normalized):
            raise ValueError("ids must not contain blank values")
        if len(set(normalized)) != len(normalized):
            raise ValueError("ids must contain unique values")
        return normalized


class _WorkflowPreflightRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    deck_id: str = Field(min_length=1)
    binding_revision: int = Field(ge=0)
    input_data: dict[str, Any] = Field(alias="input")


class _WorkflowRunCreateRequest(BaseModel):
    """Client input intentionally excludes every frozen provenance field."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    workflow_preflight_id: str = Field(pattern=r"^pf_[0-9a-f]{32}$")
    preflight_token: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1, max_length=255)
    source_voice_thread_id: str | None = None
    source_message_id: str | None = None
    source_message_time: str | None = None


class _WorkflowRunRetryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    workflow_preflight_id: str = Field(pattern=r"^pf_[0-9a-f]{32}$")
    preflight_token: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1, max_length=255)


class _WorkflowRunCancelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    reason: str = Field(default="Cancelled from Dream", min_length=1, max_length=500)


class DreamLaunchEndpoint(Protocol):
    async def start_dream_run(
        self,
        request: StoryWorkspaceDreamLaunchCommand,
        *,
        actor: dict[str, str],
        admin_client: Any,
        admin_actor: AdminRequestActor,
        runtime_port: AdminDreamLaunchRuntime,
    ) -> Any: ...


class DreamArtifactService(Protocol):
    async def get_dream_files(
        self,
        workflow_run_id: str,
        *,
        actor: dict[str, str],
        artifact_data: AdminStoryWorkspaceArtifactData,
        access_token: str,
    ) -> Any: ...

    async def get_episode_artifacts(
        self,
        workflow_run_id: str,
        *,
        actor: dict[str, str],
        artifact_data: AdminStoryWorkspaceArtifactData,
        access_token: str,
        episode_id: str | None = None,
    ) -> Any: ...

    async def get_episode_index(
        self,
        workflow_run_id: str,
        *,
        actor: dict[str, str],
        artifact_data: AdminStoryWorkspaceArtifactData,
        access_token: str,
    ) -> Any: ...

    async def get_story_index(
        self,
        workflow_run_id: str,
        *,
        actor: dict[str, str],
        artifact_data: AdminStoryWorkspaceArtifactData,
        access_token: str,
    ) -> Any: ...

    async def reconcile_story_index(
        self,
        workflow_run_id: str,
        request: StoryWorkspaceStoryIndexReconcileCommand,
        *,
        actor: dict[str, str],
        artifact_data: AdminStoryWorkspaceArtifactData,
        access_token: str,
        if_match: str,
    ) -> Any: ...

    async def list_dream_runs(
        self,
        *,
        actor: dict[str, str],
        artifact_data: AdminStoryWorkspaceArtifactData,
        access_token: str,
    ) -> Any: ...


class DreamConfirmationService(Protocol):
    async def submit_dream_confirmation(
        self,
        workflow_run_id: str,
        request: StoryWorkspaceDreamConfirmationCommand,
        *,
        actor: dict[str, str],
        run_data: AdminRunData,
        confirmation_data: AdminStoryWorkspaceConfirmationData,
        access_token: str,
    ) -> Any: ...


def get_dream_artifact_service() -> DreamArtifactService:
    return get_dream_artifact_application_service()


def get_dream_confirmation_service() -> DreamConfirmationService:
    return get_dream_confirmation_application_service()


async def _story_workflow_current_user(
    current_user: dict[str, Any] = Depends(get_current_user),
    owner: AdminRequestAuth = Depends(get_admin_request_auth),
) -> dict[str, Any]:
    return await resolve_admin_default_workspace(current_user, owner)


def _workflow_actor(current_user: dict[str, Any]) -> dict[str, str]:
    workspace_id = current_user.get("workspace_id")
    if workspace_id is None:
        raise ApiRouteError("WORKFLOW_PERMISSION_DENIED", status_code=403)
    return {
        "workspace_id": str(workspace_id),
        "actor_id": str(current_user["user_id"]),
    }


def _workflow_json(value: Any, *, by_alias: bool = False) -> Any:
    return (
        value.model_dump(mode="json", by_alias=by_alias)
        if hasattr(value, "model_dump")
        else value
    )


async def _workflow_call(awaitable: Any, *, by_alias: bool = False) -> Any:
    try:
        return _workflow_json(await awaitable, by_alias=by_alias)
    except ApiRouteError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content=build_error_payload(
                exc.code,
                operation_id=exc.operation_id,
                run_id=exc.run_id,
                failed_check=exc.failed_check,
            ),
        )
    except Exception:
        logger.exception("Story Workspace workflow call failed closed")
        return JSONResponse(
            status_code=503,
            content=build_error_payload("DECK_RUNTIME_CONFIG_UNAVAILABLE"),
        )


async def _story_index_call(awaitable: Any) -> Any:
    """Serialize only the fixed Story index error vocabulary."""

    try:
        return _workflow_json(await awaitable, by_alias=True)
    except ApiRouteError as exc:
        allowed_statuses = _STORY_INDEX_ROUTE_ERROR_STATUSES.get(exc.code)
        if allowed_statuses is None or exc.status_code not in allowed_statuses:
            logger.error("Story index application service returned a non-public error")
            return JSONResponse(
                status_code=503,
                content=build_error_payload("story_index_database_unavailable"),
            )
        return JSONResponse(
            status_code=exc.status_code,
            content=build_error_payload(exc.code),
        )
    except Exception:
        logger.exception("Story index request failed")
        return JSONResponse(
            status_code=503,
            content=build_error_payload("story_index_database_unavailable"),
        )


def _story_catalog_data(
    owner: AdminRequestAuth = Depends(get_admin_request_auth),
) -> AdminStoryWorkspaceCatalogData:
    return AdminStoryWorkspaceCatalogData(owner.client)


def _csv_values(raw: Optional[str]) -> list[str]:
    if not raw:
        return []
    return [value.strip() for value in raw.split(",") if value.strip()]


def _story_catalog_error(exc: AdminDataError, request_id: str) -> JSONResponse:
    if not exc.outcome_unknown:
        if exc.code == "STORY_WORKSPACE_CATALOG_NOT_FOUND" and exc.status_code == 404:
            return JSONResponse(status_code=404, content={"detail": "Resource not found"})
        if exc.code in {"INPUT_INVALID", "ADMIN_OPERATION_INPUT_INVALID"} and exc.status_code == 400:
            return JSONResponse(status_code=400, content={"detail": "Invalid Story Workspace request"})
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": {
            "error_code": exc.code,
            "request_id": exc.request_id or request_id,
            "outcome_unknown": exc.outcome_unknown,
        }},
    )


def _catalog_input(model, value: dict[str, Any], detail: str):
    try:
        return model.model_validate(value)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=detail) from exc


@router.get("/workspace")
async def get_workspace(
    current_user: dict[str, Any] = Depends(get_current_user),
    data: AdminStoryWorkspaceCatalogData = Depends(_story_catalog_data),
) -> Any:
    input_dto = StoryWorkspaceCatalogWorkspaceInputDTO.model_validate({"action": "ensure"})
    result = await invoke_admin_operation(
        current_user, data.workspace_recovering, input_dto,
        error_handler=_story_catalog_error,
    )
    return result if isinstance(result, JSONResponse) else result.item.model_dump(mode="json")


@router.patch("/workspace/{workspace_id}")
async def patch_workspace(
    workspace_id: str,
    patch: StoryWorkspaceWorkspacePatch,
    current_user: dict[str, Any] = Depends(get_current_user),
    data: AdminStoryWorkspaceCatalogData = Depends(_story_catalog_data),
) -> Any:
    values = patch.model_dump(exclude_unset=True)
    if not values:
        raise HTTPException(status_code=400, detail="At least one field is required")
    input_dto = _catalog_input(StoryWorkspaceCatalogWorkspaceInputDTO, {
        "action": "patch", "workspace_id": workspace_id, "patch": values,
    }, "Invalid Workspace patch")
    result = await invoke_admin_operation(
        current_user, data.workspace_recovering, input_dto,
        error_handler=_story_catalog_error,
    )
    return result if isinstance(result, JSONResponse) else result.item.model_dump(mode="json")


@router.get("/stories")
async def list_stories(
    q: Optional[str] = None,
    review_status: Optional[str] = None,
    status: Optional[str] = None,
    type: Optional[str] = None,
    sort: str = "updated_at",
    order: str = "desc",
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: dict[str, Any] = Depends(get_current_user),
    data: AdminStoryWorkspaceCatalogData = Depends(_story_catalog_data),
) -> Any:
    input_dto = _catalog_input(StoryWorkspaceCatalogReadInputDTO, {
        "view": "story_list", "q": q or None,
        "review_status": _csv_values(review_status), "status": _csv_values(status),
        "type": _csv_values(type), "sort": sort, "order": order.lower(),
        "page": page, "per_page": per_page,
    }, "Unsupported Story query")
    result = await invoke_admin_operation(current_user, data.read, input_dto, error_handler=_story_catalog_error)
    return result if isinstance(result, JSONResponse) else result.model_dump(mode="json", exclude={"view"})


@router.get("/stories/{story_id}")
async def get_story(
    story_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    data: AdminStoryWorkspaceCatalogData = Depends(_story_catalog_data),
) -> Any:
    input_dto = _catalog_input(StoryWorkspaceCatalogReadInputDTO, {
        "view": "story_detail", "resource_id": story_id,
    }, "Invalid Story identifier")
    result = await invoke_admin_operation(current_user, data.read, input_dto, error_handler=_story_catalog_error)
    return result if isinstance(result, JSONResponse) else result.item.model_dump(mode="json")


@router.patch("/stories/{story_id}")
async def patch_story(
    story_id: str,
    patch: StoryWorkspaceStoryPatch,
    current_user: dict[str, Any] = Depends(get_current_user),
    data: AdminStoryWorkspaceCatalogData = Depends(_story_catalog_data),
) -> Any:
    return await _patch_catalog_resource("story", story_id, patch.model_dump(exclude_unset=True), current_user, data)


@router.get("/characters")
async def list_characters(
    q: Optional[str] = None,
    review_status: Optional[str] = None,
    sort: str = "updated_at",
    order: str = "desc",
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: dict[str, Any] = Depends(get_current_user),
    data: AdminStoryWorkspaceCatalogData = Depends(_story_catalog_data),
) -> Any:
    input_dto = _catalog_input(StoryWorkspaceCatalogReadInputDTO, {
        "view": "character_list", "q": q or None,
        "review_status": _csv_values(review_status), "sort": sort, "order": order.lower(),
        "page": page, "per_page": per_page,
    }, "Unsupported Character query")
    result = await invoke_admin_operation(current_user, data.read, input_dto, error_handler=_story_catalog_error)
    return result if isinstance(result, JSONResponse) else result.model_dump(mode="json", exclude={"view"})


@router.get("/characters/{character_id}")
async def get_character(
    character_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    data: AdminStoryWorkspaceCatalogData = Depends(_story_catalog_data),
) -> Any:
    input_dto = _catalog_input(StoryWorkspaceCatalogReadInputDTO, {
        "view": "character_detail", "resource_id": character_id,
    }, "Invalid Character identifier")
    result = await invoke_admin_operation(current_user, data.read, input_dto, error_handler=_story_catalog_error)
    return result if isinstance(result, JSONResponse) else result.item.model_dump(mode="json")


@router.patch("/characters/{character_id}")
async def patch_character(
    character_id: str,
    patch: StoryWorkspaceCharacterPatch,
    current_user: dict[str, Any] = Depends(get_current_user),
    data: AdminStoryWorkspaceCatalogData = Depends(_story_catalog_data),
) -> Any:
    return await _patch_catalog_resource("character", character_id, patch.model_dump(exclude_unset=True), current_user, data)


@router.get("/scenes")
async def list_scenes(
    q: Optional[str] = None,
    review_status: Optional[str] = None,
    story_id: Optional[str] = None,
    sort: str = "updated_at",
    order: str = "desc",
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: dict[str, Any] = Depends(get_current_user),
    data: AdminStoryWorkspaceCatalogData = Depends(_story_catalog_data),
) -> Any:
    input_dto = _catalog_input(StoryWorkspaceCatalogReadInputDTO, {
        "view": "scene_list", "q": q or None, "review_status": _csv_values(review_status),
        "story_id": story_id or None, "sort": sort, "order": order.lower(),
        "page": page, "per_page": per_page,
    }, "Unsupported Scene query")
    result = await invoke_admin_operation(current_user, data.read, input_dto, error_handler=_story_catalog_error)
    return result if isinstance(result, JSONResponse) else result.model_dump(mode="json", exclude={"view"})


@router.get("/scenes/{scene_id}")
async def get_scene(
    scene_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    data: AdminStoryWorkspaceCatalogData = Depends(_story_catalog_data),
) -> Any:
    input_dto = _catalog_input(StoryWorkspaceCatalogReadInputDTO, {
        "view": "scene_detail", "resource_id": scene_id,
    }, "Invalid Scene identifier")
    result = await invoke_admin_operation(current_user, data.read, input_dto, error_handler=_story_catalog_error)
    return result if isinstance(result, JSONResponse) else result.item.model_dump(mode="json")


@router.patch("/scenes/{scene_id}")
async def patch_scene(
    scene_id: str,
    patch: StoryWorkspaceScenePatch,
    current_user: dict[str, Any] = Depends(get_current_user),
    data: AdminStoryWorkspaceCatalogData = Depends(_story_catalog_data),
) -> Any:
    return await _patch_catalog_resource("scene", scene_id, patch.model_dump(exclude_unset=True), current_user, data)


async def _patch_catalog_resource(
    resource_type: str,
    resource_id: str,
    values: dict[str, Any],
    current_user: dict[str, Any],
    data: AdminStoryWorkspaceCatalogData,
) -> Any:
    if not values:
        raise HTTPException(status_code=400, detail="At least one field is required")
    input_dto = _catalog_input(StoryWorkspaceCatalogPatchInputDTO, {
        "resource_type": resource_type, "resource_id": resource_id, "patch": values,
    }, "Invalid Story Workspace patch")
    result = await invoke_admin_operation(
        current_user, data.patch_recovering, input_dto, error_handler=_story_catalog_error,
    )
    return result if isinstance(result, JSONResponse) else result.item.model_dump(mode="json")


def _story_review_data(
    owner: AdminRequestAuth = Depends(get_admin_request_auth),
) -> AdminStoryWorkspaceReviewData:
    return AdminStoryWorkspaceReviewData(owner.client)


def _story_review_error(invalid_detail: str, *, batch: bool = False):
    def handle(exc: AdminDataError, request_id: str) -> JSONResponse:
        if not exc.outcome_unknown:
            if exc.code == "STORY_WORKSPACE_REVIEW_NOT_FOUND" and exc.status_code == 404:
                return JSONResponse(status_code=404, content={"detail": "Resource not found"})
            if exc.code == "STORY_WORKSPACE_REVIEW_STATE_INVALID" and exc.status_code == 409:
                return JSONResponse(status_code=400, content={"detail": invalid_detail})
            if batch and exc.code == "STORY_WORKSPACE_REVIEW_STATE_CHANGED" and exc.status_code == 409:
                return JSONResponse(
                    status_code=409,
                    content={"detail": "Review state changed during batch operation"},
                )
            if exc.code in {"INPUT_INVALID", "ADMIN_OPERATION_INPUT_INVALID"} and exc.status_code == 400:
                return JSONResponse(status_code=422, content={"detail": "Invalid review request"})
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": {"error_code": exc.code,
                "request_id": exc.request_id or request_id,
                "outcome_unknown": exc.outcome_unknown}},
        )

    return handle


async def _transition_story_review(
    *,
    resource_type: StoryWorkspaceResourceType,
    resource_id: str,
    action: StoryWorkspaceBatchAction,
    review_notes: str | None,
    current_user: dict[str, Any],
    data: AdminStoryWorkspaceReviewData,
) -> Any:
    try:
        input_dto = StoryWorkspaceReviewTransitionInputDTO(
            resource_type=resource_type.value,
            resource_id=resource_id,
            action=action.value,
            review_notes=review_notes,
        )
    except ValidationError:
        return JSONResponse(status_code=422, content={"detail": "Invalid review request"})
    invalid_detail = (
        "Item is already archived"
        if action == StoryWorkspaceBatchAction.ARCHIVE
        else "Item is not in pending review status"
    )
    result = await invoke_admin_operation(
        current_user,
        data.transition_recovering,
        input_dto,
        error_handler=_story_review_error(invalid_detail),
    )
    if isinstance(result, JSONResponse):
        return result
    return result.item.model_dump(mode="json")


@router.post("/stories/{story_id}/confirm")
async def confirm_story(
    story_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    data: AdminStoryWorkspaceReviewData = Depends(_story_review_data),
) -> Any:
    return await _transition_story_review(
        resource_type=StoryWorkspaceResourceType.STORY,
        resource_id=story_id,
        action=StoryWorkspaceBatchAction.CONFIRM,
        review_notes=None,
        current_user=current_user,
        data=data,
    )


@router.post("/stories/{story_id}/reject")
async def reject_story(
    story_id: str,
    body: Optional[_ReviewActionRequest] = None,
    current_user: dict[str, Any] = Depends(get_current_user),
    data: AdminStoryWorkspaceReviewData = Depends(_story_review_data),
) -> Any:
    return await _transition_story_review(
        resource_type=StoryWorkspaceResourceType.STORY,
        resource_id=story_id,
        action=StoryWorkspaceBatchAction.REJECT,
        review_notes=body.review_notes if body else None,
        current_user=current_user,
        data=data,
    )


@router.post("/stories/{story_id}/archive")
async def archive_story(
    story_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    data: AdminStoryWorkspaceReviewData = Depends(_story_review_data),
) -> Any:
    return await _transition_story_review(
        resource_type=StoryWorkspaceResourceType.STORY,
        resource_id=story_id,
        action=StoryWorkspaceBatchAction.ARCHIVE,
        review_notes=None,
        current_user=current_user,
        data=data,
    )


@router.post("/characters/{character_id}/confirm")
async def confirm_character(
    character_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    data: AdminStoryWorkspaceReviewData = Depends(_story_review_data),
) -> Any:
    return await _transition_story_review(
        resource_type=StoryWorkspaceResourceType.CHARACTER,
        resource_id=character_id,
        action=StoryWorkspaceBatchAction.CONFIRM,
        review_notes=None,
        current_user=current_user,
        data=data,
    )


@router.post("/characters/{character_id}/reject")
async def reject_character(
    character_id: str,
    body: Optional[_ReviewActionRequest] = None,
    current_user: dict[str, Any] = Depends(get_current_user),
    data: AdminStoryWorkspaceReviewData = Depends(_story_review_data),
) -> Any:
    return await _transition_story_review(
        resource_type=StoryWorkspaceResourceType.CHARACTER,
        resource_id=character_id,
        action=StoryWorkspaceBatchAction.REJECT,
        review_notes=body.review_notes if body else None,
        current_user=current_user,
        data=data,
    )


@router.post("/scenes/{scene_id}/confirm")
async def confirm_scene(
    scene_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    data: AdminStoryWorkspaceReviewData = Depends(_story_review_data),
) -> Any:
    return await _transition_story_review(
        resource_type=StoryWorkspaceResourceType.SCENE,
        resource_id=scene_id,
        action=StoryWorkspaceBatchAction.CONFIRM,
        review_notes=None,
        current_user=current_user,
        data=data,
    )


@router.post("/scenes/{scene_id}/reject")
async def reject_scene(
    scene_id: str,
    body: Optional[_ReviewActionRequest] = None,
    current_user: dict[str, Any] = Depends(get_current_user),
    data: AdminStoryWorkspaceReviewData = Depends(_story_review_data),
) -> Any:
    return await _transition_story_review(
        resource_type=StoryWorkspaceResourceType.SCENE,
        resource_id=scene_id,
        action=StoryWorkspaceBatchAction.REJECT,
        review_notes=body.review_notes if body else None,
        current_user=current_user,
        data=data,
    )


@router.post("/batch")
async def batch_review(
    body: _BatchReviewRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
    data: AdminStoryWorkspaceReviewData = Depends(_story_review_data),
) -> Any:
    try:
        input_dto = StoryWorkspaceReviewBatchInputDTO(
            resource_type=body.resource_type.value,
            ids=body.ids,
            action=body.action.value,
            review_notes=body.review_notes,
        )
    except ValidationError:
        return JSONResponse(status_code=422, content={"detail": "Invalid review request"})
    result = await invoke_admin_operation(
        current_user,
        data.batch_recovering,
        input_dto,
        error_handler=_story_review_error(
            "Item is not in pending review status", batch=True
        ),
    )
    if isinstance(result, JSONResponse):
        return result
    return result.model_dump(mode="json")


def _story_output_data(
    owner: AdminRequestAuth = Depends(get_admin_request_auth),
) -> AdminStoryWorkspaceOutputData:
    return AdminStoryWorkspaceOutputData(owner.client)


def _agent_story_output_error(
    exc: AdminDataError,
    request_id: str,
) -> JSONResponse:
    if not exc.outcome_unknown and (
        (exc.code == "ADMIN_OPERATION_INPUT_INVALID" and exc.status_code == 400)
        or (exc.code == "CHAT_THREAD_NOT_FOUND" and exc.status_code == 404)
    ):
        return JSONResponse(
            status_code=422,
            content={"detail": "Unable to persist Agent story output"},
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": {
                "error_code": exc.code,
                "request_id": exc.request_id or request_id,
                "outcome_unknown": exc.outcome_unknown,
            }
        },
    )


@router.post("/internal/agent-output")
async def receive_agent_story_output(
    body: StoryWorkspaceAgentStoryPayload,
    agent_session_id: Optional[str] = Header(None, alias="X-Agent-Session-Id"),
    current_user: dict[str, Any] = Depends(get_current_user),
    data: AdminStoryWorkspaceOutputData = Depends(_story_output_data),
) -> Any:
    """Persist one authenticated Chat Thread Story bundle through Admin."""

    if not agent_session_id or not agent_session_id.strip():
        raise HTTPException(status_code=400, detail="X-Agent-Session-Id is required")

    try:
        input_dto = StoryWorkspaceOutputInputDTO(
            thread_id=agent_session_id.strip(),
            story=body.model_dump(mode="json"),
        )
    except ValidationError:
        raise HTTPException(status_code=422, detail="Unable to persist Agent story output") from None
    result = await invoke_admin_operation(
        current_user,
        data.store_recovering,
        input_dto,
        error_handler=_agent_story_output_error,
    )
    if isinstance(result, JSONResponse):
        return result
    return {
        "story_id": result.story_id,
        "review_status": result.review_status,
        "character_ids": result.character_ids,
        "scene_ids": result.scene_ids,
    }


def _preflight_data(request: Request, current_user: dict = Depends(get_current_user)) -> AdminPreflightData:
    owner = getattr(request.app.state, "admin_request_auth", None)
    actor = current_user.get("_admin_actor")
    if not isinstance(owner, AdminRequestAuth) or not isinstance(actor, AdminRequestActor):
        raise HTTPException(status_code=503, detail="ADMIN_CONFIGURATION_INVALID")
    return AdminPreflightData(owner.client, canonical_user_id=actor.canonical_user_id)


class _PreflightExecutionRoute(SafeRequestValidationRoute):
    validation_error_detail = "Invalid Preflight request"


_preflight_execution_router = APIRouter(route_class=_PreflightExecutionRoute)


@_preflight_execution_router.post("/workflow-preflights", status_code=202)
async def create_workflow_preflight(
    request: _WorkflowPreflightRequest,
    current_user: dict[str, Any] = Depends(_story_workflow_current_user),
    data: AdminPreflightData = Depends(_preflight_data),
):
    try:
        actor = _workflow_actor(current_user)
    except ApiRouteError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content=build_error_payload(exc.code),
        )
    try:
        input_json = json.dumps(request.input_data, ensure_ascii=False, allow_nan=False, separators=(",", ":"), sort_keys=True)
        input_json.encode("utf-8")
        input_dto = PreflightExecutionInputDTO(workspace_id=actor["workspace_id"], deck_id=request.deck_id,
            binding_revision=request.binding_revision, input_json=input_json)
    except (ValueError, RecursionError):
        return JSONResponse(status_code=422, content={"detail": "Invalid Preflight request"})
    return await invoke_admin_operation(current_user, data.execute, input_dto)


router.include_router(_preflight_execution_router)


@router.post("/dream-runs/start", status_code=201)
async def story_workspace_start_dream_run(
    request: StoryWorkspaceDreamLaunchCommand,
    current_user: dict[str, Any] = Depends(_story_workflow_current_user),
    owner: AdminRequestAuth = Depends(get_admin_request_auth),
    launch_service: DreamLaunchEndpoint = Depends(get_dream_launch_endpoint_service),
):
    try:
        actor = _workflow_actor(current_user)
        admin_actor = current_user.get("_admin_actor")
        if not isinstance(owner, AdminRequestAuth) or not isinstance(
            admin_actor, AdminRequestActor
        ):
            raise ApiRouteError("ADMIN_CONFIGURATION_INVALID", status_code=503)
    except ApiRouteError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content=build_error_payload(exc.code),
        )

    async def accepted_response() -> StoryWorkspaceDreamLaunchAccepted:
        runtime_port = AdminDreamLaunchRuntime(
            AdminDeckPluginBindingData(owner.client),
            admin_actor.access_token,
        )
        context = await launch_service.start_dream_run(
            request,
            actor=actor,
            admin_client=owner.client,
            admin_actor=admin_actor,
            runtime_port=runtime_port,
        )
        return StoryWorkspaceDreamLaunchAccepted.from_context(context)

    return await _workflow_call(accepted_response(), by_alias=True)


def _artifact_data(
    owner: AdminRequestAuth = Depends(get_admin_request_auth),
    current_user: dict = Depends(get_current_user),
) -> AdminStoryWorkspaceArtifactData:
    actor = current_user.get("_admin_actor")
    if not isinstance(actor, AdminRequestActor):
        raise HTTPException(status_code=503, detail="ADMIN_CONFIGURATION_INVALID")
    return AdminStoryWorkspaceArtifactData(
        owner.client,
        canonical_user_id=actor.canonical_user_id,
    )


@router.get("/dream-runs")
async def story_workspace_list_dream_runs(
    current_user: dict[str, Any] = Depends(get_current_user),
    service: DreamArtifactService = Depends(get_dream_artifact_service),
    artifact_data: AdminStoryWorkspaceArtifactData = Depends(_artifact_data),
) -> Any:
    """List only durable Dream runs visible to the authenticated actor."""

    try:
        actor = {"actor_id": str(current_user["user_id"])}
        request_actor = current_user["_admin_actor"]
        if not isinstance(request_actor, AdminRequestActor):
            raise ValueError("Admin actor unavailable")
    except (KeyError, TypeError, ValueError):
        exc = ApiRouteError("WORKFLOW_PERMISSION_DENIED", status_code=403)
        return JSONResponse(
            status_code=exc.status_code,
            content=build_error_payload(exc.code),
        )
    return await _workflow_call(
        service.list_dream_runs(
            actor=actor,
            artifact_data=artifact_data,
            access_token=request_actor.access_token,
        ),
        by_alias=True,
    )


def _preflight_read_error(exc: AdminDataError, request_id: str):
    if exc.code == "WORKFLOW_PERMISSION_DENIED" and exc.status_code in {403, 404}:
        return JSONResponse(status_code=404, content=build_error_payload("WORKFLOW_PERMISSION_DENIED"))
    raise HTTPException(status_code=exc.status_code, detail={"error_code": exc.code, "request_id": exc.request_id or request_id, "outcome_unknown": exc.outcome_unknown})


@router.get("/workflow-preflights/{preflight_id}")
async def get_workflow_preflight(
    preflight_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    data: AdminPreflightData = Depends(_preflight_data),
):
    try:
        input_dto = PreflightInputDTO(workflow_preflight_id=preflight_id)
        if input_dto.workflow_preflight_id != preflight_id:
            raise ValueError("Preflight path must match its original ID")
    except (ValidationError, ValueError):
        return JSONResponse(status_code=404, content=build_error_payload("WORKFLOW_PERMISSION_DENIED"))
    return await invoke_admin_operation(current_user, data.read, input_dto, error_handler=_preflight_read_error)


def _run_data(owner: AdminRequestAuth = Depends(get_admin_request_auth), current_user: dict = Depends(get_current_user)) -> AdminRunData:
    actor = current_user.get("_admin_actor")
    if not isinstance(actor, AdminRequestActor):
        raise HTTPException(status_code=503, detail="ADMIN_CONFIGURATION_INVALID")
    return AdminRunData(owner.client, canonical_user_id=actor.canonical_user_id)


def _run_data_error(exc: AdminDataError, request_id: str):
    mapped = WORKFLOW_RUN_ROUTE_ERRORS.get(exc.code)
    if not exc.outcome_unknown and ((mapped is not None and exc.status_code == mapped[1]) or (exc.code == "INVALID_RUN_REQUEST" and exc.status_code in {400, 422})):
        error = workflow_run_route_error(exc.code)
        return JSONResponse(status_code=error.status_code, content=build_error_payload(error.code))
    raise HTTPException(status_code=exc.status_code, detail={"error_code": exc.code, "request_id": request_id, "outcome_unknown": exc.outcome_unknown}) from None


def _guidance_data(
    owner: AdminRequestAuth = Depends(get_admin_request_auth),
    current_user: dict = Depends(get_current_user),
) -> AdminStoryWorkspaceGuidanceData:
    actor = current_user.get("_admin_actor")
    if not isinstance(actor, AdminRequestActor):
        raise HTTPException(status_code=503, detail="ADMIN_CONFIGURATION_INVALID")
    return AdminStoryWorkspaceGuidanceData(
        owner.client,
        canonical_user_id=actor.canonical_user_id,
    )


def _confirmation_data(
    owner: AdminRequestAuth = Depends(get_admin_request_auth),
    current_user: dict = Depends(get_current_user),
) -> AdminStoryWorkspaceConfirmationData:
    actor = current_user.get("_admin_actor")
    if not isinstance(actor, AdminRequestActor):
        raise HTTPException(status_code=503, detail="ADMIN_CONFIGURATION_INVALID")
    return AdminStoryWorkspaceConfirmationData(
        owner.client,
        canonical_user_id=actor.canonical_user_id,
    )


def _guidance_data_error(exc: AdminDataError, request_id: str):
    if not exc.outcome_unknown:
        if exc.code == "WORKFLOW_RUN_NOT_FOUND" and exc.status_code == 404:
            error = workflow_run_route_error(exc.code)
            return JSONResponse(
                status_code=error.status_code,
                content=build_error_payload(error.code),
            )
        if exc.code in {"WORKFLOW_RUN_NOT_GUIDABLE", "IDEMPOTENCY_CONFLICT"} and exc.status_code == 409:
            return JSONResponse(
                status_code=exc.status_code,
                content=build_error_payload(exc.code),
            )
    raise HTTPException(
        status_code=exc.status_code,
        detail={
            "error_code": exc.code,
            "request_id": exc.request_id or request_id,
            "outcome_unknown": exc.outcome_unknown,
        },
    ) from None


class _RunCommandRoute(SafeRequestValidationRoute):
    validation_error_detail = "Invalid Workflow Run request"


_run_create_router = APIRouter(route_class=_RunCommandRoute)
_run_retry_router = APIRouter(route_class=_RunCommandRoute)
_run_cancel_router = APIRouter(route_class=_RunCommandRoute)


@_run_create_router.post("/workflow-runs", status_code=201)
async def create_workflow_run(
    request: _WorkflowRunCreateRequest,
    current_user: dict[str, Any] = Depends(_story_workflow_current_user),
    data: AdminRunData = Depends(_run_data),
):
    try:
        actor = _workflow_actor(current_user)
    except ApiRouteError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content=build_error_payload(exc.code),
        )
    try:
        source_time = datetime.fromisoformat(request.source_message_time.replace("Z", "+00:00")).isoformat() if request.source_message_time else None
        input_dto = RunCreateInputDTO(workspace_id=actor["workspace_id"], workflow_preflight_id=request.workflow_preflight_id,
            preflight_token=request.preflight_token, idempotency_key=request.idempotency_key,
            source_voice_thread_id=request.source_voice_thread_id, source_message_id=request.source_message_id, source_message_time=source_time)
    except (ValueError, RecursionError):
        error = workflow_run_route_error("INVALID_RUN_REQUEST")
        return JSONResponse(status_code=error.status_code, content=build_error_payload(error.code))
    return await invoke_admin_operation(current_user, data.create, input_dto, error_handler=_run_data_error)


router.include_router(_run_create_router)


@router.get("/workflow-runs/{workflow_run_id}")
async def get_workflow_run(
    workflow_run_id: str,
    current_user: dict[str, Any] = Depends(_story_workflow_current_user),
    data: AdminRunData = Depends(_run_data),
):
    try:
        actor = _workflow_actor(current_user)
    except ApiRouteError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content=build_error_payload(exc.code),
        )
    try:
        input_dto = RunLookupInputDTO(workspace_id=actor["workspace_id"], workflow_run_id=workflow_run_id)
        if input_dto.workflow_run_id != workflow_run_id:
            raise ValueError("Run path is invalid")
    except (ValueError, RecursionError):
        error = workflow_run_route_error("WORKFLOW_RUN_NOT_FOUND")
        return JSONResponse(status_code=error.status_code, content=build_error_payload(error.code))
    return await invoke_admin_operation(current_user, data.read, input_dto, error_handler=_run_data_error)


@router.get("/workflow-runs/{workflow_run_id}/dream-files")
async def story_workspace_get_workflow_run_dream_files(
    workflow_run_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    service: DreamArtifactService = Depends(get_dream_artifact_service),
    artifact_data: AdminStoryWorkspaceArtifactData = Depends(_artifact_data),
):
    try:
        actor = {"actor_id": str(current_user["user_id"])}
        request_actor = current_user["_admin_actor"]
        if not isinstance(request_actor, AdminRequestActor):
            raise ValueError("Admin actor unavailable")
    except (KeyError, TypeError, ValueError):
        exc = ApiRouteError("WORKFLOW_PERMISSION_DENIED", status_code=403)
        return JSONResponse(
            status_code=exc.status_code,
            content=build_error_payload(exc.code),
        )
    return await _workflow_call(
        service.get_dream_files(
            workflow_run_id,
            actor=actor,
            artifact_data=artifact_data,
            access_token=request_actor.access_token,
        ),
        by_alias=True,
    )


@router.get("/workflow-runs/{workflow_run_id}/episode-artifacts")
async def story_workspace_get_workflow_run_episode_artifacts(
    workflow_run_id: str,
    episode_id: Optional[str] = Query(
        default=None,
        alias="episode",
        pattern=r"^[0-9a-f]{32}$",
    ),
    if_none_match: Optional[str] = Header(default=None, alias="If-None-Match"),
    current_user: dict[str, Any] = Depends(get_current_user),
    service: DreamArtifactService = Depends(get_dream_artifact_service),
    artifact_data: AdminStoryWorkspaceArtifactData = Depends(_artifact_data),
):
    """Return one registry-owned Episode surface; no browser path is accepted."""

    try:
        actor = {"actor_id": str(current_user["user_id"])}
        request_actor = current_user["_admin_actor"]
        if not isinstance(request_actor, AdminRequestActor):
            raise ValueError("Admin actor unavailable")
    except (KeyError, TypeError, ValueError):
        exc = ApiRouteError("WORKFLOW_PERMISSION_DENIED", status_code=403)
        return JSONResponse(
            status_code=exc.status_code,
            content=build_error_payload(exc.code),
        )
    result = await _workflow_call(
        service.get_episode_artifacts(
            workflow_run_id,
            actor=actor,
            artifact_data=artifact_data,
            access_token=request_actor.access_token,
            episode_id=episode_id,
        ),
        by_alias=True,
    )
    if isinstance(result, JSONResponse):
        return result
    etag = result.get("etag") if isinstance(result, dict) else None
    headers: dict[str, str] = {}
    if isinstance(etag, str):
        quoted_etag = f'"{etag}"'
        headers["ETag"] = quoted_etag
        if if_none_match is not None and if_none_match.strip() == quoted_etag:
            return Response(status_code=304, headers=headers)
    return JSONResponse(content=result, headers=headers)


@router.get("/workflow-runs/{workflow_run_id}/episodes")
async def story_workspace_get_workflow_run_episodes(
    workflow_run_id: str,
    if_none_match: Optional[str] = Header(default=None, alias="If-None-Match"),
    current_user: dict[str, Any] = Depends(get_current_user),
    service: DreamArtifactService = Depends(get_dream_artifact_service),
    artifact_data: AdminStoryWorkspaceArtifactData = Depends(_artifact_data),
):
    """Return registry identity and bounded availability facts without bodies."""

    try:
        actor = {"actor_id": str(current_user["user_id"])}
        request_actor = current_user["_admin_actor"]
        if not isinstance(request_actor, AdminRequestActor):
            raise ValueError("Admin actor unavailable")
    except (KeyError, TypeError, ValueError):
        exc = ApiRouteError("WORKFLOW_PERMISSION_DENIED", status_code=403)
        return JSONResponse(
            status_code=exc.status_code,
            content=build_error_payload(exc.code),
        )
    result = await _workflow_call(
        service.get_episode_index(
            workflow_run_id,
            actor=actor,
            artifact_data=artifact_data,
            access_token=request_actor.access_token,
        ),
        by_alias=True,
    )
    if isinstance(result, JSONResponse):
        return result
    etag = result.get("etag") if isinstance(result, dict) else None
    headers: dict[str, str] = {}
    if isinstance(etag, str):
        quoted_etag = f'"{etag}"'
        headers["ETag"] = quoted_etag
        if if_none_match is not None and if_none_match.strip() == quoted_etag:
            return Response(status_code=304, headers=headers)
    return JSONResponse(content=result, headers=headers)


@router.get("/workflow-runs/{workflow_run_id}/story-index")
async def story_workspace_get_workflow_run_story_index(
    workflow_run_id: str,
    if_none_match: Optional[str] = Header(default=None, alias="If-None-Match"),
    current_user: dict[str, Any] = Depends(get_current_user),
    service: DreamArtifactService = Depends(get_dream_artifact_service),
    artifact_data: AdminStoryWorkspaceArtifactData = Depends(_artifact_data),
):
    """Compare server-bound Artifact revisions with PostgreSQL without writing."""

    try:
        actor = {"actor_id": str(current_user["user_id"])}
        request_actor = current_user["_admin_actor"]
        if not isinstance(request_actor, AdminRequestActor):
            raise ValueError("Admin actor unavailable")
    except (KeyError, TypeError, ValueError):
        return JSONResponse(
            status_code=403,
            content=build_error_payload("WORKFLOW_PERMISSION_DENIED"),
        )
    result = await _story_index_call(
        service.get_story_index(
            workflow_run_id,
            actor=actor,
            artifact_data=artifact_data,
            access_token=request_actor.access_token,
        )
    )
    if isinstance(result, JSONResponse):
        return result
    etag = result.get("etag") if isinstance(result, dict) else None
    headers: dict[str, str] = {}
    if isinstance(etag, str):
        quoted = f'"{etag}"'
        headers["ETag"] = quoted
        if if_none_match is not None and if_none_match.strip() == quoted:
            return Response(status_code=304, headers=headers)
    return JSONResponse(content=result, headers=headers)


@router.post("/workflow-runs/{workflow_run_id}/story-index/reconcile")
async def story_workspace_reconcile_workflow_run_story_index(
    workflow_run_id: str,
    request: StoryWorkspaceStoryIndexReconcileCommand,
    if_match: str = Header(
        alias="If-Match",
        min_length=73,
        max_length=73,
        pattern=r'^"sha256:[0-9a-f]{64}"$',
    ),
    current_user: dict[str, Any] = Depends(get_current_user),
    service: DreamArtifactService = Depends(get_dream_artifact_service),
    artifact_data: AdminStoryWorkspaceArtifactData = Depends(_artifact_data),
):
    """Retry one revision-guarded materialization; no locator input is accepted."""

    try:
        actor = {"actor_id": str(current_user["user_id"])}
        request_actor = current_user["_admin_actor"]
        if not isinstance(request_actor, AdminRequestActor):
            raise ValueError("Admin actor unavailable")
    except (KeyError, TypeError, ValueError):
        return JSONResponse(
            status_code=403,
            content=build_error_payload("WORKFLOW_PERMISSION_DENIED"),
        )
    result = await _story_index_call(
        service.reconcile_story_index(
            workflow_run_id,
            request,
            actor=actor,
            artifact_data=artifact_data,
            access_token=request_actor.access_token,
            if_match=if_match,
        )
    )
    if isinstance(result, JSONResponse):
        return result
    etag = result.get("etag") if isinstance(result, dict) else None
    headers = {"ETag": f'"{etag}"'} if isinstance(etag, str) else {}
    return JSONResponse(content=result, headers=headers)


@router.post(
    "/workflow-runs/{workflow_run_id}/dream-confirmation",
    status_code=202,
)
async def story_workspace_submit_workflow_run_dream_confirmation(
    workflow_run_id: str,
    request: StoryWorkspaceDreamConfirmationCommand,
    current_user: dict[str, Any] = Depends(_story_workflow_current_user),
    service: DreamConfirmationService = Depends(get_dream_confirmation_service),
    run_data: AdminRunData = Depends(_run_data),
    confirmation_data: AdminStoryWorkspaceConfirmationData = Depends(_confirmation_data),
):
    """Persist one hidden confirmation and queue the originating Chat Agent."""

    try:
        actor = {
            "actor_id": str(current_user["user_id"]),
            "workspace_id": str(current_user["workspace_id"]),
        }
        request_actor = current_user["_admin_actor"]
        if not isinstance(request_actor, AdminRequestActor):
            raise ValueError("Admin actor unavailable")
    except (KeyError, TypeError, ValueError):
        exc = ApiRouteError("WORKFLOW_PERMISSION_DENIED", status_code=403)
        return JSONResponse(
            status_code=exc.status_code,
            content=build_error_payload(exc.code),
        )
    return await _workflow_call(
        service.submit_dream_confirmation(
            workflow_run_id,
            request,
            actor=actor,
            run_data=run_data,
            confirmation_data=confirmation_data,
            access_token=request_actor.access_token,
        ),
        by_alias=True,
    )


@_run_retry_router.post("/workflow-runs/{workflow_run_id}/retry", status_code=201)
async def retry_workflow_run(
    workflow_run_id: str,
    request: _WorkflowRunRetryRequest,
    current_user: dict[str, Any] = Depends(_story_workflow_current_user),
    data: AdminRunData = Depends(_run_data),
):
    try:
        actor = _workflow_actor(current_user)
    except ApiRouteError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content=build_error_payload(exc.code),
        )
    try:
        input_dto = RunRetryInputDTO(workspace_id=actor["workspace_id"], workflow_run_id=workflow_run_id,
            workflow_preflight_id=request.workflow_preflight_id, preflight_token=request.preflight_token, idempotency_key=request.idempotency_key)
        if input_dto.workflow_run_id != workflow_run_id:
            raise ValueError("Run path is invalid")
    except ValidationError as exc:
        code = "WORKFLOW_RUN_NOT_FOUND" if any(error["loc"] == ("workflow_run_id",) for error in exc.errors(include_input=False)) else "INVALID_RUN_REQUEST"
        error = workflow_run_route_error(code)
        return JSONResponse(status_code=error.status_code, content=build_error_payload(error.code))
    except ValueError:
        error = workflow_run_route_error("WORKFLOW_RUN_NOT_FOUND")
        return JSONResponse(status_code=error.status_code, content=build_error_payload(error.code))
    return await invoke_admin_operation(current_user, data.retry, input_dto, error_handler=_run_data_error)


router.include_router(_run_retry_router)


@_run_cancel_router.post("/workflow-runs/{workflow_run_id}/cancel")
async def cancel_workflow_run(
    workflow_run_id: str,
    request: _WorkflowRunCancelRequest,
    current_user: dict[str, Any] = Depends(_story_workflow_current_user),
    data: AdminRunData = Depends(_run_data),
):
    try:
        actor = _workflow_actor(current_user)
    except ApiRouteError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content=build_error_payload(exc.code),
        )
    try:
        input_dto = RunCancelInputDTO(workspace_id=actor["workspace_id"], workflow_run_id=workflow_run_id,
            reason_code=f"user_cancelled:{request.reason}")
        if input_dto.workflow_run_id != workflow_run_id:
            raise ValueError("Run path is invalid")
    except ValueError:
        error = workflow_run_route_error("WORKFLOW_RUN_NOT_FOUND")
        return JSONResponse(status_code=error.status_code, content=build_error_payload(error.code))
    return await invoke_admin_operation(current_user, data.cancel, input_dto, error_handler=_run_data_error)


router.include_router(_run_cancel_router)


@router.post("/runs/{workflow_run_id}/guidance", status_code=202)
async def submit_run_guidance(
    workflow_run_id: str,
    request: StoryWorkspaceGuidanceCommandPayload,
    current_user: dict[str, Any] = Depends(get_current_user),
    request_auth: AdminRequestAuth = Depends(get_admin_request_auth),
    data: AdminStoryWorkspaceGuidanceData = Depends(_guidance_data),
):
    """Submit one idempotent guidance command to a guidable run.

    202 — accepted (persisted as a ``metadata.kind="story-workspace-guidance"``
    chat_message row and handed to the same thread's runner as a new turn);
    a same-key same-content replay also returns 202 with ``replayed: true``
    and no duplicate injection. 409 — run not guidable or same key with
    different content (``IDEMPOTENCY_CONFLICT``).
    """
    try:
        actor_id = str(current_user["user_id"])
        if request.actor != actor_id:
            raise ApiRouteError("WORKFLOW_PERMISSION_DENIED", status_code=403)
        input_dto = StoryWorkspaceGuidanceInputDTO(
            workflow_run_id=workflow_run_id,
            kind=request.kind.value,
            text=request.text,
            step_id=request.step_id,
            idempotency_key=request.idempotency_key,
        )
    except (ApiRouteError, ValidationError) as exc:
        if isinstance(exc, ValidationError):
            return JSONResponse(status_code=422, content={"detail": "Invalid guidance request"})
        return JSONResponse(
            status_code=exc.status_code,
            content=build_error_payload(exc.code),
        )
    result = await invoke_admin_operation(
        current_user,
        data.submit_recovering,
        input_dto,
        error_handler=_guidance_data_error,
    )
    if isinstance(result, JSONResponse):
        return result

    dispatched = False
    if result.dispatch is not None:
        dispatch = result.dispatch
        turn_owner = None
        try:
            actor = current_user.get("_admin_actor")
            if not isinstance(actor, AdminRequestActor):
                raise AdminDataError("ADMIN_CONFIGURATION_INVALID", 503)
            turn_owner = await prepare_guidance_turn_owner(
                request_auth=request_auth,
                actor=actor,
                thread_id=dispatch.thread_id,
                workflow_run_id=result.story_workspace_run_id,
            )
            parts = [part.model_dump(mode="json") for part in dispatch.parts]
            metadata = dispatch.metadata.model_dump(mode="json")
            owned_turn = turn_owner
            turn_owner = None
            dispatched = bool(build_thread_turn_dispatcher()(
                owned_turn,
                result.story_workspace_run_id,
                dispatch.message_id,
                parts,
                metadata,
            ))
        except Exception:
            if turn_owner is not None:
                await asyncio.to_thread(turn_owner.persistence.close)
            logger.exception(
                "Guidance dispatch failed for run_id=%s message_id=%s",
                workflow_run_id,
                dispatch.message_id,
            )
    payload = result.model_dump(mode="json", exclude={"dispatch"})
    payload["dispatched"] = dispatched
    return payload
