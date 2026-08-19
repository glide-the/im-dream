"""Public Agent SDK Claude MCP inventory contracts.

[Input] Fake streaming SDK status responses, exact user runtime identities, and bounded inventory settings.
[Output] Pending convergence, safe tool annotations, payload limits, timeout, and malformed-response evidence.
[Pos] Provider-free inventory adapter coverage; no model prompt, OAuth provider, or MCP tool is invoked.
[Sync] 2026-08-20: cover the public get_mcp_status discovery path used by Resources details.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from claude_mcp.contracts import (
    ClaudeMcpError,
    ClaudeMcpErrorCode,
    ClaudeMcpRuntimeIdentity,
)
from claude_mcp.inventory import ClaudeMcpInventoryClient
from claude_mcp.settings import ClaudeMcpSettings


class _Options:
    def __init__(self, **values) -> None:
        self.values = values


class _Client:
    def __init__(self, responses, *, options) -> None:
        self.responses = list(responses)
        self.options = options
        self.calls = 0
        self.entered = False
        self.exited = False

    async def __aenter__(self):
        self.entered = True
        return self

    async def __aexit__(self, *_args):
        self.exited = True

    async def get_mcp_status(self):
        index = min(self.calls, len(self.responses) - 1)
        self.calls += 1
        response = self.responses[index]
        if isinstance(response, BaseException):
            raise response
        return response


def _settings(**overrides: int) -> ClaudeMcpSettings:
    values = {
        "auth_timeout_seconds": 3,
        "command_timeout_seconds": 3,
        "terminate_grace_seconds": 1,
        "readiness_timeout_seconds": 2,
        "max_capture_bytes": 65536,
        "max_server_name_length": 512,
        "max_redirect_url_length": 8192,
        **overrides,
    }
    return ClaudeMcpSettings(**values)


def _identity(tmp_path: Path) -> ClaudeMcpRuntimeIdentity:
    config = tmp_path / "config"
    work = tmp_path / "work"
    config.mkdir(parents=True)
    work.mkdir(parents=True)
    return ClaudeMcpRuntimeIdentity(
        command=("/bin/sh",),
        config_dir=config.resolve(),
        cwd=work.resolve(),
        env={"PATH": "/usr/bin:/bin"},
        fingerprint="actor-7-inventory",
    )


def _payload(status: str, **extra):
    return {"mcpServers": [{"name": "comfy", "status": status, **extra}]}


def test_pending_converges_and_projects_only_safe_tool_metadata(tmp_path: Path) -> None:
    async def scenario() -> None:
        responses = [
            _payload("pending"),
            _payload(
                "connected",
                scope="dynamic",
                error="must-not-be-returned token=private",
                config={"type": "http", "headers": {"Authorization": "secret"}},
                serverInfo={"name": "Comfy Cloud", "version": "1.2.3"},
                tools=[
                    {
                        "name": "submit_workflow",
                        "description": "Submit\n  one workflow",
                        "annotations": {"destructive": True},
                    },
                    {
                        "name": "get_job_status",
                        "description": "Read job status",
                        "annotations": {"readOnly": True, "openWorld": False},
                    },
                ],
            ),
        ]
        clients = []

        def client_factory(*, options):
            client = _Client(responses, options=options)
            clients.append(client)
            return client

        inventory = await ClaudeMcpInventoryClient(
            _settings(inventory_poll_interval_ms=1),
            sdk_client_factory=client_factory,
            sdk_options_factory=_Options,
        ).inspect(
            identity=_identity(tmp_path),
            server_name="comfy",
            server_config={
                "type": "http",
                "url": "https://cloud.comfy.org/mcp",
                "headers": {"Authorization": "opaque-secret"},
            },
            secure_storage_home="/private/user-store",
        )

        payload = inventory.to_dict()
        assert payload["status"] == "connected"
        assert payload["url"] == "https://cloud.comfy.org/mcp"
        assert payload["tool_count"] == 2
        assert payload["tools"][0] == {
            "name": "submit_workflow",
            "description": "Submit one workflow",
            "annotations": {
                "read_only": None,
                "destructive": True,
                "open_world": None,
            },
        }
        assert payload["capabilities"]["resources"] == {
            "status": "not_reported",
            "count": None,
        }
        assert "secret" not in repr(payload)
        assert "token" not in repr(payload)
        options = clients[0].options.values
        assert options["tools"] == []
        assert options["strict_mcp_config"] is True
        assert options["cli_path"] == "/bin/sh"
        assert options["env"]["CLAUDE_CONFIG_DIR"].endswith("/config")
        assert options["env"]["CLAUDE_SECURESTORAGE_CONFIG_DIR"] == "/private/user-store"
        assert clients[0].calls == 2
        assert clients[0].entered and clients[0].exited

    asyncio.run(scenario())


def test_inventory_truncates_bounded_tool_payload(tmp_path: Path) -> None:
    async def scenario() -> None:
        responses = [_payload(
            "connected",
            tools=[
                {"name": "first", "description": "x" * 20},
                {"name": "second"},
            ],
        )]
        inventory = await ClaudeMcpInventoryClient(
            _settings(
                max_inventory_tools=1,
                max_tool_description_length=8,
            ),
            sdk_client_factory=lambda *, options: _Client(responses, options=options),
            sdk_options_factory=_Options,
        ).inspect(
            identity=_identity(tmp_path),
            server_name="comfy",
            server_config={"type": "http", "url": "https://example.test/mcp"},
            secure_storage_home=None,
        )
        assert inventory.tool_count == 2
        assert inventory.tools_truncated is True
        assert len(inventory.tools) == 1
        assert inventory.tools[0].description == "xxxxxxxx"

    asyncio.run(scenario())


def test_inventory_rejects_malformed_output_and_maps_sdk_failure(tmp_path: Path) -> None:
    async def scenario() -> None:
        for responses, expected in (
            ([{"mcpServers": "invalid"}], ClaudeMcpErrorCode.INVENTORY_MALFORMED),
            ([RuntimeError("token=private")], ClaudeMcpErrorCode.INVENTORY_UNAVAILABLE),
        ):
            client = ClaudeMcpInventoryClient(
                _settings(),
                sdk_client_factory=lambda *, options, values=responses: _Client(values, options=options),
                sdk_options_factory=_Options,
            )
            try:
                await client.inspect(
                    identity=_identity(tmp_path / expected.value),
                    server_name="comfy",
                    server_config={"type": "http", "url": "https://example.test/mcp"},
                    secure_storage_home=None,
                )
            except ClaudeMcpError as exc:
                assert exc.code is expected
                assert "private" not in str(exc)
            else:  # pragma: no cover
                raise AssertionError("unsafe inventory result was accepted")

    asyncio.run(scenario())


def test_inventory_timeout_is_safe_and_closes_client(tmp_path: Path) -> None:
    class _SlowClient(_Client):
        async def get_mcp_status(self):
            await asyncio.sleep(2)
            return _payload("pending")

    async def scenario() -> None:
        clients = []

        def factory(*, options):
            client = _SlowClient([], options=options)
            clients.append(client)
            return client

        try:
            await ClaudeMcpInventoryClient(
                _settings(inventory_timeout_seconds=1),
                sdk_client_factory=factory,
                sdk_options_factory=_Options,
            ).inspect(
                identity=_identity(tmp_path),
                server_name="comfy",
                server_config={"type": "http", "url": "https://example.test/mcp"},
                secure_storage_home=None,
            )
        except ClaudeMcpError as exc:
            assert exc.code is ClaudeMcpErrorCode.INVENTORY_TIMEOUT
        else:  # pragma: no cover
            raise AssertionError("inventory timeout was not enforced")
        assert clients[0].exited is True

    asyncio.run(scenario())


def test_inventory_cancellation_propagates_and_closes_client(tmp_path: Path) -> None:
    async def scenario() -> None:
        entered = asyncio.Event()
        blocked = asyncio.Event()

        class _CancellingClient(_Client):
            async def __aenter__(self):
                await super().__aenter__()
                entered.set()
                return self

            async def get_mcp_status(self):
                await blocked.wait()
                return _payload("pending")

        clients = []

        def factory(*, options):
            client = _CancellingClient([], options=options)
            clients.append(client)
            return client

        task = asyncio.create_task(
            ClaudeMcpInventoryClient(
                _settings(inventory_timeout_seconds=2),
                sdk_client_factory=factory,
                sdk_options_factory=_Options,
            ).inspect(
                identity=_identity(tmp_path),
                server_name="comfy",
                server_config={"type": "http", "url": "https://example.test/mcp"},
                secure_storage_home=None,
            )
        )
        await entered.wait()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        else:  # pragma: no cover
            raise AssertionError("inventory cancellation was not propagated")
        assert clients[0].exited is True

    asyncio.run(scenario())
