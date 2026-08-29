# [Input] Notion connector state and snapshot resource helpers.
# [Output] Build lightweight canonical indexes and materialize them into workspace files.
# [Pos] sync node in backend/notion
# [Sync] 2026-07-04: initial canonical snapshot builder + workspace materializer.
# [Sync] 2026-08-28: keep background snapshots index-only; page Markdown is
#                    fetched on demand through the Runtime selected-page Read hook.
# [Sync] 2026-08-28: clear failed thread projections without following symlinks
#                    so stale `.notion` content cannot survive a fail-closed turn.
# [Sync] 2026-08-28: discard legacy embedded page bodies during every thread
#                    projection so the virtual Read hook remains the only body path.

"""Canonical Notion snapshot assembly and workspace file materialization."""
from __future__ import annotations

import json
import shutil
import stat
from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from libs.claude_agent_kit.server.notion_snapshot import (
    CanonicalWorkspaceSnapshot,
    SnapshotLifecycleState,
    SnapshotMetadata,
    get_notion_snapshot_resource_data,
)

from .errors import NotionOperationError
from .operations import DatabaseQuery, NotionOperationClient, normalize_page_item

NOTION_DIRNAME = ".notion"


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _json_write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _resource_title(resource: Mapping[str, Any]) -> str:
    return str(resource.get("title") or resource.get("name") or resource.get("external_id") or "").strip()


def _build_index_entry(page_summary: Mapping[str, Any]) -> dict[str, Any]:
    """Project only the fields needed to locate a page for a later live read."""

    page_id = str(page_summary.get("page_id") or "").strip()
    return {
        "page_id": page_id,
        "title": _resource_title(page_summary) or page_id,
        "url": page_summary.get("url") or "",
        "last_edited": page_summary.get("last_edited") or "",
    }


def _build_database_summary(resource: Mapping[str, Any], pages: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "database_id": str(resource.get("external_id") or ""),
        "title": _resource_title(resource),
        "page_count": len(pages),
        "properties_schema": _mapping(resource.get("metadata")).get("properties_schema") or {},
        "last_edited": _mapping(resource.get("metadata")).get("last_edited") or "",
        "url": _mapping(resource.get("metadata")).get("url") or "",
    }


async def build_canonical_snapshot(
    *,
    connector: Mapping[str, Any],
    selected_resources: Iterable[Mapping[str, Any]],
    workspace_id: str,
    operations: NotionOperationClient,
    page_size: int = 100,
) -> dict[str, Any]:
    """Build an index-only snapshot from selected Notion resources.

    Database queries enumerate row IDs and compact metadata. Page bodies are
    deliberately excluded: the Agent Runtime reads one selected page at a time
    through the credential-isolated Read hook when the user actually needs it.
    """

    selected = [dict(item) for item in selected_resources]
    selected_databases = [item for item in selected if item.get("resource_type") == "notion_database"]
    selected_pages = [item for item in selected if item.get("resource_type") == "notion_page"]

    index_entries: dict[str, dict[str, Any]] = {}
    databases_payload: list[dict[str, Any]] = []
    database_pages_payload: dict[str, list[dict[str, Any]]] = {}
    source_revisions: list[str] = []

    for database_resource in selected_databases:
        database_id = str(database_resource.get("external_id") or "").strip()
        if not database_id:
            continue
        indexed_pages: list[dict[str, Any]] = []
        start_cursor: str | None = None
        observed_cursors: set[str] = set()
        while True:
            query_result = await operations.query_database(
                DatabaseQuery(
                    database_id=database_id,
                    page_size=page_size,
                    start_cursor=start_cursor,
                )
            )
            for raw_page in query_result.results:
                page_summary = normalize_page_item(raw_page)
                entry = _build_index_entry(page_summary)
                page_id = str(entry["page_id"] or "").strip()
                if not page_id:
                    continue
                index_entries.setdefault(page_id, entry)
                indexed_pages.append(entry)
                if entry.get("last_edited"):
                    source_revisions.append(str(entry["last_edited"]))
            if not query_result.has_more:
                break
            next_cursor = str(query_result.next_cursor or "").strip()
            if not next_cursor or next_cursor in observed_cursors:
                raise NotionOperationError(
                    "Notion database pagination did not advance. Please retry."
                )
            observed_cursors.add(next_cursor)
            start_cursor = next_cursor
        database_pages_payload[database_id] = indexed_pages
        databases_payload.append(_build_database_summary(database_resource, indexed_pages))
        database_revision = _mapping(database_resource.get("metadata")).get("last_edited")
        if database_revision:
            source_revisions.append(str(database_revision))

    for page_resource in selected_pages:
        page_id = str(page_resource.get("external_id") or "").strip()
        if not page_id:
            continue
        page_summary = normalize_page_item(
            {
                "id": page_id,
                "title": page_resource.get("title"),
                "url": _mapping(page_resource.get("metadata")).get("url") or "",
                "last_edited": _mapping(page_resource.get("metadata")).get("last_edited") or "",
                "parent": _mapping(page_resource.get("metadata")).get("parent") or {},
            }
        )
        entry = _build_index_entry(page_summary)
        index_entries.setdefault(page_id, entry)
        if entry.get("last_edited"):
            source_revisions.append(str(entry["last_edited"]))

    fetched_at = _utcnow_iso()
    snapshot_version = f"snap-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}"
    source_revision = max(source_revisions) if source_revisions else snapshot_version
    sync_cursor = f"cursor-{uuid4().hex[:8]}"

    metadata = SnapshotMetadata(
        workspace_id=workspace_id,
        resource_connector_id=str(connector.get("id") or ""),
        snapshot_version=snapshot_version,
        source_revision=source_revision,
        sync_cursor=sync_cursor,
        fetched_at=fetched_at,
        state=SnapshotLifecycleState.SNAPSHOT_READY,
    )
    CanonicalWorkspaceSnapshot(
        metadata=metadata,
        connector=dict(connector),
        index=list(index_entries.values()),
        databases=databases_payload,
        database_pages=database_pages_payload,
        pages={},
    )
    payload = {
        "metadata": {
            **metadata.__dict__,
            "state": metadata.state.value,
        },
        "connector": dict(connector),
        "index": list(index_entries.values()),
        "databases": databases_payload,
        "database_pages": database_pages_payload,
        "pages": {},
    }
    payload["identity"] = {
        "snapshot_version": snapshot_version,
        "source_revision": source_revision,
        "sync_cursor": sync_cursor,
        "workspace_id": workspace_id,
        "resource_connector_id": str(connector.get("id") or ""),
    }
    return payload


