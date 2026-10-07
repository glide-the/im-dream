# [Sync] 2026-10-07: map safe domain-only busy Retry-After and selection_saved feedback while retaining original statuses and errors.
# [Sync] 2026-10-06: expose selected-date snapshot reads and version-bound metadata verification through one public handler.
# [Input] Notion facade, current Admin OAuth actor, discovery, and snapshot materialization.
# [Output] Register /api/connectors* endpoints, read-only Notion capability/Skill projections, and own the strategy-driven snapshot worker lifecycle.
# [Pos] notion route node in backend/routers
# [Sync] 2026-10-05: add actor/preference-bound read-only today metadata with distinct safe upstream errors.
# [Sync] 2026-07-04: initial Notion connector routes for create/auth/discover/
#                    select/sync/resource listing and connector CRUD.
# [Sync] 2026-08-28: remove browser credential-path/config authority and map
#                    Notion failures to stable, credential-free HTTP responses.
# [Sync] 2026-08-28: expose versioned snapshot-sync strategy and run scheduled synchronization outside Chat turns.
# [Sync] 2026-08-29: expose actor-scoped capability, Skill body, and stable-ID Skill file reads without adding MCP execution or filesystem path input.
# [Sync] 2026-08-30: expose ntn installation-required state before auth and return an actionable missing-CLI response.
# [Sync] 2026-09-16: bind user routes and scheduled sync to separate Admin DTO authorities.

"""Notion resource connector HTTP routes."""
from __future__ import annotations

from datetime import datetime, timezone

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Iterable, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from notion import (
    NotionAuthError,
    NotionAuthRequiredError,
    NotionCLIUnavailableError,
    NotionConnectorError,
    NotionConnectorNotFoundError,
    NotionCredentialError,
    NotionOperationError,
    NotionPermissionError,
    NotionSnapshotNotReadyError,
    build_notion_facade,
    close_default_store,
    open_default_store,
)
from notion.capabilities import (
    NotionCapabilityNotFoundError,
    NotionCapabilityRevisionError,
    NotionCapabilityUnavailableError,
    build_notion_capability_catalog,
    get_notion_skill_detail,
    get_notion_skill_file,
)
from notion.store import NotionConnectorStore
from services.admin_data.notion_connector_data import AdminNotionConnectorData
from services.admin_data.errors import AdminDataError
from services.admin_data.request_auth import AdminRequestActor, AdminRequestAuth

from .deps import get_admin_request_auth, get_current_user
from .deps import invoke_admin_operation
from notion.today import NotionTodayError
from services.admin_data.preferences_data import AdminPreferencesData, PreferencesGetInputDTO

@asynccontextmanager
async def _notion_store_lifespan(app: Any) -> AsyncIterator[None]:
    """Own the background DTO client; schema and transactions stay in Admin."""

    from notion.sync_scheduler import NotionSnapshotSyncWorker

    owner = getattr(app.state, "admin_request_auth", None)
    if not isinstance(owner, AdminRequestAuth):
        raise RuntimeError("ADMIN_CONFIGURATION_INVALID")
    open_default_store(
        store=NotionConnectorStore(
            AdminNotionConnectorData(owner.client),
            background=True,
        )
    )
    worker = NotionSnapshotSyncWorker()
    worker.start()
    try:
        yield
    finally:
        await worker.stop()
        close_default_store()


router = APIRouter(lifespan=_notion_store_lifespan)


class ConnectorCreateRequest(BaseModel):
    name: str
    platform: str = "notion"


class ConnectorUpdateRequest(BaseModel):
    name: Optional[str] = None
    platform: Optional[str] = None


class ResourceSelectionRequest(BaseModel):
    selected_databases: list[Any] = Field(default_factory=list)
    selected_pages: list[Any] = Field(default_factory=list)
    workspace_id: Optional[str] = None


class SyncRequest(BaseModel):
    workspace_id: Optional[str] = None


class SyncPolicyUpdateRequest(BaseModel):
    enabled: bool
    interval_minutes: int


def _user_id(current_user: dict) -> int:
    return int(current_user["user_id"])


def _connector_facade(
    current_user: dict,
    owner: AdminRequestAuth,
    connector_id: Optional[str] = None,
):
    actor = current_user.get("_admin_actor")
    if not isinstance(owner, AdminRequestAuth) or not isinstance(
        actor, AdminRequestActor
    ):
        raise HTTPException(status_code=503, detail="ADMIN_CONFIGURATION_INVALID")
    connector_store = NotionConnectorStore(
        AdminNotionConnectorData(owner.client),
        access_token=actor.access_token,
        expected_user_id=actor.canonical_user_id,
    )
    return build_notion_facade(
        _user_id(current_user),
        connector_id,
        connector_store=connector_store,
    )


