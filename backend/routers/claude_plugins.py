"""Settings → Plugins: shared Claude Code plugin administration API.

[Input] Authenticated Dream users, manual package specs or Admin-approved
Marketplace entry IDs, and shared ClaudePlugin services.
[Output] One global catalog plus public install/operation/installation/Deck-ref
routes with terminal, client-safe errors.
[Pos] Thin FastAPI boundary; catalog governance stays in Admin and install
orchestration stays in focused services.
[Sync] 2026-08-19: add exact entry-ID Marketplace installs and guarantee
background failures leave the queued operation in an error terminal state.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator

import database

from .deps import get_current_user

try:
    from services.errors.error_registry import build_error_payload
    from services.claude_plugin.install_service import (
        PLUGIN_CLI_UNAVAILABLE,
        PLUGIN_INSTALL_FAILED,
        PLUGIN_MANIFEST_INVALID,
        PLUGIN_SPEC_INVALID,
        PLUGIN_SOURCE_UNKNOWN,
        PluginInstallError,
        PluginInstallService,
    )
    from services.claude_plugin.deck_refs_service import (
        DeckPluginRefError,
        DeckPluginRefService,
    )
    from services.claude_plugin.marketplace_service import (
        MARKETPLACE_CAPABILITY_MISSING,
        MARKETPLACE_ENTRY_NOT_FOUND,
        MARKETPLACE_ENTRY_UNAVAILABLE,
        MARKETPLACE_REMOTE_DRIFT,
        MarketplaceCatalogError,
        MarketplaceCatalogService,
    )
except ModuleNotFoundError:
    from backend.services.errors.error_registry import build_error_payload
    from backend.services.claude_plugin.install_service import (
        PLUGIN_CLI_UNAVAILABLE,
        PLUGIN_INSTALL_FAILED,
        PLUGIN_MANIFEST_INVALID,
        PLUGIN_SPEC_INVALID,
        PLUGIN_SOURCE_UNKNOWN,
        PluginInstallError,
        PluginInstallService,
    )
    from backend.services.claude_plugin.deck_refs_service import (
        DeckPluginRefError,
        DeckPluginRefService,
    )
    from backend.services.claude_plugin.marketplace_service import (
        MARKETPLACE_CAPABILITY_MISSING,
        MARKETPLACE_ENTRY_NOT_FOUND,
        MARKETPLACE_ENTRY_UNAVAILABLE,
        MARKETPLACE_REMOTE_DRIFT,
        MarketplaceCatalogError,
        MarketplaceCatalogService,
    )


router = APIRouter(tags=["claude-plugins"])

_ERROR_STATUS = {
    PLUGIN_SPEC_INVALID: 422,
    PLUGIN_SOURCE_UNKNOWN: 422,
    PLUGIN_MANIFEST_INVALID: 422,
    PLUGIN_CLI_UNAVAILABLE: 503,
    PLUGIN_INSTALL_FAILED: 502,
    MARKETPLACE_CAPABILITY_MISSING: 503,
    MARKETPLACE_ENTRY_NOT_FOUND: 404,
    MARKETPLACE_ENTRY_UNAVAILABLE: 409,
    MARKETPLACE_REMOTE_DRIFT: 409,
    "CLAUDE_PLUGIN_NOT_FOUND": 404,
}


def _error_response(exc: PluginInstallError) -> JSONResponse:
    status = _ERROR_STATUS.get(exc.code, 500)
    return JSONResponse(
        status_code=status,
        content=build_error_payload(exc.code),
    )


def _require_authenticated(current_user: dict[str, Any]) -> JSONResponse | None:
    """Any authenticated user may read and manage plugins."""
    if current_user.get("user_id") is not None:
        return None
    return JSONResponse(
        status_code=403,
        content=build_error_payload("WORKFLOW_PERMISSION_DENIED"),
    )


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class InstallRequest(_Strict):
    package_spec: str | None = Field(default=None, min_length=3, max_length=300)
    marketplace_entry_id: str | None = Field(
        default=None, min_length=3, max_length=160
    )
    source_type: Literal["claude-official", "marketplace", "platform-builtin"] | None = None

    @model_validator(mode="after")
    def require_exactly_one_source(self) -> "InstallRequest":
        if (self.package_spec is None) == (self.marketplace_entry_id is None):
            raise ValueError(
                "exactly one of package_spec or marketplace_entry_id is required"
            )
        if self.marketplace_entry_id is not None and self.source_type is not None:
            raise ValueError("source_type is resolved by marketplace_entry_id")
        return self


class DeckRefsPutRequest(_Strict):
    refs: list[dict[str, Any]] = Field(default_factory=list, max_length=32)


def _run_install(
    operation_id: str,
    package_spec: str,
    source_type: str,
    marketplace_entry_id: str | None = None,
) -> None:
    """Background task: real CLI install on a fresh DB connection."""
    db = database.get_db()

    def finish_error(code: str, summary: str) -> None:
        now = datetime.now(UTC).isoformat()
        db.execute(
            """
            UPDATE claude_plugin_operations SET
                status = 'error', phase = 'error', progress = 100,
                message = %s, error_code = %s, error_summary = %s,
                updated_at = %s, finished_at = %s
            WHERE id = %s AND status IN ('queued', 'running')
            """,
            (summary, code, summary, now, now, operation_id),
        )
        db.commit()

    try:
        marketplace_entry = (
            MarketplaceCatalogService(db).resolve_install_source(
                marketplace_entry_id
            )
            if marketplace_entry_id is not None
            else None
        )
        PluginInstallService(db).install(
            package_spec,
            source_type=source_type or None,
            marketplace_entry=marketplace_entry,
            operation_id=operation_id,
        )
    except MarketplaceCatalogError as exc:
        finish_error(exc.code, str(exc))
    except PluginInstallError as exc:
        # The install service normally owns the terminal evidence. This
        # conditional update also covers validation failures before it starts.
        finish_error(exc.code, str(exc))
    except Exception:  # noqa: BLE001 - never let a background task die silently
        import logging

        finish_error(
            PLUGIN_INSTALL_FAILED,
            "ClaudePlugin install background task failed unexpectedly",
        )
        logging.getLogger(__name__).exception(
            "claude plugin install background task crashed for %s", package_spec
        )
    finally:
        db.close()


@router.get("/api/claude-plugins/installations")
async def list_installations(current_user: dict = Depends(get_current_user)):
    denied = _require_authenticated(current_user)
    if denied is not None:
        return denied
    db = database.get_db()
    try:
        service = PluginInstallService(db)
        installations = service.list_installations()
        ref_counts = {
            row[0]: row[1]
            for row in db.execute(
                "SELECT plugin_installation_id, COUNT(*) FROM deck_claude_plugin_refs "
                "GROUP BY plugin_installation_id"
            ).fetchall()
        }
        for item in installations:
            item["deck_ref_count"] = ref_counts.get(item["id"], 0)
        return {
            "installations": installations,
            "permissions": {"can_manage_shared_plugins": True},
        }
    finally:
        db.close()


@router.get("/api/claude-plugins/marketplace")
async def list_marketplace(current_user: dict = Depends(get_current_user)):
    denied = _require_authenticated(current_user)
    if denied is not None:
        return denied
    db = database.get_db()
    try:
        try:
            entries = MarketplaceCatalogService(db).list_entries()
        except MarketplaceCatalogError as exc:
            return JSONResponse(
                status_code=_ERROR_STATUS.get(exc.code, 503),
                content=build_error_payload(exc.code),
            )
        return {
            "entries": entries,
            "scope": "platform-global",
            "permissions": {"can_install_shared_plugins": True},
        }
    finally:
        db.close()


@router.post("/api/claude-plugins/install", status_code=202)
async def install_plugin(
    request: InstallRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    denied = _require_authenticated(current_user)
    if denied is not None:
        return denied
    package_spec = request.package_spec
    if request.marketplace_entry_id is not None:
        db = database.get_db()
        try:
            try:
                resolved_entry = MarketplaceCatalogService(db).resolve_install_source(
                    request.marketplace_entry_id
                )
            except MarketplaceCatalogError as exc:
                return JSONResponse(
                    status_code=_ERROR_STATUS.get(exc.code, 503),
                    content=build_error_payload(exc.code),
                )
            package_spec = resolved_entry.package_spec
        finally:
            db.close()
    assert package_spec is not None
    try:
        from services.claude_plugin.package_spec import (
            PackageSpecError,
            parse_package_spec,
        )
    except ModuleNotFoundError:
        from backend.services.claude_plugin.package_spec import (
            PackageSpecError,
            parse_package_spec,
        )
    try:
        parse_package_spec(package_spec)
    except PackageSpecError:
        return JSONResponse(
            status_code=422,
            content=build_error_payload("CLAUDE_PLUGIN_SPEC_INVALID"),
        )
    # Pre-create the queued operation row so the client can poll immediately.
    operation_id = f"cop_{uuid.uuid4().hex}"
    now = datetime.now(UTC).isoformat()
    db = database.get_db()
    try:
        if request.marketplace_entry_id is not None:
            db.execute(
                """
                INSERT INTO claude_plugin_operations (
                    id, operation_kind, requested_package_spec,
                    marketplace_entry_id, status, phase, progress, message,
                    created_at, updated_at
                ) VALUES (%s, 'install', %s, %s, 'queued', 'queued', 0, %s, %s, %s)
                """,
                (
                    operation_id,
                    package_spec,
                    request.marketplace_entry_id,
                    "Queued for approved Marketplace install",
                    now,
                    now,
                ),
            )
        else:
            db.execute(
                """
                INSERT INTO claude_plugin_operations (
                    id, operation_kind, requested_package_spec, status, phase,
                    progress, message, created_at, updated_at
                ) VALUES (%s, 'install', %s, 'queued', 'queued', 0, %s, %s, %s)
                """,
                (
                    operation_id,
                    package_spec,
                    "Queued for real claude plugin install",
                    now,
                    now,
                ),
            )
        db.commit()
    finally:
        db.close()
    background_tasks.add_task(
        _run_install,
        operation_id,
        package_spec,
        "marketplace" if request.marketplace_entry_id else request.source_type or "",
        request.marketplace_entry_id,
    )
    return {
        "accepted": True,
        "operation_id": operation_id,
        "package_spec": package_spec,
        "marketplace_entry_id": request.marketplace_entry_id,
    }


@router.get("/api/claude-plugins/operations")
async def list_operations(
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
):
    denied = _require_authenticated(current_user)
    if denied is not None:
        return denied
    db = database.get_db()
    try:
        cursor = db.execute(
            "SELECT * FROM claude_plugin_operations ORDER BY created_at DESC LIMIT %s",
            (max(1, min(limit, 100)),),
        )
        columns = [desc[0] for desc in cursor.description]
        return {"operations": [dict(zip(columns, row)) for row in cursor.fetchall()]}
    finally:
        db.close()


@router.get("/api/claude-plugins/operations/{operation_id}")
async def get_operation(operation_id: str, current_user: dict = Depends(get_current_user)):
    denied = _require_authenticated(current_user)
    if denied is not None:
        return denied
    db = database.get_db()
    try:
        operation = PluginInstallService(db).get_operation(operation_id)
        if operation is None:
            return JSONResponse(
                status_code=404,
                content=build_error_payload("CLAUDE_PLUGIN_OPERATION_NOT_FOUND"),
            )
        return operation
    finally:
        db.close()


@router.get("/api/claude-plugins/installations/{installation_id}")
async def get_installation(installation_id: str, current_user: dict = Depends(get_current_user)):
    denied = _require_authenticated(current_user)
    if denied is not None:
        return denied
    db = database.get_db()
    try:
        record = PluginInstallService(db).get_installation(installation_id)
        if record is None:
            return JSONResponse(
                status_code=404,
                content=build_error_payload("CLAUDE_PLUGIN_NOT_FOUND"),
            )
        refs = db.execute(
            "SELECT deck_id, enabled, order_index FROM deck_claude_plugin_refs "
            "WHERE plugin_installation_id = %s",
            (installation_id,),
        ).fetchall()
        record["deck_refs"] = [
            {"deck_id": row[0], "enabled": bool(row[1]), "order_index": row[2]}
            for row in refs
        ]
        return record
    finally:
        db.close()


@router.post("/api/claude-plugins/installations/{installation_id}/uninstall")
async def uninstall_plugin(installation_id: str, current_user: dict = Depends(get_current_user)):
    denied = _require_authenticated(current_user)
    if denied is not None:
        return denied
    db = database.get_db()
    try:
        try:
            return PluginInstallService(db).uninstall(installation_id)
        except PluginInstallError as exc:
            return _error_response(exc)
    finally:
        db.close()


@router.get("/api/decks/{deck_id}/claude-plugins")
async def list_deck_plugins(deck_id: str, current_user: dict = Depends(get_current_user)):
    db = database.get_db()
    try:
        try:
            refs = DeckPluginRefService(db).list_refs(deck_id, str(current_user["user_id"]))
        except DeckPluginRefError as exc:
            return JSONResponse(
                status_code=exc.status_code,
                content=build_error_payload(exc.code),
            )
        return {"deck_id": deck_id, "refs": refs}
    finally:
        db.close()


@router.put("/api/decks/{deck_id}/claude-plugins")
async def put_deck_plugins(
    deck_id: str,
    request: DeckRefsPutRequest,
    current_user: dict = Depends(get_current_user),
):
    db = database.get_db()
    try:
        try:
            refs = DeckPluginRefService(db).replace_refs(
                deck_id, str(current_user["user_id"]), request.refs
            )
        except DeckPluginRefError as exc:
            return JSONResponse(
                status_code=exc.status_code,
                content=build_error_payload(exc.code),
            )
        return {"deck_id": deck_id, "refs": refs}
    finally:
        db.close()
