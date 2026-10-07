# [Sync] 2026-10-07: cache opaque accepted versions only, validate metadata-only full identity and recover legacy current candidates conservatively.
# [Input] Actor-scoped Notion agentdata roots, canonical connector snapshots, and validated thread workspaces.
# [Output] Atomic user-level lightweight-index persistence and per-turn `.notion/` projection without remote I/O.
# [Pos] canonical snapshot delivery boundary in backend/notion
# [Sync] 2026-08-28: move the Runtime snapshot source to actor agentdata and keep Chat turns projection-only.
# [Sync] 2026-08-28: reject new snapshots that contain page bodies; live text
#                    is owned exclusively by the Runtime Read hook.
# [Sync] 2026-08-29: intersect LKG projections with current source selection and
#                    exclude private connector configuration from thread files.

"""Actor-scoped canonical Notion snapshot storage.

The connector synchronizer is the only writer. Agent turns only read the
current immutable payload and project its public content into one validated
thread workspace.
"""
from __future__ import annotations

import json
import hashlib
import os
import re
import stat
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping
from datetime import datetime

from services.admin_data.notion_connector_data import NotionLightSnapshotDTO

from .credentials import (
    NotionCredentialStore,
    _private_directory,
    _read_private_file,
    _remove_private_tree,
    _write_private_file,
)
from .errors import NotionCredentialError, NotionSnapshotNotReadyError
from .sync import filter_snapshot_for_connector, materialize_workspace_snapshot

NOTION_CURRENT_SNAPSHOT_FILENAME = "current.json"
NOTION_THREAD_SNAPSHOT_DIRNAME = ".notion"
_CONNECTOR_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
_DEFAULT_MAX_SNAPSHOT_BYTES = 128 * 1024 * 1024


def _positive_snapshot_limit() -> int:
    raw = os.environ.get("INK_NOTION_MAX_SNAPSHOT_BYTES", "").strip()
    if not raw:
        return _DEFAULT_MAX_SNAPSHOT_BYTES
    try:
        parsed = int(raw)
    except ValueError:
        return _DEFAULT_MAX_SNAPSHOT_BYTES
    return parsed if 1024 <= parsed <= 512 * 1024 * 1024 else _DEFAULT_MAX_SNAPSHOT_BYTES


def _connector_key(connector_id: str) -> str:
    value = str(connector_id).strip()
    if not _CONNECTOR_ID_RE.fullmatch(value):
        raise NotionSnapshotNotReadyError("Notion connector identity is invalid.")
    return value


def _snapshot_payload(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(snapshot)
    metadata = payload.get("metadata")
    if not isinstance(metadata, Mapping):
        raise NotionSnapshotNotReadyError("Snapshot metadata is missing.")
    required = (
        "resource_connector_id",
        "snapshot_version",
        "source_revision",
        "sync_cursor",
        "fetched_at",
    )
    if any(not str(metadata.get(field) or "").strip() for field in required):
        raise NotionSnapshotNotReadyError("Snapshot identity is incomplete.")
    return payload


def _harden_public_projection(root: Path) -> None:
    for path in [root, *root.rglob("*")]:
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode):
            raise NotionCredentialError("Notion snapshot projection is not safe.")
        if stat.S_ISDIR(info.st_mode):
            os.chmod(path, 0o700, follow_symlinks=False)
        elif stat.S_ISREG(info.st_mode):
            os.chmod(path, 0o600, follow_symlinks=False)
        else:
            raise NotionCredentialError("Notion snapshot projection contains an invalid entry.")


@dataclass(frozen=True)
class NotionSnapshotProjection:
    available: bool
    thread_snapshot_root: Path | None = field(default=None, repr=False)
    snapshot_version: str | None = None