def _coerce_resource_item(item: Any, kind: str) -> dict[str, Any]:
    if isinstance(item, dict):
        return dict(item)
    identifier_key = "database_id" if kind == "database" else "page_id"
    return {
        identifier_key: str(item),
        "title": str(item),
    }


def _coerce_resource_list(items: Iterable[Any], kind: str) -> list[dict[str, Any]]:
    return [_coerce_resource_item(item, kind) for item in items]


def _http_error(exc: Exception) -> HTTPException:
    from notion.errors import NotionSyncBusyError, NotionSelectionSyncError
    if isinstance(exc, NotionSelectionSyncError):
        original = _http_error(exc.cause)
        if isinstance(original.detail, dict):
            detail = {**original.detail, "selection_saved": True}
        else:
            text = str(original.detail)
            is_code = text.isupper() and all(character.isupper() or character == "_" for character in text)
            detail = {"error_code": text if is_code else "NOTION_SYNC_FAILED", "selection_saved": True}
            if not is_code:
                detail["message"] = text
        return HTTPException(original.status_code, detail=detail, headers=original.headers)
    if isinstance(exc, NotionSyncBusyError):
        retry = exc.retry_after
        headers = {"Retry-After": str(retry)} if type(retry) is int and 0 <= retry <= 9_007_199_254_740_991 else None
        return HTTPException(409, detail={"error_code": "NOTION_SYNC_BUSY"}, headers=headers)
    if isinstance(exc, NotionTodayError):
        headers = {"Retry-After": str(exc.retry_after)} if exc.retry_after is not None else None
        return HTTPException(exc.status, detail={"error_code": exc.code, **exc.context}, headers=headers)
    if isinstance(exc, AdminDataError):
        return HTTPException(status_code=exc.status_code, detail=exc.code)
    if isinstance(exc, NotionCapabilityNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, NotionCapabilityRevisionError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, NotionCapabilityUnavailableError):
        return HTTPException(status_code=503, detail=str(exc))
    if isinstance(exc, NotionConnectorNotFoundError):
        return HTTPException(status_code=404, detail="Notion connector not found.")
    if isinstance(exc, (NotionAuthRequiredError, NotionCredentialError)):
        return HTTPException(
            status_code=401,
            detail="Notion is not connected or its authorization expired. Reconnect Notion and retry.",
        )
    if isinstance(exc, NotionPermissionError):
        return HTTPException(
            status_code=403,
            detail="Notion denied access to this resource. Update its permissions or reconnect Notion.",
        )
    if isinstance(exc, NotionCLIUnavailableError):
        return HTTPException(
            status_code=503,
            detail="Notion CLI is not installed. Install ntn on the Dream host and retry.",
        )
    if isinstance(exc, NotionSnapshotNotReadyError):
        return HTTPException(
            status_code=409,
            detail="Notion is not ready to sync. Connect Notion and select at least one resource.",
        )
    if isinstance(exc, NotionAuthError):
        return HTTPException(
            status_code=400,
            detail="Notion authorization could not be completed. Retry or reconnect Notion.",
        )
    if isinstance(exc, NotionOperationError):
        return HTTPException(
            status_code=502,
            detail="Notion could not complete the request. Retry later.",
        )
    if isinstance(exc, NotionConnectorError):
        return HTTPException(status_code=400, detail="Notion request is invalid.")
    return HTTPException(status_code=500, detail="Notion request failed safely.")


def _current_notion_connector(
    current_user: dict, owner: AdminRequestAuth
) -> dict[str, Any] | None:
    facade = _connector_facade(current_user, owner)
    connectors = [
        connector
        for connector in facade.list_connectors()
        if str(connector.get("platform") or "").lower() == "notion"
    ]
    if not connectors:
        return None
    return max(
        connectors,
        key=lambda connector: str(
            connector.get("updated_at") or connector.get("created_at") or ""
        ),
    )


@router.get("/api/connectors")
def list_connectors(
    current_user: dict = Depends(get_current_user),
    owner: AdminRequestAuth = Depends(get_admin_request_auth),
):
    facade = _connector_facade(current_user, owner)
    try:
        return {"connectors": facade.list_connectors()}
    except Exception as exc:  # noqa: BLE001
        raise _http_error(exc) from exc


@router.post("/api/connectors")
def create_connector(
    body: ConnectorCreateRequest,
    current_user: dict = Depends(get_current_user),
    owner: AdminRequestAuth = Depends(get_admin_request_auth),
):
    facade = _connector_facade(current_user, owner)
    try:
        connector = facade.create_connector(
            name=body.name,
            platform=body.platform or "notion",
            config={},
        )
        return {"connector": connector}
    except Exception as exc:  # noqa: BLE001
        raise _http_error(exc) from exc


