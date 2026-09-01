# [Input] backend/builtin_skills common/platform source tree and canonical Skill package manifests.
# [Output] Validated directory/.skill package catalog, safe file reads, exact directory links, and staged archive materialization.
# [Pos] Single builtin Skill package boundary shared by workspace publishing and connector capability metadata.
# [Sync] 2026-09-01: add common/platform discovery, canonical ZIP `.skill` validation, directory-source symlinks, global selected-ID collision checks, and flat archive publication.

"""Discover and materialize backend-owned Skill packages.

Source ownership is namespaced under ``backend/builtin_skills`` while Claude's
workspace discovery remains flat by canonical Skill ID.
"""

from __future__ import annotations

import os
import re
import shutil
import stat
import tempfile
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import yaml

COMMON_SKILL_NAMESPACE = "common"
DEFAULT_BUILTIN_SKILLS_ROOT = Path(__file__).resolve().parents[3] / "builtin_skills"
_IDENTIFIER_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")
_FRONTMATTER_PATTERN = re.compile(
    r"\A---[ \t]*\r?\n(?P<frontmatter>.*?)\r?\n---[ \t]*(?:\r?\n|\Z)",
    re.DOTALL,
)
_MAX_MANIFEST_BYTES = 256 * 1024


class BuiltinSkillPackageError(RuntimeError):
    """A server-owned Skill package cannot be safely cataloged or published."""


@dataclass(frozen=True)
class BuiltinSkillPackage:
    """One validated directory or ``.skill`` package."""

    namespace: str
    skill_id: str
    source_path: Path
    is_archive: bool


@dataclass(frozen=True)
class BuiltinSkillSyncResult:
    """Non-sensitive result of one builtin workspace refresh."""

    synced_ids: tuple[str, ...]
    removed_ids: tuple[str, ...]
    linked_source_paths: tuple[str, ...]


def _require_identifier(value: str, *, label: str) -> str:
    normalized = str(value or "").strip()
    if not _IDENTIFIER_PATTERN.fullmatch(normalized):
        raise BuiltinSkillPackageError(f"Invalid builtin Skill {label}.")
    return normalized


def _require_relative_package_path(relative_path: str) -> PurePosixPath:
    value = str(relative_path or "")
    candidate = PurePosixPath(value)
    if (
        not value
        or "\\" in value
        or candidate.is_absolute()
        or any(part in {"", ".", ".."} for part in candidate.parts)
    ):
        raise BuiltinSkillPackageError("Invalid builtin Skill package path.")
    return candidate


def _validate_zip_member(
    info: zipfile.ZipInfo,
    *,
    expected_skill_id: str,
) -> PurePosixPath | None:
    relative = _require_relative_package_path(info.filename.rstrip("/"))
    if relative.parts[0] != expected_skill_id:
        raise BuiltinSkillPackageError("Builtin .skill top-level directory is invalid.")
    unix_mode = (info.external_attr >> 16) & 0xFFFF
    if unix_mode and stat.S_ISLNK(unix_mode):
        raise BuiltinSkillPackageError("Builtin .skill symbolic links are not allowed.")
    if len(relative.parts) == 1:
        if info.is_dir():
            return None
        raise BuiltinSkillPackageError("Builtin .skill root entry is invalid.")
    return PurePosixPath(*relative.parts[1:])


def _archive_file_index(package: BuiltinSkillPackage) -> dict[str, zipfile.ZipInfo]:
    files: dict[str, zipfile.ZipInfo] = {}
    try:
        with zipfile.ZipFile(package.source_path, "r") as archive:
            for info in archive.infolist():
                relative = _validate_zip_member(
                    info,
                    expected_skill_id=package.skill_id,
                )
                if relative is None or info.is_dir():
                    continue
                key = relative.as_posix()
                if key in files:
                    raise BuiltinSkillPackageError(
                        "Builtin .skill contains duplicate file entries."
                    )
                files[key] = info
    except (OSError, zipfile.BadZipFile) as exc:
        raise BuiltinSkillPackageError("Builtin .skill archive is unavailable.") from exc
    if "SKILL.md" not in files:
        raise BuiltinSkillPackageError("Builtin .skill manifest is missing.")
    return files


