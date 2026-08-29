# [Input] Actor-scoped Notion agentdata roots, canonical connector snapshots, and validated thread workspaces.
# [Output] Atomic user-level lightweight-index persistence and per-turn `.notion/` projection without remote I/O.
# [Pos] canonical snapshot delivery boundary in backend/notion
# [Sync] 2026-08-28: move the Runtime snapshot source to actor agentdata and keep Chat turns projection-only.
# [Sync] 2026-08-28: reject new snapshots that contain page bodies; live text
#                    is owned exclusively by the Runtime Read hook.

"""Actor-scoped canonical Notion snapshot storage.

The connector synchronizer is the only writer. Agent turns only read the
current immutable payload and project its public content into one validated
thread workspace.
"""
from __future__ import annotations

import json
import os
import re
import stat
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from .credentials import (
    NotionCredentialStore,
    _private_directory,
    _read_private_file,
    _remove_private_tree,
    _write_private_file,
)
from .errors import NotionCredentialError, NotionSnapshotNotReadyError
from .sync import materialize_workspace_snapshot

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
    """Own the current actor snapshot and its thread-local public projection."""

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
    ) -> NotionSnapshotProjection:
        """Project current agentdata content without querying PostgreSQL or Notion."""

        resolved = self.credential_store.validate_thread_workspace(workspace)
        connector_id = _connector_key(str(connector.get("id") or ""))
        snapshot = self.load_current(actor_id, connector_id)
        target = resolved / NOTION_THREAD_SNAPSHOT_DIRNAME
        staging_parent = Path(
            tempfile.mkdtemp(prefix=".notion-snapshot.", dir=str(resolved))
        )
        os.chmod(staging_parent, 0o700, follow_symlinks=False)
        try:
            materialize_workspace_snapshot(
                staging_parent,
                connector=connector,
                snapshot=snapshot,
            )
            staging = staging_parent / NOTION_THREAD_SNAPSHOT_DIRNAME
            _harden_public_projection(staging)
            _remove_private_tree(target, parent=resolved)
            os.replace(staging, target)
            metadata = dict(snapshot.get("metadata") or {}) if snapshot else {}
            return NotionSnapshotProjection(
                available=snapshot is not None,
                thread_snapshot_root=target,
                snapshot_version=str(metadata.get("snapshot_version") or "") or None,
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
