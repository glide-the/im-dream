"""Real Claude plugin install orchestration.

[Input] Manual package specs or immutable Admin-approved Remote Marketplace receipts.
[Output] Lifecycle reports, verified immutable artifacts and Admin persistence evidence.
[Pos] Single production ClaudePlugin install pipeline used by Settings and Deck consumers.
[Sync] 2026-08-19: verify remote URL/ref/commit/manifests/full-plugin digest without using local-path catalog constants for entry installs.
[Sync] 2026-09-15: artifact and CLI checks are shared static methods for server-derived Admin metadata; algorithms unchanged.
[Sync] 2026-09-16: replace operation and installation SQL with the typed Admin report port.
[Sync] 2026-09-15: verify current canonical and immutable Admin 0.1.0 full-plugin digest receipts without weakening content checks.

Every install flows through the same pipeline:

    validate spec → (marketplace installs only) ensure marketplace +
    real `claude plugin install` → read the CLI's own registry → locate the
    plugin root → read the manifest → enumerate official component kinds →
    deterministic SHA-256 → import into the immutable artifact store →
    Admin report (status ready).

A failed step never produces a ``ready`` record; the operation evidence
(argv, cwd, CLI version, exit code, sanitized output, file-tree delta) is
always persisted.  Re-running an install that resolves to the same version
and digest replays the existing installation record.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any, Iterator, Literal, Protocol
from urllib.parse import urlsplit, urlunsplit

from . import artifact_store, cli, runtime
from .builtin_sources import (
    KNOWN_MARKETPLACE_REPOS,
    get_builtin_declaration,
    resolve_builtin_source,
    resolve_local_marketplace,
)
from .compatibility import cli_version_to_semver, version_satisfies
from .digest import compute_legacy_admin_plugin_digest, compute_plugin_digest
from .package_spec import PackageSpec, PackageSpecError, parse_package_spec
from services.admin_data.claude_plugin_data import (
    ClaudePluginExecutionEvidenceDTO,
    ClaudePluginInstallationEvidenceDTO,
    ClaudePluginInstallReportInputDTO,
    ClaudePluginMarketplaceSourceDTO,
    ClaudePluginOperationDTO,
)

MARKETPLACE_REMOTE_DRIFT = "CLAUDE_PLUGIN_MARKETPLACE_REMOTE_DRIFT"

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


def _normalized_remote_url(value: str) -> str:
    parsed = urlsplit(value.strip())
    path = parsed.path.rstrip("/")
    if path.endswith(".git"):
        path = path[:-4]
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, "", ""))


def _git_checkout_value(checkout: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(checkout), *args],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            env={"PATH": os.environ.get("PATH", "")},
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PluginInstallError(
            MARKETPLACE_REMOTE_DRIFT,
            "approved marketplace checkout could not be verified",
        ) from exc
    if result.returncode != 0:
        raise PluginInstallError(
            MARKETPLACE_REMOTE_DRIFT,
            "approved marketplace checkout has no verifiable git provenance",
        )
    return result.stdout.strip()


def _verified_remote_marketplace_checkout(
    spec: PackageSpec,
    source: ClaudePluginMarketplaceSourceDTO,
    evidence: dict[str, Any],
) -> None:
    known = _known_marketplaces().get(spec.marketplace)
    if not isinstance(known, dict):
        raise PluginInstallError(
            MARKETPLACE_REMOTE_DRIFT,
            "the Claude CLI did not register the approved marketplace",
        )
    install_location = Path(str(known.get("installLocation") or "")).resolve()
    marketplace_root = (runtime.get_config_dir() / "plugins" / "marketplaces").resolve()
    try:
        install_location.relative_to(marketplace_root)
    except ValueError as exc:
        raise PluginInstallError(
            MARKETPLACE_REMOTE_DRIFT,
            "the registered marketplace checkout is outside the managed runtime",
        ) from exc
    if not install_location.is_dir():
        raise PluginInstallError(
            MARKETPLACE_REMOTE_DRIFT,
            "the registered marketplace checkout is missing",
        )
    origin = _git_checkout_value(install_location, "remote", "get-url", "origin")
    commit_sha = _git_checkout_value(install_location, "rev-parse", "HEAD")
    manifest_path = install_location / ".claude-plugin" / "marketplace.json"
    try:
        observed_manifest_sha = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    except OSError as exc:
        raise PluginInstallError(
            MARKETPLACE_REMOTE_DRIFT,
            "the registered marketplace manifest is missing",
        ) from exc
    evidence["marketplace_revision"] = {
        "entry_id": source.entry_id,
        "remote_url": source.remote_url,
        "requested_ref": source.requested_ref,
        "approved_commit_sha": source.approved_commit_sha,
        "observed_commit_sha": commit_sha,
        "marketplace_manifest_sha256": source.marketplace_manifest_sha256,
        "plugin_manifest_sha256": source.plugin_manifest_sha256,
        "observed_marketplace_manifest_sha256": observed_manifest_sha,
    }
    if (
        _normalized_remote_url(origin) != _normalized_remote_url(source.remote_url)
        or commit_sha != source.approved_commit_sha
        or observed_manifest_sha != source.marketplace_manifest_sha256
    ):
        raise PluginInstallError(
            MARKETPLACE_REMOTE_DRIFT,
            "the remote marketplace checkout no longer matches the approved revision",
            detail={
                "entry_id": source.entry_id,
                "approved_commit_sha": source.approved_commit_sha,
                "observed_commit_sha": commit_sha,
            },
        )


def _ensure_marketplace(
    spec: PackageSpec,
    evidence: dict[str, Any],
    *,
    marketplace_entry: ClaudePluginMarketplaceSourceDTO | None = None,
) -> None:
    """Register the marketplace via the real CLI when not yet known."""
    if marketplace_entry is not None:
        if marketplace_entry.package_spec != spec.canonical:
            raise PluginInstallError(
                PLUGIN_SPEC_INVALID,
                "approved marketplace entry does not match the requested package",
            )
        if spec.marketplace not in _known_marketplaces():
            remote_source = marketplace_entry.remote_url
            if marketplace_entry.requested_ref:
                remote_source = f"{remote_source}#{marketplace_entry.requested_ref}"
            execution = cli.run_claude(
                ["plugin", "marketplace", "add", remote_source],
                cwd=runtime.get_install_workspace(),
            )
            evidence["marketplace_add"] = execution.to_json()
        else:
            execution = cli.run_claude(
                ["plugin", "marketplace", "update", spec.marketplace],
                cwd=runtime.get_install_workspace(),
            )
            evidence["marketplace_update"] = execution.to_json()
        if not execution.ok:
            raise PluginInstallError(
                PLUGIN_INSTALL_FAILED,
                f"claude plugin marketplace synchronization failed (exit {execution.exit_code})",
                detail={"exit_code": execution.exit_code, "stderr": execution.stderr[-500:]},
            )
        _verified_remote_marketplace_checkout(spec, marketplace_entry, evidence)
        return
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
# Admin persistence port. CLI/Git/filesystem execution remains in Dream.
# ---------------------------------------------------------------------------


class PluginInstallReporter(Protocol):
    def report(
        self, request: ClaudePluginInstallReportInputDTO
    ) -> ClaudePluginOperationDTO: ...


# ---------------------------------------------------------------------------
# Install service
# ---------------------------------------------------------------------------


class PluginInstallService:
    """Coordinates real CLI installs into the shared artifact store."""

    def __init__(self, reporter: PluginInstallReporter) -> None:
        self._reporter = reporter
    # -- public API ---------------------------------------------------------

    def install(
        self,
        raw_spec: str,
        *,
        source_type: str | None = None,
        marketplace_entry: ClaudePluginMarketplaceSourceDTO | None = None,
        timeout_seconds: int = 300,
        operation_id: str,
    ) -> dict[str, Any]:
        """Install *raw_spec* and return the operation record (finished)."""
        try:
            spec = parse_package_spec(raw_spec)
        except PackageSpecError as exc:
            raise PluginInstallError(PLUGIN_SPEC_INVALID, str(exc)) from exc

        if marketplace_entry is not None and (
            marketplace_entry.package_spec != spec.canonical
            or marketplace_entry.package_name != spec.package_name
            or marketplace_entry.marketplace_name != spec.marketplace
        ):
            raise PluginInstallError(
                PLUGIN_SPEC_INVALID,
                "approved marketplace entry does not match the requested package",
            )

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
            operation = self._begin_operation(
                spec,
                kind,
                operation_id=operation_id,
                marketplace_entry_id=(
                    marketplace_entry.entry_id if marketplace_entry else None
                ),
            )
            try:
                if kind == "platform-builtin":
                    result = self._install_platform_builtin(spec, operation)
                else:
                    result = self._install_from_marketplace(
                        spec,
                        operation,
                        timeout_seconds=timeout_seconds,
                        marketplace_entry=marketplace_entry,
                    )
            except PluginInstallError as exc:
                self._fail_operation(operation, exc)
                raise
            except (cli.ClaudeCliError, artifact_store.ArtifactStoreError) as exc:
                error = PluginInstallError(PLUGIN_INSTALL_FAILED, str(exc))
                self._fail_operation(operation, error)
                raise error from None
            except Exception as exc:
                # Unexpected filesystem or process failures must still move
                # the Admin operation to a terminal error state.
                error = PluginInstallError(
                    PLUGIN_INSTALL_FAILED, f"unexpected install failure: {exc}"
                )
                self._fail_operation(operation, error)
                raise error from None
        return result

    @staticmethod
    def check_cli_compatibility(record: dict[str, Any]) -> bool:
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

    @staticmethod
    def verify_installation_artifact(record: dict[str, Any]) -> bool:
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
        self,
        spec: PackageSpec,
        kind: str,
        *,
        operation_id: str,
        marketplace_entry_id: str | None = None,
    ) -> dict[str, Any]:
        reported = self._reporter.report(
            ClaudePluginInstallReportInputDTO(
                event="begin", operation_id=operation_id
            )
        )
        requested = spec.canonical + (
            f"@{spec.requested_version}" if spec.requested_version else ""
        )
        if (
            reported.id != operation_id
            or reported.requested_package_spec != requested
            or reported.marketplace_entry_id != marketplace_entry_id
            or reported.status != "running"
        ):
            raise PluginInstallError(
                PLUGIN_INSTALL_FAILED,
                "Admin returned a mismatched Claude Plugin operation",
            )
        operation = reported.model_dump(mode="json")
        operation["source_type"] = kind
        return operation

    def _progress(
        self,
        operation_id: str,
        *,
        phase: Literal["cli-install", "cli-validate", "verify", "import"],
        progress: Literal[20, 55, 80],
        message: str,
    ) -> None:
        self._reporter.report(
            ClaudePluginInstallReportInputDTO(
                event="progress",
                operation_id=operation_id,
                phase=phase,
                progress=progress,
                message=message,
            )
        )

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
        self._reporter.report(
            ClaudePluginInstallReportInputDTO(
                event="fail",
                operation_id=operation["id"],
                error_code=error.code,
                error_summary=str(error),
                evidence_path=str(evidence_path),
            )
        )

    def _finish_operation(
        self,
        operation: dict[str, Any],
        *,
        installation: ClaudePluginInstallationEvidenceDTO,
        evidence: dict[str, Any],
        execution: cli.CliExecution | None,
    ) -> dict[str, Any]:
        evidence.update(
            {
                "operation_id": operation["id"],
                "requested_package_spec": operation["requested_package_spec"],
                "status": "ready",
                "finished_at": _now(),
            }
        )
        evidence_path = cli.write_operation_evidence(operation["id"], evidence)
        execution_dto = (
            ClaudePluginExecutionEvidenceDTO(
                executable=execution.executable,
                argv=execution.argv,
                cwd=execution.cwd,
                cli_version=execution.cli_version,
                exit_code=execution.exit_code,
            )
            if execution is not None
            else None
        )
        finished = self._reporter.report(
            ClaudePluginInstallReportInputDTO(
                event="complete",
                operation_id=operation["id"],
                installation=installation,
                execution=execution_dto,
                evidence_path=str(evidence_path),
            )
        )
        evidence["installation_id"] = finished.installation_id
        evidence["replayed"] = "replayed existing record" in (finished.message or "")
        cli.write_operation_evidence(operation["id"], evidence)
        return finished.model_dump(mode="json")

    # -- marketplace install path --------------------------------------------

    def _install_from_marketplace(
        self,
        spec: PackageSpec,
        operation: dict[str, Any],
        *,
        timeout_seconds: int,
        marketplace_entry: ClaudePluginMarketplaceSourceDTO | None,
    ) -> dict[str, Any]:
        evidence: dict[str, Any] = {"source_type": operation["source_type"]}
        before = cli.snapshot_file_tree(runtime.get_config_dir())
        if marketplace_entry is None:
            _ensure_marketplace(spec, evidence)
        else:
            _ensure_marketplace(
                spec,
                evidence,
                marketplace_entry=marketplace_entry,
            )
        self._progress(
            operation["id"], phase="cli-install", progress=20,
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
        if marketplace_entry and marketplace_entry.plugin_manifest_sha256:
            manifest_path = (
                Path(registry_record["installPath"])
                / ".claude-plugin"
                / "plugin.json"
            )
            try:
                observed_plugin_manifest_sha = hashlib.sha256(
                    manifest_path.read_bytes()
                ).hexdigest()
            except OSError as exc:
                raise PluginInstallError(
                    MARKETPLACE_REMOTE_DRIFT,
                    "installed plugin manifest is missing from the approved revision",
                ) from exc
            evidence["marketplace_revision"][
                "observed_plugin_manifest_sha256"
            ] = observed_plugin_manifest_sha
            if observed_plugin_manifest_sha != marketplace_entry.plugin_manifest_sha256:
                raise PluginInstallError(
                    MARKETPLACE_REMOTE_DRIFT,
                    "installed plugin manifest no longer matches the approved revision",
                )
        return self._record_success(
            spec,
            operation,
            plugin_root=Path(registry_record["installPath"]),
            source_type=operation["source_type"],
            cli_version=execution.cli_version,
            cli_git_commit_sha=registry_record.get("gitCommitSha"),
            execution=execution,
            evidence=evidence,
            marketplace_entry_id=(
                marketplace_entry.entry_id if marketplace_entry else None
            ),
            compatibility=(
                marketplace_entry.compatibility if marketplace_entry else None
            ),
            approved_plugin_digest=(
                marketplace_entry.approved_plugin_digest
                if marketplace_entry
                else None
            ),
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
        self._progress(
            operation["id"], phase="cli-validate", progress=20,
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
            marketplace_entry_id=None,
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
        compatibility: dict[str, Any] | None = None,
        marketplace_entry_id: str | None = None,
        approved_plugin_digest: str | None = None,
    ) -> dict[str, Any]:
        self._progress(
            operation["id"], phase="verify", progress=55,
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
        if approved_plugin_digest is not None:
            legacy_admin_digest = compute_legacy_admin_plugin_digest(plugin_root)
            evidence["marketplace_revision"]["approved_plugin_digest"] = (
                approved_plugin_digest
            )
            evidence["marketplace_revision"]["observed_plugin_digest"] = digest
            evidence["marketplace_revision"][
                "observed_legacy_admin_plugin_digest"
            ] = legacy_admin_digest
            if approved_plugin_digest not in {digest, legacy_admin_digest}:
                raise PluginInstallError(
                    MARKETPLACE_REMOTE_DRIFT,
                    "installed plugin content no longer matches the approved revision",
                    detail={
                        "marketplace_entry_id": marketplace_entry_id,
                        "approved_plugin_digest": approved_plugin_digest,
                        "observed_plugin_digest": digest,
                    },
                )
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
        installation = ClaudePluginInstallationEvidenceDTO(
            package_name=spec.package_name,
            marketplace=spec.marketplace,
            requested_version=spec.requested_version,
            resolved_version=resolved_version,
            source_type=source_type,
            artifact_digest=digest,
            artifact_path=str(artifact.path),
            claude_cli_version=cli_version,
            cli_git_commit_sha=cli_git_commit_sha,
            manifest_json=(
                json.dumps(manifest, ensure_ascii=False, sort_keys=True)
                if manifest is not None
                else None
            ),
            component_inventory_json=json.dumps(
                inventory, ensure_ascii=False, sort_keys=True
            ),
            compatibility_json=json.dumps(
                compatibility or {}, ensure_ascii=False, sort_keys=True
            ),
            file_count=artifact.file_count,
        )
        return self._finish_operation(
            operation,
            installation=installation,
            evidence=evidence,
            execution=execution,
        )
