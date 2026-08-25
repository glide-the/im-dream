"""Central policy settings for managed MCP plus legacy importer adapters.

[Input] Optional process-level policy environment variables and backend data root.
[Output] Validated discovery/cache/concurrency/OAuth/stdio policy plus retained legacy-import bounds.
[Pos] Sole configuration source for Claude MCP policy; route/service handlers contain no thresholds.
[Sync] 2026-08-19: add bounded, deployment-name-independent OAuth process settings.
[Sync] 2026-08-19: add the absolute server-owned user credential root and bounded JSON projection size.
[Sync] 2026-08-19: add the bounded restricted HTTP server URL policy.
[Sync] 2026-08-20: add bounded public-SDK tool inventory polling and payload limits.
[Sync] 2026-08-25: add database-managed discovery, cache, concurrency, OAuth, and stdio-profile policy.
[Sync] 2026-08-25: add an explicit standard-MCP inventory pagination page bound.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


_DEFAULT_RUNTIME_ROOT = (
    Path(__file__).resolve().parents[1] / "data" / "claude-mcp-runtime"
)


def _absolute_path(name: str, default: Path) -> Path:
    raw = os.environ.get(name, "").strip()
    candidate = Path(raw).expanduser() if raw else default
    if not candidate.is_absolute():
        return default.resolve(strict=False)
    return candidate.resolve(strict=False)


def _positive_int(name: str, default: int, *, maximum: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if 0 < value <= maximum else default


def _positive_float(name: str, default: float, *, maximum: float) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    return value if 0 < value <= maximum else default


@dataclass(frozen=True)
class ClaudeMcpSettings:
    auth_timeout_seconds: int
    command_timeout_seconds: int
    terminate_grace_seconds: int
    readiness_timeout_seconds: int
    max_capture_bytes: int
    max_server_name_length: int
    max_redirect_url_length: int
    max_server_url_length: int = 2048
    runtime_root: Path = _DEFAULT_RUNTIME_ROOT
    max_credential_file_bytes: int = 1048576
    minimum_cli_version: str = "2.1.186"
    headless_minimum_cli_version: str = "2.1.191"
    inventory_timeout_seconds: int = 30
    inventory_poll_interval_ms: int = 250
    max_inventory_tools: int = 512
    max_tool_name_length: int = 512
    max_tool_description_length: int = 4096
    discovery_max_parallel_servers: int = 5
    discovery_server_timeout_seconds: float = 30.0
    discovery_item_timeout_seconds: float = 15.0
    discovery_cache_ttl_seconds: float = 300.0
    max_inventory_items: int = 512
    max_inventory_text_length: int = 4096
    max_servers_per_actor: int = 64
    max_inventory_pages: int = 64
    oauth_redirect_uri: str | None = None
    oauth_client_name: str = "Ink & Memory Dream"
    stdio_profiles_json: str = "{}"

    @classmethod
    def from_env(cls) -> "ClaudeMcpSettings":
        return cls(
            runtime_root=_absolute_path(
                "INK_CLAUDE_MCP_RUNTIME_ROOT", _DEFAULT_RUNTIME_ROOT
            ),
            auth_timeout_seconds=_positive_int(
                "INK_CLAUDE_MCP_AUTH_TIMEOUT_SECONDS", 600, maximum=3600
            ),
            command_timeout_seconds=_positive_int(
                "INK_CLAUDE_MCP_COMMAND_TIMEOUT_SECONDS", 30, maximum=300
            ),
            terminate_grace_seconds=_positive_int(
                "INK_CLAUDE_MCP_TERMINATE_GRACE_SECONDS", 3, maximum=30
            ),
            readiness_timeout_seconds=_positive_int(
                "INK_CLAUDE_MCP_READINESS_TIMEOUT_SECONDS", 15, maximum=120
            ),
            max_capture_bytes=_positive_int(
                "INK_CLAUDE_MCP_MAX_CAPTURE_BYTES", 65536, maximum=1048576
            ),
            max_server_name_length=_positive_int(
                "INK_CLAUDE_MCP_MAX_SERVER_NAME_LENGTH", 512, maximum=2048
            ),
            max_redirect_url_length=_positive_int(
                "INK_CLAUDE_MCP_MAX_REDIRECT_URL_LENGTH", 8192, maximum=32768
            ),
            max_server_url_length=_positive_int(
                "INK_CLAUDE_MCP_MAX_SERVER_URL_LENGTH", 2048, maximum=8192
            ),
            max_credential_file_bytes=_positive_int(
                "INK_CLAUDE_MCP_MAX_CREDENTIAL_FILE_BYTES",
                1048576,
                maximum=16777216,
            ),
            inventory_timeout_seconds=_positive_int(
                "INK_CLAUDE_MCP_INVENTORY_TIMEOUT_SECONDS", 30, maximum=120
            ),
            inventory_poll_interval_ms=_positive_int(
                "INK_CLAUDE_MCP_INVENTORY_POLL_INTERVAL_MS", 250, maximum=5000
            ),
            max_inventory_tools=_positive_int(
                "INK_CLAUDE_MCP_MAX_INVENTORY_TOOLS", 512, maximum=4096
            ),
            max_tool_name_length=_positive_int(
                "INK_CLAUDE_MCP_MAX_TOOL_NAME_LENGTH", 512, maximum=2048
            ),
            max_tool_description_length=_positive_int(
                "INK_CLAUDE_MCP_MAX_TOOL_DESCRIPTION_LENGTH", 4096, maximum=16384
            ),
            discovery_max_parallel_servers=_positive_int(
                "INK_CLAUDE_MCP_DISCOVERY_MAX_PARALLEL_SERVERS", 5, maximum=64
            ),
            discovery_server_timeout_seconds=_positive_float(
                "INK_CLAUDE_MCP_DISCOVERY_SERVER_TIMEOUT_SECONDS", 30.0, maximum=300.0
            ),
            discovery_item_timeout_seconds=_positive_float(
                "INK_CLAUDE_MCP_DISCOVERY_ITEM_TIMEOUT_SECONDS", 15.0, maximum=120.0
            ),
            discovery_cache_ttl_seconds=_positive_float(
                "INK_CLAUDE_MCP_DISCOVERY_CACHE_TTL_SECONDS", 300.0, maximum=86400.0
            ),
            max_inventory_items=_positive_int(
                "INK_CLAUDE_MCP_MAX_INVENTORY_ITEMS", 512, maximum=4096
            ),
            max_inventory_text_length=_positive_int(
                "INK_CLAUDE_MCP_MAX_INVENTORY_TEXT_LENGTH", 4096, maximum=16384
            ),
            max_servers_per_actor=_positive_int(
                "INK_CLAUDE_MCP_MAX_SERVERS_PER_ACTOR", 64, maximum=1024
            ),
            max_inventory_pages=_positive_int(
                "INK_CLAUDE_MCP_MAX_INVENTORY_PAGES", 64, maximum=1024
            ),
            oauth_redirect_uri=os.environ.get("INK_CLAUDE_MCP_OAUTH_REDIRECT_URI", "").strip() or None,
            oauth_client_name=os.environ.get("INK_CLAUDE_MCP_OAUTH_CLIENT_NAME", "").strip() or "Ink & Memory Dream",
            stdio_profiles_json=os.environ.get("INK_CLAUDE_MCP_STDIO_PROFILES_JSON", "{}").strip() or "{}",
        )