@router.get("/api/connectors/notion/capabilities")
def get_notion_capabilities(
    current_user: dict = Depends(get_current_user),
    owner: AdminRequestAuth = Depends(get_admin_request_auth),
):
    try:
        return {
            "catalog": build_notion_capability_catalog(
                _current_notion_connector(current_user, owner)
            )
        }
    except Exception as exc:  # noqa: BLE001
        raise _http_error(exc) from exc


@router.get("/api/connectors/notion/skills/{skill_id}")
def read_notion_skill(
    skill_id: str,
    current_user: dict = Depends(get_current_user),
    owner: AdminRequestAuth = Depends(get_admin_request_auth),
):
    try:
        return get_notion_skill_detail(
            skill_id,
            _current_notion_connector(current_user, owner),
        )
    except Exception as exc:  # noqa: BLE001
        raise _http_error(exc) from exc


@router.get("/api/connectors/notion/skills/{skill_id}/files/{file_id}")
def read_notion_skill_file(
    skill_id: str,
    file_id: str,
    package_revision: str | None = None,
    _current_user: dict = Depends(get_current_user),
):
    try:
        return get_notion_skill_file(
            skill_id,
            file_id,
            expected_revision=package_revision,
        )
    except Exception as exc:  # noqa: BLE001
        raise _http_error(exc) from exc


@router.get("/api/connectors/{connector_id}")
def get_connector(
    connector_id: str,
    current_user: dict = Depends(get_current_user),
    owner: AdminRequestAuth = Depends(get_admin_request_auth),
):
    facade = _connector_facade(current_user, owner, connector_id)
    try:
        return {"connector": facade.get_connector(connector_id)}
    except Exception as exc:  # noqa: BLE001
        raise _http_error(exc) from exc


@router.patch("/api/connectors/{connector_id}")
def update_connector(
    connector_id: str,
    body: ConnectorUpdateRequest,
    current_user: dict = Depends(get_current_user),
    owner: AdminRequestAuth = Depends(get_admin_request_auth),
):
    facade = _connector_facade(current_user, owner, connector_id)
    updates: dict[str, Any] = {}
    if body.name is not None:
        updates["name"] = body.name
    if body.platform is not None:
        updates["platform"] = body.platform
    try:
        return {"connector": facade.update_connector(updates, connector_id)}
    except Exception as exc:  # noqa: BLE001
        raise _http_error(exc) from exc


@router.delete("/api/connectors/{connector_id}")
def delete_connector(
    connector_id: str,
    current_user: dict = Depends(get_current_user),
    owner: AdminRequestAuth = Depends(get_admin_request_auth),
):
    facade = _connector_facade(current_user, owner, connector_id)
    try:
        deleted = facade.delete_connector(connector_id)
        return {"deleted": deleted}
    except Exception as exc:  # noqa: BLE001
        raise _http_error(exc) from exc


@router.post("/api/connectors/{connector_id}/auth/login")
async def auth_login(
    connector_id: str,
    current_user: dict = Depends(get_current_user),
    owner: AdminRequestAuth = Depends(get_admin_request_auth),
):
    facade = _connector_facade(current_user, owner, connector_id)
    try:
        return await facade.start_auth(connector_id)
    except Exception as exc:  # noqa: BLE001
        raise _http_error(exc) from exc


@router.post("/api/connectors/{connector_id}/auth/poll")
async def auth_poll(
    connector_id: str,
    current_user: dict = Depends(get_current_user),
    owner: AdminRequestAuth = Depends(get_admin_request_auth),
):
    facade = _connector_facade(current_user, owner, connector_id)
    try:
        return await facade.poll_auth(connector_id)
    except Exception as exc:  # noqa: BLE001
        raise _http_error(exc) from exc


@router.get("/api/connectors/{connector_id}/databases")
async def list_databases(
    connector_id: str,
    current_user: dict = Depends(get_current_user),
    owner: AdminRequestAuth = Depends(get_admin_request_auth),
):
    facade = _connector_facade(current_user, owner, connector_id)
    try:
        databases = await facade.list_databases(connector_id)
        return {"connectorId": connector_id, "databases": databases}
    except Exception as exc:  # noqa: BLE001
        raise _http_error(exc) from exc


@router.get("/api/connectors/{connector_id}/pages")
async def list_pages(
    connector_id: str,
    current_user: dict = Depends(get_current_user),
    owner: AdminRequestAuth = Depends(get_admin_request_auth),
):
    facade = _connector_facade(current_user, owner, connector_id)
    try:
        pages = await facade.list_pages(connector_id)
        return {"connectorId": connector_id, "pages": pages}
    except Exception as exc:  # noqa: BLE001
        raise _http_error(exc) from exc


