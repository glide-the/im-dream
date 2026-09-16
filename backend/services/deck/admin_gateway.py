# [Input] Current Admin OAuth actor, Registry170-174 DTO client and server-published artifact targets.
# [Output] Existing Deck Plugin route projections after local byte/manifest verification and Admin apply.
# [Pos] Dream control adapter; it owns filesystem evidence but no SQL, ORM, transaction or policy state.
# [Sync] 2026-09-16: replace Dream PostgreSQL lifecycle persistence with the Admin DTO service.
"""Application adapter for Admin-owned Deck Plugin lifecycle operations."""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from starlette.concurrency import run_in_threadpool

try:
    from services.admin_data.deck_plugin_control_data import (
        AdminDeckPluginControlData,
        DeckPluginControlApplyInputDTO,
        DeckPluginControlCommandDTO,
        DeckPluginControlEvidenceDTO,
        DeckPluginControlListInputDTO,
        DeckPluginControlPlanDTO,
        DeckPluginControlReadinessInputDTO,
        DeckPluginControlVersionInputDTO,
    )
    from services.admin_data.errors import AdminDataError
    from services.admin_data.request_auth import AdminRequestActor, AdminRequestAuth
    from services.claude_plugin.install_service import PluginInstallError, read_manifest
    from services.deck.builtin_plugin import (
        plugin_artifact_digest,
        resolve_builtin_source,
    )
    from services.errors.error_registry import ApiRouteError, registered_error_codes
except ModuleNotFoundError:  # pragma: no cover - package import compatibility
    from backend.services.admin_data.deck_plugin_control_data import (
        AdminDeckPluginControlData,
        DeckPluginControlApplyInputDTO,
        DeckPluginControlCommandDTO,
        DeckPluginControlEvidenceDTO,
        DeckPluginControlListInputDTO,
        DeckPluginControlPlanDTO,
        DeckPluginControlReadinessInputDTO,
        DeckPluginControlVersionInputDTO,
    )
    from backend.services.admin_data.errors import AdminDataError
    from backend.services.admin_data.request_auth import (
        AdminRequestActor,
        AdminRequestAuth,
    )
    from backend.services.claude_plugin.install_service import (
        PluginInstallError,
        read_manifest,
    )
    from backend.services.deck.builtin_plugin import (
        plugin_artifact_digest,
        resolve_builtin_source,
    )
    from backend.services.errors.error_registry import (
        ApiRouteError,
        registered_error_codes,
    )


