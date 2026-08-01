"""Single-node, digest-addressed runtime plugin materialization for task_008."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
import inspect
import os
from pathlib import Path
import re
import sqlite3
import tempfile
from typing import Awaitable, Callable, Protocol
import uuid

try:
    from backend.database import create_runtime_plugin_tables
    from backend.models.runtime_plugin import (
        ActivationStatus,
        DeclarationStatus,
        MaterializationResult,
        MaterializationStatus,
        RuntimePlacementContext,
        RuntimePluginMaterialization,
        compute_materialization_key,
        sha256_digest,
    )
except ModuleNotFoundError:  # Support the backend directory on PYTHONPATH.
    from database import create_runtime_plugin_tables
    from models.runtime_plugin import (
        ActivationStatus,
        DeclarationStatus,
        MaterializationResult,
        MaterializationStatus,
        RuntimePlacementContext,
        RuntimePluginMaterialization,
        compute_materialization_key,
        sha256_digest,
    )


MATERIALIZATION_DIGEST_MISMATCH = "MATERIALIZATION_DIGEST_MISMATCH"
MATERIALIZATION_RETENTION_EVIDENCE_MISSING = (
    "MATERIALIZATION_RETENTION_EVIDENCE_MISSING"
)
MATERIALIZATION_PROVIDER_FAILED = "MATERIALIZATION_PROVIDER_FAILED"


class MaterializationError(RuntimeError):
    def __init__(self, code: str, summary: str) -> None:
        self.code = code
        self.summary = summary
        super().__init__(summary)


@dataclass(frozen=True)
class StagedArtifact:
    """Already-resolved artifact bytes and supply-chain evidence."""

    content: bytes
    artifact_digest: str
    verification_status: str
    signature_bundle_ref: str | None
    retention_state: str
    restore_source_ref: str | None


@dataclass(frozen=True)
class RetentionEvidence:
    authoritative: bool
    pinned_or_recoverable: bool
    evidence_ref: str


class ArtifactProvider(Protocol):
    def load_staged(
        self,
        *,
        claude_code_plugin_id: str,
        resolved_version: str,
        artifact_digest: str,
    ) -> StagedArtifact | Awaitable[StagedArtifact]: ...


class RetentionEvidenceReader(Protocol):
    def read(
        self,
        *,
        claude_code_plugin_id: str,
        resolved_version: str,
        artifact_digest: str,
    ) -> RetentionEvidence | None | Awaitable[RetentionEvidence | None]: ...


class AtomicArtifactPublisher(Protocol):
    def publish_atomic(
        self,
        *,
        materialization_key: str,
        content: bytes,
    ) -> str | Awaitable[str]: ...


class FileSystemAtomicPublisher:
    """Publish complete bytes with os.replace into an injected node-local cache."""

    def __init__(self, cache_root: str | Path) -> None:
        self.cache_root = Path(cache_root)

    def publish_atomic(self, *, materialization_key: str, content: bytes) -> str:
        cache_name = materialization_key.removeprefix("sha256:")
        if not re.fullmatch(r"[0-9a-f]{64}", cache_name):
            raise ValueError("invalid materialization key")
        self.cache_root.mkdir(parents=True, exist_ok=True)
        target = self.cache_root / cache_name
        if target.exists():
            if sha256_digest(target.read_bytes()) != sha256_digest(content):
                raise MaterializationError(
                    MATERIALIZATION_DIGEST_MISMATCH,
                    "existing cache bytes do not match staged artifact",
                )
            return str(target)
        handle, temporary_name = tempfile.mkstemp(
            dir=self.cache_root,
            prefix=f".{cache_name}.",
        )
        try:
            with os.fdopen(handle, "wb") as temporary:
                temporary.write(content)
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temporary_name, target)
        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)
        return str(target)


class MaterializationManager:
    """Coordinate one in-flight owner per canonical materialization key."""

    def __init__(
        self,
        db: sqlite3.Connection,
        *,
        artifact_provider: ArtifactProvider,
        retention_evidence_reader: RetentionEvidenceReader,
        publisher: AtomicArtifactPublisher,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        create_runtime_plugin_tables(db)
        self.db = db
        self.db.row_factory = sqlite3.Row
        self._artifact_provider = artifact_provider
        self._retention_evidence_reader = retention_evidence_reader
        self._publisher = publisher
        self._clock = clock or (lambda: datetime.now(UTC))
        self._inflight: dict[str, asyncio.Task[MaterializationResult]] = {}
        self._inflight_lock = asyncio.Lock()

    async def materialize(
        self,
        placement_context: RuntimePlacementContext,
        claude_code_plugin_id: str,
        resolved_version: str,
        artifact_digest: str,
    ) -> MaterializationResult:
        """Materialize staged bytes once; concurrent duplicates share the operation."""

        if not claude_code_plugin_id.strip() or not resolved_version.strip():
            raise ValueError("plugin ID and resolved version are required")
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", artifact_digest):
            raise ValueError("artifact digest must be immutable sha256")
        key = compute_materialization_key(
            placement_context,
            claude_code_plugin_id,
            resolved_version,
            artifact_digest,
        )
        existing = self._select(key)
        if existing is not None and existing["materialization_status"] == "materialized":
            return MaterializationResult(
                materialization=self._row_to_materialization(existing),
                reused=True,
            )

        async with self._inflight_lock:
            operation = self._inflight.get(key)
            reused = operation is not None
            if operation is None:
                operation = asyncio.create_task(
                    self._perform_materialization(
                        placement_context=placement_context,
                        claude_code_plugin_id=claude_code_plugin_id,
                        resolved_version=resolved_version,
                        artifact_digest=artifact_digest,
                        materialization_key=key,
                    )
                )
                self._inflight[key] = operation
        try:
            result = await operation
            if reused:
                return MaterializationResult(
                    materialization=result.materialization,
                    reused=True,
                )
            return result
        finally:
            if operation.done():
                async with self._inflight_lock:
                    if self._inflight.get(key) is operation:
                        self._inflight.pop(key, None)

    async def _perform_materialization(
        self,
        *,
        placement_context: RuntimePlacementContext,
        claude_code_plugin_id: str,
        resolved_version: str,
        artifact_digest: str,
        materialization_key: str,
    ) -> MaterializationResult:
        materialization_id, attempt_id, attempt_count, created_at = self._begin_attempt(
            placement_context=placement_context,
            claude_code_plugin_id=claude_code_plugin_id,
            resolved_version=resolved_version,
            artifact_digest=artifact_digest,
            materialization_key=materialization_key,
        )
        try:
            staged = await _resolve(
                self._artifact_provider.load_staged(
                    claude_code_plugin_id=claude_code_plugin_id,
                    resolved_version=resolved_version,
                    artifact_digest=artifact_digest,
                )
            )
            if staged.artifact_digest != artifact_digest:
                raise MaterializationError(
                    MATERIALIZATION_DIGEST_MISMATCH,
                    "staged descriptor digest does not match runtime lock",
                )
            actual_digest = sha256_digest(staged.content)
            if actual_digest != artifact_digest:
                raise MaterializationError(
                    MATERIALIZATION_DIGEST_MISMATCH,
                    "staged artifact bytes do not match runtime lock",
                )
            if staged.verification_status not in {"verified", "legacy_unverified"}:
                raise MaterializationError(
                    MATERIALIZATION_PROVIDER_FAILED,
                    "staged artifact verification status is unsupported",
                )
            retention = await _resolve(
                self._retention_evidence_reader.read(
                    claude_code_plugin_id=claude_code_plugin_id,
                    resolved_version=resolved_version,
                    artifact_digest=artifact_digest,
                )
            )
            if (
                retention is None
                or not retention.authoritative
                or not retention.pinned_or_recoverable
            ):
                raise MaterializationError(
                    MATERIALIZATION_RETENTION_EVIDENCE_MISSING,
                    "authoritative pin or recoverable evidence is required",
                )
            cache_ref = await _resolve(
                self._publisher.publish_atomic(
                    materialization_key=materialization_key,
                    content=staged.content,
                )
            )
            updated_at = self._clock()
            self.db.execute(
                """
                UPDATE runtime_plugin_materializations
                SET materialized_digest = ?, materialization_status = 'materialized',
                    activation_status = 'loadable', verification_status = ?,
                    signature_bundle_ref = ?, retention_state = ?,
                    restore_source_ref = ?, cache_ref = ?, last_error = NULL,
                    updated_at = ?
                WHERE runtime_materialization_id = ? AND attempt_id = ?
                """,
                (
                    actual_digest,
                    staged.verification_status,
                    staged.signature_bundle_ref,
                    staged.retention_state,
                    staged.restore_source_ref,
                    cache_ref,
                    self._iso(updated_at),
                    materialization_id,
                    attempt_id,
                ),
            )
            self.db.commit()
            row = self._select(materialization_key)
            assert row is not None
            return MaterializationResult(
                materialization=self._row_to_materialization(row),
                reused=False,
            )
        except Exception as exc:
            error = exc if isinstance(exc, MaterializationError) else MaterializationError(
                MATERIALIZATION_PROVIDER_FAILED,
                "runtime artifact materialization failed",
            )
            self.db.execute(
                """
                UPDATE runtime_plugin_materializations
                SET materialization_status = 'failed', activation_status = 'inactive',
                    last_error = ?, updated_at = ?
                WHERE runtime_materialization_id = ? AND attempt_id = ?
                """,
                (
                    self._sanitize_error(error.summary),
                    self._iso(self._clock()),
                    materialization_id,
                    attempt_id,
                ),
            )
            self.db.commit()
            raise error from exc if error is not exc else None

    def _begin_attempt(
        self,
        *,
        placement_context: RuntimePlacementContext,
        claude_code_plugin_id: str,
        resolved_version: str,
        artifact_digest: str,
        materialization_key: str,
    ) -> tuple[str, str, int, datetime]:
        row = self._select(materialization_key)
        attempt_id = "rpa_" + uuid.uuid4().hex
        now = self._clock()
        if row is None:
            materialization_id = "rm_" + uuid.uuid4().hex
            attempt_count = 1
            created_at = now
            self.db.execute(
                """
                INSERT INTO runtime_plugin_materializations (
                    runtime_materialization_id, runtime_environment_id,
                    runtime_pool_id, runtime_node_id, claude_code_plugin_id,
                    resolved_version, artifact_digest, artifact_set_hash,
                    policy_revision, declaration_status, materialization_status,
                    activation_status, materialization_key, attempt_id,
                    attempt_count, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'declared',
                          'materializing', 'inactive', ?, ?, 1, ?, ?)
                """,
                (
                    materialization_id,
                    placement_context.runtime_environment_id,
                    placement_context.runtime_pool_id,
                    placement_context.runtime_node_id,
                    claude_code_plugin_id,
                    resolved_version,
                    artifact_digest,
                    placement_context.artifact_set_hash,
                    placement_context.policy_revision,
                    materialization_key,
                    attempt_id,
                    self._iso(now),
                    self._iso(now),
                ),
            )
        else:
            materialization_id = row["runtime_materialization_id"]
            attempt_count = int(row["attempt_count"]) + 1
            created_at = self._parse_datetime(row["created_at"])
            self.db.execute(
                """
                UPDATE runtime_plugin_materializations
                SET materialized_digest = NULL, materialization_status = 'materializing',
                    activation_status = 'inactive', attempt_id = ?, attempt_count = ?,
                    verification_status = NULL, signature_bundle_ref = NULL,
                    retention_state = NULL, restore_source_ref = NULL,
                    cache_ref = NULL, last_error = NULL, updated_at = ?
                WHERE materialization_key = ?
                """,
                (attempt_id, attempt_count, self._iso(now), materialization_key),
            )
        self.db.commit()
        return materialization_id, attempt_id, attempt_count, created_at

    def _select(self, materialization_key: str) -> sqlite3.Row | None:
        return self.db.execute(
            "SELECT * FROM runtime_plugin_materializations WHERE materialization_key = ?",
            (materialization_key,),
        ).fetchone()

    @classmethod
    def _row_to_materialization(cls, row: sqlite3.Row) -> RuntimePluginMaterialization:
        return RuntimePluginMaterialization(
            runtime_materialization_id=row["runtime_materialization_id"],
            runtime_environment_id=row["runtime_environment_id"],
            runtime_pool_id=row["runtime_pool_id"],
            runtime_node_id=row["runtime_node_id"],
            claude_code_plugin_id=row["claude_code_plugin_id"],
            resolved_version=row["resolved_version"],
            artifact_digest=row["artifact_digest"],
            materialized_digest=row["materialized_digest"],
            artifact_set_hash=row["artifact_set_hash"],
            policy_revision=row["policy_revision"],
            declaration_status=DeclarationStatus(row["declaration_status"]),
            materialization_status=MaterializationStatus(row["materialization_status"]),
            activation_status=ActivationStatus(row["activation_status"]),
            materialization_key=row["materialization_key"],
            attempt_id=row["attempt_id"],
            attempt_count=row["attempt_count"],
            verification_status=row["verification_status"],
            signature_bundle_ref=row["signature_bundle_ref"],
            retention_state=row["retention_state"],
            restore_source_ref=row["restore_source_ref"],
            cache_ref=row["cache_ref"],
            last_error=row["last_error"],
            created_at=cls._parse_datetime(row["created_at"]),
            updated_at=cls._parse_datetime(row["updated_at"]),
        )

    @staticmethod
    def _sanitize_error(value: str) -> str:
        sanitized = re.sub(
            r"(?i)(token|secret|password|authorization)\s*[:=]\s*\S+",
            r"\1=[REDACTED]",
            value,
        )
        return sanitized[:512]

    @staticmethod
    def _iso(value: datetime) -> str:
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _parse_datetime(value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))


async def _resolve(value):
    if inspect.isawaitable(value):
        return await value
    return value
