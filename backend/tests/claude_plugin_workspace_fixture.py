# [Input] SQLite Claude Plugin fixture rows and optional server adapter package specs.
# [Output] Registry106-shaped metadata passed to the production filesystem packer loader seam.
# [Pos] Test-only compatibility fixture; production Dream receives metadata from Admin DTOs.
# [Sync] 2026-09-16: move the retired Dream SQL pack entry out of production modules.
"""Test-only SQLite metadata adapter for workspace plugin pack tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from services.claude_plugin.package_spec import PackageSpecError, parse_package_spec
from services.claude_plugin.workspace_packer import (
    WorkspacePackError,
    pack_workspace_plugins_with_refs_loader,
)


def _row_to_dict(row: Any) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def _load_deck_plugin_refs(db: Any, deck_id: str) -> list[dict[str, Any]]:
    rows = db.execute(
        """
        SELECT r.*, i.package_name, i.marketplace,
               i.status AS installation_status,
               i.compatibility_json AS installation_compatibility_json
        FROM deck_claude_plugin_refs r
        JOIN claude_plugin_installations i ON i.id = r.plugin_installation_id
        WHERE r.deck_id = %s AND r.enabled = 1
        ORDER BY r.order_index, r.created_at, r.plugin_installation_id
        """,
        (deck_id,),
    ).fetchall()
    return [_row_to_dict(row) for row in rows]


def _load_server_adapter_refs(
    db: Any,
    package_specs: tuple[str, ...],
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw_spec in package_specs:
        try:
            spec = parse_package_spec(raw_spec)
        except PackageSpecError as exc:
            raise WorkspacePackError(
                "CLAUDE_PLUGIN_NOT_FOUND",
                f"server adapter package spec is invalid: {raw_spec!r}",
            ) from exc
        canonical = spec.canonical
        if canonical in seen:
            continue
        seen.add(canonical)

        predicates = ["package_name = %s", "marketplace = %s"]
        params: list[Any] = [spec.package_name, spec.marketplace]
        if spec.requested_version is not None:
            predicates.append("resolved_version = %s")
            params.append(spec.requested_version)
        rows = db.execute(
            f"""
            SELECT * FROM claude_plugin_installations
            WHERE {' AND '.join(predicates)}
            ORDER BY installed_at DESC NULLS LAST, created_at DESC, id DESC
            """,
            params,
        ).fetchall()
        if not rows:
            raise WorkspacePackError(
                "CLAUDE_PLUGIN_NOT_FOUND",
                f"server adapter installation was not found: {canonical}",
            )
        ready = next((row for row in rows if row["status"] == "ready"), None)
        if ready is None:
            raise WorkspacePackError(
                "CLAUDE_PLUGIN_NOT_READY",
                f"server adapter installation is not ready: {canonical} "
                f"(status={rows[0]['status']})",
            )
        row = _row_to_dict(ready)
        refs.append(
            {
                "plugin_installation_id": row["id"],
                "package_spec": canonical,
                "resolved_version": row["resolved_version"],
                "artifact_digest": row["artifact_digest"],
                "package_name": row["package_name"],
                "marketplace": row["marketplace"],
                "installation_status": row["status"],
                "installation_compatibility_json": row.get(
                    "compatibility_json", "{}"
                ),
            }
        )
    return refs


def _load_fixture_refs(
    db: Any,
    deck_id: str,
    server_adapter_package_specs: tuple[str, ...],
) -> list[dict[str, Any]]:
    refs = _load_deck_plugin_refs(db, deck_id)
    package_specs_seen = {str(ref["package_spec"]) for ref in refs}
    for adapter_ref in _load_server_adapter_refs(
        db, server_adapter_package_specs
    ):
        package_spec = str(adapter_ref["package_spec"])
        if package_spec in package_specs_seen:
            continue
        package_specs_seen.add(package_spec)
        refs.append(adapter_ref)
    return refs


def pack_workspace_plugins_from_fixture(
    db: Any,
    *,
    workspace: Path,
    deck_id: str | None,
    server_adapter_package_specs: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Adapt historical SQLite fixtures to the production loader contract."""

    return pack_workspace_plugins_with_refs_loader(
        workspace=workspace,
        deck_id=deck_id,
        refs_loader=lambda: _load_fixture_refs(
            db,
            str(deck_id),
            server_adapter_package_specs,
        ),
    )
