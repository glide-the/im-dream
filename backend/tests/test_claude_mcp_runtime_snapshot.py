"""Managed MCP Runtime snapshot loader contracts.

[Input] Enabled user/workspace rows, encrypted fake credentials, and injected stdio profiles.
[Output] Workspace override, local secret resolution, redacted repr, and zero-file-write evidence.
[Pos] Provider-free Chat integration seam tests; does not import or modify Chat/Runner code.
[Sync] 2026-08-25: define the injectable managed MCP runtime snapshot contract.
[Sync] 2026-08-25: cover bounded standard-MCP refresh before expired OAuth projection.
[Sync] 2026-09-06: require a monotonic refresh revision and coherent authoritative single-Server record.
[Sync] 2026-09-06: bind Apps only through current descriptor metadata plus a listed ui:// resource.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from claude_mcp.contracts import ClaudeMcpError, McpAuthKind, McpTransport
from claude_mcp.crypto import (
    McpCredentialCipher,
    McpCredentialConfigurationError,
    McpCredentialContext,
)
from claude_mcp.inventory import StdioProfile, StdioProfileResolver
from claude_mcp.repository import McpCredentialRecord, McpServerRecord
from claude_mcp.runtime_snapshot import ManagedMcpRuntimeSnapshotLoader


def _server(server_id, key, *, scope="user", workspace_id=None, transport=McpTransport.STREAMABLE_HTTP):
    return McpServerRecord(
        id=server_id, user_id="7", workspace_id=workspace_id, scope=scope,
        server_key=key, display_name=key, transport=transport,
        remote_url=None if transport is McpTransport.STDIO else f"https://{server_id}.example.test/mcp",
        stdio_profile_key="profile" if transport is McpTransport.STDIO else None,
        auth_kind=McpAuthKind.OAUTH if key == "shared" else McpAuthKind.NONE,
        enabled=True, config_revision=1, credential_revision=1,
        credential_id="credential-1" if key == "shared" else None,
        credential_configured=key == "shared",
        created_at="2026-08-25T00:00:00+00:00", updated_at="2026-08-25T00:00:00+00:00",
    )


class _Repository:
    def __init__(self, rows, credential=None, capability=True, snapshots=None):
        self.rows = rows; self.credential = credential; self.capability = capability
        self.snapshots = snapshots or {}
    async def capability_available(self): return self.capability
    async def list_servers(self, actor_id, workspace_id=None):
        assert actor_id == "7"
        return [row for row in self.rows if row.scope == "user" or row.workspace_id == workspace_id]
    async def get_credential(self, actor_id, server_id):
        assert actor_id == "7"
        return self.credential if self.credential and self.credential.server_id == server_id else None
    async def get_discovery_snapshot(self, actor_id, server):
        assert actor_id == "7"
        return self.snapshots.get(server.id)


def _credential(cipher, server_id, token, *, expires_at=None, revision=1):
    payload = json.dumps({"tokens": {"access_token": token, "token_type": "Bearer"}}).encode()
    envelope = cipher.encrypt(payload, McpCredentialContext("7", server_id, "oauth", 1))
    return McpCredentialRecord(
        id="credential-1", server_id=server_id, user_id="7", kind="oauth",
        ciphertext=envelope.ciphertext, iv=envelope.iv, tag=envelope.tag,
        fingerprint=envelope.fingerprint, key_version=1, credential_revision=revision,
        expires_at=expires_at,
    )


def test_workspace_override_and_secret_projection_are_memory_only_and_repr_safe(tmp_path):
    async def scenario():
        cipher = McpCredentialCipher(key=b"k" * 32, key_version=1)
        user = _server("user-shared", "shared")
        workspace = _server("workspace-shared", "shared", scope="workspace", workspace_id="workspace-1")
        stdio = _server("stdio", "local", transport=McpTransport.STDIO)
        secret = "must-not-leak"
        loader = ManagedMcpRuntimeSnapshotLoader(
            _Repository([user, workspace, stdio], _credential(cipher, "workspace-shared", secret)),
            cipher,
            stdio_profiles=StdioProfileResolver({
                "profile": StdioProfile("/usr/bin/true", ("--safe",), {"SAFE": "1"}, None)
            }),
            max_servers=8,
        )
        before = list(tmp_path.iterdir())
        snapshot = await loader.load("7", "workspace-1")
        assert snapshot["shared"]["url"].startswith("https://workspace-shared")
        assert snapshot["shared"]["headers"]["Authorization"] == f"Bearer {secret}"
        assert snapshot["local"] == {
            "type": "stdio", "command": "/usr/bin/true", "args": ["--safe"], "env": {"SAFE": "1"}
        }
        assert secret not in repr(snapshot) and secret not in repr(snapshot["shared"])
        assert list(tmp_path.iterdir()) == before

    asyncio.run(scenario())


def test_descriptor_app_bindings_follow_effective_scope_and_require_resource():
    async def scenario():
        user = _server("user-apps", "apps")
        workspace = _server(
            "workspace-apps",
            "apps",
            scope="workspace",
            workspace_id="workspace-1",
        )
        snapshots = {
            user.id: {
                "status": "complete",
                "inventory": {
                    "tools": [{
                        "name": "get-time",
                        "_meta": {
                            "ui": {"resourceUri": "ui://get-time/mcp-app.html"}
                        },
                    }],
                    "resources": [{"uri": "ui://get-time/mcp-app.html"}],
                },
            },
            workspace.id: {
                "status": "complete",
                "inventory": {
                    "tools": [{
                        "name": "get-time",
                        "_meta": {
                            "ui": {"resourceUri": "ui://missing/app.html"}
                        },
                    }],
                    "resources": [],
                },
            },
        }
        loader = ManagedMcpRuntimeSnapshotLoader(
            _Repository([user, workspace], snapshots=snapshots),
            McpCredentialCipher(key=b"k" * 32, key_version=1),
            stdio_profiles=StdioProfileResolver({}),
            max_servers=8,
        )

        user_snapshot = await loader.load("7", None)
        assert user_snapshot.mcp_app_resource_bindings == {
            "apps": {"get-time": "ui://get-time/mcp-app.html"}
        }
        workspace_snapshot = await loader.load("7", "workspace-1")
        assert workspace_snapshot.mcp_app_resource_bindings == {}
        assert await loader.load_mcp_app_resource_bindings("7", None) == {
            "apps": {"get-time": "ui://get-time/mcp-app.html"}
        }

    asyncio.run(scenario())


def test_disabled_and_other_workspace_rows_are_excluded():
    async def scenario():
        cipher = McpCredentialCipher(key=b"k" * 32, key_version=1)
        disabled = replace(_server("disabled", "disabled"), enabled=False)
        foreign_workspace = _server("foreign", "foreign", scope="workspace", workspace_id="workspace-2")
        loader = ManagedMcpRuntimeSnapshotLoader(
            _Repository([disabled, foreign_workspace]), cipher,
            stdio_profiles=StdioProfileResolver({}), max_servers=8,
        )
        assert await loader.load("7", "workspace-1") == {}

    asyncio.run(scenario())


def test_missing_exact_capability_fails_closed():
    async def scenario():
        loader = ManagedMcpRuntimeSnapshotLoader(
            _Repository([], capability=False),
            McpCredentialCipher(key=b"k" * 32, key_version=1),
            stdio_profiles=StdioProfileResolver({}), max_servers=8,
        )
        with pytest.raises(ClaudeMcpError):
            await loader.load("7", None)

    asyncio.run(scenario())


def test_missing_key_allows_anonymous_snapshot_but_fails_at_credential_boundary():
    async def scenario():
        anonymous = _server("anonymous", "anonymous")
        loader = ManagedMcpRuntimeSnapshotLoader(
            _Repository([anonymous]), None,
            stdio_profiles=StdioProfileResolver({}), max_servers=8,
        )
        assert (await loader.load("7", None))["anonymous"]["type"] == "http"

        cipher = McpCredentialCipher(key=b"k" * 32, key_version=1)
        credentialed = _server("credentialed", "shared")
        unavailable = ManagedMcpRuntimeSnapshotLoader(
            _Repository([credentialed], _credential(cipher, "credentialed", "private")),
            None,
            stdio_profiles=StdioProfileResolver({}), max_servers=8,
        )
        with pytest.raises(McpCredentialConfigurationError) as raised:
            await unavailable.load("7", None)
        assert "private" not in str(raised.value)

    asyncio.run(scenario())


def test_expired_oauth_is_refreshed_and_reloaded_before_runtime_projection():
    async def scenario():
        cipher = McpCredentialCipher(key=b"k" * 32, key_version=1)
        server = _server("oauth-server", "shared")
        expired = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        repository = _Repository(
            [server], _credential(cipher, server.id, "stale-secret", expires_at=expired)
        )

        class _Refresher:
            def __init__(self):
                self.calls = []

            async def discover_one(self, actor_id, server_id, **kwargs):
                self.calls.append((actor_id, server_id, kwargs))
                repository.credential = _credential(
                    cipher,
                    server.id,
                    "fresh-secret",
                    expires_at=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
                    revision=2,
                )
                return SimpleNamespace(error=None)

        refresher = _Refresher()
        loader = ManagedMcpRuntimeSnapshotLoader(
            repository,
            cipher,
            stdio_profiles=StdioProfileResolver({}),
            max_servers=8,
            oauth_refresher=refresher,
        )
        snapshot = await loader.load("7", None)
        assert snapshot["shared"]["headers"]["Authorization"] == "Bearer fresh-secret"
        assert refresher.calls == [
            ("7", server.id, {"workspace_id": None, "force": True})
        ]
        assert "stale-secret" not in repr(snapshot)

    asyncio.run(scenario())


def test_expired_oauth_refresh_failure_is_safe_and_never_projects_stale_token():
    async def scenario():
        cipher = McpCredentialCipher(key=b"k" * 32, key_version=1)
        server = _server("oauth-server", "shared")
        repository = _Repository(
            [server],
            _credential(
                cipher,
                server.id,
                "stale-secret",
                expires_at=(datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(),
            ),
        )

        class _Refresher:
            async def discover_one(self, *_args, **_kwargs):
                return SimpleNamespace(error=SimpleNamespace(code="safe"))

        loader = ManagedMcpRuntimeSnapshotLoader(
            repository,
            cipher,
            stdio_profiles=StdioProfileResolver({}),
            max_servers=8,
            oauth_refresher=_Refresher(),
        )
        with pytest.raises(ClaudeMcpError) as raised:
            await loader.load("7", None)
        assert raised.value.code.value == "CLAUDE_MCP_CREDENTIAL_REQUIRED"
        assert "stale-secret" not in str(raised.value)

    asyncio.run(scenario())


def test_single_server_expired_oauth_fails_when_record_revision_does_not_advance():
    async def scenario():
        cipher = McpCredentialCipher(key=b"k" * 32, key_version=1)
        server = _server("oauth-server", "shared")
        repository = _Repository(
            [server],
            _credential(
                cipher,
                server.id,
                "stale-secret",
                expires_at=(datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(),
            ),
        )

        async def get_server(actor_id, identifier, workspace_id=None):
            assert actor_id == server.user_id
            assert identifier == server.id
            assert workspace_id == server.workspace_id
            return server

        repository.get_server = get_server

        class _Refresher:
            async def discover_one(self, *_args, **_kwargs):
                repository.credential = _credential(
                    cipher,
                    server.id,
                    "fresh-secret",
                    expires_at=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
                    revision=2,
                )
                return SimpleNamespace(error=None)

        loader = ManagedMcpRuntimeSnapshotLoader(
            repository,
            cipher,
            stdio_profiles=StdioProfileResolver({}),
            max_servers=8,
            oauth_refresher=_Refresher(),
        )
        with pytest.raises(ClaudeMcpError) as raised:
            await loader.load_server_config(
                server.user_id,
                server,
                expected_config_revision=1,
                expected_credential_revision=1,
            )
        assert raised.value.code.value == "CLAUDE_MCP_APP_RUNTIME_REVISION_CONFLICT"
        assert "stale-secret" not in str(raised.value)
        assert "fresh-secret" not in str(raised.value)

    asyncio.run(scenario())