def _directory_file_paths(package: BuiltinSkillPackage) -> dict[str, Path]:
    root = package.source_path
    if root.is_symlink() or not root.is_dir():
        raise BuiltinSkillPackageError("Builtin Skill directory is unavailable.")
    files: dict[str, Path] = {}
    try:
        entries = sorted(root.rglob("*"), key=lambda item: item.as_posix())
    except OSError as exc:
        raise BuiltinSkillPackageError("Builtin Skill directory is unavailable.") from exc
    for entry in entries:
        if entry.is_symlink():
            raise BuiltinSkillPackageError("Builtin Skill symbolic links are not allowed.")
        if not entry.is_file():
            continue
        relative = entry.relative_to(root).as_posix()
        _require_relative_package_path(relative)
        files[relative] = entry
    if "SKILL.md" not in files:
        raise BuiltinSkillPackageError("Builtin Skill manifest is missing.")
    return files


def list_builtin_skill_files(package: BuiltinSkillPackage) -> tuple[str, ...]:
    """Return every package-relative regular-file path in stable order."""

    files = (
        _archive_file_index(package)
        if package.is_archive
        else _directory_file_paths(package)
    )
    return tuple(sorted(files))


def read_builtin_skill_file(
    package: BuiltinSkillPackage,
    relative_path: str,
) -> bytes:
    """Read one validated package-relative file without persistent extraction."""

    relative = _require_relative_package_path(relative_path).as_posix()
    if package.is_archive:
        files = _archive_file_index(package)
        info = files.get(relative)
        if info is None:
            raise BuiltinSkillPackageError("Builtin Skill file is unavailable.")
        try:
            with zipfile.ZipFile(package.source_path, "r") as archive:
                return archive.read(info)
        except (OSError, KeyError, zipfile.BadZipFile) as exc:
            raise BuiltinSkillPackageError("Builtin Skill file is unavailable.") from exc

    files = _directory_file_paths(package)
    path = files.get(relative)
    if path is None:
        raise BuiltinSkillPackageError("Builtin Skill file is unavailable.")
    try:
        return path.read_bytes()
    except OSError as exc:
        raise BuiltinSkillPackageError("Builtin Skill file is unavailable.") from exc


def _manifest_name(package: BuiltinSkillPackage) -> str:
    content = read_builtin_skill_file(package, "SKILL.md")
    if len(content) > _MAX_MANIFEST_BYTES:
        raise BuiltinSkillPackageError("Builtin Skill manifest is too large.")
    try:
        text = content.decode("utf-8")
    except UnicodeError as exc:
        raise BuiltinSkillPackageError("Builtin Skill manifest is unavailable.") from exc
    match = _FRONTMATTER_PATTERN.match(text)
    if match is None:
        raise BuiltinSkillPackageError("Builtin Skill manifest metadata is invalid.")
    try:
        metadata = yaml.safe_load(match.group("frontmatter"))
    except yaml.YAMLError as exc:
        raise BuiltinSkillPackageError("Builtin Skill manifest metadata is invalid.") from exc
    if not isinstance(metadata, dict):
        raise BuiltinSkillPackageError("Builtin Skill manifest metadata is invalid.")
    return _require_identifier(str(metadata.get("name") or ""), label="manifest name")


def _package_from_source(namespace: str, source: Path) -> BuiltinSkillPackage:
    if source.is_symlink():
        raise BuiltinSkillPackageError("Builtin Skill package links are not allowed.")
    if source.is_dir():
        skill_id = _require_identifier(source.name, label="ID")
        is_archive = False
    elif source.is_file() and source.suffix.lower() == ".skill":
        skill_id = _require_identifier(source.stem, label="ID")
        is_archive = True
    else:
        raise BuiltinSkillPackageError("Builtin Skill source type is unsupported.")
    package = BuiltinSkillPackage(
        namespace=namespace,
        skill_id=skill_id,
        source_path=source,
        is_archive=is_archive,
    )
    if _manifest_name(package) != skill_id:
        raise BuiltinSkillPackageError("Builtin Skill package ID does not match its manifest.")
    return package