class NotionSnapshotStore:
    """Cache Admin-accepted actor metadata and project its current-scope subset."""

    def __init__(
        self,
        credential_store: NotionCredentialStore | None = None,
        *,
        max_snapshot_bytes: int | None = None,
    ) -> None:
        self.credential_store = credential_store or NotionCredentialStore()
        self.max_snapshot_bytes = max_snapshot_bytes or _positive_snapshot_limit()

    def _connector_root(self, actor_id: str | int, connector_id: str) -> Path:
        paths = self.credential_store.user_paths(actor_id)
        return _private_directory(paths.snapshot_root / _connector_key(connector_id))

    @staticmethod
    def accepted_payload(snapshot: Mapping[str, Any], connector: Mapping[str, Any]) -> dict[str, Any]:
        """Strict metadata-only shape and full Admin-accepted identity, not local recency."""
        try:
            candidate = dict(snapshot)
            # Existing metadata indexes may predate upstream time fields. Null retains partial
            # semantics; strict models still reject unknown body/config fields at every depth.
            def page_times(page):
                return {"created_time": None, "last_edited_time": None, **dict(page)}
            if isinstance(candidate.get("index"), list):
                candidate["index"] = [page_times(page) for page in candidate["index"]]
            if isinstance(candidate.get("database_pages"), Mapping):
                candidate["database_pages"] = {key: [page_times(page) for page in pages]
                    for key, pages in candidate["database_pages"].items()}
            payload = NotionLightSnapshotDTO.model_validate(candidate).model_dump(mode="json")
            metadata = payload["metadata"]
            expected = {"resource_connector_id": connector.get("id"), "workspace_id": connector.get("id"),
                "snapshot_version": connector.get("current_snapshot_version"),
                "source_revision": connector.get("current_source_revision"),
                "sync_cursor": connector.get("current_sync_cursor")}
            if any(metadata[key] != value for key, value in expected.items()):
                raise ValueError("Snapshot is not the accepted identity")
            if datetime.fromisoformat(metadata["fetched_at"].replace("Z", "+00:00")) != datetime.fromisoformat(
                str(connector.get("last_synced_at")).replace("Z", "+00:00")):
                raise ValueError("Snapshot fetched time is not the accepted time")
            return payload
        except (ValueError, TypeError, KeyError) as exc:
            raise NotionSnapshotNotReadyError("Accepted Notion snapshot is invalid.") from exc

    def _version_path(self, actor_id, connector_id, version: str) -> Path:
        # EntityId is opaque and may contain separators; never interpolate it into a path.
        key = hashlib.sha256(version.encode("utf-8")).hexdigest()
        return self._connector_root(actor_id, connector_id) / f"snapshot-{key}.json"

    def cache_accepted(self, actor_id, connector: Mapping[str, Any], snapshot: Mapping[str, Any]) -> dict:
        payload = self.accepted_payload(snapshot, connector)
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
        if len(encoded) > self.max_snapshot_bytes:
            raise NotionSnapshotNotReadyError("Notion snapshot exceeds the configured size limit.")
        _write_private_file(self._version_path(actor_id, str(connector["id"]), payload["metadata"]["snapshot_version"]), encoded)
        return payload

    def load_accepted(self, actor_id, connector: Mapping[str, Any]) -> dict | None:
        version = connector.get("current_snapshot_version")
        if not isinstance(version, str) or not version:
            return None
        root = self._connector_root(actor_id, str(connector["id"]))
        for path in (self._version_path(actor_id, str(connector["id"]), version), root / NOTION_CURRENT_SNAPSHOT_FILENAME):
            try:
                raw = _read_private_file(path, max_bytes=self.max_snapshot_bytes)
                if raw is not None:
                    return self.accepted_payload(json.loads(raw.decode("utf-8")), connector)
            except (ValueError, TypeError, UnicodeError, NotionSnapshotNotReadyError):
                # A stale/corrupt cache is not authority; the facade can recover via Admin reads.
                continue
        return None

    def publish_current(
        self,
        actor_id: str | int,
        connector_id: str,
        snapshot: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Atomically replace one actor connector's last-known-good snapshot."""

        payload = _snapshot_payload(snapshot)
        metadata = dict(payload["metadata"])
        if str(metadata.get("resource_connector_id")) != _connector_key(connector_id):
            raise NotionSnapshotNotReadyError("Snapshot connector identity does not match.")
        if payload.get("pages"):
            raise NotionSnapshotNotReadyError(
                "Notion snapshots may contain only the lightweight page index."
            )
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        if len(encoded) > self.max_snapshot_bytes:
            raise NotionSnapshotNotReadyError("Notion snapshot exceeds the configured size limit.")
        root = self._connector_root(actor_id, connector_id)
        _write_private_file(root / NOTION_CURRENT_SNAPSHOT_FILENAME, encoded)
        return payload

    def load_current(
        self,
        actor_id: str | int,
        connector_id: str,
    ) -> dict[str, Any] | None:
        root = self._connector_root(actor_id, connector_id)
        raw = _read_private_file(
            root / NOTION_CURRENT_SNAPSHOT_FILENAME,
            max_bytes=self.max_snapshot_bytes,
        )
        if raw is None:
            return None
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise NotionSnapshotNotReadyError("Stored Notion snapshot is invalid.") from exc
        if not isinstance(parsed, Mapping):
            raise NotionSnapshotNotReadyError("Stored Notion snapshot has an invalid shape.")
        payload = _snapshot_payload(parsed)
        if str(dict(payload["metadata"]).get("resource_connector_id")) != _connector_key(connector_id):
            raise NotionSnapshotNotReadyError("Stored Notion snapshot belongs to another connector.")
        return payload

    def clear_connector(self, actor_id: str | int, connector_id: str) -> None:
        paths = self.credential_store.user_paths(actor_id)
        target = paths.snapshot_root / _connector_key(connector_id)
        _remove_private_tree(target, parent=paths.snapshot_root)

    def clear_thread(self, workspace: Path) -> None:
        resolved = self.credential_store.validate_thread_workspace(workspace)
        _remove_private_tree(
            resolved / NOTION_THREAD_SNAPSHOT_DIRNAME,
            parent=resolved,
        )

    def project_thread(
        self,
        actor_id: str | int,
        connector: Mapping[str, Any],
        workspace: Path,
        *, snapshot: Mapping[str, Any] | None = None,
    ) -> NotionSnapshotProjection:
        """Project current agentdata content without querying PostgreSQL or Notion."""

        resolved = self.credential_store.validate_thread_workspace(workspace)
        connector_id = _connector_key(str(connector.get("id") or ""))
        snapshot = self.accepted_payload(snapshot, connector) if snapshot is not None else self.load_accepted(actor_id, connector)
        projected_snapshot = (
            filter_snapshot_for_connector(snapshot, connector) if snapshot else None
        )
        target = resolved / NOTION_THREAD_SNAPSHOT_DIRNAME
        staging_parent = Path(
            tempfile.mkdtemp(prefix=".notion-snapshot.", dir=str(resolved))
        )
        os.chmod(staging_parent, 0o700, follow_symlinks=False)
        try:
            materialize_workspace_snapshot(
                staging_parent,
                connector=connector,
                snapshot=projected_snapshot,
            )
            staging = staging_parent / NOTION_THREAD_SNAPSHOT_DIRNAME
            _harden_public_projection(staging)
            _remove_private_tree(target, parent=resolved)
            os.replace(staging, target)
            metadata = (
                dict(projected_snapshot.get("metadata") or {})
                if projected_snapshot
                else {}
            )
            available = bool(
                projected_snapshot
                and (
                    projected_snapshot.get("index")
                    or projected_snapshot.get("databases")
                )
            )
            return NotionSnapshotProjection(
                available=available,
                thread_snapshot_root=target,
                snapshot_version=(
                    (str(metadata.get("snapshot_version") or "") or None)
                    if available
                    else None
                ),
            )
        finally:
            if staging_parent.exists():
                _remove_private_tree(staging_parent, parent=resolved)


__all__ = [
    "NOTION_CURRENT_SNAPSHOT_FILENAME",
    "NOTION_THREAD_SNAPSHOT_DIRNAME",
    "NotionSnapshotProjection",
    "NotionSnapshotStore",
]
