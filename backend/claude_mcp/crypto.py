"""AES-256-GCM envelope for managed MCP credentials.

[Input] Explicit process key configuration plus actor/server/kind/key-version AAD context.
[Output] Opaque ciphertext/IV/tag/fingerprint envelopes and fail-closed decryption.
[Pos] Sole managed MCP secret primitive; plaintext never enters DTOs, repr, logs, or errors.
[Sync] 2026-08-25: add cryptography-backed AES-GCM with actor/server AAD binding.
"""

from __future__ import annotations

import base64
from collections.abc import Mapping
from dataclasses import dataclass, replace
import hashlib
import hmac
import json
import os
from typing import Final

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


_KEY_ENV: Final = "INK_CLAUDE_MCP_CREDENTIAL_KEY"
_KEY_VERSION_ENV: Final = "INK_CLAUDE_MCP_CREDENTIAL_KEY_VERSION"
_MAX_PLAINTEXT_ENV: Final = "INK_CLAUDE_MCP_CREDENTIAL_MAX_BYTES"


class McpCredentialConfigurationError(RuntimeError):
    code = "CLAUDE_MCP_CREDENTIAL_ENCRYPTION_NOT_CONFIGURED"

    def __init__(self) -> None:
        super().__init__("Claude MCP credential encryption is not configured.")


class McpCredentialIntegrityError(RuntimeError):
    code = "CLAUDE_MCP_CREDENTIAL_INVALID"

    def __init__(self) -> None:
        super().__init__("Claude MCP credential could not be verified.")


@dataclass(frozen=True)
class McpCredentialContext:
    user_id: str
    server_id: str
    kind: str
    key_version: int

    def __post_init__(self) -> None:
        if (
            not self.user_id
            or not self.server_id
            or self.kind not in {"oauth", "headers", "stdio_env"}
            or self.key_version < 1
        ):
            raise ValueError("invalid MCP credential context")

    def aad(self) -> bytes:
        return json.dumps(
            {
                "domain": "dream-managed-mcp-credential-v1",
                "kind": self.kind,
                "keyVersion": self.key_version,
                "serverId": self.server_id,
                "userId": self.user_id,
            },
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("ascii")


@dataclass(frozen=True, repr=False)
class McpEncryptedCredential:
    ciphertext: str
    iv: str
    tag: str
    fingerprint: str
    key_version: int

    def __repr__(self) -> str:
        return (
            "McpEncryptedCredential(configured=True, "
            f"key_version={self.key_version}, fingerprint=<redacted>)"
        )

    def safe_dict(self) -> dict[str, object]:
        return {
            "configured": True,
            "keyVersion": self.key_version,
            "fingerprint": self.fingerprint,
        }

    def with_ciphertext(self, ciphertext: str) -> "McpEncryptedCredential":
        return replace(self, ciphertext=ciphertext)


def _parse_key(raw: str) -> bytes:
    value = raw.strip()
    try:
        if len(value) == 64:
            decoded = bytes.fromhex(value)
        else:
            decoded = base64.b64decode(value, validate=True)
    except (ValueError, TypeError):
        raise McpCredentialConfigurationError() from None
    if len(decoded) != 32:
        raise McpCredentialConfigurationError()
    return decoded


def _positive_config(values: Mapping[str, str], name: str, default: int, maximum: int) -> int:
    raw = values.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        raise McpCredentialConfigurationError() from None
    if value < 1 or value > maximum:
        raise McpCredentialConfigurationError()
    return value


class McpCredentialCipher:
    """Encrypt and authenticate one bounded credential document."""

    def __init__(self, *, key: bytes, key_version: int, max_plaintext_bytes: int = 1_048_576) -> None:
        if len(key) != 32 or key_version < 1 or max_plaintext_bytes < 1:
            raise McpCredentialConfigurationError()
        self._key = bytes(key)
        self.key_version = key_version
        self.max_plaintext_bytes = max_plaintext_bytes
        self._aesgcm = AESGCM(self._key)

    @classmethod
    def from_env(cls, *, environ: Mapping[str, str] | None = None) -> "McpCredentialCipher":
        values = os.environ if environ is None else environ
        raw = values.get(_KEY_ENV)
        if not isinstance(raw, str) or not raw.strip():
            raise McpCredentialConfigurationError()
        return cls(
            key=_parse_key(raw),
            key_version=_positive_config(values, _KEY_VERSION_ENV, 1, 2_147_483_647),
            max_plaintext_bytes=_positive_config(values, _MAX_PLAINTEXT_ENV, 1_048_576, 16_777_216),
        )

    def encrypt(self, plaintext: bytes, context: McpCredentialContext) -> McpEncryptedCredential:
        if context.key_version != self.key_version:
            raise McpCredentialConfigurationError()
        if not plaintext or len(plaintext) > self.max_plaintext_bytes:
            raise McpCredentialIntegrityError()
        iv = os.urandom(12)
        combined = self._aesgcm.encrypt(iv, plaintext, context.aad())
        ciphertext, tag = combined[:-16], combined[-16:]
        fingerprint = hmac.new(
            self._key,
            b"dream-managed-mcp-fingerprint-v1\0" + plaintext,
            hashlib.sha256,
        ).hexdigest()[:16]
        return McpEncryptedCredential(
            ciphertext=base64.b64encode(ciphertext).decode("ascii"),
            iv=base64.b64encode(iv).decode("ascii"),
            tag=base64.b64encode(tag).decode("ascii"),
            fingerprint=fingerprint,
            key_version=self.key_version,
        )

    def decrypt(self, envelope: McpEncryptedCredential, context: McpCredentialContext) -> bytes:
        if envelope.key_version != context.key_version or context.key_version != self.key_version:
            raise McpCredentialIntegrityError()
        try:
            iv = base64.b64decode(envelope.iv, validate=True)
            ciphertext = base64.b64decode(envelope.ciphertext, validate=True)
            tag = base64.b64decode(envelope.tag, validate=True)
            if len(iv) != 12 or len(tag) != 16:
                raise ValueError
            plaintext = self._aesgcm.decrypt(iv, ciphertext + tag, context.aad())
        except (InvalidTag, ValueError, TypeError):
            raise McpCredentialIntegrityError() from None
        if not plaintext or len(plaintext) > self.max_plaintext_bytes:
            raise McpCredentialIntegrityError()
        return plaintext


__all__ = [
    "McpCredentialCipher",
    "McpCredentialConfigurationError",
    "McpCredentialContext",
    "McpCredentialIntegrityError",
    "McpEncryptedCredential",
]
