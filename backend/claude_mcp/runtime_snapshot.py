"""In-memory Runtime projection of managed MCP configuration.

[Input] Enabled actor user/workspace Server rows, stdio policy profiles, and encrypted credential references.
[Output] Detached public Agent-SDK `mcp_servers` mapping with workspace override and redacted repr.
[Pos] Injectable Chat integration seam; performs no file write, logging, Agent import, CLI, or MCP network call.
[Sync] 2026-08-25: add actor/workspace managed snapshot loader for later Chat service injection.
[Sync] 2026-08-25: refresh expired OAuth through bounded standard-MCP discovery before projecting a Runtime bearer header.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
from typing import Any

from .contracts import ClaudeMcpError, ClaudeMcpErrorCode, McpTransport
from .crypto import (
    McpCredentialCipher,
    McpCredentialConfigurationError,
    McpCredentialContext,
    McpCredentialIntegrityError,
    McpEncryptedCredential,
)
from .inventory import StdioProfileResolver


class SecretMcpConfigDict(dict[str, Any]):
    def __repr__(self) -> str:
        return "SecretMcpConfigDict(<redacted>)"


class ManagedMcpRuntimeSnapshot(dict[str, SecretMcpConfigDict]):
    def __repr__(self) -> str:
        return f"ManagedMcpRuntimeSnapshot(server_count={len(self)}, values=<redacted>)"


def _string_mapping(value: Any) -> dict[str, str]:
    if not isinstance(value, dict) or not all(
        isinstance(key, str)
        and key
        and isinstance(item, str)
        and "\x00" not in key
        and "\x00" not in item
        for key, item in value.items()
    ):
        raise McpCredentialIntegrityError()
    return dict(value)


class ManagedMcpRuntimeSnapshotLoader:
    """Load one detached, actor-owned snapshot for a new or resumed turn."""

    def __init__(
        self,
        repository: Any,
        cipher: McpCredentialCipher | None,
        *,
        stdio_profiles: StdioProfileResolver,
        max_servers: int,
        oauth_refresher: Any | None = None,
    ) -> None:
        if max_servers < 1:
            raise ValueError("max_servers must be positive")
        self.repository = repository
        self.cipher = cipher
        self.stdio_profiles = stdio_profiles
        self.max_servers = max_servers
        self.oauth_refresher = oauth_refresher

    async def load(
        self,
        actor_id: str,
        workspace_id: str | None,
    ) -> dict[str, dict[str, Any]]:
        if not await self.repository.capability_available():
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.SCHEMA_CAPABILITY_MISSING,
                "Managed Claude MCP schema capability is unavailable.",
            )
        rows = await self.repository.list_servers(actor_id, workspace_id)
        enabled = [row for row in rows if row.enabled]
        if len(enabled) > self.max_servers:
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.SERVER_CONFIGURATION_INVALID,
                "Managed Claude MCP server count exceeds policy.",
            )

        # User scope is projected first; the current actor-owned workspace row
        # with the same stable server_key intentionally replaces it.
        ordered = sorted(enabled, key=lambda row: 0 if row.scope == "user" else 1)
        # Credential reads are local DB operations.  Expired OAuth rows may
        # trigger discovery, whose coordinator owns the bounded semaphore and
        # per-Server timeout.  A single refresh failure aborts this Chat turn
        # safely instead of injecting a known-stale bearer token.
        configs = await asyncio.gather(
            *(self._server_config(actor_id, server) for server in ordered)
        )
        snapshot = ManagedMcpRuntimeSnapshot()
        for server, config in zip(ordered, configs):
            snapshot[server.server_key] = config
        return snapshot

    async def _server_config(self, actor_id: str, server: Any) -> SecretMcpConfigDict:
        if server.transport is McpTransport.STREAMABLE_HTTP:
            config = SecretMcpConfigDict(type="http", url=server.remote_url)
        elif server.transport is McpTransport.SSE:
            config = SecretMcpConfigDict(type="sse", url=server.remote_url)
        elif server.transport is McpTransport.STDIO:
            if not server.stdio_profile_key:
                raise ClaudeMcpError(
                    ClaudeMcpErrorCode.STDIO_PROFILE_DENIED,
                    "Managed Claude MCP stdio profile is unavailable.",
                )
            try:
                profile = self.stdio_profiles.resolve(server.stdio_profile_key)
            except ValueError:
                raise ClaudeMcpError(
                    ClaudeMcpErrorCode.STDIO_PROFILE_DENIED,
                    "Managed Claude MCP stdio profile is unavailable.",
                ) from None
            config = SecretMcpConfigDict(
                type="stdio",
                command=profile.command,
                args=list(profile.args),
                env=dict(profile.env),
            )
            if profile.cwd is not None:
                config["cwd"] = profile.cwd
        else:  # pragma: no cover - enum guards normal rows
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.TRANSPORT_UNSUPPORTED,
                "Managed Claude MCP transport is unsupported.",
            )

        credential = await self.repository.get_credential(actor_id, server.id)
        if credential is None:
            return config
        if credential.kind == "oauth" and server.auth_kind.value != "oauth":
            raise McpCredentialIntegrityError()
        if credential.kind == "oauth" and self._is_expired(credential.expires_at):
            if self.oauth_refresher is None:
                raise ClaudeMcpError(
                    ClaudeMcpErrorCode.CREDENTIAL_REQUIRED,
                    "Managed Claude MCP authentication must be refreshed.",
                )
            result = await self.oauth_refresher.discover_one(
                actor_id,
                server.id,
                workspace_id=server.workspace_id,
                force=True,
            )
            if getattr(result, "error", None) is not None:
                raise ClaudeMcpError(
                    ClaudeMcpErrorCode.CREDENTIAL_REQUIRED,
                    "Managed Claude MCP authentication must be refreshed.",
                )
            credential = await self.repository.get_credential(actor_id, server.id)
            if credential is None or credential.kind != "oauth" or self._is_expired(
                credential.expires_at
            ):
                raise ClaudeMcpError(
                    ClaudeMcpErrorCode.CREDENTIAL_REQUIRED,
                    "Managed Claude MCP authentication must be refreshed.",
                )
        document = self._credential_document(actor_id, server.id, credential)
        if credential.kind == "oauth":
            tokens = document.get("tokens")
            if not isinstance(tokens, dict) or not isinstance(tokens.get("access_token"), str):
                raise McpCredentialIntegrityError()
            headers = dict(config.get("headers", {}))
            headers["Authorization"] = f"Bearer {tokens['access_token']}"
            config["headers"] = headers
        elif credential.kind == "headers":
            config["headers"] = _string_mapping(document.get("headers"))
        elif credential.kind == "stdio_env":
            if server.transport is not McpTransport.STDIO:
                raise McpCredentialIntegrityError()
            config["env"] = {
                **_string_mapping(config.get("env", {})),
                **_string_mapping(document.get("env")),
            }
        else:
            raise McpCredentialIntegrityError()
        return config

    @staticmethod
    def _is_expired(expires_at: str | None) -> bool:
        if not expires_at:
            return False
        try:
            expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        except ValueError:
            raise McpCredentialIntegrityError() from None
        if expiry.tzinfo is None:
            raise McpCredentialIntegrityError()
        return expiry <= datetime.now(timezone.utc)

    def _credential_document(self, actor_id: str, server_id: str, record: Any) -> dict[str, Any]:
        if self.cipher is None:
            raise McpCredentialConfigurationError()
        plaintext = self.cipher.decrypt(
            McpEncryptedCredential(
                ciphertext=record.ciphertext,
                iv=record.iv,
                tag=record.tag,
                fingerprint=record.fingerprint,
                key_version=record.key_version,
            ),
            McpCredentialContext(
                user_id=actor_id,
                server_id=server_id,
                kind=record.kind,
                key_version=record.key_version,
            ),
        )
        try:
            document = json.loads(plaintext)
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise McpCredentialIntegrityError() from None
        if not isinstance(document, dict):
            raise McpCredentialIntegrityError()
        return document


__all__ = [
    "ManagedMcpRuntimeSnapshot",
    "ManagedMcpRuntimeSnapshotLoader",
    "SecretMcpConfigDict",
]
