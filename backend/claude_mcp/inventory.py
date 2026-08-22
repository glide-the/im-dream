"""Read-only Claude MCP tool inventory through the public Agent SDK.

[Input] One exact user runtime identity, one opaque MCP server definition, and bounded discovery policy.
[Output] Sanitized server metadata, tool names/descriptions, and formal MCP safety annotations.
[Pos] Public-SDK discovery adapter inside the claude-mcp domain; it never sends a prompt or invokes a tool.
[Sync] 2026-08-20: add get_mcp_status polling without `/mcp` TUI or private control subtypes.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from typing import Any, Protocol

from .contracts import (
    ClaudeMcpError,
    ClaudeMcpErrorCode,
    ClaudeMcpInventoryStatus,
    ClaudeMcpRuntimeIdentity,
    ClaudeMcpServerInfo,
    ClaudeMcpServerInventory,
    ClaudeMcpTool,
    ClaudeMcpToolAnnotations,
)
from .settings import ClaudeMcpSettings


_FINAL_STATUS_MAP = {
    "connected": ClaudeMcpInventoryStatus.CONNECTED,
    "failed": ClaudeMcpInventoryStatus.FAILED,
    "needs-auth": ClaudeMcpInventoryStatus.NEEDS_AUTH,
    "disabled": ClaudeMcpInventoryStatus.DISABLED,
}
_SAFE_RUNTIME_SCOPES = frozenset(
    {"dynamic", "project", "user", "local", "claudeai", "managed"}
)
_SAFE_TRANSPORTS = frozenset({"http", "sse", "stdio", "sdk", "claudeai-proxy"})


class _SdkClient(Protocol):
    async def __aenter__(self) -> "_SdkClient": ...

    async def __aexit__(self, *args: object) -> None: ...

    async def get_mcp_status(self) -> Mapping[str, object]: ...


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _bounded_text(value: object, *, maximum: int) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = " ".join(value.split()).strip()
    if not normalized:
        return None
    return normalized[:maximum]


def _optional_bool(value: object) -> bool | None:
    return value if isinstance(value, bool) else None


class ClaudeMcpInventoryClient:
    """Open one prompt-free streaming session and read its public MCP status."""

    def __init__(
        self,
        settings: ClaudeMcpSettings,
        *,
        sdk_client_factory: Callable[..., _SdkClient] | None = None,
        sdk_options_factory: Callable[..., object] | None = None,
    ) -> None:
        self.settings = settings
        self._sdk_client_factory = sdk_client_factory
        self._sdk_options_factory = sdk_options_factory

    def _factories(self) -> tuple[Callable[..., _SdkClient], Callable[..., object]]:
        if self._sdk_client_factory is not None and self._sdk_options_factory is not None:
            return self._sdk_client_factory, self._sdk_options_factory
        from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient

        return (
            self._sdk_client_factory or ClaudeSDKClient,
            self._sdk_options_factory or ClaudeAgentOptions,
        )

    def _options(
        self,
        *,
        identity: ClaudeMcpRuntimeIdentity,
        server_name: str,
        server_config: Mapping[str, object],
        secure_storage_home: str | None,
    ) -> object:
        _, options_factory = self._factories()
        environment = dict(identity.env)
        environment["CLAUDE_CONFIG_DIR"] = str(identity.config_dir)
        if secure_storage_home:
            environment["CLAUDE_SECURESTORAGE_CONFIG_DIR"] = secure_storage_home
        return options_factory(
            tools=[],
            mcp_servers={server_name: dict(server_config)},
            strict_mcp_config=True,
            cwd=str(identity.cwd),
            cli_path=identity.command[0],
            env=environment,
            permission_mode="dontAsk",
            max_turns=1,
        )

    async def inspect(
        self,
        *,
        identity: ClaudeMcpRuntimeIdentity,
        server_name: str,
        server_config: Mapping[str, object],
        secure_storage_home: str | None,
    ) -> ClaudeMcpServerInventory:
        options = self._options(
            identity=identity,
            server_name=server_name,
            server_config=server_config,
            secure_storage_home=secure_storage_home,
        )
        client_factory, _ = self._factories()
        try:
            async with asyncio.timeout(self.settings.inventory_timeout_seconds):
                async with client_factory(options=options) as client:
                    while True:
                        payload = await client.get_mcp_status()
                        selected = self._selected_server(payload, server_name)
                        raw_status = selected.get("status")
                        if raw_status in _FINAL_STATUS_MAP:
                            return self._inventory(
                                server_name=server_name,
                                server_config=server_config,
                                selected=selected,
                                status=_FINAL_STATUS_MAP[str(raw_status)],
                            )
                        if raw_status != "pending":
                            raise ClaudeMcpError(
                                ClaudeMcpErrorCode.INVENTORY_MALFORMED,
                                "Claude MCP inventory returned an unsupported status.",
                            )
                        await asyncio.sleep(
                            self.settings.inventory_poll_interval_ms / 1000
                        )
        except TimeoutError as exc:
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.INVENTORY_TIMEOUT,
                "Claude MCP tool discovery timed out.",
            ) from exc
        except ClaudeMcpError:
            raise
        except Exception as exc:
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.INVENTORY_UNAVAILABLE,
                "Claude MCP tool discovery is unavailable.",
            ) from exc

    def _selected_server(
        self,
        payload: Mapping[str, object],
        server_name: str,
    ) -> Mapping[str, object]:
        if not isinstance(payload, Mapping):
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.INVENTORY_MALFORMED,
                "Claude MCP inventory response is malformed.",
            )
        servers = payload.get("mcpServers")
        if not isinstance(servers, list):
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.INVENTORY_MALFORMED,
                "Claude MCP inventory response is malformed.",
            )
        for item in servers:
            if isinstance(item, Mapping) and item.get("name") == server_name:
                return item
        raise ClaudeMcpError(
            ClaudeMcpErrorCode.INVENTORY_MALFORMED,
            "Claude MCP inventory did not contain the requested server.",
        )

    def _inventory(
        self,
        *,
        server_name: str,
        server_config: Mapping[str, object],
        selected: Mapping[str, object],
        status: ClaudeMcpInventoryStatus,
    ) -> ClaudeMcpServerInventory:
        tools: list[ClaudeMcpTool] = []
        raw_tools = selected.get("tools", [])
        if status is ClaudeMcpInventoryStatus.CONNECTED and not isinstance(raw_tools, list):
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.INVENTORY_MALFORMED,
                "Claude MCP tool inventory is malformed.",
            )
        if isinstance(raw_tools, list):
            for raw_tool in raw_tools[: self.settings.max_inventory_tools]:
                if not isinstance(raw_tool, Mapping):
                    raise ClaudeMcpError(
                        ClaudeMcpErrorCode.INVENTORY_MALFORMED,
                        "Claude MCP tool inventory is malformed.",
                    )
                name = _bounded_text(
                    raw_tool.get("name"), maximum=self.settings.max_tool_name_length
                )
                if name is None:
                    raise ClaudeMcpError(
                        ClaudeMcpErrorCode.INVENTORY_MALFORMED,
                        "Claude MCP tool inventory is malformed.",
                    )
                raw_annotations = raw_tool.get("annotations")
                annotations = raw_annotations if isinstance(raw_annotations, Mapping) else {}
                tools.append(
                    ClaudeMcpTool(
                        name=name,
                        description=_bounded_text(
                            raw_tool.get("description"),
                            maximum=self.settings.max_tool_description_length,
                        ),
                        annotations=ClaudeMcpToolAnnotations(
                            read_only=_optional_bool(annotations.get("readOnly")),
                            destructive=_optional_bool(annotations.get("destructive")),
                            open_world=_optional_bool(annotations.get("openWorld")),
                        ),
                    )
                )

        raw_info = selected.get("serverInfo")
        server_info = None
        if isinstance(raw_info, Mapping):
            info_name = _bounded_text(raw_info.get("name"), maximum=256)
            info_version = _bounded_text(raw_info.get("version"), maximum=128)
            if info_name and info_version:
                server_info = ClaudeMcpServerInfo(info_name, info_version)

        raw_scope = selected.get("scope")
        runtime_scope = (
            raw_scope
            if isinstance(raw_scope, str) and raw_scope in _SAFE_RUNTIME_SCOPES
            else None
        )
        raw_transport = server_config.get("type")
        transport = (
            raw_transport
            if isinstance(raw_transport, str) and raw_transport in _SAFE_TRANSPORTS
            else None
        )
        raw_url = server_config.get("url")
        url = raw_url if isinstance(raw_url, str) and raw_url.startswith("https://") else None
        return ClaudeMcpServerInventory(
            server_name=server_name,
            status=status,
            config_scope="user",
            runtime_scope=runtime_scope,
            transport=transport,
            url=url,
            server_info=server_info,
            tools=tuple(tools),
            tool_count=len(raw_tools) if isinstance(raw_tools, list) else 0,
            tools_truncated=isinstance(raw_tools, list) and len(raw_tools) > len(tools),
            refreshed_at=_now(),
        )
