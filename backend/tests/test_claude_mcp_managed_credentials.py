"""Provider-free managed MCP credential-envelope contracts.

[Input] Synthetic keys, actor/server bindings, and tampered ciphertext bytes.
[Output] AES-256-GCM round-trip plus fail-closed key/AAD/tamper evidence.
[Pos] Managed MCP credential boundary tests; no database, provider, or real secret access.
[Sync] 2026-08-25: define the database-managed credential envelope contract.
"""

from __future__ import annotations

import base64

import pytest

from claude_mcp.crypto import (
    McpCredentialCipher,
    McpCredentialConfigurationError,
    McpCredentialContext,
    McpCredentialIntegrityError,
)
from claude_mcp.service import build_default_claude_mcp_service


def _context(*, user_id: str = "7") -> McpCredentialContext:
    return McpCredentialContext(
        user_id=user_id,
        server_id="server-1",
        kind="oauth",
        key_version=3,
    )


def test_aes_gcm_round_trip_repr_and_projection_never_expose_plaintext() -> None:
    cipher = McpCredentialCipher(key=b"k" * 32, key_version=3)
    plaintext = b'{"access_token":"top-secret","token_type":"Bearer"}'

    envelope = cipher.encrypt(plaintext, _context())

    assert cipher.decrypt(envelope, _context()) == plaintext
    assert "top-secret" not in repr(envelope)
    assert "top-secret" not in repr(envelope.safe_dict())
    assert envelope.safe_dict() == {
        "configured": True,
        "keyVersion": 3,
        "fingerprint": envelope.fingerprint,
    }


def test_tamper_and_wrong_actor_fail_with_the_same_safe_error() -> None:
    cipher = McpCredentialCipher(key=b"k" * 32, key_version=3)
    envelope = cipher.encrypt(b"private", _context())
    tampered = envelope.with_ciphertext(
        base64.b64encode(base64.b64decode(envelope.ciphertext)[:-1] + b"x").decode()
    )

    for candidate, context in (
        (tampered, _context()),
        (envelope, _context(user_id="8")),
    ):
        with pytest.raises(McpCredentialIntegrityError) as raised:
            cipher.decrypt(candidate, context)
        assert "private" not in str(raised.value)
        assert raised.value.code == "CLAUDE_MCP_CREDENTIAL_INVALID"


def test_missing_or_malformed_key_configuration_fails_closed() -> None:
    for environ in ({}, {"INK_CLAUDE_MCP_CREDENTIAL_KEY": "not-a-key"}):
        with pytest.raises(McpCredentialConfigurationError):
            McpCredentialCipher.from_env(environ=environ)


def test_missing_key_does_not_prevent_default_service_startup(monkeypatch) -> None:
    from backend.persistence.postgres import PostgresPool

    class _Pool:
        def __init__(self):
            self.opened = False
            self.closed = False

        def open(self):
            self.opened = True

        def close(self):
            self.closed = True

        def connection(self, *_args, **_kwargs):  # never entered in this test
            raise AssertionError("database must not be touched during composition")

    pool = _Pool()
    monkeypatch.setattr(
        PostgresPool,
        "from_env",
        classmethod(lambda _cls, **_kwargs: pool),
    )
    monkeypatch.delenv("INK_CLAUDE_MCP_CREDENTIAL_KEY", raising=False)

    service = build_default_claude_mcp_service()

    assert pool.opened is True
    assert service.runtime_snapshot_loader.cipher is None
