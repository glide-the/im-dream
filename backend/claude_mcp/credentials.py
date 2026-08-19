"""User-scoped Claude MCP state delivery into Agent thread homes.

[Input] Canonical platform user IDs, ClaudeMcpSettings, existing chat-thread IDs, and Agent workspace roots.
[Output] Safe user runtime paths, opaque MCP definitions for SDK injection, atomic Linux credential projections, and the macOS secure-storage home.
[Pos] Cross-platform identity boundary shared by Resources OAuth and every Agent startup.
[Sync] 2026-08-19: add Linux file-store identity, minimal JSON projection, revocation, and per-user/thread locks.
[Sync] 2026-08-20: keep macOS secrets inside Claude Code Keychain; Agent reuses the user secure-storage identity.
[Sync] 2026-08-20: return user MCP definitions to the Agent SDK directly because project-only setting sources ignore user-scope config files.
[Sync] 2026-08-20: expose a bounded opaque-definition read for the public SDK inventory probe.
"""

from __future__ import annotations

import asyncio
import copy
from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
from typing import Callable, Mapping

from .settings import ClaudeMcpSettings


USER_DIRECTORY_HASH_DOMAIN = b"ink-claude-mcp-user-v1\0"
CLAUDE_USER_CONFIG_FILENAME = ".claude.json"
CLAUDE_CREDENTIALS_FILENAME = ".credentials.json"
CLAUDE_MCP_SERVERS_KEY = "mcpServers"
CLAUDE_MCP_OAUTH_KEY = "mcpOAuth"
CLAUDE_THREAD_CONFIG_HOME_NAME = ".claude-home"


class ClaudeMcpCredentialError(RuntimeError):
    """Safe credential capability/synchronization failure without file data."""


class ClaudeMcpCredentialStoreUnsupported(ClaudeMcpCredentialError):
    """Raised when the host does not provide a supported credential store."""


@dataclass(frozen=True)
class ClaudeMcpUserPaths:
    root: Path
    config_dir: Path
    workspace: Path


@dataclass(frozen=True)
class ClaudeMcpSyncResult:
    config_changed: bool
    credentials_changed: bool
    credentials_present: bool
    mcp_configured: bool
    mcp_servers: Mapping[str, object] = field(default_factory=dict, repr=False)


@dataclass(frozen=True)
class ClaudeMcpSyncSummary:
    thread_count: int
    changed_count: int


def canonicalize_actor_id(actor_id: str) -> str:
    """Return the canonical positive decimal platform user ID."""

    value = str(actor_id).strip()
    if not value or not value.isdecimal():
        raise ClaudeMcpCredentialError("Platform user identity is invalid.")
    canonical = str(int(value))
    if canonical == "0":
        raise ClaudeMcpCredentialError("Platform user identity is invalid.")
    return canonical


def _private_directory(path: Path) -> Path:
    """Create/validate one server-owned directory without accepting symlinks."""

    try:
        info = path.lstat()
    except FileNotFoundError:
        path.mkdir(mode=0o700)
        info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise ClaudeMcpCredentialError("Credential directory is not a safe directory.")
    os.chmod(path, 0o700, follow_symlinks=False)
    return path


def resolve_user_paths(
    actor_id: str,
    settings: ClaudeMcpSettings,
) -> ClaudeMcpUserPaths:
    """Resolve and create one opaque, private user-level CLI identity root."""

    canonical = canonicalize_actor_id(actor_id)
    runtime_root = settings.runtime_root
    if not runtime_root.is_absolute():
        raise ClaudeMcpCredentialError("Claude MCP runtime root must be absolute.")
    digest = hashlib.sha256(
        USER_DIRECTORY_HASH_DOMAIN + canonical.encode("ascii")
    ).hexdigest()

    # ``settings.runtime_root`` is canonicalized centrally. Descendants are
    # created one component at a time so a user-controlled symlink cannot be
    # accepted as an identity or credential directory.
    runtime_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    _private_directory(runtime_root)
    users_root = _private_directory(runtime_root / "users")
    user_root = _private_directory(users_root / digest)
    return ClaudeMcpUserPaths(
        root=user_root,
        config_dir=_private_directory(user_root / "config"),
        workspace=_private_directory(user_root / "workspace"),
    )


