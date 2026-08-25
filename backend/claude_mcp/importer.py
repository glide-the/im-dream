"""One-time, redacted import of legacy Claude MCP JSON configuration.

[Input] An explicit bounded JSON path, actor identity, and injected managed-MCP repository.
[Output] Canonical-hash import receipts without overwriting managed rows or exposing secrets.
[Pos] Offline cutover adapter only; the online service never imports or dual-reads CLI files.
[Sync] 2026-08-25: add idempotent managed-MCP legacy configuration import.
[Sync] 2026-08-25: preserve a boolean legacy OAuth intent while rejecting normalized secret-bearing fields.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .contracts import McpAuthKind, McpScope, McpServerCreate, McpTransport


def _canonical_hash(value: object) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class LegacyMcpImportSummary:
    imported: int = 0
    unchanged: int = 0
    conflicts: int = 0
    rejected: int = 0

    def safe_dict(self) -> dict[str, int]:
        return {
            "imported": self.imported,
            "unchanged": self.unchanged,
            "conflicts": self.conflicts,
            "rejected": self.rejected,
        }


class LegacyMcpConfigImporter:
    """Import safe server metadata through repository receipts exactly once."""

    _SECRET_FIELDS = frozenset(
        {
            "apikey",
            "authorization",
            "clientsecret",
            "cookie",
            "env",
            "headers",
            "password",
            "refreshtoken",
            "accesstoken",
            "token",
        }
    )

    def __init__(self, repository: Any, *, max_bytes: int) -> None:
        self._repository = repository
        self._max_bytes = max_bytes

    async def import_file(
        self, actor_id: str, source_path: str | Path
    ) -> LegacyMcpImportSummary:
        path = Path(source_path)
        if path.is_symlink() or not path.is_file():
            return LegacyMcpImportSummary(rejected=1)
        raw = path.read_bytes()
        if len(raw) > self._max_bytes:
            return LegacyMcpImportSummary(rejected=1)
        try:
            document = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return LegacyMcpImportSummary(rejected=1)
        if not isinstance(document, Mapping):
            return LegacyMcpImportSummary(rejected=1)
        servers = document.get("mcpServers", {})
        if not isinstance(servers, Mapping):
            return LegacyMcpImportSummary(rejected=1)

        counters = {"imported": 0, "unchanged": 0, "conflicts": 0, "rejected": 0}
        for key, raw_config in sorted(servers.items(), key=lambda item: str(item[0])):
            source_hash = _canonical_hash({"server_key": key, "config": raw_config})
            receipt = await self._repository.find_import_receipt(actor_id, source_hash)
            if receipt is not None:
                counters["unchanged"] += 1
                continue
            create = self._parse_server(str(key), raw_config)
            if create is None:
                counters["rejected"] += 1
                continue
            config_hash = _canonical_hash(
                {
                    "server_key": create.server_key,
                    "display_name": create.display_name,
                    "transport": create.transport.value,
                    "remote_url": create.remote_url,
                    "auth_kind": create.auth_kind.value,
                    "scope": create.scope.value,
                }
            )
            receipt = await self._repository.import_server(
                actor_id, create, source_hash, config_hash
            )
            state = (
                receipt.get("state")
                if isinstance(receipt, Mapping)
                else getattr(receipt, "state", None)
            )
            if state == "imported":
                counters["imported"] += 1
            elif state == "conflict":
                counters["conflicts"] += 1
            else:
                counters["unchanged"] += 1
        return LegacyMcpImportSummary(**counters)

    def _parse_server(self, key: str, value: object) -> McpServerCreate | None:
        if not isinstance(value, Mapping) or not key.strip():
            return None
        if self._contains_secret_field(value):
            return None
        raw_type = str(value.get("type", "http")).strip().lower()
        transport = {
            "http": McpTransport.STREAMABLE_HTTP,
            "streamable_http": McpTransport.STREAMABLE_HTTP,
            "streamable-http": McpTransport.STREAMABLE_HTTP,
            "sse": McpTransport.SSE,
        }.get(raw_type)
        url = value.get("url")
        oauth_marker = value.get("oauth", False)
        if not isinstance(oauth_marker, bool):
            return None
        if transport is None or not isinstance(url, str):
            # Legacy stdio argv/env cannot cross the browser/server policy boundary.
            return None
        try:
            return McpServerCreate(
                server_key=key.strip(),
                display_name=key.strip(),
                transport=transport,
                auth_kind=(
                    McpAuthKind.OAUTH if oauth_marker else McpAuthKind.NONE
                ),
                scope=McpScope.USER,
                remote_url=url,
            )
        except ValueError:
            return None

    def _contains_secret_field(self, value: object) -> bool:
        if isinstance(value, Mapping):
            for key, item in value.items():
                normalized_key = "".join(
                    character
                    for character in str(key).casefold()
                    if character.isalnum()
                )
                if normalized_key in self._SECRET_FIELDS:
                    return True
                if self._contains_secret_field(item):
                    return True
        elif isinstance(value, (list, tuple)):
            return any(self._contains_secret_field(item) for item in value)
        return False


__all__ = ["LegacyMcpConfigImporter", "LegacyMcpImportSummary"]
