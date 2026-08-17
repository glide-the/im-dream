"""Pure fake PostgreSQL transaction boundary for Notion store tests."""

from __future__ import annotations

from contextlib import AbstractContextManager
from copy import deepcopy
from datetime import datetime, timezone
import re
from typing import Any

from notion.store import NotionConnectorStore


TABLE_NAMES = (
    "resource_connectors",
    "connector_resources",
    "connector_resource_pages",
    "connector_snapshots",
    "connector_chat_threads",
)


class FakeCursor:
    def __init__(
        self,
        *,
        rows: list[dict[str, Any]] | None = None,
        row: dict[str, Any] | None = None,
        rowcount: int = 0,
    ) -> None:
        self._rows = deepcopy(rows or [])
        self._row = deepcopy(row)
        self.rowcount = rowcount

    def fetchall(self) -> list[dict[str, Any]]:
        return deepcopy(self._rows)

    def fetchone(self) -> dict[str, Any] | None:
        return deepcopy(self._row)


class FakeNotionDatabase:
    def __init__(self, *, users: set[int] | None = None) -> None:
        self.users = set(users or {7})
        self.tables: dict[str, list[dict[str, Any]]] = {
            table: [] for table in TABLE_NAMES
        }
        self.fail_marker: str | None = None


def _marker(query: str) -> str:
    match = re.search(r"/\*\s*(notion\.[a-z0-9_.]+)\s*\*/", query)
    return match.group(1) if match else ""


def _timestamp(value: Any) -> float:
    if isinstance(value, datetime):
        current = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return current.timestamp()
    return 0.0


