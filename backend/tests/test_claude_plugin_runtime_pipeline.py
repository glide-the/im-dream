"""Installed CLI → shared artifact → Deck workspace → SDK launch regression.

[Input] Explicit INK_PLUGIN_TEST_CLI, local Marketplace, named SQLite fixture.
[Output] Actual CLI install and production pack/launch evidence without a model.
[Pos] Opt-in provider-free runtime integration; not PostgreSQL user acceptance.
[Sync] 2026-09-15: cover the whole install-to-launch pipeline with no CLI mocks.
"""
import json
import os
from pathlib import Path
import sqlite3

import pytest
from backend.schema import legacy_main_sqlite
from services.claude_plugin import install_service, runtime
from services.claude_plugin.install_service import PluginInstallService
from services.claude_plugin.workspace_packer import pack_workspace_plugins
from libs.claude_agent_kit.server.plugin_launcher import apply_plugin_launch_options


@pytest.mark.skipif(not os.environ.get("INK_PLUGIN_TEST_CLI"), reason="set INK_PLUGIN_TEST_CLI to an explicit built Runtime fixture")
def test_real_install_artifact_deck_pack_and_launch(tmp_path, monkeypatch):
    executable = Path(os.environ["INK_PLUGIN_TEST_CLI"])
    assert executable.is_absolute() and executable.is_file() and os.access(executable, os.X_OK)
    home = tmp_path / "home"
    home.mkdir(mode=0o700)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("INK_CLAUDE_CLI_PATH", str(executable))
    monkeypatch.setenv("INK_CLAUDE_PLUGIN_RUNTIME_ROOT", str(tmp_path / "runtime"))
    scratch = runtime.get_install_workspace() / ".claude-tmp"
    scratch.mkdir(mode=0o700)
    monkeypatch.setenv("CLAUDE_CODE_TMPDIR", str(scratch))
    monkeypatch.setenv("CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC", "1")
    monkeypatch.setenv("DISABLE_AUTOUPDATER", "1")
    for key in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "NOTION_API_TOKEN", "NOTION_HOME", "NOTION_WORKERS_CONFIG_FILE", "NOTION_KEYRING"):
        monkeypatch.delenv(key, raising=False)

    marketplace = tmp_path / "marketplace"
    plugin = marketplace / "pipeline-plugin"
    (plugin / ".claude-plugin").mkdir(parents=True)
    (plugin / ".claude-plugin" / "plugin.json").write_text(json.dumps({"name": "pipeline-plugin", "version": "1.0.0"}))
    skill = plugin / "skills" / "pipeline-skill" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: pipeline-skill\ndescription: Pipeline fixture.\n---\nReturn pipeline-ok.\n")
    (marketplace / ".claude-plugin").mkdir()
    (marketplace / ".claude-plugin" / "marketplace.json").write_text(json.dumps({
        "name": "pipeline-marketplace", "owner": {"name": "Pipeline fixture"},
        "plugins": [{"name": "pipeline-plugin", "source": "./pipeline-plugin"}],
    }))
    # Source injection belongs only to this fixture, not the production catalog.
    monkeypatch.setattr(install_service, "resolve_local_marketplace", lambda name: marketplace if name == "pipeline-marketplace" else None)
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    try:
        db.execute("CREATE TABLE decks (id TEXT PRIMARY KEY, owner_id TEXT, enabled INTEGER DEFAULT 1)")
        db.execute("INSERT INTO decks VALUES ('selected', 'fixture', 1), ('empty', 'fixture', 1)")
        legacy_main_sqlite.create_claude_plugin_tables(db)
        service = PluginInstallService(db)
        spec = "pipeline-plugin@pipeline-marketplace"
        operation = service.install(spec)
        assert operation["status"] == "ready" and operation["exit_code"] == 0
        installation = service.get_installation(operation["installation_id"])
        assert installation["status"] == "ready"
        artifact = Path(installation["artifact_path"])
        artifact.relative_to(runtime.get_artifacts_root())
        assert (artifact / "skills" / "pipeline-skill" / "SKILL.md").is_file()
        assert json.loads(operation["argv_json"])[1:] == ["plugin", "install", spec]
        assert service.install(spec)["installation_id"] == installation["id"]
        db.execute("INSERT INTO deck_claude_plugin_refs (deck_id, plugin_installation_id, package_spec, resolved_version, artifact_digest, enabled, order_index) VALUES ('selected', %s, %s, %s, %s, 1, 0)",
                   (installation["id"], spec, installation["resolved_version"], installation["artifact_digest"]))
        db.commit()
        selected = tmp_path / "selected-workspace"
        empty = tmp_path / "empty-workspace"
        selected.mkdir()
        empty.mkdir()
        packed = pack_workspace_plugins(db, workspace=selected, deck_id="selected")
        assert len(packed["plugins"]) == 1 and packed["plugins"][0]["verified"]
        packed_path = selected / packed["plugins"][0]["relative_path"]
        assert (packed_path / "skills" / "pipeline-skill" / "SKILL.md").read_text() == skill.read_text()
        assert pack_workspace_plugins(db, workspace=empty, deck_id="empty")["plugins"] == []
        class Options:
            plugins = None
        options = Options()
        apply_plugin_launch_options(options, selected)
        assert options.plugins == [{"type": "local", "path": str(packed_path.resolve())}]
        service.uninstall(installation["id"])
        fresh = tmp_path / "fresh-workspace"
        fresh.mkdir()
        assert pack_workspace_plugins(db, workspace=fresh, deck_id="selected")["plugins"] == []
        assert pack_workspace_plugins(db, workspace=selected, deck_id="selected")["frozen"]
    finally:
        db.close()
