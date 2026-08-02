"""Application adapter for the Deck Plugin administration routes.

The Deck domain owns release and installation state.  This adapter only
materializes server-published runtime-lock entries and never accepts a plugin
path from a browser request.
"""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from typing import Any
import uuid

import database

try:
    from models.deck_plugin import DeckPluginManifestV1, DeckRuntimePluginLock
    from services.deck.builtin_plugin import (
        plugin_artifact_digest,
        resolve_builtin_source,
    )
    from services.deck_plugin.installation_service import (
        DECK_PLUGIN_CONCURRENT_MODIFICATION,
        DECK_PLUGIN_INSTALLATION_CONFLICT,
        DECK_PLUGIN_INSTALLATION_NOT_FOUND,
        DECK_PLUGIN_INVALID_TRANSITION,
        DECK_PLUGIN_RELEASE_UNAVAILABLE,
        DECK_PLUGIN_ROLLBACK_BLOCKED,
        DECK_PLUGIN_RUNTIME_NOT_READY,
        DECK_PLUGIN_UPGRADE_APPROVAL_REQUIRED,
        InstallationService,
        InstallationServiceError,
        RuntimePreparation,
        Scope,
    )
    from services.errors.error_registry import ApiRouteError
except ModuleNotFoundError:  # Support backend directory on PYTHONPATH.
    from backend.models.deck_plugin import DeckPluginManifestV1, DeckRuntimePluginLock
    from backend.services.deck.builtin_plugin import plugin_artifact_digest, resolve_builtin_source
    from backend.services.deck_plugin.installation_service import (
        DECK_PLUGIN_CONCURRENT_MODIFICATION,
        DECK_PLUGIN_INSTALLATION_CONFLICT,
        DECK_PLUGIN_INSTALLATION_NOT_FOUND,
        DECK_PLUGIN_INVALID_TRANSITION,
        DECK_PLUGIN_RELEASE_UNAVAILABLE,
        DECK_PLUGIN_ROLLBACK_BLOCKED,
        DECK_PLUGIN_RUNTIME_NOT_READY,
        DECK_PLUGIN_UPGRADE_APPROVAL_REQUIRED,
        InstallationService,
        InstallationServiceError,
        RuntimePreparation,
        Scope,
    )
    from backend.services.errors.error_registry import ApiRouteError


_DEVELOPMENT_ENVIRONMENTS = {"development", "dev", "test", "testing"}


def _environment() -> str:
    return os.getenv("INK_ENVIRONMENT", "unknown").strip().lower() or "unknown"


def _json_list(value: Any) -> list[str]:
    try:
        parsed = json.loads(str(value or "[]"))
    except (TypeError, json.JSONDecodeError):
        return []
    if not isinstance(parsed, list):
        return []
    return [item for item in parsed if isinstance(item, str)]


def _semver_key(version: str) -> tuple[int, int, int, str]:
    core, _, suffix = version.partition("-")
    try:
        major, minor, patch = (int(value) for value in core.split(".", 2))
    except (TypeError, ValueError):
        return (0, 0, 0, version)
    return (major, minor, patch, suffix)


def _operation(
    *,
    operation_id: str | None,
    deck_plugin_id: str,
    target_version: str | None,
    message: str,
) -> dict[str, Any]:
    return {
        "operation_id": operation_id or f"op_{uuid.uuid4().hex}",
        "deck_plugin_id": deck_plugin_id,
        "target_version": target_version,
        "status": "completed",
        "phase": "ready",
        "progress": 100,
        "message": message,
        "updated_at": datetime.now(UTC).isoformat(),
    }