class FakeNotionConnection:
    def __init__(self, database: FakeNotionDatabase) -> None:
        self.database = database
        self.tables = deepcopy(database.tables)
        self.executions: list[tuple[str, tuple[Any, ...]]] = []
        self.commits = 0
        self.rollbacks = 0

    def execute(
        self, query: str, parameters: tuple[Any, ...] | None = None
    ) -> FakeCursor:
        params = tuple(parameters or ())
        self.executions.append((query, params))
        if query.strip().startswith("SET TRANSACTION"):
            return FakeCursor()
        marker = _marker(query)
        if not marker:
            raise AssertionError(f"Notion query is missing a domain marker: {query}")
        if self.database.fail_marker == marker:
            raise RuntimeError(f"injected failure at {marker}")
        handler = getattr(self, "_" + marker.replace(".", "_"), None)
        if handler is None:
            raise AssertionError(f"Unhandled Notion query marker: {marker}")
        return handler(params)

    def commit(self) -> None:
        self.database.tables = deepcopy(self.tables)
        self.commits += 1

    def rollback(self) -> None:
        self.tables = deepcopy(self.database.tables)
        self.rollbacks += 1

    def _notion_connector_insert(self, params: tuple[Any, ...]) -> FakeCursor:
        connector_id, user_id, name, platform, config_json, created_at, updated_at = params
        if user_id not in self.database.users:
            raise RuntimeError("canonical user foreign key rejected")
        row = {
            "id": connector_id,
            "user_id": user_id,
            "name": name,
            "platform": platform,
            "auth_status": "pending",
            "config_json": config_json,
            "current_snapshot_version": None,
            "current_source_revision": None,
            "current_sync_cursor": None,
            "last_synced_at": None,
            "created_at": created_at,
            "updated_at": updated_at,
        }
        self.tables["resource_connectors"].append(row)
        return FakeCursor(row=row, rowcount=1)

    def _notion_connector_list(self, params: tuple[Any, ...]) -> FakeCursor:
        (user_id,) = params
        rows = [
            row for row in self.tables["resource_connectors"] if row["user_id"] == user_id
        ]
        rows.sort(
            key=lambda row: (
                _timestamp(row.get("updated_at")),
                _timestamp(row.get("created_at")),
            ),
            reverse=True,
        )
        return FakeCursor(rows=rows)

    def _connector_get(
        self, params: tuple[Any, ...], *, require_user: bool
    ) -> FakeCursor:
        connector_id = params[0]
        user_id = params[1] if require_user else None
        row = next(
            (
                item
                for item in self.tables["resource_connectors"]
                if item["id"] == connector_id
                and (user_id is None or item["user_id"] == user_id)
            ),
            None,
        )
        return FakeCursor(row=row, rowcount=int(row is not None))

    def _notion_connector_get_user(self, params: tuple[Any, ...]) -> FakeCursor:
        return self._connector_get(params, require_user=True)

    def _notion_connector_get_user_for_update(
        self, params: tuple[Any, ...]
    ) -> FakeCursor:
        return self._connector_get(params, require_user=True)

    def _notion_connector_get_any(self, params: tuple[Any, ...]) -> FakeCursor:
        return self._connector_get(params, require_user=False)

    def _notion_connector_get_any_for_update(
        self, params: tuple[Any, ...]
    ) -> FakeCursor:
        return self._connector_get(params, require_user=False)

    def _notion_connector_active(self, params: tuple[Any, ...]) -> FakeCursor:
        (user_id,) = params
        rank = {"authenticated": 0, "pending": 1, "expired": 2}
        rows = [
            row for row in self.tables["resource_connectors"] if row["user_id"] == user_id
        ]
        rows.sort(
            key=lambda row: (
                rank.get(str(row.get("auth_status")), 3),
                -_timestamp(row.get("updated_at")),
                -_timestamp(row.get("created_at")),
            )
        )
        return FakeCursor(row=rows[0] if rows else None)

    def _notion_connector_update(self, params: tuple[Any, ...]) -> FakeCursor:
        (
            name,
            platform,
            auth_status,
            config_json,
            current_snapshot_version,
            current_source_revision,
            current_sync_cursor,
            last_synced_at,
            updated_at,
            connector_id,
            user_id,
        ) = params
        row = next(
            (
                item
                for item in self.tables["resource_connectors"]
                if item["id"] == connector_id and item["user_id"] == user_id
            ),
            None,
        )
        if row is None:
            return FakeCursor()
        row.update(
            {
                "name": name,
                "platform": platform,
                "auth_status": auth_status,
                "config_json": config_json,
                "current_snapshot_version": current_snapshot_version,
                "current_source_revision": current_source_revision,
                "current_sync_cursor": current_sync_cursor,
                "last_synced_at": last_synced_at,
                "updated_at": updated_at,
            }
        )
        return FakeCursor(row=row, rowcount=1)

    def _notion_connector_delete(self, params: tuple[Any, ...]) -> FakeCursor:
        connector_id, user_id = params
        row = next(
            (
                item
                for item in self.tables["resource_connectors"]
                if item["id"] == connector_id and item["user_id"] == user_id
            ),
            None,
        )
        if row is None:
            return FakeCursor()
        self.tables["resource_connectors"].remove(row)
        resource_ids = {
            item["id"]
            for item in self.tables["connector_resources"]
            if item["connector_id"] == connector_id
        }
        self.tables["connector_resources"] = [
            item
            for item in self.tables["connector_resources"]
            if item["connector_id"] != connector_id
        ]
        self.tables["connector_resource_pages"] = [
            item
            for item in self.tables["connector_resource_pages"]
            if item["resource_id"] not in resource_ids
        ]
        for table in ("connector_snapshots", "connector_chat_threads"):
            self.tables[table] = [
                item for item in self.tables[table] if item["connector_id"] != connector_id
            ]
        return FakeCursor(row={"id": connector_id}, rowcount=1)

    def _delete_resources(self, predicate) -> list[dict[str, Any]]:
        removed = [item for item in self.tables["connector_resources"] if predicate(item)]
        removed_ids = {item["id"] for item in removed}
        self.tables["connector_resources"] = [
            item for item in self.tables["connector_resources"] if item["id"] not in removed_ids
        ]
        self.tables["connector_resource_pages"] = [
            item
            for item in self.tables["connector_resource_pages"]
            if item["resource_id"] not in removed_ids
        ]
        return removed

    def _notion_resource_delete_selected(self, params: tuple[Any, ...]) -> FakeCursor:
        (connector_id,) = params
        removed = self._delete_resources(
            lambda item: item["connector_id"] == connector_id
            and item["resource_type"] in {"notion_database", "notion_page"}
        )
        return FakeCursor(rowcount=len(removed))

    def _notion_resource_insert(self, params: tuple[Any, ...]) -> FakeCursor:
        (
            resource_id,
            connector_id,
            resource_type,
            external_id,
            title,
            metadata_json,
            created_at,
            updated_at,
        ) = params
        row = {
            "id": resource_id,
            "connector_id": connector_id,
            "resource_type": resource_type,
            "external_id": external_id,
            "title": title,
            "metadata_json": metadata_json,
            "sync_status": "synced",
            "created_at": created_at,
            "updated_at": updated_at,
        }
        self.tables["connector_resources"].append(row)
        return FakeCursor(rowcount=1)

    def _notion_resource_list(self, params: tuple[Any, ...]) -> FakeCursor:
        (connector_id,) = params
        rows = [
            item
            for item in self.tables["connector_resources"]
            if item["connector_id"] == connector_id
        ]
        rows.sort(
            key=lambda item: (
                item["resource_type"],
                str(item["title"]).casefold(),
                str(item["title"]),
                -_timestamp(item.get("created_at")),
            )
        )
        return FakeCursor(rows=rows)

    def _notion_resource_delete(self, params: tuple[Any, ...]) -> FakeCursor:
        resource_id, connector_id = params
        removed = self._delete_resources(
            lambda item: item["id"] == resource_id
            and item["connector_id"] == connector_id
        )
        return FakeCursor(
            row={"id": resource_id} if removed else None, rowcount=len(removed)
        )

    def _notion_snapshot_upsert(self, params: tuple[Any, ...]) -> FakeCursor:
        (
            snapshot_id,
            connector_id,
            snapshot_version,
            source_revision,
            sync_cursor,
            fetched_at,
            state,
            snapshot_json,
            created_at,
            updated_at,
        ) = params
        row = next(
            (
                item
                for item in self.tables["connector_snapshots"]
                if item["connector_id"] == connector_id
                and item["snapshot_version"] == snapshot_version
            ),
            None,
        )
        if row is None:
            row = {
                "id": snapshot_id,
                "connector_id": connector_id,
                "snapshot_version": snapshot_version,
                "created_at": created_at,
            }
            self.tables["connector_snapshots"].append(row)
        row.update(
            {
                "source_revision": source_revision,
                "sync_cursor": sync_cursor,
                "fetched_at": fetched_at,
                "state": state,
                "snapshot_json": snapshot_json,
                "updated_at": updated_at,
            }
        )
        return FakeCursor(row=row, rowcount=1)

    def _notion_resource_find_database(self, params: tuple[Any, ...]) -> FakeCursor:
        connector_id, external_id = params
        row = next(
            (
                {"id": item["id"]}
                for item in self.tables["connector_resources"]
                if item["connector_id"] == connector_id
                and item["resource_type"] == "notion_database"
                and item["external_id"] == external_id
            ),
            None,
        )
        return FakeCursor(row=row)

    def _notion_resource_page_delete(self, params: tuple[Any, ...]) -> FakeCursor:
        (resource_id,) = params
        before = len(self.tables["connector_resource_pages"])
        self.tables["connector_resource_pages"] = [
            item
            for item in self.tables["connector_resource_pages"]
            if item["resource_id"] != resource_id
        ]
        return FakeCursor(rowcount=before - len(self.tables["connector_resource_pages"]))

    def _notion_resource_page_insert(self, params: tuple[Any, ...]) -> FakeCursor:
        (
            page_row_id,
            resource_id,
            page_id,
            title,
            last_edited,
            properties_json,
            page_json,
            created_at,
            updated_at,
        ) = params
        self.tables["connector_resource_pages"].append(
            {
                "id": page_row_id,
                "resource_id": resource_id,
                "page_id": page_id,
                "title": title,
                "last_edited": last_edited,
                "properties_json": properties_json,
                "page_json": page_json,
                "created_at": created_at,
                "updated_at": updated_at,
            }
        )
        return FakeCursor(rowcount=1)

    def _snapshot_row(
        self, connector_id: str, version: str, user_id: int
    ) -> dict[str, Any] | None:
        owns = any(
            item["id"] == connector_id and item["user_id"] == user_id
            for item in self.tables["resource_connectors"]
        )
        if not owns:
            return None
        return next(
            (
                item
                for item in self.tables["connector_snapshots"]
                if item["connector_id"] == connector_id
                and item["snapshot_version"] == version
            ),
            None,
        )

    def _notion_snapshot_current(self, params: tuple[Any, ...]) -> FakeCursor:
        connector_id, user_id = params
        connector = next(
            (
                item
                for item in self.tables["resource_connectors"]
                if item["id"] == connector_id and item["user_id"] == user_id
            ),
            None,
        )
        version = connector.get("current_snapshot_version") if connector else None
        row = self._snapshot_row(connector_id, version, user_id) if version else None
        return FakeCursor(row=row)

    def _notion_snapshot_get(self, params: tuple[Any, ...]) -> FakeCursor:
        connector_id, snapshot_version, user_id = params
        return FakeCursor(row=self._snapshot_row(connector_id, snapshot_version, user_id))

    def _notion_snapshot_list(self, params: tuple[Any, ...]) -> FakeCursor:
        connector_id, user_id = params
        owns = any(
            item["id"] == connector_id and item["user_id"] == user_id
            for item in self.tables["resource_connectors"]
        )
        rows = (
            [
                item
                for item in self.tables["connector_snapshots"]
                if item["connector_id"] == connector_id
            ]
            if owns
            else []
        )
        rows.sort(key=lambda item: _timestamp(item.get("created_at")), reverse=True)
        return FakeCursor(rows=rows)

    def _notion_thread_upsert(self, params: tuple[Any, ...]) -> FakeCursor:
        row_id, connector_id, thread_id, created_at, updated_at = params
        row = next(
            (
                item
                for item in self.tables["connector_chat_threads"]
                if item["connector_id"] == connector_id
                and item["thread_id"] == thread_id
            ),
            None,
        )
        if row is None:
            row = {
                "id": row_id,
                "connector_id": connector_id,
                "thread_id": thread_id,
                "created_at": created_at,
            }
            self.tables["connector_chat_threads"].append(row)
        row["updated_at"] = updated_at
        return FakeCursor(rowcount=1)

    def _notion_thread_connector(self, params: tuple[Any, ...]) -> FakeCursor:
        thread_id, user_id = params
        candidates = [
            item
            for item in self.tables["connector_chat_threads"]
            if item["thread_id"] == thread_id
        ]
        candidates.sort(key=lambda item: _timestamp(item["updated_at"]), reverse=True)
        for thread in candidates:
            connector = next(
                (
                    item
                    for item in self.tables["resource_connectors"]
                    if item["id"] == thread["connector_id"]
                    and item["user_id"] == user_id
                ),
                None,
            )
            if connector is not None:
                return FakeCursor(row=connector)
        return FakeCursor()


class FakeConnectionManager(AbstractContextManager[FakeNotionConnection]):
    def __init__(self, connection: FakeNotionConnection) -> None:
        self.connection = connection

    def __enter__(self) -> FakeNotionConnection:
        return self.connection

    def __exit__(self, *_args: Any) -> bool:
        return False


class FakeNotionPool:
    def __init__(self, database: FakeNotionDatabase) -> None:
        self.database = database
        self.connections: list[FakeNotionConnection] = []

    def connection(self, timeout: float | None = None) -> FakeConnectionManager:
        del timeout
        connection = FakeNotionConnection(self.database)
        self.connections.append(connection)
        return FakeConnectionManager(connection)


def build_fake_notion_store(
    *, users: set[int] | None = None
) -> tuple[NotionConnectorStore, FakeNotionDatabase, FakeNotionPool]:
    database = FakeNotionDatabase(users=users)
    pool = FakeNotionPool(database)
    return NotionConnectorStore(pool), database, pool


__all__ = [
    "FakeNotionDatabase",
    "FakeNotionPool",
    "TABLE_NAMES",
    "build_fake_notion_store",
]
