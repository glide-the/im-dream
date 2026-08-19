"""Non-secret macOS Claude MCP Keychain identity contracts.

[Input] Absolute and invalid secure-storage config homes.
[Output] Stable per-user service labels without any Keychain value access.
[Pos] Provider-free proof that backend code derives identity metadata only.
[Sync] 2026-08-20: prohibit Security CLI reads/writes/deletes and retain label derivation only.
"""

from __future__ import annotations

from pathlib import Path
import sys

import pytest


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from claude_mcp.keychain import ClaudeMcpKeychainError, claude_keychain_service_name


def test_keychain_service_is_stable_and_isolated_by_absolute_config_home(
    tmp_path: Path,
) -> None:
    first_home = (tmp_path / "users" / "first" / "config").resolve()
    other_home = (tmp_path / "users" / "other" / "config").resolve()

    first = claude_keychain_service_name(first_home)
    assert first == claude_keychain_service_name(first_home)
    assert first != claude_keychain_service_name(other_home)
    assert first.startswith("Claude Code-credentials-")
    assert len(first.removeprefix("Claude Code-credentials-")) == 8


@pytest.mark.parametrize("value", ["relative/config", "/"])
def test_keychain_service_rejects_unsafe_config_home(value: str) -> None:
    with pytest.raises(ClaudeMcpKeychainError):
        claude_keychain_service_name(value)
