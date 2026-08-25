"""Claude MCP parser and secret-redaction contracts.

[Input] Representative bounded Claude MCP version/list/login/status output.
[Output] Colon-safe names, OAuth URL extraction, state/auth/failure mapping, and redacted secrets.
[Pos] Provider-free parser unit coverage for the `claude-mcp` compatibility seam.
[Sync] 2026-08-19: cover URL, malformed output, version gates, status, and redaction.
[Sync] 2026-08-21: cover absolute HTTP(S) URLs and fail-closed CLI config scope parsing.
[Sync] 2026-08-25: cover stable auth identity, semantic failure whitelist, and unknown-output fail-closed behavior.
"""

from __future__ import annotations

from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from claude_mcp.contracts import (
    ClaudeMcpAuthState,
    ClaudeMcpConfigScope,
    ClaudeMcpErrorCode,
    ClaudeMcpState,
)
from claude_mcp.parser import (
    parse_authorization_url,
    parse_runtime_failure_code,
    parse_server_auth_state,
    parse_server_names,
    parse_server_scope,
    parse_server_state,
    parse_server_transport,
    redact_sensitive,
    validate_redirect_url,
    validate_server_url,
    validate_server_name,
    version_at_least,
)


def test_authorization_url_is_extracted_without_treating_plain_urls_as_oauth() -> None:
    assert parse_authorization_url("Docs: https://example.test/docs") is None
    assert parse_authorization_url(
        "Open \x1b[32mhttps://oauth.example.test/authorize?state=abc\x1b[0m"
    ) == "https://oauth.example.test/authorize?state=abc"
    # Claude Code renders its authorization URL as an OSC-8 hyperlink: the
    # hidden target must be discarded while the visible URL remains exactly once.
    osc_url = "https://oauth.example.test/authorize?state=opaque"
    osc_output = f"Open \x1b]8;;{osc_url}\x07{osc_url}\x1b]8;;\x07\r\n"
    assert parse_authorization_url(osc_output) == osc_url
    assert parse_authorization_url("Waiting for browser with no URL") is None


def test_colon_bearing_plugin_server_names_survive_list_parsing() -> None:
    output = (
        "MCP servers\n"
        "plugin:comfy-cloud:comfy-cloud: https://mcp.example.test - ✓ Connected\n"
        "plain-server: stdio command - Needs auth\n"
    )
    assert parse_server_names(output, max_length=512) == [
        "plugin:comfy-cloud:comfy-cloud",
        "plain-server",
    ]
    assert validate_server_name("plugin:one:two", max_length=512) == "plugin:one:two"


def test_state_version_and_redirect_validation_fail_closed() -> None:
    assert parse_server_state("Status: Needs authentication") is ClaudeMcpState.NEEDS_AUTH
    assert parse_server_state("Status: ✓ Connected") is ClaudeMcpState.CONNECTED
    assert parse_server_state("No server found") is ClaudeMcpState.NOT_CONFIGURED
    assert (
        parse_server_state('No MCP server named "demo". Run `claude mcp add` to add one.')
        is ClaudeMcpState.NOT_CONFIGURED
    )
    for status in ("Failed", "Unavailable", "Forbidden", "✗ Failed"):
        assert parse_server_state(f"Status: {status}") is ClaudeMcpState.FAILED
    assert parse_server_state("Status: Configured") is ClaudeMcpState.CONFIGURED
    assert parse_server_state("Status: Logged out") is ClaudeMcpState.LOGGED_OUT
    assert parse_server_state("Status: Future state") is ClaudeMcpState.FAILED
    assert parse_server_state("provider says connected in raw text") is ClaudeMcpState.FAILED
    assert version_at_least("2.1.191 (Claude Code)", "2.1.191")
    assert not version_at_least("2.1.186", "2.1.191")
    assert not version_at_least("unknown", "2.1.191")
    assert validate_redirect_url(
        "https://callback.example.test/path?code=secret&state=opaque",
        max_length=8192,
    ).startswith("https://callback.example.test/")
    for invalid in ("javascript:alert(1)", "https://user:pass@example.test/callback", "not a url"):
        try:
            validate_redirect_url(invalid, max_length=8192)
        except ValueError:
            pass
        else:  # pragma: no cover - assertion branch
            raise AssertionError(f"accepted unsafe redirect: {invalid}")


