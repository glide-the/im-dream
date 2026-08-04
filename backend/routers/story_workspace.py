#!/usr/bin/env python3
# [Input] Consume authenticated users, Story Workspace SQLite tables, and REST requests.
# [Output] Publish user-scoped Story Workspace read and controlled-update API routes.
# [Pos] Story Workspace baseline FastAPI router in backend/routers.
# [Sync] 2026-08-01: add task_202 workspace, story, character, and scene REST baseline.

"""Authenticated, user-scoped REST API for the Story Workspace baseline."""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from typing import Any, Iterator, Optional, Protocol
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

import database
from story_workspace.contracts import (
    STORY_WORKSPACE_REVIEW_NOTES_MAX_LENGTH,
    StoryWorkspaceAgentStoryPayload,
    StoryWorkspaceBatchAction,
    StoryWorkspaceCharacterPatch,
    StoryWorkspaceDreamConfirmationCommand,
    StoryWorkspaceGuidanceCommandPayload,
    StoryWorkspaceResourceType,
    StoryWorkspaceScenePatch,
    StoryWorkspaceStoryPatch,
    StoryWorkspaceWorkspacePatch,
)
from services.story_workspace.agent_integration import (
    AgentIntegrationError,
    get_or_create_default_workspace,
    store_agent_story_output,
)
from .deps import get_current_user

try:
    from services.errors.error_registry import ApiRouteError, build_error_payload
    from services.deck.story_workflow_gateway import (
        get_story_workflow_application_gateway,
    )
except ModuleNotFoundError:
    from backend.services.errors.error_registry import ApiRouteError, build_error_payload
    from backend.services.deck.story_workflow_gateway import (
        get_story_workflow_application_gateway,
    )


router = APIRouter(prefix="/api/story-workspace", tags=["story-workspace"])
logger = logging.getLogger(__name__)

_STORY_SORT_FIELDS = {"updated_at", "created_at", "title"}
_CHARACTER_SORT_FIELDS = {"updated_at", "created_at", "name"}
_SCENE_SORT_FIELDS = {"updated_at", "created_at", "name", "order_index"}

