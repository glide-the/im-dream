"""Bounded parsers and redaction for official Claude MCP CLI output.

[Input] Incremental terminal output from `claude mcp` argv commands.
[Output] Safe version, authorization URL, server status, and redacted diagnostic signals.
[Pos] Central compatibility seam; services never parse human CLI text directly.
[Sync] 2026-08-19: support colon-bearing server names and secret-safe OAuth parsing.
[Sync] 2026-08-19: validate the restricted user-scope HTTPS MCP server URL contract.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

from .contracts import ClaudeMcpState


_OSC_RE = re.compile(r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")
_ANSI_RE = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
_C0_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_VERSION_RE = re.compile(r"(?<!\d)(\d+)\.(\d+)\.(\d+)(?!\d)")
_URL_RE = re.compile(r"https?://[^\x00-\x20<>\"']+")
_SECRET_PATTERNS = (
    re.compile(r"(?i)(authorization\s*:\s*bearer\s+)[^\s]+"),
    re.compile(r"(?i)((?:access|refresh|id)_token[=:\s]+)[^\s&]+"),
    re.compile(r"(?i)(client_secret[=:\s]+)[^\s&]+"),
    re.compile(r"(?i)([?&](?:code|state)=)[^&#\s]+"),
)


def strip_terminal_control(text: str) -> str:
    without_osc = _OSC_RE.sub("", text)
    without_ansi = _ANSI_RE.sub("", without_osc).replace("\r", "")
    return _C0_RE.sub("", without_ansi)


def redact_sensitive(text: str, *, max_bytes: int = 65536) -> str:
    safe = strip_terminal_control(text)
    for pattern in _SECRET_PATTERNS:
        safe = pattern.sub(lambda match: f"{match.group(1)}<redacted>", safe)
    encoded = safe.encode("utf-8", errors="replace")
    if len(encoded) <= max_bytes:
        return safe
    half = max_bytes // 2
    return (
        encoded[:half].decode("utf-8", errors="replace")
        + "\n…<truncated>…\n"
        + encoded[-half:].decode("utf-8", errors="replace")
    )


def parse_version(text: str) -> tuple[int, int, int] | None:
    match = _VERSION_RE.search(strip_terminal_control(text))
    return tuple(int(part) for part in match.groups()) if match else None


def version_at_least(actual: str, minimum: str) -> bool:
    actual_parts = parse_version(actual)
    minimum_parts = parse_version(minimum)
    return bool(actual_parts and minimum_parts and actual_parts >= minimum_parts)


def validate_server_name(name: str, *, max_length: int) -> str:
    value = name.strip()
    if not value or len(value) > max_length:
        raise ValueError("server name length is invalid")
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError("server name contains control characters")
    return value


def validate_redirect_url(value: str, *, max_length: int) -> str:
    candidate = value.strip()
    parsed = urlparse(candidate)
    if (
        not candidate
        or len(candidate) > max_length
        or parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ValueError("redirect URL must be an absolute HTTP(S) URL")
    if any(ord(char) < 32 or ord(char) == 127 for char in candidate):
        raise ValueError("redirect URL contains control characters")
    return candidate


def validate_server_url(value: str, *, max_length: int) -> str:
    candidate = value.strip()
    parsed = urlparse(candidate)
    if (
        not candidate
        or len(candidate) > max_length
        or parsed.scheme != "https"
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or bool(parsed.fragment)
    ):
        raise ValueError("server URL must be an absolute HTTPS URL without credentials")
    if any(ord(char) < 32 or ord(char) == 127 for char in candidate):
        raise ValueError("server URL contains control characters")
    return candidate


def parse_authorization_url(text: str) -> str | None:
    """Return the first plausible OAuth URL from bounded incremental output."""
    for raw in _URL_RE.findall(strip_terminal_control(text)):
        candidate = raw.rstrip(".,);]")
        parsed = urlparse(candidate)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            continue
        marker = f"{parsed.path}?{parsed.query}".lower()
        if any(token in marker for token in ("authorize", "oauth", "consent")):
            return candidate
    return None


def parse_server_state(text: str) -> ClaudeMcpState:
    normalized = strip_terminal_control(text).lower()
    if any(
        marker in normalized
        for marker in (
            "not found",
            "no server",
            "no mcp server",
            "does not exist",
        )
    ):
        return ClaudeMcpState.NOT_CONFIGURED
    if any(
        marker in normalized
        for marker in (
            "needs authentication",
            "needs auth",
            "not authenticated",
            "authentication required",
            "unauthorized",
        )
    ):
        return ClaudeMcpState.NEEDS_AUTH
    if any(marker in normalized for marker in ("connected", "✓", "✔")):
        return ClaudeMcpState.CONNECTED
    if any(marker in normalized for marker in ("disabled", "not enabled")):
        return ClaudeMcpState.DISABLED
    if text.strip():
        return ClaudeMcpState.CONFIGURED
    return ClaudeMcpState.FAILED


def parse_server_names(text: str, *, max_length: int) -> list[str]:
    """Parse list rows without splitting colon-bearing names."""
    names: list[str] = []
    for raw_line in strip_terminal_control(text).splitlines():
        line = raw_line.strip()
        if not line or line.lower().startswith(("checking ", "no mcp", "mcp servers")):
            continue
        match = re.match(r"^(.*?)(?:\s+-\s+(?:✓|✔|✗|connected|failed|needs auth|disabled).*)$", line, re.I)
        prefix = (match.group(1) if match else line).strip(" •")
        # Claude prints `<name>: <transport/config> - <status>`. A plugin name
        # may itself contain `:`, so only `: ` is a structural delimiter.
        candidate = prefix.split(": ", 1)[0].strip()
        try:
            candidate = validate_server_name(candidate, max_length=max_length)
        except ValueError:
            continue
        if candidate not in names:
            names.append(candidate)
    return names
