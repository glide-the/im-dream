"""Pack Deck-referenced plugin artifacts into an agent workspace.

When a Deck Chat workspace is prepared, the packer:

1. reads the Deck's enabled plugin installation references (digest-pinned),
2. re-verifies every artifact in the shared store,
3. copies each artifact to ``<workspace>/.ink/plugins/<immutable-name>``,
4. writes the server-controlled ``<workspace>/.ink/launch-manifest.json``,
5. returns a pack receipt.

Freeze semantics: a workspace that already has a launch manifest is *not*
silently reconfigured.  The existing manifest is re-validated and its packed
directories repaired from the artifact store when missing or mangled (the
packed copy is a derived cache; the store is the digest-verified source of
truth), but plugin versions are never swapped mid-thread.  Disabling a
plugin on the Deck only affects workspaces created afterwards.
"""

from __future__ import annotations

from datetime import UTC, datetime
from dataclasses import asdict
import json
import logging
import os
from pathlib import Path
import sqlite3
import tempfile
from typing import Any

from . import artifact_store, runtime, workspace_init
from .package_spec import PackageSpecError, parse_package_spec

logger = logging.getLogger(__name__)


def _as_pack_error(exc: workspace_init.WorkspaceInitError) -> "WorkspacePackError":
    return WorkspacePackError(exc.code, str(exc))

LAUNCH_MANIFEST_RELATIVE_PATH = Path(".ink") / "launch-manifest.json"
PLUGIN_SLOTS_RELATIVE_DIR = Path(".ink") / "plugins"
PACK_RECEIPT_RELATIVE_PATH = Path(".ink") / "plugin-pack-receipt.json"
LAUNCH_MANIFEST_SCHEMA_VERSION = "claude-launch/v1"
DRAMA_FORGE_PACKAGE_SPEC = "drama-forge@drama-studio"
_DREAM_DRAMA_COMPATIBILITY_FILES = (
    (Path(".claude-plugin/plugin.json"), Path("plugin.json")),
    (
        Path(".claude/docs/templates/project-init.md"),
        Path(".claude/docs/templates/project-init.md"),
    ),
    (Path(".claude/hooks/hooks.json"), Path(".claude/hooks/hooks.json")),
)


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


