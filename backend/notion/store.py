# [Sync] 2026-10-07: adapt request/claim/renew/finish with server process UUID and service-only renew/finish; no legacy sync fallback.
# [Input] Strict Admin Notion DTO client, one OAuth/delegated actor or scheduled-sync service authority.
# [Output] Store compatibility API with Registry148-168 reads and frozen owned-execution operations.
# [Pos] Sole connector persistence adapter; contains no SQL, ORM, pool, DDL or database fallback.
# [Sync] 2026-09-16: replace Dream PostgreSQL repository/UOW with Admin DTO operations.
"""Admin-backed Notion connector persistence compatibility layer."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import asdict, is_dataclass
import os
from threading import RLock
from typing import Any, Optional
from uuid import uuid4

from services.admin_data.errors import AdminDataError, configuration_invalid
from services.admin_data.notion_connector_data import (
    ATTACH_NOTION_THREAD, CREATE_NOTION_CONNECTOR, DELETE_NOTION_CONNECTOR,
    DELETE_NOTION_RESOURCE, GET_ACTIVE_NOTION_CONNECTOR,
    GET_CURRENT_NOTION_SNAPSHOT, GET_NOTION_CONNECTOR, GET_NOTION_SNAPSHOT,
    GET_NOTION_SYNC_CONNECTOR, LIST_NOTION_CONNECTORS, LIST_NOTION_RESOURCES,
    LIST_NOTION_SNAPSHOTS, LIST_NOTION_SYNC_CANDIDATES,
    LIST_NOTION_SYNC_RESOURCES, PATCH_NOTION_CONNECTOR,
    PATCH_NOTION_SYNC_CONNECTOR, REPLACE_NOTION_RESOURCES,
    RESOLVE_NOTION_THREAD, SAVE_NOTION_AUTH_STATE, SAVE_NOTION_SNAPSHOT,
    SAVE_NOTION_SYNC_SNAPSHOT, AdminNotionConnectorData,
    NotionAuthStateSaveInputDTO, NotionAuthorityDTO,
    NotionConnectorActiveInputDTO, NotionConnectorCreateInputDTO,
    NotionConnectorDeleteInputDTO, NotionConnectorDTO,
    NotionConnectorGetInputDTO, NotionConnectorListInputDTO,
    NotionConnectorPatchDTO, NotionConnectorPatchInputDTO,
    NotionResourceDeleteInputDTO, NotionResourceSelectionDTO,
    NotionResourcesListInputDTO, NotionResourcesReplaceInputDTO,
    NotionSnapshotCurrentInputDTO, NotionSnapshotGetInputDTO,
    NotionSnapshotListInputDTO, NotionSnapshotSaveInputDTO,
    NotionSyncCandidatesInputDTO, NotionSyncConnectorInputDTO,
    NotionSyncConnectorPatchInputDTO, NotionSyncResourcesInputDTO,
    NotionSyncSnapshotSaveInputDTO, NotionSyncedResourceDTO,
    NotionThreadAttachInputDTO, NotionThreadResolveInputDTO,
    REQUEST_NOTION_SYNC_RUN, CLAIM_NOTION_SYNC_RUN, RENEW_NOTION_SYNC_RUN,
    FINISH_NOTION_SYNC_RUN, NotionSyncRunClaimInputDTO, NotionSyncRunRequestInputDTO,
    NotionSyncRunKeyDTO, NotionSyncRunFinishInputDTO, NotionSyncRunDTO,
)

from .errors import NotionSnapshotNotReadyError
from .sync_policy import SYNC_POLICY_CONFIG_KEY, resolve_sync_policy

_worker_identity: tuple[int, str] | None = None
_worker_identity_lock = RLock()


def _process_worker_id() -> str:
    """Server-only UUID; a prefork child must not inherit its parent's worker."""
    global _worker_identity
    with _worker_identity_lock:
        if _worker_identity is None or _worker_identity[0] != os.getpid():
            _worker_identity = (os.getpid(), str(uuid4()))
        return _worker_identity[1]


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _snapshot_payload(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        payload = dict(value)
    elif is_dataclass(value):
        payload = asdict(value)
    elif hasattr(value, "to_dict"):
        payload = dict(value.to_dict())
    elif hasattr(value, "__dict__"):
        payload = dict(value.__dict__)
    else:
        raise NotionSnapshotNotReadyError("Snapshot payload is invalid.")
    metadata = _mapping(payload.get("metadata"))
    required = (
        "workspace_id", "resource_connector_id", "snapshot_version",
        "source_revision", "sync_cursor", "fetched_at", "state",
    )
    if any(not str(metadata.get(field) or "").strip() for field in required):
        raise NotionSnapshotNotReadyError("Snapshot metadata is incomplete.")
    return payload


class NotionConnectorStore:
    """Map the historical facade contract to strict Admin operations."""

    def __init__(
        self, data: AdminNotionConnectorData, *, access_token: str | None = None,
        authority: NotionAuthorityDTO | None = None,
        expected_user_id: int | str | None = None, background: bool = False,
    ) -> None:
        if not isinstance(data, AdminNotionConnectorData):
            raise TypeError("Notion connector data client must be exact")
        if background:
            if access_token is not None or authority is not None or expected_user_id is not None:
                raise ValueError("Scheduled Notion storage cannot carry user authority")
        elif (
            not access_token or expected_user_id is None
            or not str(expected_user_id).isdecimal()
            or int(str(expected_user_id)) < 1
        ):
            raise ValueError("User Notion storage requires exact Admin authority")
        self._data = data
        self._access_token = access_token
        self._authority = authority
        self._expected_user_id = None if expected_user_id is None else str(expected_user_id)
        self._background = background

    @property
    def background(self) -> bool:
        """Authority selected by server composition, never by a browser payload."""
        return self._background

    def _request_id(self) -> str:
        return str(uuid4())

    def _assert_user(self, user_id: int | str) -> None:
        if self._background or self._expected_user_id is None or str(user_id) != self._expected_user_id:
            raise AdminDataError("DREAM_DELEGATION_ENTITY_DENIED", 403)

    @staticmethod
    def _project_resource(value) -> dict[str, Any]:
        result = value.model_dump(mode="json")
        result["selected"] = True
        return result

    def _project_connector(self, value: NotionConnectorDTO | None, *, requested_user_id: int | str | None = None) -> dict[str, Any] | None:
        if value is None:
            return None
        if requested_user_id is not None and value.user_id != str(requested_user_id):
            raise AdminDataError("ADMIN_RESPONSE_INVALID", 503)
        if self._expected_user_id is not None and value.user_id != self._expected_user_id:
            raise AdminDataError("ADMIN_RESPONSE_INVALID", 503)
        result = value.model_dump(mode="json")
        result["user_id"] = int(value.user_id)
        config = dict(value.config)
        result["config"] = config
        result["selected_databases"] = list(config.get("selected_databases") or [])
        result["selected_pages"] = list(config.get("selected_pages") or [])
        result["sync_policy"] = resolve_sync_policy(
            config.get(SYNC_POLICY_CONFIG_KEY), last_synced_at=value.last_synced_at,
        )
        result["sources"] = [self._project_resource(item) for item in value.sources]
        return result

    def _execute(self, operation, input_dto, *, connector_id: str | None = None):
        return self._data.execute(
            operation, input_dto, self._request_id(),
            access_token=self._access_token,
            background_connector_id=connector_id if self._background else None,
        )

    def begin_sync_run(self, connector_id: str, user_id: int):
        if not self._background:
            self._assert_user(user_id)
        operation = CLAIM_NOTION_SYNC_RUN if self._background else REQUEST_NOTION_SYNC_RUN
        fields = {"connector_id": connector_id, "worker_id": _process_worker_id()}
        input_dto = (NotionSyncRunClaimInputDTO(**fields) if self._background else
            NotionSyncRunRequestInputDTO(**fields, authority=self._authority))
        result = self._data.execute(operation, input_dto, self._request_id(),
            access_token=None if self._background else self._access_token,
            background_connector_id=connector_id if self._background else None)
        self._project_connector(result.connector, requested_user_id=user_id)
        if result.run is not None and result.run.owner_user_id != str(user_id):
            raise AdminDataError("ADMIN_RESPONSE_INVALID", 503)
        return result

    @staticmethod
    def _run_key(connector_id: str, run: NotionSyncRunDTO) -> dict:
        return {"connector_id": connector_id, "worker_id": _process_worker_id(),
            "run_id": run.run_id, "fence_epoch": run.fence_epoch}

    def renew_sync_run(self, connector_id: str, run: NotionSyncRunDTO):
        result = self._data.execute(RENEW_NOTION_SYNC_RUN,
            NotionSyncRunKeyDTO(**self._run_key(connector_id, run)), self._request_id(),
            access_token=None, background_connector_id=connector_id)
        return self._checked_run_context(result, run)

    def finish_sync_run(self, connector_id: str, run: NotionSyncRunDTO, outcome: dict):
        result = self._data.execute(FINISH_NOTION_SYNC_RUN,
            NotionSyncRunFinishInputDTO(**self._run_key(connector_id, run), outcome=outcome),
            self._request_id(), access_token=None, background_connector_id=connector_id)
        return self._checked_run_context(result, run)

    @staticmethod
    def _checked_run_context(result, original):
        fields = ("run_id", "fence_epoch", "service_client_id", "worker_id", "owner_user_id",
            "selection_revision", "authorization_revision", "policy_revision", "started_at")
        if result.run is None or any(getattr(result.run, key) != getattr(original, key) for key in fields):
            raise AdminDataError("ADMIN_RESPONSE_INVALID", 503, outcome_unknown=True)
        return result

    def create_connector(self, user_id: int, name: str, platform: str = "notion", config: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        self._assert_user(user_id)
        result = self._execute(CREATE_NOTION_CONNECTOR, NotionConnectorCreateInputDTO(
            authority=self._authority, name=name.strip() or "Notion Connector",
            platform=platform.strip() or "notion", config=config or {},
        ))
        return self._project_connector(result.connector, requested_user_id=user_id) or {}

    def list_connectors(self, user_id: int) -> list[dict[str, Any]]:
        self._assert_user(user_id)
        result = self._execute(LIST_NOTION_CONNECTORS, NotionConnectorListInputDTO(authority=self._authority))
        return [self._project_connector(item, requested_user_id=user_id) or {} for item in result.connectors]

    def list_sync_candidates(self) -> list[dict[str, Any]]:
        if not self._background:
            raise AdminDataError("DREAM_SERVICE_SCOPE_REQUIRED", 403)
        result = self._execute(LIST_NOTION_SYNC_CANDIDATES, NotionSyncCandidatesInputDTO())
        return [self._project_connector(item) or {} for item in result.connectors]

    def get_connector(self, connector_id: str, user_id: Optional[int] = None) -> Optional[dict[str, Any]]:
        if self._background:
            result = self._execute(GET_NOTION_SYNC_CONNECTOR, NotionSyncConnectorInputDTO(connector_id=connector_id))
        else:
            if user_id is None:
                user_id = int(self._expected_user_id or "0")
            self._assert_user(user_id)
            result = self._execute(GET_NOTION_CONNECTOR, NotionConnectorGetInputDTO(
                authority=self._authority, connector_id=connector_id,
            ))
        return self._project_connector(result.connector, requested_user_id=user_id)

    def get_active_connector_for_user(self, user_id: int) -> Optional[dict[str, Any]]:
        self._assert_user(user_id)
        result = self._execute(GET_ACTIVE_NOTION_CONNECTOR, NotionConnectorActiveInputDTO(authority=self._authority))
        return self._project_connector(result.connector, requested_user_id=user_id)

    def update_connector(self, connector_id: str, user_id: int, updates: Mapping[str, Any]) -> dict[str, Any]:
        fields: dict[str, Any] = {}
        for name in ("name", "platform", "auth_status"):
            if name in updates and updates[name] is not None:
                fields[name] = str(updates[name]).strip()
        if isinstance(updates.get("config"), Mapping):
            fields["config_patch"] = dict(updates["config"])
        for name in ("current_snapshot_version", "current_source_revision", "current_sync_cursor", "last_synced_at"):
            if name in updates:
                fields[name] = updates[name]
        patch = NotionConnectorPatchDTO(**fields)
        if self._background:
            result = self._execute(PATCH_NOTION_SYNC_CONNECTOR, NotionSyncConnectorPatchInputDTO(
                connector_id=connector_id, patch=patch,
            ), connector_id=connector_id)
        else:
            self._assert_user(user_id)
            result = self._execute(PATCH_NOTION_CONNECTOR, NotionConnectorPatchInputDTO(
                authority=self._authority, connector_id=connector_id, patch=patch,
            ))
        return self._project_connector(result.connector, requested_user_id=user_id) or {}

    def delete_connector(self, connector_id: str, user_id: int) -> bool:
        self._assert_user(user_id)
        return self._execute(DELETE_NOTION_CONNECTOR, NotionConnectorDeleteInputDTO(
            authority=self._authority, connector_id=connector_id,
        )).deleted

    def save_auth_state(self, connector_id: str, user_id: int, *, auth_status: str,
        config_patch: Optional[Mapping[str, Any]] = None,
        verification_url: Optional[str] = None, verification_code: Optional[str] = None,
        poll_interval_seconds: Optional[int] = None, error_detail: Optional[str] = None) -> dict[str, Any]:
        self._assert_user(user_id)
        patch = dict(config_patch or {})
        if verification_url is not None: patch["verification_url"] = verification_url
        if verification_code is not None: patch["verification_code"] = verification_code
        if poll_interval_seconds is not None: patch["poll_interval_seconds"] = poll_interval_seconds
        if error_detail is not None: patch["auth_error"] = error_detail
        result = self._execute(SAVE_NOTION_AUTH_STATE, NotionAuthStateSaveInputDTO(
            authority=self._authority, connector_id=connector_id,
            auth_status=auth_status, config_patch=patch,
        ))
        return self._project_connector(result.connector, requested_user_id=user_id) or {}

    @staticmethod
    def _selection(item: Mapping[str, Any], kind: str) -> NotionResourceSelectionDTO | None:
        key = "database_id" if kind == "database" else "page_id"
        external_id = str(item.get(key) or item.get("id") or "").strip()
        if not external_id: return None
        metadata = ({
            "page_count": item.get("page_count"), "properties_schema": item.get("properties_schema") or {},
            "url": item.get("url") or "", "last_edited": item.get("last_edited") or "",
        } if kind == "database" else {
            "url": item.get("url") or "", "last_edited": item.get("last_edited") or "",
            "parent": item.get("parent") or {},
        })
        return NotionResourceSelectionDTO(
            external_id=external_id, title=str(item.get("title") or external_id), metadata=metadata,
        )

    def replace_connector_resources(self, connector_id: str, user_id: int,
        databases: Iterable[Mapping[str, Any]], pages: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
        self._assert_user(user_id)
        database_values = [value for item in databases if (value := self._selection(dict(item), "database")) is not None]
        page_values = [value for item in pages if (value := self._selection(dict(item), "page")) is not None]
        result = self._execute(REPLACE_NOTION_RESOURCES, NotionResourcesReplaceInputDTO(
            authority=self._authority, connector_id=connector_id,
            databases=database_values, pages=page_values,
        ))
        connector = self._project_connector(result.connector, requested_user_id=user_id) or {}
        return {"connector": connector, "resources": connector.get("sources", [])}

    def list_connector_resources(self, connector_id: str, user_id: int) -> list[dict[str, Any]]:
        if self._background:
            result = self._execute(LIST_NOTION_SYNC_RESOURCES, NotionSyncResourcesInputDTO(connector_id=connector_id))
        else:
            self._assert_user(user_id)
            result = self._execute(LIST_NOTION_RESOURCES, NotionResourcesListInputDTO(
                authority=self._authority, connector_id=connector_id,
            ))
        return [self._project_resource(item) for item in result.resources]

    def delete_connector_resource(self, connector_id: str, user_id: int, resource_id: str) -> bool:
        self._assert_user(user_id)
        return self._execute(DELETE_NOTION_RESOURCE, NotionResourceDeleteInputDTO(
            authority=self._authority, connector_id=connector_id, resource_id=resource_id,
        )).deleted

    def save_snapshot(self, connector_id: str, user_id: int, workspace_id: str,
        snapshot: Any, synced_resources: Iterable[Mapping[str, Any]] = ()) -> dict[str, Any]:
        payload = _snapshot_payload(snapshot)
        exact_resources = [NotionSyncedResourceDTO(
            resource_type=str(item.get("resource_type") or ""),
            external_id=str(item.get("external_id") or ""),
        ) for item in synced_resources if isinstance(item, Mapping)
            and str(item.get("resource_type") or "") in {"notion_database", "notion_page"}
            and str(item.get("external_id") or "").strip()]
        if self._background:
            result = self._execute(SAVE_NOTION_SYNC_SNAPSHOT, NotionSyncSnapshotSaveInputDTO(
                connector_id=connector_id, workspace_id=workspace_id,
                snapshot=payload, synced_resources=exact_resources,
            ), connector_id=connector_id)
        else:
            self._assert_user(user_id)
            result = self._execute(SAVE_NOTION_SNAPSHOT, NotionSnapshotSaveInputDTO(
                authority=self._authority, connector_id=connector_id,
                workspace_id=workspace_id, snapshot=payload,
                synced_resources=exact_resources,
            ))
        return dict(result.snapshot)

    def get_current_snapshot(self, workspace_id: str, connector_id: str, user_id: int) -> Optional[dict[str, Any]]:
        self._assert_user(user_id)
        result = self._execute(GET_CURRENT_NOTION_SNAPSHOT, NotionSnapshotCurrentInputDTO(
            authority=self._authority, connector_id=connector_id, workspace_id=workspace_id,
        ))
        return None if result.snapshot is None else dict(result.snapshot)

    def get_snapshot(self, connector_id: str, snapshot_version: str, user_id: int) -> Optional[dict[str, Any]]:
        self._assert_user(user_id)
        result = self._execute(GET_NOTION_SNAPSHOT, NotionSnapshotGetInputDTO(
            authority=self._authority, connector_id=connector_id, snapshot_version=snapshot_version,
        ))
        return None if result.snapshot is None else dict(result.snapshot)

    def list_snapshots(self, connector_id: str, user_id: int) -> list[dict[str, Any]]:
        self._assert_user(user_id)
        result = self._execute(LIST_NOTION_SNAPSHOTS, NotionSnapshotListInputDTO(
            authority=self._authority, connector_id=connector_id,
        ))
        return [item.model_dump(mode="json") for item in result.snapshots]

    def attach_thread_to_connector(self, connector_id: str, user_id: int, thread_id: str) -> dict[str, Any]:
        self._assert_user(user_id)
        result = self._execute(ATTACH_NOTION_THREAD, NotionThreadAttachInputDTO(
            authority=self._authority, connector_id=connector_id, thread_id=thread_id,
        ))
        return self._project_connector(result.connector, requested_user_id=user_id) or {}

    def get_connector_for_thread(self, thread_id: str, user_id: int) -> Optional[dict[str, Any]]:
        self._assert_user(user_id)
        result = self._execute(RESOLVE_NOTION_THREAD, NotionThreadResolveInputDTO(
            authority=self._authority, thread_id=thread_id,
        ))
        return self._project_connector(result.connector, requested_user_id=user_id)


class _DefaultNotionStoreRuntime:
    def __init__(self) -> None:
        self._lock = RLock()
        self._store: NotionConnectorStore | None = None

    def open(self, *, store: NotionConnectorStore) -> NotionConnectorStore:
        if not isinstance(store, NotionConnectorStore):
            raise TypeError("default Notion store must be exact")
        with self._lock:
            if self._store is not None and self._store is not store:
                raise configuration_invalid()
            if self._store is None:
                self._store = store
            return self._store

    def get(self) -> NotionConnectorStore:
        with self._lock: store = self._store
        if store is None: raise configuration_invalid()
        return store

    def close(self) -> None:
        with self._lock: self._store = None


_default_runtime = _DefaultNotionStoreRuntime()


def open_default_store(*, store: NotionConnectorStore) -> NotionConnectorStore: return _default_runtime.open(store=store)
def close_default_store() -> None: _default_runtime.close()
def default_store() -> NotionConnectorStore: return _default_runtime.get()
def create_connector(user_id: int, name: str, platform: str = "notion", config=None): return default_store().create_connector(user_id, name, platform, config)
def list_connectors(user_id: int): return default_store().list_connectors(user_id)
def list_sync_candidates(): return default_store().list_sync_candidates()
def get_connector(connector_id: str, user_id: Optional[int] = None): return default_store().get_connector(connector_id, user_id)
def get_active_connector_for_user(user_id: int): return default_store().get_active_connector_for_user(user_id)
def update_connector(connector_id: str, user_id: int, updates: Mapping[str, Any]): return default_store().update_connector(connector_id, user_id, updates)
def delete_connector(connector_id: str, user_id: int): return default_store().delete_connector(connector_id, user_id)
def save_auth_state(connector_id: str, user_id: int, **kwargs): return default_store().save_auth_state(connector_id, user_id, **kwargs)
def replace_connector_resources(connector_id: str, user_id: int, databases, pages): return default_store().replace_connector_resources(connector_id, user_id, databases, pages)
def list_connector_resources(connector_id: str, user_id: int): return default_store().list_connector_resources(connector_id, user_id)
def delete_connector_resource(connector_id: str, user_id: int, resource_id: str): return default_store().delete_connector_resource(connector_id, user_id, resource_id)
def save_snapshot(connector_id: str, user_id: int, workspace_id: str, snapshot, synced_resources=()): return default_store().save_snapshot(connector_id, user_id, workspace_id, snapshot, synced_resources)
def get_current_snapshot(workspace_id: str, connector_id: str, user_id: int): return default_store().get_current_snapshot(workspace_id, connector_id, user_id)
def get_snapshot(connector_id: str, snapshot_version: str, user_id: int): return default_store().get_snapshot(connector_id, snapshot_version, user_id)
def list_snapshots(connector_id: str, user_id: int): return default_store().list_snapshots(connector_id, user_id)
def attach_thread_to_connector(connector_id: str, user_id: int, thread_id: str): return default_store().attach_thread_to_connector(connector_id, user_id, thread_id)
def get_connector_for_thread(thread_id: str, user_id: int): return default_store().get_connector_for_thread(thread_id, user_id)


__all__ = ["NotionConnectorStore", "attach_thread_to_connector", "close_default_store", "create_connector", "default_store", "delete_connector", "delete_connector_resource", "get_active_connector_for_user", "get_connector", "get_connector_for_thread", "get_current_snapshot", "get_snapshot", "list_connector_resources", "list_connectors", "list_sync_candidates", "list_snapshots", "open_default_store", "replace_connector_resources", "save_auth_state", "save_snapshot", "update_connector"]