def _read_private_json(
    path: Path,
    *,
    max_bytes: int,
) -> dict[str, object] | None:
    """Read one bounded private JSON object without following a symlink."""

    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise ClaudeMcpCredentialError("Claude credential material is not a regular file.")
    if info.st_mode & 0o077:
        raise ClaudeMcpCredentialError("Claude credential material has unsafe permissions.")
    if info.st_size > max_bytes:
        raise ClaudeMcpCredentialError("Claude credential material exceeds the size limit.")

    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        chunks: list[bytes] = []
        remaining = max_bytes + 1
        while remaining > 0:
            chunk = os.read(descriptor, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        payload = b"".join(chunks)
    finally:
        os.close(descriptor)
    if len(payload) > max_bytes:
        raise ClaudeMcpCredentialError("Claude credential material exceeds the size limit.")
    try:
        parsed = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ClaudeMcpCredentialError("Claude credential material is malformed.") from exc
    if not isinstance(parsed, dict):
        raise ClaudeMcpCredentialError("Claude credential material is malformed.")
    return parsed


def _managed_mapping(
    source: Mapping[str, object] | None,
    key: str,
) -> dict[str, object] | None:
    if source is None or key not in source:
        return None
    value = source[key]
    if not isinstance(value, dict):
        raise ClaudeMcpCredentialError("Claude MCP credential structure is malformed.")
    return value


def _validated_mcp_server_mapping(
    value: dict[str, object] | None,
) -> dict[str, dict[str, object]]:
    if value is None:
        return {}
    validated: dict[str, dict[str, object]] = {}
    for name, config in value.items():
        if not isinstance(name, str) or not name or not isinstance(config, dict):
            raise ClaudeMcpCredentialError("Claude MCP server configuration is malformed.")
        validated[name] = config
    return validated


def _lexists(path: Path) -> bool:
    try:
        path.lstat()
    except FileNotFoundError:
        return False
    return True


def _fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_private_json(path: Path, value: Mapping[str, object]) -> None:
    """Atomically replace one 0600 JSON file in its validated directory."""

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        payload = (
            json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n"
        ).encode("utf-8")
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            descriptor = -1
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600, follow_symlinks=False)
        _fsync_directory(path.parent)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _project_key(
    *,
    source_value: dict[str, object] | None,
    target_path: Path,
    target_key: str,
    max_bytes: int,
) -> bool:
    target = _read_private_json(target_path, max_bytes=max_bytes)
    updated: dict[str, object] = dict(target or {})
    if source_value is None:
        updated.pop(target_key, None)
    else:
        updated[target_key] = source_value
    if target is None and not updated:
        return False
    if target == updated:
        return False
    if not updated:
        target_path.unlink()
        _fsync_directory(target_path.parent)
        return True
    _write_private_json(target_path, updated)
    return True


