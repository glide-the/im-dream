"""User-scoped platform credential identity for Claude MCP operations.

[Input] Authenticated platform actor IDs, shared Agent CLI resolver, and Claude MCP runtime settings.
[Output] A user-level Linux/macOS CLAUDE_CONFIG_DIR identity using the same system CLI as Agent.
[Pos] Safety boundary separating pre-thread Resources authentication from per-thread credential projections.
[Sync] 2026-08-19: replace the disabled placeholder with the production file-backed user identity.
[Sync] 2026-08-19: allowlist only OS/network/CLI runtime environment keys so backend secrets are not inherited.
[Sync] 2026-08-19: allow the reviewed macOS config-dir-keyed Keychain capability.
[Sync] 2026-08-20: fail closed when a Darwin CLI lacks the secure-storage selector used by Agent reuse.
[Sync] 2026-08-21: use a neutral CLI cwd so ancestor project `.mcp.json` files cannot leak into a platform-user identity.
"""

from __future__ import annotations

import hashlib
import os
from functools import lru_cache
from pathlib import Path
from typing import Callable, Protocol

from .contracts import (
    ClaudeMcpError,
    ClaudeMcpErrorCode,
    ClaudeMcpRuntimeIdentity,
)
from .credentials import (
    ClaudeMcpCredentialError,
    ClaudeMcpCredentialSynchronizer,
    resolve_user_paths,
)
from .settings import ClaudeMcpSettings

try:
    from libs.claude_agent_kit.server.sdk_env import resolve_claude_cli_path
except ModuleNotFoundError:
    from backend.libs.claude_agent_kit.server.sdk_env import resolve_claude_cli_path


class ClaudeMcpIdentityProvider(Protocol):
    def resolve(self, actor_id: str) -> ClaudeMcpRuntimeIdentity: ...


_SAFE_RUNTIME_ENV_NAMES = frozenset(
    {
        "PATH",
        "HOME",
        "USER",
        "LOGNAME",
        "SHELL",
        "LANG",
        "LANGUAGE",
        "TZ",
        "TERM",
        "COLORTERM",
        "TMPDIR",
        "TEMP",
        "TMP",
        "SSL_CERT_FILE",
        "SSL_CERT_DIR",
        "NODE_EXTRA_CA_CERTS",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "NO_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
        "no_proxy",
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC",
        "CLAUDE_CODE_TMPDIR",
    }
)

_SECURE_STORAGE_CLI_MARKER = b"CLAUDE_SECURESTORAGE_CONFIG_DIR"


@lru_cache(maxsize=8)
def _cli_has_secure_storage_marker(executable: str) -> bool:
    """Boundedly scan the exact CLI for its shipped secure-store selector."""

    path = Path(executable)
    try:
        with path.open("rb") as handle:
            overlap = b""
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    return False
                data = overlap + chunk
                if _SECURE_STORAGE_CLI_MARKER in data:
                    return True
                overlap = data[-len(_SECURE_STORAGE_CLI_MARKER) :]
    except OSError:
        return False


def _safe_runtime_env(source: dict[str, str] | None = None) -> dict[str, str]:
    values = os.environ if source is None else source
    return {
        str(key): str(value)
        for key, value in values.items()
        if value is not None
        and (key in _SAFE_RUNTIME_ENV_NAMES or key.startswith("LC_"))
    }


class PlatformClaudeMcpIdentityProvider:
    """Resolve one isolated pre-thread CLI home for each platform user."""

    def __init__(
        self,
        settings: ClaudeMcpSettings | None = None,
        *,
        synchronizer: ClaudeMcpCredentialSynchronizer | None = None,
        secure_storage_marker_checker: Callable[[str], bool] = _cli_has_secure_storage_marker,
    ) -> None:
        self.settings = settings or ClaudeMcpSettings.from_env()
        self.synchronizer = synchronizer or ClaudeMcpCredentialSynchronizer(
            self.settings
        )
        self._secure_storage_marker_checker = secure_storage_marker_checker

    def resolve(self, actor_id: str) -> ClaudeMcpRuntimeIdentity:
        try:
            self.synchronizer.require_supported()
            paths = resolve_user_paths(actor_id, self.settings)
        except ClaudeMcpCredentialError as exc:
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.IDENTITY_UNAVAILABLE,
                "Claude MCP requires an isolated platform user credential identity.",
            ) from exc
        executable = resolve_claude_cli_path()
        if not executable:
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.CLI_UNAVAILABLE,
                "Claude Code system CLI is unavailable.",
            )
        if (
            self.synchronizer.store_kind == "secure_storage"
            and not self._secure_storage_marker_checker(executable)
        ):
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.IDENTITY_UNAVAILABLE,
                "Claude Code CLI does not expose the required macOS secure-storage selector.",
            )
        fingerprint = hashlib.sha256(
            b"ink-claude-mcp-identity-v1\0"
            + str(paths.root).encode("utf-8")
            + b"\0"
            + executable.encode("utf-8")
        ).hexdigest()
        return ClaudeMcpRuntimeIdentity(
            command=(executable,),
            config_dir=paths.config_dir,
            # Claude walks cwd ancestors for project `.mcp.json`. The managed
            # runtime lives below the operator's home/repository, so using its
            # workspace would merge unrelated project servers into every
            # platform user and make user-scope removal target the wrong scope.
            # The filesystem anchor is neutral; mutable state remains isolated
            # in the actor-specific config directory above.
            cwd=Path(paths.root.anchor).resolve(),
            env=_safe_runtime_env(),
            fingerprint=fingerprint,
        )


# Transitional import alias for the still-unreleased first implementation.
FileBackedClaudeMcpIdentityProvider = PlatformClaudeMcpIdentityProvider
