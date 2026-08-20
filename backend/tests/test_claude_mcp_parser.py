"""Claude MCP parser and secret-redaction contracts.

[Input] Representative bounded Claude MCP version/list/login/status output.
[Output] Colon-safe names, OAuth URL extraction, state mapping, and redacted secrets.
[Pos] Provider-free parser unit coverage for the `claude-mcp` compatibility seam.
[Sync] 2026-08-19: cover URL, malformed output, version gates, status, and redaction.
[Sync] 2026-08-21: cover absolute HTTP(S) URLs and fail-closed CLI config scope parsing.
"""

from __future__ import annotations

from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from claude_mcp.contracts import ClaudeMcpConfigScope, ClaudeMcpState
from claude_mcp.parser import (
    parse_authorization_url,
    parse_server_names,
    parse_server_scope,
    parse_server_state,
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
