"""Immutable shared plugin artifact store.

Artifacts are directories named ``<package>@<marketplace>@sha256-<digest>``
under the managed ``artifacts/`` root.  They are copied from the real CLI
cache (or a server-declared platform-builtin source), verified by digest,
and marked read-only.  Re-importing the same content returns the existing
artifact (content-addressed idempotency).  No symlinks are accepted and no
path may escape the artifacts root.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil

from . import runtime
from .digest import compute_plugin_digest, digest_is_valid
from .package_spec import PackageSpec


class ArtifactStoreError(RuntimeError):
    """Raised when an artifact cannot be imported, found, or verified."""


@dataclass(frozen=True)
class Artifact:
    package_name: str
    marketplace: str
    digest: str
    path: Path
    file_count: int

    @property
    def dir_name(self) -> str:
        return f"{self.package_name}@{self.marketplace}@{self.digest.replace(':', '-')}"


def artifact_dir_name(package_name: str, marketplace: str, digest: str) -> str:
    if not digest_is_valid(digest):
        raise ArtifactStoreError(f"invalid artifact digest: {digest!r}")
    return f"{package_name}@{marketplace}@{digest.replace(':', '-')}"


def _count_files(root: Path) -> int:
    from .digest import entry_is_excluded

    count = 0
    for item in root.rglob("*"):
        relative = item.relative_to(root)
        if entry_is_excluded(relative):
            continue
        if item.is_file():
            count += 1
    return count


def _assert_no_escaping_symlinks(root: Path) -> None:
    """Reject symlinks that are absolute or resolve outside *root*.

    Mirrors the CLI's own policy (plugins-reference): symlinks whose target
    stays inside the plugin directory are preserved as relative links;
    anything pointing outside is a security risk and is refused.
    """
    root = root.resolve()
    for item in root.rglob("*"):
        if not item.is_symlink():
            continue
        raw_target = os.readlink(item)
        if os.path.isabs(raw_target):
            raise ArtifactStoreError(
                f"plugin tree contains an absolute symlink, refusing: {item}"
            )
        resolved = (item.parent / raw_target).resolve()
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise ArtifactStoreError(
                f"plugin tree contains a symlink escaping the plugin root: "
                f"{item} -> {raw_target}"
            ) from exc


def _make_read_only(root: Path) -> None:
    for item in sorted(root.rglob("*")):
        try:
            item.chmod(0o555 if item.is_dir() else 0o444)
        except OSError:  # pragma: no cover - best effort
            pass
    try:
        root.chmod(0o555)
    except OSError:  # pragma: no cover
        pass


def _make_writable(root: Path) -> None:
    for item in sorted(root.rglob("*")):
        try:
            item.chmod(0o755 if item.is_dir() else 0o644)
        except OSError:  # pragma: no cover
            pass
    try:
        root.chmod(0o755)
    except OSError:  # pragma: no cover
        pass


def import_tree(source: Path, *, package_name: str, marketplace: str) -> Artifact:
    """Import *source* into the store and return the immutable artifact.

    The source digest is computed first; if an artifact with the same
    content-addressed name already exists and verifies, it is returned
    unchanged (idempotent replay).
    """
    source = Path(source).resolve()
    if not source.is_dir():
        raise ArtifactStoreError(f"plugin source directory is missing: {source}")
    digest = compute_plugin_digest(source)
    dir_name = artifact_dir_name(package_name, marketplace, digest)
    artifacts_root = runtime.get_artifacts_root().resolve()
    target = artifacts_root / dir_name
    # Containment guard — the computed name comes from validated package
    # tokens, but verify anyway before touching the filesystem.
    try:
        target.resolve(strict=False).relative_to(artifacts_root)
    except ValueError as exc:
        raise ArtifactStoreError(
            f"artifact path escapes the managed store: {target}"
        ) from exc
    if target.is_dir():
        existing_digest = compute_plugin_digest(target)
        if existing_digest == digest:
            return Artifact(
                package_name=package_name,
                marketplace=marketplace,
                digest=digest,
                path=target,
                file_count=_count_files(target),
            )
        raise ArtifactStoreError(
            f"artifact {dir_name} exists but fails digest verification "
            f"({existing_digest} != {digest}); refusing to overwrite"
        )
    staging = artifacts_root / f".staging-{os.getpid()}-{dir_name}"
    if staging.exists():
        shutil.rmtree(staging, ignore_errors=True)
    _assert_no_escaping_symlinks(source)
    # Preserve in-tree relative symlinks (the CLI keeps them; our digest
    # hashes the link target string, so copies must keep links as links).
    shutil.copytree(source, staging, symlinks=True)
    # Drop volatile CLI runtime markers and platform metadata junk (Finder
    # .DS_Store / AppleDouble companions etc.) from the staged copy so the
    # immutable artifact stays clean.
    from .digest import EXCLUDED_DIR_NAMES, entry_is_excluded

    for volatile in staging.rglob(".in_use"):
        if volatile.is_dir():
            shutil.rmtree(volatile, ignore_errors=True)
    for item in staging.rglob("*"):
        rel = item.relative_to(staging)
        if any(part in EXCLUDED_DIR_NAMES for part in rel.parts):
            continue  # .in_use handled above; .git retained by design
        if not entry_is_excluded(rel):
            continue
        if item.is_symlink() or item.is_file():
            item.unlink()
    staged_digest = compute_plugin_digest(staging)
    if staged_digest != digest:
        shutil.rmtree(staging, ignore_errors=True)
        raise ArtifactStoreError(
            f"staged artifact digest mismatch ({staged_digest} != {digest})"
        )
    # Rename before read-only: moving a directory rewrites its ``..`` entry,
    # which macOS refuses on a non-writable directory.
    staging.rename(target)
    _make_read_only(target)
    return Artifact(
        package_name=package_name,
        marketplace=marketplace,
        digest=digest,
        path=target,
        file_count=_count_files(target),
    )


def get_artifact(package_name: str, marketplace: str, digest: str) -> Artifact:
    """Locate an artifact and verify its digest before returning it."""
    artifacts_root = runtime.get_artifacts_root().resolve()
    target = (artifacts_root / artifact_dir_name(package_name, marketplace, digest))
    try:
        target.resolve(strict=False).relative_to(artifacts_root)
    except ValueError as exc:
        raise ArtifactStoreError(
            f"artifact path escapes the managed store: {target}"
        ) from exc
    if not target.is_dir():
        raise ArtifactStoreError(f"artifact is missing: {target}")
    actual = compute_plugin_digest(target)
    if actual != digest:
        raise ArtifactStoreError(
            f"artifact digest mismatch: expected {digest}, found {actual}"
        )
    return Artifact(
        package_name=package_name,
        marketplace=marketplace,
        digest=digest,
        path=target,
        file_count=_count_files(target),
    )


def copy_into_workspace(artifact: Artifact, destination: Path) -> Path:
    """Copy an artifact into an agent workspace plugin slot.

    The destination is created as a writable copy (agent workspaces are
    per-thread scratch, not part of the immutable store).  The copy is
    digest-verified after writing.
    """
    destination = Path(destination)
    if destination.exists():
        shutil.rmtree(destination, ignore_errors=True)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(artifact.path, destination, symlinks=True)
    _make_writable(destination)
    actual = compute_plugin_digest(destination)
    if actual != artifact.digest:
        shutil.rmtree(destination, ignore_errors=True)
        raise ArtifactStoreError(
            f"workspace copy digest mismatch: expected {artifact.digest}, "
            f"found {actual}"
        )
    return destination
