"""Settings → Plugins: shared Claude Code plugin administration API.

[Input] Authenticated Dream users, package specs or Admin-approved Marketplace entry IDs.
[Output] Existing public catalog/install/operation/installation/Deck-ref routes.
[Pos] Thin FastAPI boundary; Admin owns all database reads/writes while Dream owns CLI/filesystem execution.
[Sync] 2026-09-16: replace catalog/install/operation PostgreSQL access with Registry175-182 DTO operations.
"""

from __future__ import annotations

import logging
from typing import Any, Literal
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator

from services.admin_data.claude_plugin_data import (
    AdminClaudePluginData,
    ClaudePluginEmptyInputDTO,
    ClaudePluginInstallPlanDTO,
    ClaudePluginInstallPrepareInputDTO,
    ClaudePluginInstallationReadInputDTO,
    ClaudePluginInstallReportInputDTO,
    ClaudePluginOperationReadInputDTO,
    ClaudePluginOperationsListInputDTO,
)
from services.admin_data.deck_refs_data import (
    AdminDeckRefsData,
    PublicRefsRequestDTO,
    RefsListInputDTO,
    RefsSelectionDTO,
)
from services.admin_data.errors import AdminDataError
from services.admin_data.request_auth import AdminRequestActor, AdminRequestAuth

from .deps import SafeRequestValidationRoute, get_current_user, invoke_admin_operation

try:
    from services.errors.error_registry import build_error_payload
    from services.claude_plugin import cli
    from services.claude_plugin.install_service import (
        PLUGIN_INSTALL_FAILED,
        PluginInstallError,
        PluginInstallReporter,
        PluginInstallService,
    )
except ModuleNotFoundError:
    from backend.services.errors.error_registry import build_error_payload
    from backend.services.claude_plugin import cli
    from backend.services.claude_plugin.install_service import (
        PLUGIN_INSTALL_FAILED,
        PluginInstallError,
        PluginInstallReporter,
        PluginInstallService,
    )


class _PluginRoute(SafeRequestValidationRoute):
    validation_error_detail = "Invalid plugin request"


router = APIRouter(tags=["claude-plugins"], route_class=_PluginRoute)


def _admin_error(exc: AdminDataError, request_id: str) -> JSONResponse:
    code = (
        "CLAUDE_PLUGIN_OPERATION_RESULT_UNKNOWN"
        if exc.code == "ADMIN_WRITE_RESULT_UNKNOWN"
        else exc.code
    )
    payload = build_error_payload(
        code, operation_id=exc.request_id or request_id
    )
    payload["error"]["request_id"] = exc.request_id or request_id
    payload["error"]["outcome_unknown"] = exc.outcome_unknown
    return JSONResponse(status_code=exc.status_code, content=payload)


def _require_authenticated(current_user: dict[str, Any]) -> JSONResponse | None:
    if current_user.get("user_id") is not None:
        return None
    return JSONResponse(
        status_code=403,
        content=build_error_payload("WORKFLOW_PERMISSION_DENIED"),
    )


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class InstallRequest(_Strict):
    package_spec: str | None = Field(default=None, min_length=3, max_length=300)
    marketplace_entry_id: str | None = Field(
        default=None, min_length=3, max_length=160
    )
    source_type: Literal[
        "claude-official", "marketplace", "platform-builtin"
    ] | None = None

    @model_validator(mode="after")
    def require_exactly_one_source(self) -> "InstallRequest":
        if (self.package_spec is None) == (self.marketplace_entry_id is None):
            raise ValueError(
                "exactly one of package_spec or marketplace_entry_id is required"
            )
        if self.marketplace_entry_id is not None and self.source_type is not None:
            raise ValueError("source_type is resolved by marketplace_entry_id")
        return self


DeckRefsPutRequest = PublicRefsRequestDTO


def _owner(request: Request) -> AdminRequestAuth:
    owner = getattr(request.app.state, "admin_request_auth", None)
    if not isinstance(owner, AdminRequestAuth):
        raise HTTPException(status_code=503, detail="ADMIN_CONFIGURATION_INVALID")
    return owner


def _plugin_data(request: Request) -> AdminClaudePluginData:
    return AdminClaudePluginData(_owner(request).client)