def _load_server_adapter_refs(
    db: sqlite3.Connection,
    package_specs: tuple[str, ...],
) -> list[dict[str, Any]]:
    """Resolve server-selected adapters to ready, digest-pinned installs.

    These transient references intentionally have the same shape as Deck refs
    so the immutable pack pipeline can consume both uniformly.  They are never
    persisted to ``deck_claude_plugin_refs``.
    """

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

        predicates = ["package_name = ?", "marketplace = ?"]
        params: list[Any] = [spec.package_name, spec.marketplace]
        if spec.requested_version is not None:
            predicates.append("resolved_version = ?")
            params.append(spec.requested_version)
        rows = db.execute(
            f"""
            SELECT * FROM claude_plugin_installations
            WHERE {' AND '.join(predicates)}
            ORDER BY rowid DESC
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


def _ensure_dream_drama_compatibility(
    workspace: Path,
    packed_plugin: Path,
    *,
    allow_install: bool,
) -> None:
    """Install or validate drama-forge's consumer-workspace preflight files.

    drama-forge resolves these paths from the consumer project root rather
    than its isolated plugin directory.  A fresh Dream pack may install them;
    a frozen workspace only validates the launch-time result.
    """
    def validate_target_path(target: Path) -> None:
        try:
            relative = target.relative_to(workspace)
        except ValueError as exc:
            raise WorkspacePackError(
                "CLAUDE_PLUGIN_INIT_PROFILE_INVALID",
                f"drama-forge compatibility target escapes workspace: {target}",
            ) from exc
        current = workspace
        for part in relative.parts[:-1]:
            current /= part
            if current.is_symlink():
                raise WorkspacePackError(
                    "CLAUDE_PLUGIN_INIT_PROFILE_INVALID",
                    "drama-forge compatibility target has a symlink parent: "
                    f"{current.relative_to(workspace)}",
                )
            if current.exists() and not current.is_dir():
                raise WorkspacePackError(
                    "CLAUDE_PLUGIN_INIT_PROFILE_INVALID",
                    "drama-forge compatibility target parent is not a directory: "
                    f"{current.relative_to(workspace)}",
                )
        try:
            target.parent.resolve(strict=False).relative_to(workspace)
        except ValueError as exc:
            raise WorkspacePackError(
                "CLAUDE_PLUGIN_INIT_PROFILE_INVALID",
                "drama-forge compatibility target resolves outside workspace: "
                f"{relative}",
            ) from exc

    files: list[tuple[Path, Path, bytes]] = []
    for source_relative, target_relative in _DREAM_DRAMA_COMPATIBILITY_FILES:
        source = packed_plugin / source_relative
        target = workspace / target_relative
        validate_target_path(target)
        if not source.is_file():
            raise WorkspacePackError(
                "CLAUDE_PLUGIN_INIT_PROFILE_INVALID",
                f"drama-forge compatibility source is missing: {source_relative}",
            )
        try:
            content = source.read_bytes()
        except OSError as exc:
            raise WorkspacePackError(
                "CLAUDE_PLUGIN_INIT_PROFILE_INVALID",
                f"failed to read drama-forge compatibility source: {source_relative}",
            ) from exc
        files.append((source_relative, target, content))

    missing: list[tuple[Path, bytes]] = []
    for source_relative, target, content in files:
        if target.exists() or target.is_symlink():
            try:
                matches = (
                    target.is_file()
                    and not target.is_symlink()
                    and target.read_bytes() == content
                )
            except OSError:
                matches = False
            if not matches:
                raise WorkspacePackError(
                    "CLAUDE_PLUGIN_INIT_PROFILE_INVALID",
                    "drama-forge compatibility target conflicts with the "
                    f"packed source: {target.relative_to(workspace)} "
                    f"(source={source_relative})",
                )
            continue
        if not allow_install:
            raise WorkspacePackError(
                "CLAUDE_PLUGIN_INIT_PROFILE_INVALID",
                "frozen workspace is missing drama-forge compatibility target: "
                f"{target.relative_to(workspace)}",
            )
        missing.append((target, content))

    staged: list[tuple[Path, Path]] = []
    installed: list[tuple[Path, tuple[int, int]]] = []
    try:
        for target, content in missing:
            target.parent.mkdir(parents=True, exist_ok=True)
            validate_target_path(target)
            with tempfile.NamedTemporaryFile(
                dir=target.parent,
                prefix=f".{target.name}.dream-compat-",
                delete=False,
            ) as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
                staged.append((Path(handle.name), target))
        for temporary, target in staged:
            # A hard-link publishes the complete staged bytes without
            # overwriting a target created after the conflict preflight.  The
            # caller prepares this private workspace before its final publish;
            # group rollback therefore keeps partial compatibility files out
            # of the workspace that becomes visible to the Agent.
            temporary_stat = temporary.stat()
            os.link(temporary, target)
            installed.append(
                (target, (temporary_stat.st_dev, temporary_stat.st_ino))
            )
    except OSError as exc:
        for target, published_identity in reversed(installed):
            try:
                current_stat = target.lstat()
            except FileNotFoundError:
                continue
            if (current_stat.st_dev, current_stat.st_ino) == published_identity:
                target.unlink(missing_ok=True)
        raise WorkspacePackError(
            "CLAUDE_PLUGIN_INIT_PROFILE_INVALID",
            f"failed to install drama-forge compatibility files: {exc}",
        ) from exc
    finally:
        for temporary, _target in staged:
            temporary.unlink(missing_ok=True)


def pack_workspace_plugins(
    db: sqlite3.Connection,
    *,
    workspace: Path,
    deck_id: str | None,
    server_adapter_package_specs: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Idempotently pack a workspace for its locked Deck.

    Returns the pack receipt.  With no Deck (or no enabled refs) the receipt
    has an empty plugin list and no manifest is created.  Server-selected
    adapter package specs are resolved from ready installation records only on
    the first pack; they never mutate Deck refs or a frozen workspace.
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
        # Frozen surfaces: validate only, never rebuild — a materialized
        # protocol directory is an init result, not a derived cache
        # (design_004 §3.4.4; audit A1).
        existing_surfaces = existing_manifest.get("surfaces") or []
        missing = [
            surface["protocol_dir"]
            for surface in existing_surfaces
            if isinstance(surface, dict)
            and surface.get("protocol_dir")
            and not (workspace / surface["protocol_dir"] / "workspace.json").exists()
        ]
        if missing:
            raise WorkspacePackError(
                "CLAUDE_PLUGIN_INIT_PROFILE_INVALID",
                f"frozen workspace is missing materialized surfaces: {missing}",
            )
        has_dream_surface = any(
            isinstance(surface, dict) and surface.get("name") == "dream"
            for surface in existing_surfaces
        )
        drama_entry = next(
            (
                entry
                for entry in plugins
                if isinstance(entry, dict)
                and entry.get("package_spec") == DRAMA_FORGE_PACKAGE_SPEC
            ),
            None,
        )
        if has_dream_surface and drama_entry is not None:
            _ensure_dream_drama_compatibility(
                workspace,
                workspace / str(drama_entry.get("relative_path") or ""),
                allow_install=False,
            )
        receipt.update(
            {
                "packed_at": existing_manifest.get("written_at"),
                "plugins": repaired,
                "frozen": True,
            }
        )
        if existing_surfaces:
            receipt["surfaces"] = existing_surfaces
        if existing_manifest.get("runtime"):
            receipt["runtime"] = existing_manifest["runtime"]
        if existing_manifest.get("init_steps"):
            receipt["init_steps"] = existing_manifest["init_steps"]
        _write_json(workspace / PACK_RECEIPT_RELATIVE_PATH, receipt)
        return receipt

    refs = load_deck_plugin_refs(db, deck_id)
    package_specs_seen = {str(ref["package_spec"]) for ref in refs}
    for adapter_ref in _load_server_adapter_refs(
        db, server_adapter_package_specs
    ):
        package_spec = str(adapter_ref["package_spec"])
        if package_spec in package_specs_seen:
            continue
        package_specs_seen.add(package_spec)
        refs.append(adapter_ref)
    manifest_entries: list[dict[str, Any]] = []
    receipt_entries: list[dict[str, Any]] = []
    init_steps: list[dict[str, Any]] = []
    venv_dirs: list[str] = []
    merged_surfaces: list[workspace_init.SurfaceSpec] = []
    surface_names_seen: set[str] = set()
    warnings: list[dict[str, Any]] = []
    drama_packed_plugin: Path | None = None
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
        if ref["package_spec"] == DRAMA_FORGE_PACKAGE_SPEC:
            drama_packed_plugin = destination
        try:
            profile = workspace_init.load_init_profile(destination)
            if profile is not None:
                init_steps.extend(
                    {**step, "package_spec": ref["package_spec"]}
                    for step in workspace_init.execute_init_profile(
                        workspace, destination, profile
                    )
                )
                # Merge declared surfaces: first declaration in pack order
                # wins; later conflicts are recorded as receipt warnings
                # (design_004 §3.1/§3.4.4 multi-plugin rule).
                for spec in profile.surfaces:
                    if spec.name in surface_names_seen:
                        warnings.append(
                            {
                                "kind": "surface-conflict",
                                "surface": spec.name,
                                "package_spec": ref["package_spec"],
                            }
                        )
                        continue
                    surface_names_seen.add(spec.name)
                    merged_surfaces.append(spec)
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
    has_dream_surface = any(spec.name == "dream" for spec in merged_surfaces)
    if has_dream_surface and drama_packed_plugin is not None:
        _ensure_dream_drama_compatibility(
            workspace,
            drama_packed_plugin,
            allow_install=True,
        )

    # Materialize protocol directories once, after every artifact has been
    # copied and init has run — workspace.json needs the full plugin list
    # (design_004 §3.4.4; audit A1/A4).  Any failure fails the whole pack.
    if merged_surfaces:
        plugins_payload = [
            {
                "package_spec": entry["package_spec"],
                "artifact_digest": entry["artifact_digest"],
                "resolved_version": entry["resolved_version"],
            }
            for entry in manifest_entries
        ]
        for spec in merged_surfaces:
            if spec.name == "dream":
                try:
                    init_steps.append(
                        workspace_init.materialize_dream_surface(
                            workspace, deck_id, plugins_payload, spec.entry_route
                        )
                    )
                except Exception as exc:
                    raise WorkspacePackError(
                        "CLAUDE_PLUGIN_INIT_PROFILE_INVALID",
                        f"failed to materialize dream surface: {exc}",
                    ) from exc
    manifest = {
        "schema_version": LAUNCH_MANIFEST_SCHEMA_VERSION,
        "deck_id": deck_id,
        "written_at": _now(),
        "plugins": manifest_entries,
    }
    if merged_surfaces:
        manifest["surfaces"] = [asdict(spec) for spec in merged_surfaces]
    if venv_dirs:
        manifest["runtime"] = {"venv_dirs": venv_dirs}
    if init_steps:
        manifest["init_steps"] = init_steps
    if manifest_entries:
        _write_json(workspace / LAUNCH_MANIFEST_RELATIVE_PATH, manifest)
    receipt.update({"packed_at": manifest["written_at"], "plugins": receipt_entries})
    if merged_surfaces:
        receipt["surfaces"] = manifest["surfaces"]
    if warnings:
        receipt["warnings"] = warnings
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
    if actual != digest and allow_repair:
        # The packed copy is a derived cache; the immutable artifact store is
        # the source of truth. Copies mangled outside our control — zip
        # archives flattening symlinks, Finder metadata junk, manual edits —
        # fail the digest check. Repair from the store and re-verify; only
        # fail closed when the store cannot supply the pinned artifact.
        logger.warning(
            "packed plugin copy failed digest verification for %s (%s); "
            "repairing from artifact store",
            package_spec,
            relative_path,
        )
        try:
            artifact = artifact_store.get_artifact(package_name, marketplace, digest)
            artifact_store.copy_into_workspace(artifact, packed_dir)
        except artifact_store.ArtifactStoreError:
            logger.exception(
                "repair from artifact store failed for %s", package_spec
            )
        else:
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
