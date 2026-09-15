# [Sync] 2026-09-16: move agent-type clear/plan/prepare to Registry127-129 Admin DTOs plus local artifact verification.
# [Input] Current Admin OAuth actor, shared default Workspace and typed Admin binding consumer.
# [Output] Original authenticated binding/options/history/validation/Agent-type API projections.
# [Pos] Public Deck binding ingress; no PostgreSQL client, ORM, transaction or fallback.
# [Sync] 2026-09-15: resolve default Workspace through the shared registered OAuth-write consumer.
"""Authenticated Deck Plugin binding, options, history, and validation endpoints.

[Sync 2026-08-16] Add the folded Deck panel's owner-checked history read.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from services.admin_data.request_auth import AdminRequestAuth
from services.admin_data.deck_plugin_binding_data import (
    AdminDeckPluginBindingData,
    AgentTypeRuntimePrepareInputDTO,
    BindingClearInputDTO,
    BindingHistoryInputDTO,
    BindingRevisionConflictDetailsDTO,
    BindingSaveInputDTO,
    BindingScopeInputDTO,
    BindingSelectionInputDTO,
    BindingSelectionRejectedDetailsDTO,
)
from services.deck.agent_type_runtime import (
    AgentTypeRuntimeUnavailable,
    verify_agent_type_runtime,
)
from starlette.concurrency import run_in_threadpool

from .deps import (
    get_admin_request_auth,
    get_current_user,
    invoke_admin_operation,
    resolve_admin_default_workspace,
)

try:
    from backend.models.deck_plugin import (
        DeckPluginBindingResponse,
        DeckPluginBindingHistoryResponse,
        DeckPluginBindingState,
        DeckPluginBindingUpdateRequest,
        DeckAgentType,
        DeckAgentTypeResponse,
        DeckAgentTypeUpdateRequest,
        DeckPluginOptionsResponse,
        DeckPluginSelectionRequest,
        DeckPluginSelectionValidationResponse,
    )
except ModuleNotFoundError:  # Support the backend directory on PYTHONPATH.
    from models.deck_plugin import (
        DeckPluginBindingResponse,
        DeckPluginBindingHistoryResponse,
        DeckPluginBindingState,
        DeckPluginBindingUpdateRequest,
        DeckAgentType,
        DeckAgentTypeResponse,
        DeckAgentTypeUpdateRequest,
        DeckPluginOptionsResponse,
        DeckPluginSelectionRequest,
        DeckPluginSelectionValidationResponse,
    )


router = APIRouter(prefix="/api/voice-decks", tags=["deck-plugin-binding"])


def _requested_workspace(current_user: dict[str, Any]) -> str | None:
    workspace_id = current_user.get("workspace_id")
    return str(workspace_id) if workspace_id else None


async def _deck_current_user(
    current_user: dict[str, Any] = Depends(get_current_user),
    owner: AdminRequestAuth = Depends(get_admin_request_auth),
) -> dict[str, Any]:
    """Ensure Deck binding always has the authenticated user's default workspace."""
    return await resolve_admin_default_workspace(current_user, owner)


def _access_denied() -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={
            "error_code": "DECK_ACCESS_DENIED",
            "message": "Deck not found or permission denied.",
        },
    )


def _binding_data(request: Request) -> AdminDeckPluginBindingData:
    owner = getattr(request.app.state, "admin_request_auth", None)
    if not isinstance(owner, AdminRequestAuth):
        raise HTTPException(status_code=503, detail="ADMIN_CONFIGURATION_INVALID")
    return AdminDeckPluginBindingData(owner.client)


def _binding_scope(deck_id: str, current_user: dict[str, Any]) -> BindingScopeInputDTO:
    workspace_id = _requested_workspace(current_user)
    if workspace_id is None:
        raise HTTPException(status_code=503, detail="ADMIN_CONFIGURATION_INVALID")
    return BindingScopeInputDTO(deck_id=deck_id, workspace_id=workspace_id)


def _binding_admin_error(exc, request_id: str):
    if not exc.outcome_unknown and exc.code == "DECK_ACCESS_DENIED" and exc.status_code == 404:
        return _access_denied()
    if not exc.outcome_unknown and exc.code == "BINDING_REVISION_CONFLICT" and exc.status_code == 409:
        details = exc.details
        if isinstance(details, BindingRevisionConflictDetailsDTO):
            return JSONResponse(status_code=409, content={
                "error_code": "BINDING_REVISION_CONFLICT",
                "current_revision": details.current_revision,
                "message": "Binding was modified concurrently. Please refresh and confirm your selection.",
            })
    if not exc.outcome_unknown and exc.code == "SELECTION_NOT_ALLOWED" and exc.status_code == 422:
        details = exc.details
        if isinstance(details, BindingSelectionRejectedDetailsDTO):
            return JSONResponse(status_code=422, content={
                "error_code": details.validation.reason_code,
                "message": "The selected Deck Plugin release is not selectable.",
                "validation": details.validation.model_dump(mode="json"),
            })
    if not exc.outcome_unknown and exc.code in {
        "DECK_PLUGIN_UNAVAILABLE",
        "DECK_RUNTIME_CONFIG_INVALID",
        "RUNTIME_PLUGIN_NOT_READY",
    }:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error_code": exc.code,
                "message": "The Dream Runtime is not ready for this Deck.",
            },
        )
    raise HTTPException(status_code=exc.status_code, detail={
        "error_code": exc.code,
        "request_id": exc.request_id or request_id,
        "outcome_unknown": exc.outcome_unknown,
    })