_REVIEW_RESOURCES = {
    StoryWorkspaceResourceType.STORY: "story_workspace_stories",
    StoryWorkspaceResourceType.CHARACTER: "story_workspace_characters",
    StoryWorkspaceResourceType.SCENE: "story_workspace_scenes",
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


class StoryWorkflowGateway(Protocol):
    async def create_preflight(
        self,
        request: _WorkflowPreflightRequest,
        *,
        actor: dict[str, str],
    ) -> Any: ...

    async def get_preflight(self, preflight_id: str, *, actor: dict[str, str]) -> Any: ...

    async def create_run(
        self,
        request: _WorkflowRunCreateRequest,
        *,
        actor: dict[str, str],
    ) -> Any: ...

    async def get_run(self, workflow_run_id: str, *, actor: dict[str, str]) -> Any: ...

    async def get_dream_files(
        self,
        workflow_run_id: str,
        *,
        actor: dict[str, str],
    ) -> Any: ...

    async def submit_dream_confirmation(
        self,
        workflow_run_id: str,
        request: StoryWorkspaceDreamConfirmationCommand,
        *,
        actor: dict[str, str],
    ) -> Any: ...

    async def retry_run(
        self,
        workflow_run_id: str,
        request: _WorkflowRunRetryRequest,
        *,
        actor: dict[str, str],
    ) -> Any: ...

    async def cancel_run(
        self,
        workflow_run_id: str,
        request: _WorkflowRunCancelRequest,
        *,
        actor: dict[str, str],
    ) -> Any: ...

    async def submit_guidance(
        self,
        workflow_run_id: str,
        request: StoryWorkspaceGuidanceCommandPayload,
        *,
        actor: dict[str, str],
    ) -> Any: ...


class _UnavailableStoryWorkflowGateway:
    def __getattr__(self, _name: str):
        async def unavailable(*_args: Any, **_kwargs: Any) -> Any:
            raise ApiRouteError("DECK_RUNTIME_CONFIG_UNAVAILABLE", status_code=503)

        return unavailable


def get_story_workflow_gateway() -> StoryWorkflowGateway:
    """Return the application wiring for authoritative preflight/run services."""

    return get_story_workflow_application_gateway()


async def _story_workflow_current_user(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    if current_user.get("workspace_id"):
        return current_user
    db = database.get_db()
    try:
        workspace_id = get_or_create_default_workspace(db, int(current_user["user_id"]))
    finally:
        db.close()
    return {**current_user, "workspace_id": workspace_id}


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
        return JSONResponse(
            status_code=503,
            content=build_error_payload("DECK_RUNTIME_CONFIG_UNAVAILABLE"),
        )


def _story_db() -> Iterator[sqlite3.Connection]:
    db = database.get_db()
    try:
        yield db
    finally:
        db.close()


def _user_id(current_user: dict[str, Any]) -> int:
    return int(current_user["user_id"])


def _decode_json(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    if "settings" in item:
        item["settings"] = _decode_json(item["settings"], {})
    if "tags" in item:
        item["tags"] = _decode_json(item["tags"], [])
    if "agent_generated" in item:
        item["agent_generated"] = bool(item["agent_generated"])
    return item


def _csv_values(raw: Optional[str]) -> list[str]:
    if not raw:
        return []
    return [value.strip() for value in raw.split(",") if value.strip()]


def _append_in_filter(
    conditions: list[str],
    params: list[Any],
    column: str,
    raw: Optional[str],
) -> None:
    values = _csv_values(raw)
    if not values:
        return
    conditions.append(f"{column} IN ({', '.join('?' for _ in values)})")
    params.extend(values)


def _sort_clause(sort: str, order: str, allowed: set[str]) -> str:
    if sort not in allowed:
        raise HTTPException(status_code=400, detail="Unsupported sort field")
    normalized_order = order.lower()
    if normalized_order not in {"asc", "desc"}:
        raise HTTPException(status_code=400, detail="Order must be 'asc' or 'desc'")
    return f" ORDER BY {sort} {normalized_order.upper()}, id ASC"


def _paginate_query(
    db: sqlite3.Connection,
    select_sql: str,
    count_sql: str,
    params: list[Any],
    page: int,
    per_page: int,
) -> dict[str, Any]:
    total = int(db.execute(count_sql, tuple(params)).fetchone()[0])
    offset = (page - 1) * per_page
    rows = db.execute(
        select_sql + " LIMIT ? OFFSET ?",
        tuple(params) + (per_page, offset),
    ).fetchall()
    return {
        "data": [_row_to_dict(row) for row in rows],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": (total + per_page - 1) // per_page,
        },
    }


def _owned_row(
    db: sqlite3.Connection,
    table: str,
    resource_id: str,
    owner_column: str,
    user_id: int,
) -> sqlite3.Row:
    row = db.execute(
        f"SELECT * FROM {table} WHERE id = ? AND {owner_column} = ?",
        (resource_id, user_id),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    return row


def _patch_owned_row(
    db: sqlite3.Connection,
    table: str,
    resource_id: str,
    owner_column: str,
    user_id: int,
    values: dict[str, Any],
) -> dict[str, Any]:
    _owned_row(db, table, resource_id, owner_column, user_id)
    if not values:
        raise HTTPException(status_code=400, detail="At least one field is required")
    columns = list(values)
    assignments = ", ".join(f"{column} = ?" for column in columns)
    cursor = db.execute(
        f"UPDATE {table} SET {assignments}, updated_at = CURRENT_TIMESTAMP "
        f"WHERE id = ? AND {owner_column} = ?",
        tuple(values[column] for column in columns) + (resource_id, user_id),
    )
    if cursor.rowcount != 1:
        db.rollback()
        raise HTTPException(status_code=404, detail="Resource not found")
    db.commit()
    return _row_to_dict(_owned_row(db, table, resource_id, owner_column, user_id))


def _owned_review_row(
    db: sqlite3.Connection,
    table: str,
    resource_id: str,
    user_id: int,
) -> sqlite3.Row:
    row = db.execute(
        f"SELECT * FROM {table} "
        "WHERE id = ? AND author_id = ? AND agent_generated = 1",
        (resource_id, user_id),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    return row


def _audit_review_action(
    user_id: int,
    resource_type: StoryWorkspaceResourceType,
    resource_id: str,
    action: StoryWorkspaceBatchAction,
    previous_status: str,
    new_status: str,
    review_notes: Optional[str] = None,
) -> None:
    logger.info(
        "story_workspace_review",
        extra={
            "id": str(uuid4()),
            "user_id": user_id,
            "resource_type": resource_type.value,
            "resource_id": resource_id,
            "action": action.value,
            "previous_status": previous_status,
            "new_status": new_status,
            "review_notes": review_notes,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )


def _transition_pending_review(
    db: sqlite3.Connection,
    user_id: int,
    resource_type: StoryWorkspaceResourceType,
    resource_id: str,
    action: StoryWorkspaceBatchAction,
    review_notes: Optional[str] = None,
) -> dict[str, Any]:
    table = _REVIEW_RESOURCES[resource_type]
    try:
        db.execute("BEGIN IMMEDIATE")
        previous = _owned_review_row(db, table, resource_id, user_id)
        if previous["status"] == "archived" or previous["review_status"] != "pending":
            raise HTTPException(
                status_code=400,
                detail="Item is not in pending review status",
            )

        if action == StoryWorkspaceBatchAction.CONFIRM:
            if resource_type == StoryWorkspaceResourceType.STORY:
                cursor = db.execute(
                    f"UPDATE {table} SET review_status = 'confirmed', status = 'published', "
                    "confirmed_at = CURRENT_TIMESTAMP, published_at = CURRENT_TIMESTAMP, "
                    "updated_at = CURRENT_TIMESTAMP "
                    "WHERE id = ? AND author_id = ? AND agent_generated = 1 "
                    "AND review_status = 'pending' AND status != 'archived'",
                    (resource_id, user_id),
                )
                # Final story approval is the bundle gate described by Dream:
                # the reviewed proposal is committed and its linked generated
                # characters/scenes become usable in one transaction.
                db.execute(
                    """
                    UPDATE story_workspace_scenes
                    SET review_status = 'confirmed', confirmed_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE story_id = ? AND author_id = ? AND agent_generated = 1
                      AND review_status = 'pending' AND status != 'archived'
                    """,
                    (resource_id, user_id),
                )
                db.execute(
                    """
                    UPDATE story_workspace_characters
                    SET review_status = 'confirmed', confirmed_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE author_id = ? AND agent_generated = 1
                      AND review_status = 'pending' AND status != 'archived'
                      AND id IN (
                        SELECT character_id FROM story_workspace_story_characters
                        WHERE story_id = ?
                      )
                    """,
                    (user_id, resource_id),
                )
            else:
                cursor = db.execute(
                    f"UPDATE {table} SET review_status = 'confirmed', "
                    "confirmed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP "
                    "WHERE id = ? AND author_id = ? AND agent_generated = 1 "
                    "AND review_status = 'pending' AND status != 'archived'",
                    (resource_id, user_id),
                )
            new_status = "confirmed"
        else:
            cursor = db.execute(
                f"UPDATE {table} SET review_status = 'rejected', review_notes = ?, "
                "updated_at = CURRENT_TIMESTAMP "
                "WHERE id = ? AND author_id = ? AND agent_generated = 1 "
                "AND review_status = 'pending' AND status != 'archived'",
                (review_notes, resource_id, user_id),
            )
            new_status = "rejected"

        if cursor.rowcount != 1:
            raise HTTPException(
                status_code=400,
                detail="Item is not in pending review status",
            )
        updated = _row_to_dict(_owned_review_row(db, table, resource_id, user_id))
        if action == StoryWorkspaceBatchAction.CONFIRM and resource_type == StoryWorkspaceResourceType.STORY:
            updated["execution"] = {
                "action": "publish_story_bundle",
                "status": "completed",
                "completed_at": updated.get("published_at"),
            }
        db.commit()
    except Exception:
        db.rollback()
        raise

    _audit_review_action(
        user_id,
        resource_type,
        resource_id,
        action,
        str(previous["review_status"]),
        new_status,
        review_notes,
    )
    return updated


def _archive_story(
    db: sqlite3.Connection,
    user_id: int,
    story_id: str,
) -> dict[str, Any]:
    try:
        db.execute("BEGIN IMMEDIATE")
        previous = _owned_review_row(
            db,
            _REVIEW_RESOURCES[StoryWorkspaceResourceType.STORY],
            story_id,
            user_id,
        )
        if previous["status"] == "archived":
            raise HTTPException(status_code=400, detail="Item is already archived")
        cursor = db.execute(
            "UPDATE story_workspace_stories "
            "SET status = 'archived', updated_at = CURRENT_TIMESTAMP "
            "WHERE id = ? AND author_id = ? AND agent_generated = 1 "
            "AND status != 'archived'",
            (story_id, user_id),
        )
        if cursor.rowcount != 1:
            raise HTTPException(status_code=400, detail="Item is already archived")
        updated = _row_to_dict(
            _owned_review_row(
                db,
                _REVIEW_RESOURCES[StoryWorkspaceResourceType.STORY],
                story_id,
                user_id,
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    _audit_review_action(
        user_id,
        StoryWorkspaceResourceType.STORY,
        story_id,
        StoryWorkspaceBatchAction.ARCHIVE,
        str(previous["status"]),
        "archived",
    )
    return updated


def _batch_review(
    db: sqlite3.Connection,
    user_id: int,
    request: _BatchReviewRequest,
) -> dict[str, Any]:
    table = _REVIEW_RESOURCES[request.resource_type]
    placeholders = ", ".join("?" for _ in request.ids)
    try:
        db.execute("BEGIN IMMEDIATE")
        rows = db.execute(
            f"SELECT * FROM {table} WHERE id IN ({placeholders}) "
            "AND author_id = ? AND agent_generated = 1",
            tuple(request.ids) + (user_id,),
        ).fetchall()
        previous_by_id = {str(row["id"]): row for row in rows}
        eligible_ids = [
            resource_id
            for resource_id in request.ids
            if resource_id in previous_by_id
            and previous_by_id[resource_id]["review_status"] == "pending"
            and previous_by_id[resource_id]["status"] != "archived"
        ]

        if eligible_ids:
            eligible_placeholders = ", ".join("?" for _ in eligible_ids)
            common_where = (
                f"WHERE id IN ({eligible_placeholders}) AND author_id = ? "
                "AND agent_generated = 1 AND review_status = 'pending' "
                "AND status != 'archived'"
            )
            params: tuple[Any, ...] = tuple(eligible_ids) + (user_id,)
            if request.action == StoryWorkspaceBatchAction.CONFIRM:
                if request.resource_type == StoryWorkspaceResourceType.STORY:
                    cursor = db.execute(
                        f"UPDATE {table} SET review_status = 'confirmed', status = 'published', "
                        "confirmed_at = CURRENT_TIMESTAMP, published_at = CURRENT_TIMESTAMP, "
                        "updated_at = CURRENT_TIMESTAMP " + common_where,
                        params,
                    )
                    for story_id in eligible_ids:
                        db.execute(
                            "UPDATE story_workspace_scenes SET review_status = 'confirmed', "
                            "confirmed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP "
                            "WHERE story_id = ? AND author_id = ? AND agent_generated = 1 "
                            "AND review_status = 'pending' AND status != 'archived'",
                            (story_id, user_id),
                        )
                        db.execute(
                            "UPDATE story_workspace_characters SET review_status = 'confirmed', "
                            "confirmed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP "
                            "WHERE author_id = ? AND agent_generated = 1 "
                            "AND review_status = 'pending' AND status != 'archived' "
                            "AND id IN (SELECT character_id FROM story_workspace_story_characters "
                            "WHERE story_id = ?)",
                            (user_id, story_id),
                        )
                else:
                    cursor = db.execute(
                        f"UPDATE {table} SET review_status = 'confirmed', "
                        "confirmed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP "
                        + common_where,
                        params,
                    )
                new_status = "confirmed"
            elif request.action == StoryWorkspaceBatchAction.REJECT:
                cursor = db.execute(
                    f"UPDATE {table} SET review_status = 'rejected', "
                    "review_notes = ?, updated_at = CURRENT_TIMESTAMP "
                    + common_where,
                    (request.review_notes,) + params,
                )
                new_status = "rejected"
            else:
                archive_fields = "status = 'archived', "
                if request.resource_type != StoryWorkspaceResourceType.STORY:
                    archive_fields += "archived_at = CURRENT_TIMESTAMP, "
                cursor = db.execute(
                    f"UPDATE {table} SET {archive_fields}"
                    "updated_at = CURRENT_TIMESTAMP " + common_where,
                    params,
                )
                new_status = "archived"

            if cursor.rowcount != len(eligible_ids):
                raise HTTPException(
                    status_code=409,
                    detail="Review state changed during batch operation",
                )

            updated_rows = db.execute(
                f"SELECT * FROM {table} WHERE id IN ({eligible_placeholders}) "
                "AND author_id = ?",
                params,
            ).fetchall()
            updated_by_id = {
                str(row["id"]): _row_to_dict(row) for row in updated_rows
            }
        else:
            new_status = request.action.value
            updated_by_id = {}

        db.commit()
    except Exception:
        db.rollback()
        raise

    updated_items = [updated_by_id[resource_id] for resource_id in eligible_ids]
    skipped_ids = [
        resource_id for resource_id in request.ids if resource_id not in updated_by_id
    ]
    for resource_id in eligible_ids:
        previous = previous_by_id[resource_id]
        previous_status = (
            previous["status"]
            if request.action == StoryWorkspaceBatchAction.ARCHIVE
            else previous["review_status"]
        )
        _audit_review_action(
            user_id,
            request.resource_type,
            resource_id,
            request.action,
            str(previous_status),
            new_status,
            request.review_notes,
        )

    return {
        "success": True,
        "action": request.action.value,
        "resource_type": request.resource_type.value,
        "total_requested": len(request.ids),
        "total_updated": len(updated_items),
        "skipped_ids": skipped_ids,
        "updated_items": updated_items,
    }


@router.get("/workspace")
def get_workspace(
    current_user: dict[str, Any] = Depends(get_current_user),
    db: sqlite3.Connection = Depends(_story_db),
) -> dict[str, Any]:
    user_id = _user_id(current_user)
    row = db.execute(
        "SELECT * FROM story_workspace_workspaces WHERE owner_id = ? "
        "ORDER BY created_at ASC, id ASC LIMIT 1",
        (user_id,),
    ).fetchone()
    if row is None:
        workspace_id = str(uuid4())
        db.execute(
            "INSERT INTO story_workspace_workspaces (id, name, owner_id, settings) "
            "VALUES (?, ?, ?, ?)",
            (workspace_id, "默认工作区", user_id, "{}"),
        )
        db.commit()
        row = db.execute(
            "SELECT * FROM story_workspace_workspaces WHERE id = ? AND owner_id = ?",
            (workspace_id, user_id),
        ).fetchone()
    return _row_to_dict(row)


@router.patch("/workspace/{workspace_id}")
def patch_workspace(
    workspace_id: str,
    patch: StoryWorkspaceWorkspacePatch,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: sqlite3.Connection = Depends(_story_db),
) -> dict[str, Any]:
    values = patch.model_dump(exclude_unset=True)
    if "settings" in values:
        values["settings"] = json.dumps(values["settings"], ensure_ascii=False)
    return _patch_owned_row(
        db,
        "story_workspace_workspaces",
        workspace_id,
        "owner_id",
        _user_id(current_user),
        values,
    )


@router.get("/stories")
def list_stories(
    q: Optional[str] = None,
    review_status: Optional[str] = None,
    status: Optional[str] = None,
    type: Optional[str] = None,
    sort: str = "updated_at",
    order: str = "desc",
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: dict[str, Any] = Depends(get_current_user),
    db: sqlite3.Connection = Depends(_story_db),
) -> dict[str, Any]:
    conditions = ["author_id = ?"]
    params: list[Any] = [_user_id(current_user)]
    if q:
        conditions.append("title LIKE ?")
        params.append(f"%{q}%")
    _append_in_filter(conditions, params, "review_status", review_status)
    _append_in_filter(conditions, params, "status", status)
    _append_in_filter(conditions, params, "type", type)
    where = " WHERE " + " AND ".join(conditions)
    select_sql = "SELECT * FROM story_workspace_stories" + where
    select_sql += _sort_clause(sort, order, _STORY_SORT_FIELDS)
    count_sql = "SELECT COUNT(*) FROM story_workspace_stories" + where
    return _paginate_query(db, select_sql, count_sql, params, page, per_page)


@router.get("/stories/{story_id}")
def get_story(
    story_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: sqlite3.Connection = Depends(_story_db),
) -> dict[str, Any]:
    user_id = _user_id(current_user)
    result = _row_to_dict(
        _owned_row(db, "story_workspace_stories", story_id, "author_id", user_id)
    )
    characters = db.execute(
        "SELECT c.*, sc.role_type FROM story_workspace_characters c "
        "JOIN story_workspace_story_characters sc ON sc.character_id = c.id "
        "WHERE sc.story_id = ? AND c.author_id = ? "
        "ORDER BY c.name ASC, c.id ASC",
        (story_id, user_id),
    ).fetchall()
    scenes = db.execute(
        "SELECT * FROM story_workspace_scenes "
        "WHERE story_id = ? AND author_id = ? ORDER BY order_index ASC, id ASC",
        (story_id, user_id),
    ).fetchall()
    result["characters"] = [_row_to_dict(row) for row in characters]
    result["scenes"] = [_row_to_dict(row) for row in scenes]
    return result


@router.patch("/stories/{story_id}")
def patch_story(
    story_id: str,
    patch: StoryWorkspaceStoryPatch,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: sqlite3.Connection = Depends(_story_db),
) -> dict[str, Any]:
    return _patch_owned_row(
        db,
        "story_workspace_stories",
        story_id,
        "author_id",
        _user_id(current_user),
        patch.model_dump(exclude_unset=True),
    )


@router.get("/characters")
def list_characters(
    q: Optional[str] = None,
    review_status: Optional[str] = None,
    sort: str = "updated_at",
    order: str = "desc",
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: dict[str, Any] = Depends(get_current_user),
    db: sqlite3.Connection = Depends(_story_db),
) -> dict[str, Any]:
    conditions = ["author_id = ?"]
    params: list[Any] = [_user_id(current_user)]
    if q:
        conditions.append("name LIKE ?")
        params.append(f"%{q}%")
    _append_in_filter(conditions, params, "review_status", review_status)
    where = " WHERE " + " AND ".join(conditions)
    select_sql = "SELECT * FROM story_workspace_characters" + where
    select_sql += _sort_clause(sort, order, _CHARACTER_SORT_FIELDS)
    count_sql = "SELECT COUNT(*) FROM story_workspace_characters" + where
    return _paginate_query(db, select_sql, count_sql, params, page, per_page)


@router.get("/characters/{character_id}")
def get_character(
    character_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: sqlite3.Connection = Depends(_story_db),
) -> dict[str, Any]:
    user_id = _user_id(current_user)
    result = _row_to_dict(
        _owned_row(
            db,
            "story_workspace_characters",
            character_id,
            "author_id",
            user_id,
        )
    )
    stories = db.execute(
        "SELECT s.*, sc.role_type FROM story_workspace_stories s "
        "JOIN story_workspace_story_characters sc ON sc.story_id = s.id "
        "WHERE sc.character_id = ? AND s.author_id = ? "
        "ORDER BY s.updated_at DESC, s.id ASC",
        (character_id, user_id),
    ).fetchall()
    result["stories"] = [_row_to_dict(row) for row in stories]
    return result


@router.patch("/characters/{character_id}")
def patch_character(
    character_id: str,
    patch: StoryWorkspaceCharacterPatch,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: sqlite3.Connection = Depends(_story_db),
) -> dict[str, Any]:
    values = patch.model_dump(exclude_unset=True)
    if "tags" in values:
        values["tags"] = json.dumps(values["tags"], ensure_ascii=False)
    return _patch_owned_row(
        db,
        "story_workspace_characters",
        character_id,
        "author_id",
        _user_id(current_user),
        values,
    )


@router.get("/scenes")
def list_scenes(
    q: Optional[str] = None,
    review_status: Optional[str] = None,
    story_id: Optional[str] = None,
    sort: str = "updated_at",
    order: str = "desc",
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: dict[str, Any] = Depends(get_current_user),
    db: sqlite3.Connection = Depends(_story_db),
) -> dict[str, Any]:
    conditions = ["author_id = ?"]
    params: list[Any] = [_user_id(current_user)]
    if q:
        conditions.append("name LIKE ?")
        params.append(f"%{q}%")
    if story_id:
        conditions.append("story_id = ?")
        params.append(story_id)
    _append_in_filter(conditions, params, "review_status", review_status)
    where = " WHERE " + " AND ".join(conditions)
    select_sql = "SELECT * FROM story_workspace_scenes" + where
    select_sql += _sort_clause(sort, order, _SCENE_SORT_FIELDS)
    count_sql = "SELECT COUNT(*) FROM story_workspace_scenes" + where
    return _paginate_query(db, select_sql, count_sql, params, page, per_page)


@router.get("/scenes/{scene_id}")
def get_scene(
    scene_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: sqlite3.Connection = Depends(_story_db),
) -> dict[str, Any]:
    user_id = _user_id(current_user)
    result = _row_to_dict(
        _owned_row(db, "story_workspace_scenes", scene_id, "author_id", user_id)
    )
    story = None
    if result.get("story_id"):
        story_row = db.execute(
            "SELECT * FROM story_workspace_stories WHERE id = ? AND author_id = ?",
            (result["story_id"], user_id),
        ).fetchone()
        if story_row is not None:
            story = _row_to_dict(story_row)
    characters = db.execute(
        "SELECT c.* FROM story_workspace_characters c "
        "JOIN story_workspace_scene_characters sc ON sc.character_id = c.id "
        "WHERE sc.scene_id = ? AND c.author_id = ? "
        "ORDER BY c.name ASC, c.id ASC",
        (scene_id, user_id),
    ).fetchall()
    result["story"] = story
    result["characters"] = [_row_to_dict(row) for row in characters]
    return result


@router.patch("/scenes/{scene_id}")
def patch_scene(
    scene_id: str,
    patch: StoryWorkspaceScenePatch,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: sqlite3.Connection = Depends(_story_db),
) -> dict[str, Any]:
    user_id = _user_id(current_user)
    values = patch.model_dump(exclude_unset=True)
    if "story_id" in values and values["story_id"] is not None:
        _owned_row(
            db,
            "story_workspace_stories",
            values["story_id"],
            "author_id",
            user_id,
        )
    return _patch_owned_row(
        db,
        "story_workspace_scenes",
        scene_id,
        "author_id",
        user_id,
        values,
    )


@router.post("/stories/{story_id}/confirm")
def confirm_story(
    story_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: sqlite3.Connection = Depends(_story_db),
) -> dict[str, Any]:
    return _transition_pending_review(
        db,
        _user_id(current_user),
        StoryWorkspaceResourceType.STORY,
        story_id,
        StoryWorkspaceBatchAction.CONFIRM,
    )


@router.post("/stories/{story_id}/reject")
def reject_story(
    story_id: str,
    body: Optional[_ReviewActionRequest] = None,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: sqlite3.Connection = Depends(_story_db),
) -> dict[str, Any]:
    return _transition_pending_review(
        db,
        _user_id(current_user),
        StoryWorkspaceResourceType.STORY,
        story_id,
        StoryWorkspaceBatchAction.REJECT,
        body.review_notes if body else None,
    )


@router.post("/stories/{story_id}/archive")
def archive_story(
    story_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: sqlite3.Connection = Depends(_story_db),
) -> dict[str, Any]:
    return _archive_story(db, _user_id(current_user), story_id)


@router.post("/characters/{character_id}/confirm")
def confirm_character(
    character_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: sqlite3.Connection = Depends(_story_db),
) -> dict[str, Any]:
    return _transition_pending_review(
        db,
        _user_id(current_user),
        StoryWorkspaceResourceType.CHARACTER,
        character_id,
        StoryWorkspaceBatchAction.CONFIRM,
    )


@router.post("/characters/{character_id}/reject")
def reject_character(
    character_id: str,
    body: Optional[_ReviewActionRequest] = None,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: sqlite3.Connection = Depends(_story_db),
) -> dict[str, Any]:
    return _transition_pending_review(
        db,
        _user_id(current_user),
        StoryWorkspaceResourceType.CHARACTER,
        character_id,
        StoryWorkspaceBatchAction.REJECT,
        body.review_notes if body else None,
    )


@router.post("/scenes/{scene_id}/confirm")
def confirm_scene(
    scene_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: sqlite3.Connection = Depends(_story_db),
) -> dict[str, Any]:
    return _transition_pending_review(
        db,
        _user_id(current_user),
        StoryWorkspaceResourceType.SCENE,
        scene_id,
        StoryWorkspaceBatchAction.CONFIRM,
    )


@router.post("/scenes/{scene_id}/reject")
def reject_scene(
    scene_id: str,
    body: Optional[_ReviewActionRequest] = None,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: sqlite3.Connection = Depends(_story_db),
) -> dict[str, Any]:
    return _transition_pending_review(
        db,
        _user_id(current_user),
        StoryWorkspaceResourceType.SCENE,
        scene_id,
        StoryWorkspaceBatchAction.REJECT,
        body.review_notes if body else None,
    )


@router.post("/batch")
def batch_review(
    body: _BatchReviewRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: sqlite3.Connection = Depends(_story_db),
) -> dict[str, Any]:
    return _batch_review(db, _user_id(current_user), body)


@router.post("/internal/agent-output")
def receive_agent_story_output(
    body: StoryWorkspaceAgentStoryPayload,
    agent_session_id: Optional[str] = Header(None, alias="X-Agent-Session-Id"),
    current_user: dict[str, Any] = Depends(get_current_user),
    db: sqlite3.Connection = Depends(_story_db),
) -> dict[str, Any]:
    """Receive one authenticated Agent story bundle and persist it atomically."""

    if not agent_session_id or not agent_session_id.strip():
        raise HTTPException(status_code=400, detail="X-Agent-Session-Id is required")

    user_id = _user_id(current_user)
    try:
        workspace_id = get_or_create_default_workspace(db, user_id)
        return store_agent_story_output(
            db,
            user_id,
            workspace_id,
            agent_session_id,
            body,
        )
    except AgentIntegrationError as exc:
        raise HTTPException(
            status_code=422,
            detail="Unable to persist Agent story output",
        ) from exc


@router.post("/workflow-preflights", status_code=202)
async def create_workflow_preflight(
    request: _WorkflowPreflightRequest,
    current_user: dict[str, Any] = Depends(_story_workflow_current_user),
    gateway: StoryWorkflowGateway = Depends(get_story_workflow_gateway),
):
    try:
        actor = _workflow_actor(current_user)
    except ApiRouteError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content=build_error_payload(exc.code),
        )
    return await _workflow_call(gateway.create_preflight(request, actor=actor))


@router.get("/workflow-preflights/{preflight_id}")
async def get_workflow_preflight(
    preflight_id: str,
    current_user: dict[str, Any] = Depends(_story_workflow_current_user),
    gateway: StoryWorkflowGateway = Depends(get_story_workflow_gateway),
):
    try:
        actor = _workflow_actor(current_user)
    except ApiRouteError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content=build_error_payload(exc.code),
        )
    return await _workflow_call(gateway.get_preflight(preflight_id, actor=actor))


@router.post("/workflow-runs", status_code=201)
async def create_workflow_run(
    request: _WorkflowRunCreateRequest,
    current_user: dict[str, Any] = Depends(_story_workflow_current_user),
    gateway: StoryWorkflowGateway = Depends(get_story_workflow_gateway),
):
    try:
        actor = _workflow_actor(current_user)
    except ApiRouteError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content=build_error_payload(exc.code),
        )
    return await _workflow_call(gateway.create_run(request, actor=actor))


@router.get("/workflow-runs/{workflow_run_id}")
async def get_workflow_run(
    workflow_run_id: str,
    current_user: dict[str, Any] = Depends(_story_workflow_current_user),
    gateway: StoryWorkflowGateway = Depends(get_story_workflow_gateway),
):
    try:
        actor = _workflow_actor(current_user)
    except ApiRouteError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content=build_error_payload(exc.code),
        )
    return await _workflow_call(gateway.get_run(workflow_run_id, actor=actor))


@router.get("/workflow-runs/{workflow_run_id}/dream-files")
async def get_workflow_run_dream_files(
    workflow_run_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    gateway: StoryWorkflowGateway = Depends(get_story_workflow_gateway),
):
    try:
        actor = {"actor_id": str(current_user["user_id"])}
    except (KeyError, TypeError, ValueError):
        exc = ApiRouteError("WORKFLOW_PERMISSION_DENIED", status_code=403)
        return JSONResponse(
            status_code=exc.status_code,
            content=build_error_payload(exc.code),
        )
    return await _workflow_call(
        gateway.get_dream_files(workflow_run_id, actor=actor),
        by_alias=True,
    )


@router.post(
    "/workflow-runs/{workflow_run_id}/dream-confirmation",
    status_code=202,
)
async def submit_workflow_run_dream_confirmation(
    workflow_run_id: str,
    request: StoryWorkspaceDreamConfirmationCommand,
    current_user: dict[str, Any] = Depends(get_current_user),
    gateway: StoryWorkflowGateway = Depends(get_story_workflow_gateway),
):
    """Persist one hidden confirmation and queue the originating Chat Agent."""

    try:
        actor = {"actor_id": str(current_user["user_id"])}
    except (KeyError, TypeError, ValueError):
        exc = ApiRouteError("WORKFLOW_PERMISSION_DENIED", status_code=403)
        return JSONResponse(
            status_code=exc.status_code,
            content=build_error_payload(exc.code),
        )
    return await _workflow_call(
        gateway.submit_dream_confirmation(
            workflow_run_id,
            request,
            actor=actor,
        ),
        by_alias=True,
    )


@router.post("/workflow-runs/{workflow_run_id}/retry", status_code=201)
async def retry_workflow_run(
    workflow_run_id: str,
    request: _WorkflowRunRetryRequest,
    current_user: dict[str, Any] = Depends(_story_workflow_current_user),
    gateway: StoryWorkflowGateway = Depends(get_story_workflow_gateway),
):
    try:
        actor = _workflow_actor(current_user)
    except ApiRouteError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content=build_error_payload(exc.code),
        )
    return await _workflow_call(gateway.retry_run(workflow_run_id, request, actor=actor))


@router.post("/workflow-runs/{workflow_run_id}/cancel")
async def cancel_workflow_run(
    workflow_run_id: str,
    request: _WorkflowRunCancelRequest,
    current_user: dict[str, Any] = Depends(_story_workflow_current_user),
    gateway: StoryWorkflowGateway = Depends(get_story_workflow_gateway),
):
    try:
        actor = _workflow_actor(current_user)
    except ApiRouteError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content=build_error_payload(exc.code),
        )
    return await _workflow_call(gateway.cancel_run(workflow_run_id, request, actor=actor))


@router.post("/runs/{workflow_run_id}/guidance", status_code=202)
async def submit_run_guidance(
    workflow_run_id: str,
    request: StoryWorkspaceGuidanceCommandPayload,
    current_user: dict[str, Any] = Depends(_story_workflow_current_user),
    gateway: StoryWorkflowGateway = Depends(get_story_workflow_gateway),
):
    """Submit one idempotent guidance command to a guidable run.

    202 — accepted (persisted as a ``metadata.kind="story-workspace-guidance"``
    chat_message row and handed to the same thread's runner as a new turn);
    a same-key same-content replay also returns 202 with ``replayed: true``
    and no duplicate injection. 409 — run not guidable or same key with
    different content (``IDEMPOTENCY_CONFLICT``).
    """
    try:
        actor = _workflow_actor(current_user)
    except ApiRouteError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content=build_error_payload(exc.code),
        )
    return await _workflow_call(
        gateway.submit_guidance(workflow_run_id, request, actor=actor)
    )
