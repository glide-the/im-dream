"""Pack Deck-referenced plugin artifacts into an agent workspace.

When a Deck Chat workspace is prepared, the packer:

1. reads the Deck's enabled plugin installation references (digest-pinned),
2. re-verifies every artifact in the shared store,
3. copies each artifact to ``<workspace>/.ink/plugins/<immutable-name>``,
4. writes the server-controlled ``<workspace>/.ink/launch-manifest.json``,
5. returns a pack receipt.

Freeze semantics: a workspace that already has a launch manifest is *not*
silently reconfigured.  The existing manifest is re-validated and its packed
directories repaired from the artifact store when missing, but plugin
versions are never swapped mid-thread.  Disabling a plugin on the Deck only
affects workspaces created afterwards.
"""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import sqlite3
from typing import Any

from . import artifact_store, runtime, workspace_init


def _as_pack_error(exc: workspace_init.WorkspaceInitError) -> "WorkspacePackError":
    return WorkspacePackError(exc.code, str(exc))

LAUNCH_MANIFEST_RELATIVE_PATH = Path(".ink") / "launch-manifest.json"
PLUGIN_SLOTS_RELATIVE_DIR = Path(".ink") / "plugins"
PACK_RECEIPT_RELATIVE_PATH = Path(".ink") / "plugin-pack-receipt.json"
LAUNCH_MANIFEST_SCHEMA_VERSION = "claude-launch/v1"