class ClaudeMcpCredentialSynchronizer:
    """Project user-level MCP CLI state into every owned Agent thread home."""

    def __init__(
        self,
        settings: ClaudeMcpSettings | None = None,
        *,
        platform_name: str | None = None,
        thread_ids_provider: Callable[[int], list[dict]] | None = None,
        workspace_root_provider: Callable[[], Path] | None = None,
    ) -> None:
        self.settings = settings or ClaudeMcpSettings.from_env()
        self.platform_name = platform_name or os.sys.platform
        self._thread_ids_provider = thread_ids_provider
        self._workspace_root_provider = workspace_root_provider
        self._locks: dict[tuple[str, str], asyncio.Lock] = {}
        self._lock_registry = asyncio.Lock()

    @property
    def supported(self) -> bool:
        return self.platform_name.startswith("linux") or self.platform_name == "darwin"

    @property
    def store_kind(self) -> str:
        if self.platform_name.startswith("linux"):
            return "file"
        if self.platform_name == "darwin":
            return "secure_storage"
        return "unsupported"

    def require_supported(self) -> None:
        if not self.supported:
            raise ClaudeMcpCredentialStoreUnsupported(
                "Claude MCP requires a supported platform credential store."
            )

    @property
    def requires_file_credential_verification(self) -> bool:
        """Whether the service may safely verify the MCP OAuth file itself."""

        return self.store_kind == "file"

    def secure_storage_home(self, actor_id: str) -> Path | None:
        """Return Claude Code's user-scoped secure-store selector on macOS.

        Claude Code ignores ``.credentials.json`` for OAuth credentials on
        macOS and stores them in Keychain.  The backend must therefore never
        decrypt or copy that item.  Instead, every Agent subprocess receives
        this exact user config directory through
        ``CLAUDE_SECURESTORAGE_CONFIG_DIR`` while its ordinary
        ``CLAUDE_CONFIG_DIR`` remains thread-scoped.
        """

        self.require_supported()
        if self.store_kind != "secure_storage":
            return None
        return resolve_user_paths(actor_id, self.settings).config_dir

    async def _lock_for(self, actor_id: str, target: Path) -> asyncio.Lock:
        key = (canonicalize_actor_id(actor_id), str(target))
        async with self._lock_registry:
            return self._locks.setdefault(key, asyncio.Lock())

    def _workspace_root(self) -> Path:
        if self._workspace_root_provider is not None:
            root = self._workspace_root_provider()
        else:
            from libs.claude_agent_kit.server.workspace import get_workspace_root

            root = get_workspace_root()
        if not root.is_absolute():
            raise ClaudeMcpCredentialError("Agent workspace root must be absolute.")
        return root.resolve(strict=False)

    def _validate_target(self, target: Path) -> Path:
        if not target.is_absolute() or target.name != CLAUDE_THREAD_CONFIG_HOME_NAME:
            raise ClaudeMcpCredentialError("Thread credential target is invalid.")
        workspace_root = self._workspace_root()
        raw_workspace = target.parent
        if (
            not raw_workspace.name
            or "/" in raw_workspace.name
            or "\\" in raw_workspace.name
            or ".." in raw_workspace.name
        ):
            raise ClaudeMcpCredentialError("Thread workspace identity is invalid.")
        try:
            workspace = raw_workspace.resolve(strict=True)
        except (FileNotFoundError, OSError, RuntimeError) as exc:
            raise ClaudeMcpCredentialError("Thread workspace does not exist.") from exc
        if workspace.parent != workspace_root:
            raise ClaudeMcpCredentialError(
                "Thread credential target escapes the workspace root."
            )
        try:
            workspace_info = raw_workspace.lstat()
        except FileNotFoundError as exc:
            raise ClaudeMcpCredentialError("Thread workspace does not exist.") from exc
        if stat.S_ISLNK(workspace_info.st_mode) or not stat.S_ISDIR(workspace_info.st_mode):
            raise ClaudeMcpCredentialError("Thread workspace is not a safe directory.")
        canonical_target = workspace / CLAUDE_THREAD_CONFIG_HOME_NAME
        try:
            target_info = canonical_target.lstat()
        except FileNotFoundError:
            canonical_target.mkdir(mode=0o700)
            target_info = canonical_target.lstat()
        if stat.S_ISLNK(target_info.st_mode) or not stat.S_ISDIR(target_info.st_mode):
            raise ClaudeMcpCredentialError("Thread config home is not a safe directory.")
        os.chmod(canonical_target, 0o700, follow_symlinks=False)
        return canonical_target

    def _read_source_credentials(self, config_dir: Path) -> dict[str, object] | None:
        if self.store_kind != "file":
            raise ClaudeMcpCredentialStoreUnsupported(
                "Claude MCP credentials are not file-backed on this platform."
            )
        return _read_private_json(
            config_dir / CLAUDE_CREDENTIALS_FILENAME,
            max_bytes=self.settings.max_credential_file_bytes,
        )

    def _read_target_credentials(self, config_dir: Path) -> dict[str, object] | None:
        return _read_private_json(
            config_dir / CLAUDE_CREDENTIALS_FILENAME,
            max_bytes=self.settings.max_credential_file_bytes,
        )

    def _project_credentials(
        self,
        *,
        source_value: dict[str, object] | None,
        target: Path,
        existing_only: bool = False,
    ) -> bool:
        target_path = target / CLAUDE_CREDENTIALS_FILENAME
        if existing_only:
            current = _read_private_json(
                target_path,
                max_bytes=self.settings.max_credential_file_bytes,
            )
            if current is None or CLAUDE_MCP_OAUTH_KEY not in current:
                return False
        return _project_key(
            source_value=source_value,
            target_path=target_path,
            target_key=CLAUDE_MCP_OAUTH_KEY,
            max_bytes=self.settings.max_credential_file_bytes,
        )

    def _has_user_mcp_state_blocking(self, actor_id: str) -> bool:
        """Return whether the user store contains MCP config or OAuth state."""

        self.require_supported()
        source = resolve_user_paths(actor_id, self.settings).config_dir
        max_bytes = self.settings.max_credential_file_bytes
        source_config = _read_private_json(
            source / CLAUDE_USER_CONFIG_FILENAME,
            max_bytes=max_bytes,
        )
        source_credentials = (
            self._read_source_credentials(source)
            if self.requires_file_credential_verification
            else None
        )
        return bool(
            _managed_mapping(source_config, CLAUDE_MCP_SERVERS_KEY)
            or _managed_mapping(source_credentials, CLAUDE_MCP_OAUTH_KEY)
        )

    async def has_user_mcp_state(self, actor_id: str) -> bool:
        return await asyncio.to_thread(self._has_user_mcp_state_blocking, actor_id)

    def _read_user_mcp_servers_blocking(
        self,
        actor_id: str,
    ) -> dict[str, dict[str, object]]:
        """Return a detached opaque snapshot of the user's MCP definitions."""

        self.require_supported()
        source = resolve_user_paths(actor_id, self.settings).config_dir
        source_config = _read_private_json(
            source / CLAUDE_USER_CONFIG_FILENAME,
            max_bytes=self.settings.max_credential_file_bytes,
        )
        servers = _validated_mcp_server_mapping(
            _managed_mapping(source_config, CLAUDE_MCP_SERVERS_KEY)
        )
        return copy.deepcopy(servers)

    async def read_user_mcp_servers(
        self,
        actor_id: str,
    ) -> Mapping[str, object]:
        """Read user definitions without exposing their values in repr/logs."""

        return await asyncio.to_thread(
            self._read_user_mcp_servers_blocking,
            actor_id,
        )

    def _has_user_mcp_credentials_blocking(self, actor_id: str) -> bool:
        self.require_supported()
        if not self.requires_file_credential_verification:
            raise ClaudeMcpCredentialStoreUnsupported(
                "macOS secure credentials must be verified by Claude Code itself."
            )
        source = resolve_user_paths(actor_id, self.settings).config_dir
        return bool(
            _managed_mapping(
                self._read_source_credentials(source),
                CLAUDE_MCP_OAUTH_KEY,
            )
        )

    async def has_user_mcp_credentials(self, actor_id: str) -> bool:
        return await asyncio.to_thread(
            self._has_user_mcp_credentials_blocking,
            actor_id,
        )

    def _sync_thread_blocking(
        self,
        actor_id: str,
        thread_config_home: Path,
    ) -> ClaudeMcpSyncResult:
        self.require_supported()
        source = resolve_user_paths(actor_id, self.settings).config_dir
        source_config_path = source / CLAUDE_USER_CONFIG_FILENAME
        target_config_path = thread_config_home / CLAUDE_USER_CONFIG_FILENAME

        # New users with neither a user-level source nor an old thread snapshot
        # need no filesystem mutation. The synchronization call still occurs on
        # every turn, while test harnesses and unconfigured users avoid creating
        # a thread config home solely for an empty MCP projection.
        source_candidates = [source_config_path]
        if self.requires_file_credential_verification:
            source_candidates.append(source / CLAUDE_CREDENTIALS_FILENAME)
        if not any(
            _lexists(path)
            for path in (
                *source_candidates,
                target_config_path,
                thread_config_home / CLAUDE_CREDENTIALS_FILENAME,
            )
        ):
            return ClaudeMcpSyncResult(False, False, False, False)

        target = self._validate_target(thread_config_home)
        max_bytes = self.settings.max_credential_file_bytes

        source_config = _read_private_json(
            source_config_path,
            max_bytes=max_bytes,
        )
        source_credentials = (
            self._read_source_credentials(source)
            if self.requires_file_credential_verification
            else None
        )
        mcp_servers = _validated_mcp_server_mapping(
            _managed_mapping(source_config, CLAUDE_MCP_SERVERS_KEY)
        )
        mcp_oauth = _managed_mapping(source_credentials, CLAUDE_MCP_OAUTH_KEY)

        # Agent SDK deliberately loads project settings only. User-scope
        # `.claude.json#mcpServers` would therefore be ignored if copied into
        # the thread config home. Remove any obsolete snapshot and return the
        # opaque definitions for direct official SDK `mcp_servers`
        # injection instead. This also avoids `.mcp.json` approval prompts.
        config_changed = _project_key(
            source_value=None,
            target_path=target / CLAUDE_USER_CONFIG_FILENAME,
            target_key=CLAUDE_MCP_SERVERS_KEY,
            max_bytes=max_bytes,
        )
        credentials_changed = self._project_credentials(
            source_value=mcp_oauth,
            target=target,
        )
        return ClaudeMcpSyncResult(
            config_changed=config_changed,
            credentials_changed=credentials_changed,
            credentials_present=bool(mcp_oauth),
            mcp_configured=bool(mcp_servers),
            mcp_servers=copy.deepcopy(mcp_servers or {}),
        )

    async def sync_thread(
        self,
        actor_id: str,
        thread_config_home: Path | str,
    ) -> ClaudeMcpSyncResult:
        target = Path(thread_config_home)
        lock = await self._lock_for(actor_id, target)
        async with lock:
            return await asyncio.to_thread(
                self._sync_thread_blocking,
                actor_id,
                target,
            )

    def _source_mcp_oauth(self, actor_id: str) -> dict[str, object] | None:
        self.require_supported()
        if not self.requires_file_credential_verification:
            return None
        source = resolve_user_paths(actor_id, self.settings).config_dir
        return _managed_mapping(
            self._read_source_credentials(source),
            CLAUDE_MCP_OAUTH_KEY,
        )

    def _revoke_existing_target_blocking(
        self,
        target: Path,
        source_mcp_oauth: dict[str, object] | None,
    ) -> bool:
        canonical_target = self._validate_target(target)
        return self._project_credentials(
            source_value=source_mcp_oauth,
            target=canonical_target,
            existing_only=True,
        )

    def _thread_rows(self, actor_id: str) -> list[dict]:
        canonical = canonicalize_actor_id(actor_id)
        if self._thread_ids_provider is not None:
            return self._thread_ids_provider(int(canonical))
        import database

        return database.list_chat_threads(int(canonical))

    async def sync_existing_threads(self, actor_id: str) -> ClaudeMcpSyncSummary:
        self.require_supported()
        rows = await asyncio.to_thread(self._thread_rows, actor_id)
        workspace_root = self._workspace_root()
        thread_count = 0
        changed_count = 0
        for row in rows:
            thread_id = str(row.get("id") or "")
            if (
                not thread_id
                or "/" in thread_id
                or "\\" in thread_id
                or ".." in thread_id
            ):
                raise ClaudeMcpCredentialError("Stored thread identity is invalid.")
            workspace = workspace_root / thread_id
            if not workspace.is_dir() or workspace.is_symlink():
                continue
            result = await self.sync_thread(
                actor_id,
                workspace / CLAUDE_THREAD_CONFIG_HOME_NAME,
            )
            thread_count += 1
            if result.config_changed or result.credentials_changed:
                changed_count += 1
        return ClaudeMcpSyncSummary(
            thread_count=thread_count,
            changed_count=changed_count,
        )

    async def revoke_existing_thread_credentials(
        self,
        actor_id: str,
    ) -> ClaudeMcpSyncSummary:
        """Converge only targets that already contain an MCP credential projection."""

        self.require_supported()
        source_mcp_oauth = await asyncio.to_thread(self._source_mcp_oauth, actor_id)
        rows = await asyncio.to_thread(self._thread_rows, actor_id)
        workspace_root = self._workspace_root()
        thread_count = 0
        changed_count = 0
        for row in rows:
            thread_id = str(row.get("id") or "")
            if (
                not thread_id
                or "/" in thread_id
                or "\\" in thread_id
                or ".." in thread_id
            ):
                raise ClaudeMcpCredentialError("Stored thread identity is invalid.")
            workspace = workspace_root / thread_id
            if not workspace.is_dir() or workspace.is_symlink():
                continue
            target = workspace / CLAUDE_THREAD_CONFIG_HOME_NAME
            if not target.is_dir() or target.is_symlink():
                continue
            lock = await self._lock_for(actor_id, target)
            async with lock:
                changed = await asyncio.to_thread(
                    self._revoke_existing_target_blocking,
                    target,
                    source_mcp_oauth,
                )
            thread_count += 1
            if changed:
                changed_count += 1
        return ClaudeMcpSyncSummary(
            thread_count=thread_count,
            changed_count=changed_count,
        )


_default_synchronizer: ClaudeMcpCredentialSynchronizer | None = None


def get_default_credential_synchronizer() -> ClaudeMcpCredentialSynchronizer:
    global _default_synchronizer
    if _default_synchronizer is None:
        _default_synchronizer = ClaudeMcpCredentialSynchronizer()
    return _default_synchronizer
