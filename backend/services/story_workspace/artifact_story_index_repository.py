"""PostgreSQL repository for Artifact Story identity and public Story reads."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

try:
    from services.story_workspace.artifact_story_index_projector import (
        ARTIFACT_SOURCE_TYPE,
        ArtifactStoryProjection,
    )
except ModuleNotFoundError:  # pragma: no cover - repository-root imports.
    from backend.services.story_workspace.artifact_story_index_projector import (
        ARTIFACT_SOURCE_TYPE,
        ArtifactStoryProjection,
    )


STORY_INDEX_SCHEMA_UNAVAILABLE = "story_index_schema_unavailable"
STORY_INDEX_DATABASE_UNAVAILABLE = "story_index_database_unavailable"
STORY_INDEX_WRITE_FAILED = "story_index_write_failed"
STORY_INDEX_CONFLICT = "story_index_conflict"
STORY_INDEX_REVISION_CONFLICT = "story_index_revision_conflict"

_INDEX_COLUMNS = frozenset(
    {
        "artifact_source_type",
        "source_run_id",
        "source_thread_ref",
        "source_project_id",
        "episode_count",
        "artifact_manifest_revision",
        "script_revision",
        "artifact_sync_status",
        "artifact_indexed_at",
        "artifact_sync_error_code",
        "script_size_bytes",
        "artifact_available",
        "reconcile_version",
        "reviewed_script_revision",
    }
)
_IDENTITY_KEY_COLUMNS = (
    "workspace_id",
    "artifact_source_type",
    "source_project_id",
)

PUBLIC_STORY_COLUMNS: tuple[str, ...] = (
    "id",
    "identifier",
    "title",
    "description",
    "status",
    "review_status",
    "review_notes",
    "type",
    "character_count",
    "scene_count",
    "created_at",
    "updated_at",
    "confirmed_at",
    "source_run_id",
    "source_project_id",
    "episode_count",
    "artifact_manifest_revision",
    "script_revision",
    "artifact_sync_status",
    "artifact_indexed_at",
    "artifact_sync_error_code",
    "script_size_bytes",
    "artifact_available",
    "reconcile_version",
)

_PUBLIC_CHARACTER_COLUMNS: tuple[str, ...] = (
    "id",
    "identifier",
    "name",
    "avatar_url",
    "identity",
    "personality",
    "background",
    "catchphrase",
    "tags",
    "story_count",
    "review_status",
    "created_at",
    "updated_at",
    "confirmed_at",
)

_PUBLIC_SCENE_COLUMNS: tuple[str, ...] = (
    "id",
    "identifier",
    "name",
    "description",
    "story_id",
    "character_count",
    "order_index",
    "review_status",
    "created_at",
    "updated_at",
    "confirmed_at",
)

_STORY_SORT_FIELDS = frozenset({"updated_at", "created_at", "title"})
_STORY_FILTER_FIELDS = frozenset({"review_status", "status", "type"})
_PUBLIC_SYNC_ERROR_CODES = frozenset(
    {
        "story_index_row_missing",
        "story_index_schema_unavailable",
        "story_index_database_unavailable",
        "story_index_write_failed",
        "story_index_conflict",
        "story_index_invalid_artifact",
        "story_index_revision_conflict",
        "artifact_missing",
    }
)


class ArtifactStoryIndexRepositoryError(RuntimeError):
    """Repository failure carrying one fixed client-safe code."""

    def __init__(self, code: str, *, retryable: bool) -> None:
        super().__init__(code)
        self.code = code
        self.retryable = retryable


@dataclass(frozen=True)
class ArtifactStoryIndexRecord:
    story_id: str
    identifier: str
    title: str
    workspace_id: str
    source_run_id: str | None
    source_thread_ref: str | None
    source_project_id: str
    artifact_manifest_revision: str | None
    script_revision: str | None
    artifact_sync_status: str | None
    artifact_indexed_at: object | None
    artifact_sync_error_code: str | None
    episode_count: int | None
    script_size_bytes: int | None
    artifact_available: bool | None
    reconcile_version: int | None


@dataclass(frozen=True)
class ArtifactStoryIndexWriteResult:
    status: str
    story_id: str | None
    record: ArtifactStoryIndexRecord | None = None
    error_code: str | None = None
    retryable: bool = False


class ArtifactStoryIndexRepository:
    """Own all Story index SQL and its transaction boundary."""

    def __init__(self, db: Any) -> None:
        self.db = db

    @staticmethod
    def _rollback_quietly(db: Any) -> None:
        try:
            db.rollback()
        except Exception:
            pass

    def schema_columns(self) -> frozenset[str]:
        try:
            rows = self.db.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = current_schema() "
                "AND table_name = 'story_workspace_stories'"
            ).fetchall()
        except Exception as exc:
            self._rollback_quietly(self.db)
            raise ArtifactStoryIndexRepositoryError(
                STORY_INDEX_DATABASE_UNAVAILABLE,
                retryable=True,
            ) from exc
        return frozenset(str(row["column_name"]) for row in rows)

    def require_schema(self) -> None:
        if not _INDEX_COLUMNS.issubset(self.schema_columns()):
            self._rollback_quietly(self.db)
            raise ArtifactStoryIndexRepositoryError(
                STORY_INDEX_SCHEMA_UNAVAILABLE,
                retryable=True,
            )
        try:
            rows = self.db.execute(
                "SELECT ARRAY_AGG(attribute.attname ORDER BY key.position) "
                "AS column_names, index_info.indnkeyatts AS key_count, "
                "BOOL_AND(key.attnum > 0 AND attribute.attname IS NOT NULL) "
                "AS all_direct_columns, "
                "BOOL_AND(index_info.indpred IS NULL) AS is_full_index "
                "FROM pg_catalog.pg_index AS index_info "
                "JOIN pg_catalog.pg_class AS table_info "
                "ON table_info.oid = index_info.indrelid "
                "JOIN pg_catalog.pg_namespace AS namespace "
                "ON namespace.oid = table_info.relnamespace "
                "CROSS JOIN LATERAL UNNEST(index_info.indkey::smallint[]) "
                "WITH ORDINALITY AS key(attnum, position) "
                "LEFT JOIN pg_catalog.pg_attribute AS attribute "
                "ON attribute.attrelid = table_info.oid "
                "AND attribute.attnum = key.attnum "
                "WHERE namespace.nspname = current_schema() "
                "AND table_info.relname = 'story_workspace_stories' "
                "AND index_info.indisunique IS TRUE "
                "AND index_info.indisvalid IS TRUE "
                "AND key.position <= index_info.indnkeyatts "
                "GROUP BY index_info.indexrelid, index_info.indnkeyatts"
            ).fetchall()
        except Exception as exc:
            self._rollback_quietly(self.db)
            raise ArtifactStoryIndexRepositoryError(
                STORY_INDEX_DATABASE_UNAVAILABLE,
                retryable=True,
            ) from exc
        identity_key = frozenset(_IDENTITY_KEY_COLUMNS)
        if not any(
            isinstance(row["column_names"], (list, tuple))
            and row["key_count"] == len(_IDENTITY_KEY_COLUMNS)
            and row["all_direct_columns"] is True
            and row["is_full_index"] is True
            and len(row["column_names"]) == len(_IDENTITY_KEY_COLUMNS)
            and all(value is not None for value in row["column_names"])
            and frozenset(str(value) for value in row["column_names"])
            == identity_key
            for row in rows
        ):
            self._rollback_quietly(self.db)
            raise ArtifactStoryIndexRepositoryError(
                STORY_INDEX_SCHEMA_UNAVAILABLE,
                retryable=True,
            )

    @staticmethod
    def _record(row: Any) -> ArtifactStoryIndexRecord:
        return ArtifactStoryIndexRecord(
            story_id=str(row["id"]),
            identifier=str(row["identifier"]),
            title=str(row["title"]),
            workspace_id=str(row["workspace_id"]),
            source_run_id=(
                str(row["source_run_id"])
                if row["source_run_id"] is not None
                else None
            ),
            source_thread_ref=(
                str(row["source_thread_ref"])
                if row["source_thread_ref"] is not None
                else None
            ),
            source_project_id=str(row["source_project_id"]),
            artifact_manifest_revision=row["artifact_manifest_revision"],
            script_revision=row["script_revision"],
            artifact_sync_status=row["artifact_sync_status"],
            artifact_indexed_at=row["artifact_indexed_at"],
            artifact_sync_error_code=row["artifact_sync_error_code"],
            episode_count=(
                int(row["episode_count"])
                if row["episode_count"] is not None
                else None
            ),
            script_size_bytes=(
                int(row["script_size_bytes"])
                if row["script_size_bytes"] is not None
                else None
            ),
            artifact_available=(
                bool(row["artifact_available"])
                if row["artifact_available"] is not None
                else None
            ),
            reconcile_version=(
                int(row["reconcile_version"])
                if row["reconcile_version"] is not None
                else None
            ),
        )

    @staticmethod
    def _record_columns() -> str:
        return (
            "id, identifier, title, workspace_id, source_run_id, "
            "source_thread_ref, source_project_id, artifact_manifest_revision, "
            "script_revision, artifact_sync_status, artifact_indexed_at, "
            "artifact_sync_error_code, episode_count, script_size_bytes, "
            "artifact_available, reconcile_version"
        )

    def find(
        self,
        *,
        workspace_id: str,
        source_project_id: str,
    ) -> ArtifactStoryIndexRecord | None:
        self.require_schema()
        try:
            row = self.db.execute(
                f"SELECT {self._record_columns()} "
                "FROM story_workspace_stories "
                "WHERE workspace_id = %s AND artifact_source_type = %s "
                "AND source_project_id = %s",
                (workspace_id, ARTIFACT_SOURCE_TYPE, source_project_id),
            ).fetchone()
        except ArtifactStoryIndexRepositoryError:
            raise
        except Exception as exc:
            self._rollback_quietly(self.db)
            raise ArtifactStoryIndexRepositoryError(
                STORY_INDEX_DATABASE_UNAVAILABLE,
                retryable=True,
            ) from exc
        return self._record(row) if row is not None else None

    @staticmethod
    def _advisory_lock_key(projection: ArtifactStoryProjection) -> int:
        payload = (
            f"{projection.workspace_id}\0{projection.artifact_source_type}\0"
            f"{projection.source_project_id}"
        ).encode("utf-8")
        return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big", signed=True)

    def upsert(
        self,
        projection: ArtifactStoryProjection,
        *,
        expected_record: ArtifactStoryIndexRecord | None = None,
        require_expected_record: bool = False,
    ) -> ArtifactStoryIndexWriteResult:
        """Create/update one stable Story without touching review or content fields.

        ``require_expected_record`` is the HTTP reconcile CAS seam.  The
        caller first observes a public Story-index ETag, then supplies the
        exact internal row behind that observation.  The comparison happens
        only after the stable-key advisory lock and row lock are held, so a
        concurrent database update cannot be overwritten by a stale retry.
        Completion-time materialization deliberately leaves this disabled.
        """

        try:
            self.require_schema()
            self.db.execute(
                "SELECT pg_advisory_xact_lock(%s)",
                (self._advisory_lock_key(projection),),
            )
            rows = self.db.execute(
                f"SELECT {self._record_columns()} "
                "FROM story_workspace_stories "
                "WHERE workspace_id = %s AND artifact_source_type = %s "
                "AND source_project_id = %s FOR UPDATE",
                (
                    projection.workspace_id,
                    projection.artifact_source_type,
                    projection.source_project_id,
                ),
            ).fetchall()
            if len(rows) > 1:
                self.db.rollback()
                return ArtifactStoryIndexWriteResult(
                    status="conflict",
                    story_id=None,
                    error_code=STORY_INDEX_CONFLICT,
                    retryable=False,
                )
            current = self._record(rows[0]) if rows else None
            if require_expected_record and current != expected_record:
                self.db.rollback()
                return ArtifactStoryIndexWriteResult(
                    status="revision_conflict",
                    story_id=current.story_id if current is not None else None,
                    record=current,
                    error_code=STORY_INDEX_REVISION_CONFLICT,
                    retryable=True,
                )
            if current is not None:
                if (
                    current.story_id != projection.story_id
                    or current.source_thread_ref != projection.source_thread_ref
                ):
                    self.db.rollback()
                    return ArtifactStoryIndexWriteResult(
                        status="conflict",
                        story_id=current.story_id,
                        record=current,
                        error_code=STORY_INDEX_CONFLICT,
                        retryable=False,
                    )
                if (
                    current.identifier == projection.source_project_id
                    and current.title == projection.title
                    and current.source_run_id == projection.source_run_id
                    and current.episode_count == projection.episode_count
                    and current.artifact_manifest_revision
                    == projection.artifact_manifest_revision
                    and current.script_revision == projection.script_revision
                    and current.artifact_sync_status == "indexed"
                    and current.artifact_indexed_at is not None
                    and current.artifact_sync_error_code is None
                    and current.script_size_bytes == projection.script_size_bytes
                    and current.artifact_available
                    is projection.artifact_available
                    and current.reconcile_version == 1
                ):
                    self.db.commit()
                    return ArtifactStoryIndexWriteResult(
                        status="same_revision",
                        story_id=current.story_id,
                        record=current,
                    )
                updated = self.db.execute(
                    "UPDATE story_workspace_stories SET "
                    "identifier = %s, title = %s, source_run_id = %s, "
                    "episode_count = %s, artifact_manifest_revision = %s, "
                    "script_revision = %s, artifact_sync_status = 'indexed', "
                    "artifact_indexed_at = CURRENT_TIMESTAMP, "
                    "artifact_sync_error_code = NULL, script_size_bytes = %s, "
                    "artifact_available = %s, reconcile_version = 1, "
                    "updated_at = CURRENT_TIMESTAMP "
                    "WHERE id = %s "
                    f"RETURNING {self._record_columns()}",
                    (
                        projection.source_project_id,
                        projection.title,
                        projection.source_run_id,
                        projection.episode_count,
                        projection.artifact_manifest_revision,
                        projection.script_revision,
                        projection.script_size_bytes,
                        projection.artifact_available,
                        current.story_id,
                    ),
                ).fetchone()
                if updated is None:
                    raise RuntimeError("Story index update returned no row")
                record = self._record(updated)
                self.db.commit()
                return ArtifactStoryIndexWriteResult(
                    status="updated",
                    story_id=record.story_id,
                    record=record,
                )

            id_collision = self.db.execute(
                "SELECT id FROM story_workspace_stories WHERE id = %s FOR UPDATE",
                (projection.story_id,),
            ).fetchone()
            if id_collision is not None:
                self.db.rollback()
                return ArtifactStoryIndexWriteResult(
                    status="conflict",
                    story_id=projection.story_id,
                    error_code=STORY_INDEX_CONFLICT,
                    retryable=False,
                )
            inserted = self.db.execute(
                "INSERT INTO story_workspace_stories ("
                "id, identifier, title, description, status, review_status, type, "
                "content, author_id, workspace_id, character_count, scene_count, "
                "agent_generated, artifact_source_type, source_run_id, "
                "source_thread_ref, source_project_id, episode_count, "
                "artifact_manifest_revision, script_revision, artifact_sync_status, "
                "artifact_indexed_at, artifact_sync_error_code, script_size_bytes, "
                "artifact_available, reconcile_version"
                ") VALUES ("
                "%s, %s, %s, NULL, 'draft', 'pending', 'script', NULL, %s, %s, "
                "0, 0, 1, %s, %s, %s, %s, %s, %s, %s, 'indexed', "
                "CURRENT_TIMESTAMP, NULL, %s, %s, 1"
                f") RETURNING {self._record_columns()}",
                (
                    projection.story_id,
                    projection.source_project_id,
                    projection.title,
                    projection.author_id,
                    projection.workspace_id,
                    projection.artifact_source_type,
                    projection.source_run_id,
                    projection.source_thread_ref,
                    projection.source_project_id,
                    projection.episode_count,
                    projection.artifact_manifest_revision,
                    projection.script_revision,
                    projection.script_size_bytes,
                    projection.artifact_available,
                ),
            ).fetchone()
            if inserted is None:
                raise RuntimeError("Story index insert returned no row")
            record = self._record(inserted)
            self.db.commit()
            return ArtifactStoryIndexWriteResult(
                status="created",
                story_id=record.story_id,
                record=record,
            )
        except ArtifactStoryIndexRepositoryError:
            self._rollback_quietly(self.db)
            raise
        except Exception as exc:
            self._rollback_quietly(self.db)
            raise ArtifactStoryIndexRepositoryError(
                STORY_INDEX_WRITE_FAILED,
                retryable=True,
            ) from exc

    def list_records(
        self,
        *,
        workspace_id: str | None,
        limit: int,
        cursor: str | None,
        source_run_id: str | None = None,
    ) -> list[ArtifactStoryIndexRecord]:
        """Bounded internal read used only by dry-run reconcile."""

        self.require_schema()
        conditions = ["artifact_source_type = %s"]
        params: list[object] = [ARTIFACT_SOURCE_TYPE]
        if workspace_id is not None:
            conditions.append("workspace_id = %s")
            params.append(workspace_id)
        if source_run_id is not None:
            conditions.append("source_run_id = %s")
            params.append(source_run_id)
        if cursor is not None:
            conditions.append("id > %s")
            params.append(cursor)
        params.append(limit)
        try:
            rows = self.db.execute(
                f"SELECT {self._record_columns()} FROM story_workspace_stories "
                f"WHERE {' AND '.join(conditions)} ORDER BY id ASC LIMIT %s",
                tuple(params),
            ).fetchall()
        except Exception as exc:
            self._rollback_quietly(self.db)
            raise ArtifactStoryIndexRepositoryError(
                STORY_INDEX_DATABASE_UNAVAILABLE,
                retryable=True,
            ) from exc
        return [self._record(row) for row in rows]


class StoryWorkspacePublicStoryRepository:
    """Read-only explicit allowlist for every browser-visible Story row."""

    def __init__(self, db: Any) -> None:
        self.db = db

    def _available_columns(self, table: str) -> frozenset[str]:
        if hasattr(self.db, "executescript"):
            rows = self.db.execute(f"PRAGMA table_info({table})").fetchall()
            return frozenset(str(row[1]) for row in rows)
        rows = self.db.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = current_schema() AND table_name = %s",
            (table,),
        ).fetchall()
        return frozenset(str(row["column_name"]) for row in rows)

    @staticmethod
    def _select_projection(
        columns: tuple[str, ...],
        available: frozenset[str],
        *,
        prefix: str = "",
    ) -> str:
        return ", ".join(
            f"{prefix}{column} AS {column}" if column in available else f"NULL AS {column}"
            for column in columns
        )

    @staticmethod
    def _public_row(row: Any) -> dict[str, Any]:
        item = dict(row)
        if item.get("artifact_available") is not None:
            item["artifact_available"] = bool(item["artifact_available"])
        stored_error = item.get("artifact_sync_error_code")
        if stored_error is not None and stored_error not in _PUBLIC_SYNC_ERROR_CODES:
            item["artifact_sync_error_code"] = None
        if isinstance(item.get("tags"), str):
            try:
                parsed_tags = json.loads(item["tags"])
                item["tags"] = parsed_tags if isinstance(parsed_tags, list) else []
            except (TypeError, ValueError):
                item["tags"] = []
        return item

    @staticmethod
    def _csv_values(raw: str | None) -> list[str]:
        return [value.strip() for value in (raw or "").split(",") if value.strip()]

    def list_stories(
        self,
        *,
        author_id: int,
        q: str | None,
        review_status: str | None,
        status: str | None,
        story_type: str | None,
        sort: str,
        order: str,
        page: int,
        per_page: int,
    ) -> dict[str, Any]:
        if sort not in _STORY_SORT_FIELDS:
            raise ValueError("unsupported_story_sort")
        normalized_order = order.lower()
        if normalized_order not in {"asc", "desc"}:
            raise ValueError("unsupported_story_order")
        conditions = ["author_id = %s"]
        params: list[Any] = [author_id]
        if q:
            conditions.append("title ILIKE %s")
            params.append(f"%{q}%")
        for column, raw in (
            ("review_status", review_status),
            ("status", status),
            ("type", story_type),
        ):
            if column not in _STORY_FILTER_FIELDS:
                raise ValueError("unsupported_story_filter")
            values = self._csv_values(raw)
            if values:
                conditions.append(
                    f"{column} IN ({', '.join('%s' for _ in values)})"
                )
                params.extend(values)
        where = " WHERE " + " AND ".join(conditions)
        available = self._available_columns("story_workspace_stories")
        projection = self._select_projection(PUBLIC_STORY_COLUMNS, available)
        total = int(
            self.db.execute(
                "SELECT COUNT(*) FROM story_workspace_stories" + where,
                tuple(params),
            ).fetchone()[0]
        )
        rows = self.db.execute(
            f"SELECT {projection} FROM story_workspace_stories{where} "
            f"ORDER BY {sort} {normalized_order.upper()}, id ASC LIMIT %s OFFSET %s",
            tuple(params) + (per_page, (page - 1) * per_page),
        ).fetchall()
        return {
            "data": [self._public_row(row) for row in rows],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": (total + per_page - 1) // per_page,
            },
        }

    def get_story(self, *, story_id: str, author_id: int) -> dict[str, Any]:
        story_available = self._available_columns("story_workspace_stories")
        story_projection = self._select_projection(
            PUBLIC_STORY_COLUMNS,
            story_available,
        )
        row = self.db.execute(
            f"SELECT {story_projection} FROM story_workspace_stories "
            "WHERE id = %s AND author_id = %s",
            (story_id, author_id),
        ).fetchone()
        if row is None:
            raise LookupError("story_not_found")
        result = self._public_row(row)

        character_available = self._available_columns("story_workspace_characters")
        character_projection = self._select_projection(
            _PUBLIC_CHARACTER_COLUMNS,
            character_available,
            prefix="c.",
        )
        characters = self.db.execute(
            f"SELECT {character_projection}, sc.role_type AS role_type "
            "FROM story_workspace_characters AS c "
            "JOIN story_workspace_story_characters AS sc ON sc.character_id = c.id "
            "WHERE sc.story_id = %s AND c.author_id = %s "
            "ORDER BY c.name ASC, c.id ASC",
            (story_id, author_id),
        ).fetchall()
        scene_available = self._available_columns("story_workspace_scenes")
        scene_projection = self._select_projection(
            _PUBLIC_SCENE_COLUMNS,
            scene_available,
        )
        scenes = self.db.execute(
            f"SELECT {scene_projection} FROM story_workspace_scenes "
            "WHERE story_id = %s AND author_id = %s "
            "ORDER BY order_index ASC, id ASC",
            (story_id, author_id),
        ).fetchall()
        result["characters"] = [self._public_row(item) for item in characters]
        result["scenes"] = [dict(item) for item in scenes]
        return result

    def get_story_row(
        self,
        *,
        story_id: str,
        author_id: int,
    ) -> dict[str, Any] | None:
        available = self._available_columns("story_workspace_stories")
        projection = self._select_projection(PUBLIC_STORY_COLUMNS, available)
        row = self.db.execute(
            f"SELECT {projection} FROM story_workspace_stories "
            "WHERE id = %s AND author_id = %s",
            (story_id, author_id),
        ).fetchone()
        return self._public_row(row) if row is not None else None

    def list_stories_for_character(
        self,
        *,
        character_id: str,
        author_id: int,
    ) -> list[dict[str, Any]]:
        available = self._available_columns("story_workspace_stories")
        projection = self._select_projection(
            PUBLIC_STORY_COLUMNS,
            available,
            prefix="s.",
        )
        rows = self.db.execute(
            f"SELECT {projection} "
            "FROM story_workspace_stories AS s "
            "JOIN story_workspace_story_characters AS sc ON sc.story_id = s.id "
            "WHERE sc.character_id = %s AND s.author_id = %s "
            "ORDER BY s.updated_at DESC, s.id ASC",
            (character_id, author_id),
        ).fetchall()
        return [self._public_row(row) for row in rows]


__all__ = [
    "ArtifactStoryIndexRecord",
    "ArtifactStoryIndexRepository",
    "ArtifactStoryIndexRepositoryError",
    "ArtifactStoryIndexWriteResult",
    "PUBLIC_STORY_COLUMNS",
    "STORY_INDEX_CONFLICT",
    "STORY_INDEX_DATABASE_UNAVAILABLE",
    "STORY_INDEX_SCHEMA_UNAVAILABLE",
    "STORY_INDEX_REVISION_CONFLICT",
    "STORY_INDEX_WRITE_FAILED",
    "StoryWorkspacePublicStoryRepository",
]
