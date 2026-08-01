"""Authoritative, fixed-order Workflow Preflight orchestration."""

from __future__ import annotations

import asyncio
import base64
from collections.abc import Awaitable, Callable, Mapping
from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import inspect
import json
import sqlite3
from typing import Any, Literal
import uuid

from pydantic import BaseModel, ConfigDict, Field

try:
    from backend.models.workflow_preflight import (
        PreflightCheck,
        PreflightStatus,
        WorkflowPreflight,
    )
except ModuleNotFoundError:  # Support the backend directory on PYTHONPATH.
    from models.workflow_preflight import (
        PreflightCheck,
        PreflightStatus,
        WorkflowPreflight,
    )


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class IdentityContext(_StrictModel):
    workspace_id: str = Field(min_length=1)


class RequiredRuntimePlugin(_StrictModel):
    claude_code_plugin_id: str = Field(min_length=1)
    artifact_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class BindingReleaseContext(_StrictModel):
    deck_plugin_id: str = Field(min_length=1)
    deck_plugin_version: str = Field(min_length=1)
    runtime_plugin_lock_id: str = Field(min_length=1)
    deck_runtime_profile_id: str = Field(min_length=1)
    deck_runtime_snapshot_contract: str = Field(min_length=1)
    manifest_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    workflow_definition_ref: str = Field(min_length=1)
    input_schema_ref: str = Field(min_length=1)
    output_schema_ref: str = Field(min_length=1)
    required_runtime_plugins: list[RequiredRuntimePlugin] = Field(
        default_factory=list
    )


class DeckRuntimeSnapshotReceipt(_StrictModel):
    """The only Deck-owned snapshot data Story Workspace may retain."""

    deck_runtime_snapshot_id: str = Field(min_length=1)
    sanitized_summary_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    reused: bool = False


class RuntimePluginMaterialization(_StrictModel):
    claude_code_plugin_id: str = Field(min_length=1)
    declaration_status: Literal["undeclared", "declared", "disabled"]
    materialization_status: Literal[
        "missing", "materializing", "materialized", "failed"
    ]
    activation_status: Literal[
        "inactive", "loadable", "loaded", "load_failed"
    ]
    artifact_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class RuntimeMaterializationResult(_StrictModel):
    runtime_plugin_lock_id: str = Field(min_length=1)
    plugins: list[RuntimePluginMaterialization] = Field(default_factory=list)
    load_smoke_passed: bool


class PreflightCheckError(ValueError):
    """A safe structured failure returned by an authoritative dependency."""

    def __init__(self, code: str, summary: str = "preflight check failed") -> None:
        super().__init__(summary)
        self.code = code
        self.summary = summary


class PreflightTokenError(ValueError):
    """A safe token rejection that callers can map to an API error response."""

    def __init__(self, code: str, summary: str) -> None:
        super().__init__(summary)
        self.code = code
        self.summary = summary


CheckCallable = Callable[..., Any | Awaitable[Any]]


_DEFAULT_ERROR_CODES = {
    PreflightCheck.IDENTITY_WORKSPACE_PERMISSION: "WORKFLOW_PERMISSION_DENIED",
    PreflightCheck.BINDING_RELEASE: "DECK_PLUGIN_UNAVAILABLE",
    PreflightCheck.MANIFEST_WORKFLOW_SCHEMA: "DECK_PLUGIN_MANIFEST_INVALID",
    PreflightCheck.HOST_AGENT_RUNTIME_COMPATIBILITY: (
        "CLAUDE_AGENT_INCOMPATIBLE"
    ),
    PreflightCheck.CAPABILITY_SOURCE_POLICY: "WORKFLOW_PERMISSION_DENIED",
    PreflightCheck.DECK_RUNTIME_SNAPSHOT: "DECK_RUNTIME_CONFIG_INVALID",
    PreflightCheck.RUNTIME_MATERIALIZATION: "RUNTIME_PLUGIN_NOT_READY",
    PreflightCheck.TOKEN_ISSUANCE: "PREFLIGHT_TOKEN_ISSUE_FAILED",
}


