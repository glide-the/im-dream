"""Real Claude plugin install orchestration.

Every install flows through the same pipeline:

    validate spec → (marketplace installs only) ensure marketplace +
    real `claude plugin install` → read the CLI's own registry → locate the
    plugin root → read the manifest → enumerate official component kinds →
    deterministic SHA-256 → import into the immutable artifact store →
    database record (status ready).

A failed step never produces a ``ready`` record; the operation evidence
(argv, cwd, CLI version, exit code, sanitized output, file-tree delta) is
always persisted.  Re-running an install that resolves to the same version
and digest replays the existing installation record.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import sqlite3
from typing import Any, Iterator
import uuid

from . import artifact_store, cli, runtime
from .builtin_sources import (
    KNOWN_MARKETPLACE_REPOS,
    get_builtin_declaration,
    resolve_builtin_source,
    resolve_local_marketplace,
)
from .compatibility import cli_version_to_semver, version_satisfies
from .digest import compute_plugin_digest
from .package_spec import PackageSpec, PackageSpecError, parse_package_spec

try:  # POSIX file lock for concurrent install de-duplication.
    import fcntl
except ImportError:  # pragma: no cover - non-POSIX fallback
    fcntl = None  # type: ignore[assignment]


# Error codes (stable, surfaced through the API).
PLUGIN_SPEC_INVALID = "CLAUDE_PLUGIN_SPEC_INVALID"
PLUGIN_SOURCE_UNKNOWN = "CLAUDE_PLUGIN_SOURCE_UNKNOWN"
PLUGIN_CLI_UNAVAILABLE = "CLAUDE_PLUGIN_CLI_UNAVAILABLE"
PLUGIN_INSTALL_FAILED = "CLAUDE_PLUGIN_INSTALL_FAILED"
PLUGIN_REGISTRY_MISMATCH = "CLAUDE_PLUGIN_REGISTRY_MISMATCH"
PLUGIN_MANIFEST_INVALID = "CLAUDE_PLUGIN_MANIFEST_INVALID"
PLUGIN_ARTIFACT_FAILED = "CLAUDE_PLUGIN_ARTIFACT_FAILED"
PLUGIN_MARKETPLACE_UNKNOWN = "CLAUDE_PLUGIN_MARKETPLACE_UNKNOWN"


class PluginInstallError(RuntimeError):
    def __init__(self, code: str, message: str, *, detail: dict[str, Any] | None = None):
        self.code = code
        self.detail = detail or {}
        super().__init__(message)


@contextmanager
def _install_lock(key: str) -> Iterator[None]:
    """Cross-process install de-dup lock keyed by package spec."""
    locks_dir = runtime.get_operations_root() / ".locks"
    locks_dir.mkdir(parents=True, exist_ok=True)
    lock_path = locks_dir / f"{abs(hash(key))}.lock"
    handle = lock_path.open("w")
    try:
        if fcntl is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        if fcntl is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


# ---------------------------------------------------------------------------
# Component inventory — official plugin component kinds (plugins-reference).
# ---------------------------------------------------------------------------

_COMPONENT_DIRS = (
    "skills",
    "commands",
    "agents",
    "hooks",
    "monitors",
    "output-styles",
    "themes",
    "bin",
    "scripts",
)
_COMPONENT_FILES = (".mcp.json", ".lsp.json", "settings.json")


def enumerate_components(plugin_root: Path) -> dict[str, Any]:
    """Enumerate the official component kinds present in a plugin root."""
    inventory: dict[str, Any] = {"skills": [], "commands": [], "agents": [], "hooks": []}
    root = Path(plugin_root)
    skills_dir = root / "skills"
    if skills_dir.is_dir():
        inventory["skills"] = sorted(
            item.name
            for item in skills_dir.iterdir()
            if item.is_dir() and (item / "SKILL.md").is_file()
        )
    if (root / "SKILL.md").is_file():
        inventory["skills"] = sorted({*inventory["skills"], "<root>"})
    commands_dir = root / "commands"
    if commands_dir.is_dir():
        inventory["commands"] = sorted(
            item.name for item in commands_dir.glob("*.md")
        )
    agents_dir = root / "agents"
    if agents_dir.is_dir():
        inventory["agents"] = sorted(item.name for item in agents_dir.glob("*.md"))
    hooks_dir = root / "hooks"
    if hooks_dir.is_dir():
        inventory["hooks"] = sorted(
            item.name for item in hooks_dir.glob("*.json")
        )
    for extra_dir in ("monitors", "output-styles", "themes", "bin", "scripts"):
        directory = root / extra_dir
        if directory.is_dir():
            inventory[extra_dir] = sorted(
                item.name for item in directory.iterdir() if item.is_file()
            )
    for marker in _COMPONENT_FILES:
        if (root / marker).is_file():
            inventory[marker.lstrip(".").replace(".json", "")] = True
    _enumerate_manifest_declared_components(root, inventory)
    return inventory


def _as_path_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def _enumerate_manifest_declared_components(root: Path, inventory: dict[str, Any]) -> None:
    """Merge components declared via plugin.json custom paths (official
    component config fields: skills/commands/agents/hooks) — e.g. plugins
    that keep their tree under ``.claude/`` like drama-forge."""
    manifest = read_manifest(root)
    if not manifest:
        return
    for skills_path in _as_path_list(manifest.get("skills")):
        skills_dir = root / skills_path
        if skills_dir.is_dir():
            inventory["skills"] = sorted(
                {
                    *inventory["skills"],
                    *(
                        item.name
                        for item in skills_dir.iterdir()
                        if item.is_dir() and (item / "SKILL.md").is_file()
                    ),
                }
            )
    for commands_path in _as_path_list(manifest.get("commands")):
        commands_dir = root / commands_path
        if commands_dir.is_dir():
            inventory["commands"] = sorted(
                {*inventory["commands"], *(item.name for item in commands_dir.glob("*.md"))}
            )
        elif commands_dir.is_file() and commands_dir.suffix == ".md":
            inventory["commands"] = sorted({*inventory["commands"], commands_dir.name})
    for agents_path in _as_path_list(manifest.get("agents")):
        agents_entry = root / agents_path
        if agents_entry.is_dir():
            inventory["agents"] = sorted(
                {*inventory["agents"], *(item.name for item in agents_entry.glob("*.md"))}
            )
        elif agents_entry.is_file() and agents_entry.suffix == ".md":
            inventory["agents"] = sorted({*inventory["agents"], agents_entry.name})
    for hooks_path in _as_path_list(manifest.get("hooks")):
        hooks_entry = root / hooks_path
        if hooks_entry.is_file():
            inventory["hooks"] = sorted({*inventory["hooks"], hooks_entry.name})
        elif hooks_entry.is_dir():
            inventory["hooks"] = sorted(
                {*inventory["hooks"], *(item.name for item in hooks_entry.glob("*.json"))}
            )


def read_manifest(plugin_root: Path) -> dict[str, Any] | None:
    """Read ``.claude-plugin/plugin.json`` when present (it is optional)."""
    manifest_path = Path(plugin_root) / ".claude-plugin" / "plugin.json"
    if not manifest_path.is_file():
        return None
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PluginInstallError(
            PLUGIN_MANIFEST_INVALID,
            f"plugin manifest is not valid JSON: {exc}",
        ) from exc
    if not isinstance(payload, dict):
        raise PluginInstallError(
            PLUGIN_MANIFEST_INVALID, "plugin manifest must be a JSON object"
        )
    name = payload.get("name")
    if name is not None and not isinstance(name, str):
        raise PluginInstallError(
            PLUGIN_MANIFEST_INVALID, "plugin manifest field 'name' must be a string"
        )
    return payload


# ---------------------------------------------------------------------------
# CLI registry reading (managed CLAUDE_CONFIG_DIR only — never ~/.claude).
# ---------------------------------------------------------------------------


def _read_cli_registry() -> dict[str, Any]:
    registry_path = runtime.get_cli_registry_path()
    if not registry_path.is_file():
        return {"version": 2, "plugins": {}}
    try:
        payload = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": 2, "plugins": {}}
    return payload if isinstance(payload, dict) else {"version": 2, "plugins": {}}


def _registry_entry_for(spec: PackageSpec) -> dict[str, Any]:
    registry = _read_cli_registry()
    plugins = registry.get("plugins") or {}
    records = plugins.get(spec.canonical) or []
    if isinstance(records, dict):
        records = [records]
    cache_root = runtime.get_cli_cache_root().resolve()
    for record in records:
        install_path = Path(str(record.get("installPath", ""))).resolve()
        try:
            install_path.relative_to(cache_root)
        except ValueError:
            continue
        if install_path.is_dir():
            return {**record, "installPath": str(install_path)}
    raise PluginInstallError(
        PLUGIN_REGISTRY_MISMATCH,
        "the CLI registry has no cache-contained entry for "
        f"{spec.canonical} after install",
    )


def _known_marketplaces() -> dict[str, Any]:
    path = runtime.get_config_dir() / "plugins" / "known_marketplaces.json"
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _ensure_marketplace(spec: PackageSpec, evidence: dict[str, Any]) -> None:
    """Register the marketplace via the real CLI when not yet known."""
    if spec.marketplace in _known_marketplaces():
        return
    repo = KNOWN_MARKETPLACE_REPOS.get(spec.marketplace)
    source: str | None = repo
    if source is None:
        local = resolve_local_marketplace(spec.marketplace)
        source = str(local) if local is not None else None
    if source is None:
        raise PluginInstallError(
            PLUGIN_MARKETPLACE_UNKNOWN,
            f"marketplace {spec.marketplace!r} is not registered in the managed "
            "workspace and has no server-declared repository",
        )
    execution = cli.run_claude(
        ["plugin", "marketplace", "add", source],
        cwd=runtime.get_install_workspace(),
    )
    evidence["marketplace_add"] = execution.to_json()
    if not execution.ok:
        raise PluginInstallError(
            PLUGIN_INSTALL_FAILED,
            f"claude plugin marketplace add {source} failed "
            f"(exit {execution.exit_code})",
            detail={"stderr": execution.stderr[-500:]},
        )


# ---------------------------------------------------------------------------
# Database helpers (tables created in database.py).
# ---------------------------------------------------------------------------


def _insert_operation(db: sqlite3.Connection, operation: dict[str, Any]) -> None:
    db.execute(
        """
        INSERT INTO claude_plugin_operations (
            id, operation_kind, requested_package_spec, status, phase,
            progress, message, executable, argv_json, cwd, cli_version,
            exit_code, evidence_path, installation_id, error_code,
            error_summary, created_at, updated_at, finished_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            operation["id"],
            operation["operation_kind"],
            operation["requested_package_spec"],
            operation["status"],
            operation["phase"],
            operation["progress"],
            operation.get("message"),
            operation.get("executable"),
            operation.get("argv_json"),
            operation.get("cwd"),
            operation.get("cli_version"),
            operation.get("exit_code"),
            operation.get("evidence_path"),
            operation.get("installation_id"),
            operation.get("error_code"),
            operation.get("error_summary"),
            operation["created_at"],
            operation["updated_at"],
            operation.get("finished_at"),
        ),
    )