def discover_builtin_skill_packages(
    namespaces: Iterable[str],
    *,
    skills_root: Path | None = None,
) -> tuple[BuiltinSkillPackage, ...]:
    """Discover validated packages in the requested source namespaces."""

    root = skills_root or DEFAULT_BUILTIN_SKILLS_ROOT
    requested = sorted({_require_identifier(item, label="namespace") for item in namespaces})
    packages: list[BuiltinSkillPackage] = []
    seen_ids: set[str] = set()
    for namespace in requested:
        namespace_root = root / namespace
        if namespace_root.is_symlink():
            raise BuiltinSkillPackageError("Builtin Skill namespace links are not allowed.")
        if not namespace_root.is_dir():
            continue
        try:
            sources = sorted(namespace_root.iterdir(), key=lambda item: item.name)
        except OSError as exc:
            raise BuiltinSkillPackageError("Builtin Skill namespace is unavailable.") from exc
        for source in sources:
            if source.name.startswith("."):
                continue
            package = _package_from_source(namespace, source)
            if package.skill_id in seen_ids:
                raise BuiltinSkillPackageError(
                    "Duplicate builtin Skill ID across selected namespaces."
                )
            seen_ids.add(package.skill_id)
            packages.append(package)
    return tuple(packages)


def get_builtin_skill_package(
    namespace: str,
    skill_id: str,
    *,
    skills_root: Path | None = None,
) -> BuiltinSkillPackage:
    """Resolve one validated package by namespace and canonical ID."""

    expected = _require_identifier(skill_id, label="ID")
    for package in discover_builtin_skill_packages(
        (namespace,),
        skills_root=skills_root,
    ):
        if package.skill_id == expected:
            return package
    raise BuiltinSkillPackageError("Builtin Skill package was not found.")


def _known_builtin_skill_ids(skills_root: Path) -> set[str]:
    """Collect reserved IDs without opening inactive platform package content."""

    known: set[str] = set()
    if skills_root.is_symlink() or not skills_root.is_dir():
        return known
    for namespace_root in sorted(skills_root.iterdir(), key=lambda item: item.name):
        if (
            namespace_root.name.startswith(".")
            or namespace_root.is_symlink()
            or not namespace_root.is_dir()
        ):
            continue
        _require_identifier(namespace_root.name, label="namespace")
        for source in sorted(namespace_root.iterdir(), key=lambda item: item.name):
            if source.name.startswith(".") or source.is_symlink():
                continue
            if source.is_dir():
                known.add(_require_identifier(source.name, label="ID"))
            elif source.is_file() and source.suffix.lower() == ".skill":
                known.add(_require_identifier(source.stem, label="ID"))
    return known


def _materialize_package(package: BuiltinSkillPackage, staging: Path) -> None:
    staging.mkdir(mode=0o700, parents=True, exist_ok=False)
    if package.is_archive:
        files = _archive_file_index(package)
        try:
            with zipfile.ZipFile(package.source_path, "r") as archive:
                for relative, info in sorted(files.items()):
                    destination = staging / relative
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(info, "r") as source_handle, destination.open("wb") as target:
                        shutil.copyfileobj(source_handle, target)
                    unix_mode = (info.external_attr >> 16) & 0o777
                    if unix_mode:
                        destination.chmod(unix_mode)
        except (OSError, zipfile.BadZipFile) as exc:
            raise BuiltinSkillPackageError("Builtin .skill extraction failed.") from exc
    else:
        files = _directory_file_paths(package)
        for relative, source in sorted(files.items()):
            destination = staging / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

    staged = BuiltinSkillPackage(
        namespace=package.namespace,
        skill_id=package.skill_id,
        source_path=staging,
        is_archive=False,
    )
    if _manifest_name(staged) != package.skill_id:
        raise BuiltinSkillPackageError("Staged builtin Skill manifest is invalid.")


