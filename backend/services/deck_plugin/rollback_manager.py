"""Explicit, future-only rollback orchestration for Deck Plugin installations."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
import inspect
import re
import sqlite3
from typing import Any
import uuid

try:
    from backend.models.deck_plugin import (
        DeckPluginManifestV1,
        DeckRuntimePluginLock,
        InstallationStatus,
    )
    from backend.services.deck_plugin.installation_service import (
        InstallationService,
        InstallationServiceError,
    )
except ModuleNotFoundError:  # Support running with ``backend`` on PYTHONPATH.
    from models.deck_plugin import (
        DeckPluginManifestV1,
        DeckRuntimePluginLock,
        InstallationStatus,
    )
    from services.deck_plugin.installation_service import (
        InstallationService,
        InstallationServiceError,
    )


ROLLBACK_INSTALLATION_NOT_FOUND = "DECK_PLUGIN_INSTALLATION_NOT_FOUND"
ROLLBACK_TARGET_UNAVAILABLE = "DECK_PLUGIN_ROLLBACK_TARGET_UNAVAILABLE"
ROLLBACK_DIGEST_INVALID = "DECK_PLUGIN_ROLLBACK_DIGEST_INVALID"
ROLLBACK_INCOMPATIBLE = "DECK_PLUGIN_ROLLBACK_INCOMPATIBLE"
ROLLBACK_AUDIT_FAILED = "DECK_PLUGIN_ROLLBACK_AUDIT_FAILED"

_DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class RollbackAuditEvent:
    audit_event_id: str
    installation_id: str
    actor: str
    from_version: str
    target_version: str
    occurred_at: datetime
    historical_runs_modified: bool = False
    existing_bindings_modified: bool = False


@dataclass(frozen=True)
class RollbackResult:
    installation_id: str
    previous_default_version: str
    target_version: str
    status: InstallationStatus
    audit_event_id: str
    affects_future_resolution_only: bool = True


class RollbackManagerError(ValueError):
    def __init__(self, code: str, summary: str) -> None:
        super().__init__(summary)
        self.code = code
        self.summary = summary


CompatibilityChecker = Callable[
    [DeckPluginManifestV1, DeckRuntimePluginLock], bool | Awaitable[bool]
]
DigestVerifier = Callable[[str], bool | Awaitable[bool]]
AuditAppender = Callable[[RollbackAuditEvent], None | Awaitable[None]]


async def _resolve(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


class RollbackManager:
    """Validate a named old release, then switch only ``default_version``."""

    def __init__(
        self,
        db: sqlite3.Connection,
        installation_service: InstallationService,
        *,
        compatibility_checker: CompatibilityChecker,
        digest_verifier: DigestVerifier,
        audit_appender: AuditAppender,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.db = db
        self.db.row_factory = sqlite3.Row
        self._installation_service = installation_service
        self._compatibility_checker = compatibility_checker
        self._digest_verifier = digest_verifier
        self._audit_appender = audit_appender
        self._clock = clock or (lambda: datetime.now(UTC))

    async def rollback_installation(
        self,
        installation_id: str,
        target_version: str,
        actor: str,
    ) -> RollbackResult:
        if not actor.strip():
            raise RollbackManagerError(ROLLBACK_AUDIT_FAILED, "actor is required")

        row = self.db.execute(
            "SELECT * FROM deck_plugin_installations WHERE id = ?",
            (installation_id,),
        ).fetchone()
        if row is None:
            raise RollbackManagerError(
                ROLLBACK_INSTALLATION_NOT_FOUND, "installation was not found"
            )
        if row["status"] != InstallationStatus.READY.value:
            raise RollbackManagerError(
                ROLLBACK_TARGET_UNAVAILABLE,
                "rollback requires a ready installation",
            )
        previous = row["default_version"]
        if not previous or previous == target_version:
            raise RollbackManagerError(
                ROLLBACK_TARGET_UNAVAILABLE,
                "rollback target must differ from the current default version",
            )

        release = self.db.execute(
            """
            SELECT status, manifest_json, manifest_hash
            FROM deck_plugin_releases
            WHERE deck_plugin_id = ? AND deck_plugin_version = ?
            """,
            (row["deck_plugin_id"], target_version),
        ).fetchone()
        lock_row = self.db.execute(
            """
            SELECT deck_plugin_manifest_hash, lock_json
            FROM deck_runtime_plugin_locks
            WHERE deck_plugin_id = ? AND deck_plugin_version = ?
            """,
            (row["deck_plugin_id"], target_version),
        ).fetchone()
        if (
            release is None
            or release["status"] not in {"published", "deprecated"}
            or lock_row is None
            or lock_row["deck_plugin_manifest_hash"] != release["manifest_hash"]
        ):
            raise RollbackManagerError(
                ROLLBACK_TARGET_UNAVAILABLE,
                "rollback target is not an available release with a matching lock",
            )

        try:
            manifest = DeckPluginManifestV1.model_validate_json(release["manifest_json"])
            runtime_lock = DeckRuntimePluginLock.model_validate_json(lock_row["lock_json"])
        except Exception as exc:
            raise RollbackManagerError(
                ROLLBACK_TARGET_UNAVAILABLE,
                "rollback release or runtime lock is invalid",
            ) from exc

        digests = [entry.artifact_digest for entry in runtime_lock.claude_code_plugins]
        digests_valid = bool(digests)
        for digest in digests:
            if not _DIGEST_PATTERN.fullmatch(digest) or not await _resolve(
                self._digest_verifier(digest)
            ):
                digests_valid = False
                break
        if not digests_valid:
            raise RollbackManagerError(
                ROLLBACK_DIGEST_INVALID,
                "every rollback artifact digest must be present and verified",
            )
        if not await _resolve(self._compatibility_checker(manifest, runtime_lock)):
            raise RollbackManagerError(
                ROLLBACK_INCOMPATIBLE,
                "rollback target failed the current host/runtime compatibility gate",
            )

        bindings_before = self._table_projection(
            "deck_plugin_bindings", "deck_plugin_id", row["deck_plugin_id"]
        )
        runs_before = self._table_projection(
            "workflow_runs", "deck_plugin_id", row["deck_plugin_id"]
        )
        try:
            rolled_back = await self._installation_service.rollback(
                installation_id, target_version
            )
        except InstallationServiceError as exc:
            raise RollbackManagerError(exc.code, exc.summary) from exc

        if bindings_before != self._table_projection(
            "deck_plugin_bindings", "deck_plugin_id", row["deck_plugin_id"]
        ) or runs_before != self._table_projection(
            "workflow_runs", "deck_plugin_id", row["deck_plugin_id"]
        ):
            raise RollbackManagerError(
                ROLLBACK_AUDIT_FAILED,
                "rollback unexpectedly modified an existing binding or historical run",
            )

        event = RollbackAuditEvent(
            audit_event_id=f"rae_{uuid.uuid4().hex}",
            installation_id=installation_id,
            actor=actor,
            from_version=previous,
            target_version=target_version,
            occurred_at=self._clock(),
        )
        try:
            await _resolve(self._audit_appender(event))
        except Exception as exc:
            raise RollbackManagerError(
                ROLLBACK_AUDIT_FAILED,
                "the rollback succeeded but its append-only audit write failed",
            ) from exc
        return RollbackResult(
            installation_id=installation_id,
            previous_default_version=previous,
            target_version=rolled_back.default_version or target_version,
            status=rolled_back.status,
            audit_event_id=event.audit_event_id,
        )

    def _table_projection(
        self, table: str, key_column: str, key_value: str
    ) -> tuple[tuple[Any, ...], ...] | None:
        exists = self.db.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table,),
        ).fetchone()
        if exists is None:
            return None
        columns = tuple(
            row[1] for row in self.db.execute(f"PRAGMA table_info({table})")
        )
        rows = self.db.execute(
            f"SELECT * FROM {table} WHERE {key_column} = ? ORDER BY rowid",
            (key_value,),
        ).fetchall()
        return tuple(tuple(row[column] for column in columns) for row in rows)