@router.get("/api/connectors/{connector_id}/notion/documents")
@router.get("/api/connectors/{connector_id}/notion/today", include_in_schema=False)
async def today_pages(
    connector_id: str,
    date_key: str,
    validate_remote: bool = False,
    snapshot_version: str | None = None,
    current_user: dict = Depends(get_current_user),
    owner: AdminRequestAuth = Depends(get_admin_request_auth),
):
    facade = _connector_facade(current_user, owner, connector_id)
    try:
        # Ownership is checked before reading preferences or touching credentials.
        facade.get_connector(connector_id)
        preferences = await invoke_admin_operation(current_user, AdminPreferencesData(owner.client).get, PreferencesGetInputDTO())
        result = await facade.today_pages(date_key, preferences.get("timezone"),
                                          validate_remote=validate_remote, snapshot_version=snapshot_version)
        latest = await invoke_admin_operation(current_user, AdminPreferencesData(owner.client).get, PreferencesGetInputDTO())
        if latest.get("timezone") != preferences.get("timezone"):
            from notion.today import day_context
            raise NotionTodayError("NOTION_DATE_CONTEXT_CHANGED", 409,
                                  context=day_context(latest.get("timezone"), date_key, datetime.now(timezone.utc)))
        return result
    except HTTPException:
        raise
    except NotionTodayError as exc:
        headers = {"Retry-After": str(exc.retry_after)} if exc.retry_after is not None else None
        raise HTTPException(exc.status, detail={"error_code": exc.code, **exc.context}, headers=headers) from None
    except (NotionAuthRequiredError, NotionCredentialError):
        raise HTTPException(401, detail={"error_code": "NOTION_AUTH_EXPIRED"}) from None
    except NotionPermissionError:
        raise HTTPException(403, detail={"error_code": "NOTION_PERMISSION_DENIED"}) from None
    except NotionConnectorNotFoundError:
        raise HTTPException(404, detail={"error_code": "NOTION_CONNECTOR_UNAVAILABLE"}) from None
    except Exception as exc:
        raise _http_error(exc) from None


@router.get("/api/connectors/{connector_id}/resources")
def list_resources(
    connector_id: str,
    current_user: dict = Depends(get_current_user),
    owner: AdminRequestAuth = Depends(get_admin_request_auth),
):
    facade = _connector_facade(current_user, owner, connector_id)
    try:
        return {"connectorId": connector_id, "resources": facade.list_selected_resources(connector_id)}
    except Exception as exc:  # noqa: BLE001
        raise _http_error(exc) from exc


@router.post("/api/connectors/{connector_id}/resources/select")
async def select_resources(
    connector_id: str,
    body: ResourceSelectionRequest,
    current_user: dict = Depends(get_current_user),
    owner: AdminRequestAuth = Depends(get_admin_request_auth),
):
    facade = _connector_facade(current_user, owner, connector_id)
    try:
        databases = _coerce_resource_list(body.selected_databases, "database")
        pages = _coerce_resource_list(body.selected_pages, "page")
        return await facade.select_resources(
            databases=databases,
            pages=pages,
            connector_id=connector_id,
            workspace_id=body.workspace_id,
        )
    except Exception as exc:  # noqa: BLE001
        raise _http_error(exc) from exc


@router.post("/api/connectors/{connector_id}/sync")
async def sync_connector(
    connector_id: str,
    body: SyncRequest | None = None,
    current_user: dict = Depends(get_current_user),
    owner: AdminRequestAuth = Depends(get_admin_request_auth),
):
    facade = _connector_facade(current_user, owner, connector_id)
    try:
        return await facade.sync(connector_id=connector_id, workspace_id=(body.workspace_id if body else None))
    except Exception as exc:  # noqa: BLE001
        raise _http_error(exc) from exc


@router.put("/api/connectors/{connector_id}/sync-policy")
def update_sync_policy(
    connector_id: str,
    body: SyncPolicyUpdateRequest,
    current_user: dict = Depends(get_current_user),
    owner: AdminRequestAuth = Depends(get_admin_request_auth),
):
    facade = _connector_facade(current_user, owner, connector_id)
    try:
        return {
            "connector": facade.update_sync_policy(
                enabled=body.enabled,
                interval_minutes=body.interval_minutes,
                connector_id=connector_id,
            )
        }
    except Exception as exc:  # noqa: BLE001
        raise _http_error(exc) from exc


@router.delete("/api/connectors/{connector_id}/resources/{resource_id}")
def delete_resource(
    connector_id: str,
    resource_id: str,
    current_user: dict = Depends(get_current_user),
    owner: AdminRequestAuth = Depends(get_admin_request_auth),
):
    facade = _connector_facade(current_user, owner, connector_id)
    try:
        deleted = facade.delete_selected_resource(resource_id, connector_id)
        return {"deleted": deleted}
    except Exception as exc:  # noqa: BLE001
        raise _http_error(exc) from exc