class WorkspacePackError(RuntimeError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def load_deck_plugin_refs(db: sqlite3.Connection, deck_id: str) -> list[dict[str, Any]]:
    """Enabled, ordered plugin installation references for a Deck."""
    rows = db.execute(
        """
        SELECT r.*, i.package_name, i.marketplace,
               i.status AS installation_status,
               i.compatibility_json AS installation_compatibility_json
        FROM deck_claude_plugin_refs r
        JOIN claude_plugin_installations i ON i.id = r.plugin_installation_id
        WHERE r.deck_id = ? AND r.enabled = 1
        ORDER BY r.order_index, r.created_at, r.plugin_installation_id
        """,
        (deck_id,),
    ).fetchall()
    return [_row_to_dict(row) for row in rows]


def _manifest_entry(
    ref: dict[str, Any], workspace: Path, packed_dir_name: str
) -> dict[str, Any]:
    relative_path = (PLUGIN_SLOTS_RELATIVE_DIR / packed_dir_name).as_posix()
    return {
        "package_spec": ref["package_spec"],
        "resolved_version": ref["resolved_version"],
        "relative_path": relative_path,
        "artifact_digest": ref["artifact_digest"],
    }


def _read_manifest(workspace: Path) -> dict[str, Any] | None:
    manifest_path = workspace / LAUNCH_MANIFEST_RELATIVE_PATH
    if not manifest_path.is_file():
        return None
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def pack_workspace_plugins(
    db: sqlite3.Connection,
    *,
    workspace: Path,
    deck_id: str | None,
) -> dict[str, Any]:
    """Idempotently pack a workspace for its locked Deck.

    Returns the pack receipt.  With no Deck (or no enabled refs) the receipt
    has an empty plugin list and no manifest is created.
    """
    workspace = Path(workspace).resolve()
    receipt: dict[str, Any] = {
        "schema_version": LAUNCH_MANIFEST_SCHEMA_VERSION,
        "workspace": str(workspace),
        "deck_id": deck_id,
        "packed_at": None,
        "plugins": [],
        "frozen": False,
    }
    if not deck_id:
        _write_json(workspace / PACK_RECEIPT_RELATIVE_PATH, receipt)
        return receipt

    existing_manifest = _read_manifest(workspace)
    if existing_manifest is not None:
        # Frozen workspace: re-validate, repair missing packed dirs, never swap.
        # Init steps are never re-run; the managed venv is a derived cache
        # keyed by digest and may be rebuilt when missing.
        plugins = existing_manifest.get("plugins") or []
        repaired: list[dict[str, Any]] = []
        for entry in plugins:
            repaired_entry = _ensure_packed_entry(workspace, entry, allow_repair=True)
            _ensure_frozen_runtime(workspace, entry)
            repaired.append(repaired_entry)
        receipt.update(
            {
                "packed_at": existing_manifest.get("written_at"),
                "plugins": repaired,
                "frozen": True,
            }
        )
        if existing_manifest.get("runtime"):
            receipt["runtime"] = existing_manifest["runtime"]
        if existing_manifest.get("init_steps"):
            receipt["init_steps"] = existing_manifest["init_steps"]
        _write_json(workspace / PACK_RECEIPT_RELATIVE_PATH, receipt)
        return receipt

    refs = load_deck_plugin_refs(db, deck_id)
    manifest_entries: list[dict[str, Any]] = []
    receipt_entries: list[dict[str, Any]] = []
    init_steps: list[dict[str, Any]] = []
    venv_dirs: list[str] = []
    for ref in refs:
        if ref["installation_status"] != "ready":
            raise WorkspacePackError(
                "CLAUDE_PLUGIN_NOT_READY",
                f"installation {ref['plugin_installation_id']} is not ready "
                f"(status={ref['installation_status']})",
            )
        artifact = artifact_store.get_artifact(
            ref["package_name"], ref["marketplace"], ref["artifact_digest"]
        )
        packed_name = artifact_store.artifact_dir_name(
            ref["package_name"], ref["marketplace"], ref["artifact_digest"]
        )
        destination = workspace / PLUGIN_SLOTS_RELATIVE_DIR / packed_name
        artifact_store.copy_into_workspace(artifact, destination)
        try:
            profile = workspace_init.load_init_profile(destination)
            if profile is not None:
                init_steps.extend(
                    {**step, "package_spec": ref["package_spec"]}
                    for step in workspace_init.execute_init_profile(
                        workspace, destination, profile
                    )
                )
                if profile.python is not None:
                    venv_dir = workspace_init.ensure_plugin_venv(
                        runtime.get_runtime_root(),
                        ref["artifact_digest"],
                        destination,
                        profile.python,
                    )
                    venv_dirs.append(str(venv_dir))
        except workspace_init.WorkspaceInitError as exc:
            raise _as_pack_error(exc) from exc
        manifest_entries.append(_manifest_entry(ref, workspace, packed_name))
        receipt_entries.append(
            {
                "package_spec": ref["package_spec"],
                "resolved_version": ref["resolved_version"],
                "artifact_digest": ref["artifact_digest"],
                "relative_path": (PLUGIN_SLOTS_RELATIVE_DIR / packed_name).as_posix(),
                "file_count": artifact.file_count,
                "verified": True,
            }
        )
    manifest = {
        "schema_version": LAUNCH_MANIFEST_SCHEMA_VERSION,
        "deck_id": deck_id,
        "written_at": _now(),
        "plugins": manifest_entries,
    }
    if venv_dirs:
        manifest["runtime"] = {"venv_dirs": venv_dirs}
    if init_steps:
        manifest["init_steps"] = init_steps
    if manifest_entries:
        _write_json(workspace / LAUNCH_MANIFEST_RELATIVE_PATH, manifest)
    receipt.update({"packed_at": manifest["written_at"], "plugins": receipt_entries})
    if venv_dirs:
        receipt["runtime"] = {"venv_dirs": venv_dirs}
    if init_steps:
        receipt["init_steps"] = init_steps
    _write_json(workspace / PACK_RECEIPT_RELATIVE_PATH, receipt)
    return receipt


def _ensure_frozen_runtime(workspace: Path, entry: dict[str, Any]) -> None:
    """Rebuild the managed venv of a frozen workspace entry when missing.

    Never re-runs init steps and never swaps plugin versions — the venv is a
    derived cache addressable by the pinned artifact digest.
    """
    relative_path = str(entry.get("relative_path") or "")
    digest = str(entry.get("artifact_digest") or "")
    packed_dir = (workspace / relative_path).resolve()
    if not packed_dir.is_dir():
        return  # missing-dir repair is handled by _ensure_packed_entry
    try:
        profile = workspace_init.load_init_profile(packed_dir)
        if profile is None or profile.python is None:
            return
        workspace_init.ensure_plugin_venv(
            runtime.get_runtime_root(), digest, packed_dir, profile.python
        )
    except workspace_init.WorkspaceInitError as exc:
        raise _as_pack_error(exc) from exc


def _ensure_packed_entry(
    workspace: Path, entry: dict[str, Any], *, allow_repair: bool
) -> dict[str, Any]:
    """Re-validate one frozen manifest entry; repair the copy when missing."""
    relative_path = str(entry.get("relative_path") or "")
    digest = str(entry.get("artifact_digest") or "")
    package_spec = str(entry.get("package_spec") or "")
    try:
        package_name, marketplace = package_spec.split("@", 1)
    except ValueError as exc:
        raise WorkspacePackError(
            "CLAUDE_PLUGIN_MANIFEST_INVALID",
            f"manifest entry has an invalid package_spec: {package_spec!r}",
        ) from exc
    packed_dir = (workspace / relative_path).resolve()
    try:
        packed_dir.relative_to(workspace)
    except ValueError as exc:
        raise WorkspacePackError(
            "CLAUDE_PLUGIN_MANIFEST_INVALID",
            f"manifest entry path escapes the workspace: {relative_path!r}",
        ) from exc
    if not packed_dir.is_dir():
        if not allow_repair:
            raise WorkspacePackError(
                "CLAUDE_PLUGIN_PACK_MISSING",
                f"packed plugin directory is missing: {relative_path}",
            )
        artifact = artifact_store.get_artifact(package_name, marketplace, digest)
        artifact_store.copy_into_workspace(artifact, packed_dir)
    from .digest import compute_plugin_digest

    actual = compute_plugin_digest(packed_dir)
    if actual != digest:
        raise WorkspacePackError(
            "CLAUDE_PLUGIN_INTEGRITY_FAILED",
            f"packed plugin digest mismatch for {package_spec}: "
            f"expected {digest}, found {actual}",
        )
    return {
        "package_spec": package_spec,
        "resolved_version": entry.get("resolved_version"),
        "artifact_digest": digest,
        "relative_path": relative_path,
        "verified": True,
    }
