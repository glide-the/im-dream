#!/usr/bin/env python3
"""One-time import of safe legacy Claude MCP server metadata.

[Input] Explicit actor ID and bounded legacy JSON path plus configured PostgreSQL capability.
[Output] Redacted canonical-receipt counts; no credentials, paths, CLI output, or raw config.
[Pos] Offline managed-MCP cutover entrypoint; never used by the online service.
[Sync] 2026-08-25: add idempotent no-overwrite legacy MCP config importer.
[Sync] 2026-08-25: resolve the same Admin-owned PostgreSQL environment contract as the normal Dream server.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import sys

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from claude_mcp.importer import LegacyMcpConfigImporter  # noqa: E402
from claude_mcp.repository import PostgresMcpRepository  # noqa: E402
from persistence.config import load_database_url_from_env_file  # noqa: E402
from persistence.postgres import PostgresPool  # noqa: E402


_DATABASE_URL_WAS_INHERITED = bool(os.environ.get("DATABASE_URL", "").strip())
load_dotenv(BACKEND_DIR / ".env", override=False)
if os.environ.get("INK_LOAD_DATABASE_URL_FROM_ENV_FILE") == "1":
    load_database_url_from_env_file(override=not _DATABASE_URL_WAS_INHERITED)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import non-secret legacy MCP metadata into managed PostgreSQL."
    )
    parser.add_argument("--actor-id", required=True)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--max-bytes", type=int, default=1_048_576)
    return parser.parse_args()


async def _run(arguments: argparse.Namespace) -> dict[str, int]:
    if arguments.max_bytes < 1 or not arguments.actor_id.strip():
        raise SystemExit("invalid importer policy")
    pool = PostgresPool.from_env(application_name="ink-dream-mcp-import")
    pool.open()
    try:
        repository = PostgresMcpRepository(pool)
        if not await repository.capability_available():
            raise SystemExit("managed MCP database capability is unavailable")
        result = await LegacyMcpConfigImporter(
            repository, max_bytes=arguments.max_bytes
        ).import_file(arguments.actor_id.strip(), arguments.config)
        return result.safe_dict()
    finally:
        pool.close()


def main() -> None:
    # The only stdout receipt is a closed integer DTO. Source paths, legacy
    # config, credentials, and database errors never enter output.
    print(json.dumps(asyncio.run(_run(_arguments())), sort_keys=True))


if __name__ == "__main__":
    main()
