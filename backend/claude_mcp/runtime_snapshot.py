"""In-memory Runtime projection of managed MCP configuration.

[Input] Enabled actor user/workspace Server rows, stdio policy profiles, and encrypted credential references.
[Output] Detached public Agent-SDK `mcp_servers` mapping with workspace override and redacted repr.
[Pos] Injectable Chat integration seam; performs no file write, logging, Agent import, CLI, or MCP network call.
[Sync] 2026-08-25: add actor/workspace managed snapshot loader for later Chat service injection.
[Sync] 2026-08-25: refresh expired OAuth through bounded standard-MCP discovery before projecting a Runtime bearer header.
[Sync] 2026-09-06: re-read identity/enabled/revisions before any single-Server credential access.
[Sync] 2026-09-06: return only a post-refresh record/credential-coherent single-Server projection.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timezone
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


@dataclass(frozen=True, repr=False)
class ManagedMcpServerConfigProjection:
    """One coherent single-Server config plus its authoritative revisions."""

    config: SecretMcpConfigDict
    config_revision: int
    credential_revision: int

    def __repr__(self) -> str:
        return (
            "ManagedMcpServerConfigProjection("
            f"config_revision={self.config_revision}, "
            f"credential_revision={self.credential_revision}, config=<redacted>)"
        )


@dataclass(frozen=True)
class _McpConfigMaterial:
    config: SecretMcpConfigDict
    credential_id: str | None
    credential_revision: int
    refreshed: bool


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

    async def load_server_config(
        self,
        actor_id: str,
        server: Any,
        *,
        expected_config_revision: int | None = None,
        expected_credential_revision: int | None = None,
    ) -> ManagedMcpServerConfigProjection:
        """Project one already-scoped Server after identity/enabled checks.

        The caller must obtain the row through the actor-scoped repository. These
        checks intentionally happen before `_server_config` can read/decrypt a
        credential and leave the existing multi-Server `load()` path unchanged.
        """
        if str(server.user_id) != str(actor_id) or not server.enabled:
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.APP_RUNTIME_DENIED,
                "MCP Apps connection view is unavailable.",
            )
        current = await self.repository.get_server(
            actor_id,
            server.id,
            server.workspace_id,
        )
        if not self._same_enabled_server(actor_id, server, current):
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.APP_RUNTIME_DENIED,
                "MCP Apps connection view is unavailable.",
            )
        if (
            expected_config_revision is not None
            and current.config_revision != expected_config_revision
        ) or (
            expected_credential_revision is not None
            and current.credential_revision != expected_credential_revision
        ):
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.APP_RUNTIME_REVISION_CONFLICT,
                "MCP Apps session revision is no longer current.",
            )
        material = await self._server_config_material(actor_id, current)
        authoritative = await self.repository.get_server(
            actor_id,
            current.id,
            current.workspace_id,
        )
        if not self._same_enabled_server(actor_id, current, authoritative):
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.APP_RUNTIME_DENIED,
                "MCP Apps connection view is unavailable.",
            )
        if (
            authoritative.config_revision != current.config_revision
            or authoritative.credential_revision != material.credential_revision
            or authoritative.credential_id != material.credential_id
            or authoritative.credential_configured
            != (material.credential_id is not None)
            or (
                material.refreshed
                and authoritative.credential_revision
                <= current.credential_revision
            )
        ):
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.APP_RUNTIME_REVISION_CONFLICT,
                "MCP Apps session revision is no longer current.",
            )
        return ManagedMcpServerConfigProjection(
            config=material.config,
            config_revision=authoritative.config_revision,
            credential_revision=authoritative.credential_revision,
        )

    async def _server_config(self, actor_id: str, server: Any) -> SecretMcpConfigDict:
        return (await self._server_config_material(actor_id, server)).config

    async def _server_config_material(
        self,
        actor_id: str,
        server: Any,
    ) -> _McpConfigMaterial:
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
            return _McpConfigMaterial(config, None, 0, False)
        if (
            str(credential.server_id) != str(server.id)
            or str(credential.user_id) != str(actor_id)
        ):
            raise McpCredentialIntegrityError()
        refreshed = False
        if credential.kind == "oauth" and server.auth_kind.value != "oauth":
            raise McpCredentialIntegrityError()
        if credential.kind == "oauth" and self._is_expired(credential.expires_at):
            if self.oauth_refresher is None:
                raise ClaudeMcpError(
                    ClaudeMcpErrorCode.CREDENTIAL_REQUIRED,
                    "Managed Claude MCP authentication must be refreshed.",
                )
            previous_credential_revision = credential.credential_revision
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
            if (
                credential is None
                or str(credential.server_id) != str(server.id)
                or str(credential.user_id) != str(actor_id)
                or credential.kind != "oauth"
                or credential.credential_revision <= previous_credential_revision
                or self._is_expired(credential.expires_at)
            ):
                raise ClaudeMcpError(
                    ClaudeMcpErrorCode.CREDENTIAL_REQUIRED,
                    "Managed Claude MCP authentication must be refreshed.",
                )
            refreshed = True
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
        return _McpConfigMaterial(
            config,
            str(credential.id),
            credential.credential_revision,
            refreshed,
        )

    @staticmethod
    def _same_enabled_server(actor_id: str, expected: Any, current: Any) -> bool:
        return bool(
            current is not None
            and str(current.id) == str(expected.id)
            and str(current.user_id) == str(actor_id)
            and current.server_key == expected.server_key
            and current.scope == expected.scope
            and current.workspace_id == expected.workspace_id
            and current.enabled
        )

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
    "ManagedMcpServerConfigProjection",
    "SecretMcpConfigDict",
]