@router.put(
    "/{deck_id}/agent-type",
    response_model=DeckAgentTypeResponse,
)
async def put_agent_type(
    deck_id: str,
    request: DeckAgentTypeUpdateRequest,
    current_user: dict[str, Any] = Depends(_deck_current_user),
    data: AdminDeckPluginBindingData = Depends(_binding_data),
):
    scope = _binding_scope(deck_id, current_user)
    if request.agent_type is DeckAgentType.CHAT:
        return await invoke_admin_operation(
            current_user,
            data.clear,
            BindingClearInputDTO(
                **scope.model_dump(),
                expected_binding_revision=request.expected_binding_revision,
            ),
            error_handler=_binding_admin_error,
        )
    plan = await invoke_admin_operation(
        current_user,
        data.runtime_plan,
        scope,
        error_handler=_binding_admin_error,
    )
    if plan.current_binding_revision != request.expected_binding_revision:
        return JSONResponse(
            status_code=409,
            content={
                "error_code": "BINDING_REVISION_CONFLICT",
                "current_revision": plan.current_binding_revision,
                "message": "Binding was modified concurrently. Please refresh and confirm your selection.",
            },
        )
    try:
        evidence = await run_in_threadpool(
            verify_agent_type_runtime, plan.target
        )
    except AgentTypeRuntimeUnavailable:
        return JSONResponse(
            status_code=503,
            content={
                "error_code": "RUNTIME_PLUGIN_NOT_READY",
                "message": "The Dream Runtime is not ready for this Deck.",
            },
        )
    prepared = await invoke_admin_operation(
        current_user,
        data.runtime_prepare,
        AgentTypeRuntimePrepareInputDTO(
            **scope.model_dump(),
            expected_binding_revision=request.expected_binding_revision,
            verified_plugin=evidence,
        ),
        error_handler=_binding_admin_error,
    )
    selected = await invoke_admin_operation(
        current_user,
        data.save,
        BindingSaveInputDTO(
            **scope.model_dump(),
            deck_plugin_id=prepared.deck_plugin_id,
            deck_plugin_version=prepared.deck_plugin_version,
            apply_to="next_run",
            expected_binding_revision=prepared.current_binding_revision,
        ),
        error_handler=_binding_admin_error,
    )
    return DeckAgentTypeResponse(
        deck_id=deck_id,
        agent_type=DeckAgentType.DREAM,
        binding_revision=selected.binding_revision,
    )


@router.get(
    "/{deck_id}/plugin-options",
    response_model=DeckPluginOptionsResponse,
)
async def get_plugin_options(
    deck_id: str,
    current_user: dict[str, Any] = Depends(_deck_current_user),
    data: AdminDeckPluginBindingData = Depends(_binding_data),
):
    return await invoke_admin_operation(
        current_user, data.options, _binding_scope(deck_id, current_user),
        error_handler=_binding_admin_error,
    )


@router.get(
    "/{deck_id}/plugin-binding",
    response_model=DeckPluginBindingState,
)
async def get_plugin_binding(
    deck_id: str,
    current_user: dict[str, Any] = Depends(_deck_current_user),
    data: AdminDeckPluginBindingData = Depends(_binding_data),
):
    return await invoke_admin_operation(
        current_user, data.current, _binding_scope(deck_id, current_user),
        error_handler=_binding_admin_error,
    )


@router.get(
    "/{deck_id}/plugin-binding/history",
    response_model=DeckPluginBindingHistoryResponse,
)
async def get_plugin_binding_history(
    deck_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    current_user: dict[str, Any] = Depends(_deck_current_user),
    data: AdminDeckPluginBindingData = Depends(_binding_data),
):
    scope = _binding_scope(deck_id, current_user)
    return await invoke_admin_operation(
        current_user, data.history,
        BindingHistoryInputDTO(**scope.model_dump(), limit=limit),
        error_handler=_binding_admin_error,
    )


@router.put(
    "/{deck_id}/plugin-binding",
    response_model=DeckPluginBindingResponse,
)
async def put_plugin_binding(
    deck_id: str,
    request: DeckPluginBindingUpdateRequest,
    current_user: dict[str, Any] = Depends(_deck_current_user),
    data: AdminDeckPluginBindingData = Depends(_binding_data),
):
    scope = _binding_scope(deck_id, current_user)
    return await invoke_admin_operation(
        current_user,
        data.save,
        BindingSaveInputDTO(
            **scope.model_dump(),
            deck_plugin_id=request.deck_plugin_id,
            deck_plugin_version=request.deck_plugin_version,
            apply_to=request.apply_to.value,
            expected_binding_revision=request.expected_binding_revision,
        ),
        error_handler=_binding_admin_error,
    )


@router.post(
    "/{deck_id}/plugin-binding/validate",
    response_model=DeckPluginSelectionValidationResponse,
)
async def validate_plugin_binding(
    deck_id: str,
    request: DeckPluginSelectionRequest,
    current_user: dict[str, Any] = Depends(_deck_current_user),
    data: AdminDeckPluginBindingData = Depends(_binding_data),
):
    scope = _binding_scope(deck_id, current_user)
    return await invoke_admin_operation(
        current_user,
        data.validate,
        BindingSelectionInputDTO(
            **scope.model_dump(),
            deck_plugin_id=request.deck_plugin_id,
            deck_plugin_version=request.deck_plugin_version,
            apply_to=request.apply_to.value,
        ),
        error_handler=_binding_admin_error,
    )