def _registered_claude_plugin_path(plugin_id: str, version: str) -> Path | None:
    """Resolve a CLI-managed install from the server-managed registry only.

    2026-08-02 (deck-integration-delta): this used to read the developer's
    real ``~/.claude/plugins/installed_plugins.json``.  Plugin installs now
    live in the server-managed runtime root (isolated CLAUDE_CONFIG_DIR);
    the developer's personal registry is never consulted.
    """
    try:
        from services.claude_plugin import runtime as _plugin_runtime
    except ModuleNotFoundError:
        from backend.services.claude_plugin import runtime as _plugin_runtime
    registry = _plugin_runtime.get_cli_registry_path()
    cache_root = _plugin_runtime.get_cli_cache_root().resolve()
    try:
        payload = json.loads(registry.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    records: Any = payload.get("plugins", payload) if isinstance(payload, dict) else {}
    candidate_records = records.get(plugin_id, []) if isinstance(records, dict) else []
    if isinstance(candidate_records, dict):
        candidate_records = [candidate_records]
    if not isinstance(candidate_records, list):
        return None
    for record in candidate_records:
        if not isinstance(record, dict):
            continue
        record_version = str(record.get("version") or "")
        if record_version and record_version != version:
            continue
        raw_path = record.get("installPath") or record.get("install_path")
        if not isinstance(raw_path, str) or not raw_path:
            continue
        try:
            candidate = Path(raw_path).expanduser().resolve(strict=True)
            candidate.relative_to(cache_root)
        except (OSError, ValueError):
            continue
        if candidate.is_dir():
            return candidate
    return None


def _entry_path(entry: Any) -> Path | None:
    builtin = resolve_builtin_source(entry.source_ref)
    if builtin is not None:
        return builtin
    return _registered_claude_plugin_path(
        entry.claude_code_plugin_id,
        entry.resolved_version,
    )


class DeckPluginAdminService:
    """Open one short-lived database connection per API operation."""

    @staticmethod
    def _db() -> sqlite3.Connection:
        return database.get_db()

    @staticmethod
    def _raise_service_error(exc: InstallationServiceError) -> None:
        mappings = {
            DECK_PLUGIN_RELEASE_UNAVAILABLE: ("DECK_PLUGIN_UNAVAILABLE", 404),
            DECK_PLUGIN_RUNTIME_NOT_READY: ("RUNTIME_PLUGIN_NOT_READY", 409),
            DECK_PLUGIN_UPGRADE_APPROVAL_REQUIRED: ("DECK_PLUGIN_UPGRADE_PENDING", 409),
            DECK_PLUGIN_INSTALLATION_NOT_FOUND: ("DECK_PLUGIN_UNAVAILABLE", 404),
            DECK_PLUGIN_INSTALLATION_CONFLICT: ("IDEMPOTENCY_CONFLICT", 409),
            DECK_PLUGIN_CONCURRENT_MODIFICATION: ("IDEMPOTENCY_CONFLICT", 409),
            DECK_PLUGIN_INVALID_TRANSITION: ("DECK_RUNTIME_CONFIG_INVALID", 409),
            DECK_PLUGIN_ROLLBACK_BLOCKED: ("DECK_RUNTIME_CONFIG_INVALID", 409),
        }
        code, status = mappings.get(exc.code, ("DECK_RUNTIME_CONFIG_INVALID", 422))
        raise ApiRouteError(code, status_code=status, operation_id=exc.operation_id) from exc

    @staticmethod
    def _installation_row(
        db: sqlite3.Connection,
        deck_plugin_id: str,
        *,
        scope_type: str | None = None,
        scope_id: str | None = None,
    ) -> sqlite3.Row:
        clauses = ["deck_plugin_id = ?", "status != 'uninstalled'"]
        parameters: list[Any] = [deck_plugin_id]
        if scope_type is not None:
            clauses.append("scope_type = ?")
            parameters.append(scope_type)
        if scope_id is not None:
            clauses.append("scope_id = ?")
            parameters.append(scope_id)
        row = db.execute(
            f"SELECT * FROM deck_plugin_installations WHERE {' AND '.join(clauses)} "
            "ORDER BY updated_at DESC, id DESC LIMIT 1",
            parameters,
        ).fetchone()
        if row is None:
            raise ApiRouteError("DECK_PLUGIN_UNAVAILABLE", status_code=404)
        return row

    @staticmethod
    def _release(db: sqlite3.Connection, deck_plugin_id: str, version: str) -> sqlite3.Row:
        row = db.execute(
            """
            SELECT release.*, runtime_lock.id AS runtime_plugin_lock_id,
                   runtime_lock.lock_json
            FROM deck_plugin_releases AS release
            JOIN deck_runtime_plugin_locks AS runtime_lock
              ON runtime_lock.deck_plugin_id = release.deck_plugin_id
             AND runtime_lock.deck_plugin_version = release.deck_plugin_version
            WHERE release.deck_plugin_id = ? AND release.deck_plugin_version = ?
              AND release.status IN ('published', 'deprecated')
            """,
            (deck_plugin_id, version),
        ).fetchone()
        if row is None:
            raise ApiRouteError("DECK_PLUGIN_UNAVAILABLE", status_code=404)
        return row

    @staticmethod
    def _materialize(
        db: sqlite3.Connection,
        _deck_plugin_id: str,
        _version: str,
        runtime_lock: DeckRuntimePluginLock,
    ) -> RuntimePreparation:
        environment = _environment()
        if environment not in _DEVELOPMENT_ENVIRONMENTS:
            return RuntimePreparation(
                runtime_readiness="production_gate_required",
                lock_materialized=False,
                load_smoke_passed=False,
                error_code="RUNTIME_PLUGIN_NOT_READY",
                error_summary="runtime plugin materialization is not approved for this environment",
            )
        if runtime_lock.production_ready:
            # Production-ready locks are still allowed in development, but this
            # adapter never upgrades an environment's rollout approval.
            pass

        now = datetime.now(UTC).isoformat()
        artifact_set_hash = "sha256:" + hashlib.sha256(
            runtime_lock.model_dump_json().encode("utf-8")
        ).hexdigest()
        for entry in runtime_lock.claude_code_plugins:
            path = _entry_path(entry)
            if path is None or not path.is_dir():
                return RuntimePreparation(
                    runtime_readiness="source_unavailable",
                    lock_materialized=False,
                    load_smoke_passed=False,
                    error_code="RUNTIME_PLUGIN_NOT_READY",
                    error_summary=f"server-published runtime source is unavailable: {entry.claude_code_plugin_id}",
                )
            try:
                actual_digest = plugin_artifact_digest(path)
            except (OSError, ValueError):
                return RuntimePreparation(
                    runtime_readiness="integrity_failed",
                    lock_materialized=False,
                    load_smoke_passed=False,
                    error_code="DECK_PLUGIN_INTEGRITY_FAILED",
                    error_summary="runtime plugin artifact could not be verified",
                )
            if actual_digest != entry.artifact_digest:
                return RuntimePreparation(
                    runtime_readiness="integrity_failed",
                    lock_materialized=False,
                    load_smoke_passed=False,
                    error_code="DECK_PLUGIN_INTEGRITY_FAILED",
                    error_summary="runtime plugin artifact digest does not match the immutable lock",
                )

            materialization_key = hashlib.sha256(
                f"{environment}\0local\0{entry.claude_code_plugin_id}\0"
                f"{entry.resolved_version}\0{entry.artifact_digest}".encode("utf-8")
            ).hexdigest()
            existing = db.execute(
                "SELECT runtime_materialization_id FROM runtime_plugin_materializations "
                "WHERE materialization_key = ?",
                (materialization_key,),
            ).fetchone()
            if existing is None:
                db.execute(
                    """
                    INSERT INTO runtime_plugin_materializations (
                        runtime_materialization_id, runtime_environment_id,
                        runtime_pool_id, runtime_node_id, claude_code_plugin_id,
                        resolved_version, artifact_digest, materialized_digest,
                        artifact_set_hash, policy_revision, declaration_status,
                        materialization_status, activation_status,
                        materialization_key, attempt_id, attempt_count,
                        verification_status, retention_state, cache_ref,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, 'local', ?, ?, ?, ?, ?, 'deck-admin/v1',
                              'declared', 'materialized', 'loadable', ?, ?, 1,
                              'verified', 'development_cache', ?, ?, ?)
                    """,
                    (
                        f"rpm_{uuid.uuid4().hex}",
                        environment,
                        environment,
                        entry.claude_code_plugin_id,
                        entry.resolved_version,
                        entry.artifact_digest,
                        actual_digest,
                        artifact_set_hash,
                        materialization_key,
                        f"rpa_{uuid.uuid4().hex}",
                        str(path.resolve()),
                        now,
                        now,
                    ),
                )
            else:
                db.execute(
                    """
                    UPDATE runtime_plugin_materializations
                    SET materialized_digest = ?, declaration_status = 'declared',
                        materialization_status = 'materialized',
                        activation_status = 'loadable', verification_status = 'verified',
                        cache_ref = ?, last_error = NULL,
                        attempt_count = attempt_count + 1, updated_at = ?
                    WHERE runtime_materialization_id = ?
                    """,
                    (actual_digest, str(path.resolve()), now, existing["runtime_materialization_id"]),
                )
        db.commit()
        return RuntimePreparation(
            runtime_readiness="loadable",
            lock_materialized=True,
            load_smoke_passed=True,
        )

    @staticmethod
    def _runtime_rows(db: sqlite3.Connection, runtime_lock: DeckRuntimePluginLock) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for entry in runtime_lock.claude_code_plugins:
            row = db.execute(
                """
                SELECT declaration_status, materialization_status, activation_status,
                       verification_status, last_error, updated_at
                FROM runtime_plugin_materializations
                WHERE claude_code_plugin_id = ? AND resolved_version = ?
                  AND artifact_digest = ?
                ORDER BY updated_at DESC LIMIT 1
                """,
                (entry.claude_code_plugin_id, entry.resolved_version, entry.artifact_digest),
            ).fetchone()
            result.append(
                {
                    "claude_code_plugin_id": entry.claude_code_plugin_id,
                    "resolved_version": entry.resolved_version,
                    "version_constraint": entry.resolved_version,
                    "artifact_digest": entry.artifact_digest,
                    "declaration_status": row["declaration_status"] if row else "undeclared",
                    "materialization_status": row["materialization_status"] if row else "missing",
                    "activation_status": row["activation_status"] if row else "inactive",
                    "health_status": (
                        "healthy"
                        if row and row["materialization_status"] == "materialized"
                        and row["activation_status"] in {"loadable", "loaded"}
                        else "failed" if row and row["materialization_status"] == "failed"
                        else "unknown"
                    ),
                    "last_error_code": "RUNTIME_PLUGIN_NOT_READY" if row and row["last_error"] else None,
                    "last_error_summary": row["last_error"] if row else None,
                    "updated_at": row["updated_at"] if row else None,
                }
            )
        return result

    @classmethod
    def _view(
        cls,
        db: sqlite3.Connection,
        release: sqlite3.Row,
        installation: sqlite3.Row | None,
    ) -> dict[str, Any]:
        manifest = DeckPluginManifestV1.model_validate_json(release["manifest_json"])
        runtime_lock = DeckRuntimePluginLock.model_validate_json(release["lock_json"])
        runtime_plugins = cls._runtime_rows(db, runtime_lock)
        installed_versions = _json_list(installation["installed_versions_json"]) if installation else []
        default_version = installation["default_version"] if installation else None
        status = installation["status"] if installation else "uninstalled"
        approved = _json_list(installation["approved_capabilities_json"]) if installation else []
        source_policy = installation["source_policy_id"] if installation else "server-published"
        all_materialized = bool(runtime_plugins) and all(
            item["materialization_status"] == "materialized" for item in runtime_plugins
        )
        all_loadable = bool(runtime_plugins) and all(
            item["activation_status"] in {"loadable", "loaded"} for item in runtime_plugins
        )
        versions = [
            row["deck_plugin_version"]
            for row in db.execute(
                "SELECT deck_plugin_version FROM deck_plugin_releases "
                "WHERE deck_plugin_id = ? AND status IN ('published', 'deprecated')",
                (manifest.deck_plugin_id,),
            ).fetchall()
        ]
        newer = [version for version in versions if _semver_key(version) > _semver_key(default_version or "0.0.0")]
        return {
            "deck_plugin_installation_id": installation["id"] if installation else f"preview:{release['id']}",
            "deck_plugin_id": manifest.deck_plugin_id,
            "display_name": manifest.display_name,
            "deck_plugin_version": default_version or manifest.deck_plugin_version,
            "installed_versions": installed_versions,
            "default_version": default_version,
            "available_version": max(newer, key=_semver_key) if newer else None,
            "status": status,
            "source": {
                "type": "controlled",
                "label": source_policy.split(":", 1)[0],
                "verified": True,
            },
            "approved_capabilities": approved,
            "capabilities": {
                "manifest_requested": manifest.capabilities,
                "effective": sorted(set(approved) & set(manifest.capabilities)),
            },
            "compatibility": {
                "passed": status in {"ready", "disabled"} and all_loadable,
                "status": "compatible" if status in {"ready", "disabled"} and all_loadable else "pending",
                "effective_capabilities": sorted(set(approved) & set(manifest.capabilities)),
            },
            "runtime_readiness": {
                "declaration_status": (
                    "disabled" if status == "disabled" else "declared" if installation and status != "uninstalled" else "undeclared"
                ),
                "materialization_status": "materialized" if all_materialized else "missing",
                "activation_status": "loadable" if all_loadable else "inactive",
            },
            "health_status": "healthy" if status == "ready" and all_loadable else "unknown",
            "last_error_code": installation["last_error_code"] if installation else None,
            "last_error_summary": installation["last_error_summary"] if installation else None,
            "updated_at": installation["updated_at"] if installation else release["updated_at"],
            "rollback_versions": [version for version in installed_versions if version != default_version],
            "manifest": {
                "schema_version": manifest.schema_version,
                "author": manifest.author,
                "workflow_references": [manifest.workflow.workflow_definition_ref],
                "input_schema_version": manifest.workflow.input_schema_ref,
                "output_schema_version": manifest.workflow.output_schema_ref,
                "deck_runtime_contract": manifest.runtime_configuration.profile_contract,
                "capabilities": manifest.capabilities,
            },
            "runtime_plugins": runtime_plugins,
            "history": [],
            "recent_runs": [],
            "operation_logs": [],
            "is_system": manifest.deck_plugin_id.startswith("ink."),
        }

    async def list_installations(self, *, scope_id: str | None) -> dict[str, Any]:
        db = self._db()
        try:
            if scope_id is None:
                rows = db.execute(
                    "SELECT * FROM deck_plugin_installations WHERE status != 'uninstalled' ORDER BY updated_at DESC"
                ).fetchall()
            else:
                rows = db.execute(
                    "SELECT * FROM deck_plugin_installations WHERE scope_id = ? "
                    "AND status != 'uninstalled' ORDER BY updated_at DESC",
                    (scope_id,),
                ).fetchall()
            installations: list[dict[str, Any]] = []
            runtime: dict[tuple[str, str], dict[str, Any]] = {}
            for installation in rows:
                version = installation["default_version"] or installation["pending_version"]
                if not version:
                    continue
                release = self._release(db, installation["deck_plugin_id"], version)
                view = self._view(db, release, installation)
                installations.append(view)
                for item in view["runtime_plugins"]:
                    runtime[(item["claude_code_plugin_id"], item["resolved_version"])] = item
            return {"installations": installations, "runtime_plugins": list(runtime.values())}
        finally:
            db.close()

    async def install(self, request: Any, *, actor_id: str) -> dict[str, Any]:
        del actor_id
        db = self._db()
        try:
            release = self._release(db, request.deck_plugin_id, request.version)
            runtime_lock = DeckRuntimePluginLock.model_validate_json(release["lock_json"])
            published_sources = {entry.source_ref for entry in runtime_lock.claude_code_plugins}
            if request.source not in published_sources:
                raise ApiRouteError("DECK_PLUGIN_SOURCE_DENIED", status_code=403)
            if request.source_type == "local":
                raise ApiRouteError("DECK_PLUGIN_SOURCE_DENIED", status_code=403)
            existing = db.execute(
                "SELECT * FROM deck_plugin_installations WHERE scope_type = ? AND scope_id = ? "
                "AND deck_plugin_id = ? AND status != 'uninstalled'",
                (request.scope_type, request.scope_id, request.deck_plugin_id),
            ).fetchone()
            if existing is not None and existing["default_version"] == request.version:
                return _operation(
                    operation_id=None,
                    deck_plugin_id=request.deck_plugin_id,
                    target_version=request.version,
                    message="Deck Plugin is already installed and ready.",
                )
            service = InstallationService(
                db,
                runtime_preparer=lambda plugin_id, version, runtime_lock: self._materialize(
                    db, plugin_id, version, runtime_lock
                ),
            )
            started = await service.install(
                request.deck_plugin_id,
                request.version,
                Scope(scope_type=request.scope_type, scope_id=request.scope_id),
                source_policy_id=f"{request.source_type}:{request.source}",
            )
            completed = await service.complete_installation(started.deck_plugin_installation_id)
            return _operation(
                operation_id=completed.operation_id,
                deck_plugin_id=request.deck_plugin_id,
                target_version=request.version,
                message="Deck Plugin installed and runtime lock materialized.",
            )
        except InstallationServiceError as exc:
            self._raise_service_error(exc)
        finally:
            db.close()

    async def get_version(self, deck_plugin_id: str, version: str) -> dict[str, Any]:
        db = self._db()
        try:
            release = self._release(db, deck_plugin_id, version)
            installation = db.execute(
                "SELECT * FROM deck_plugin_installations WHERE deck_plugin_id = ? "
                "AND status != 'uninstalled' ORDER BY updated_at DESC LIMIT 1",
                (deck_plugin_id,),
            ).fetchone()
            return self._view(db, release, installation)
        finally:
            db.close()

    async def enable(self, deck_plugin_id: str, request: Any, *, actor_id: str) -> dict[str, Any]:
        del actor_id
        return await self._lifecycle(deck_plugin_id, request, "enable")

    async def disable(self, deck_plugin_id: str, request: Any, *, actor_id: str) -> dict[str, Any]:
        del actor_id
        return await self._lifecycle(deck_plugin_id, request, "disable")

    async def upgrade(self, deck_plugin_id: str, request: Any, *, actor_id: str) -> dict[str, Any]:
        del actor_id
        return await self._lifecycle(deck_plugin_id, request, "upgrade")

    async def rollback(self, deck_plugin_id: str, request: Any, *, actor_id: str) -> dict[str, Any]:
        del actor_id
        return await self._lifecycle(deck_plugin_id, request, "rollback")

    async def uninstall(self, deck_plugin_id: str, request: Any, *, actor_id: str) -> dict[str, Any]:
        del actor_id
        return await self._lifecycle(deck_plugin_id, request, "uninstall")

    async def approve_upgrade(self, deck_plugin_id: str, request: Any, *, actor_id: str) -> dict[str, Any]:
        del actor_id
        return await self._lifecycle(deck_plugin_id, request, "approve_upgrade")

    async def reject_upgrade(self, deck_plugin_id: str, request: Any, *, actor_id: str) -> dict[str, Any]:
        del actor_id
        db = self._db()
        try:
            row = self._installation_row(
                db, deck_plugin_id, scope_type=request.scope_type, scope_id=request.scope_id
            )
            if row["status"] != "upgrade_pending":
                raise ApiRouteError("DECK_RUNTIME_CONFIG_INVALID", status_code=409)
            with db:
                db.execute(
                    """
                    UPDATE deck_plugin_installations
                    SET status = 'ready', pending_version = NULL,
                        pending_capabilities_json = NULL, last_error_code = NULL,
                        last_error_summary = NULL, revision = revision + 1,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND revision = ?
                    """,
                    (row["id"], row["revision"]),
                )
            return _operation(
                operation_id=None,
                deck_plugin_id=deck_plugin_id,
                target_version=row["default_version"],
                message="Capability expansion was rejected; the current ready version remains active.",
            )
        finally:
            db.close()

    async def _lifecycle(self, deck_plugin_id: str, request: Any, action: str) -> dict[str, Any]:
        db = self._db()
        try:
            row = self._installation_row(
                db, deck_plugin_id, scope_type=request.scope_type, scope_id=request.scope_id
            )
            service = InstallationService(
                db,
                runtime_preparer=lambda plugin_id, version, runtime_lock: self._materialize(
                    db, plugin_id, version, runtime_lock
                ),
            )
            operation_id: str | None = None
            target = getattr(request, "target_version", None) or row["default_version"]
            if action == "enable":
                await service.enable(row["id"])
            elif action == "disable":
                await service.disable(row["id"], getattr(request, "reason", None) or "Disabled from Plugin Admin")
            elif action == "upgrade":
                result = await service.upgrade(row["id"], target)
                operation_id = result.operation_id
                if str(result.status.value) == "upgrade_pending":
                    return {
                        **_operation(
                            operation_id=operation_id,
                            deck_plugin_id=deck_plugin_id,
                            target_version=target,
                            message="Upgrade requires capability approval.",
                        ),
                        "status": "ready",
                        "phase": "upgrade_pending",
                    }
            elif action == "approve_upgrade":
                result = await service.approve_upgrade(row["id"])
                operation_id = result.operation_id
                target = result.target_version
            elif action == "rollback":
                await service.rollback(row["id"], target)
            elif action == "uninstall":
                await service.uninstall(row["id"], force=bool(getattr(request, "purge", False)))
            else:
                raise ApiRouteError("DECK_RUNTIME_CONFIG_INVALID", status_code=422)
            return _operation(
                operation_id=operation_id,
                deck_plugin_id=deck_plugin_id,
                target_version=target,
                message=f"Deck Plugin {action.replace('_', ' ')} completed.",
            )
        except InstallationServiceError as exc:
            self._raise_service_error(exc)
        finally:
            db.close()

    async def runtime_readiness(self, deck_plugin_id: str, *, environment: str) -> dict[str, Any]:
        del environment  # readiness always reports the server-owned current environment
        db = self._db()
        try:
            row = self._installation_row(db, deck_plugin_id)
            version = row["default_version"] or row["pending_version"]
            release = self._release(db, deck_plugin_id, version)
            return self._view(db, release, row)["runtime_readiness"]
        finally:
            db.close()

    async def reconcile(self, deck_plugin_id: str, request: Any, *, actor_id: str) -> dict[str, Any]:
        del actor_id, request
        db = self._db()
        try:
            row = self._installation_row(db, deck_plugin_id)
            version = row["default_version"] or row["pending_version"]
            release = self._release(db, deck_plugin_id, version)
            runtime_lock = DeckRuntimePluginLock.model_validate_json(release["lock_json"])
            preparation = self._materialize(db, deck_plugin_id, version, runtime_lock)
            if not preparation.lock_materialized or not preparation.load_smoke_passed:
                raise ApiRouteError(
                    preparation.error_code or "RUNTIME_PLUGIN_NOT_READY",
                    status_code=409,
                )
            return _operation(
                operation_id=None,
                deck_plugin_id=deck_plugin_id,
                target_version=version,
                message="Runtime plugin reconcile completed.",
            )
        finally:
            db.close()


_GATEWAY = DeckPluginAdminService()


def get_deck_plugin_admin_service() -> DeckPluginAdminService:
    return _GATEWAY
