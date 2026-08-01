"""SQLite-backed Deck Plugin Installation lifecycle orchestration.

This is a non-production control-plane foundation. Release compatibility and
runtime materialization are injected checks so this module does not pre-empt
the later compatibility or ClaudeAgent runtime tasks.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
import inspect
import json
import re
import sqlite3
from typing import Any, Literal
import uuid

from pydantic import BaseModel, ConfigDict, Field

try:
    from backend.models.deck_plugin import (
        DeckPluginInstallation,
        DeckPluginManifestV1,
        DeckRuntimePluginLock,
        InstallationStatus,
        SEMVER_PATTERN,
    )
except ModuleNotFoundError:  # Support the backend directory on PYTHONPATH.
    from models.deck_plugin import (
        DeckPluginInstallation,
        DeckPluginManifestV1,
        DeckRuntimePluginLock,
        InstallationStatus,
        SEMVER_PATTERN,
    )


DECK_PLUGIN_INSTALLATION_NOT_FOUND = "DECK_PLUGIN_INSTALLATION_NOT_FOUND"
DECK_PLUGIN_INSTALLATION_CONFLICT = "DECK_PLUGIN_INSTALLATION_CONFLICT"
DECK_PLUGIN_INVALID_TRANSITION = "DECK_PLUGIN_INVALID_TRANSITION"
DECK_PLUGIN_RELEASE_UNAVAILABLE = "DECK_PLUGIN_RELEASE_UNAVAILABLE"
DECK_PLUGIN_RUNTIME_NOT_READY = "DECK_PLUGIN_RUNTIME_NOT_READY"
DECK_PLUGIN_UPGRADE_APPROVAL_REQUIRED = "DECK_PLUGIN_UPGRADE_APPROVAL_REQUIRED"
DECK_PLUGIN_ROLLBACK_BLOCKED = "DECK_PLUGIN_ROLLBACK_BLOCKED"
DECK_PLUGIN_PURGE_RETENTION_BLOCKED = "DECK_PLUGIN_PURGE_RETENTION_BLOCKED"
DECK_PLUGIN_CONCURRENT_MODIFICATION = "DECK_PLUGIN_CONCURRENT_MODIFICATION"


ALLOWED_INSTALLATION_TRANSITIONS = {
    InstallationStatus.INSTALLING: {
        InstallationStatus.READY,
        InstallationStatus.ERROR,
        InstallationStatus.UNINSTALLED,
    },
    InstallationStatus.READY: {
        InstallationStatus.DISABLED,
        InstallationStatus.UPGRADE_PENDING,
        InstallationStatus.UNINSTALLED,
    },
    InstallationStatus.DISABLED: {
        InstallationStatus.READY,
        InstallationStatus.UNINSTALLED,
    },
    InstallationStatus.ERROR: {
        InstallationStatus.INSTALLING,
        InstallationStatus.UNINSTALLED,
    },
    InstallationStatus.UPGRADE_PENDING: {
        InstallationStatus.INSTALLING,
        InstallationStatus.UNINSTALLED,
    },
    InstallationStatus.UNINSTALLED: set(),
}


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Scope(_StrictModel):
    scope_type: Literal["instance", "workspace"]
    scope_id: str = Field(min_length=1)


class CapabilityDiff(_StrictModel):
    added: list[str] = Field(default_factory=list)
    removed: list[str] = Field(default_factory=list)


class RuntimePreparation(_StrictModel):
    runtime_readiness: str
    lock_materialized: bool
    load_smoke_passed: bool
    error_code: str | None = None
    error_summary: str | None = None


class InstallationOperationResult(_StrictModel):
    operation_id: str = Field(pattern=r"^op_[0-9a-f]{32}$")
    deck_plugin_installation_id: str = Field(pattern=r"^dpi_[0-9a-f]{32}$")
    deck_plugin_id: str
    target_version: str
    status: InstallationStatus
    capability_diff: CapabilityDiff
    runtime_readiness: str


class InstallResult(InstallationOperationResult):
    pass


class UpgradeResult(InstallationOperationResult):
    pass


class InstallationServiceError(ValueError):
    """Structured lifecycle failure suitable for an API error response."""

    def __init__(
        self,
        code: str,
        summary: str,
        *,
        installation_id: str | None = None,
        operation_id: str | None = None,
        retryable: bool = False,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(summary)
        self.code = code
        self.summary = summary
        self.installation_id = installation_id
        self.operation_id = operation_id
        self.retryable = retryable
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "summary": self.summary,
                "retryable": self.retryable,
                "deck_plugin_installation_id": self.installation_id,
                "operation_id": self.operation_id,
                "details": self.details,
            }
        }


@dataclass(frozen=True)
class _ReleaseSnapshot:
    deck_plugin_id: str
    version: str
    capabilities: tuple[str, ...]
    manifest_hash: str
    runtime_lock: DeckRuntimePluginLock


RuntimePreparer = Callable[
    [str, str, DeckRuntimePluginLock],
    RuntimePreparation | Awaitable[RuntimePreparation],
]
CompatibilityChecker = Callable[
    [str, str],
    bool | Awaitable[bool],
]
RetentionChecker = Callable[
    [DeckPluginInstallation],
    bool | Awaitable[bool],
]


def assert_installation_transition(
    current: InstallationStatus,
    target: InstallationStatus,
) -> None:
    if target not in ALLOWED_INSTALLATION_TRANSITIONS[current]:
        raise InstallationServiceError(
            DECK_PLUGIN_INVALID_TRANSITION,
            f"invalid Deck Plugin installation transition: {current.value} -> {target.value}",
        )


async def _resolve(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


class InstallationService:
    def __init__(
        self,
        db: sqlite3.Connection,
        *,
        runtime_preparer: RuntimePreparer | None = None,
        compatibility_checker: CompatibilityChecker | None = None,
        retention_checker: RetentionChecker | None = None,
    ) -> None:
        self.db = db
        self.db.row_factory = sqlite3.Row
        self._runtime_preparer = runtime_preparer or self._baseline_runtime_preparer
        self._compatibility_checker = compatibility_checker or (lambda _p, _v: True)
        self._retention_checker = retention_checker or (lambda _installation: False)
        self._write_lock = asyncio.Lock()
        self._inflight_installations: set[str] = set()

    async def install(
        self,
        deck_plugin_id: str,
        version: str,
        scope: Scope,
        *,
        source_policy_id: str = "default",
    ) -> InstallResult:
        if not source_policy_id.strip():
            raise InstallationServiceError(
                DECK_PLUGIN_RELEASE_UNAVAILABLE,
                "source_policy_id is required",
            )
        snapshot = await self._validated_release(deck_plugin_id, version)
        operation_id = self._operation_id()
        installation_id = f"dpi_{uuid.uuid4().hex}"
        capability_diff = CapabilityDiff(added=list(snapshot.capabilities), removed=[])

        async with self._write_lock:
            existing = self.db.execute(
                """
                SELECT id FROM deck_plugin_installations
                WHERE scope_type = ? AND scope_id = ? AND deck_plugin_id = ?
                """,
                (scope.scope_type, scope.scope_id, deck_plugin_id),
            ).fetchone()
            if existing is not None:
                raise InstallationServiceError(
                    DECK_PLUGIN_INSTALLATION_CONFLICT,
                    "an installation already exists for this scope and Deck Plugin",
                    installation_id=existing["id"],
                    operation_id=operation_id,
                    retryable=False,
                )
            try:
                with self.db:
                    self.db.execute(
                        """
                        INSERT INTO deck_plugin_installations (
                            id, scope_type, scope_id, deck_plugin_id,
                            installed_versions_json, default_version, status,
                            approved_capabilities_json, source_policy_id,
                            pending_version, pending_capabilities_json
                        ) VALUES (?, ?, ?, ?, '[]', NULL, ?, '[]', ?, ?, ?)
                        """,
                        (
                            installation_id,
                            scope.scope_type,
                            scope.scope_id,
                            deck_plugin_id,
                            InstallationStatus.INSTALLING.value,
                            source_policy_id,
                            version,
                            json.dumps(list(snapshot.capabilities)),
                        ),
                    )
            except sqlite3.IntegrityError as exc:
                raise InstallationServiceError(
                    DECK_PLUGIN_INSTALLATION_CONFLICT,
                    "concurrent installation lost the unique scope conflict",
                    operation_id=operation_id,
                    retryable=False,
                ) from exc

        return InstallResult(
            operation_id=operation_id,
            deck_plugin_installation_id=installation_id,
            deck_plugin_id=deck_plugin_id,
            target_version=version,
            status=InstallationStatus.INSTALLING,
            capability_diff=capability_diff,
            runtime_readiness="materializing",
        )

    async def complete_installation(self, installation_id: str) -> InstallResult:
        operation_id = self._operation_id()
        async with self._write_lock:
            row = self._required_row(installation_id)
            self._require_status(row, InstallationStatus.INSTALLING, operation_id)
            target_version = self._required_pending_version(row, operation_id)
            snapshot = await self._validated_release(row["deck_plugin_id"], target_version)
            preparation = await self._prepare(snapshot)
            if not preparation.lock_materialized or not preparation.load_smoke_passed:
                self._record_initial_failure(row, preparation, operation_id)
                raise self._runtime_error(row, preparation, operation_id)

            approved = self._json_list(row["pending_capabilities_json"])
            installed = self._json_list(row["installed_versions_json"])
            if target_version == row["default_version"]:
                raise InstallationServiceError(
                    DECK_PLUGIN_ROLLBACK_BLOCKED,
                    "rollback target must differ from the current default version",
                    installation_id=installation_id,
                    operation_id=operation_id,
                    details={"target_version": target_version},
                )
            if target_version not in installed:
                installed.append(target_version)
            assert_installation_transition(
                InstallationStatus(row["status"]), InstallationStatus.READY
            )
            self._update_row(
                row,
                installed_versions_json=json.dumps(installed),
                default_version=target_version,
                status=InstallationStatus.READY.value,
                approved_capabilities_json=json.dumps(approved),
                pending_version=None,
                pending_capabilities_json=None,
                last_error_code=None,
                last_error_summary=None,
            )
            return InstallResult(
                operation_id=operation_id,
                deck_plugin_installation_id=installation_id,
                deck_plugin_id=row["deck_plugin_id"],
                target_version=target_version,
                status=InstallationStatus.READY,
                capability_diff=CapabilityDiff(added=approved, removed=[]),
                runtime_readiness=preparation.runtime_readiness,
            )

    async def enable(self, installation_id: str) -> DeckPluginInstallation:
        async with self._write_lock:
            row = self._required_row(installation_id)
            assert_installation_transition(
                InstallationStatus(row["status"]), InstallationStatus.READY
            )
            self._update_row(
                row,
                status=InstallationStatus.READY.value,
                last_error_code=None,
                last_error_summary=None,
            )
            return self.get(installation_id)

    async def disable(
        self,
        installation_id: str,
        reason: str,
    ) -> DeckPluginInstallation:
        if not reason.strip():
            raise InstallationServiceError(
                DECK_PLUGIN_INVALID_TRANSITION,
                "disable requires a non-empty audit reason",
                installation_id=installation_id,
            )
        async with self._write_lock:
            row = self._required_row(installation_id)
            assert_installation_transition(
                InstallationStatus(row["status"]), InstallationStatus.DISABLED
            )
            self._update_row(
                row,
                status=InstallationStatus.DISABLED.value,
                last_error_code="DECK_PLUGIN_DISABLED",
                last_error_summary=reason,
            )
            return self.get(installation_id)

    async def retry(self, installation_id: str) -> InstallResult:
        operation_id = self._operation_id()
        async with self._write_lock:
            row = self._required_row(installation_id)
            assert_installation_transition(
                InstallationStatus(row["status"]), InstallationStatus.INSTALLING
            )
            target_version = self._required_pending_version(row, operation_id)
            self._update_row(
                row,
                status=InstallationStatus.INSTALLING.value,
                last_error_code=None,
                last_error_summary=None,
            )
            pending = self._json_list(row["pending_capabilities_json"])
            approved = self._json_list(row["approved_capabilities_json"])
            return InstallResult(
                operation_id=operation_id,
                deck_plugin_installation_id=installation_id,
                deck_plugin_id=row["deck_plugin_id"],
                target_version=target_version,
                status=InstallationStatus.INSTALLING,
                capability_diff=self._capability_diff(approved, pending),
                runtime_readiness="materializing",
            )

    async def upgrade(
        self,
        installation_id: str,
        target_version: str,
    ) -> UpgradeResult:
        self._claim_inflight(installation_id)
        try:
            return await self._upgrade(installation_id, target_version)
        finally:
            self._inflight_installations.discard(installation_id)

    async def _upgrade(
        self,
        installation_id: str,
        target_version: str,
    ) -> UpgradeResult:
        operation_id = self._operation_id()
        async with self._write_lock:
            row = self._required_row(installation_id)
            self._require_status(row, InstallationStatus.READY, operation_id)
            if target_version == row["default_version"]:
                raise InstallationServiceError(
                    DECK_PLUGIN_INSTALLATION_CONFLICT,
                    "target version is already the default version",
                    installation_id=installation_id,
                    operation_id=operation_id,
                )
            snapshot = await self._validated_release(
                row["deck_plugin_id"], target_version
            )
            approved = self._json_list(row["approved_capabilities_json"])
            target_capabilities = list(snapshot.capabilities)
            diff = self._capability_diff(approved, target_capabilities)
            if diff.added:
                assert_installation_transition(
                    InstallationStatus(row["status"]),
                    InstallationStatus.UPGRADE_PENDING,
                )
                self._update_row(
                    row,
                    status=InstallationStatus.UPGRADE_PENDING.value,
                    pending_version=target_version,
                    pending_capabilities_json=json.dumps(target_capabilities),
                    last_error_code=DECK_PLUGIN_UPGRADE_APPROVAL_REQUIRED,
                    last_error_summary="capability expansion requires administrator approval",
                )
                return UpgradeResult(
                    operation_id=operation_id,
                    deck_plugin_installation_id=installation_id,
                    deck_plugin_id=row["deck_plugin_id"],
                    target_version=target_version,
                    status=InstallationStatus.UPGRADE_PENDING,
                    capability_diff=diff,
                    runtime_readiness="pending_approval",
                )

            return await self._switch_version(row, snapshot, diff, operation_id)

    async def approve_upgrade(self, installation_id: str) -> UpgradeResult:
        operation_id = self._operation_id()
        async with self._write_lock:
            row = self._required_row(installation_id)
            self._require_status(row, InstallationStatus.UPGRADE_PENDING, operation_id)
            target_version = self._required_pending_version(row, operation_id)
            snapshot = await self._validated_release(
                row["deck_plugin_id"], target_version
            )
            approved = self._json_list(row["approved_capabilities_json"])
            target_capabilities = self._json_list(row["pending_capabilities_json"])
            diff = self._capability_diff(approved, target_capabilities)
            assert_installation_transition(
                InstallationStatus(row["status"]), InstallationStatus.INSTALLING
            )
            self._update_row(row, status=InstallationStatus.INSTALLING.value)
            row = self._required_row(installation_id)
            return await self._switch_version(row, snapshot, diff, operation_id)

    async def rollback(
        self,
        installation_id: str,
        target_version: str,
    ) -> DeckPluginInstallation:
        operation_id = self._operation_id()
        async with self._write_lock:
            row = self._required_row(installation_id)
            self._require_status(row, InstallationStatus.READY, operation_id)
            installed = self._json_list(row["installed_versions_json"])
            if target_version not in installed:
                raise InstallationServiceError(
                    DECK_PLUGIN_ROLLBACK_BLOCKED,
                    "the explicitly requested compatible release is not installed",
                    installation_id=installation_id,
                    operation_id=operation_id,
                    details={"target_version": target_version},
                )
            snapshot = await self._validated_release(
                row["deck_plugin_id"], target_version
            )
            self._assert_rollback_digests(snapshot, installation_id, operation_id)
            preparation = await self._prepare(snapshot)
            if not preparation.lock_materialized or not preparation.load_smoke_passed:
                self._record_non_destructive_failure(row, preparation)
                raise self._runtime_error(row, preparation, operation_id, rollback=True)
            self._update_row(
                row,
                default_version=target_version,
                last_error_code=None,
                last_error_summary=None,
            )
            return self.get(installation_id)

    async def uninstall(
        self,
        installation_id: str,
        force: bool = False,
    ) -> DeckPluginInstallation:
        async with self._write_lock:
            row = self._required_row(installation_id)
            installation = self._installation_from_row(row)
            if installation.status is InstallationStatus.UNINSTALLED:
                raise InstallationServiceError(
                    DECK_PLUGIN_INVALID_TRANSITION,
                    "uninstalled is terminal",
                    installation_id=installation_id,
                )
            if force and not await _resolve(self._retention_checker(installation)):
                raise InstallationServiceError(
                    DECK_PLUGIN_PURGE_RETENTION_BLOCKED,
                    "force purge requires proof that no audit or retention obligation remains",
                    installation_id=installation_id,
                )
            assert_installation_transition(
                installation.status, InstallationStatus.UNINSTALLED
            )
            self._update_row(
                row,
                status=InstallationStatus.UNINSTALLED.value,
                pending_version=None,
                pending_capabilities_json=None,
            )
            removed = self.get(installation_id)
            if force:
                with self.db:
                    self.db.execute(
                        "DELETE FROM deck_plugin_installations WHERE id = ?",
                        (installation_id,),
                    )
            return removed

    def get(self, installation_id: str) -> DeckPluginInstallation:
        return self._installation_from_row(self._required_row(installation_id))

    def _claim_inflight(self, installation_id: str) -> None:
        if installation_id in self._inflight_installations:
            raise InstallationServiceError(
                DECK_PLUGIN_CONCURRENT_MODIFICATION,
                "another lifecycle operation is already in flight for this installation",
                installation_id=installation_id,
                retryable=True,
            )
        self._inflight_installations.add(installation_id)

    async def _validated_release(
        self,
        deck_plugin_id: str,
        version: str,
    ) -> _ReleaseSnapshot:
        if not SEMVER_PATTERN.fullmatch(version):
            raise InstallationServiceError(
                DECK_PLUGIN_RELEASE_UNAVAILABLE,
                "an exact SemVer target version is required",
                details={"target_version": version},
            )
        row = self.db.execute(
            """
            SELECT manifest_json, manifest_hash, status
            FROM deck_plugin_releases
            WHERE deck_plugin_id = ? AND deck_plugin_version = ?
            """,
            (deck_plugin_id, version),
        ).fetchone()
        if row is None or row["status"] not in {"published", "deprecated"}:
            raise InstallationServiceError(
                DECK_PLUGIN_RELEASE_UNAVAILABLE,
                "the requested release is not available for installation",
                details={"deck_plugin_id": deck_plugin_id, "target_version": version},
            )
        lock_row = self.db.execute(
            """
            SELECT deck_plugin_manifest_hash, lock_json
            FROM deck_runtime_plugin_locks
            WHERE deck_plugin_id = ? AND deck_plugin_version = ?
            """,
            (deck_plugin_id, version),
        ).fetchone()
        if lock_row is None or lock_row["deck_plugin_manifest_hash"] != row["manifest_hash"]:
            raise InstallationServiceError(
                DECK_PLUGIN_RUNTIME_NOT_READY,
                "the release has no matching immutable runtime lock",
                details={"deck_plugin_id": deck_plugin_id, "target_version": version},
            )
        try:
            manifest = DeckPluginManifestV1.model_validate_json(row["manifest_json"])
            runtime_lock = DeckRuntimePluginLock.model_validate_json(lock_row["lock_json"])
        except Exception as exc:
            raise InstallationServiceError(
                DECK_PLUGIN_RELEASE_UNAVAILABLE,
                "the persisted release or runtime lock is invalid",
                details={"target_version": version},
            ) from exc
        if (
            manifest.deck_plugin_id != deck_plugin_id
            or manifest.deck_plugin_version != version
            or runtime_lock.deck_plugin_id != deck_plugin_id
            or runtime_lock.deck_plugin_version != version
        ):
            raise InstallationServiceError(
                DECK_PLUGIN_RELEASE_UNAVAILABLE,
                "release identity does not match its persisted installation target",
                details={"target_version": version},
            )
        compatible = await _resolve(self._compatibility_checker(deck_plugin_id, version))
        if not compatible:
            raise InstallationServiceError(
                DECK_PLUGIN_RELEASE_UNAVAILABLE,
                "the requested release failed the injected compatibility gate",
                details={"target_version": version},
            )
        return _ReleaseSnapshot(
            deck_plugin_id=deck_plugin_id,
            version=version,
            capabilities=tuple(manifest.capabilities),
            manifest_hash=row["manifest_hash"],
            runtime_lock=runtime_lock,
        )

    async def _switch_version(
        self,
        row: sqlite3.Row,
        snapshot: _ReleaseSnapshot,
        diff: CapabilityDiff,
        operation_id: str,
    ) -> UpgradeResult:
        preparation = await self._prepare(snapshot)
        if not preparation.lock_materialized or not preparation.load_smoke_passed:
            self._record_non_destructive_failure(row, preparation)
            raise self._runtime_error(row, preparation, operation_id)
        installed = self._json_list(row["installed_versions_json"])
        if snapshot.version not in installed:
            installed.append(snapshot.version)
        self._update_row(
            row,
            installed_versions_json=json.dumps(installed),
            default_version=snapshot.version,
            status=InstallationStatus.READY.value,
            approved_capabilities_json=json.dumps(list(snapshot.capabilities)),
            pending_version=None,
            pending_capabilities_json=None,
            last_error_code=None,
            last_error_summary=None,
        )
        return UpgradeResult(
            operation_id=operation_id,
            deck_plugin_installation_id=row["id"],
            deck_plugin_id=row["deck_plugin_id"],
            target_version=snapshot.version,
            status=InstallationStatus.READY,
            capability_diff=diff,
            runtime_readiness=preparation.runtime_readiness,
        )

    async def _prepare(self, snapshot: _ReleaseSnapshot) -> RuntimePreparation:
        result = await _resolve(
            self._runtime_preparer(
                snapshot.deck_plugin_id,
                snapshot.version,
                snapshot.runtime_lock,
            )
        )
        if not isinstance(result, RuntimePreparation):
            result = RuntimePreparation.model_validate(result)
        return result

    @staticmethod
    def _baseline_runtime_preparer(
        _deck_plugin_id: str,
        _version: str,
        _runtime_lock: DeckRuntimePluginLock,
    ) -> RuntimePreparation:
        return RuntimePreparation(
            runtime_readiness="runtime_adapter_required",
            lock_materialized=False,
            load_smoke_passed=False,
            error_code=DECK_PLUGIN_RUNTIME_NOT_READY,
            error_summary=(
                "a runtime materialization and load-smoke adapter must provide evidence"
            ),
        )

    def _required_row(self, installation_id: str) -> sqlite3.Row:
        row = self.db.execute(
            "SELECT * FROM deck_plugin_installations WHERE id = ?",
            (installation_id,),
        ).fetchone()
        if row is None:
            raise InstallationServiceError(
                DECK_PLUGIN_INSTALLATION_NOT_FOUND,
                "Deck Plugin installation was not found",
                installation_id=installation_id,
            )
        return row

    def _require_status(
        self,
        row: sqlite3.Row,
        required: InstallationStatus,
        operation_id: str,
    ) -> None:
        current = InstallationStatus(row["status"])
        if current is not required:
            raise InstallationServiceError(
                DECK_PLUGIN_INVALID_TRANSITION,
                f"operation requires {required.value}, found {current.value}",
                installation_id=row["id"],
                operation_id=operation_id,
            )

    @staticmethod
    def _required_pending_version(row: sqlite3.Row, operation_id: str) -> str:
        if not row["pending_version"]:
            raise InstallationServiceError(
                DECK_PLUGIN_CONCURRENT_MODIFICATION,
                "pending target version is missing",
                installation_id=row["id"],
                operation_id=operation_id,
                retryable=True,
            )
        return row["pending_version"]

    def _update_row(self, row: sqlite3.Row, **updates: Any) -> None:
        updates["updated_at"] = "CURRENT_TIMESTAMP"
        assignments: list[str] = []
        parameters: list[Any] = []
        for column, value in updates.items():
            if value == "CURRENT_TIMESTAMP" and column == "updated_at":
                assignments.append("updated_at = CURRENT_TIMESTAMP")
            else:
                assignments.append(f"{column} = ?")
                parameters.append(value)
        assignments.append("revision = revision + 1")
        parameters.extend((row["id"], row["revision"]))
        with self.db:
            cursor = self.db.execute(
                f"UPDATE deck_plugin_installations SET {', '.join(assignments)} "
                "WHERE id = ? AND revision = ?",
                parameters,
            )
        if cursor.rowcount != 1:
            raise InstallationServiceError(
                DECK_PLUGIN_CONCURRENT_MODIFICATION,
                "installation revision changed during the operation",
                installation_id=row["id"],
                retryable=True,
            )

    def _record_initial_failure(
        self,
        row: sqlite3.Row,
        preparation: RuntimePreparation,
        operation_id: str,
    ) -> None:
        assert_installation_transition(
            InstallationStatus(row["status"]), InstallationStatus.ERROR
        )
        self._update_row(
            row,
            status=InstallationStatus.ERROR.value,
            last_error_code=preparation.error_code or DECK_PLUGIN_RUNTIME_NOT_READY,
            last_error_summary=(
                preparation.error_summary
                or f"runtime preparation failed for operation {operation_id}"
            ),
        )

    def _record_non_destructive_failure(
        self,
        row: sqlite3.Row,
        preparation: RuntimePreparation,
    ) -> None:
        self._update_row(
            row,
            status=InstallationStatus.READY.value,
            last_error_code=preparation.error_code or DECK_PLUGIN_RUNTIME_NOT_READY,
            last_error_summary=preparation.error_summary or "target runtime is not ready",
            pending_version=None,
            pending_capabilities_json=None,
        )

    @staticmethod
    def _runtime_error(
        row: sqlite3.Row,
        preparation: RuntimePreparation,
        operation_id: str,
        *,
        rollback: bool = False,
    ) -> InstallationServiceError:
        return InstallationServiceError(
            DECK_PLUGIN_ROLLBACK_BLOCKED if rollback else (
                preparation.error_code or DECK_PLUGIN_RUNTIME_NOT_READY
            ),
            preparation.error_summary or "runtime materialization/load smoke failed",
            installation_id=row["id"],
            operation_id=operation_id,
            retryable=True,
            details={"runtime_readiness": preparation.runtime_readiness},
        )

    @staticmethod
    def _assert_rollback_digests(
        snapshot: _ReleaseSnapshot,
        installation_id: str,
        operation_id: str,
    ) -> None:
        digest_pattern = re.compile(r"^sha256:[0-9a-f]{64}$")
        if any(
            not digest_pattern.fullmatch(entry.artifact_digest)
            for entry in snapshot.runtime_lock.claude_code_plugins
        ):
            raise InstallationServiceError(
                DECK_PLUGIN_ROLLBACK_BLOCKED,
                "rollback release does not have verifiable artifact digests",
                installation_id=installation_id,
                operation_id=operation_id,
                details={"target_version": snapshot.version},
            )

    @staticmethod
    def _installation_from_row(row: sqlite3.Row) -> DeckPluginInstallation:
        return DeckPluginInstallation(
            deck_plugin_installation_id=row["id"],
            scope_type=row["scope_type"],
            scope_id=row["scope_id"],
            deck_plugin_id=row["deck_plugin_id"],
            installed_versions=InstallationService._json_list(
                row["installed_versions_json"]
            ),
            default_version=row["default_version"],
            status=row["status"],
            approved_capabilities=InstallationService._json_list(
                row["approved_capabilities_json"]
            ),
            source_policy_id=row["source_policy_id"],
            last_error_code=row["last_error_code"],
            last_error_summary=row["last_error_summary"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _json_list(value: str | None) -> list[str]:
        parsed = json.loads(value or "[]")
        if not isinstance(parsed, list) or any(not isinstance(item, str) for item in parsed):
            raise InstallationServiceError(
                DECK_PLUGIN_CONCURRENT_MODIFICATION,
                "installation JSON list storage is invalid",
            )
        return parsed

    @staticmethod
    def _capability_diff(current: list[str], target: list[str]) -> CapabilityDiff:
        return CapabilityDiff(
            added=sorted(set(target) - set(current)),
            removed=sorted(set(current) - set(target)),
        )

    @staticmethod
    def _operation_id() -> str:
        return f"op_{uuid.uuid4().hex}"