def _refs_data(request: Request) -> AdminDeckRefsData:
    return AdminDeckRefsData(_owner(request).client)


def _refs_error(exc: AdminDataError, request_id: str) -> JSONResponse:
    code = "DECK_ACCESS_DENIED" if exc.code == "ENTITY_NOT_FOUND" else exc.code
    payload = build_error_payload(code, operation_id=exc.request_id or request_id)
    payload["error"]["request_id"] = exc.request_id or request_id
    payload["error"]["outcome_unknown"] = exc.outcome_unknown
    return JSONResponse(status_code=exc.status_code, content=payload)


class _AdminReporter(PluginInstallReporter):
    def __init__(self, data: AdminClaudePluginData, access_token: str) -> None:
        self._data = data
        self._access_token = access_token

    def report(self, request: ClaudePluginInstallReportInputDTO):
        return self._data.report(
            request, str(uuid.uuid4()), access_token=self._access_token
        )


def _terminal_failure(
    data: AdminClaudePluginData,
    actor: AdminRequestActor,
    plan: ClaudePluginInstallPlanDTO,
    error: PluginInstallError,
) -> None:
    evidence_path = cli.write_operation_evidence(
        plan.operation_id,
        {
            "operation_id": plan.operation_id,
            "requested_package_spec": plan.package_spec,
            "status": "error",
            "error_code": error.code,
            "error_summary": str(error),
        },
    )
    data.report(
        ClaudePluginInstallReportInputDTO(
            event="fail",
            operation_id=plan.operation_id,
            error_code=error.code,
            error_summary=str(error),
            evidence_path=str(evidence_path),
        ),
        str(uuid.uuid4()),
        access_token=actor.access_token,
    )


def _run_install(
    plan: ClaudePluginInstallPlanDTO,
    data: AdminClaudePluginData,
    actor: AdminRequestActor,
) -> None:
    """Execute only CLI/Git/filesystem work and report lifecycle to Admin."""

    try:
        PluginInstallService(_AdminReporter(data, actor.access_token)).install(
            plan.package_spec,
            source_type=plan.requested_source_type,
            marketplace_entry=plan.marketplace_source,
            operation_id=plan.operation_id,
        )
    except PluginInstallError as exc:
        try:
            _terminal_failure(data, actor, plan, exc)
        except AdminDataError:
            logging.getLogger(__name__).exception(
                "Admin could not confirm terminal Claude Plugin failure for %s",
                plan.operation_id,
            )
    except AdminDataError:
        logging.getLogger(__name__).exception(
            "Admin Claude Plugin lifecycle unavailable for %s", plan.operation_id
        )
    except Exception:  # noqa: BLE001 - background tasks need terminal visibility
        error = PluginInstallError(
            PLUGIN_INSTALL_FAILED,
            "ClaudePlugin install background task failed unexpectedly",
        )
        try:
            _terminal_failure(data, actor, plan, error)
        except AdminDataError:
            logging.getLogger(__name__).exception(
                "Admin could not confirm unexpected Claude Plugin failure for %s",
                plan.operation_id,
            )


@router.get("/api/claude-plugins/installations")
async def list_installations(
    current_user: dict = Depends(get_current_user),
    data: AdminClaudePluginData = Depends(_plugin_data),
):
    denied = _require_authenticated(current_user)
    if denied is not None:
        return denied
    return await invoke_admin_operation(
        current_user,
        data.list_installations,
        ClaudePluginEmptyInputDTO(),
        error_handler=_admin_error,
    )


@router.get("/api/claude-plugins/marketplace")
async def list_marketplace(
    current_user: dict = Depends(get_current_user),
    data: AdminClaudePluginData = Depends(_plugin_data),
):
    denied = _require_authenticated(current_user)
    if denied is not None:
        return denied
    return await invoke_admin_operation(
        current_user,
        data.list_marketplace,
        ClaudePluginEmptyInputDTO(),
        error_handler=_admin_error,
    )


