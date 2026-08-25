"""Explicit legacy Claude MCP config importer contracts.

[Input] Temporary bounded `.claude.json` fixtures and an injected receipt repository.
[Output] Canonical hash idempotency, no-overwrite conflict, and redacted summary evidence.
[Pos] One-time importer tests; never invokes the online service, CLI, OAuth, or PostgreSQL.
[Sync] 2026-08-25: define the managed MCP cutover import boundary.
[Sync] 2026-08-25: preserve boolean OAuth intent and reject normalized credential aliases.
"""

from __future__ import annotations

import asyncio
import json

from claude_mcp.importer import LegacyMcpConfigImporter


class _Repository:
    def __init__(self):
        self.receipts = {}
        self.existing = {}
        self.imported = []

    async def find_import_receipt(self, actor_id, source_hash):
        return self.receipts.get((actor_id, source_hash))

    async def get_server(self, actor_id, key, workspace_id=None):
        return self.existing.get((actor_id, key))

    async def import_server(self, actor_id, create, source_hash, config_hash):
        if (actor_id, create.server_key) in self.existing:
            receipt = {"state": "conflict", "target_server_id": None}
        else:
            self.imported.append((actor_id, create, source_hash, config_hash))
            receipt = {"state": "imported", "target_server_id": f"server-{len(self.imported)}"}
        self.receipts[(actor_id, source_hash)] = receipt
        return receipt


def _write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_repeated_import_is_idempotent_and_summary_is_redacted(tmp_path):
    async def scenario():
        source = tmp_path / ".claude.json"
        _write(source, {"mcpServers": {"alpha": {"type": "http", "url": "https://mcp.example.test/mcp"}}})
        repository = _Repository()
        importer = LegacyMcpConfigImporter(repository, max_bytes=4096)
        first = await importer.import_file("7", source)
        second = await importer.import_file("7", source)
        assert first.imported == 1 and second.unchanged == 1
        assert len(repository.imported) == 1
        assert str(source) not in repr(first.safe_dict())

    asyncio.run(scenario())


def test_existing_managed_server_is_never_overwritten_and_conflict_receipt_is_durable(tmp_path):
    async def scenario():
        source = tmp_path / ".claude.json"
        _write(source, {"mcpServers": {"alpha": {"type": "sse", "url": "https://mcp.example.test/sse"}}})
        repository = _Repository()
        repository.existing[("7", "alpha")] = object()
        importer = LegacyMcpConfigImporter(repository, max_bytes=4096)
        result = await importer.import_file("7", source)
        repeated = await importer.import_file("7", source)
        assert result.conflicts == 1 and repository.imported == []
        assert repeated.unchanged == 1

    asyncio.run(scenario())


def test_secret_bearing_legacy_fields_are_rejected_without_output(tmp_path):
    async def scenario():
        source = tmp_path / ".claude.json"
        secret = "Bearer must-not-leak"
        _write(source, {"mcpServers": {"alpha": {"type": "http", "url": "https://mcp.example.test/mcp", "headers": {"Authorization": secret}}}})
        result = await LegacyMcpConfigImporter(_Repository(), max_bytes=4096).import_file("7", source)
        assert result.rejected == 1
        assert secret not in repr(result.safe_dict()) and secret not in repr(result)

    asyncio.run(scenario())


def test_nested_unknown_oauth_secret_fields_fail_closed(tmp_path):
    async def scenario():
        source = tmp_path / ".claude.json"
        secret = "nested-must-not-leak"
        _write(source, {"mcpServers": {"alpha": {
            "type": "http",
            "url": "https://mcp.example.test/mcp",
            "extensions": [{"oauth": {"client_secret": secret}}],
        }}})
        repository = _Repository()
        result = await LegacyMcpConfigImporter(
            repository, max_bytes=4096
        ).import_file("7", source)
        assert result.rejected == 1 and repository.imported == []
        assert secret not in repr(result)

    asyncio.run(scenario())


def test_boolean_oauth_intent_is_preserved_without_importing_credentials(tmp_path):
    async def scenario():
        source = tmp_path / ".claude.json"
        _write(source, {"mcpServers": {"cloud": {
            "type": "streamable-http",
            "url": "https://mcp.example.test/mcp",
            "oauth": True,
        }}})
        repository = _Repository()
        result = await LegacyMcpConfigImporter(
            repository, max_bytes=4096
        ).import_file("7", source)
        assert result.imported == 1
        assert repository.imported
        imported = repository.imported[0]
        receipt = next(iter(repository.receipts.values()))
        assert imported[1].server_key == "cloud"
        assert imported[1].auth_kind.value == "oauth"
        assert receipt["state"] == "imported"

    asyncio.run(scenario())


def test_credential_aliases_and_structured_oauth_marker_fail_closed(tmp_path):
    async def scenario():
        repository = _Repository()
        importer = LegacyMcpConfigImporter(repository, max_bytes=4096)
        for index, config in enumerate((
            {"oauth": {"accessToken": "must-not-import"}},
            {"refresh-token": "must-not-import"},
            {"apiKey": "must-not-import"},
        )):
            source = tmp_path / f"legacy-{index}.json"
            _write(source, {"mcpServers": {"cloud": {
                "type": "http",
                "url": "https://mcp.example.test/mcp",
                **config,
            }}})
            result = await importer.import_file("7", source)
            assert result.rejected == 1
        assert repository.imported == []

    asyncio.run(scenario())
