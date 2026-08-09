"""Declarative runtime plugin reconcile, controlled CLI, and load receipts."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
import inspect
import json
import re
from typing import Any, Awaitable, Callable, Literal, Protocol
import uuid

from pydantic import BaseModel, ConfigDict

try:
    from backend.models.deck_plugin import DeckRuntimePluginLock
    from backend.models.runtime_plugin import (
        ActivationStatus,
        CliResult,
        HeadlessPluginState,
        LoadReceiptEntry,
        MaterializationResult,
        MaterializationStatus,
        ReconcileResult,
        RuntimeLoadReceipt,
        RuntimePlacementContext,
        RuntimePluginMaterialization,
        compute_artifact_set_hash,
        runtime_lock_digest,
    )
except ModuleNotFoundError:  # Support the backend directory on PYTHONPATH.
    from models.deck_plugin import DeckRuntimePluginLock
    from models.runtime_plugin import (
        ActivationStatus,
        CliResult,
        HeadlessPluginState,
        LoadReceiptEntry,
        MaterializationResult,
        MaterializationStatus,
        ReconcileResult,
        RuntimeLoadReceipt,
        RuntimePlacementContext,
        RuntimePluginMaterialization,
        compute_artifact_set_hash,
        runtime_lock_digest,
    )


RECONCILE_CONTEXT_MISMATCH = "RECONCILE_CONTEXT_MISMATCH"
RECONCILE_POLICY_DENIED = "RECONCILE_POLICY_DENIED"
RECONCILE_HEADLESS_FAILED = "RECONCILE_HEADLESS_FAILED"
RECONCILE_OUTPUT_INVALID = "RECONCILE_OUTPUT_INVALID"
CLI_POLICY_DENIED = "CLI_POLICY_DENIED"
CLI_EXECUTION_FAILED = "CLI_EXECUTION_FAILED"
CLI_OUTPUT_INVALID = "CLI_OUTPUT_INVALID"
LOAD_RECEIPT_NOT_READY = "LOAD_RECEIPT_NOT_READY"


class ReconcileError(RuntimeError):
    def __init__(self, code: str, summary: str) -> None:
        self.code = code
        self.summary = summary
        super().__init__(summary)


@dataclass(frozen=True)
class MarketplaceIntent:
    alias: str
    source: Literal["github"]
    repo: str
    allowed_source_refs: frozenset[str]

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,62}", self.alias):
            raise ValueError("marketplace alias is not controlled")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", self.repo):
            raise ValueError("marketplace repository is not controlled")
        if not self.allowed_source_refs:
            raise ValueError("marketplace policy requires source references")


class RuntimeSourcePolicy(Protocol):
    policy_revision: str

    def marketplace_for(
        self,
        claude_code_plugin_id: str,
        source_ref: str,
    ) -> MarketplaceIntent: ...


class AllowlistRuntimeSourcePolicy:
    def __init__(
        self,
        *,
        policy_revision: str,
        plugins: dict[str, MarketplaceIntent],
    ) -> None:
        if not policy_revision.strip():
            raise ValueError("policy revision is required")
        self.policy_revision = policy_revision
        self._plugins = dict(plugins)

    def marketplace_for(
        self,
        claude_code_plugin_id: str,
        source_ref: str,
    ) -> MarketplaceIntent:
        intent = self._plugins.get(claude_code_plugin_id)
        if intent is None or source_ref not in intent.allowed_source_refs:
            raise ReconcileError(
                RECONCILE_POLICY_DENIED,
                "runtime plugin source is not allowlisted",
            )
        _, separator, alias = claude_code_plugin_id.rpartition("@")
        if not separator or alias != intent.alias:
            raise ReconcileError(
                RECONCILE_POLICY_DENIED,
                "plugin marketplace alias does not match trusted policy",
            )
        return intent


class SettingsIntentWriter(Protocol):
    def write_settings(
        self,
        *,
        workflow_run_id: str,
        runtime_node_id: str,
        settings: dict[str, object],
    ) -> None | Awaitable[None]: ...


class HeadlessReconcileRunner(Protocol):
    def reconcile(
        self,
        *,
        workflow_run_id: str,
        runtime_node_id: str,
        settings: dict[str, object],
        env: dict[str, str],
    ) -> dict[str, object] | Awaitable[dict[str, object]]: ...


class _HeadlessInitEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plugins: list[HeadlessPluginState]


@dataclass(frozen=True)
class CompletedCliProcess:
    exit_code: int
    stdout: bytes
    stderr: bytes


class CliSourcePolicy(Protocol):
    policy_revision: str

    def authorize(
        self,
        *,
        claude_code_plugin_id: str,
        resolved_version: str,
        scope: str,
    ) -> None: ...


class AllowlistCliSourcePolicy:
    """Closed plugin/version/marketplace/scope policy for CLI fallback."""

    def __init__(
        self,
        *,
        policy_revision: str,
        allowed_plugins: dict[str, frozenset[str]],
        allowed_marketplace_sources: dict[str, frozenset[str]],
        allowed_scopes: frozenset[str] = frozenset({"project", "local"}),
    ) -> None:
        if not policy_revision.strip():
            raise ValueError("policy revision is required")
        self.policy_revision = policy_revision
        self._allowed_plugins = dict(allowed_plugins)
        if any(not sources for sources in allowed_marketplace_sources.values()):
            raise ValueError("every CLI marketplace requires an allowlisted source")
        self._allowed_marketplace_sources = dict(allowed_marketplace_sources)
        self._allowed_scopes = allowed_scopes

    def authorize(
        self,
        *,
        claude_code_plugin_id: str,
        resolved_version: str,
        scope: str,
    ) -> None:
        _, separator, marketplace = claude_code_plugin_id.rpartition("@")
        allowed_versions = self._allowed_plugins.get(claude_code_plugin_id)
        if (
            not separator
            or marketplace not in self._allowed_marketplace_sources
            or allowed_versions is None
            or resolved_version not in allowed_versions
            or scope not in self._allowed_scopes
        ):
            raise ReconcileError(CLI_POLICY_DENIED, "CLI install request is not allowlisted")


class CliRunner(Protocol):
    def run(
        self,
        argv: list[str],
        *,
        timeout_seconds: int,
        shell: bool,
    ) -> CompletedCliProcess | Awaitable[CompletedCliProcess]: ...


class SubprocessCliRunner:
    async def run(
        self,
        argv: list[str],
        *,
        timeout_seconds: int,
        shell: bool,
    ) -> CompletedCliProcess:
        if shell:
            raise ValueError("shell execution is forbidden")
        process = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout_seconds,
            )
        except TimeoutError:
            process.kill()
            await process.communicate()
            raise ReconcileError(CLI_EXECUTION_FAILED, "CLI install timed out")
        return CompletedCliProcess(
            exit_code=int(process.returncode or 0),
            stdout=stdout,
            stderr=stderr,
        )


@dataclass(frozen=True)
class CliAuditRecord:
    attempt_id: str
    policy_revision: str
    argv: tuple[str, ...]
    timeout_seconds: int
    exit_code: int | None
    stdout_summary: str
    stderr_summary: str
    result_status: Literal["succeeded", "failed"]
    error_code: str | None
    claude_code_plugin_id: str
    resolved_version: str
    created_at: datetime


class CliAuditSink(Protocol):
    def record(self, record: CliAuditRecord) -> None | Awaitable[None]: ...


class SqliteCliAuditSink:
    def __init__(self, db: Any) -> None:
        self.db = db

    def record(self, record: CliAuditRecord) -> None:
        self.db.execute(
            """
            INSERT INTO runtime_plugin_reconcile_attempts (
                attempt_id, reconcile_path, claude_code_plugin_id,
                resolved_version, policy_revision, argv_json,
                timeout_seconds, exit_code, stdout_summary, stderr_summary,
                result_status, error_code, created_at
            ) VALUES (%s, 'cli', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                record.attempt_id,
                record.claude_code_plugin_id,
                record.resolved_version,
                record.policy_revision,
                json.dumps(list(record.argv), separators=(",", ":")),
                record.timeout_seconds,
                record.exit_code,
                record.stdout_summary,
                record.stderr_summary,
                record.result_status,
                record.error_code,
                ReconcileService._iso(record.created_at),
            ),
        )
        self.db.commit()


