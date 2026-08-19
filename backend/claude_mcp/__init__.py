"""Claude MCP resource-connector domain package.

[Input] Authenticated actor identity, user-scoped CLI roots, and Agent thread config homes.
[Output] MCP discovery/OAuth services plus minimal user-to-thread credential projection.
[Pos] Domain boundary between Resources APIs and the official Claude Code MCP argv protocol.
[Sync] 2026-08-19: add the schema-free user credential identity and thread projection boundary.
"""

from .service import ClaudeMcpService

__all__ = ["ClaudeMcpService"]