def test_server_configuration_accepts_only_absolute_secret_free_http_urls() -> None:
    for valid in (
        "https://mcp.example.test/api",
        "http://mcp.example.test/api",
        "http://127.0.0.1:43123/mcp",
    ):
        assert validate_server_url(valid, max_length=2048) == valid
    for invalid in (
        "ftp://mcp.example.test",
        "https://user:secret@mcp.example.test",
        "https://mcp.example.test/api#fragment",
        "not-a-url",
    ):
        try:
            validate_server_url(invalid, max_length=2048)
        except ValueError:
            pass
        else:  # pragma: no cover
            raise AssertionError(f"accepted unsafe MCP server URL: {invalid}")


def test_server_scope_parsing_is_explicit_and_unknown_is_fail_closed() -> None:
    assert parse_server_scope(
        "Scope: User config (available in all your projects)"
    ) is ClaudeMcpConfigScope.USER
    assert parse_server_scope(
        "Scope: Local config (private to this project)"
    ) is ClaudeMcpConfigScope.LOCAL
    assert parse_server_scope(
        "Scope: Project config (shared via .mcp.json)"
    ) is ClaudeMcpConfigScope.PROJECT
    assert parse_server_scope("Scope: Plugin server") is ClaudeMcpConfigScope.PLUGIN
    assert parse_server_scope("Scope: Future config") is ClaudeMcpConfigScope.UNKNOWN
    assert parse_server_scope("Status: Connected") is ClaudeMcpConfigScope.UNKNOWN


def test_authentication_and_transport_projection_are_strict_and_backward_compatible() -> None:
    for value, expected in (
        ("anonymous", ClaudeMcpAuthState.ANONYMOUS),
        ("required", ClaudeMcpAuthState.REQUIRED),
        ("authenticated", ClaudeMcpAuthState.AUTHENTICATED),
        ("unknown", ClaudeMcpAuthState.UNKNOWN),
    ):
        assert (
            parse_server_auth_state(f"Authentication: {value}") is expected
        )
    assert parse_server_auth_state("Status: Connected") is ClaudeMcpAuthState.UNKNOWN
    assert (
        parse_server_auth_state("Authentication: future")
        is ClaudeMcpAuthState.UNKNOWN
    )
    assert parse_server_transport("Transport: http") == "http"
    assert parse_server_transport("Type: stdio") == "stdio"
    assert parse_server_transport("Transport: private-provider") is None
    assert parse_server_transport("Transport: http\nTransport: sse") is None


def test_runtime_failure_code_uses_only_the_fixed_safe_whitelist() -> None:
    expected = {
        "auth_not_required": ClaudeMcpErrorCode.AUTH_NOT_REQUIRED,
        "auth_not_advertised": ClaudeMcpErrorCode.AUTH_NOT_ADVERTISED,
        "metadata_invalid": ClaudeMcpErrorCode.AUTH_METADATA_INVALID,
        "network_unreachable": ClaudeMcpErrorCode.NETWORK_UNREACHABLE,
        "server_rejected": ClaudeMcpErrorCode.SERVER_REJECTED,
        "timeout": ClaudeMcpErrorCode.AUTH_TIMEOUT,
        "process_exited": ClaudeMcpErrorCode.PROCESS_EXITED,
        "cancelled": ClaudeMcpErrorCode.AUTH_CANCELLED,
    }
    for runtime_code, dream_code in expected.items():
        assert (
            parse_runtime_failure_code(f"Failure-Code: {runtime_code}")
            is dream_code
        )
    assert parse_runtime_failure_code("Failure-Code: provider_secret_error") is None
    assert (
        parse_runtime_failure_code(
            "Failure-Code: network_unreachable\nFailure-Code: server_rejected"
        )
        is None
    )


def test_sensitive_diagnostics_redact_oauth_and_bearer_material() -> None:
    raw = (
        "Authorization: Bearer bearer-secret\n"
        "https://callback.test/cb?code=auth-code&state=session-state\n"
        "access_token=access-secret refresh_token: refresh-secret "
        "client_secret=client-secret"
    )
    safe = redact_sensitive(raw)
    for secret in (
        "bearer-secret",
        "auth-code",
        "session-state",
        "access-secret",
        "refresh-secret",
        "client-secret",
    ):
        assert secret not in safe
    assert safe.count("<redacted>") >= 6
