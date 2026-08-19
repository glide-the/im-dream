"""Claude MCP user credential identity and thread projection contracts.

[Input] Test-owned user config roots and Agent thread config homes.
[Output] User isolation, Linux file projection, macOS secure-store reuse, revocation, permissions, and symlink evidence.
[Pos] Provider-free cross-platform credential-store tests; no real OAuth token or Claude CLI is used.
[Sync] 2026-08-19: cover the production Linux file-backed user-to-thread synchronization boundary.
[Sync] 2026-08-20: prove macOS never copies Keychain material and reuses a user secure-store selector.
[Sync] 2026-08-20: cover detached user MCP definition reads for inventory and Agent injection.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from claude_mcp.credentials import (
    CLAUDE_CREDENTIALS_FILENAME,
    CLAUDE_USER_CONFIG_FILENAME,
    ClaudeMcpCredentialError,
    ClaudeMcpCredentialStoreUnsupported,
    ClaudeMcpCredentialSynchronizer,
    resolve_user_paths,
)
from claude_mcp.settings import ClaudeMcpSettings
from claude_mcp.contracts import ClaudeMcpError, ClaudeMcpErrorCode
import claude_mcp.identity as identity_module
from claude_mcp.identity import FileBackedClaudeMcpIdentityProvider, _safe_runtime_env


def _settings(tmp_path: Path) -> ClaudeMcpSettings:
    return ClaudeMcpSettings(
        auth_timeout_seconds=3,
        command_timeout_seconds=3,
        terminate_grace_seconds=1,
        readiness_timeout_seconds=2,
        max_capture_bytes=65536,
        max_server_name_length=512,
        max_redirect_url_length=8192,
        runtime_root=(tmp_path / "runtime").resolve(),
        max_credential_file_bytes=65536,
    )


def _write_private_json(path: Path, value: dict[str, object]) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")
    path.chmod(0o600)


def _read_private_fixture(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _synchronizer(
    tmp_path: Path,
    *,
    thread_rows: list[dict] | None = None,
) -> ClaudeMcpCredentialSynchronizer:
    workspace_root = (tmp_path / "workspaces").resolve()
    workspace_root.mkdir(exist_ok=True)
    return ClaudeMcpCredentialSynchronizer(
        _settings(tmp_path),
        platform_name="linux",
        thread_ids_provider=lambda _user_id: list(thread_rows or []),
        workspace_root_provider=lambda: workspace_root,
    )


def test_user_roots_are_stable_private_and_isolated(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    first = resolve_user_paths("7", settings)
    repeated = resolve_user_paths("007", settings)
    other = resolve_user_paths("8", settings)

    assert first == repeated
    assert first.root != other.root
    assert first.root.name != "7"
    assert len(first.root.name) == 64
    for path in (settings.runtime_root, first.root, first.config_dir, first.workspace):
        assert path.stat().st_mode & 0o777 == 0o700


def test_user_mcp_definition_read_is_detached_and_actor_scoped(tmp_path: Path) -> None:
    synchronizer = _synchronizer(tmp_path)
    first = resolve_user_paths("7", synchronizer.settings)
    second = resolve_user_paths("8", synchronizer.settings)
    _write_private_json(
        first.config_dir / CLAUDE_USER_CONFIG_FILENAME,
        {"mcpServers": {"comfy": {"type": "http", "url": "https://example.test/mcp"}}},
    )
    _write_private_json(
        second.config_dir / CLAUDE_USER_CONFIG_FILENAME,
        {"mcpServers": {"other": {"type": "http", "url": "https://other.test/mcp"}}},
    )

    first_read = asyncio.run(synchronizer.read_user_mcp_servers("7"))
    first_read["comfy"]["url"] = "mutated"  # type: ignore[index]
    repeated = asyncio.run(synchronizer.read_user_mcp_servers("7"))
    other = asyncio.run(synchronizer.read_user_mcp_servers("8"))
    assert repeated["comfy"]["url"] == "https://example.test/mcp"  # type: ignore[index]
    assert set(other) == {"other"}


def test_identity_uses_shared_absolute_cli_and_user_config(
    tmp_path: Path,
    monkeypatch,
) -> None:
    settings = _settings(tmp_path)
    synchronizer = _synchronizer(tmp_path)
    monkeypatch.setattr(identity_module, "resolve_claude_cli_path", lambda: "/bin/sh")
    provider = FileBackedClaudeMcpIdentityProvider(
        settings,
        synchronizer=synchronizer,
    )
    first = provider.resolve("7")
    other = provider.resolve("8")
    assert first.command == ("/bin/sh",)
    assert first.config_dir == resolve_user_paths("7", settings).config_dir
    assert first.cwd == resolve_user_paths("7", settings).workspace
    assert first.fingerprint != other.fingerprint


def test_macos_identity_requires_cli_secure_storage_marker(tmp_path: Path, monkeypatch) -> None:
    settings = _settings(tmp_path)
    workspace_root = (tmp_path / "workspaces").resolve()
    workspace_root.mkdir()
    synchronizer = ClaudeMcpCredentialSynchronizer(
        settings,
        platform_name="darwin",
        workspace_root_provider=lambda: workspace_root,
    )
    monkeypatch.setattr(identity_module, "resolve_claude_cli_path", lambda: "/bin/sh")

    provider = FileBackedClaudeMcpIdentityProvider(
        settings,
        synchronizer=synchronizer,
        secure_storage_marker_checker=lambda executable: executable == "/bin/sh",
    )
    identity = provider.resolve("7")
    assert identity.config_dir == synchronizer.secure_storage_home("7")
    assert synchronizer.secure_storage_home("7") != synchronizer.secure_storage_home("8")

    unavailable = FileBackedClaudeMcpIdentityProvider(
        settings,
        synchronizer=synchronizer,
        secure_storage_marker_checker=lambda _executable: False,
    )
    try:
        unavailable.resolve("7")
    except ClaudeMcpError as exc:
        assert exc.code is ClaudeMcpErrorCode.IDENTITY_UNAVAILABLE
    else:  # pragma: no cover
        raise AssertionError("Darwin CLI without secure-storage support was accepted")


def test_identity_subprocess_env_drops_backend_secrets() -> None:
    environment = _safe_runtime_env(
        {
            "PATH": "/usr/bin",
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "HTTPS_PROXY": "http://proxy.example.test",
            "DATABASE_URL": "postgresql://must-not-propagate",
            "JWT_SECRET_KEY": "must-not-propagate",
            "ANTHROPIC_AUTH_TOKEN": "must-not-propagate",
            "INK_ADMIN_INTERNAL_TOKEN": "must-not-propagate",
        }
    )

    assert environment == {
        "PATH": "/usr/bin",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "HTTPS_PROXY": "http://proxy.example.test",
    }


def test_sync_delivers_remote_config_and_projects_only_linux_oauth(tmp_path: Path) -> None:
    async def scenario() -> None:
        settings = _settings(tmp_path)
        source = resolve_user_paths("7", settings).config_dir
        _write_private_json(
            source / CLAUDE_USER_CONFIG_FILENAME,
            {
                "mcpServers": {
                    "plugin:comfy-cloud:comfy-cloud": {
                        "type": "http",
                        "url": "https://mcp.example.test",
                    }
                },
                "numStartups": 99,
            },
        )
        _write_private_json(
            source / CLAUDE_CREDENTIALS_FILENAME,
            {
                "mcpOAuth": {
                    "plugin:comfy-cloud:comfy-cloud": {
                        "accessToken": "test-secret-token",
                    }
                },
                "claudeAiOauth": {"accessToken": "must-not-copy"},
            },
        )

        workspace = tmp_path / "workspaces" / "thread-1"
        target = workspace / ".claude-home"
        target.mkdir(parents=True)
        _write_private_json(
            target / CLAUDE_USER_CONFIG_FILENAME,
            {"projects": {"thread": {"session": "kept"}}},
        )
        _write_private_json(
            target / CLAUDE_CREDENTIALS_FILENAME,
            {"threadOwned": "kept"},
        )

        result = await _synchronizer(tmp_path).sync_thread("7", target)
        assert not result.config_changed
        assert result.credentials_changed
        assert result.credentials_present
        assert "test-secret-token" not in repr(result)

        projected_config = json.loads(
            (target / CLAUDE_USER_CONFIG_FILENAME).read_text(encoding="utf-8")
        )
        projected_credentials = json.loads(
            (target / CLAUDE_CREDENTIALS_FILENAME).read_text(encoding="utf-8")
        )
        assert projected_config["projects"]["thread"]["session"] == "kept"
        assert "numStartups" not in projected_config
        assert "mcpServers" not in projected_config
        assert list(result.mcp_servers) == ["plugin:comfy-cloud:comfy-cloud"]
        assert projected_credentials["threadOwned"] == "kept"
        assert "mcpOAuth" in projected_credentials
        assert "claudeAiOauth" not in projected_credentials
        assert (target / CLAUDE_USER_CONFIG_FILENAME).stat().st_mode & 0o777 == 0o600
        assert (target / CLAUDE_CREDENTIALS_FILENAME).stat().st_mode & 0o777 == 0o600

    asyncio.run(scenario())


def test_sync_is_noop_then_revokes_mcp_oauth_after_logout(tmp_path: Path) -> None:
    async def scenario() -> None:
        settings = _settings(tmp_path)
        source = resolve_user_paths("7", settings).config_dir
        source_credentials = source / CLAUDE_CREDENTIALS_FILENAME
        _write_private_json(
            source_credentials,
            {"mcpOAuth": {"server": {"accessToken": "secret"}}},
        )
        target = tmp_path / "workspaces" / "thread-1" / ".claude-home"
        target.mkdir(parents=True)
        synchronizer = _synchronizer(tmp_path)

        first = await synchronizer.sync_thread("7", target)
        first_mtime = (target / CLAUDE_CREDENTIALS_FILENAME).stat().st_mtime_ns
        second = await synchronizer.sync_thread("7", target)
        assert first.credentials_changed
        assert not second.credentials_changed
        assert (target / CLAUDE_CREDENTIALS_FILENAME).stat().st_mtime_ns == first_mtime

        _write_private_json(source_credentials, {"claudeAiOauth": {"kept": True}})
        revoked = await synchronizer.sync_thread("7", target)
        assert revoked.credentials_changed
        assert not revoked.credentials_present
        assert not (target / CLAUDE_CREDENTIALS_FILENAME).exists()

    asyncio.run(scenario())


def test_user_mcp_state_detection_uses_minimal_managed_keys(tmp_path: Path) -> None:
    async def scenario() -> None:
        settings = _settings(tmp_path)
        source = resolve_user_paths("7", settings).config_dir
        synchronizer = _synchronizer(tmp_path)

        assert not await synchronizer.has_user_mcp_state("7")
        _write_private_json(
            source / CLAUDE_CREDENTIALS_FILENAME,
            {"claudeAiOauth": {"accessToken": "must-not-count"}},
        )
        assert not await synchronizer.has_user_mcp_state("7")
        _write_private_json(
            source / CLAUDE_USER_CONFIG_FILENAME,
            {"mcpServers": {"server": {"type": "http"}}},
        )
        assert await synchronizer.has_user_mcp_state("7")

    asyncio.run(scenario())


def test_existing_thread_sync_skips_missing_workspaces_and_is_user_scoped(tmp_path: Path) -> None:
    async def scenario() -> None:
        settings = _settings(tmp_path)
        source = resolve_user_paths("7", settings).config_dir
        _write_private_json(
            source / CLAUDE_CREDENTIALS_FILENAME,
            {"mcpOAuth": {"server": {"refreshToken": "secret"}}},
        )
        workspace = tmp_path / "workspaces" / "thread-present"
        workspace.mkdir(parents=True)
        synchronizer = _synchronizer(
            tmp_path,
            thread_rows=[{"id": "thread-present"}, {"id": "thread-missing"}],
        )
        summary = await synchronizer.sync_existing_threads("7")
        assert summary.thread_count == 1
        assert summary.changed_count == 1
        assert (
            workspace / ".claude-home" / CLAUDE_CREDENTIALS_FILENAME
        ).is_file()
        assert not (tmp_path / "workspaces" / "thread-missing").exists()

    asyncio.run(scenario())


def test_malformed_permissions_symlinks_and_unsupported_platform_fail_closed(tmp_path: Path) -> None:
    async def scenario() -> None:
        settings = _settings(tmp_path)
        source = resolve_user_paths("7", settings).config_dir
        malformed = source / CLAUDE_CREDENTIALS_FILENAME
        malformed.write_text("not-json", encoding="utf-8")
        malformed.chmod(0o600)
        target = tmp_path / "workspaces" / "thread-1" / ".claude-home"
        target.mkdir(parents=True)
        synchronizer = _synchronizer(tmp_path)
        try:
            await synchronizer.sync_thread("7", target)
        except ClaudeMcpCredentialError:
            pass
        else:  # pragma: no cover
            raise AssertionError("malformed credential JSON was accepted")

        _write_private_json(malformed, {"mcpOAuth": {}})
        malformed.chmod(0o644)
        try:
            await synchronizer.sync_thread("7", target)
        except ClaudeMcpCredentialError:
            pass
        else:  # pragma: no cover
            raise AssertionError("world-readable credential JSON was accepted")

        malformed.chmod(0o600)
        linked_target = tmp_path / "workspaces" / "thread-link" / ".claude-home"
        linked_target.parent.mkdir()
        linked_target.symlink_to(target, target_is_directory=True)
        try:
            await synchronizer.sync_thread("7", linked_target)
        except ClaudeMcpCredentialError:
            pass
        else:  # pragma: no cover
            raise AssertionError("symlinked thread config home was accepted")

        unsupported = ClaudeMcpCredentialSynchronizer(
            settings,
            platform_name="win32",
            workspace_root_provider=lambda: tmp_path / "workspaces",
        )
        try:
            await unsupported.sync_thread("7", target)
        except ClaudeMcpCredentialStoreUnsupported:
            pass
        else:  # pragma: no cover
            raise AssertionError("unsupported platform was treated as a credential store")

    asyncio.run(scenario())


def test_macos_projects_only_config_and_reuses_user_secure_storage_home(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        settings = _settings(tmp_path)
        source = resolve_user_paths("7", settings).config_dir
        other_source = resolve_user_paths("8", settings).config_dir
        _write_private_json(
            source / CLAUDE_USER_CONFIG_FILENAME,
            {
                "mcpServers": {
                    "server": {"type": "http", "url": "https://mcp.example.test"}
                },
                "unmanaged": "must-not-copy",
            },
        )
        _write_private_json(
            other_source / CLAUDE_USER_CONFIG_FILENAME,
            {"mcpServers": {"other": {"type": "http"}}},
        )
        workspace_root = (tmp_path / "workspaces").resolve()
        target = workspace_root / "thread-1" / ".claude-home"
        target.mkdir(parents=True)
        _write_private_json(
            target / CLAUDE_CREDENTIALS_FILENAME,
            {
                "threadOwned": "kept",
                "mcpOAuth": {"stale": {"accessToken": "must-be-removed"}},
            },
        )
        synchronizer = ClaudeMcpCredentialSynchronizer(
            settings,
            platform_name="darwin",
            workspace_root_provider=lambda: workspace_root,
        )

        result = await synchronizer.sync_thread("7", target)
        assert not result.credentials_present and result.credentials_changed
        assert list(result.mcp_servers) == ["server"]
        assert not (target / CLAUDE_USER_CONFIG_FILENAME).exists()
        projected = _read_private_fixture(target / CLAUDE_CREDENTIALS_FILENAME)
        assert projected == {"threadOwned": "kept"}
        assert (target / CLAUDE_CREDENTIALS_FILENAME).stat().st_mode & 0o077 == 0
        assert synchronizer.secure_storage_home("7") == source
        assert synchronizer.secure_storage_home("8") == other_source

    asyncio.run(scenario())


def test_logout_revokes_only_existing_macos_file_projections(tmp_path: Path) -> None:
    async def scenario() -> None:
        settings = _settings(tmp_path)
        workspace_root = (tmp_path / "workspaces").resolve()
        projected = workspace_root / "projected" / ".claude-home"
        untouched = workspace_root / "untouched" / ".claude-home"
        projected.mkdir(parents=True)
        untouched.mkdir(parents=True)
        _write_private_json(
            projected / CLAUDE_CREDENTIALS_FILENAME,
            {"threadOwned": "kept", "mcpOAuth": {"server": {"token": "old"}}},
        )
        synchronizer = ClaudeMcpCredentialSynchronizer(
            settings,
            platform_name="darwin",
            thread_ids_provider=lambda _user_id: [
                {"id": "projected"},
                {"id": "untouched"},
            ],
            workspace_root_provider=lambda: workspace_root,
        )

        summary = await synchronizer.revoke_existing_thread_credentials("7")
        assert summary.thread_count == 2
        assert summary.changed_count == 1
        assert _read_private_fixture(
            projected / CLAUDE_CREDENTIALS_FILENAME
        ) == {"threadOwned": "kept"}
        assert not (untouched / CLAUDE_CREDENTIALS_FILENAME).exists()

    asyncio.run(scenario())
