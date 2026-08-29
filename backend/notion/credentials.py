"""Server-owned Notion credential homes and per-thread projections.

[Input] Canonical Dream actor IDs, server process policy, ntn file credentials, and validated Agent workspaces.
[Output] Private agentdata user homes, isolated auth-session/snapshot roots, atomic credential promotion, and thread-local Runtime projections.
[Pos] Notion credential identity boundary shared by connector auth and every Agent turn.
[Sync] 2026-08-28: replace process-user ~/.config and request-controlled homes with actor-scoped agentdata state and per-thread delivery.
[Sync] 2026-08-28: reserve the same actor root for connector-owned canonical snapshots while keeping them out of the CLI credential projection.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import stat
import tempfile
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

from claude_mcp.credentials import canonicalize_actor_id

from .errors import NotionConfigError, NotionCredentialError

USER_DIRECTORY_HASH_DOMAIN = b"ink-notion-user-v1\0"
NOTION_THREAD_HOME_NAME = ".notion-home"
NOTION_AUTH_FILENAME = "auth.json"
NOTION_PROJECTED_FILENAMES: tuple[str, ...] = (
    NOTION_AUTH_FILENAME,
    "config.json",
    "workspaces.json",
)
_AUTH_SESSION_RE = re.compile(r"^[a-f0-9]{32}$")
_DEFAULT_MAX_CREDENTIAL_FILE_BYTES = 1024 * 1024


def _default_runtime_root() -> Path:
    """Resolve Notion under server agentdata, never the process user's home."""

    agent_cwd = os.environ.get("AGENT_CWD", "").strip()
    if agent_cwd:
        candidate = Path(agent_cwd).expanduser()
        if candidate.is_absolute():
            return candidate.resolve(strict=False).parent / "notion-runtime"
    return Path(__file__).resolve().parents[1] / "data" / "notion-runtime"


def _positive_int_env(name: str, default: int, *, maximum: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if 0 < value <= maximum else default


@dataclass(frozen=True)
class NotionCredentialSettings:
    """Central server policy for Notion file credentials."""

    runtime_root: Path = field(default_factory=_default_runtime_root)
    max_credential_file_bytes: int = _DEFAULT_MAX_CREDENTIAL_FILE_BYTES

    @classmethod
    def from_env(cls) -> NotionCredentialSettings:
        raw_root = os.environ.get("INK_NOTION_RUNTIME_ROOT", "").strip()
        root = Path(raw_root).expanduser() if raw_root else _default_runtime_root()
        if not root.is_absolute():
            raise NotionConfigError("Notion runtime root must be an absolute server path.")
        return cls(
            runtime_root=root.resolve(strict=False),
            max_credential_file_bytes=_positive_int_env(
                "INK_NOTION_MAX_CREDENTIAL_FILE_BYTES",
                _DEFAULT_MAX_CREDENTIAL_FILE_BYTES,
                maximum=16 * 1024 * 1024,
            ),
        )


@dataclass(frozen=True)
class NotionUserPaths:
    root: Path
    home: Path
    pending_root: Path
    snapshot_root: Path


@dataclass(frozen=True)
class NotionCredentialProjection:
    """Safe capability result; credential bytes and digest stay out of repr."""

    available: bool
    thread_home: Path | None = field(default=None, repr=False)
    revision: str | None = field(default=None, repr=False)


def _private_directory(path: Path, *, parents: bool = False) -> Path:
    try:
        info = path.lstat()
    except FileNotFoundError:
        path.mkdir(mode=0o700, parents=parents)
        info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise NotionCredentialError("Notion credential directory is not safe.")
    os.chmod(path, 0o700, follow_symlinks=False)
    return path


def _remove_private_tree(path: Path, *, parent: Path) -> None:
    """Remove exactly one validated child without following a symlink."""

    try:
        info = path.lstat()
    except FileNotFoundError:
        return
    if path.parent.resolve(strict=True) != parent.resolve(strict=True):
        raise NotionCredentialError("Notion credential cleanup target is invalid.")
    if stat.S_ISLNK(info.st_mode):
        path.unlink()
        return
    if not stat.S_ISDIR(info.st_mode):
        raise NotionCredentialError("Notion credential cleanup target is not a directory.")
    shutil.rmtree(path)


def _read_private_file(path: Path, *, max_bytes: int) -> bytes | None:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise NotionCredentialError("Notion credential material is not a regular file.")
    if info.st_size > max_bytes:
        raise NotionCredentialError("Notion credential material exceeds the size limit.")

    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        payload = bytearray()
        while len(payload) <= max_bytes:
            chunk = os.read(descriptor, min(65536, max_bytes + 1 - len(payload)))
            if not chunk:
                break
            payload.extend(chunk)
    finally:
        os.close(descriptor)
    if len(payload) > max_bytes:
        raise NotionCredentialError("Notion credential material exceeds the size limit.")
    os.chmod(path, 0o600, follow_symlinks=False)
    return bytes(payload)


def _write_private_file(path: Path, payload: bytes) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            descriptor = -1
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600, follow_symlinks=False)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


