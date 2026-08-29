# [Input] Unified PostgreSQL pool/UoW and canonical Notion snapshot payloads.
# [Output] Domain-scoped connector, resource, snapshot, page, thread, and scheduled-sync candidate storage.
# [Pos] PostgreSQL-only runtime store for backend/notion.
# [Sync] 2026-08-28: expose authenticated connector candidates and project the versioned snapshot-sync policy from existing config JSON without schema changes.
# [Sync] 2026-08-28: keep new resource selections pending until their exact IDs
#                    are committed in a successful lightweight snapshot.

"""PostgreSQL persistence for Notion resource connectors.

The five tables are created only by Admin-owned Drizzle migrations. This
module owns runtime queries and transactions; it never creates schema objects
and has no alternate database implementation.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
import json
from threading import RLock
from typing import Any, Optional, Protocol, cast
from uuid import uuid4

try:
    from persistence.postgres import ConnectionPool, PostgresPool
    from persistence.unit_of_work import PostgresUnitOfWork, UnitOfWork
except ModuleNotFoundError:  # pragma: no cover - package import compatibility
    from backend.persistence.postgres import ConnectionPool, PostgresPool
    from backend.persistence.unit_of_work import PostgresUnitOfWork, UnitOfWork

from libs.claude_agent_kit.server.notion_snapshot import (
    CanonicalWorkspaceSnapshot,
    SnapshotLifecycleState,
)

from .errors import (
    NotionConnectorError,
    NotionConnectorNotFoundError,
    NotionSnapshotNotReadyError,
)
from .sync_policy import SYNC_POLICY_CONFIG_KEY, resolve_sync_policy


class _Cursor(Protocol):
    rowcount: int

    def fetchone(self) -> Any: ...

    def fetchall(self) -> list[Any]: ...


UnitOfWorkFactory = Callable[[bool], UnitOfWork]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _json_loads(value: Any, *, field: str, expected: type[Any]) -> Any:
    if isinstance(value, expected):
        return value
    if value in (None, ""):
        parsed: Any = expected()
    else:
        try:
            parsed = json.loads(str(value))
        except (TypeError, ValueError, json.JSONDecodeError):
            raise NotionConnectorError(f"Stored {field} is invalid.") from None
    if not isinstance(parsed, expected):
        raise NotionConnectorError(f"Stored {field} has an invalid shape.")
    return parsed


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _snapshot_payload(
    snapshot: CanonicalWorkspaceSnapshot | dict[str, Any],
) -> dict[str, Any]:
    if is_dataclass(snapshot):
        return cast(dict[str, Any], asdict(snapshot))
    if isinstance(snapshot, dict):
        return dict(snapshot)
    return {}


def _row_mapping(row: Any | None) -> Optional[dict[str, Any]]:
    if row is None:
        return None
    if isinstance(row, Mapping):
        return dict(row)
    try:
        return dict(row)
    except (TypeError, ValueError):
        raise NotionConnectorError("PostgreSQL returned an invalid row shape.") from None


def _iso_timestamp(value: Any) -> Any:
    if isinstance(value, datetime):
        normalized = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
        return normalized.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return value


def _db_timestamp(
    value: Any,
    *,
    required: bool = False,
    field: str = "timestamp",
) -> datetime | None:
    if value in (None, ""):
        if required:
            raise NotionSnapshotNotReadyError(f"Snapshot {field} is missing.")
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            raise NotionSnapshotNotReadyError(
                f"Snapshot {field} must be an ISO timestamp with timezone."
            ) from None
    if parsed.tzinfo is None:
        raise NotionSnapshotNotReadyError(
            f"Snapshot {field} must include a timezone."
        )
    return parsed.astimezone(timezone.utc)


class NotionConnectorRepository:
    """Domain SQL for the five canonical Notion Connector tables."""

    def __init__(self, connection: Any) -> None:
        self._connection = connection

    def _execute(self, query: str, parameters: tuple[Any, ...] = ()) -> _Cursor:
        return cast(_Cursor, self._connection.execute(query, parameters))

    def insert_connector(
        self,
        *,
        connector_id: str,
        user_id: int,
        name: str,
        platform: str,
        config_json: str,
        now: datetime,
    ) -> dict[str, Any]:
        row = self._execute(
            """
            /* notion.connector.insert */
            INSERT INTO resource_connectors (
              id, user_id, name, platform, auth_status, config_json,
              created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, 'pending', %s, %s, %s)
            RETURNING *
            """,
            (connector_id, user_id, name, platform, config_json, now, now),
        ).fetchone()
        return _row_mapping(row) or {}

    def list_connectors(self, user_id: int) -> list[dict[str, Any]]:
        rows = self._execute(
            """
            /* notion.connector.list */
            SELECT *
            FROM resource_connectors
            WHERE user_id = %s
            ORDER BY updated_at DESC NULLS LAST, created_at DESC NULLS LAST
            """,
            (user_id,),
        ).fetchall()
        return [_row_mapping(row) or {} for row in rows]

    def list_sync_candidates(self) -> list[dict[str, Any]]:
        rows = self._execute(
            """
            /* notion.connector.sync_candidates */
            SELECT *
            FROM resource_connectors
            WHERE platform = 'notion' AND auth_status = 'authenticated'
            ORDER BY updated_at ASC NULLS FIRST, created_at ASC NULLS FIRST
            """
        ).fetchall()
        return [_row_mapping(row) or {} for row in rows]

    def get_connector(
        self,
        connector_id: str,
        user_id: int | None = None,
        *,
        for_update: bool = False,
    ) -> Optional[dict[str, Any]]:
        marker = (
            "/* notion.connector.get_user_for_update */"
            if user_id is not None and for_update
            else "/* notion.connector.get_user */"
            if user_id is not None
            else "/* notion.connector.get_any_for_update */"
            if for_update
            else "/* notion.connector.get_any */"
        )
        user_clause = "AND user_id = %s" if user_id is not None else ""
        lock_clause = "FOR UPDATE" if for_update else ""
        parameters: tuple[Any, ...] = (
            (connector_id, user_id) if user_id is not None else (connector_id,)
        )
        row = self._execute(
            f"""
            {marker}
            SELECT *
            FROM resource_connectors
            WHERE id = %s {user_clause}
            LIMIT 1
            {lock_clause}
            """,
            parameters,
        ).fetchone()
        return _row_mapping(row)

    def get_active_connector(self, user_id: int) -> Optional[dict[str, Any]]:
        row = self._execute(
            """
            /* notion.connector.active */
            SELECT *
            FROM resource_connectors
            WHERE user_id = %s
            ORDER BY
              CASE auth_status
                WHEN 'authenticated' THEN 0
                WHEN 'pending' THEN 1
                WHEN 'expired' THEN 2
                ELSE 3
              END,
              updated_at DESC NULLS LAST,
              created_at DESC NULLS LAST
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()
        return _row_mapping(row)

    def update_connector(
        self,
        row: Mapping[str, Any],
        *,
        user_id: int,
    ) -> Optional[dict[str, Any]]:
        result = self._execute(
            """
            /* notion.connector.update */
            UPDATE resource_connectors
            SET name = %s,
                platform = %s,
                auth_status = %s,
                config_json = %s,
                current_snapshot_version = %s,
                current_source_revision = %s,
                current_sync_cursor = %s,
                last_synced_at = %s,
                updated_at = %s
            WHERE id = %s AND user_id = %s
            RETURNING *
            """,
            (
                row["name"],
                row["platform"],
                row["auth_status"],
                row["config_json"],
                row.get("current_snapshot_version"),
                row.get("current_source_revision"),
                row.get("current_sync_cursor"),
                _db_timestamp(row.get("last_synced_at"), field="last_synced_at"),
                row["updated_at"],
                row["id"],
                user_id,
            ),
        ).fetchone()
        return _row_mapping(result)

    def delete_connector(self, connector_id: str, user_id: int) -> bool:
        return (
            self._execute(
                """
                /* notion.connector.delete */
                DELETE FROM resource_connectors
                WHERE id = %s AND user_id = %s
                RETURNING id
                """,
                (connector_id, user_id),
            ).fetchone()
            is not None
        )

    def delete_selected_resources(self, connector_id: str) -> None:
        self._execute(
            """
            /* notion.resource.delete_selected */
            DELETE FROM connector_resources
            WHERE connector_id = %s
              AND resource_type IN ('notion_database', 'notion_page')
            """,
            (connector_id,),
        )

    def insert_resource(
        self,
        *,
        resource_id: str,
        connector_id: str,
        resource_type: str,
        external_id: str,
        title: str,
        metadata_json: str,
        now: datetime,
    ) -> None:
        self._execute(
            """
            /* notion.resource.insert */
            INSERT INTO connector_resources (
              id, connector_id, resource_type, external_id, title,
              metadata_json, sync_status, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, 'pending', %s, %s)
            """,
            (
                resource_id,
                connector_id,
                resource_type,
                external_id,
                title,
                metadata_json,
                now,
                now,
            ),
        )

    def mark_resource_synced(
        self,
        *,
        connector_id: str,
        resource_type: str,
        external_id: str,
        now: datetime,
    ) -> None:
        self._execute(
            """
            /* notion.resource.mark_synced */
            UPDATE connector_resources
            SET sync_status = 'synced', updated_at = %s
            WHERE connector_id = %s
              AND resource_type = %s
              AND external_id = %s
            """,
            (now, connector_id, resource_type, external_id),
        )

    def list_resources(self, connector_id: str) -> list[dict[str, Any]]:
        rows = self._execute(
            """
            /* notion.resource.list */
            SELECT *
            FROM connector_resources
            WHERE connector_id = %s
            ORDER BY resource_type, lower(title), title, created_at DESC NULLS LAST
            """,
            (connector_id,),
        ).fetchall()
        return [_row_mapping(row) or {} for row in rows]

    def delete_resource(self, connector_id: str, resource_id: str) -> bool:
        return (
            self._execute(
                """
                /* notion.resource.delete */
                DELETE FROM connector_resources
                WHERE id = %s AND connector_id = %s
                RETURNING id
                """,
                (resource_id, connector_id),
            ).fetchone()
            is not None
        )

    def upsert_snapshot(
        self,
        *,
        snapshot_id: str,
        connector_id: str,
        snapshot_version: str,
        source_revision: str,
        sync_cursor: str,
        fetched_at: datetime,
        state: str,
        snapshot_json: str,
        now: datetime,
    ) -> dict[str, Any]:
        row = self._execute(
            """
            /* notion.snapshot.upsert */
            INSERT INTO connector_snapshots (
              id, connector_id, snapshot_version, source_revision, sync_cursor,
              fetched_at, state, snapshot_json, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (connector_id, snapshot_version) DO UPDATE SET
              source_revision = EXCLUDED.source_revision,
              sync_cursor = EXCLUDED.sync_cursor,
              fetched_at = EXCLUDED.fetched_at,
              state = EXCLUDED.state,
              snapshot_json = EXCLUDED.snapshot_json,
              updated_at = EXCLUDED.updated_at
            RETURNING *
            """,
            (
                snapshot_id,
                connector_id,
                snapshot_version,
                source_revision,
                sync_cursor,
                fetched_at,
                state,
                snapshot_json,
                fetched_at,
                now,
            ),
        ).fetchone()
        return _row_mapping(row) or {}

    def find_database_resource(
        self, connector_id: str, external_id: str
    ) -> Optional[str]:
        row = self._execute(
            """
            /* notion.resource.find_database */
            SELECT id
            FROM connector_resources
            WHERE connector_id = %s
              AND resource_type = 'notion_database'
              AND external_id = %s
            LIMIT 1
            """,
            (connector_id, external_id),
        ).fetchone()
        mapped = _row_mapping(row)
        return str(mapped["id"]) if mapped is not None else None

    def replace_resource_pages(
        self,
        resource_id: str,
        pages: Iterable[Mapping[str, Any]],
        *,
        fetched_at: datetime,
        now: datetime,
    ) -> None:
        self._execute(
            """
            /* notion.resource_page.delete */
            DELETE FROM connector_resource_pages
            WHERE resource_id = %s
            """,
            (resource_id,),
        )
        for page in pages:
            page_map = dict(page)
            page_id = str(page_map.get("page_id") or page_map.get("id") or "").strip()
            if not page_id:
                continue
            self._execute(
                """
                /* notion.resource_page.insert */
                INSERT INTO connector_resource_pages (
                  id, resource_id, page_id, title, last_edited,
                  properties_json, page_json, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    str(uuid4()),
                    resource_id,
                    page_id,
                    str(page_map.get("title") or page_id),
                    _db_timestamp(page_map.get("last_edited"), field="last_edited"),
                    _json_dumps(page_map.get("properties") or {}),
                    _json_dumps(page_map),
                    fetched_at,
                    now,
                ),
            )

    def get_current_snapshot(
        self, connector_id: str, user_id: int
    ) -> Optional[dict[str, Any]]:
        row = self._execute(
            """
            /* notion.snapshot.current */
            SELECT s.*
            FROM resource_connectors AS c
            JOIN connector_snapshots AS s
              ON s.connector_id = c.id
             AND s.snapshot_version = c.current_snapshot_version
            WHERE c.id = %s AND c.user_id = %s
            LIMIT 1
            """,
            (connector_id, user_id),
        ).fetchone()
        return _row_mapping(row)

    def get_snapshot(
        self, connector_id: str, snapshot_version: str, user_id: int
    ) -> Optional[dict[str, Any]]:
        row = self._execute(
            """
            /* notion.snapshot.get */
            SELECT s.*
            FROM connector_snapshots AS s
            JOIN resource_connectors AS c ON c.id = s.connector_id
            WHERE s.connector_id = %s
              AND s.snapshot_version = %s
              AND c.user_id = %s
            LIMIT 1
            """,
            (connector_id, snapshot_version, user_id),
        ).fetchone()
        return _row_mapping(row)

    def list_snapshots(self, connector_id: str, user_id: int) -> list[dict[str, Any]]:
        rows = self._execute(
            """
            /* notion.snapshot.list */
            SELECT s.*
            FROM connector_snapshots AS s
            JOIN resource_connectors AS c ON c.id = s.connector_id
            WHERE s.connector_id = %s AND c.user_id = %s
            ORDER BY s.created_at DESC NULLS LAST
            """,
            (connector_id, user_id),
        ).fetchall()
        return [_row_mapping(row) or {} for row in rows]

    def attach_thread(
        self,
        connector_id: str,
        thread_id: str,
        *,
        now: datetime,
    ) -> None:
        self._execute(
            """
            /* notion.thread.upsert */
            INSERT INTO connector_chat_threads (
              id, connector_id, thread_id, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (connector_id, thread_id) DO UPDATE SET
              updated_at = EXCLUDED.updated_at
            """,
            (str(uuid4()), connector_id, thread_id, now, now),
        )

    def get_connector_for_thread(
        self, thread_id: str, user_id: int
    ) -> Optional[dict[str, Any]]:
        row = self._execute(
            """
            /* notion.thread.connector */
            SELECT c.*
            FROM connector_chat_threads AS t
            JOIN resource_connectors AS c ON c.id = t.connector_id
            WHERE t.thread_id = %s AND c.user_id = %s
            ORDER BY t.updated_at DESC NULLS LAST
            LIMIT 1
            """,
            (thread_id, user_id),
        ).fetchone()
        return _row_mapping(row)


class NotionConnectorStore:
    """Transactional application service preserving the historical store API."""

    def __init__(
        self,
        pool: ConnectionPool | None = None,
        *,
        unit_of_work_factory: UnitOfWorkFactory | None = None,
    ) -> None:
        if (pool is None) == (unit_of_work_factory is None):
            raise ValueError("exactly one PostgreSQL dependency is required")
        self._unit_of_work_factory = unit_of_work_factory or (
            lambda read_only: PostgresUnitOfWork(
                cast(ConnectionPool, pool), read_only=read_only
            )
        )

    def _unit_of_work(self, *, read_only: bool) -> UnitOfWork:
        return self._unit_of_work_factory(read_only)

    @staticmethod
    def _connector_from_row(row: Any | None) -> Optional[dict[str, Any]]:
        data = _row_mapping(row)
        if data is None:
            return None
        config = _json_loads(data.get("config_json"), field="connector config", expected=dict)
        data["config"] = config
        data["selected_databases"] = list(config.get("selected_databases") or [])
        data["selected_pages"] = list(config.get("selected_pages") or [])
        data.pop("config_json", None)
        for field in ("last_synced_at", "created_at", "updated_at"):
            data[field] = _iso_timestamp(data.get(field))
        data["sync_policy"] = resolve_sync_policy(
            config.get(SYNC_POLICY_CONFIG_KEY),
            last_synced_at=data.get("last_synced_at"),
        )
        return data

    @staticmethod
    def _resource_from_row(row: Any) -> dict[str, Any]:
        data = _row_mapping(row) or {}
        data["metadata"] = _json_loads(
            data.get("metadata_json"), field="resource metadata", expected=dict
        )
        data.pop("metadata_json", None)
        for field in ("created_at", "updated_at"):
            data[field] = _iso_timestamp(data.get(field))
        data["selected"] = True
        return data

    @staticmethod
    def _snapshot_from_row(row: Any | None) -> Optional[dict[str, Any]]:
        data = _row_mapping(row)
        if data is None:
            return None
        return cast(
            dict[str, Any],
            _json_loads(data.get("snapshot_json"), field="snapshot", expected=dict),
        )

    def _attach_connector_resources(
        self,
        repository: NotionConnectorRepository,
        connector: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if connector is None:
            return None
        result = dict(connector)
        result["sources"] = [
            self._resource_from_row(row)
            for row in repository.list_resources(str(result["id"]))
        ]
        return result

    @staticmethod
    def _require_connector_row(
        repository: NotionConnectorRepository,
        connector_id: str,
        user_id: int,
        *,
        for_update: bool = False,
    ) -> dict[str, Any]:
        connector = repository.get_connector(
            connector_id, user_id, for_update=for_update
        )
        if connector is None:
            raise NotionConnectorNotFoundError(
                f"Connector {connector_id!r} not found for user_id={user_id}"
            )
        return connector

    def create_connector(
        self,
        user_id: int,
        name: str,
        platform: str = "notion",
        config: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        with self._unit_of_work(read_only=False) as unit_of_work:
            repository = NotionConnectorRepository(unit_of_work.connection)
            row = repository.insert_connector(
                connector_id=str(uuid4()),
                user_id=user_id,
                name=name.strip() or "Notion Connector",
                platform=platform.strip() or "notion",
                config_json=_json_dumps(config or {}),
                now=_utcnow(),
            )
            connector = self._attach_connector_resources(
                repository, self._connector_from_row(row)
            )
            unit_of_work.commit()
        return connector or {}

    def list_connectors(self, user_id: int) -> list[dict[str, Any]]:
        with self._unit_of_work(read_only=True) as unit_of_work:
            repository = NotionConnectorRepository(unit_of_work.connection)
            connectors: list[dict[str, Any]] = []
            for row in repository.list_connectors(user_id):
                connector = self._attach_connector_resources(
                    repository, self._connector_from_row(row)
                )
                if connector is not None:
                    connectors.append(connector)
            return connectors

    def list_sync_candidates(self) -> list[dict[str, Any]]:
        """Return server-owned scheduled-sync candidates across actors."""

        with self._unit_of_work(read_only=True) as unit_of_work:
            repository = NotionConnectorRepository(unit_of_work.connection)
            connectors: list[dict[str, Any]] = []
            for row in repository.list_sync_candidates():
                connector = self._attach_connector_resources(
                    repository, self._connector_from_row(row)
                )
                if connector is not None:
                    connectors.append(connector)
            return connectors

    def get_connector(
        self, connector_id: str, user_id: Optional[int] = None
    ) -> Optional[dict[str, Any]]:
        with self._unit_of_work(read_only=True) as unit_of_work:
            repository = NotionConnectorRepository(unit_of_work.connection)
            connector = self._connector_from_row(
                repository.get_connector(connector_id, user_id)
            )
            return self._attach_connector_resources(repository, connector)

    def get_active_connector_for_user(self, user_id: int) -> Optional[dict[str, Any]]:
        with self._unit_of_work(read_only=True) as unit_of_work:
            repository = NotionConnectorRepository(unit_of_work.connection)
            return self._connector_from_row(repository.get_active_connector(user_id))

    def update_connector(
        self,
        connector_id: str,
        user_id: int,
        updates: Mapping[str, Any],
    ) -> dict[str, Any]:
        with self._unit_of_work(read_only=False) as unit_of_work:
            repository = NotionConnectorRepository(unit_of_work.connection)
            row = self._require_connector_row(
                repository, connector_id, user_id, for_update=True
            )
            config = _json_loads(
                row.get("config_json"), field="connector config", expected=dict
            )
            for field in ("name", "platform", "auth_status"):
                value = updates.get(field)
                if value is not None and str(value).strip():
                    row[field] = str(value).strip()
            if isinstance(updates.get("config"), Mapping):
                config.update(dict(cast(Mapping[str, Any], updates["config"])))
            for field in (
                "current_snapshot_version",
                "current_source_revision",
                "current_sync_cursor",
                "last_synced_at",
            ):
                if field in updates:
                    row[field] = updates[field]
            row["config_json"] = _json_dumps(config)
            row["updated_at"] = _utcnow()
            updated = repository.update_connector(row, user_id=user_id)
            connector = self._attach_connector_resources(
                repository, self._connector_from_row(updated)
            )
            unit_of_work.commit()
        return connector or {}

    def delete_connector(self, connector_id: str, user_id: int) -> bool:
        with self._unit_of_work(read_only=False) as unit_of_work:
            repository = NotionConnectorRepository(unit_of_work.connection)
            deleted = repository.delete_connector(connector_id, user_id)
            unit_of_work.commit()
            return deleted

    def save_auth_state(
        self,
        connector_id: str,
        user_id: int,
        *,
        auth_status: str,
        config_patch: Optional[Mapping[str, Any]] = None,
        verification_url: Optional[str] = None,
        verification_code: Optional[str] = None,
        poll_interval_seconds: Optional[int] = None,
        error_detail: Optional[str] = None,
    ) -> dict[str, Any]:
        with self._unit_of_work(read_only=False) as unit_of_work:
            repository = NotionConnectorRepository(unit_of_work.connection)
            row = self._require_connector_row(
                repository, connector_id, user_id, for_update=True
            )
            config = _json_loads(
                row.get("config_json"), field="connector config", expected=dict
            )
            if config_patch:
                config.update({key: value for key, value in config_patch.items() if value is not None})
            if verification_url is not None:
                config["verification_url"] = verification_url
            if verification_code is not None:
                config["verification_code"] = verification_code
            if poll_interval_seconds is not None:
                config["poll_interval_seconds"] = int(poll_interval_seconds)
            if error_detail is not None:
                config["auth_error"] = error_detail
            row["auth_status"] = auth_status
            row["config_json"] = _json_dumps(config)
            row["updated_at"] = _utcnow()
            updated = repository.update_connector(row, user_id=user_id)
            connector = self._attach_connector_resources(
                repository, self._connector_from_row(updated)
            )
            unit_of_work.commit()
        return connector or {}

    def replace_connector_resources(
        self,
        connector_id: str,
        user_id: int,
        databases: Iterable[Mapping[str, Any]],
        pages: Iterable[Mapping[str, Any]],
    ) -> dict[str, Any]:
        selected_databases = [dict(item) for item in databases]
        selected_pages = [dict(item) for item in pages]
        with self._unit_of_work(read_only=False) as unit_of_work:
            repository = NotionConnectorRepository(unit_of_work.connection)
            connector_row = self._require_connector_row(
                repository, connector_id, user_id, for_update=True
            )
            repository.delete_selected_resources(connector_id)
            now = _utcnow()
            for item in selected_databases:
                external_id = str(item.get("database_id") or item.get("id") or "").strip()
                if not external_id:
                    continue
                repository.insert_resource(
                    resource_id=str(uuid4()),
                    connector_id=connector_id,
                    resource_type="notion_database",
                    external_id=external_id,
                    title=str(item.get("title") or external_id),
                    metadata_json=_json_dumps(
                        {
                            "page_count": item.get("page_count"),
                            "properties_schema": item.get("properties_schema") or {},
                            "url": item.get("url") or "",
                            "last_edited": item.get("last_edited") or "",
                            "raw": item.get("raw") or {},
                        }
                    ),
                    now=now,
                )
            for item in selected_pages:
                external_id = str(item.get("page_id") or item.get("id") or "").strip()
                if not external_id:
                    continue
                repository.insert_resource(
                    resource_id=str(uuid4()),
                    connector_id=connector_id,
                    resource_type="notion_page",
                    external_id=external_id,
                    title=str(item.get("title") or external_id),
                    metadata_json=_json_dumps(
                        {
                            "url": item.get("url") or "",
                            "last_edited": item.get("last_edited") or "",
                            "parent": item.get("parent") or {},
                            "raw": item.get("raw") or {},
                        }
                    ),
                    now=now,
                )
            config = _json_loads(
                connector_row.get("config_json"),
                field="connector config",
                expected=dict,
            )
            config.update(
                {
                    "selected_databases": [
                        item.get("database_id") or item.get("id")
                        for item in selected_databases
                        if item.get("database_id") or item.get("id")
                    ],
                    "selected_pages": [
                        item.get("page_id") or item.get("id")
                        for item in selected_pages
                        if item.get("page_id") or item.get("id")
                    ],
                }
            )
            connector_row["config_json"] = _json_dumps(config)
            connector_row["updated_at"] = now
            updated = repository.update_connector(connector_row, user_id=user_id)
            connector = self._attach_connector_resources(
                repository, self._connector_from_row(updated)
            )
            resources = [
                self._resource_from_row(row)
                for row in repository.list_resources(connector_id)
            ]
            unit_of_work.commit()
        return {"connector": connector or {}, "resources": resources}

    def list_connector_resources(
        self, connector_id: str, user_id: int
    ) -> list[dict[str, Any]]:
        with self._unit_of_work(read_only=True) as unit_of_work:
            repository = NotionConnectorRepository(unit_of_work.connection)
            self._require_connector_row(repository, connector_id, user_id)
            return [
                self._resource_from_row(row)
                for row in repository.list_resources(connector_id)
            ]

    def delete_connector_resource(
        self, connector_id: str, user_id: int, resource_id: str
    ) -> bool:
        with self._unit_of_work(read_only=False) as unit_of_work:
            repository = NotionConnectorRepository(unit_of_work.connection)
            self._require_connector_row(
                repository, connector_id, user_id, for_update=True
            )
            deleted = repository.delete_resource(connector_id, resource_id)
            unit_of_work.commit()
            return deleted

    def save_snapshot(
        self,
        connector_id: str,
        user_id: int,
        workspace_id: str,
        snapshot: CanonicalWorkspaceSnapshot | dict[str, Any],
        synced_resources: Iterable[Mapping[str, Any]] = (),
    ) -> dict[str, Any]:
        del workspace_id  # The canonical payload already carries workspace identity.
        payload = _snapshot_payload(snapshot)
        metadata = _mapping(payload.get("metadata"))
        if not metadata:
            raise NotionSnapshotNotReadyError("Snapshot metadata is missing.")
        snapshot_version = str(metadata.get("snapshot_version") or "").strip()
        source_revision = str(metadata.get("source_revision") or "").strip()
        sync_cursor = str(metadata.get("sync_cursor") or "").strip()
        if not snapshot_version:
            raise NotionSnapshotNotReadyError("Snapshot version is missing.")
        if not source_revision:
            raise NotionSnapshotNotReadyError("Snapshot source revision is missing.")
        if not sync_cursor:
            raise NotionSnapshotNotReadyError("Snapshot sync cursor is missing.")
        fetched_at = _db_timestamp(
            metadata.get("fetched_at") or _utcnow(),
            required=True,
            field="fetched_at",
        )
        assert fetched_at is not None
        state_value = metadata.get("state") or SnapshotLifecycleState.SNAPSHOT_READY.value
        state = state_value.value if isinstance(state_value, SnapshotLifecycleState) else str(state_value)
        now = _utcnow()
        with self._unit_of_work(read_only=False) as unit_of_work:
            repository = NotionConnectorRepository(unit_of_work.connection)
            connector_row = self._require_connector_row(
                repository, connector_id, user_id, for_update=True
            )
            repository.upsert_snapshot(
                snapshot_id=str(uuid4()),
                connector_id=connector_id,
                snapshot_version=snapshot_version,
                source_revision=source_revision,
                sync_cursor=sync_cursor,
                fetched_at=fetched_at,
                state=state,
                snapshot_json=_json_dumps(payload),
                now=now,
            )
            connector_row.update(
                {
                    "current_snapshot_version": snapshot_version,
                    "current_source_revision": source_revision,
                    "current_sync_cursor": sync_cursor,
                    "last_synced_at": fetched_at,
                    "auth_status": "authenticated",
                    "updated_at": now,
                }
            )
            repository.update_connector(connector_row, user_id=user_id)
            database_pages = _mapping(payload.get("database_pages"))
            for database_id, pages in database_pages.items():
                if not isinstance(pages, list):
                    continue
                resource_id = repository.find_database_resource(
                    connector_id, str(database_id)
                )
                if resource_id is None:
                    continue
                repository.replace_resource_pages(
                    resource_id,
                    [item for item in pages if isinstance(item, Mapping)],
                    fetched_at=fetched_at,
                    now=now,
                )
            exact_resources = {
                (
                    str(item.get("resource_type") or "").strip(),
                    str(item.get("external_id") or "").strip(),
                )
                for item in synced_resources
                if isinstance(item, Mapping)
            }
            for resource_type, external_id in sorted(exact_resources):
                if resource_type not in {"notion_database", "notion_page"} or not external_id:
                    continue
                repository.mark_resource_synced(
                    connector_id=connector_id,
                    resource_type=resource_type,
                    external_id=external_id,
                    now=now,
                )
            unit_of_work.commit()
        return payload

    def get_current_snapshot(
        self, workspace_id: str, connector_id: str, user_id: int
    ) -> Optional[dict[str, Any]]:
        del workspace_id
        with self._unit_of_work(read_only=True) as unit_of_work:
            repository = NotionConnectorRepository(unit_of_work.connection)
            return self._snapshot_from_row(
                repository.get_current_snapshot(connector_id, user_id)
            )

    def get_snapshot(
        self, connector_id: str, snapshot_version: str, user_id: int
    ) -> Optional[dict[str, Any]]:
        with self._unit_of_work(read_only=True) as unit_of_work:
            repository = NotionConnectorRepository(unit_of_work.connection)
            self._require_connector_row(repository, connector_id, user_id)
            return self._snapshot_from_row(
                repository.get_snapshot(connector_id, snapshot_version, user_id)
            )

    def list_snapshots(
        self, connector_id: str, user_id: int
    ) -> list[dict[str, Any]]:
        with self._unit_of_work(read_only=True) as unit_of_work:
            repository = NotionConnectorRepository(unit_of_work.connection)
            self._require_connector_row(repository, connector_id, user_id)
            snapshots: list[dict[str, Any]] = []
            for row in repository.list_snapshots(connector_id, user_id):
                item = dict(row)
                item["snapshot"] = self._snapshot_from_row(row)
                item.pop("snapshot_json", None)
                for field in ("fetched_at", "created_at", "updated_at"):
                    item[field] = _iso_timestamp(item.get(field))
                snapshots.append(item)
            return snapshots

    def attach_thread_to_connector(
        self, connector_id: str, user_id: int, thread_id: str
    ) -> dict[str, Any]:
        with self._unit_of_work(read_only=False) as unit_of_work:
            repository = NotionConnectorRepository(unit_of_work.connection)
            connector_row = self._require_connector_row(
                repository, connector_id, user_id, for_update=True
            )
            repository.attach_thread(connector_id, thread_id, now=_utcnow())
            connector = self._attach_connector_resources(
                repository, self._connector_from_row(connector_row)
            )
            unit_of_work.commit()
        return connector or {}

    def get_connector_for_thread(
        self, thread_id: str, user_id: int
    ) -> Optional[dict[str, Any]]:
        with self._unit_of_work(read_only=True) as unit_of_work:
            repository = NotionConnectorRepository(unit_of_work.connection)
            return self._connector_from_row(
                repository.get_connector_for_thread(thread_id, user_id)
            )


class _DefaultNotionStoreRuntime:
    """Own the default pool lifecycle without doing work at module import."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._store: NotionConnectorStore | None = None
        self._owned_pool: PostgresPool | None = None

    def open(
        self,
        *,
        pool: ConnectionPool | None = None,
        store: NotionConnectorStore | None = None,
    ) -> NotionConnectorStore:
        if pool is not None and store is not None:
            raise ValueError("configure either a PostgreSQL pool or a store")
        with self._lock:
            if self._store is not None:
                return self._store
            owned_pool: PostgresPool | None = None
            if store is None:
                if pool is None:
                    owned_pool = PostgresPool.from_env(
                        application_name="ink-dream-notion-connectors"
                    )
                    try:
                        owned_pool.open()
                    except Exception:
                        try:
                            owned_pool.close()
                        except Exception:
                            pass
                        raise
                    pool = owned_pool
                store = NotionConnectorStore(pool)
            self._store = store
            self._owned_pool = owned_pool
            return store

    def get(self) -> NotionConnectorStore:
        with self._lock:
            existing = self._store
        return existing if existing is not None else self.open()

    def close(self) -> None:
        with self._lock:
            pool = self._owned_pool
            self._owned_pool = None
            self._store = None
        if pool is not None:
            pool.close()


_default_runtime = _DefaultNotionStoreRuntime()


def open_default_store(
    *,
    pool: ConnectionPool | None = None,
    store: NotionConnectorStore | None = None,
) -> NotionConnectorStore:
    """Open or explicitly inject the default runtime store."""

    return _default_runtime.open(pool=pool, store=store)


def close_default_store() -> None:
    """Close the owned runtime pool and forget injected test state."""

    _default_runtime.close()


def create_connector(
    user_id: int,
    name: str,
    platform: str = "notion",
    config: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    return _default_runtime.get().create_connector(user_id, name, platform, config)


def list_connectors(user_id: int) -> list[dict[str, Any]]:
    return _default_runtime.get().list_connectors(user_id)


def list_sync_candidates() -> list[dict[str, Any]]:
    return _default_runtime.get().list_sync_candidates()


def get_connector(
    connector_id: str, user_id: Optional[int] = None
) -> Optional[dict[str, Any]]:
    return _default_runtime.get().get_connector(connector_id, user_id)


def get_active_connector_for_user(user_id: int) -> Optional[dict[str, Any]]:
    return _default_runtime.get().get_active_connector_for_user(user_id)


def update_connector(
    connector_id: str, user_id: int, updates: Mapping[str, Any]
) -> dict[str, Any]:
    return _default_runtime.get().update_connector(connector_id, user_id, updates)


def delete_connector(connector_id: str, user_id: int) -> bool:
    return _default_runtime.get().delete_connector(connector_id, user_id)


def save_auth_state(
    connector_id: str,
    user_id: int,
    *,
    auth_status: str,
    config_patch: Optional[Mapping[str, Any]] = None,
    verification_url: Optional[str] = None,
    verification_code: Optional[str] = None,
    poll_interval_seconds: Optional[int] = None,
    error_detail: Optional[str] = None,
) -> dict[str, Any]:
    return _default_runtime.get().save_auth_state(
        connector_id,
        user_id,
        auth_status=auth_status,
        config_patch=config_patch,
        verification_url=verification_url,
        verification_code=verification_code,
        poll_interval_seconds=poll_interval_seconds,
        error_detail=error_detail,
    )


def replace_connector_resources(
    connector_id: str,
    user_id: int,
    databases: Iterable[Mapping[str, Any]],
    pages: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    return _default_runtime.get().replace_connector_resources(
        connector_id, user_id, databases, pages
    )


def list_connector_resources(connector_id: str, user_id: int) -> list[dict[str, Any]]:
    return _default_runtime.get().list_connector_resources(connector_id, user_id)


def delete_connector_resource(
    connector_id: str, user_id: int, resource_id: str
) -> bool:
    return _default_runtime.get().delete_connector_resource(
        connector_id, user_id, resource_id
    )


def save_snapshot(
    connector_id: str,
    user_id: int,
    workspace_id: str,
    snapshot: CanonicalWorkspaceSnapshot | dict[str, Any],
    synced_resources: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    return _default_runtime.get().save_snapshot(
        connector_id,
        user_id,
        workspace_id,
        snapshot,
        synced_resources,
    )


def get_current_snapshot(
    workspace_id: str, connector_id: str, user_id: int
) -> Optional[dict[str, Any]]:
    return _default_runtime.get().get_current_snapshot(
        workspace_id, connector_id, user_id
    )


def get_snapshot(
    connector_id: str, snapshot_version: str, user_id: int
) -> Optional[dict[str, Any]]:
    return _default_runtime.get().get_snapshot(
        connector_id, snapshot_version, user_id
    )


def list_snapshots(connector_id: str, user_id: int) -> list[dict[str, Any]]:
    return _default_runtime.get().list_snapshots(connector_id, user_id)


def attach_thread_to_connector(
    connector_id: str, user_id: int, thread_id: str
) -> dict[str, Any]:
    return _default_runtime.get().attach_thread_to_connector(
        connector_id, user_id, thread_id
    )


def get_connector_for_thread(
    thread_id: str, user_id: int
) -> Optional[dict[str, Any]]:
    return _default_runtime.get().get_connector_for_thread(thread_id, user_id)


__all__ = [
    "NotionConnectorRepository",
    "NotionConnectorStore",
    "attach_thread_to_connector",
    "close_default_store",
    "create_connector",
    "delete_connector",
    "delete_connector_resource",
    "get_active_connector_for_user",
    "get_connector",
    "get_connector_for_thread",
    "get_current_snapshot",
    "get_snapshot",
    "list_connector_resources",
    "list_connectors",
    "list_sync_candidates",
    "list_snapshots",
    "open_default_store",
    "replace_connector_resources",
    "save_auth_state",
    "save_snapshot",
    "update_connector",
]
