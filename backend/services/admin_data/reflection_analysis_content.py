# [Input] Actor-owned Notion facade, accepted resource index and read-only page operation.
# [Output] Metadata-only candidates and per-request frozen bodies without synchronization or workspace scan.
# [Pos] Reflections source assembly; Admin owns persistence and Agent prompt resolution.
# [Sync] 2026-10-13: distinguish index versions from submission-time body reads and recheck source identity.
# [Sync] 2026-10-13: retain complete request-bound candidates briefly across a definite OAuth renewal, always revalidating before creation.
"""Read only pages already included in the accepted Notion index."""
from __future__ import annotations
import asyncio
import hashlib
import json
import os
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock

from notion.errors import NotionSnapshotNotReadyError
from notion.operations import NotionOperationClient
from notion.today import snapshot_records, safe_url, page_identity
from .errors import AdminDataError
from .reflection_analysis_content_data import ReflectionNotionInputDTO, ReflectionNotionPageDTO


@dataclass(frozen=True)
class _PreparedNotionSource:
    content: ReflectionNotionInputDTO = field(repr=False)
    context: object = field(repr=False)
    metadata: dict = field(repr=False)
    credential_identity: object = field(repr=False)


@dataclass(frozen=True)
class _PreparedEntry:
    fingerprint: str
    source: _PreparedNotionSource = field(repr=False)
    expires_at: float
    payload_bytes: int
    timer: object = field(repr=False)
    marker: object = field(repr=False)


class NotionPreparationCache:
    """Bounded private read candidates, never authorization or committed task state."""

    def __init__(self, *, ttl_seconds: int, max_entries: int, max_bytes: int,
                 clock=time.monotonic, schedule=None):
        if any(type(value) is not int or value <= 0 for value in (ttl_seconds, max_entries, max_bytes)):
            raise AdminDataError("REFLECTION_PREPARATION_CONFIGURATION_INVALID", 503)
        self.ttl_seconds, self.max_entries, self.max_bytes = ttl_seconds, max_entries, max_bytes
        self._clock = clock
        self._schedule = schedule or (lambda delay, callback: asyncio.get_running_loop().call_later(delay, callback))
        self._entries = OrderedDict()
        self._bytes = 0
        self._lock = RLock()

    def discard(self, key):
        with self._lock:
            item = self._entries.pop(key, None)
            if item is not None:
                self._bytes -= item.payload_bytes
                item.timer.cancel()

    def get(self, key, fingerprint):
        with self._lock:
            item = self._entries.get(key)
            if item is None:
                return None
            if self._clock() >= item.expires_at:
                self.discard(key)
                return None
            if item.fingerprint != fingerprint:
                raise AdminDataError("REFLECTION_SUBMISSION_CONFLICT", 409)
            self._entries.move_to_end(key)
            return item.source

    def _expire(self, key, marker):
        with self._lock:
            item = self._entries.get(key)
            if item is not None and item.marker is marker:
                self.discard(key)

    def put(self, key, fingerprint, value):
        size = len(value.content.model_dump_json().encode()) + len(json.dumps(value.metadata).encode())
        if size > self.max_bytes:
            raise AdminDataError("REFLECTION_PREPARATION_TOO_LARGE", 413)
        with self._lock:
            existing = self.get(key, fingerprint)
            if existing is not None:
                return existing
            self.discard(key)
            while self._entries and (len(self._entries) >= self.max_entries or self._bytes + size > self.max_bytes):
                self.discard(next(iter(self._entries)))
            expiry = self._clock() + self.ttl_seconds
            marker = object()
            timer = self._schedule(self.ttl_seconds, lambda: self._expire(key, marker))
            self._entries[key] = _PreparedEntry(fingerprint, value, expiry, size, timer, marker)
            self._bytes += size
            return value


_PREPARATION_CACHE: NotionPreparationCache | None = None


def _preparation_cache():
    global _PREPARATION_CACHE
    if _PREPARATION_CACHE is None:
        from notion.snapshot_store import NotionSnapshotStore
        try:
            _PREPARATION_CACHE = NotionPreparationCache(
                ttl_seconds=int(os.environ.get("INK_REFLECTIONS_SOURCE_PREPARATION_TTL_SECONDS", "300")),
                max_entries=int(os.environ.get("INK_REFLECTIONS_SOURCE_PREPARATION_MAX_ENTRIES", "32")),
                max_bytes=int(os.environ.get("INK_REFLECTIONS_SOURCE_PREPARATION_MAX_BYTES", str(NotionSnapshotStore().max_snapshot_bytes))),
            )
        except (ValueError, TypeError):
            raise AdminDataError("REFLECTION_PREPARATION_CONFIGURATION_INVALID", 503) from None
    return _PREPARATION_CACHE