class NotionCredentialStore:
    """Own actor-level ntn homes and project them into Agent threads."""

    def __init__(
        self,
        settings: NotionCredentialSettings | None = None,
        *,
        workspace_root_provider: Callable[[], Path] | None = None,
        thread_ids_provider: Callable[[int], Iterable[object]] | None = None,
    ) -> None:
        self.settings = settings or NotionCredentialSettings.from_env()
        self._workspace_root_provider = workspace_root_provider
        self._thread_ids_provider = thread_ids_provider

    def user_paths(self, actor_id: str | int) -> NotionUserPaths:
        try:
            canonical = canonicalize_actor_id(str(actor_id))
        except Exception as exc:
            raise NotionCredentialError("Notion actor identity is invalid.") from exc
        digest = hashlib.sha256(
            USER_DIRECTORY_HASH_DOMAIN + canonical.encode("ascii")
        ).hexdigest()
        root = self.settings.runtime_root
        if not root.is_absolute():
            raise NotionCredentialError("Notion runtime root must be absolute.")
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        _private_directory(root)
        users_root = _private_directory(root / "users")
        user_root = _private_directory(users_root / digest)
        return NotionUserPaths(
            root=user_root,
            home=_private_directory(user_root / "home"),
            pending_root=_private_directory(user_root / "pending"),
            snapshot_root=_private_directory(user_root / "snapshots"),
        )

    def begin_auth(self, actor_id: str | int, auth_session_id: str) -> Path:
        """Create one empty private pending home without touching effective auth."""

        if not _AUTH_SESSION_RE.fullmatch(str(auth_session_id)):
            raise NotionCredentialError("Notion auth session identity is invalid.")
        paths = self.user_paths(actor_id)
        for entry in list(paths.pending_root.iterdir()):
            _remove_private_tree(entry, parent=paths.pending_root)
        return _private_directory(paths.pending_root / str(auth_session_id))

    def pending_home(self, actor_id: str | int, auth_session_id: str) -> Path:
        if not _AUTH_SESSION_RE.fullmatch(str(auth_session_id)):
            raise NotionCredentialError("Notion auth session identity is invalid.")
        paths = self.user_paths(actor_id)
        path = paths.pending_root / str(auth_session_id)
        try:
            info = path.lstat()
        except FileNotFoundError as exc:
            raise NotionCredentialError("Notion authorization session is no longer active.") from exc
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise NotionCredentialError("Notion authorization session is not safe.")
        os.chmod(path, 0o700, follow_symlinks=False)
        return path

    def abort_auth(self, actor_id: str | int, auth_session_id: str) -> None:
        paths = self.user_paths(actor_id)
        if not _AUTH_SESSION_RE.fullmatch(str(auth_session_id)):
            raise NotionCredentialError("Notion auth session identity is invalid.")
        _remove_private_tree(paths.pending_root / str(auth_session_id), parent=paths.pending_root)

    def promote_auth(self, actor_id: str | int, auth_session_id: str) -> Path:
        """Atomically replace effective auth only after ntn produced auth.json."""

        paths = self.user_paths(actor_id)
        pending = self.pending_home(actor_id, auth_session_id)
        if _read_private_file(
            pending / NOTION_AUTH_FILENAME,
            max_bytes=self.settings.max_credential_file_bytes,
        ) is None:
            raise NotionCredentialError(
                "Notion authorization completed without a usable credential. Reconnect Notion."
            )
        for filename in NOTION_PROJECTED_FILENAMES:
            _read_private_file(
                pending / filename,
                max_bytes=self.settings.max_credential_file_bytes,
            )

        backup = paths.root / ".home-previous"
        _remove_private_tree(backup, parent=paths.root)
        if paths.home.exists():
            os.replace(paths.home, backup)
        try:
            os.replace(pending, paths.home)
        except BaseException:
            if backup.exists() and not paths.home.exists():
                os.replace(backup, paths.home)
            raise
        _remove_private_tree(backup, parent=paths.root)
        _private_directory(paths.home)
        return paths.home

    def effective_home(self, actor_id: str | int, *, require_credentials: bool = True) -> Path:
        paths = self.user_paths(actor_id)
        if require_credentials and _read_private_file(
            paths.home / NOTION_AUTH_FILENAME,
            max_bytes=self.settings.max_credential_file_bytes,
        ) is None:
            raise NotionCredentialError(
                "Notion is not connected. Connect Notion in Resource Links and retry."
            )
        return paths.home

    def has_credentials(self, actor_id: str | int) -> bool:
        try:
            self.effective_home(actor_id, require_credentials=True)
        except NotionCredentialError:
            return False
        return True

    def _workspace_root(self) -> Path:
        if self._workspace_root_provider is not None:
            root = self._workspace_root_provider()
        else:
            from libs.claude_agent_kit.server.workspace import get_workspace_root

            root = get_workspace_root()
        if not root.is_absolute():
            raise NotionCredentialError("Agent workspace root must be absolute.")
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        return root.resolve(strict=True)

    def _validate_workspace(self, workspace: Path) -> Path:
        root = self._workspace_root()
        if not workspace.is_absolute():
            raise NotionCredentialError("Notion thread workspace is invalid.")
        try:
            info = workspace.lstat()
            resolved = workspace.resolve(strict=True)
        except (FileNotFoundError, OSError, RuntimeError) as exc:
            raise NotionCredentialError("Notion thread workspace does not exist.") from exc
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode) or resolved.parent != root:
            raise NotionCredentialError("Notion thread workspace escapes the Agent root.")
        return resolved

    def validate_thread_workspace(self, workspace: Path) -> Path:
        """Expose the shared thread boundary to sibling agentdata projections."""

        return self._validate_workspace(workspace)

    def clear_thread_projection(self, workspace: Path) -> None:
        resolved = self._validate_workspace(workspace)
        _remove_private_tree(resolved / NOTION_THREAD_HOME_NAME, parent=resolved)

    def project_thread(
        self,
        actor_id: str | int,
        workspace: Path,
    ) -> NotionCredentialProjection:
        """Refresh an immutable credential snapshot for exactly one thread."""

        resolved_workspace = self._validate_workspace(workspace)
        target = resolved_workspace / NOTION_THREAD_HOME_NAME
        try:
            source = self.effective_home(actor_id, require_credentials=True)
            payloads: dict[str, bytes] = {}
            for filename in NOTION_PROJECTED_FILENAMES:
                payload = _read_private_file(
                    source / filename,
                    max_bytes=self.settings.max_credential_file_bytes,
                )
                if payload is not None:
                    payloads[filename] = payload
            if NOTION_AUTH_FILENAME not in payloads:
                raise NotionCredentialError("Notion is not connected.")
        except NotionCredentialError:
            _remove_private_tree(target, parent=resolved_workspace)
            raise

        staging = Path(
            tempfile.mkdtemp(
                prefix=f".{NOTION_THREAD_HOME_NAME}.",
                dir=str(resolved_workspace),
            )
        )
        os.chmod(staging, 0o700, follow_symlinks=False)
        try:
            revision_hash = hashlib.sha256(b"ink-notion-projection-v1\0")
            for filename in NOTION_PROJECTED_FILENAMES:
                payload = payloads.get(filename)
                if payload is None:
                    continue
                _write_private_file(staging / filename, payload)
                revision_hash.update(filename.encode("utf-8") + b"\0" + payload)
            _remove_private_tree(target, parent=resolved_workspace)
            os.replace(staging, target)
            os.chmod(target, 0o700, follow_symlinks=False)
            return NotionCredentialProjection(
                available=True,
                thread_home=target,
                revision=revision_hash.hexdigest(),
            )
        finally:
            if staging.exists():
                _remove_private_tree(staging, parent=resolved_workspace)

    def _default_thread_ids(self, actor_id: int) -> Iterable[object]:
        import database

        return database.list_chat_threads(actor_id)

    def clear_user(self, actor_id: str | int) -> None:
        """Revoke the actor source and every existing owned thread projection."""

        canonical = canonicalize_actor_id(str(actor_id))
        provider = self._thread_ids_provider or self._default_thread_ids
        try:
            thread_rows = list(provider(int(canonical)))
        except Exception:  # noqa: BLE001
            thread_rows = []
        root = self._workspace_root()
        for row in thread_rows:
            thread_id = row.get("id") if isinstance(row, dict) else row
            if not isinstance(thread_id, str) or not thread_id or any(
                token in thread_id for token in ("/", "\\", "..")
            ):
                continue
            workspace = root / thread_id
            if not workspace.exists() or workspace.is_symlink():
                continue
            try:
                self.clear_thread_projection(workspace)
            except NotionCredentialError:
                continue

        paths = self.user_paths(canonical)
        _remove_private_tree(paths.home, parent=paths.root)
        _remove_private_tree(paths.pending_root, parent=paths.root)
        _remove_private_tree(paths.snapshot_root, parent=paths.root)
        _private_directory(paths.home)
        _private_directory(paths.pending_root)
        _private_directory(paths.snapshot_root)


__all__ = [
    "NOTION_AUTH_FILENAME",
    "NOTION_PROJECTED_FILENAMES",
    "NOTION_THREAD_HOME_NAME",
    "NotionCredentialProjection",
    "NotionCredentialSettings",
    "NotionCredentialStore",
    "NotionUserPaths",
]
