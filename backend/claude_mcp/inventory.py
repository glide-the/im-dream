"""Standard Python MCP SDK discovery with bounded per-Server concurrency.

[Input] Actor-owned managed Server rows, injected stdio profiles/auth, and mcp 1.27.1 clients.
[Output] Safe tools/resources/prompts snapshots with timeout, cancel, cache, single-flight, and partial-result semantics.
[Pos] Online MCP protocol boundary; deliberately contains no Agent SDK, Runtime, CLI, subprocess API, or database DDL.
[Sync] 2026-08-25: replace Agent-Runtime inventory polling with direct standard MCP ClientSession discovery.
[Sync] 2026-08-25: exhaust bounded tools/resources/prompts pagination inside the same initialized MCP session.
[Sync] 2026-08-25: isolate interactive OAuth discovery from short inventory single-flight/timeout ownership.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Mapping
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from enum import Enum
import ipaddress
import json
import logging
from pathlib import Path
import tempfile
from typing import Any, Protocol
from urllib.parse import urlsplit

from .contracts import ClaudeMcpError, ClaudeMcpErrorCode, McpTransport
from .crypto import McpCredentialConfigurationError
from .repository import McpServerRecord


logger = logging.getLogger(__name__)


class McpDiscoveryStatus(str, Enum):
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class McpDiscoveryError:
    code: str
    retryable: bool

    def to_dict(self) -> dict[str, object]:
        return {"code": self.code, "retryable": self.retryable}


@dataclass(frozen=True)
class McpDiscoveryResult:
    server_id: str
    status: McpDiscoveryStatus
    config_revision: int
    credential_revision: int
    tools: tuple[dict[str, Any], ...]
    resources: tuple[dict[str, Any], ...]
    prompts: tuple[dict[str, Any], ...]
    server_info: dict[str, str] | None
    error: McpDiscoveryError | None
    discovered_at: str
    cached: bool = False
    truncated: bool = False

    def inventory_dict(self) -> dict[str, Any]:
        return {
            "tools": list(self.tools),
            "resources": list(self.resources),
            "prompts": list(self.prompts),
            "serverInfo": self.server_info,
            "truncated": self.truncated,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "server_id": self.server_id,
            "status": self.status.value,
            "config_revision": self.config_revision,
            "credential_revision": self.credential_revision,
            **self.inventory_dict(),
            "error": self.error.to_dict() if self.error else None,
            "discovered_at": self.discovered_at,
            "cached": self.cached,
        }


@dataclass(frozen=True)
class McpDiscoveryPolicy:
    max_parallel_servers: int
    server_timeout_seconds: float
    item_timeout_seconds: float
    max_inventory_items: int
    max_inventory_pages: int
    max_text_length: int
    cache_ttl_seconds: float = 300.0

    def __post_init__(self) -> None:
        if (
            self.max_parallel_servers < 1
            or self.server_timeout_seconds <= 0
            or self.item_timeout_seconds <= 0
            or self.max_inventory_items < 1
            or self.max_inventory_pages < 1
            or self.max_text_length < 1
            or self.cache_ttl_seconds <= 0
        ):
            raise ValueError("invalid MCP discovery policy")


class McpTransportHttpError(RuntimeError):
    """Provider-free HTTP classification seam; response bodies stay private."""

    def __init__(self, status_code: int, *, private_body: str | None = None) -> None:
        self.status_code = status_code
        self._private_body = private_body
        super().__init__("MCP transport HTTP request failed.")


@dataclass(frozen=True, repr=False)
class StdioProfile:
    command: str
    args: tuple[str, ...]
    env: Mapping[str, str]
    cwd: str | None

    def __repr__(self) -> str:
        return f"StdioProfile(command={self.command!r}, args_count={len(self.args)}, env=<redacted>)"


class StdioProfileResolver:
    """Resolve only server-owned absolute executable profiles."""

    def __init__(self, profiles: Mapping[str, StdioProfile]) -> None:
        self._profiles = dict(profiles)

    @classmethod
    def from_json(cls, raw: str) -> "StdioProfileResolver":
        try:
            payload = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            payload = None
        if not isinstance(payload, dict):
            raise ValueError("invalid stdio profile policy")
        profiles: dict[str, StdioProfile] = {}
        for key, value in payload.items():
            if not isinstance(key, str) or not isinstance(value, dict):
                raise ValueError("invalid stdio profile policy")
            command = value.get("command")
            args = value.get("args", [])
            env = value.get("env", {})
            cwd = value.get("cwd")
            if (
                not isinstance(command, str)
                or not Path(command).is_absolute()
                or not isinstance(args, list)
                or not all(isinstance(item, str) and item for item in args)
                or not isinstance(env, dict)
                or not all(isinstance(k, str) and isinstance(v, str) for k, v in env.items())
                or (cwd is not None and (not isinstance(cwd, str) or not Path(cwd).is_absolute()))
            ):
                raise ValueError("invalid stdio profile policy")
            profiles[key] = StdioProfile(command, tuple(args), dict(env), cwd)
        return cls(profiles)

    def resolve(self, key: str) -> StdioProfile:
        try:
            return self._profiles[key]
        except KeyError:
            raise ValueError("stdio profile is not allowed") from None


class McpSessionFactory(Protocol):
    def open(
        self,
        server: McpServerRecord,
        *,
        auth: Any = None,
        request_read_timeout_seconds: float | None = None,
    ): ...


def _validate_remote_url(url: str) -> str:
    parsed = urlsplit(url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("remote MCP endpoint is denied")
    try:
        address = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        pass
    else:
        if not address.is_global:
            raise ValueError("remote MCP endpoint is denied")
    return url


class McpSdkSessionFactory:
    """Open one request-local mcp.ClientSession for each transport."""

    def __init__(
        self,
        *,
        stdio_profiles: StdioProfileResolver,
        connect_timeout_seconds: float,
        read_timeout_seconds: float,
    ) -> None:
        if connect_timeout_seconds <= 0 or read_timeout_seconds <= 0:
            raise ValueError("MCP transport timeouts must be positive")
        self._stdio_profiles = stdio_profiles
        self._connect_timeout_seconds = connect_timeout_seconds
        self._read_timeout_seconds = read_timeout_seconds

    @asynccontextmanager
    async def open(
        self,
        server: McpServerRecord,
        *,
        auth: Any = None,
        request_read_timeout_seconds: float | None = None,
    ) -> AsyncIterator[Any]:
        from mcp import ClientSession
        from mcp.client.sse import sse_client
        from mcp.client.stdio import StdioServerParameters, stdio_client
        from mcp.client.streamable_http import streamable_http_client

        async with AsyncExitStack() as stack:
            if server.transport is McpTransport.STDIO:
                if auth is not None or not server.stdio_profile_key:
                    raise ValueError("stdio authentication/profile is invalid")
                profile = self._stdio_profiles.resolve(server.stdio_profile_key)
                stderr = tempfile.TemporaryFile(mode="w+", encoding="utf-8")
                stack.callback(stderr.close)
                streams = await stack.enter_async_context(
                    stdio_client(
                        StdioServerParameters(
                            command=profile.command,
                            args=list(profile.args),
                            env=dict(profile.env),
                            cwd=profile.cwd,
                        ),
                        errlog=stderr,
                    )
                )
                read_stream, write_stream = streams
            elif server.transport is McpTransport.SSE:
                if not server.remote_url:
                    raise ValueError("remote MCP URL is unavailable")
                streams = await stack.enter_async_context(
                    sse_client(
                        _validate_remote_url(server.remote_url),
                        timeout=self._connect_timeout_seconds,
                        sse_read_timeout=self._read_timeout_seconds,
                        auth=auth,
                    )
                )
                read_stream, write_stream = streams
            elif server.transport is McpTransport.STREAMABLE_HTTP:
                if not server.remote_url:
                    raise ValueError("remote MCP URL is unavailable")
                import httpx

                client = await stack.enter_async_context(
                    httpx.AsyncClient(
                        auth=auth,
                        follow_redirects=False,
                        timeout=httpx.Timeout(
                            self._read_timeout_seconds,
                            connect=self._connect_timeout_seconds,
                        ),
                    )
                )
                streams = await stack.enter_async_context(
                    streamable_http_client(
                        _validate_remote_url(server.remote_url),
                        http_client=client,
                    )
                )
                read_stream, write_stream, _session_id = streams
            else:  # pragma: no cover - enum guards this in normal code
                raise ValueError("unsupported MCP transport")

            session = await stack.enter_async_context(
                ClientSession(
                    read_stream,
                    write_stream,
                    read_timeout_seconds=timedelta(
                        seconds=(
                            request_read_timeout_seconds
                            if request_read_timeout_seconds is not None
                            else self._read_timeout_seconds
                        )
                    ),
                )
            )
            yield session


def _safe_text(value: Any, maximum: int) -> str | None:
    if value is None:
        return None
    text = str(value).replace("\x00", "").strip()
    return text[:maximum] if text else None


def _annotations(value: Any) -> dict[str, bool | None]:
    if value is None:
        return {"read_only": None, "destructive": None, "open_world": None}
    return {
        "read_only": getattr(value, "readOnlyHint", getattr(value, "read_only", None)),
        "destructive": getattr(value, "destructiveHint", getattr(value, "destructive", None)),
        "open_world": getattr(value, "openWorldHint", getattr(value, "open_world", None)),
    }


def _status_from_exception(exc: BaseException) -> int | None:
    queue = [exc]
    seen: set[int] = set()
    while queue:
        current = queue.pop(0)
        if id(current) in seen:
            continue
        seen.add(id(current))
        status = getattr(current, "status_code", None)
        if isinstance(status, int):
            return status
        response = getattr(current, "response", None)
        status = getattr(response, "status_code", None)
        if isinstance(status, int):
            return status
        queue.extend(getattr(current, "exceptions", ()) or ())
        cause = current.__cause__ or current.__context__
        if cause is not None:
            queue.append(cause)
    return None


def _safe_error(exc: BaseException) -> McpDiscoveryError:
    if isinstance(exc, ClaudeMcpError):
        retryable_codes = {
            ClaudeMcpErrorCode.INVENTORY_TIMEOUT,
            ClaudeMcpErrorCode.NETWORK_UNREACHABLE,
        }
        return McpDiscoveryError(
            exc.code.value,
            exc.code in retryable_codes,
        )
    status = _status_from_exception(exc)
    if status in {401, 403}:
        return McpDiscoveryError("CLAUDE_MCP_CREDENTIAL_REQUIRED", False)
    if status == 404:
        return McpDiscoveryError("CLAUDE_MCP_SERVER_REJECTED", False)
    if isinstance(exc, TimeoutError):
        return McpDiscoveryError("CLAUDE_MCP_INVENTORY_TIMEOUT", True)
    if isinstance(exc, McpCredentialConfigurationError):
        return McpDiscoveryError(
            "CLAUDE_MCP_CREDENTIAL_ENCRYPTION_NOT_CONFIGURED", False
        )
    if isinstance(exc, ValueError):
        return McpDiscoveryError("CLAUDE_MCP_SERVER_CONFIGURATION_INVALID", False)
    return McpDiscoveryError("CLAUDE_MCP_PROTOCOL_ERROR", True)


def _exception_type_summary(exc: BaseException) -> str:
    """Return only exception class names; never render provider payloads."""

    queue = [exc]
    seen: set[int] = set()
    names: set[str] = set()
    while queue and len(seen) < 32:
        current = queue.pop(0)
        if id(current) in seen:
            continue
        seen.add(id(current))
        names.add(type(current).__name__)
        queue.extend(getattr(current, "exceptions", ()) or ())
        cause = current.__cause__ or current.__context__
        if cause is not None:
            queue.append(cause)
    return ",".join(sorted(names))[:512]


class McpDiscoveryCoordinator:
    """Discover independent Servers concurrently and deduplicate equal revisions."""

    def __init__(
        self,
        repository: Any,
        session_factory: McpSessionFactory,
        *,
        policy: McpDiscoveryPolicy,
        auth_resolver: Any = None,
    ) -> None:
        self.repository = repository
        self.session_factory = session_factory
        self.policy = policy
        self.auth_resolver = auth_resolver
        self._semaphore = asyncio.Semaphore(policy.max_parallel_servers)
        self._inflight: dict[tuple[str, str, int, int], asyncio.Task[McpDiscoveryResult]] = {}
        self._inflight_lock = asyncio.Lock()

    async def discover_many(
        self,
        actor_id: str,
        server_ids: list[str],
        *,
        workspace_id: str | None = None,
        force: bool = False,
    ) -> list[McpDiscoveryResult]:
        if not server_ids:
            return []
        results: list[McpDiscoveryResult | None] = [None] * len(server_ids)

        async def worker(index: int, server_id: str) -> None:
            try:
                results[index] = await self.discover_one(
                    actor_id,
                    server_id,
                    workspace_id=workspace_id,
                    force=force,
                )
            except asyncio.CancelledError:
                raise
            except BaseException as exc:
                results[index] = McpDiscoveryResult(
                    server_id=server_id,
                    status=McpDiscoveryStatus.FAILED,
                    config_revision=0,
                    credential_revision=0,
                    tools=(), resources=(), prompts=(), server_info=None,
                    error=_safe_error(exc),
                    discovered_at=datetime.now(timezone.utc).isoformat(),
                )

        async with asyncio.TaskGroup() as group:
            for index, server_id in enumerate(server_ids):
                group.create_task(worker(index, server_id))
        return [item for item in results if item is not None]

    async def discover_one(
        self,
        actor_id: str,
        server_id: str,
        *,
        workspace_id: str | None = None,
        force: bool = False,
        auth: Any = None,
        operation_timeout_seconds: float | None = None,
    ) -> McpDiscoveryResult:
        server = await self.repository.get_server(actor_id, server_id, workspace_id)
        if server is None:
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.SERVER_NOT_FOUND,
                "Claude MCP server was not found.",
            )
        if not force:
            cached = await self.repository.get_discovery_snapshot(actor_id, server)
            parsed = self._cached_result(server, cached)
            if parsed is not None:
                return replace(parsed, cached=True)

        if operation_timeout_seconds is not None and operation_timeout_seconds <= 0:
            raise ValueError("MCP operation timeout must be positive")
        if auth is not None:
            # Interactive OAuth owns a process-local callback Future and can
            # wait much longer than an ordinary inventory request.  It must
            # not share or shield the anonymous discovery single-flight: an
            # auth cancel must cancel this exact SDK session, and an unrelated
            # list refresh must never inherit the OAuth provider/state.
            return await self._discover_and_save(
                actor_id,
                server,
                auth=auth,
                timeout_seconds=(
                    operation_timeout_seconds
                    if operation_timeout_seconds is not None
                    else self.policy.server_timeout_seconds
                ),
            )

        key = (
            actor_id,
            server.id,
            server.config_revision,
            server.credential_revision,
        )
        async with self._inflight_lock:
            task = self._inflight.get(key)
            if task is None:
                task = asyncio.create_task(
                    self._discover_and_save(actor_id, server, auth=auth)
                )
                self._inflight[key] = task
        try:
            return await asyncio.shield(task)
        except asyncio.CancelledError:
            # The initiating HTTP task may be cancelled while another waiter
            # still owns the same revision. Explicit operation cancellation is
            # handled by the service/coordinator task owner.
            raise
        finally:
            if task.done():
                async with self._inflight_lock:
                    if self._inflight.get(key) is task:
                        self._inflight.pop(key, None)

    async def cancel(self, actor_id: str, server_id: str) -> bool:
        """Cancel only in-flight discovery tasks for one actor-owned Server."""
        async with self._inflight_lock:
            tasks = [
                task
                for key, task in self._inflight.items()
                if key[0] == actor_id and key[1] == server_id and not task.done()
            ]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        return bool(tasks)

    def _cached_result(self, server: McpServerRecord, cached: Any) -> McpDiscoveryResult | None:
        if cached is None:
            return None
        if isinstance(cached, McpDiscoveryResult):
            if (
                cached.config_revision == server.config_revision
                and cached.credential_revision == server.credential_revision
            ):
                return cached
            return None
        if not isinstance(cached, Mapping):
            return None
        inventory = cached.get("inventory")
        if not isinstance(inventory, Mapping):
            return None
        try:
            status = McpDiscoveryStatus(str(cached["status"]))
        except (KeyError, ValueError):
            return None
        error_code = cached.get("safe_error_code")
        non_retryable = {
            "CLAUDE_MCP_CREDENTIAL_REQUIRED",
            "CLAUDE_MCP_CREDENTIAL_ENCRYPTION_NOT_CONFIGURED",
            "CLAUDE_MCP_SERVER_REJECTED",
            "CLAUDE_MCP_SERVER_CONFIGURATION_INVALID",
            "CLAUDE_MCP_ENDPOINT_DENIED",
            "CLAUDE_MCP_STDIO_PROFILE_DENIED",
        }
        return McpDiscoveryResult(
            server_id=server.id,
            status=status,
            config_revision=server.config_revision,
            credential_revision=server.credential_revision,
            tools=tuple(inventory.get("tools", ())),
            resources=tuple(inventory.get("resources", ())),
            prompts=tuple(inventory.get("prompts", ())),
            server_info=inventory.get("serverInfo"),
            error=(
                McpDiscoveryError(
                    str(error_code), str(error_code) not in non_retryable
                )
                if error_code
                else None
            ),
            discovered_at=_safe_text(cached.get("discovered_at"), 100) or datetime.now(timezone.utc).isoformat(),
            truncated=bool(inventory.get("truncated", False)),
        )

    async def _discover_and_save(
        self,
        actor_id: str,
        server: McpServerRecord,
        *,
        auth: Any,
        timeout_seconds: float | None = None,
    ) -> McpDiscoveryResult:
        async with self._semaphore:
            try:
                async with asyncio.timeout(
                    timeout_seconds
                    if timeout_seconds is not None
                    else self.policy.server_timeout_seconds
                ):
                    resolved_auth = auth
                    if resolved_auth is None and self.auth_resolver is not None:
                        resolved_auth = await self.auth_resolver.resolve(actor_id, server)
                    result = await self._discover_session(
                        server,
                        resolved_auth,
                        initialize_timeout_seconds=(
                            timeout_seconds if auth is not None else None
                        ),
                    )
            except asyncio.CancelledError:
                raise
            except BaseException as exc:
                logger.warning(
                    "Managed MCP discovery failed safely server_id=%s auth=%s exception_types=%s",
                    server.id,
                    auth is not None,
                    _exception_type_summary(exc),
                )
                result = McpDiscoveryResult(
                    server_id=server.id,
                    status=McpDiscoveryStatus.FAILED,
                    config_revision=server.config_revision,
                    credential_revision=server.credential_revision,
                    tools=(), resources=(), prompts=(), server_info=None,
                    error=_safe_error(exc),
                    discovered_at=datetime.now(timezone.utc).isoformat(),
                )
        try:
            await self.repository.save_discovery_snapshot(
                actor_id,
                server,
                result,
                ttl_seconds=self.policy.cache_ttl_seconds,
            )
        except TypeError:
            # Provider-free repository protocol compatibility; production
            # Postgres repository accepts the explicit policy TTL.
            await self.repository.save_discovery_snapshot(actor_id, server, result)
        return result

    async def _discover_session(
        self,
        server: McpServerRecord,
        auth: Any,
        *,
        initialize_timeout_seconds: float | None = None,
    ) -> McpDiscoveryResult:
        async with self.session_factory.open(
            server,
            auth=auth,
            request_read_timeout_seconds=initialize_timeout_seconds,
        ) as session:
            initialized = await asyncio.wait_for(
                session.initialize(),
                timeout=(
                    initialize_timeout_seconds
                    if initialize_timeout_seconds is not None
                    else self.policy.item_timeout_seconds
                ),
            )
            capabilities = getattr(initialized, "capabilities", None)
            requests: list[tuple[str, Any]] = []
            if getattr(capabilities, "tools", None) is not None:
                requests.append(
                    ("tools", self._collect_pages(session.list_tools, "tools"))
                )
            if getattr(capabilities, "resources", None) is not None:
                requests.append(
                    (
                        "resources",
                        self._collect_pages(session.list_resources, "resources"),
                    )
                )
            if getattr(capabilities, "prompts", None) is not None:
                requests.append(
                    ("prompts", self._collect_pages(session.list_prompts, "prompts"))
                )
            responses = await asyncio.gather(
                *(request for _, request in requests)
            )
        response_by_kind = {
            kind: response for (kind, _), response in zip(requests, responses)
        }
        tools_raw, tools_truncated = response_by_kind.get("tools", ([], False))
        resources_raw, resources_truncated = response_by_kind.get(
            "resources", ([], False)
        )
        prompts_raw, prompts_truncated = response_by_kind.get(
            "prompts", ([], False)
        )
        total = len(tools_raw) + len(resources_raw) + len(prompts_raw)
        remaining = self.policy.max_inventory_items

        tools = []
        for item in tools_raw[:remaining]:
            tools.append(
                {
                    "name": _safe_text(getattr(item, "name", None), self.policy.max_text_length) or "unnamed",
                    "description": _safe_text(getattr(item, "description", None), self.policy.max_text_length),
                    "annotations": _annotations(getattr(item, "annotations", None)),
                }
            )
        remaining -= len(tools)
        resources = []
        for item in resources_raw[:remaining]:
            resources.append(
                {
                    "uri": _safe_text(getattr(item, "uri", None), self.policy.max_text_length),
                    "name": _safe_text(getattr(item, "name", None), self.policy.max_text_length),
                    "description": _safe_text(getattr(item, "description", None), self.policy.max_text_length),
                    "mime_type": _safe_text(getattr(item, "mimeType", None), self.policy.max_text_length),
                }
            )
        remaining -= len(resources)
        prompts = []
        for item in prompts_raw[:remaining]:
            prompts.append(
                {
                    "name": _safe_text(getattr(item, "name", None), self.policy.max_text_length) or "unnamed",
                    "description": _safe_text(getattr(item, "description", None), self.policy.max_text_length),
                    "argument_count": len(getattr(item, "arguments", ()) or ()),
                }
            )
        info = getattr(initialized, "serverInfo", getattr(initialized, "server_info", None))
        server_info = (
            {
                "name": _safe_text(getattr(info, "name", None), self.policy.max_text_length) or "unknown",
                "version": _safe_text(getattr(info, "version", None), self.policy.max_text_length) or "unknown",
            }
            if info is not None
            else None
        )
        return McpDiscoveryResult(
            server_id=server.id,
            status=McpDiscoveryStatus.COMPLETE,
            config_revision=server.config_revision,
            credential_revision=server.credential_revision,
            tools=tuple(tools),
            resources=tuple(resources),
            prompts=tuple(prompts),
            server_info=server_info,
            error=None,
            discovered_at=datetime.now(timezone.utc).isoformat(),
            truncated=(
                tools_truncated
                or resources_truncated
                or prompts_truncated
                or total > self.policy.max_inventory_items
            ),
        )

    async def _collect_pages(
        self,
        list_method: Any,
        result_attribute: str,
    ) -> tuple[list[Any], bool]:
        """Exhaust one standard-MCP list cursor within explicit item/page bounds."""

        items: list[Any] = []
        cursor: str | None = None
        seen_cursors: set[str] = set()
        for _page_number in range(self.policy.max_inventory_pages):
            response = await asyncio.wait_for(
                list_method(cursor=cursor),
                timeout=self.policy.item_timeout_seconds,
            )
            page_items = list(getattr(response, result_attribute, ()) or ())
            remaining = self.policy.max_inventory_items - len(items)
            if len(page_items) > remaining:
                items.extend(page_items[:remaining])
                return items, True
            items.extend(page_items)

            next_cursor = getattr(
                response,
                "nextCursor",
                getattr(response, "next_cursor", None),
            )
            if next_cursor in {None, ""}:
                return items, False
            if not isinstance(next_cursor, str) or next_cursor in seen_cursors:
                raise RuntimeError("invalid MCP pagination cursor")
            if len(items) >= self.policy.max_inventory_items:
                return items, True
            seen_cursors.add(next_cursor)
            cursor = next_cursor
        return items, True


# Legacy import name retained for direct test imports; online Service no longer
# constructs or references the Agent SDK based implementation.
ClaudeMcpInventoryClient = McpDiscoveryCoordinator


__all__ = [
    "ClaudeMcpInventoryClient",
    "McpDiscoveryCoordinator",
    "McpDiscoveryError",
    "McpDiscoveryPolicy",
    "McpDiscoveryResult",
    "McpDiscoveryStatus",
    "McpSdkSessionFactory",
    "McpTransportHttpError",
    "StdioProfile",
    "StdioProfileResolver",
]
