"""Settings → Plugins: shared Claude Code plugin administration API.

Installs are executed by the real Claude CLI inside the server-managed
runtime root (never the developer's ``~/.claude``) and recorded with full
operation evidence.  Clients submit only a *package spec*
(``<plugin>@<marketplace>``) — never a filesystem path, never settings JSON,
never a ``--plugin-dir`` value.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

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


router = APIRouter(tags=["claude-plugins"])

_ERROR_STATUS = {
    PLUGIN_SPEC_INVALID: 422,
    PLUGIN_SOURCE_UNKNOWN: 422,
    PLUGIN_MANIFEST_INVALID: 422,
    PLUGIN_CLI_UNAVAILABLE: 503,
    PLUGIN_INSTALL_FAILED: 502,
    "CLAUDE_PLUGIN_NOT_FOUND": 404,
}


def _error_response(exc: PluginInstallError) -> JSONResponse:
    status = _ERROR_STATUS.get(exc.code, 500)
    return JSONResponse(
        status_code=status,
        content=build_error_payload(exc.code),
    )


def _permissions(current_user: dict[str, Any]) -> set[str]:
    raw = current_user.get("permissions", current_user.get("scopes", []))
    if isinstance(raw, str):
        return set(raw.split())
    return {str(item) for item in raw}


def _require_admin(current_user: dict[str, Any]) -> JSONResponse | None:
    if current_user.get("role") == "admin":
        return None
    if _permissions(current_user).intersection({"plugin:admin"}):
        return None
    return JSONResponse(
        status_code=403,
        content=build_error_payload("WORKFLOW_PERMISSION_DENIED"),
    )


def _require_reader(current_user: dict[str, Any]) -> JSONResponse | None:
    if current_user.get("role") == "admin":
        return None
    if _permissions(current_user).intersection({"plugin:read", "plugin:admin"}):
        return None
    # Settings → Plugins is an owner-facing surface in this app; any
    # authenticated user may read installation state.
    if current_user.get("user_id") is not None:
        return None
    return JSONResponse(
        status_code=403,
        content=build_error_payload("WORKFLOW_PERMISSION_DENIED"),
    )


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class InstallRequest(_Strict):
    package_spec: str = Field(min_length=3, max_length=300)
    source_type: Literal["claude-official", "marketplace", "platform-builtin"] | None = None


class DeckRefsPutRequest(_Strict):
    refs: list[dict[str, Any]] = Field(default_factory=list, max_length=32)


def _run_install(operation_id: str, package_spec: str, source_type: str) -> None:
    """Background task: real CLI install on a fresh DB connection."""
    db = database.get_db()
    try:
        PluginInstallService(db).install(
            package_spec,
            source_type=source_type or None,
            operation_id=operation_id,
        )
    except PluginInstallError:
        # Operation row already carries the error state + evidence path.
        pass
    except Exception:  # noqa: BLE001 - never let a background task die silently
        import logging

        logging.getLogger(__name__).exception(
            "claude plugin install background task crashed for %s", package_spec
        )
    finally:
        db.close()


@router.get("/api/claude-plugins/installations")
async def list_installations(current_user: dict = Depends(get_current_user)):
    denied = _require_reader(current_user)
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
        return {"installations": installations}
    finally:
        db.close()


@router.post("/api/claude-plugins/install", status_code=202)
async def install_plugin(
    request: InstallRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    denied = _require_admin(current_user)
    if denied is not None:
        return denied
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
        parse_package_spec(request.package_spec)
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
        db.execute(
            """
            INSERT INTO claude_plugin_operations (
                id, operation_kind, requested_package_spec, status, phase,
                progress, message, created_at, updated_at
            ) VALUES (?, 'install', ?, 'queued', 'queued', 0, ?, ?, ?)
            """,
            (
                operation_id,
                request.package_spec,
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
        request.package_spec,
        request.source_type or "",
    )
    return {
        "accepted": True,
        "operation_id": operation_id,
        "package_spec": request.package_spec,
    }


@router.get("/api/claude-plugins/operations")
async def list_operations(
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
):
    denied = _require_reader(current_user)
    if denied is not None:
        return denied
    db = database.get_db()
    try:
        cursor = db.execute(
            "SELECT * FROM claude_plugin_operations ORDER BY created_at DESC LIMIT ?",
            (max(1, min(limit, 100)),),
        )
        columns = [desc[0] for desc in cursor.description]
        return {"operations": [dict(zip(columns, row)) for row in cursor.fetchall()]}
    finally:
        db.close()


@router.get("/api/claude-plugins/operations/{operation_id}")
async def get_operation(operation_id: str, current_user: dict = Depends(get_current_user)):
    denied = _require_reader(current_user)
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
    denied = _require_reader(current_user)
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
            "WHERE plugin_installation_id = ?",
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
    denied = _require_admin(current_user)
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
    denied = _require_admin(current_user)
    if denied is not None:
        return denied
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