def clear_notion_analysis_preparation(user_id, request_key):
    if request_key and _PREPARATION_CACHE is not None:
        _PREPARATION_CACHE.discard((str(user_id), request_key))

def _records(snapshot):
    if snapshot is None:
        raise AdminDataError("NOTION_SNAPSHOT_UNAVAILABLE", 409)
    records, reasons = snapshot_records(snapshot)
    if reasons:
        # Contradictory duplicates or malformed identities cannot silently narrow analysis.
        raise AdminDataError("NOTION_ANALYSIS_INDEX_INVALID", 409)
    return {key: item for key, item in records.items() if item.get("archived") is not True and item.get("in_trash") is not True}


def _validate_mounted_scope(connector, snapshot):
    if snapshot is None:
        return
    source = snapshot.get("connector") or {}
    for kind, key in (("notion_page", "selected_pages"), ("notion_database", "selected_databases")):
        current = {page_identity(item.get("external_id")) for item in connector.get("sources") or [] if item.get("resource_type") == kind}
        indexed = {page_identity(item) for item in source.get(key) or []}
        if current != indexed:
            raise AdminDataError("NOTION_ANALYSIS_SCOPE_CHANGED", 409)

def analysis_content_candidates(facade):
    connector = facade.get_connector()
    snapshot = facade.get_current_snapshot()
    if snapshot is None:
        return {"status": "no_snapshot", "page_count": 0, "snapshot_version": None}
    _validate_mounted_scope(connector, snapshot)
    records = _records(snapshot)
    return {"status": "ready" if records else "empty", "page_count": len(records),
            "connector_id": connector["id"], "snapshot_version": snapshot["metadata"]["snapshot_version"]}

async def freeze_notion_analysis_input(facade, expected_version: str | None, expected_connector_id: str | None,
                                      *, request_key: str | None = None, request_fingerprint: str | None = None):
    cache = _preparation_cache() if request_key and request_fingerprint else None
    key = (str(facade.user_id), request_key)
    prepared = cache.get(key, request_fingerprint) if cache else None
    if prepared is None:
        prepared = await _read_notion_analysis_input(facade, expected_version, expected_connector_id)
        if cache:
            prepared = cache.put(key, request_fingerprint, prepared)
    try:
        current = await asyncio.to_thread(facade.get_connector)
        latest = await asyncio.to_thread(facade.get_current_snapshot)
        after = await asyncio.to_thread(facade._credential_identity)
        if (prepared.credential_identity != after or facade._read_context(current) != prepared.context
            or latest is None or latest["metadata"] != prepared.metadata):
            raise NotionSnapshotNotReadyError("Notion analysis scope changed. Refresh and retry.")
    except Exception as error:
        # Only a definite OAuth rejection retains a complete candidate for the
        # same authorized request. All source/credential failures discard it.
        if cache and not (isinstance(error, AdminDataError) and error.code == "ACCESS_TOKEN_REQUIRED"
                          and error.status_code == 401 and not error.outcome_unknown):
            cache.discard(key)
        raise
    return prepared.content


async def _read_notion_analysis_input(facade, expected_version, expected_connector_id):
    connector = await asyncio.to_thread(facade.get_connector)
    if expected_connector_id is None or str(connector["id"]) != expected_connector_id:
        raise AdminDataError("NOTION_CONNECTOR_CHANGED", 409)
    before = await asyncio.to_thread(facade._credential_identity)
    snapshot = await asyncio.to_thread(facade.get_current_snapshot)
    _validate_mounted_scope(connector, snapshot)
    records = _records(snapshot)
    version = snapshot["metadata"]["snapshot_version"]
    if expected_version is None or expected_version != version:
        raise AdminDataError("NOTION_SNAPSHOT_CHANGED", 409)
    client = NotionOperationClient(facade.credential_store.effective_home(facade.user_id))
    pages, empty = [], []
    for page_id, item in records.items():
        result = await client.get_page_markdown(page_id)
        if not result.success:
            raise AdminDataError("NOTION_ANALYSIS_READ_FAILED", 502)
        markdown = str((result.data or {}).get("markdown") or "")
        if not markdown.strip():
            empty.append(page_id)
            continue
        pages.append(ReflectionNotionPageDTO(page_id=page_id, title=str(item.get("title") or ""),
            url=safe_url(item.get("url")), markdown=markdown,
            content_sha256=hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
            read_at=datetime.now(timezone.utc).isoformat()))
    after = await asyncio.to_thread(facade._credential_identity)
    if before != after:
        raise NotionSnapshotNotReadyError("Notion analysis scope changed. Refresh and retry.")
    return _PreparedNotionSource(
        ReflectionNotionInputDTO(connector_id=str(connector["id"]), snapshot_version=version, pages=pages, empty_page_ids=empty),
        facade._read_context(connector), snapshot["metadata"], before,
    )