def _update_operation(db: sqlite3.Connection, operation_id: str, **fields: Any) -> None:
    if not fields:
        return
    assignments = ", ".join(f"{key} = ?" for key in fields)
    values = [value if not isinstance(value, (dict, list)) else json.dumps(value) for value in fields.values()]
    db.execute(
        f"UPDATE claude_plugin_operations SET {assignments}, updated_at = ? WHERE id = ?",
        (*values, _now(), operation_id),
    )


def _find_installation_by_artifact(
    db: sqlite3.Connection, spec: PackageSpec, resolved_version: str, digest: str
) -> dict[str, Any] | None:
    row = db.execute(
        """
        SELECT * FROM claude_plugin_installations
        WHERE package_name = ? AND marketplace = ?
          AND resolved_version = ? AND artifact_digest = ?
        """,
        (spec.package_name, spec.marketplace, resolved_version, digest),
    ).fetchone()
    return _row_to_dict(row) if row is not None else None


def _insert_installation(db: sqlite3.Connection, record: dict[str, Any]) -> None:
    db.execute(
        """
        INSERT INTO claude_plugin_installations (
            id, requested_package_spec, package_name, marketplace,
            requested_version, resolved_version, source_type,
            artifact_digest, artifact_path, claude_cli_version,
            cli_git_commit_sha, manifest_json, component_inventory_json,
            compatibility_json, status, operation_id, error_code,
            error_summary, file_count, created_at, updated_at, installed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record["id"],
            record["requested_package_spec"],
            record["package_name"],
            record["marketplace"],
            record.get("requested_version"),
            record["resolved_version"],
            record["source_type"],
            record["artifact_digest"],
            record["artifact_path"],
            record["claude_cli_version"],
            record.get("cli_git_commit_sha"),
            record.get("manifest_json"),
            record["component_inventory_json"],
            record.get("compatibility_json", "{}"),
            record["status"],
            record["operation_id"],
            record.get("error_code"),
            record.get("error_summary"),
            record.get("file_count", 0),
            record["created_at"],
            record["updated_at"],
            record.get("installed_at"),
        ),
    )


# ---------------------------------------------------------------------------
# Install service
# ---------------------------------------------------------------------------


class PluginInstallService:
    """Coordinates real CLI installs into the shared artifact store."""

    def __init__(self, db: sqlite3.Connection) -> None:
        self.db = db
        self.db.row_factory = sqlite3.Row

    # -- public API ---------------------------------------------------------

    def install(
        self,
        raw_spec: str,
        *,
        source_type: str | None = None,
        timeout_seconds: int = 300,
        operation_id: str | None = None,
    ) -> dict[str, Any]:
        """Install *raw_spec* and return the operation record (finished)."""
        try:
            spec = parse_package_spec(raw_spec)
        except PackageSpecError as exc:
            raise PluginInstallError(PLUGIN_SPEC_INVALID, str(exc)) from exc

        builtin_decl = get_builtin_declaration(spec.canonical)
        if builtin_decl is not None and source_type in (None, "platform-builtin"):
            kind = "platform-builtin"
        elif source_type == "platform-builtin":
            raise PluginInstallError(
                PLUGIN_SOURCE_UNKNOWN,
                f"{spec.canonical} is not a server-declared platform-builtin source",
            )
        else:
            kind = "claude-official" if spec.marketplace == "claude-plugins-official" else "marketplace"

        with _install_lock(spec.canonical):
            operation = self._begin_operation(spec, kind, operation_id=operation_id)
            try:
                if kind == "platform-builtin":
                    result = self._install_platform_builtin(spec, operation)
                else:
                    result = self._install_from_marketplace(
                        spec, operation, timeout_seconds=timeout_seconds
                    )
            except PluginInstallError as exc:
                self._fail_operation(operation, exc)
                raise
            except (cli.ClaudeCliError, artifact_store.ArtifactStoreError) as exc:
                error = PluginInstallError(PLUGIN_INSTALL_FAILED, str(exc))
                self._fail_operation(operation, error)
                raise error from None
        return result

    def get_operation(self, operation_id: str) -> dict[str, Any] | None:
        row = self.db.execute(
            "SELECT * FROM claude_plugin_operations WHERE id = ?", (operation_id,)
        ).fetchone()
        return _row_to_dict(row) if row is not None else None

    def get_installation(self, installation_id: str) -> dict[str, Any] | None:
        row = self.db.execute(
            "SELECT * FROM claude_plugin_installations WHERE id = ?", (installation_id,)
        ).fetchone()
        return _row_to_dict(row) if row is not None else None

    def list_installations(self) -> list[dict[str, Any]]:
        rows = self.db.execute(
            """
            SELECT * FROM claude_plugin_installations
            ORDER BY created_at DESC, id DESC
            """
        ).fetchall()
        return [_row_to_dict(row) for row in rows]

    def uninstall(self, installation_id: str) -> dict[str, Any]:
        """Mark an installation uninstalled and disable its Deck refs.

        The immutable artifact is retained for audit (old thread workspaces
        keep their own packed copies; nothing is silently mutated).
        """
        record = self.get_installation(installation_id)
        if record is None:
            raise PluginInstallError(
                "CLAUDE_PLUGIN_NOT_FOUND", f"no installation {installation_id}"
            )
        with self.db:
            self.db.execute(
                "UPDATE claude_plugin_installations SET status = 'uninstalled', "
                "updated_at = ? WHERE id = ?",
                (_now(), installation_id),
            )
            self.db.execute(
                "UPDATE deck_claude_plugin_refs SET enabled = 0, updated_at = ? "
                "WHERE plugin_installation_id = ?",
                (_now(), installation_id),
            )
        updated = self.get_installation(installation_id)
        assert updated is not None
        return updated

    def check_cli_compatibility(self, record: dict[str, Any]) -> bool:
        """SemVer compatibility of an installation against the current CLI."""
        try:
            compatibility = json.loads(record.get("compatibility_json") or "{}")
        except (TypeError, json.JSONDecodeError):
            compatibility = {}
        range_expr = str(compatibility.get("claude_code") or "").strip()
        if not range_expr:
            return True
        try:
            cli_version = cli_version_to_semver(cli.get_cli_version())
        except (cli.ClaudeCliError, ValueError):
            return False
        try:
            return version_satisfies(cli_version, range_expr)
        except ValueError:
            return False

    def verify_installation_artifact(self, record: dict[str, Any]) -> bool:
        """Re-verify the artifact digest for an installation record."""
        try:
            artifact_store.get_artifact(
                record["package_name"], record["marketplace"], record["artifact_digest"]
            )
        except artifact_store.ArtifactStoreError:
            return False
        return True

    # -- operation lifecycle -------------------------------------------------

    def _begin_operation(
        self, spec: PackageSpec, kind: str, *, operation_id: str | None = None
    ) -> dict[str, Any]:
        operation = {
            "id": operation_id or f"cop_{uuid.uuid4().hex}",
            "operation_kind": "install",
            "requested_package_spec": spec.canonical
            + (f"@{spec.requested_version}" if spec.requested_version else ""),
            "status": "running",
            "phase": "starting",
            "progress": 5,
            "message": f"Install requested ({kind})",
            "source_type": kind,
            "created_at": _now(),
            "updated_at": _now(),
        }
        with self.db:
            existing = self.db.execute(
                "SELECT id FROM claude_plugin_operations WHERE id = ?",
                (operation["id"],),
            ).fetchone()
            if existing is not None:
                # Pre-created queued row (API path): transition to running.
                _update_operation(
                    self.db,
                    operation["id"],
                    status="running",
                    phase="starting",
                    progress=5,
                    message=operation["message"],
                )
            else:
                _insert_operation(self.db, operation)
        return operation

    def _fail_operation(self, operation: dict[str, Any], error: PluginInstallError) -> None:
        evidence = {
            "operation_id": operation["id"],
            "requested_package_spec": operation["requested_package_spec"],
            "status": "error",
            "error_code": error.code,
            "error_summary": str(error),
            "detail": error.detail,
            "finished_at": _now(),
        }
        evidence_path = cli.write_operation_evidence(operation["id"], evidence)
        with self.db:
            _update_operation(
                self.db,
                operation["id"],
                status="error",
                phase="error",
                progress=100,
                message=str(error),
                error_code=error.code,
                error_summary=str(error),
                evidence_path=str(evidence_path),
                finished_at=_now(),
            )

    def _finish_operation(
        self,
        operation: dict[str, Any],
        *,
        installation_id: str,
        evidence: dict[str, Any],
        message: str,
        execution: cli.CliExecution | None,
        replayed: bool,
    ) -> dict[str, Any]:
        evidence.update(
            {
                "operation_id": operation["id"],
                "requested_package_spec": operation["requested_package_spec"],
                "status": "ready",
                "installation_id": installation_id,
                "replayed": replayed,
                "finished_at": _now(),
            }
        )
        evidence_path = cli.write_operation_evidence(operation["id"], evidence)
        with self.db:
            _update_operation(
                self.db,
                operation["id"],
                status="ready",
                phase="ready",
                progress=100,
                message=message,
                executable=execution.executable if execution else None,
                argv_json=json.dumps(execution.argv) if execution else None,
                cwd=execution.cwd if execution else None,
                cli_version=execution.cli_version if execution else None,
                exit_code=execution.exit_code if execution else None,
                evidence_path=str(evidence_path),
                installation_id=installation_id,
                finished_at=_now(),
            )
        finished = self.get_operation(operation["id"])
        assert finished is not None
        return finished

    # -- marketplace install path --------------------------------------------

    def _install_from_marketplace(
        self, spec: PackageSpec, operation: dict[str, Any], *, timeout_seconds: int
    ) -> dict[str, Any]:
        evidence: dict[str, Any] = {"source_type": operation["source_type"]}
        before = cli.snapshot_file_tree(runtime.get_config_dir())
        _ensure_marketplace(spec, evidence)
        _update_operation(
            self.db, operation["id"], phase="cli-install", progress=20,
            message=f"Running claude plugin install {spec.install_argv_spec}",
        )
        execution = cli.run_claude(
            ["plugin", "install", spec.install_argv_spec],
            cwd=runtime.get_install_workspace(),
            timeout_seconds=timeout_seconds,
        )
        evidence["install"] = execution.to_json()
        after = cli.snapshot_file_tree(runtime.get_config_dir())
        evidence["file_delta"] = cli.snapshot_delta(before, after)
        if not execution.ok:
            raise PluginInstallError(
                PLUGIN_INSTALL_FAILED,
                f"claude plugin install {spec.install_argv_spec} failed "
                f"(exit {execution.exit_code})",
                detail={
                    "exit_code": execution.exit_code,
                    "timed_out": execution.timed_out,
                    "stderr": execution.stderr[-500:],
                },
            )
        registry_record = _registry_entry_for(spec)
        evidence["registry_record"] = registry_record
        return self._record_success(
            spec,
            operation,
            plugin_root=Path(registry_record["installPath"]),
            source_type=operation["source_type"],
            cli_version=execution.cli_version,
            cli_git_commit_sha=registry_record.get("gitCommitSha"),
            execution=execution,
            evidence=evidence,
        )

    # -- platform-builtin install path ---------------------------------------

    def _install_platform_builtin(
        self, spec: PackageSpec, operation: dict[str, Any]
    ) -> dict[str, Any]:
        source = resolve_builtin_source(spec.canonical)
        if source is None:
            raise PluginInstallError(
                PLUGIN_SOURCE_UNKNOWN,
                f"platform-builtin source for {spec.canonical} is missing",
            )
        evidence: dict[str, Any] = {
            "source_type": "platform-builtin",
            "declared_source": str(source),
        }
        _update_operation(
            self.db, operation["id"], phase="cli-validate", progress=20,
            message="Validating plugin with the real Claude CLI",
        )
        execution: cli.CliExecution | None = None
        cli_version = "unavailable"
        try:
            execution = cli.run_claude(
                ["plugin", "validate", str(source)],
                cwd=runtime.get_install_workspace(),
                timeout_seconds=60,
            )
            cli_version = execution.cli_version
            evidence["validate"] = execution.to_json()
            if not execution.ok:
                raise PluginInstallError(
                    PLUGIN_MANIFEST_INVALID,
                    f"claude plugin validate failed for {spec.canonical} "
                    f"(exit {execution.exit_code})",
                    detail={"stderr": execution.stderr[-500:]},
                )
        except cli.ClaudeCliError as exc:
            raise PluginInstallError(PLUGIN_CLI_UNAVAILABLE, str(exc)) from exc
        decl = get_builtin_declaration(spec.canonical) or {}
        return self._record_success(
            spec,
            operation,
            plugin_root=source,
            source_type="platform-builtin",
            cli_version=cli_version,
            cli_git_commit_sha=None,
            execution=execution,
            evidence=evidence,
            compatibility=decl.get("compatibility") or {},
        )

    # -- shared success path ---------------------------------------------------

    def _record_success(
        self,
        spec: PackageSpec,
        operation: dict[str, Any],
        *,
        plugin_root: Path,
        source_type: str,
        cli_version: str,
        cli_git_commit_sha: str | None,
        execution: cli.CliExecution | None,
        evidence: dict[str, Any],
        compatibility: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        _update_operation(
            self.db, operation["id"], phase="verify", progress=55,
            message="Verifying manifest and computing artifact digest",
        )
        manifest = read_manifest(plugin_root)
        manifest_version = None
        if manifest is not None:
            manifest_version = manifest.get("version")
        registry_version: str | None = None
        if execution is not None and source_type != "platform-builtin":
            registry_record = evidence.get("registry_record") or {}
            registry_version = registry_record.get("version")
        resolved_version = str(
            registry_version or manifest_version or cli_git_commit_sha or "unknown"
        )
        inventory = enumerate_components(plugin_root)
        digest = compute_plugin_digest(plugin_root)
        artifact = artifact_store.import_tree(
            plugin_root,
            package_name=spec.package_name,
            marketplace=spec.marketplace,
        )
        evidence["manifest"] = manifest
        evidence["component_inventory"] = inventory
        evidence["resolved_version"] = resolved_version
        evidence["artifact"] = {
            "digest": artifact.digest,
            "path": str(artifact.path),
            "file_count": artifact.file_count,
            "dir_name": artifact.dir_name,
        }
        # Idempotent replay: same package + resolved version + digest.
        existing = _find_installation_by_artifact(
            self.db, spec, resolved_version, digest
        )
        if existing is not None and existing["status"] == "ready":
            return self._finish_operation(
                operation,
                installation_id=existing["id"],
                evidence=evidence,
                message=(
                    f"{spec.canonical} {resolved_version} already installed; "
                    "replayed existing record"
                ),
                execution=execution,
                replayed=True,
            )
        record = {
            "id": f"cpi_{uuid.uuid4().hex}",
            "requested_package_spec": operation["requested_package_spec"],
            "package_name": spec.package_name,
            "marketplace": spec.marketplace,
            "requested_version": spec.requested_version,
            "resolved_version": resolved_version,
            "source_type": source_type,
            "artifact_digest": digest,
            "artifact_path": str(artifact.path),
            "claude_cli_version": cli_version,
            "cli_git_commit_sha": cli_git_commit_sha,
            "manifest_json": json.dumps(manifest, ensure_ascii=False, sort_keys=True)
            if manifest is not None
            else None,
            "component_inventory_json": json.dumps(
                inventory, ensure_ascii=False, sort_keys=True
            ),
            "compatibility_json": json.dumps(
                compatibility or {}, ensure_ascii=False, sort_keys=True
            ),
            "status": "ready",
            "operation_id": operation["id"],
            "file_count": artifact.file_count,
            "created_at": _now(),
            "updated_at": _now(),
            "installed_at": _now(),
        }
        with self.db:
            _insert_installation(self.db, record)
        return self._finish_operation(
            operation,
            installation_id=record["id"],
            evidence=evidence,
            message=(
                f"Installed {spec.canonical} {resolved_version} "
                f"({digest[:19]}…)"
            ),
            execution=execution,
            replayed=False,
        )
