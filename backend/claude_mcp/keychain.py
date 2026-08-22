"""Non-secret macOS Claude Code Keychain identity metadata.

[Input] One absolute, server-owned Claude secure-storage config directory.
[Output] The deterministic Claude Code Keychain service label only; never the item value.
[Pos] Diagnostic identity helper; production code must not read, write, or delete Keychain secrets.
[Sync] 2026-08-20: remove Security CLI access after SecurityAgent proved it is not headless-safe.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


CLAUDE_KEYCHAIN_SERVICE_PREFIX = "Claude Code-credentials-"
KEYCHAIN_SERVICE_HASH_LENGTH = 8


class ClaudeMcpKeychainError(RuntimeError):
    """Safe Keychain identity validation failure without credential material."""


def claude_keychain_service_name(config_dir: Path | str) -> str:
    """Return Claude Code's non-secret service label for an absolute home."""

    path = Path(config_dir)
    if not path.is_absolute():
        raise ClaudeMcpKeychainError("Claude Keychain config home must be absolute.")
    canonical = path.resolve(strict=False)
    if canonical == Path("/"):
        raise ClaudeMcpKeychainError("Claude Keychain config home is invalid.")
    digest = hashlib.sha256(str(canonical).encode("utf-8")).hexdigest()
    return f"{CLAUDE_KEYCHAIN_SERVICE_PREFIX}{digest[:KEYCHAIN_SERVICE_HASH_LENGTH]}"