class PreflightService:
    """Run the eight authoritative checks in order and stop on first failure.

    Deck, compatibility, permission and runtime facts stay with their owning
    services. This coordinator accepts only their narrow, sanitized receipts.
    It has no Workflow Run or ClaudeAgent collaborator, so a failed preflight
    cannot create a pseudo run or start a session.
    """

    def __init__(
        self,
        db: sqlite3.Connection,
        *,
        identity_checker: CheckCallable,
        binding_resolver: CheckCallable,
        manifest_schema_checker: CheckCallable,
        compatibility_checker: CheckCallable,
        capability_policy_checker: CheckCallable,
        deck_snapshot_owner: CheckCallable,
        runtime_materialization_reader: CheckCallable,
        token_secret: bytes | str,
        token_ttl_seconds: int = 300,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if token_ttl_seconds <= 0:
            raise ValueError("token_ttl_seconds must be positive")
        secret = token_secret.encode("utf-8") if isinstance(token_secret, str) else token_secret
        if len(secret) < 32:
            raise ValueError("token_secret must contain at least 32 bytes")

        self.db = db
        self.db.row_factory = sqlite3.Row
        self._identity_checker = identity_checker
        self._binding_resolver = binding_resolver
        self._manifest_schema_checker = manifest_schema_checker
        self._compatibility_checker = compatibility_checker
        self._capability_policy_checker = capability_policy_checker
        self._deck_snapshot_owner = deck_snapshot_owner
        self._runtime_materialization_reader = runtime_materialization_reader
        self._token_secret = secret
        self._token_ttl = timedelta(seconds=token_ttl_seconds)
        self._clock = clock or (lambda: datetime.now(UTC))
        self._request_locks: dict[str, asyncio.Lock] = {}

    async def execute_preflight(
        self,
        deck_id: str,
        binding_revision: int,
        input_data: dict,
        actor: str,
    ) -> WorkflowPreflight:
        """Execute the fixed eight-step preflight and persist its result."""

        if not deck_id.strip() or not actor.strip():
            raise ValueError("deck_id and actor are required")
        if binding_revision < 0:
            raise ValueError("binding_revision must be non-negative")

        input_hash = self._input_hash(input_data)
        fingerprint = self._request_fingerprint(
            deck_id,
            binding_revision,
            input_hash,
            actor,
        )
        request_lock = self._request_locks.setdefault(fingerprint, asyncio.Lock())

        async with request_lock:
            now = self._now()
            reusable = self._active_preflight(fingerprint, now)
            if reusable is not None:
                return self._row_to_model(
                    reusable,
                    token=self._token_from_row(reusable)
                    if reusable["status"] == PreflightStatus.PASSED.value
                    else None,
                )

            preflight_id = "pf_" + uuid.uuid4().hex
            expires_at = now + self._token_ttl
            try:
                self._insert_checking(
                    preflight_id=preflight_id,
                    request_fingerprint=fingerprint,
                    deck_id=deck_id,
                    binding_revision=binding_revision,
                    input_hash=input_hash,
                    actor=actor,
                    created_at=now,
                    expires_at=expires_at,
                )
            except sqlite3.IntegrityError:
                # A different service instance may have won the database race.
                # Reuse its active record instead of duplicating Deck work.
                raced = self._active_preflight(fingerprint, self._now())
                if raced is None:
                    raise
                return self._row_to_model(
                    raced,
                    token=self._token_from_row(raced)
                    if raced["status"] == PreflightStatus.PASSED.value
                    else None,
                )

            current_check = PreflightCheck.IDENTITY_WORKSPACE_PERMISSION
            try:
                identity_raw = await self._call_check(
                    current_check,
                    self._identity_checker,
                    deck_id,
                    actor,
                )
                identity = IdentityContext.model_validate(identity_raw)

                current_check = PreflightCheck.BINDING_RELEASE
                binding_raw = await self._call_check(
                    current_check,
                    self._binding_resolver,
                    deck_id,
                    binding_revision,
                )
                binding = BindingReleaseContext.model_validate(binding_raw)
                self._persist_binding(preflight_id, binding)

                current_check = PreflightCheck.MANIFEST_WORKFLOW_SCHEMA
                await self._call_check(
                    current_check,
                    self._manifest_schema_checker,
                    binding,
                    input_data,
                )

                current_check = PreflightCheck.HOST_AGENT_RUNTIME_COMPATIBILITY
                await self._call_check(
                    current_check,
                    self._compatibility_checker,
                    binding,
                    identity,
                )

                current_check = PreflightCheck.CAPABILITY_SOURCE_POLICY
                await self._call_check(
                    current_check,
                    self._capability_policy_checker,
                    binding,
                    identity,
                )

                current_check = PreflightCheck.DECK_RUNTIME_SNAPSHOT
                snapshot_raw = await self._call_check(
                    current_check,
                    self._deck_snapshot_owner,
                    deck_id,
                    binding.deck_runtime_profile_id,
                    binding.deck_runtime_snapshot_contract,
                )
                snapshot = DeckRuntimeSnapshotReceipt.model_validate(snapshot_raw)
                self._persist_snapshot(preflight_id, snapshot)

                current_check = PreflightCheck.RUNTIME_MATERIALIZATION
                materialization_raw = await self._call_check(
                    current_check,
                    self._runtime_materialization_reader,
                    binding.runtime_plugin_lock_id,
                )
                materialization = RuntimeMaterializationResult.model_validate(
                    materialization_raw
                )
                self._verify_runtime_materialization(binding, materialization)

                current_check = PreflightCheck.TOKEN_ISSUANCE
                issued_at = self._now()
                expires_at = issued_at + self._token_ttl
                token = self._issue_preflight_token(
                    preflight_id,
                    binding_revision,
                    input_hash,
                    snapshot.deck_runtime_snapshot_id,
                    binding.runtime_plugin_lock_id,
                    expires_at,
                )
                self._persist_passed(
                    preflight_id,
                    snapshot,
                    token,
                    expires_at,
                )
                return self._load_model(preflight_id, token=token)
            except PreflightCheckError as exc:
                self._persist_failed(preflight_id, current_check, exc.code)
                return self._load_model(preflight_id)
            except Exception:
                self._persist_failed(
                    preflight_id,
                    current_check,
                    _DEFAULT_ERROR_CODES[current_check],
                )
                return self._load_model(preflight_id)

    def consume_preflight_token(
        self,
        token: str,
        *,
        binding_revision: int,
        input_data: dict,
        deck_runtime_snapshot_id: str,
        runtime_plugin_lock_id: str,
    ) -> WorkflowPreflight:
        """Atomically validate all token bindings and consume it exactly once."""

        token_hash = self._token_hash(token)
        now = self._now()
        try:
            self.db.execute("BEGIN IMMEDIATE")
            row = self.db.execute(
                """
                SELECT * FROM workflow_preflights
                WHERE preflight_token_hash = ?
                """,
                (token_hash,),
            ).fetchone()
            if row is None:
                raise PreflightTokenError(
                    "PREFLIGHT_TOKEN_INVALID",
                    "preflight token is invalid",
                )
            if row["status"] == PreflightStatus.EXPIRED.value:
                raise PreflightTokenError(
                    "PREFLIGHT_TOKEN_EXPIRED",
                    "preflight token has expired",
                )
            if row["status"] != PreflightStatus.PASSED.value:
                raise PreflightTokenError(
                    "PREFLIGHT_TOKEN_INVALID",
                    "preflight did not pass",
                )
            if self._parse_datetime(row["expires_at"]) <= now:
                self.db.execute(
                    """
                    UPDATE workflow_preflights
                    SET status = 'expired', preflight_token_hash = NULL,
                        updated_at = ?
                    WHERE workflow_preflight_id = ?
                    """,
                    (self._iso(now), row["workflow_preflight_id"]),
                )
                self.db.commit()
                raise PreflightTokenError(
                    "PREFLIGHT_TOKEN_EXPIRED",
                    "preflight token has expired",
                )
            if row["consumed_at"] is not None:
                raise PreflightTokenError(
                    "PREFLIGHT_TOKEN_REPLAYED",
                    "preflight token has already been consumed",
                )
            if row["binding_revision"] != binding_revision:
                raise PreflightTokenError(
                    "PREFLIGHT_TOKEN_BINDING_MISMATCH",
                    "binding revision does not match the preflight token",
                )
            if row["input_hash"] != self._input_hash(input_data):
                raise PreflightTokenError(
                    "PREFLIGHT_TOKEN_INPUT_MISMATCH",
                    "input does not match the preflight token",
                )
            if row["deck_runtime_snapshot_id"] != deck_runtime_snapshot_id:
                raise PreflightTokenError(
                    "PREFLIGHT_TOKEN_SNAPSHOT_MISMATCH",
                    "Deck runtime snapshot does not match the preflight token",
                )
            if row["runtime_plugin_lock_id"] != runtime_plugin_lock_id:
                raise PreflightTokenError(
                    "PREFLIGHT_TOKEN_RUNTIME_LOCK_MISMATCH",
                    "runtime lock does not match the preflight token",
                )

            cursor = self.db.execute(
                """
                UPDATE workflow_preflights
                SET consumed_at = ?, updated_at = ?
                WHERE workflow_preflight_id = ? AND consumed_at IS NULL
                """,
                (
                    self._iso(now),
                    self._iso(now),
                    row["workflow_preflight_id"],
                ),
            )
            if cursor.rowcount != 1:
                raise PreflightTokenError(
                    "PREFLIGHT_TOKEN_REPLAYED",
                    "preflight token has already been consumed",
                )
            self.db.commit()
        except Exception:
            if self.db.in_transaction:
                self.db.rollback()
            raise

        return self._load_model(row["workflow_preflight_id"])

    async def _call_check(
        self,
        check: PreflightCheck,
        callback: CheckCallable,
        *args: Any,
    ) -> Any:
        try:
            result = callback(*args)
            if inspect.isawaitable(result):
                result = await result
        except PreflightCheckError:
            raise
        except Exception as exc:
            raise PreflightCheckError(_DEFAULT_ERROR_CODES[check]) from exc

        if result is False:
            raise PreflightCheckError(_DEFAULT_ERROR_CODES[check])
        if isinstance(result, Mapping) and result.get("passed") is False:
            code = str(result.get("error_code") or _DEFAULT_ERROR_CODES[check])
            raise PreflightCheckError(code)
        if getattr(result, "passed", None) is False:
            code = str(
                getattr(result, "error_code", None) or _DEFAULT_ERROR_CODES[check]
            )
            raise PreflightCheckError(code)
        return result

    def _verify_runtime_materialization(
        self,
        binding: BindingReleaseContext,
        result: RuntimeMaterializationResult,
    ) -> None:
        if result.runtime_plugin_lock_id != binding.runtime_plugin_lock_id:
            raise PreflightCheckError("CONFIG_VERSION_DRIFT")

        plugins = {plugin.claude_code_plugin_id: plugin for plugin in result.plugins}
        if len(plugins) != len(result.plugins):
            raise PreflightCheckError("RUNTIME_PLUGIN_NOT_READY")

        for required in binding.required_runtime_plugins:
            actual = plugins.get(required.claude_code_plugin_id)
            if actual is None:
                raise PreflightCheckError("RUNTIME_PLUGIN_NOT_READY")
            if actual.artifact_digest != required.artifact_digest:
                raise PreflightCheckError("DECK_PLUGIN_INTEGRITY_FAILED")
            if (
                actual.declaration_status != "declared"
                or actual.materialization_status != "materialized"
                or actual.activation_status not in {"loadable", "loaded"}
            ):
                raise PreflightCheckError("RUNTIME_PLUGIN_NOT_READY")
        if not result.load_smoke_passed:
            raise PreflightCheckError("RUNTIME_PLUGIN_LOAD_FAILED")

    def _active_preflight(
        self,
        request_fingerprint: str,
        now: datetime,
    ) -> sqlite3.Row | None:
        with self.db:
            self.db.execute(
                """
                UPDATE workflow_preflights
                SET status = 'expired', preflight_token_hash = NULL,
                    updated_at = ?
                WHERE request_fingerprint = ? AND status = 'passed'
                  AND expires_at <= ?
                """,
                (self._iso(now), request_fingerprint, self._iso(now)),
            )
            return self.db.execute(
                """
                SELECT * FROM workflow_preflights
                WHERE request_fingerprint = ?
                  AND status IN ('checking', 'passed')
                  AND consumed_at IS NULL
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (request_fingerprint,),
            ).fetchone()

    def _insert_checking(
        self,
        *,
        preflight_id: str,
        request_fingerprint: str,
        deck_id: str,
        binding_revision: int,
        input_hash: str,
        actor: str,
        created_at: datetime,
        expires_at: datetime,
    ) -> None:
        with self.db:
            self.db.execute(
                """
                INSERT INTO workflow_preflights (
                    workflow_preflight_id, request_fingerprint, deck_id,
                    binding_revision, deck_plugin_id, deck_plugin_version,
                    runtime_plugin_lock_id, deck_runtime_profile_id,
                    input_hash, status, expires_at, created_by,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, 'unresolved', 'unresolved', 'unresolved',
                          'unresolved', ?, 'checking', ?, ?, ?, ?)
                """,
                (
                    preflight_id,
                    request_fingerprint,
                    deck_id,
                    binding_revision,
                    input_hash,
                    self._iso(expires_at),
                    actor,
                    self._iso(created_at),
                    self._iso(created_at),
                ),
            )

    def _persist_binding(
        self,
        preflight_id: str,
        binding: BindingReleaseContext,
    ) -> None:
        with self.db:
            self.db.execute(
                """
                UPDATE workflow_preflights
                SET deck_plugin_id = ?, deck_plugin_version = ?,
                    runtime_plugin_lock_id = ?, deck_runtime_profile_id = ?,
                    updated_at = ?
                WHERE workflow_preflight_id = ?
                """,
                (
                    binding.deck_plugin_id,
                    binding.deck_plugin_version,
                    binding.runtime_plugin_lock_id,
                    binding.deck_runtime_profile_id,
                    self._iso(self._now()),
                    preflight_id,
                ),
            )

    def _persist_snapshot(
        self,
        preflight_id: str,
        snapshot: DeckRuntimeSnapshotReceipt,
    ) -> None:
        with self.db:
            self.db.execute(
                """
                UPDATE workflow_preflights
                SET deck_runtime_snapshot_id = ?,
                    deck_runtime_snapshot_summary_hash = ?, updated_at = ?
                WHERE workflow_preflight_id = ?
                """,
                (
                    snapshot.deck_runtime_snapshot_id,
                    snapshot.sanitized_summary_hash,
                    self._iso(self._now()),
                    preflight_id,
                ),
            )

    def _persist_passed(
        self,
        preflight_id: str,
        snapshot: DeckRuntimeSnapshotReceipt,
        token: str,
        expires_at: datetime,
    ) -> None:
        with self.db:
            self.db.execute(
                """
                UPDATE workflow_preflights
                SET status = 'passed', error_code = NULL, failed_check = NULL,
                    deck_runtime_snapshot_id = ?,
                    deck_runtime_snapshot_summary_hash = ?,
                    preflight_token_hash = ?, expires_at = ?, updated_at = ?
                WHERE workflow_preflight_id = ? AND status = 'checking'
                """,
                (
                    snapshot.deck_runtime_snapshot_id,
                    snapshot.sanitized_summary_hash,
                    self._token_hash(token),
                    self._iso(expires_at),
                    self._iso(self._now()),
                    preflight_id,
                ),
            )

    def _persist_failed(
        self,
        preflight_id: str,
        check: PreflightCheck,
        error_code: str,
    ) -> None:
        with self.db:
            self.db.execute(
                """
                UPDATE workflow_preflights
                SET status = 'failed', error_code = ?, failed_check = ?,
                    preflight_token_hash = NULL, updated_at = ?
                WHERE workflow_preflight_id = ?
                """,
                (
                    error_code,
                    check.value,
                    self._iso(self._now()),
                    preflight_id,
                ),
            )

    def _load_model(
        self,
        preflight_id: str,
        *,
        token: str | None = None,
    ) -> WorkflowPreflight:
        row = self.db.execute(
            """
            SELECT * FROM workflow_preflights
            WHERE workflow_preflight_id = ?
            """,
            (preflight_id,),
        ).fetchone()
        if row is None:
            raise RuntimeError("workflow preflight record disappeared")
        return self._row_to_model(row, token=token)

    def _row_to_model(
        self,
        row: sqlite3.Row,
        *,
        token: str | None,
    ) -> WorkflowPreflight:
        return WorkflowPreflight(
            workflow_preflight_id=row["workflow_preflight_id"],
            deck_id=row["deck_id"],
            binding_revision=row["binding_revision"],
            deck_plugin_id=row["deck_plugin_id"],
            deck_plugin_version=row["deck_plugin_version"],
            runtime_plugin_lock_id=row["runtime_plugin_lock_id"],
            deck_runtime_profile_id=row["deck_runtime_profile_id"],
            deck_runtime_snapshot_id=row["deck_runtime_snapshot_id"],
            deck_runtime_snapshot_summary_hash=row[
                "deck_runtime_snapshot_summary_hash"
            ],
            input_hash=row["input_hash"],
            status=PreflightStatus(row["status"]),
            error_code=row["error_code"],
            failed_check=PreflightCheck(row["failed_check"])
            if row["failed_check"]
            else None,
            expires_at=self._parse_datetime(row["expires_at"]),
            preflight_token=token,
            created_by=row["created_by"],
            created_at=self._parse_datetime(row["created_at"]),
        )

    def _issue_preflight_token(
        self,
        preflight_id: str,
        binding_revision: int,
        input_hash: str,
        deck_runtime_snapshot_id: str,
        runtime_lock_id: str,
        expires_at: datetime,
    ) -> str:
        payload = self._token_payload(
            preflight_id,
            binding_revision,
            input_hash,
            deck_runtime_snapshot_id,
            runtime_lock_id,
            expires_at,
        )
        digest = hmac.new(self._token_secret, payload, hashlib.sha256).digest()
        encoded = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
        return "pft_" + encoded

    def _token_from_row(self, row: sqlite3.Row) -> str:
        return self._issue_preflight_token(
            row["workflow_preflight_id"],
            row["binding_revision"],
            row["input_hash"],
            row["deck_runtime_snapshot_id"],
            row["runtime_plugin_lock_id"],
            self._parse_datetime(row["expires_at"]),
        )

    @classmethod
    def _token_payload(
        cls,
        preflight_id: str,
        binding_revision: int,
        input_hash: str,
        deck_runtime_snapshot_id: str,
        runtime_lock_id: str,
        expires_at: datetime,
    ) -> bytes:
        return cls._canonical_json(
            {
                "preflight_id": preflight_id,
                "binding_revision": binding_revision,
                "input_hash": input_hash,
                "deck_runtime_snapshot_id": deck_runtime_snapshot_id,
                "runtime_plugin_lock_id": runtime_lock_id,
                "expires_at": cls._iso(expires_at),
            }
        )

    @staticmethod
    def _token_hash(token: str) -> str:
        return "sha256:" + hashlib.sha256(token.encode("utf-8")).hexdigest()

    @classmethod
    def _input_hash(cls, input_data: dict) -> str:
        return "sha256:" + hashlib.sha256(cls._canonical_json(input_data)).hexdigest()

    @classmethod
    def _request_fingerprint(
        cls,
        deck_id: str,
        binding_revision: int,
        input_hash: str,
        actor: str,
    ) -> str:
        payload = cls._canonical_json(
            {
                "deck_id": deck_id,
                "binding_revision": binding_revision,
                "input_hash": input_hash,
                "actor": actor,
            }
        )
        return "sha256:" + hashlib.sha256(payload).hexdigest()

    @staticmethod
    def _canonical_json(value: Any) -> bytes:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @staticmethod
    def _parse_datetime(value: str) -> datetime:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)

    @staticmethod
    def _iso(value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).isoformat(timespec="microseconds")
