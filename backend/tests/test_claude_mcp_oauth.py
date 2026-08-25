"""Provider-free SDK OAuth storage contracts.

[Input] Synthetic OAuthToken/client metadata, fake encrypted repository, and deterministic test key.
[Output] Standard mcp TokenStorage round-trip with ciphertext-only persistence and safe repr.
[Pos] OAuth persistence seam test; does not contact providers, browsers, MCP servers, or PostgreSQL.
[Sync] 2026-08-25: verify SDK-owned token models persist through the managed encrypted envelope.
[Sync] 2026-08-25: prove persisted absolute expiry seeds the SDK provider's restart refresh decision.
[Sync] 2026-08-25: bind the public OAuth operation to the stable Server key rather than its database UUID.
[Sync] 2026-08-25: a cancelled first login leaves client registration process-local until tokens exist.
[Sync] 2026-08-25: require OAuth operations to use their own long timeout instead of inventory timeout.
[Sync] 2026-08-25: preserve SDK-discovered authorization metadata inside the encrypted token document for restart-safe refresh routing.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from mcp.shared.auth import OAuthToken
from mcp.shared.auth import OAuthClientMetadata
from mcp.shared.auth import OAuthClientInformationFull
from mcp.shared.auth import OAuthMetadata

from claude_mcp.crypto import McpCredentialCipher
from claude_mcp.oauth import (
    EncryptedMcpTokenStorage,
    ManagedMcpAuthResolver,
    ManagedMcpOAuthCoordinator,
)
from claude_mcp.repository import McpCredentialRecord, McpServerRecord
from claude_mcp.contracts import McpAuthKind, McpTransport


class _Repository:
    def __init__(self):
        self.record = None
        self.persisted = []

    async def get_credential(self, actor_id, server_id):
        if self.record and self.record.user_id == actor_id and self.record.server_id == server_id:
            return self.record
        return None

    async def upsert_credential(self, actor_id, server_id, *, kind, envelope, expires_at=None):
        revision = 1 if self.record is None else self.record.credential_revision + 1
        self.record = McpCredentialRecord(
            id="credential-1", server_id=server_id, user_id=actor_id, kind=kind,
            ciphertext=envelope.ciphertext, iv=envelope.iv, tag=envelope.tag,
            fingerprint=envelope.fingerprint, key_version=envelope.key_version,
            credential_revision=revision,
            expires_at=expires_at.isoformat() if expires_at else None,
        )
        self.persisted.append(self.record)
        return self.record


def test_standard_token_storage_round_trip_never_persists_plaintext() -> None:
    async def scenario():
        repository = _Repository()
        storage = EncryptedMcpTokenStorage(
            repository,
            McpCredentialCipher(key=b"k" * 32, key_version=1),
            actor_id="7",
            server_id="server-1",
        )
        secret = "oauth-access-must-not-leak"
        await storage.set_tokens(
            OAuthToken(access_token=secret, token_type="Bearer", expires_in=3600)
        )
        restored = await storage.get_tokens()
        assert restored and restored.access_token == secret
        assert secret not in repr(repository.persisted)
        assert repository.record.kind == "oauth"

    asyncio.run(scenario())


def test_sdk_discovered_oauth_metadata_is_encrypted_and_restored() -> None:
    async def scenario():
        repository = _Repository()
        storage = EncryptedMcpTokenStorage(
            repository,
            McpCredentialCipher(key=b"k" * 32, key_version=1),
            actor_id="7",
            server_id="server-1",
        )
        metadata = OAuthMetadata(
            issuer="https://auth.example.test",
            authorization_endpoint="https://auth.example.test/oauth/authorize",
            token_endpoint="https://auth.example.test/oauth/token",
            response_types_supported=["code"],
        )
        storage.bind_oauth_context(SimpleNamespace(oauth_metadata=metadata))
        await storage.set_tokens(
            OAuthToken(access_token="access-secret", token_type="Bearer")
        )
        restored_context = SimpleNamespace(oauth_metadata=None)
        await storage.restore_oauth_metadata(restored_context)
        assert restored_context.oauth_metadata == metadata
        assert "https://auth.example.test/oauth/token" not in repr(repository.persisted)

    asyncio.run(scenario())


def test_client_registration_is_staged_until_tokens_exist() -> None:
    async def scenario():
        repository = _Repository()
        storage = EncryptedMcpTokenStorage(
            repository,
            McpCredentialCipher(key=b"k" * 32, key_version=1),
            actor_id="7",
            server_id="server-1",
        )
        client_info = OAuthClientInformationFull(
            client_id="registered-client",
            client_secret="registered-secret",
            redirect_uris=["https://dream.example.test/oauth/callback"],
            client_name="Dream test",
        )
        await storage.set_client_info(client_info)
        assert repository.record is None
        assert await storage.get_client_info() == client_info

        await storage.set_tokens(
            OAuthToken(access_token="access-secret", token_type="Bearer")
        )
        assert repository.record is not None
        assert await storage.get_client_info() == client_info
        assert (await storage.get_tokens()).access_token == "access-secret"

    asyncio.run(scenario())


def test_auth_resolver_restores_absolute_expiry_for_standard_sdk_refresh() -> None:
    async def scenario():
        repository = _Repository()
        cipher = McpCredentialCipher(key=b"k" * 32, key_version=1)
        storage = EncryptedMcpTokenStorage(
            repository, cipher, actor_id="7", server_id="server-1"
        )
        metadata = OAuthMetadata(
            issuer="https://oauth.example.test",
            authorization_endpoint="https://oauth.example.test/oauth/authorize",
            token_endpoint="https://oauth.example.test/oauth/token",
            response_types_supported=["code"],
        )
        storage.bind_oauth_context(SimpleNamespace(oauth_metadata=metadata))
        await storage.set_tokens(
            OAuthToken(
                access_token="expired-access",
                refresh_token="refresh-secret",
                token_type="Bearer",
                expires_in=1,
            )
        )
        expired = datetime.now(timezone.utc) - timedelta(seconds=1)
        repository.record = McpCredentialRecord(
            **{
                **repository.record.__dict__,
                "expires_at": expired.isoformat(),
            }
        )
        server = McpServerRecord(
            id="server-1", user_id="7", workspace_id=None, scope="user",
            server_key="oauth", display_name="OAuth", transport=McpTransport.STREAMABLE_HTTP,
            remote_url="https://oauth.example.test/mcp", stdio_profile_key=None,
            auth_kind=McpAuthKind.OAUTH, enabled=True, config_revision=1,
            credential_revision=1, credential_id="credential-1", credential_configured=True,
            created_at=expired.isoformat(), updated_at=expired.isoformat(),
        )
        provider = await ManagedMcpAuthResolver(
            repository,
            cipher,
            client_metadata=OAuthClientMetadata(
                redirect_uris=["https://dream.example.test/oauth/callback"],
                client_name="Dream test",
            ),
            timeout_seconds=10,
        ).resolve("7", server)
        assert provider.context.token_expiry_time == pytest.approx(expired.timestamp())
        assert provider.context.oauth_metadata == metadata

    import pytest

    asyncio.run(scenario())


def test_oauth_operation_projects_server_key_and_keeps_uuid_internal() -> None:
    class _WaitingDiscovery:
        async def discover_one(
            self,
            actor_id,
            server_id,
            *,
            workspace_id,
            force,
            auth,
            operation_timeout_seconds,
        ):
            assert actor_id == "7"
            assert server_id == "5c9d644f-16c6-4f80-87c8-629bb7c5f91f"
            assert workspace_id is None
            assert force is True
            assert operation_timeout_seconds == 10
            await auth.context.redirect_handler("https://auth.example.test/authorize")
            await auth.context.callback_handler()

    async def scenario():
        now = datetime.now(timezone.utc).isoformat()
        server = McpServerRecord(
            id="5c9d644f-16c6-4f80-87c8-629bb7c5f91f",
            user_id="7",
            workspace_id=None,
            scope="user",
            server_key="comfy-cloud",
            display_name="Comfy Cloud",
            transport=McpTransport.STREAMABLE_HTTP,
            remote_url="https://oauth.example.test/mcp",
            stdio_profile_key=None,
            auth_kind=McpAuthKind.OAUTH,
            enabled=True,
            config_revision=1,
            credential_revision=0,
            credential_id=None,
            credential_configured=False,
            created_at=now,
            updated_at=now,
        )
        coordinator = ManagedMcpOAuthCoordinator(
            _Repository(),
            McpCredentialCipher(key=b"k" * 32, key_version=1),
            _WaitingDiscovery(),
            client_metadata=OAuthClientMetadata(
                redirect_uris=["https://dream.example.test/oauth/callback"],
                client_name="Dream test",
            ),
            auth_timeout_seconds=10,
            readiness_timeout_seconds=1,
            max_redirect_url_length=8192,
        )
        operation = await coordinator.start("7", server)
        assert operation.server_name == "comfy-cloud"
        assert operation.authorization_url == "https://auth.example.test/authorize"
        assert coordinator._active == {("7", server.id): operation.id}
        await coordinator.cancel("7", operation.id)

    asyncio.run(scenario())