def _registered_claude_plugin_path(plugin_id: str, version: str) -> Path | None:
    """Resolve only a CLI-managed install contained by the server cache root."""

    try:
        from services.claude_plugin import runtime as plugin_runtime
    except ModuleNotFoundError:  # pragma: no cover - package import compatibility
        from backend.services.claude_plugin import runtime as plugin_runtime

    registry = plugin_runtime.get_cli_registry_path()
    cache_root = plugin_runtime.get_cli_cache_root().resolve()
    try:
        payload = json.loads(registry.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    records: Any = payload.get("plugins", payload) if isinstance(payload, dict) else {}
    candidates = records.get(plugin_id, []) if isinstance(records, dict) else []
    if isinstance(candidates, dict):
        candidates = [candidates]
    if not isinstance(candidates, list):
        return None
    for record in candidates:
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
        return builtin.resolve()
    return _registered_claude_plugin_path(
        entry.claude_code_plugin_id,
        entry.resolved_version,
    )


_ADMIN_ERROR_MAP: dict[str, tuple[str, int | None]] = {
    "DECK_PLUGIN_RELEASE_UNAVAILABLE": ("DECK_PLUGIN_UNAVAILABLE", 404),
    "DECK_PLUGIN_RUNTIME_NOT_READY": ("RUNTIME_PLUGIN_NOT_READY", 409),
    "DECK_PLUGIN_RUNTIME_EVIDENCE_INVALID": ("DECK_PLUGIN_INTEGRITY_FAILED", 409),
    "DECK_PLUGIN_CONCURRENT_MODIFICATION": ("IDEMPOTENCY_CONFLICT", 409),
    "DECK_PLUGIN_INSTALLATION_CONFLICT": ("IDEMPOTENCY_CONFLICT", 409),
    "DECK_PLUGIN_INVALID_TRANSITION": ("DECK_RUNTIME_CONFIG_INVALID", 409),
    "DECK_PLUGIN_ROLLBACK_BLOCKED": ("DECK_RUNTIME_CONFIG_INVALID", 409),
    "DECK_PLUGIN_PURGE_RETENTION_BLOCKED": ("DECK_RUNTIME_CONFIG_INVALID", 409),
    "DECK_PLUGIN_CONTROL_DATA_INVALID": ("DECK_RUNTIME_CONFIG_UNAVAILABLE", 503),
    "DREAM_PRINCIPAL_DISABLED": ("WORKFLOW_PERMISSION_DENIED", 403),
    "DREAM_SCOPE_REQUIRED": ("WORKFLOW_PERMISSION_DENIED", 403),
    "OPERATION_UNAVAILABLE": ("DECK_RUNTIME_CONFIG_UNAVAILABLE", 503),
    "ADMIN_CAPABILITY_UNAVAILABLE": ("DECK_RUNTIME_CONFIG_UNAVAILABLE", 503),
    "ADMIN_RESPONSE_INVALID": ("DECK_RUNTIME_CONFIG_UNAVAILABLE", 503),
    "ADMIN_WRITE_RESULT_UNKNOWN": ("DECK_RUNTIME_CONFIG_UNAVAILABLE", 503),
}


def _route_error(error: AdminDataError) -> ApiRouteError:
    if error.outcome_unknown:
        return ApiRouteError("DECK_RUNTIME_CONFIG_UNAVAILABLE", status_code=503)
    public_code, status = _ADMIN_ERROR_MAP.get(
        error.code,
        (
            error.code
            if error.code in registered_error_codes()
            else "DECK_RUNTIME_CONFIG_UNAVAILABLE",
            None,
        ),
    )
    return ApiRouteError(public_code, status_code=status or error.status_code)


class DeckPluginAdminService:
    """Orchestrate Admin plan/apply while Dream verifies local shared bytes."""

    def __init__(
        self,
        data: AdminDeckPluginControlData,
        *,
        request_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._data = data
        self._request_id_factory = request_id_factory or (lambda: str(uuid.uuid4()))

    async def _admin_call(self, function, *args, **kwargs):
        try:
            return await run_in_threadpool(function, *args, **kwargs)
        except AdminDataError as error:
            raise _route_error(error) from None

    @staticmethod
    def _runtime_evidence(
        plan: DeckPluginControlPlanDTO,
    ) -> list[DeckPluginControlEvidenceDTO]:
        if not plan.requires_runtime_evidence:
            return []
        target = plan.runtime_target
        if target is None:
            raise ApiRouteError("DECK_RUNTIME_CONFIG_INVALID", status_code=409)
        evidence: list[DeckPluginControlEvidenceDTO] = []
        for entry in target.entries:
            path = _entry_path(entry)
            if path is None or not path.is_dir():
                raise ApiRouteError("RUNTIME_PLUGIN_NOT_READY", status_code=409)
            try:
                resolved = path.resolve(strict=True)
                digest = plugin_artifact_digest(resolved)
                has_manifest = read_manifest(resolved) is not None
            except (OSError, ValueError, PluginInstallError):
                raise ApiRouteError(
                    "DECK_PLUGIN_INTEGRITY_FAILED", status_code=409
                ) from None
            if digest != entry.artifact_digest:
                raise ApiRouteError(
                    "DECK_PLUGIN_INTEGRITY_FAILED", status_code=409
                )
            if not has_manifest:
                raise ApiRouteError("RUNTIME_PLUGIN_NOT_READY", status_code=409)
            evidence.append(
                DeckPluginControlEvidenceDTO(
                    claude_code_plugin_id=entry.claude_code_plugin_id,
                    resolved_version=entry.resolved_version,
                    artifact_digest=entry.artifact_digest,
                    materialized_digest=digest,
                    cache_ref=str(resolved),
                    has_manifest=True,
                )
            )
        return evidence

    async def _plan_apply(
        self,
        command: DeckPluginControlCommandDTO,
        *,
        actor: AdminRequestActor,
        request_id: str | None = None,
    ):
        plan = await self._admin_call(
            self._data.plan,
            command,
            self._request_id_factory(),
            access_token=actor.access_token,
        )
        evidence = await run_in_threadpool(self._runtime_evidence, plan)
        return await self._admin_call(
            self._data.apply,
            DeckPluginControlApplyInputDTO(plan=plan, evidence=evidence),
            request_id or self._request_id_factory(),
            access_token=actor.access_token,
        )

    async def list_installations(
        self,
        *,
        scope_type: str,
        scope_id: str,
        actor: AdminRequestActor,
    ):
        return await self._admin_call(
            self._data.list,
            DeckPluginControlListInputDTO(
                scope_type=scope_type,
                scope_id=scope_id,
            ),
            self._request_id_factory(),
            access_token=actor.access_token,
        )

    async def install(
        self,
        request: Any,
        *,
        actor: AdminRequestActor,
    ):
        return await self._plan_apply(
            DeckPluginControlCommandDTO(
                action="install",
                scope_type=request.scope_type,
                scope_id=request.scope_id,
                deck_plugin_id=request.deck_plugin_id,
                deck_plugin_version=request.version,
                source_type=request.source_type,
                source=request.source,
            ),
            actor=actor,
            request_id=(
                "deck-plugin-install:"
                + hashlib.sha256(request.idempotency_key.encode("utf-8")).hexdigest()
            ),
        )

    async def get_version(
        self,
        deck_plugin_id: str,
        version: str,
        *,
        scope_type: str,
        scope_id: str,
        actor: AdminRequestActor,
    ):
        return await self._admin_call(
            self._data.version,
            DeckPluginControlVersionInputDTO(
                scope_type=scope_type,
                scope_id=scope_id,
                deck_plugin_id=deck_plugin_id,
                deck_plugin_version=version,
            ),
            self._request_id_factory(),
            access_token=actor.access_token,
        )

    async def _lifecycle(
        self,
        deck_plugin_id: str,
        request: Any,
        *,
        action: str,
        actor: AdminRequestActor,
    ):
        fields: dict[str, Any] = {
            "action": action,
            "scope_type": request.scope_type,
            "scope_id": request.scope_id,
            "deck_plugin_id": deck_plugin_id,
        }
        if action == "disable":
            fields["reason"] = request.reason
        elif action in {"upgrade", "rollback"}:
            fields["target_version"] = request.target_version
        elif action == "uninstall":
            fields["purge"] = request.purge
        return await self._plan_apply(
            DeckPluginControlCommandDTO(**fields),
            actor=actor,
        )

    async def enable(self, deck_plugin_id: str, request: Any, *, actor: AdminRequestActor):
        return await self._lifecycle(deck_plugin_id, request, action="enable", actor=actor)

    async def disable(self, deck_plugin_id: str, request: Any, *, actor: AdminRequestActor):
        return await self._lifecycle(deck_plugin_id, request, action="disable", actor=actor)

    async def upgrade(self, deck_plugin_id: str, request: Any, *, actor: AdminRequestActor):
        return await self._lifecycle(deck_plugin_id, request, action="upgrade", actor=actor)

    async def rollback(self, deck_plugin_id: str, request: Any, *, actor: AdminRequestActor):
        return await self._lifecycle(deck_plugin_id, request, action="rollback", actor=actor)

    async def uninstall(self, deck_plugin_id: str, request: Any, *, actor: AdminRequestActor):
        return await self._lifecycle(deck_plugin_id, request, action="uninstall", actor=actor)

    async def approve_upgrade(self, deck_plugin_id: str, request: Any, *, actor: AdminRequestActor):
        return await self._lifecycle(deck_plugin_id, request, action="approve_upgrade", actor=actor)

    async def reject_upgrade(self, deck_plugin_id: str, request: Any, *, actor: AdminRequestActor):
        return await self._lifecycle(deck_plugin_id, request, action="reject_upgrade", actor=actor)

    async def runtime_readiness(
        self,
        deck_plugin_id: str,
        *,
        scope_type: str,
        scope_id: str,
        environment: str,
        actor: AdminRequestActor,
    ):
        del environment
        return await self._admin_call(
            self._data.readiness,
            DeckPluginControlReadinessInputDTO(
                scope_type=scope_type,
                scope_id=scope_id,
                deck_plugin_id=deck_plugin_id,
            ),
            self._request_id_factory(),
            access_token=actor.access_token,
        )

    async def reconcile(self, deck_plugin_id: str, request: Any, *, actor: AdminRequestActor):
        return await self._lifecycle(deck_plugin_id, request, action="reconcile", actor=actor)


def get_deck_plugin_admin_service(owner: AdminRequestAuth) -> DeckPluginAdminService:
    """Bind the request's authenticated Admin client to the control adapter."""

    return DeckPluginAdminService(AdminDeckPluginControlData(owner.client))
