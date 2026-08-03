"""Unit tests for services.claude_plugin (shared install/pack pipeline)."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import unittest
from unittest import mock

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from services.claude_plugin.package_spec import PackageSpecError, parse_package_spec
from services.claude_plugin.compatibility import (
    SemVer,
    cli_version_to_semver,
    version_satisfies,
)
from services.claude_plugin.artifact_store import (
    ArtifactStoreError,
    artifact_dir_name,
    get_artifact,
    import_tree,
)
from services.claude_plugin.workspace_packer import (
    WorkspacePackError,
    pack_workspace_plugins,
)
from libs.claude_agent_kit.server.plugin_digest import (
    compute_plugin_digest,
    digest_is_valid,
)


class PackageSpecTests(unittest.TestCase):
    def test_valid_specs(self) -> None:
        spec = parse_package_spec("superpowers@claude-plugins-official")
        self.assertEqual(spec.package_name, "superpowers")
        self.assertEqual(spec.marketplace, "claude-plugins-official")
        self.assertIsNone(spec.requested_version)
        self.assertEqual(spec.install_argv_spec, "superpowers@claude-plugins-official")
        with_version = parse_package_spec("demo@market@1.2.3")
        self.assertEqual(with_version.requested_version, "1.2.3")

    def test_rejects_shell_metacharacters_and_traversal(self) -> None:
        for bad in (
            "x; rm -rf / @market",
            "$(whoami)@market",
            "plugin@market`id`",
            "../etc@market",
            "plugin@mar ket",
            "plugin@market;echo",
            "plugin@/etc/passwd",
            "plugin|ls@market",
            "plugin@mar\tket",
            "a@b@c@d",
            "@market",
            "plugin@",
            "",
            "plugin@market@notsemver",
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(PackageSpecError):
                    parse_package_spec(bad)


class CompatibilityTests(unittest.TestCase):
    def test_semver_ordering(self) -> None:
        self.assertTrue(SemVer.parse("2.0.0") > SemVer.parse("1.9.9"))
        self.assertTrue(SemVer.parse("1.0.0-alpha") < SemVer.parse("1.0.0"))
        self.assertEqual(str(SemVer.parse("v1.2.3")), "1.2.3")

    def test_range_satisfaction(self) -> None:
        self.assertTrue(version_satisfies("2.1.220", ">=1.0.0 <3.0.0"))
        self.assertFalse(version_satisfies("3.0.0", ">=1.0.0 <3.0.0"))
        self.assertFalse(version_satisfies("0.9.0", ">=1.0.0"))
        self.assertTrue(version_satisfies("1.0.0", ">=1.0.0"))

    def test_cli_version_parse(self) -> None:
        self.assertEqual(cli_version_to_semver("2.1.220 (Claude Code)"), "2.1.220")


class DigestTests(unittest.TestCase):
    def test_digest_is_deterministic_and_ignores_volatile_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".claude-plugin").mkdir()
            (root / ".claude-plugin" / "plugin.json").write_text('{"name":"x"}')
            (root / "skills").mkdir()
            (root / "skills" / "a.md").write_text("a")
            first = compute_plugin_digest(root)
            # Volatile runtime markers must not change the digest.
            (root / ".in_use").mkdir()
            (root / ".in_use" / "12345").write_text("pid")
            (root / ".git").mkdir()
            (root / ".git" / "HEAD").write_text("ref")
            self.assertEqual(first, compute_plugin_digest(root))
            self.assertTrue(digest_is_valid(first))
            # Content change flips the digest.
            (root / "skills" / "a.md").write_text("b")
            self.assertNotEqual(first, compute_plugin_digest(root))

    def test_symlink_hashed_as_link_not_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "target.md").write_text("content")
            (root / "link.md").symlink_to("target.md")
            digest = compute_plugin_digest(root)
            self.assertTrue(digest_is_valid(digest))

    def test_platform_metadata_junk_is_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".claude-plugin").mkdir()
            (root / ".claude-plugin" / "plugin.json").write_text('{"name":"x"}')
            (root / "skills").mkdir()
            (root / "skills" / "a.md").write_text("a")
            first = compute_plugin_digest(root)
            # Finder/zip metadata junk must not change the digest.
            (root / ".DS_Store").write_bytes(b"\x00" * 16)
            (root / "._plugin.json").write_bytes(b"\x00" * 8)
            (root / "skills" / ".DS_Store").write_bytes(b"\x00" * 16)
            (root / "skills" / "._a.md").write_bytes(b"\x00" * 8)
            (root / "Thumbs.db").write_bytes(b"\x00" * 8)
            (root / "desktop.ini").write_text("[.ShellClassInfo]")
            (root / "._junk").mkdir()
            (root / "._junk" / "inner.md").write_text("junk")
            self.assertEqual(first, compute_plugin_digest(root))
            # Real content changes still flip the digest.
            (root / "skills" / "a.md").write_text("b")
            self.assertNotEqual(first, compute_plugin_digest(root))


class ArtifactStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._env = mock.patch.dict(
            os.environ,
            {"INK_CLAUDE_PLUGIN_RUNTIME_ROOT": str(Path(self._tmp.name) / "runtime")},
        )
        self._env.start()

    def tearDown(self) -> None:
        self._env.stop()
        self._tmp.cleanup()

    def _make_plugin(self, name: str = "demo") -> Path:
        source = Path(self._tmp.name) / name
        (source / ".claude-plugin").mkdir(parents=True)
        (source / ".claude-plugin" / "plugin.json").write_text(
            json.dumps({"name": name, "version": "1.0.0"})
        )
        (source / "skills" / name).mkdir(parents=True)
        (source / "skills" / name / "SKILL.md").write_text("# skill")
        return source

    def test_import_is_content_addressed_and_read_only(self) -> None:
        source = self._make_plugin()
        artifact = import_tree(source, package_name="demo", marketplace="local-market")
        self.assertTrue(artifact.path.is_dir())
        self.assertEqual(
            artifact.path.name,
            artifact_dir_name("demo", "local-market", artifact.digest),
        )
        self.assertIn("@sha256-", artifact.path.name)
        # Idempotent replay returns the same artifact.
        again = import_tree(source, package_name="demo", marketplace="local-market")
        self.assertEqual(again.path, artifact.path)
        # Read-only: files and dirs have no write bit.
        for item in artifact.path.rglob("*"):
            if item.is_symlink():
                continue
            self.assertFalse(os.access(item, os.W_OK), item)

    def test_escaping_symlink_is_rejected(self) -> None:
        source = self._make_plugin("evil")
        (source / "escape.md").symlink_to("/etc/hostname")
        with self.assertRaises(ArtifactStoreError):
            import_tree(source, package_name="evil", marketplace="local-market")

    def test_get_artifact_reverifies_digest(self) -> None:
        source = self._make_plugin()
        artifact = import_tree(source, package_name="demo", marketplace="local-market")
        fetched = get_artifact("demo", "local-market", artifact.digest)
        self.assertEqual(fetched.digest, artifact.digest)
        with self.assertRaises(ArtifactStoreError):
            get_artifact("demo", "local-market", "sha256:" + "0" * 64)

    def test_import_strips_platform_metadata_junk(self) -> None:
        source = self._make_plugin("junk")
        (source / ".DS_Store").write_bytes(b"\x00" * 16)
        (source / "skills" / "junk" / "._SKILL.md").write_bytes(b"\x00" * 8)
        artifact = import_tree(source, package_name="junk", marketplace="local-market")
        self.assertFalse((artifact.path / ".DS_Store").exists())
        self.assertFalse((artifact.path / "skills" / "junk" / "._SKILL.md").exists())
        self.assertEqual(compute_plugin_digest(artifact.path), artifact.digest)


class WorkspacePackerTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._env = mock.patch.dict(
            os.environ,
            {"INK_CLAUDE_PLUGIN_RUNTIME_ROOT": str(Path(self._tmp.name) / "runtime")},
        )
        self._env.start()
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript(
            """
            CREATE TABLE decks (id TEXT PRIMARY KEY, owner_id TEXT, enabled INTEGER DEFAULT 1);
            CREATE TABLE claude_plugin_installations (
              id TEXT PRIMARY KEY, requested_package_spec TEXT NOT NULL,
              package_name TEXT NOT NULL, marketplace TEXT NOT NULL,
              requested_version TEXT, resolved_version TEXT NOT NULL,
              source_type TEXT NOT NULL, artifact_digest TEXT NOT NULL,
              artifact_path TEXT NOT NULL, claude_cli_version TEXT NOT NULL,
              cli_git_commit_sha TEXT, manifest_json TEXT,
              component_inventory_json TEXT NOT NULL DEFAULT '{}',
              compatibility_json TEXT NOT NULL DEFAULT '{}',
              status TEXT NOT NULL DEFAULT 'ready',
              operation_id TEXT NOT NULL, error_code TEXT, error_summary TEXT,
              file_count INTEGER NOT NULL DEFAULT 0,
              created_at TEXT, updated_at TEXT, installed_at TEXT
            );
            CREATE TABLE deck_claude_plugin_refs (
              deck_id TEXT NOT NULL, plugin_installation_id TEXT NOT NULL,
              package_spec TEXT NOT NULL, resolved_version TEXT NOT NULL,
              artifact_digest TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 1,
              order_index INTEGER NOT NULL DEFAULT 0,
              created_at TEXT, updated_at TEXT,
              PRIMARY KEY (deck_id, plugin_installation_id)
            );
            """
        )
        self.db.execute("INSERT INTO decks (id, owner_id) VALUES ('deck-1', '1')")
        source = Path(self._tmp.name) / "demo-src"
        (source / ".claude-plugin").mkdir(parents=True)
        (source / ".claude-plugin" / "plugin.json").write_text('{"name":"demo","version":"1.0.0"}')
        self.artifact = import_tree(source, package_name="demo", marketplace="m")
        self.db.execute(
            """
            INSERT INTO claude_plugin_installations (
                id, requested_package_spec, package_name, marketplace,
                resolved_version, source_type, artifact_digest, artifact_path,
                claude_cli_version, status, operation_id
            ) VALUES ('cpi-1', 'demo@m', 'demo', 'm', '1.0.0', 'marketplace',
                      ?, ?, '2.1.220', 'ready', 'cop-1')
            """,
            (self.artifact.digest, str(self.artifact.path)),
        )
        self.db.execute(
            """
            INSERT INTO deck_claude_plugin_refs (
                deck_id, plugin_installation_id, package_spec, resolved_version,
                artifact_digest, enabled, order_index
            ) VALUES ('deck-1', 'cpi-1', 'demo@m', '1.0.0', ?, 1, 0)
            """,
            (self.artifact.digest,),
        )
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()
        self._env.stop()
        self._tmp.cleanup()

    def test_pack_writes_manifest_and_receipt(self) -> None:
        workspace = Path(self._tmp.name) / "ws"
        workspace.mkdir()
        receipt = pack_workspace_plugins(self.db, workspace=workspace, deck_id="deck-1")
        self.assertEqual(len(receipt["plugins"]), 1)
        entry = receipt["plugins"][0]
        self.assertEqual(entry["package_spec"], "demo@m")
        self.assertEqual(entry["artifact_digest"], self.artifact.digest)
        manifest = json.loads((workspace / ".ink" / "launch-manifest.json").read_text())
        self.assertEqual(manifest["schema_version"], "claude-launch/v1")
        self.assertEqual(manifest["plugins"][0]["artifact_digest"], self.artifact.digest)
        packed = workspace / entry["relative_path"]
        self.assertTrue((packed / ".claude-plugin" / "plugin.json").is_file())
        # Digest of packed copy matches the pinned digest.
        self.assertEqual(compute_plugin_digest(packed), self.artifact.digest)

    def test_frozen_workspace_is_not_reconfigured(self) -> None:
        workspace = Path(self._tmp.name) / "ws"
        workspace.mkdir()
        pack_workspace_plugins(self.db, workspace=workspace, deck_id="deck-1")
        self.db.execute("UPDATE deck_claude_plugin_refs SET enabled = 0 WHERE deck_id = 'deck-1'")
        self.db.commit()
        receipt = pack_workspace_plugins(self.db, workspace=workspace, deck_id="deck-1")
        self.assertTrue(receipt["frozen"])
        self.assertEqual(len(receipt["plugins"]), 1)

    def test_disabled_ref_means_fresh_workspace_is_not_packed(self) -> None:
        self.db.execute("UPDATE deck_claude_plugin_refs SET enabled = 0 WHERE deck_id = 'deck-1'")
        self.db.commit()
        workspace = Path(self._tmp.name) / "ws2"
        workspace.mkdir()
        receipt = pack_workspace_plugins(self.db, workspace=workspace, deck_id="deck-1")
        self.assertEqual(receipt["plugins"], [])
        self.assertFalse((workspace / ".ink" / "launch-manifest.json").exists())

    def test_not_ready_installation_fails_closed(self) -> None:
        self.db.execute("UPDATE claude_plugin_installations SET status = 'installing'")
        self.db.commit()
        workspace = Path(self._tmp.name) / "ws3"
        workspace.mkdir()
        with self.assertRaises(WorkspacePackError) as caught:
            pack_workspace_plugins(self.db, workspace=workspace, deck_id="deck-1")
        self.assertEqual(caught.exception.code, "CLAUDE_PLUGIN_NOT_READY")

    def test_tampered_packed_copy_is_repaired_from_store(self) -> None:
        workspace = Path(self._tmp.name) / "ws4"
        workspace.mkdir()
        pack_workspace_plugins(self.db, workspace=workspace, deck_id="deck-1")
        manifest = json.loads((workspace / ".ink" / "launch-manifest.json").read_text())
        packed = workspace / manifest["plugins"][0]["relative_path"]
        for item in packed.rglob("*"):
            if not item.is_symlink():
                item.chmod(0o755 if item.is_dir() else 0o644)
        (packed / ".claude-plugin" / "plugin.json").write_text('{"name":"tampered"}')
        receipt = pack_workspace_plugins(self.db, workspace=workspace, deck_id="deck-1")
        self.assertTrue(receipt["frozen"])
        # The mangled copy is a derived cache: it is repaired from the
        # digest-verified artifact store instead of bricking the thread.
        restored = json.loads((packed / ".claude-plugin" / "plugin.json").read_text())
        self.assertEqual(restored["name"], "demo")
        self.assertEqual(compute_plugin_digest(packed), self.artifact.digest)

    def test_finder_junk_in_packed_copy_does_not_break_pack(self) -> None:
        workspace = Path(self._tmp.name) / "ws5"
        workspace.mkdir()
        pack_workspace_plugins(self.db, workspace=workspace, deck_id="deck-1")
        manifest = json.loads((workspace / ".ink" / "launch-manifest.json").read_text())
        packed = workspace / manifest["plugins"][0]["relative_path"]
        for item in packed.rglob("*"):
            if not item.is_symlink():
                item.chmod(0o755 if item.is_dir() else 0o644)
        (packed / ".DS_Store").write_bytes(b"\x00" * 16)
        (packed / ".claude-plugin" / "._plugin.json").write_bytes(b"\x00" * 8)
        receipt = pack_workspace_plugins(self.db, workspace=workspace, deck_id="deck-1")
        self.assertTrue(receipt["frozen"])
        self.assertTrue(receipt["plugins"][0]["verified"])

    def test_flattened_symlink_copy_is_repaired(self) -> None:
        # Simulates a zip/Finder-archive round-trip that turns in-tree
        # symlinks into regular files (observed with macOS zip→unzip).
        source = Path(self._tmp.name) / "link-src"
        (source / ".claude-plugin").mkdir(parents=True)
        (source / ".claude-plugin" / "plugin.json").write_text(
            '{"name":"linkdemo","version":"1.0.0"}'
        )
        (source / "CLAUDE.md").write_text("# guide")
        (source / "AGENTS.md").symlink_to("CLAUDE.md")
        artifact = import_tree(source, package_name="linkdemo", marketplace="m")
        self.db.execute(
            """
            INSERT INTO claude_plugin_installations (
                id, requested_package_spec, package_name, marketplace,
                resolved_version, source_type, artifact_digest, artifact_path,
                claude_cli_version, status, operation_id
            ) VALUES ('cpi-2', 'linkdemo@m', 'linkdemo', 'm', '1.0.0', 'marketplace',
                      ?, ?, '2.1.220', 'ready', 'cop-2')
            """,
            (artifact.digest, str(artifact.path)),
        )
        self.db.execute(
            """
            INSERT INTO deck_claude_plugin_refs (
                deck_id, plugin_installation_id, package_spec, resolved_version,
                artifact_digest, enabled, order_index
            ) VALUES ('deck-1', 'cpi-2', 'linkdemo@m', '1.0.0', ?, 1, 1)
            """,
            (artifact.digest,),
        )
        self.db.commit()
        workspace = Path(self._tmp.name) / "ws7"
        workspace.mkdir()
        pack_workspace_plugins(self.db, workspace=workspace, deck_id="deck-1")
        manifest = json.loads((workspace / ".ink" / "launch-manifest.json").read_text())
        entry = next(p for p in manifest["plugins"] if p["package_spec"] == "linkdemo@m")
        packed = workspace / entry["relative_path"]
        self.assertTrue((packed / "AGENTS.md").is_symlink())
        # Flatten the symlink into a regular file, like zip does.
        target_bytes = (packed / "CLAUDE.md").read_bytes()
        (packed / "AGENTS.md").unlink()
        (packed / "AGENTS.md").write_bytes(target_bytes)
        self.assertNotEqual(compute_plugin_digest(packed), artifact.digest)
        receipt = pack_workspace_plugins(self.db, workspace=workspace, deck_id="deck-1")
        self.assertTrue(receipt["frozen"])
        self.assertTrue((packed / "AGENTS.md").is_symlink())
        self.assertEqual(compute_plugin_digest(packed), artifact.digest)

    def test_mangled_copy_fails_closed_when_store_missing(self) -> None:
        workspace = Path(self._tmp.name) / "ws6"
        workspace.mkdir()
        pack_workspace_plugins(self.db, workspace=workspace, deck_id="deck-1")
        manifest = json.loads((workspace / ".ink" / "launch-manifest.json").read_text())
        packed = workspace / manifest["plugins"][0]["relative_path"]
        for item in packed.rglob("*"):
            if not item.is_symlink():
                item.chmod(0o755 if item.is_dir() else 0o644)
        (packed / ".claude-plugin" / "plugin.json").write_text('{"name":"tampered"}')
        # Remove the pinned artifact so repair from the store is impossible.
        for item in sorted(self.artifact.path.rglob("*")):
            if item.is_dir() and not item.is_symlink():
                item.chmod(0o755)
        self.artifact.path.chmod(0o755)
        shutil.rmtree(self.artifact.path)
        with self.assertRaises(WorkspacePackError) as caught:
            pack_workspace_plugins(self.db, workspace=workspace, deck_id="deck-1")
        self.assertEqual(caught.exception.code, "CLAUDE_PLUGIN_INTEGRITY_FAILED")


if __name__ == "__main__":
    unittest.main()