def materialize_skill_archive(
    archive_path: Path,
    staging: Path,
    *,
    expected_skill_id: str | None = None,
) -> str:
    """Validate and unpack one canonical ``.skill`` archive into *staging*."""

    package = _package_from_source(COMMON_SKILL_NAMESPACE, archive_path)
    if not package.is_archive:
        raise BuiltinSkillPackageError("Skill archive source type is unsupported.")
    if expected_skill_id is not None and package.skill_id != _require_identifier(
        expected_skill_id,
        label="ID",
    ):
        raise BuiltinSkillPackageError("Skill archive ID does not match its filename.")
    _materialize_package(package, staging)
    return package.skill_id


def _remove_workspace_skill(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
    elif path.is_dir():
        shutil.rmtree(path)


def sync_builtin_skill_packages(
    workspace: Path,
    *,
    enabled_platforms: Iterable[str] = (),
    skills_root: Path | None = None,
    prune_inactive_platforms: bool = False,
) -> BuiltinSkillSyncResult:
    """Publish common plus enabled-platform packages into ``workspace/skills``.

    Selected packages are fully validated first. Directory packages become
    source symlinks; archive packages are staged inside the thread before any
    existing target is replaced. Known but inactive platform IDs are removed
    precisely when requested; other workspace-owned Skill IDs are untouched.
    """

    root = skills_root or DEFAULT_BUILTIN_SKILLS_ROOT
    platforms = {
        _require_identifier(platform, label="namespace")
        for platform in enabled_platforms
    }
    platforms.discard(COMMON_SKILL_NAMESPACE)
    packages = discover_builtin_skill_packages(
        {COMMON_SKILL_NAMESPACE, *platforms},
        skills_root=root,
    )
    selected_ids = {package.skill_id for package in packages}
    known_ids = _known_builtin_skill_ids(root) if prune_inactive_platforms else set()
    destination_root = workspace / "skills"
    destination_root.mkdir(parents=True, exist_ok=True)

    staged: dict[str, Path] = {}
    try:
        for package in packages:
            if not package.is_archive:
                continue
            staging = Path(
                tempfile.mkdtemp(
                    prefix=f".builtin-{package.skill_id}.",
                    dir=destination_root,
                )
            )
            staging.rmdir()
            _materialize_package(package, staging)
            staged[package.skill_id] = staging

        removed: list[str] = []
        for skill_id in sorted(known_ids - selected_ids):
            destination = destination_root / skill_id
            if destination.exists() or destination.is_symlink():
                _remove_workspace_skill(destination)
                removed.append(skill_id)

        for package in packages:
            destination = destination_root / package.skill_id
            _remove_workspace_skill(destination)
            if package.is_archive:
                os.replace(staged.pop(package.skill_id), destination)
            else:
                destination.symlink_to(
                    package.source_path.resolve(strict=True),
                    target_is_directory=True,
                )

        return BuiltinSkillSyncResult(
            synced_ids=tuple(sorted(selected_ids)),
            removed_ids=tuple(removed),
            linked_source_paths=tuple(
                sorted(
                    str(package.source_path.resolve(strict=True))
                    for package in packages
                    if not package.is_archive
                )
            ),
        )
    finally:
        for staging in staged.values():
            if staging.exists():
                shutil.rmtree(staging, ignore_errors=True)


__all__ = [
    "COMMON_SKILL_NAMESPACE",
    "DEFAULT_BUILTIN_SKILLS_ROOT",
    "BuiltinSkillPackage",
    "BuiltinSkillPackageError",
    "BuiltinSkillSyncResult",
    "discover_builtin_skill_packages",
    "get_builtin_skill_package",
    "list_builtin_skill_files",
    "materialize_skill_archive",
    "read_builtin_skill_file",
    "sync_builtin_skill_packages",
]
