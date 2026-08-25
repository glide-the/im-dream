"""Database-managed Claude MCP resource package.

[Input] Actor/workspace identities, Admin schema capability, and injected protocol/secret policy.
[Output] Managed service plus shared Runtime snapshot-loader lifecycle accessors.
[Pos] Package boundary for PostgreSQL-managed MCP; online paths contain no CLI dependency.
[Sync] 2026-08-25: export managed service and process-singleton integration seams.
"""

from .service import (
    ClaudeMcpService,
    get_default_claude_mcp_service,
    get_default_managed_mcp_runtime_snapshot_loader,
)

__all__ = [
    "ClaudeMcpService",
    "get_default_claude_mcp_service",
    "get_default_managed_mcp_runtime_snapshot_loader",
]