class ReconcileService:
    """Own settings/headless reconcile and immutable task_008 receipts."""

    def __init__(
        self,
        db: Any,
        *,
        source_policy: RuntimeSourcePolicy,
        settings_writer: SettingsIntentWriter,
        headless_runner: HeadlessReconcileRunner,
        cli_source_policy: CliSourcePolicy,
        cli_runner: CliRunner,
        cli_audit_sink: CliAuditSink | None = None,
        cli_timeout_seconds: int = 30,
        max_cli_output_bytes: int = 4096,
        max_reconcile_attempts: int = 2,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not 1 <= cli_timeout_seconds <= 300:
            raise ValueError("CLI timeout must be within 1..300 seconds")
        if not 256 <= max_cli_output_bytes <= 65536:
            raise ValueError("CLI output limit must be within 256..65536 bytes")
        if not 1 <= max_reconcile_attempts <= 3:
            raise ValueError("headless reconcile attempts must be within 1..3")
        self.db = db
        self._source_policy = source_policy
        self._settings_writer = settings_writer
        self._headless_runner = headless_runner
        self._cli_source_policy = cli_source_policy
        self._cli_runner = cli_runner
        self._cli_audit_sink = cli_audit_sink or SqliteCliAuditSink(db)
        self._cli_timeout_seconds = cli_timeout_seconds
        self._max_cli_output_bytes = max_cli_output_bytes
        self._max_reconcile_attempts = max_reconcile_attempts
        self._clock = clock or (lambda: datetime.now(UTC))

    async def declare_and_reconcile(
        self,
        runtime_lock: DeckRuntimePluginLock,
        placement_context: RuntimePlacementContext,
    ) -> ReconcileResult:
        """Write controlled intent and synchronously validate headless init.plugins."""

        self._validate_context(runtime_lock, placement_context)
        settings = self._build_settings(runtime_lock, placement_context)
        last_error: ReconcileError | None = None
        for attempt_number in range(1, self._max_reconcile_attempts + 1):
            attempt_id = "rpa_" + uuid.uuid4().hex
            created_at = self._clock()
            try:
                try:
                    await _resolve(
                        self._settings_writer.write_settings(
                            workflow_run_id=placement_context.workflow_run_id,
                            runtime_node_id=placement_context.runtime_node_id,
                            settings=settings,
                        )
                    )
                    raw = await _resolve(
                        self._headless_runner.reconcile(
                            workflow_run_id=placement_context.workflow_run_id,
                            runtime_node_id=placement_context.runtime_node_id,
                            settings=settings,
                            env={"CLAUDE_CODE_SYNC_PLUGIN_INSTALL": "true"},
                        )
                    )
                except ReconcileError:
                    raise
                except Exception as exc:
                    raise ReconcileError(
                        RECONCILE_HEADLESS_FAILED,
                        "settings or headless reconcile execution failed",
                    ) from exc
                try:
                    envelope = _HeadlessInitEnvelope.model_validate(raw)
                except Exception as exc:
                    raise ReconcileError(
                        RECONCILE_OUTPUT_INVALID,
                        "headless reconcile returned invalid structured output",
                    ) from exc
                self._validate_headless_plugins(runtime_lock, envelope.plugins)
                result = ReconcileResult(
                    attempt_id=attempt_id,
                    workflow_run_id=placement_context.workflow_run_id,
                    runtime_node_id=placement_context.runtime_node_id,
                    policy_revision=placement_context.policy_revision,
                    settings_intent=settings,
                    plugins=envelope.plugins,
                    completed_before_first_query=True,
                    created_at=created_at,
                )
                self._record_headless_attempt(
                    result=result,
                    result_status="succeeded",
                    error_code=None,
                )
                return result
            except ReconcileError as exc:
                last_error = exc
            self._record_headless_failure(
                attempt_id=attempt_id,
                placement_context=placement_context,
                error=last_error,
                created_at=created_at,
            )
            if attempt_number < self._max_reconcile_attempts:
                await asyncio.sleep(0.01 * (2 ** (attempt_number - 1)))
        assert last_error is not None
        raise last_error

    async def cli_install(
        self,
        claude_code_plugin_id: str,
        resolved_version: str,
        scope: Literal["project", "local"] = "project",
    ) -> CliResult:
        """Execute the closed CLI fallback with strict output and audit."""

        attempt_id = "rpa_" + uuid.uuid4().hex
        created_at = self._clock()
        argv = [
            "claude",
            "plugin",
            "install",
            claude_code_plugin_id,
            "--scope",
            scope,
            "--json",
        ]
        process: CompletedCliProcess | None = None
        result: CliResult | None = None
        error: ReconcileError | None = None
        try:
            self._cli_source_policy.authorize(
                claude_code_plugin_id=claude_code_plugin_id,
                resolved_version=resolved_version,
                scope=scope,
            )
            process = await _resolve(
                self._cli_runner.run(
                    argv,
                    timeout_seconds=self._cli_timeout_seconds,
                    shell=False,
                )
            )
            if (
                len(process.stdout) > self._max_cli_output_bytes
                or len(process.stderr) > self._max_cli_output_bytes
            ):
                raise ReconcileError(CLI_OUTPUT_INVALID, "CLI output exceeded limit")
            if process.exit_code != 0:
                raise ReconcileError(CLI_EXECUTION_FAILED, "CLI install failed")
            try:
                result = CliResult.model_validate_json(process.stdout)
            except Exception as exc:
                raise ReconcileError(
                    CLI_OUTPUT_INVALID,
                    "CLI stdout is not the strict result schema",
                ) from exc
            if (
                result.claude_code_plugin_id != claude_code_plugin_id
                or result.resolved_version != resolved_version
            ):
                raise ReconcileError(
                    CLI_OUTPUT_INVALID,
                    "CLI result does not match the locked plugin",
                )
        except ReconcileError as exc:
            error = exc
        except Exception:
            error = ReconcileError(CLI_EXECUTION_FAILED, "CLI install execution failed")

        stdout_summary = self._sanitize_output(process.stdout if process else b"")
        stderr_summary = self._sanitize_output(process.stderr if process else b"")
        await _resolve(
            self._cli_audit_sink.record(
                CliAuditRecord(
                    attempt_id=attempt_id,
                    policy_revision=self._cli_source_policy.policy_revision,
                    argv=tuple(argv),
                    timeout_seconds=self._cli_timeout_seconds,
                    exit_code=process.exit_code if process is not None else None,
                    stdout_summary=stdout_summary,
                    stderr_summary=stderr_summary,
                    result_status="failed" if error else "succeeded",
                    error_code=error.code if error else None,
                    claude_code_plugin_id=claude_code_plugin_id,
                    resolved_version=resolved_version,
                    created_at=created_at,
                )
            )
        )
        if error is not None:
            raise error
        assert result is not None
        return result

    def create_load_receipt(
        self,
        *,
        runtime_lock: DeckRuntimePluginLock,
        placement_context: RuntimePlacementContext,
        reconcile_result: ReconcileResult,
        materializations: list[MaterializationResult | RuntimePluginMaterialization],
    ) -> RuntimeLoadReceipt:
        """Validate run/lock/load evidence and append one immutable receipt."""

        self._validate_context(runtime_lock, placement_context)
        if (
            reconcile_result.workflow_run_id != placement_context.workflow_run_id
            or reconcile_result.runtime_node_id != placement_context.runtime_node_id
            or reconcile_result.policy_revision != placement_context.policy_revision
        ):
            raise ReconcileError(
                LOAD_RECEIPT_NOT_READY,
                "reconcile result does not match trusted placement",
            )
        run = self.db.execute(
            "SELECT id, runtime_plugin_lock_id FROM workflow_runs WHERE id = %s",
            (placement_context.workflow_run_id,),
        ).fetchone()
        if run is None or run["runtime_plugin_lock_id"] != runtime_lock.runtime_plugin_lock_id:
            raise ReconcileError(
                LOAD_RECEIPT_NOT_READY,
                "workflow run does not bind the supplied runtime lock",
            )
        lock_row = self.db.execute(
            "SELECT lock_json FROM deck_runtime_plugin_locks WHERE id = %s",
            (runtime_lock.runtime_plugin_lock_id,),
        ).fetchone()
        if lock_row is None:
            raise ReconcileError(LOAD_RECEIPT_NOT_READY, "runtime lock was not found")

        materialization_map: dict[str, RuntimePluginMaterialization] = {}
        for item in materializations:
            materialization = (
                item.materialization
                if isinstance(item, MaterializationResult)
                else item
            )
            materialization_map[
                materialization.claude_code_plugin_id
            ] = materialization
        reconcile_map = {
            item.claude_code_plugin_id: item for item in reconcile_result.plugins
        }
        entries: list[LoadReceiptEntry] = []
        activation_updates: list[tuple[str, str]] = []
        for locked in runtime_lock.claude_code_plugins:
            materialization = materialization_map.get(locked.claude_code_plugin_id)
            loaded = reconcile_map.get(locked.claude_code_plugin_id)
            if materialization is None or loaded is None:
                raise ReconcileError(
                    LOAD_RECEIPT_NOT_READY,
                    "receipt evidence is incomplete for a locked plugin",
                )
            if (
                materialization.runtime_environment_id
                != placement_context.runtime_environment_id
                or materialization.runtime_node_id != placement_context.runtime_node_id
                or materialization.artifact_set_hash != placement_context.artifact_set_hash
                or materialization.policy_revision != placement_context.policy_revision
                or materialization.resolved_version != locked.resolved_version
                or materialization.artifact_digest != locked.artifact_digest
                or materialization.materialized_digest != locked.artifact_digest
                or materialization.materialization_status
                is not MaterializationStatus.MATERIALIZED
                or materialization.verification_status is None
                or materialization.retention_state is None
            ):
                raise ReconcileError(
                    LOAD_RECEIPT_NOT_READY,
                    "materialization evidence does not match the runtime lock",
                )
            capabilities_ready = set(locked.capability_bindings).issubset(
                loaded.loaded_capabilities
            )
            load_status = loaded.load_status if capabilities_ready else "load_failed"
            entries.append(
                LoadReceiptEntry(
                    claude_code_plugin_id=locked.claude_code_plugin_id,
                    resolved_version=locked.resolved_version,
                    artifact_digest=locked.artifact_digest,
                    materialized_digest=materialization.materialized_digest,
                    verification_status=materialization.verification_status,
                    signature_bundle_ref=materialization.signature_bundle_ref,
                    retention_state=materialization.retention_state,
                    restore_source_ref=materialization.restore_source_ref,
                    required=locked.required,
                    loaded_capabilities=loaded.loaded_capabilities,
                    load_status=load_status,
                    loaded_at=loaded.loaded_at,
                )
            )
            activation_updates.append(
                (
                    ActivationStatus.LOADED.value
                    if load_status == "loaded"
                    else ActivationStatus.LOAD_FAILED.value,
                    materialization.runtime_materialization_id,
                )
            )
        entries.sort(key=lambda item: item.claude_code_plugin_id)
        required_entries = [entry for entry in entries if entry.required]
        required_ready = bool(required_entries) and all(
            entry.load_status == "loaded"
            and entry.materialized_digest == entry.artifact_digest
            for entry in required_entries
        )
        receipt = RuntimeLoadReceipt(
            receipt_id="rlr_" + uuid.uuid4().hex,
            workflow_run_id=placement_context.workflow_run_id,
            runtime_plugin_lock_id=runtime_lock.runtime_plugin_lock_id,
            runtime_plugin_lock_digest=runtime_lock_digest(lock_row["lock_json"]),
            runtime_environment_id=placement_context.runtime_environment_id,
            runtime_pool_id=placement_context.runtime_pool_id,
            distribution_mode=placement_context.distribution_mode,
            runtime_node_id=placement_context.runtime_node_id,
            artifact_set_hash=placement_context.artifact_set_hash,
            policy_revision=placement_context.policy_revision,
            deployment_tier=placement_context.deployment_tier,
            scope="session",
            readiness_state="session_loaded",
            required_entries_ready=required_ready,
            entries=entries,
            created_at=self._clock(),
        )
        self._persist_receipt(receipt, activation_updates)
        return receipt

    def read_receipt(self, receipt_id: str) -> RuntimeLoadReceipt:
        receipt = self.db.execute(
            "SELECT * FROM runtime_load_receipts WHERE receipt_id = %s",
            (receipt_id,),
        ).fetchone()
        if receipt is None:
            raise KeyError(receipt_id)
        rows = self.db.execute(
            """
            SELECT * FROM runtime_load_receipt_entries
            WHERE receipt_id = %s ORDER BY claude_code_plugin_id
            """,
            (receipt_id,),
        ).fetchall()
        return RuntimeLoadReceipt(
            receipt_id=receipt["receipt_id"],
            workflow_run_id=receipt["workflow_run_id"],
            runtime_plugin_lock_id=receipt["runtime_plugin_lock_id"],
            runtime_plugin_lock_digest=receipt["runtime_plugin_lock_digest"],
            runtime_environment_id=receipt["runtime_environment_id"],
            runtime_pool_id=receipt["runtime_pool_id"],
            distribution_mode=receipt["distribution_mode"],
            runtime_node_id=receipt["runtime_node_id"],
            artifact_set_hash=receipt["artifact_set_hash"],
            policy_revision=receipt["policy_revision"],
            deployment_tier=receipt["deployment_tier"],
            scope=receipt["scope"],
            readiness_state=receipt["readiness_state"],
            required_entries_ready=bool(receipt["required_entries_ready"]),
            entries=[
                LoadReceiptEntry(
                    claude_code_plugin_id=row["claude_code_plugin_id"],
                    resolved_version=row["resolved_version"],
                    artifact_digest=row["artifact_digest"],
                    materialized_digest=row["materialized_digest"],
                    verification_status=row["verification_status"],
                    signature_bundle_ref=row["signature_bundle_ref"],
                    retention_state=row["retention_state"],
                    restore_source_ref=row["restore_source_ref"],
                    required=bool(row["required"]),
                    loaded_capabilities=json.loads(row["loaded_capabilities_json"]),
                    load_status=row["load_status"],
                    loaded_at=self._parse_datetime(row["loaded_at"]),
                )
                for row in rows
            ],
            created_at=self._parse_datetime(receipt["created_at"]),
        )

    def read_workflow_readiness(self, receipt_id: str) -> dict[str, object]:
        """Return exactly the five keys consumed by RuntimeLoadReceiptReadiness."""

        receipt = self.db.execute(
            """
            SELECT receipt_id, workflow_run_id, runtime_plugin_lock_id,
                   runtime_plugin_lock_digest, required_entries_ready
            FROM runtime_load_receipts WHERE receipt_id = %s
            """,
            (receipt_id,),
        ).fetchone()
        if receipt is None:
            raise KeyError(receipt_id)
        return {
            "receipt_id": receipt["receipt_id"],
            "workflow_run_id": receipt["workflow_run_id"],
            "runtime_plugin_lock_id": receipt["runtime_plugin_lock_id"],
            "runtime_plugin_lock_digest": receipt["runtime_plugin_lock_digest"],
            "required_entries_ready": bool(receipt["required_entries_ready"]),
        }

    def _validate_context(
        self,
        runtime_lock: DeckRuntimePluginLock,
        placement_context: RuntimePlacementContext,
    ) -> None:
        if self._source_policy.policy_revision != placement_context.policy_revision:
            raise ReconcileError(
                RECONCILE_CONTEXT_MISMATCH,
                "trusted policy revision does not match placement",
            )
        expected_hash = compute_artifact_set_hash(runtime_lock)
        if expected_hash != placement_context.artifact_set_hash:
            raise ReconcileError(
                RECONCILE_CONTEXT_MISMATCH,
                "artifact set hash does not match required runtime lock entries",
            )
        if not runtime_lock.claude_code_plugins or not any(
            entry.required for entry in runtime_lock.claude_code_plugins
        ):
            raise ReconcileError(
                RECONCILE_CONTEXT_MISMATCH,
                "runtime lock requires at least one required plugin",
            )

    def _build_settings(
        self,
        runtime_lock: DeckRuntimePluginLock,
        placement_context: RuntimePlacementContext,
    ) -> dict[str, object]:
        enabled: dict[str, bool] = {}
        marketplaces: dict[str, object] = {}
        for entry in runtime_lock.claude_code_plugins:
            intent = self._source_policy.marketplace_for(
                entry.claude_code_plugin_id,
                entry.source_ref,
            )
            enabled[entry.claude_code_plugin_id] = True
            declaration = {"source": intent.source, "repo": intent.repo}
            existing = marketplaces.get(intent.alias)
            if existing is not None and existing != declaration:
                raise ReconcileError(
                    RECONCILE_POLICY_DENIED,
                    "marketplace alias has conflicting trusted declarations",
                )
            marketplaces[intent.alias] = declaration
        return {
            "enabledPlugins": dict(sorted(enabled.items())),
            "extraKnownMarketplaces": dict(sorted(marketplaces.items())),
        }

    @staticmethod
    def _validate_headless_plugins(
        runtime_lock: DeckRuntimePluginLock,
        plugins: list[HeadlessPluginState],
    ) -> None:
        observed = {plugin.claude_code_plugin_id: plugin for plugin in plugins}
        if len(observed) != len(plugins):
            raise ReconcileError(RECONCILE_OUTPUT_INVALID, "duplicate init.plugins entry")
        locked_ids = {entry.claude_code_plugin_id for entry in runtime_lock.claude_code_plugins}
        if set(observed) != locked_ids:
            raise ReconcileError(
                RECONCILE_OUTPUT_INVALID,
                "headless init.plugins does not equal the locked plugin set",
            )
        for locked in runtime_lock.claude_code_plugins:
            plugin = observed[locked.claude_code_plugin_id]
            if (
                plugin.resolved_version != locked.resolved_version
                or plugin.artifact_digest != locked.artifact_digest
            ):
                raise ReconcileError(
                    RECONCILE_OUTPUT_INVALID,
                    "headless plugin evidence does not match the runtime lock",
                )

    def _record_headless_attempt(
        self,
        *,
        result: ReconcileResult,
        result_status: str,
        error_code: str | None,
    ) -> None:
        self.db.execute(
            """
            INSERT INTO runtime_plugin_reconcile_attempts (
                attempt_id, workflow_run_id, reconcile_path, runtime_node_id,
                policy_revision, result_status, error_code, created_at
            ) VALUES (%s, %s, 'headless', %s, %s, %s, %s, %s)
            """,
            (
                result.attempt_id,
                result.workflow_run_id,
                result.runtime_node_id,
                result.policy_revision,
                result_status,
                error_code,
                self._iso(result.created_at),
            ),
        )
        self.db.commit()

    def _record_headless_failure(
        self,
        *,
        attempt_id: str,
        placement_context: RuntimePlacementContext,
        error: ReconcileError,
        created_at: datetime,
    ) -> None:
        self.db.execute(
            """
            INSERT INTO runtime_plugin_reconcile_attempts (
                attempt_id, workflow_run_id, reconcile_path, runtime_node_id,
                policy_revision, stderr_summary, result_status, error_code,
                created_at
            ) VALUES (%s, %s, 'headless', %s, %s, %s, 'failed', %s, %s)
            """,
            (
                attempt_id,
                placement_context.workflow_run_id,
                placement_context.runtime_node_id,
                placement_context.policy_revision,
                self._sanitize_text(error.summary, 512),
                error.code,
                self._iso(created_at),
            ),
        )
        self.db.commit()

    def _persist_receipt(
        self,
        receipt: RuntimeLoadReceipt,
        activation_updates: list[tuple[str, str]],
    ) -> None:
        if self.db.in_transaction:
            raise RuntimeError("receipt persistence requires a clean transaction boundary")
        try:
            self.db.execute("BEGIN")
            self.db.execute(
                """
                INSERT INTO runtime_load_receipts (
                    receipt_id, workflow_run_id, runtime_plugin_lock_id,
                    runtime_plugin_lock_digest, runtime_environment_id,
                    runtime_pool_id, distribution_mode, runtime_node_id,
                    artifact_set_hash, policy_revision, deployment_tier,
                    scope, readiness_state, required_entries_ready, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    receipt.receipt_id,
                    receipt.workflow_run_id,
                    receipt.runtime_plugin_lock_id,
                    receipt.runtime_plugin_lock_digest,
                    receipt.runtime_environment_id,
                    receipt.runtime_pool_id,
                    receipt.distribution_mode,
                    receipt.runtime_node_id,
                    receipt.artifact_set_hash,
                    receipt.policy_revision,
                    receipt.deployment_tier,
                    receipt.scope,
                    receipt.readiness_state,
                    int(receipt.required_entries_ready),
                    self._iso(receipt.created_at),
                ),
            )
            for entry in receipt.entries:
                self.db.execute(
                    """
                    INSERT INTO runtime_load_receipt_entries (
                        receipt_id, claude_code_plugin_id, resolved_version,
                        artifact_digest, materialized_digest, verification_status,
                        signature_bundle_ref, retention_state, restore_source_ref,
                        required, loaded_capabilities_json, load_status, loaded_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        receipt.receipt_id,
                        entry.claude_code_plugin_id,
                        entry.resolved_version,
                        entry.artifact_digest,
                        entry.materialized_digest,
                        entry.verification_status,
                        entry.signature_bundle_ref,
                        entry.retention_state,
                        entry.restore_source_ref,
                        int(entry.required),
                        json.dumps(entry.loaded_capabilities, separators=(",", ":")),
                        entry.load_status,
                        self._iso(entry.loaded_at),
                    ),
                )
            for activation_status, materialization_id in activation_updates:
                self.db.execute(
                    """
                    UPDATE runtime_plugin_materializations
                    SET activation_status = %s, updated_at = %s
                    WHERE runtime_materialization_id = %s
                    """,
                    (activation_status, self._iso(self._clock()), materialization_id),
                )
            self.db.commit()
        except Exception:
            if self.db.in_transaction:
                self.db.rollback()
            raise

    def _sanitize_output(self, content: bytes) -> str:
        decoded = content.decode("utf-8", errors="replace")
        return self._sanitize_text(decoded, min(self._max_cli_output_bytes, 1024))

    @staticmethod
    def _sanitize_text(value: str, limit: int) -> str:
        value = re.sub(
            r"(?i)(token|secret|password|authorization)\s*[:=]\s*\S+",
            r"\1=[REDACTED]",
            value,
        )
        value = re.sub(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]+", "Bearer [REDACTED]", value)
        return value[:limit]

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
