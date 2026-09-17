#!/usr/bin/env python3
"""One-time import of safe legacy Claude MCP server metadata through Admin.

[Input] Bounded legacy JSON path, server-owned Admin config and OAuth access token env.
[Output] Redacted canonical-receipt counts; no credentials, paths, CLI output, or raw config.
[Pos] Offline Admin DTO cutover entrypoint; never opens PostgreSQL or runs DDL.
[Sync] 2026-08-25: add idempotent no-overwrite legacy MCP config importer.
[Sync] 2026-08-25: resolve the same Admin-owned PostgreSQL environment contract as the normal Dream server.
[Sync] 2026-09-16: remove direct PostgreSQL access and derive the actor from Admin principal.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import sys

from dotenv import load_dotenv
from uuid import uuid4


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from claude_mcp.importer import LegacyMcpConfigImporter  # noqa: E402
from claude_mcp.repository import (  # noqa: E402
    AdminManagedMcpRepository,
    McpDataAuthorization,
)
from services.admin_data.client import AdminDataClient  # noqa: E402
from services.admin_data.config import AdminDataConfig  # noqa: E402
from services.admin_data.managed_mcp_data import (  # noqa: E402
    MANAGED_MCP_OPERATIONS,
)


load_dotenv(BACKEND_DIR / ".env", override=False)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import non-secret legacy MCP metadata through the Admin data API."
    )
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--max-bytes", type=int, default=1_048_576)
    return parser.parse_args()


async def _run(arguments: argparse.Namespace) -> dict[str, int]:
    if arguments.max_bytes < 1:
        raise SystemExit("invalid importer policy")
    access_token = os.environ.get("INK_MCP_IMPORT_ACCESS_TOKEN", "").strip()
    if not access_token or any(
        character.isspace() or ord(character) < 32 or ord(character) == 127
        for character in access_token
    ):
        raise SystemExit("INK_MCP_IMPORT_ACCESS_TOKEN is required")
    client = AdminDataClient(
        AdminDataConfig.from_env(),
        operations=MANAGED_MCP_OPERATIONS,
    )
    try:
        client.capabilities(str(uuid4()))
        principal = client.principal(access_token, str(uuid4()))
        if not {"dream:read", "dream:write"} <= set(principal.scopes):
            raise SystemExit("Admin principal lacks managed MCP import scope")
        repository = AdminManagedMcpRepository(client)
        with repository.authorize(
            McpDataAuthorization(
                actor_id=principal.canonical_user_id,
                access_token=access_token,
            )
        ):
            if not await repository.capability_available():
                raise SystemExit("managed MCP Admin capability is unavailable")
            result = await LegacyMcpConfigImporter(
                repository, max_bytes=arguments.max_bytes
            ).import_file(principal.canonical_user_id, arguments.config)
        return result.safe_dict()
    finally:
        client.close()


def main() -> None:
    # The only stdout receipt is a closed integer DTO. Source paths, legacy
    # config, credentials, and database errors never enter output.
    print(json.dumps(asyncio.run(_run(_arguments())), sort_keys=True))


if __name__ == "__main__":
    main()