@router.post("/api/claude-plugins/install", status_code=202)
async def install_plugin(
    request: InstallRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    data: AdminClaudePluginData = Depends(_plugin_data),
):
    denied = _require_authenticated(current_user)
    if denied is not None:
        return denied
    actor = current_user.get("_admin_actor")
    if not isinstance(actor, AdminRequestActor):
        raise HTTPException(status_code=503, detail="ADMIN_CONFIGURATION_INVALID")
    if request.package_spec is not None:
        try:
            from services.claude_plugin.package_spec import (
                PackageSpecError,
                parse_package_spec,
            )
        except ModuleNotFoundError:
            from backend.services.claude_plugin.package_spec import (
                PackageSpecError,
                parse_package_spec,
            )
        try:
            parse_package_spec(request.package_spec)
        except PackageSpecError:
            return JSONResponse(
                status_code=422,
                content=build_error_payload("CLAUDE_PLUGIN_SPEC_INVALID"),
            )
        command = ClaudePluginInstallPrepareInputDTO(
            source_kind="package",
            package_spec=request.package_spec,
            source_type=request.source_type,
        )
    else:
        command = ClaudePluginInstallPrepareInputDTO(
            source_kind="marketplace_entry",
            marketplace_entry_id=request.marketplace_entry_id,
        )
    plan = await invoke_admin_operation(
        current_user, data.prepare, command, error_handler=_admin_error
    )
    if isinstance(plan, JSONResponse):
        return plan
    background_tasks.add_task(_run_install, plan, data, actor)
    return {
        "accepted": True,
        "operation_id": plan.operation_id,
        "package_spec": plan.package_spec,
        "marketplace_entry_id": plan.marketplace_entry_id,
    }


@router.get("/api/claude-plugins/operations")
async def list_operations(
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
    data: AdminClaudePluginData = Depends(_plugin_data),
):
    denied = _require_authenticated(current_user)
    if denied is not None:
        return denied
    return await invoke_admin_operation(
        current_user,
        data.list_operations,
        ClaudePluginOperationsListInputDTO(limit=max(1, min(limit, 100))),
        error_handler=_admin_error,
    )


@router.get("/api/claude-plugins/operations/{operation_id}")
async def get_operation(
    operation_id: str,
    current_user: dict = Depends(get_current_user),
    data: AdminClaudePluginData = Depends(_plugin_data),
):
    denied = _require_authenticated(current_user)
    if denied is not None:
        return denied
    return await invoke_admin_operation(
        current_user,
        data.read_operation,
        ClaudePluginOperationReadInputDTO(operation_id=operation_id),
        error_handler=_admin_error,
    )


@router.get("/api/claude-plugins/installations/{installation_id}")
async def get_installation(
    installation_id: str,
    current_user: dict = Depends(get_current_user),
    data: AdminClaudePluginData = Depends(_plugin_data),
):
    denied = _require_authenticated(current_user)
    if denied is not None:
        return denied
    return await invoke_admin_operation(
        current_user,
        data.read_installation,
        ClaudePluginInstallationReadInputDTO(installation_id=installation_id),
        error_handler=_admin_error,
    )


@router.post("/api/claude-plugins/installations/{installation_id}/uninstall")
async def uninstall_plugin(
    installation_id: str,
    current_user: dict = Depends(get_current_user),
    data: AdminClaudePluginData = Depends(_plugin_data),
):
    denied = _require_authenticated(current_user)
    if denied is not None:
        return denied
    return await invoke_admin_operation(
        current_user,
        data.uninstall,
        ClaudePluginInstallationReadInputDTO(installation_id=installation_id),
        error_handler=_admin_error,
    )


@router.get("/api/decks/{deck_id}/claude-plugins")
async def list_deck_plugins(
    deck_id: str,
    current_user: dict = Depends(get_current_user),
    data: AdminDeckRefsData = Depends(_refs_data),
):
    return await invoke_admin_operation(
        current_user,
        data.list,
        RefsListInputDTO(deck_id=deck_id),
        error_handler=_refs_error,
    )


@router.put("/api/decks/{deck_id}/claude-plugins")
async def put_deck_plugins(
    deck_id: str,
    request: DeckRefsPutRequest,
    current_user: dict = Depends(get_current_user),
    data: AdminDeckRefsData = Depends(_refs_data),
):
    return await invoke_admin_operation(
        current_user,
        data.replace,
        RefsSelectionDTO(deck_id=deck_id, refs=request.refs),
        error_handler=_refs_error,
    )
