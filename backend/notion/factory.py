# [Input] Notion connector auth, operation, store, and sync helpers.
# [Output] Provide a compact facade for routes and Claude Agent workspace attach.
# [Pos] factory node in backend/notion
# [Sync] 2026-07-04: initial Notion connector facade for auth, discovery,
#                    selection, snapshot sync, and workspace materialization.

"""Connector facade for the Notion resource connector backend."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

from . import auth, operations, store, sync
from .errors import NotionConnectorNotFoundError, NotionSnapshotNotReadyError


@dataclass
class NotionConnectorFacade:
    """Thin orchestration wrapper for a user-owned Notion connector."""

    user_id: int
    connector_id: Optional[str] = None

    def _resolve_connector(self, connector_id: Optional[str] = None) -> dict[str, Any]:
        resolved = connector_id or self.connector_id
        if resolved:
            connector = store.get_connector(resolved, self.user_id)
            if connector is None:
                raise NotionConnectorNotFoundError(
                    f"Connector {resolved!r} not found for user_id={self.user_id}"
                )
            return connector
        active = store.get_active_connector_for_user(self.user_id)
        if active is None:
            raise NotionConnectorNotFoundError(
                f"No Notion connector found for user_id={self.user_id}"
            )
        self.connector_id = str(active["id"])
        return active

    def create_connector(
        self,
        name: str,
        platform: str = "notion",
        config: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        return store.create_connector(self.user_id, name=name, platform=platform, config=config)

    def list_connectors(self) -> list[dict[str, Any]]:
        return store.list_connectors(self.user_id)

    def get_connector(self, connector_id: Optional[str] = None) -> dict[str, Any]:
        return self._resolve_connector(connector_id)

    def update_connector(self, updates: Mapping[str, Any], connector_id: Optional[str] = None) -> dict[str, Any]:
        connector = self._resolve_connector(connector_id)
        return store.update_connector(str(connector["id"]), self.user_id, updates)

    def delete_connector(self, connector_id: Optional[str] = None) -> bool:
        connector = self._resolve_connector(connector_id)
        return store.delete_connector(str(connector["id"]), self.user_id)

    async def start_auth(self, connector_id: Optional[str] = None) -> dict[str, Any]:
        connector = self._resolve_connector(connector_id)
        result = await auth.start_login(connector.get("config"))
        updated = store.save_auth_state(
            str(connector["id"]),
            self.user_id,
            auth_status="pending",
            config_patch={"notion_home": result.notion_home},
            verification_url=result.verification_url,
            verification_code=result.verification_code,
            poll_interval_seconds=result.poll_interval_seconds,
        )
        return {
            "connector": updated,
            "verificationUrl": result.verification_url,
            "verificationCode": result.verification_code,
            "pollIntervalSeconds": result.poll_interval_seconds,
            "notionHome": result.notion_home,
            "auth_status": "pending",
        }

    async def poll_auth(self, connector_id: Optional[str] = None) -> dict[str, Any]:
        connector = self._resolve_connector(connector_id)
        result = await auth.poll_login(connector.get("config"))
        updated = store.save_auth_state(
            str(connector["id"]),
            self.user_id,
            auth_status=result.status,
            config_patch={"notion_home": result.notion_home},
            error_detail=result.detail or None,
        )
        return {
            "connector": updated,
            "auth_status": result.status,
            "status": result.status,
            "detail": result.detail,
            "notionHome": result.notion_home,
        }

    async def verify_auth(self, connector_id: Optional[str] = None) -> dict[str, Any]:
        connector = self._resolve_connector(connector_id)
        result = await auth.verify_status(connector.get("config"))
        updated = store.save_auth_state(
            str(connector["id"]),
            self.user_id,
            auth_status=result.status,
            config_patch={"notion_home": result.notion_home},
            error_detail=result.detail or None,
        )
        return {
            "connector": updated,
            "auth_status": result.status,
            "status": result.status,
            "detail": result.detail,
            "notionHome": result.notion_home,
        }

    async def list_databases(self, connector_id: Optional[str] = None, query: Optional[str] = None) -> list[dict[str, Any]]:
        connector = self._resolve_connector(connector_id)
        selected_ids = {
            str(resource.get("external_id") or "")
            for resource in store.list_connector_resources(str(connector["id"]), self.user_id)
            if resource.get("resource_type") == "notion_database"
        }
        records = await operations.discover_databases(connector.get("config"), query=query)
        for record in records:
            record["selected"] = record.get("database_id") in selected_ids
        return records

    async def list_pages(self, connector_id: Optional[str] = None, query: Optional[str] = None) -> list[dict[str, Any]]:
        connector = self._resolve_connector(connector_id)
        selected_ids = {
            str(resource.get("external_id") or "")
            for resource in store.list_connector_resources(str(connector["id"]), self.user_id)
            if resource.get("resource_type") == "notion_page"
        }
        records = await operations.discover_pages(connector.get("config"), query=query)
        for record in records:
            record["selected"] = record.get("page_id") in selected_ids
        return records

    def list_selected_resources(self, connector_id: Optional[str] = None) -> list[dict[str, Any]]:
        connector = self._resolve_connector(connector_id)
        return store.list_connector_resources(str(connector["id"]), self.user_id)

    async def select_resources(
        self,
        databases: Iterable[Mapping[str, Any]],
        pages: Iterable[Mapping[str, Any]],
        connector_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> dict[str, Any]:
        connector = self._resolve_connector(connector_id)
        store.replace_connector_resources(str(connector["id"]), self.user_id, databases, pages)
        return await self.sync(connector_id=str(connector["id"]), workspace_id=workspace_id)

    async def sync(
        self,
        connector_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> dict[str, Any]:
        connector = self._resolve_connector(connector_id)
        if str(connector.get("auth_status") or "") != "authenticated":
            raise NotionSnapshotNotReadyError("Connector is not authenticated yet.")

        selected_resources = store.list_connector_resources(str(connector["id"]), self.user_id)
        if not selected_resources:
            raise NotionSnapshotNotReadyError("No selected Notion resources available.")

        ops = operations.NotionOperationClient(connector.get("config"))
        effective_workspace_id = workspace_id or str(connector.get("current_workspace_id") or connector["id"])
        snapshot = await sync.build_canonical_snapshot(
            connector=connector,
            selected_resources=selected_resources,
            workspace_id=effective_workspace_id,
            operations=ops,
        )
        saved_snapshot = store.save_snapshot(
            str(connector["id"]),
            self.user_id,
            effective_workspace_id,
            snapshot,
        )
        return {
            "connector": store.get_connector(str(connector["id"]), self.user_id) or connector,
            "snapshot": saved_snapshot,
            "snapshotIdentity": saved_snapshot.get("identity") if isinstance(saved_snapshot, dict) else None,
            "databaseCount": len(saved_snapshot.get("databases") or []),
            "pageCount": len(saved_snapshot.get("pages") or {}),
            "synced": True,
        }

    def get_current_snapshot(
        self,
        connector_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        connector = self._resolve_connector(connector_id)
        return store.get_current_snapshot(
            workspace_id or str(connector.get("current_workspace_id") or connector["id"]),
            str(connector["id"]),
            self.user_id,
        )

    def materialize_workspace(
        self,
        workspace_path: Path,
        connector_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> None:
        connector = self._resolve_connector(connector_id)
        snapshot = self.get_current_snapshot(connector_id=str(connector["id"]), workspace_id=workspace_id)
        if snapshot is None:
            sync.materialize_workspace_snapshot(workspace_path, connector=connector, snapshot=None)
            return
        sync.materialize_workspace_snapshot(workspace_path, connector=connector, snapshot=snapshot)


def build_notion_facade(user_id: int, connector_id: Optional[str] = None) -> NotionConnectorFacade:
    """Convenience constructor for router/service callers."""

    return NotionConnectorFacade(user_id=user_id, connector_id=connector_id)

