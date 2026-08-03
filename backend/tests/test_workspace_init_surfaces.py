"""Unit tests for workspace-init ``surfaces[]`` validation and .dream materialization.

Design: docs/design/story-workspace/design_004_story-workspace-dream-surface-execution-page.md §3
Plan:   docs/design/story-workspace/2026-08-03-dream-surface-execution-implementation-plan.md Task 1
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest import mock

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from services.claude_plugin.artifact_store import import_tree
from services.claude_plugin.workspace_init import (
    WorkspaceInitError,
    load_init_profile,
    materialize_dream_surface,
    validate_surfaces,
)
from services.claude_plugin.workspace_packer import (
    WorkspacePackError,
    pack_workspace_plugins,
)

REPO_ROOT = BACKEND_ROOT.parent


class ValidateSurfacesTests(unittest.TestCase):
    def test_validate_surfaces_accepts_dream(self) -> None:
        specs = validate_surfaces(
            [
                {
                    "name": "dream",
                    "protocol_dir": ".dream",
                    "entry_route": "/story-workspace/dream",
                }
            ]
        )
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0].name, "dream")
        self.assertEqual(specs[0].protocol_dir, ".dream")
        self.assertEqual(specs[0].entry_route, "/story-workspace/dream")

    def test_validate_surfaces_rejects_invalid(self) -> None:
        bad_cases = [
            # unknown name
            {"name": "evil", "protocol_dir": ".evil", "entry_route": "/story-workspace/x"},
            # reserved directory .ink
            {"name": "dream", "protocol_dir": ".ink", "entry_route": "/story-workspace/dream"},
            # reserved directory .editor
            {"name": "dream", "protocol_dir": ".editor", "entry_route": "/story-workspace/dream"},
            # missing dot prefix
            {"name": "dream", "protocol_dir": "dream", "entry_route": "/story-workspace/dream"},
            # out-of-domain entry route
            {"name": "dream", "protocol_dir": ".dream", "entry_route": "/other/route"},
            # multi-level protocol dir
            {"name": "dream", "protocol_dir": ".a/b", "entry_route": "/story-workspace/dream"},
        ]
        for bad in bad_cases:
            with self.subTest(bad=bad):
                with self.assertRaises(WorkspaceInitError) as caught:
                    validate_surfaces([bad])
                self.assertEqual(
                    caught.exception.code, "CLAUDE_PLUGIN_INIT_PROFILE_INVALID"
                )

    def test_validate_surfaces_rejects_non_dict_entry(self) -> None:
        with self.assertRaises(WorkspaceInitError) as caught:
            validate_surfaces(["dream"])
        self.assertEqual(caught.exception.code, "CLAUDE_PLUGIN_INIT_PROFILE_INVALID")

    def test_validate_surfaces_rejects_duplicates(self) -> None:
        dream = {
            "name": "dream",
            "protocol_dir": ".dream",
            "entry_route": "/story-workspace/dream",
        }
        with self.assertRaises(WorkspaceInitError) as caught:
            validate_surfaces([dream, dict(dream)])
        self.assertEqual(caught.exception.code, "CLAUDE_PLUGIN_INIT_PROFILE_INVALID")
        # Same surface name under a different protocol dir is still a
        # duplicate (design_004 §3.1 uniqueness: name and protocol_dir).
        with self.assertRaises(WorkspaceInitError):
            validate_surfaces([dream, {**dream, "protocol_dir": ".dream2"}])

    def test_validate_surfaces_empty_is_ok(self) -> None:
        self.assertEqual(validate_surfaces([]), [])

    def test_load_init_profile_parses_surfaces(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            packed = Path(tmp)
            (packed / ".ink").mkdir()
            (packed / ".ink" / "workspace-init.json").write_text(
                json.dumps(
                    {
                        "schema_version": "workspace-init/v1",
                        "surfaces": [
                            {
                                "name": "dream",
                                "protocol_dir": ".dream",
                                "entry_route": "/story-workspace/dream",
                            }
                        ],
                    }
                )
            )
            profile = load_init_profile(packed)
        self.assertIsNotNone(profile)
        self.assertEqual(len(profile.surfaces), 1)
        self.assertEqual(profile.surfaces[0].name, "dream")

    def test_load_init_profile_without_surfaces_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            packed = Path(tmp)
            (packed / ".ink").mkdir()
            (packed / ".ink" / "workspace-init.json").write_text(
                json.dumps(
                    {"schema_version": "workspace-init/v1", "runtime_dirs": ["stories"]}
                )
            )
            profile = load_init_profile(packed)
        self.assertIsNotNone(profile)
        self.assertEqual(profile.surfaces, ())
        self.assertEqual(profile.runtime_dirs, ("stories",))

    def test_load_init_profile_rejects_invalid_surfaces(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            packed = Path(tmp)
            (packed / ".ink").mkdir()
            (packed / ".ink" / "workspace-init.json").write_text(
                json.dumps(
                    {
                        "schema_version": "workspace-init/v1",
                        "surfaces": [
                            {
                                "name": "evil",
                                "protocol_dir": ".evil",
                                "entry_route": "/story-workspace/x",
                            }
                        ],
                    }
                )
            )
            with self.assertRaises(WorkspaceInitError) as caught:
                load_init_profile(packed)
        self.assertEqual(caught.exception.code, "CLAUDE_PLUGIN_INIT_PROFILE_INVALID")

    def test_load_init_profile_rejects_non_list_surfaces(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            packed = Path(tmp)
            (packed / ".ink").mkdir()
            (packed / ".ink" / "workspace-init.json").write_text(
                json.dumps(
                    {"schema_version": "workspace-init/v1", "surfaces": {"name": "dream"}}
                )
            )
            with self.assertRaises(WorkspaceInitError) as caught:
                load_init_profile(packed)
        self.assertEqual(caught.exception.code, "CLAUDE_PLUGIN_INIT_PROFILE_INVALID")


class MaterializeDreamSurfaceTests(unittest.TestCase):
    PLUGINS = [
        {
            "package_spec": "drama-forge@drama-studio",
            "artifact_digest": "sha256:ee54",
            "resolved_version": "1.0.1",
        }
    ]

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.workspace = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_materialize_dream_surface_writes_static_files(self) -> None:
        step = materialize_dream_surface(
            self.workspace, "deck-1", self.PLUGINS, "/story-workspace/dream"
        )
        ws = json.loads((self.workspace / ".dream" / "workspace.json").read_text())
        self.assertEqual(
            ws,
            {
                "schema_version": "dream-surface/v1",
                "deck_id": "deck-1",
                "plugins": self.PLUGINS,
                "entry_route": "/story-workspace/dream",
            },
        )
        readme = (self.workspace / ".dream" / "README.md").read_text()
        self.assertIn("只读", readme)
        self.assertIn("workflow_run_id", readme)  # boundary declaration
        self.assertEqual(step["step"], "materialize-surface")
        self.assertEqual(step["surface"], "dream")

    def test_materialize_is_byte_identical_on_repack(self) -> None:
        materialize_dream_surface(
            self.workspace, "deck-1", self.PLUGINS, "/story-workspace/dream"
        )
        first = (self.workspace / ".dream" / "workspace.json").read_bytes()
        materialize_dream_surface(
            self.workspace, "deck-1", self.PLUGINS, "/story-workspace/dream"
        )
        self.assertEqual(
            (self.workspace / ".dream" / "workspace.json").read_bytes(), first
        )
        self.assertNotIn("workflow_run_id", json.loads(first))  # no run-level facts

    def test_materialize_no_timestamps_anywhere(self) -> None:
        materialize_dream_surface(
            self.workspace, "deck-1", self.PLUGINS, "/story-workspace/dream"
        )
        readme_bytes = (self.workspace / ".dream" / "README.md").read_bytes()
        first = (self.workspace / ".dream" / "workspace.json").read_bytes()
        materialize_dream_surface(
            self.workspace, "deck-1", self.PLUGINS, "/story-workspace/dream"
        )
        self.assertEqual(
            (self.workspace / ".dream" / "README.md").read_bytes(), readme_bytes
        )
        self.assertEqual(
            (self.workspace / ".dream" / "workspace.json").read_bytes(), first
        )


def _write_surface_plugin(root: Path, *, with_surfaces: bool = True) -> Path:
    """Minimal plugin artifact source with a surfaces-only init profile."""
    (root / ".claude-plugin").mkdir(parents=True)
    (root / ".claude-plugin" / "plugin.json").write_text('{"name":"surf"}')
    (root / ".ink").mkdir()
    profile: dict = {"schema_version": "workspace-init/v1"}
    if with_surfaces:
        profile["surfaces"] = [
            {
                "name": "dream",
                "protocol_dir": ".dream",
                "entry_route": "/story-workspace/dream",
            }
        ]
    (root / ".ink" / "workspace-init.json").write_text(json.dumps(profile))
    return root


class PackerSurfacesIntegrationTests(unittest.TestCase):
    """pack_workspace_plugins: .dream materialization + manifest/receipt surfaces."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._env = mock.patch.dict(
            os.environ,
            {"INK_CLAUDE_PLUGIN_RUNTIME_ROOT": str(Path(self._tmp.name) / "runtime")},
        )
        self._env.start()
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.executescript(
            """
            CREATE TABLE claude_plugin_installations (
              id TEXT PRIMARY KEY, requested_package_spec TEXT NOT NULL,
              package_name TEXT NOT NULL, marketplace TEXT NOT NULL,
              resolved_version TEXT NOT NULL, source_type TEXT NOT NULL,
              artifact_digest TEXT NOT NULL, artifact_path TEXT NOT NULL,
              claude_cli_version TEXT NOT NULL,
              compatibility_json TEXT NOT NULL DEFAULT '{}',
              status TEXT NOT NULL DEFAULT 'ready', operation_id TEXT NOT NULL,
              file_count INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE deck_claude_plugin_refs (
              deck_id TEXT NOT NULL, plugin_installation_id TEXT NOT NULL,
              package_spec TEXT NOT NULL, resolved_version TEXT NOT NULL,
              artifact_digest TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 1,
              order_index INTEGER NOT NULL DEFAULT 0, created_at TEXT,
              PRIMARY KEY (deck_id, plugin_installation_id)
            );
            """
        )
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()
        self._env.stop()
        self._tmp.cleanup()

    def _register_plugin(
        self,
        deck_id: str,
        installation_id: str,
        *,
        with_surfaces: bool = True,
        order_index: int = 0,
    ):
        source = _write_surface_plugin(
            Path(self._tmp.name) / f"src-{installation_id}",
            with_surfaces=with_surfaces,
        )
        artifact = import_tree(source, package_name="surf", marketplace="ds")
        self.db.execute(
            """
            INSERT INTO claude_plugin_installations (
                id, requested_package_spec, package_name, marketplace,
                resolved_version, source_type, artifact_digest, artifact_path,
                claude_cli_version, status, operation_id
            ) VALUES (?, 'surf@ds', 'surf', 'ds', '1.0.0', 'marketplace',
                      ?, ?, '2.1.220', 'ready', ?)
            """,
            (installation_id, artifact.digest, str(artifact.path), f"op-{installation_id}"),
        )
        self.db.execute(
            """
            INSERT INTO deck_claude_plugin_refs (
                deck_id, plugin_installation_id, package_spec, resolved_version,
                artifact_digest, enabled, order_index
            ) VALUES (?, ?, 'surf@ds', '1.0.0', ?, 1, ?)
            """,
            (deck_id, installation_id, artifact.digest, order_index),
        )
        self.db.commit()
        return artifact

    def test_pack_materializes_dream_and_exposes_surfaces(self) -> None:
        artifact = self._register_plugin("deck-1", "cpi-1")
        workspace = Path(self._tmp.name) / "ws"
        workspace.mkdir()
        receipt = pack_workspace_plugins(self.db, workspace=workspace, deck_id="deck-1")

        # 1. .dream/ materialized with both files.
        dream = workspace / ".dream"
        self.assertTrue((dream / "README.md").is_file())
        ws = json.loads((dream / "workspace.json").read_text())
        self.assertEqual(ws["schema_version"], "dream-surface/v1")
        self.assertEqual(ws["deck_id"], "deck-1")
        self.assertEqual(ws["entry_route"], "/story-workspace/dream")
        self.assertEqual(
            ws["plugins"],
            [
                {
                    "package_spec": "surf@ds",
                    "artifact_digest": artifact.digest,
                    "resolved_version": "1.0.0",
                }
            ],
        )
        self.assertNotIn("workflow_run_id", ws)

        # 2. Manifest and receipt expose surfaces.
        manifest = json.loads(
            (workspace / ".ink" / "launch-manifest.json").read_text()
        )
        expected_surfaces = [
            {
                "name": "dream",
                "protocol_dir": ".dream",
                "entry_route": "/story-workspace/dream",
            }
        ]
        self.assertEqual(manifest["surfaces"], expected_surfaces)
        self.assertEqual(receipt["surfaces"], expected_surfaces)
        receipt_file = json.loads(
            (workspace / ".ink" / "plugin-pack-receipt.json").read_text()
        )
        self.assertEqual(receipt_file["surfaces"], expected_surfaces)
        self.assertTrue(
            any(
                step.get("step") == "materialize-surface"
                for step in receipt["init_steps"]
            )
        )

    def test_pack_without_surfaces_is_diff_empty(self) -> None:
        self._register_plugin("deck-1", "cpi-1", with_surfaces=False)
        workspace = Path(self._tmp.name) / "ws"
        workspace.mkdir()
        receipt = pack_workspace_plugins(self.db, workspace=workspace, deck_id="deck-1")
        self.assertFalse((workspace / ".dream").exists())
        manifest = json.loads(
            (workspace / ".ink" / "launch-manifest.json").read_text()
        )
        self.assertNotIn("surfaces", manifest)
        self.assertNotIn("surfaces", receipt)
        receipt_file = json.loads(
            (workspace / ".ink" / "plugin-pack-receipt.json").read_text()
        )
        self.assertNotIn("surfaces", receipt_file)

    def test_frozen_workspace_repack_keeps_surfaces_and_dream(self) -> None:
        self._register_plugin("deck-1", "cpi-1")
        workspace = Path(self._tmp.name) / "ws"
        workspace.mkdir()
        first = pack_workspace_plugins(self.db, workspace=workspace, deck_id="deck-1")
        first_dream = (workspace / ".dream" / "workspace.json").read_bytes()
        first_readme = (workspace / ".dream" / "README.md").read_bytes()

        second = pack_workspace_plugins(self.db, workspace=workspace, deck_id="deck-1")
        self.assertTrue(second["frozen"])
        self.assertEqual(second["surfaces"], first["surfaces"])
        # Frozen re-pack never rebuilds .dream/; bytes stay identical.
        self.assertEqual(
            (workspace / ".dream" / "workspace.json").read_bytes(), first_dream
        )
        self.assertEqual((workspace / ".dream" / "README.md").read_bytes(), first_readme)

    def test_frozen_workspace_missing_dream_fails_closed(self) -> None:
        self._register_plugin("deck-1", "cpi-1")
        workspace = Path(self._tmp.name) / "ws"
        workspace.mkdir()
        pack_workspace_plugins(self.db, workspace=workspace, deck_id="deck-1")
        (workspace / ".dream" / "workspace.json").unlink()
        with self.assertRaises(WorkspacePackError) as caught:
            pack_workspace_plugins(self.db, workspace=workspace, deck_id="deck-1")
        self.assertEqual(caught.exception.code, "CLAUDE_PLUGIN_INIT_PROFILE_INVALID")

    def test_multi_plugin_same_surface_first_wins_with_warning(self) -> None:
        self._register_plugin("deck-1", "cpi-1", order_index=0)
        self._register_plugin("deck-1", "cpi-2", order_index=1)
        workspace = Path(self._tmp.name) / "ws"
        workspace.mkdir()
        receipt = pack_workspace_plugins(self.db, workspace=workspace, deck_id="deck-1")
        self.assertEqual(len(receipt["surfaces"]), 1)
        self.assertEqual(receipt["surfaces"][0]["name"], "dream")
        self.assertTrue(receipt.get("warnings"))
        ws = json.loads((workspace / ".dream" / "workspace.json").read_text())
        # workspace.json carries the full plugin list (both plugins).
        self.assertEqual(len(ws["plugins"]), 2)


if __name__ == "__main__":
    unittest.main()
