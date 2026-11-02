# [Input] Original Runner private MCP projection, fixed internal server factories and one Runtime endpoint.
# [Output] Existing owned MCP handlers on the original SDK's in-memory transport with per-server broker values.
# [Pos] iOS stdio compatibility adapter; remote MCP configuration and tool permissions retain their owners.
from __future__ import annotations

from dataclasses import replace
from contextlib import contextmanager
import json
import os
from pathlib import Path
import stat

import anyio
from mcp import types as mcp_types


@contextmanager
def adapt_owned_mcp(options, *, workspace_root: str):
    """Bind SDK instances and a pinned private projection for one SDK connection."""
    source = options.mcp_servers
    if not isinstance(source, (str, Path)):
        yield options
        return
    path = Path(source)
    metadata = path.lstat()
    if (not stat.S_ISREG(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o600
            or metadata.st_size > 16 * 1024 * 1024 or path.is_symlink()
            or not path.resolve(strict=True).is_relative_to(Path(workspace_root).resolve(strict=True))):
        raise ValueError("IOS_MCP_PROJECTION_INVALID")
    descriptor = os.open(path, os.O_RDWR | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "r+", encoding="utf-8") as projection:
        current = os.fstat(projection.fileno())
        if (current.st_dev, current.st_ino) != (metadata.st_dev, metadata.st_ino):
            raise ValueError("IOS_MCP_PROJECTION_INVALID")
        original = projection.read(16 * 1024 * 1024 + 1)
        if len(original.encode()) > 16 * 1024 * 1024:
            raise ValueError("IOS_MCP_PROJECTION_INVALID")
        document = json.loads(original)
        configs = document["mcpServers"]
        if not isinstance(configs, dict):
            raise ValueError("IOS_MCP_PROJECTION_INVALID")
        servers = _adapt_configs(configs)
        if not servers:
            yield options
            return
        def write(value):
            projection.seek(0)
            projection.write(value)
            projection.truncate()
            projection.flush()
            os.fsync(projection.fileno())
        try:
            write(json.dumps(document, ensure_ascii=False, separators=(",", ":")))
            options.mcp_servers = servers
            yield replace(options, mcp_servers=path)
        finally:
            options.mcp_servers = source
            write(original)


def _adapt_configs(configs):
    from libs.claude_agent_kit.server import agent_runner
    from libs.claude_agent_kit.server.mcp_server import create_user_mcp_server
    from libs.claude_agent_kit.server.editor_mcp_server import create_editor_mcp_server
    from libs.claude_agent_kit.server.story_workspace_mcp_server import story_workspace_create_mcp_server
    from libs.claude_agent_kit.server.image_gen_stdio import create_image_gen_server

    factories = {
        "user": (create_user_mcp_server, agent_runner._user_mcp_stdio_config),
        "editor": (create_editor_mcp_server, agent_runner._editor_mcp_stdio_config),
        "story_workspace": (story_workspace_create_mcp_server, agent_runner._story_workspace_mcp_stdio_config),
        "image_gen": (create_image_gen_server, lambda env: agent_runner._user_mcp_stdio_config(
            env, module_name="libs.claude_agent_kit.server.image_gen_stdio")),
    }
    servers = {}
    for name, config in configs.items():
        if not isinstance(config, dict):
            raise ValueError("IOS_MCP_PROJECTION_INVALID")
        if name not in factories or config.get("type", "stdio") != "stdio":
            continue
        environment = config.get("env")
        if not isinstance(environment, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in environment.items()):
            raise ValueError("IOS_MCP_PROJECTION_INVALID")
        factory, expected = factories[name]
        definition = expected(environment)
        if any(config.get(key) != definition.get(key) for key in ("type", "command", "args")):
            raise ValueError("IOS_MCP_ENTRYPOINT_INVALID")
        server = factory(environment=dict(environment))
        # Existing handlers can perform synchronous broker I/O. Run them away
        # from the SDK control loop while preserving MCP request ContextVars.
        handler = server.request_handlers[mcp_types.CallToolRequest]

        async def dispatch(request, *, original=handler):
            async def invoke():
                return await original(request)
            return await anyio.to_thread.run_sync(lambda: anyio.run(invoke), abandon_on_cancel=True)

        server.request_handlers[mcp_types.CallToolRequest] = dispatch
        servers[name] = {"type": "sdk", "name": name, "instance": server}
        configs[name] = {"type": "sdk", "name": name}
    return servers