def clear_workspace_snapshot(workspace_path: Path) -> None:
    """Remove the workspace-local `.notion/` materialization."""

    notion_dir = workspace_path / NOTION_DIRNAME
    try:
        info = notion_dir.lstat()
    except FileNotFoundError:
        return
    if stat.S_ISDIR(info.st_mode) and not stat.S_ISLNK(info.st_mode):
        shutil.rmtree(notion_dir)
    else:
        notion_dir.unlink()


def materialize_workspace_snapshot(
    workspace_path: Path,
    *,
    connector: Mapping[str, Any] | None = None,
    snapshot: Mapping[str, Any] | None = None,
) -> None:
    """Write the canonical snapshot into workspace-local `.notion/` files."""

    notion_dir = workspace_path / NOTION_DIRNAME
    pages_dir = notion_dir / "pages"
    databases_dir = notion_dir / "databases"
    notion_dir.mkdir(parents=True, exist_ok=True)
    pages_dir.mkdir(parents=True, exist_ok=True)
    databases_dir.mkdir(parents=True, exist_ok=True)

    readme = (
        "# Notion connector index\n\n"
        "This read-only directory contains selected resource IDs and compact metadata.\n"
        "Page bodies are fetched on demand when Runtime intercepts Read(.notion/pages/<id>.json).\n"
    )
    (notion_dir / "README.md").write_text(readme, encoding="utf-8")

    snapshot_payload = _mapping(snapshot)
    snapshot_meta = _mapping(snapshot_payload.get("metadata"))
    connector_payload = dict(connector or snapshot_payload.get("connector") or {})

    if snapshot_payload:
        _json_write(notion_dir / "snapshot.json", get_notion_snapshot_resource_data(".notion/snapshot.json", snapshot_payload))
        _json_write(notion_dir / "connector.json", get_notion_snapshot_resource_data(".notion/connector.json", snapshot_payload))
        _json_write(notion_dir / "index.json", get_notion_snapshot_resource_data(".notion/index.json", snapshot_payload))
        _json_write(notion_dir / "databases.json", get_notion_snapshot_resource_data(".notion/databases.json", snapshot_payload))

        keep_database_ids = set()
        for database_item in snapshot_payload.get("databases") or []:
            if not isinstance(database_item, Mapping):
                continue
            database_id = str(database_item.get("database_id") or "").strip()
            if not database_id:
                continue
            keep_database_ids.add(database_id)
            _json_write(
                databases_dir / f"{database_id}.json",
                get_notion_snapshot_resource_data(
                    f".notion/databases/{database_id}.json",
                    snapshot_payload,
                ),
            )

        for stale_path in databases_dir.glob("*.json"):
            if stale_path.stem not in keep_database_ids:
                stale_path.unlink(missing_ok=True)
        # ``pages`` is a legacy-compatible snapshot field only. Never copy an
        # old embedded body into a thread: exact virtual page Reads are owned
        # exclusively by the Runtime hook after index-membership validation.
        for stale_path in pages_dir.glob("*.json"):
            stale_path.unlink(missing_ok=True)
        return

    # No snapshot attached yet: keep the connector metadata visible and write
    # empty canonical placeholders so workspace_context can report status.
    _json_write(notion_dir / "snapshot.json", snapshot_meta)
    _json_write(
        notion_dir / "connector.json",
        {
            **connector_payload,
            "snapshot": snapshot_meta,
        },
    )
    _json_write(notion_dir / "index.json", {"pages": [], "snapshot": snapshot_meta})
    _json_write(notion_dir / "databases.json", {"databases": [], "snapshot": snapshot_meta})
    for stale_path in databases_dir.glob("*.json"):
        stale_path.unlink(missing_ok=True)
    for stale_path in pages_dir.glob("*.json"):
        stale_path.unlink(missing_ok=True)
