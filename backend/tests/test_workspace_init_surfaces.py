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
        self.assertIn("静态启动层只读", readme)
        self.assertIn("workspace.json", readme)
        self.assertIn("runtime/runs/<workflow_run_id>", readme)
        self.assertIn("mcp__story_workspace__write_dream_run", readme)
        self.assertIn("mcp__story_workspace__write_dream_stage", readme)
        self.assertIn("禁止使用 Write、Edit 或 Bash", readme)
        self.assertEqual(step["step"], "materialize-surface")
        self.assertEqual(step["surface"], "dream")

    def test_materialized_readme_states_the_truthful_refresh_contract(self) -> None:
        materialize_dream_surface(
            self.workspace, "deck-1", self.PLUGINS, "/story-workspace/dream"
        )

        readme = (self.workspace / ".dream" / "README.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("REST API 是运行内容的真相源", readme)
        self.assertIn("waiting、editing、continuing", readme)
        self.assertIn("最长每 5 秒", readme)
        self.assertIn("story-workspace-output", readme)
        self.assertIn("匹配当前 workflow_run_id 的 runId", readme)
        self.assertIn("受控 writer 尚不主动发布 run-scoped SSE", readme)
        self.assertNotIn("SSE 只通知页面重新读取", readme)

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

    def test_materialize_write_failure_leaves_no_partial_dream(self) -> None:
        """Atomic failure path (Task 1 review follow-up, audit A4): a write
        failure inside the temp dir must fail the whole call and leave neither
        a half-written ``.dream/`` nor a stale ``.dream.tmp-*`` behind."""
        real_write_text = Path.write_text

        def flaky_write_text(self_path: Path, *args, **kwargs):  # noqa: ANN001
            if self_path.name == "README.md":
                raise OSError("simulated write failure")
            return real_write_text(self_path, *args, **kwargs)

        with mock.patch.object(Path, "write_text", flaky_write_text):
            with self.assertRaises(OSError):
                materialize_dream_surface(
                    self.workspace, "deck-1", self.PLUGINS, "/story-workspace/dream"
                )
        self.assertFalse((self.workspace / ".dream").exists())
        leftovers = [
            p.name for p in self.workspace.iterdir() if p.name.startswith(".dream")
        ]
        self.assertEqual(leftovers, [])

    def test_materialize_rebuilds_half_written_dream(self) -> None:
        """A pre-existing half-written ``.dream/`` (missing workspace.json) is
        cleared and rebuilt completely."""
        half = self.workspace / ".dream"
        half.mkdir()
        (half / "README.md").write_text("stale", encoding="utf-8")
        step = materialize_dream_surface(
            self.workspace, "deck-1", self.PLUGINS, "/story-workspace/dream"
        )
        self.assertEqual(step["step"], "materialize-surface")
        self.assertTrue((half / "workspace.json").is_file())
        self.assertNotEqual((half / "README.md").read_text(encoding="utf-8"), "stale")

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


def _write_drama_forge_compatibility_sources(root: Path) -> dict[str, bytes]:
    """Add the consumer-workspace files required by drama-forge preflight."""
    fixtures = {
        ".claude-plugin/plugin.json": b'{"name":"drama-forge"}\n',
        ".claude/docs/templates/project-init.md": b"# Drama project init\n",
        ".claude/hooks/hooks.json": b'{"hooks":{}}\n',
    }
    for relative_path, content in fixtures.items():
        target = root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    return fixtures


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

    def _register_named_plugin(
        self,
        installation_id: str,
        package_spec: str,
        *,
        deck_id: str | None = None,
        with_surfaces: bool = False,
        status: str = "ready",
        order_index: int = 0,
    ):
        package_name, marketplace = package_spec.split("@", 1)
        source = _write_surface_plugin(
            Path(self._tmp.name) / f"src-{installation_id}",
            with_surfaces=with_surfaces,
        )
        if package_spec == "drama-forge@drama-studio":
            _write_drama_forge_compatibility_sources(source)
        artifact = import_tree(
            source,
            package_name=package_name,
            marketplace=marketplace,
        )
        self.db.execute(
            """
            INSERT INTO claude_plugin_installations (
                id, requested_package_spec, package_name, marketplace,
                resolved_version, source_type, artifact_digest, artifact_path,
                claude_cli_version, status, operation_id
            ) VALUES (?, ?, ?, ?, '1.0.0', 'platform-builtin',
                      ?, ?, '2.1.220', ?, ?)
            """,
            (
                installation_id,
                package_spec,
                package_name,
                marketplace,
                artifact.digest,
                str(artifact.path),
                status,
                f"op-{installation_id}",
            ),
        )
        if deck_id is not None:
            self.db.execute(
                """
                INSERT INTO deck_claude_plugin_refs (
                    deck_id, plugin_installation_id, package_spec,
                    resolved_version, artifact_digest, enabled, order_index
                ) VALUES (?, ?, ?, '1.0.0', ?, 1, ?)
                """,
                (
                    deck_id,
                    installation_id,
                    package_spec,
                    artifact.digest,
                    order_index,
                ),
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

    def test_server_adapter_merges_with_deck_plugin_and_materializes_dream(self) -> None:
        drama = self._register_named_plugin(
            "cpi-drama",
            "drama-forge@drama-studio",
            deck_id="deck-1",
        )
        adapter = self._register_named_plugin(
            "cpi-adapter",
            "ink-dream-story@platform-builtin",
            with_surfaces=True,
        )
        workspace = Path(self._tmp.name) / "ws-adapter"
        workspace.mkdir()

        receipt = pack_workspace_plugins(
            self.db,
            workspace=workspace,
            deck_id="deck-1",
            server_adapter_package_specs=("ink-dream-story@platform-builtin",),
        )

        manifest = json.loads(
            (workspace / ".ink" / "launch-manifest.json").read_text()
        )
        self.assertEqual(
            [entry["package_spec"] for entry in manifest["plugins"]],
            ["drama-forge@drama-studio", "ink-dream-story@platform-builtin"],
        )
        self.assertEqual(
            [entry["artifact_digest"] for entry in manifest["plugins"]],
            [drama.digest, adapter.digest],
        )
        self.assertEqual(receipt["surfaces"][0]["name"], "dream")
        dream_workspace = json.loads(
            (workspace / ".dream" / "workspace.json").read_text()
        )
        self.assertEqual(
            [entry["package_spec"] for entry in dream_workspace["plugins"]],
            ["drama-forge@drama-studio", "ink-dream-story@platform-builtin"],
        )
        adapter_refs = self.db.execute(
            """
            SELECT COUNT(*) FROM deck_claude_plugin_refs
            WHERE deck_id = ? AND package_spec = ?
            """,
            ("deck-1", "ink-dream-story@platform-builtin"),
        ).fetchone()[0]
        self.assertEqual(adapter_refs, 0)

    def test_dream_pack_installs_drama_forge_consumer_compatibility_files(self) -> None:
        self._register_named_plugin(
            "cpi-drama",
            "drama-forge@drama-studio",
            deck_id="deck-1",
        )
        self._register_named_plugin(
            "cpi-adapter",
            "ink-dream-story@platform-builtin",
            with_surfaces=True,
        )
        workspace = Path(self._tmp.name) / "ws-drama-compat"
        workspace.mkdir()

        pack_workspace_plugins(
            self.db,
            workspace=workspace,
            deck_id="deck-1",
            server_adapter_package_specs=("ink-dream-story@platform-builtin",),
        )

        expected = {
            "plugin.json": b'{"name":"drama-forge"}\n',
            ".claude/docs/templates/project-init.md": b"# Drama project init\n",
            ".claude/hooks/hooks.json": b'{"hooks":{}}\n',
        }
        for relative_path, content in expected.items():
            with self.subTest(relative_path=relative_path):
                self.assertEqual((workspace / relative_path).read_bytes(), content)

    def test_server_adapter_is_opt_in_for_normal_chat_pack(self) -> None:
        self._register_named_plugin(
            "cpi-drama",
            "drama-forge@drama-studio",
            deck_id="deck-1",
        )
        self._register_named_plugin(
            "cpi-adapter",
            "ink-dream-story@platform-builtin",
            with_surfaces=True,
        )
        workspace = Path(self._tmp.name) / "ws-default"
        workspace.mkdir()

        receipt = pack_workspace_plugins(
            self.db,
            workspace=workspace,
            deck_id="deck-1",
        )

        self.assertEqual(
            [entry["package_spec"] for entry in receipt["plugins"]],
            ["drama-forge@drama-studio"],
        )
        self.assertNotIn("surfaces", receipt)
        self.assertFalse((workspace / ".dream").exists())
        self.assertFalse((workspace / "plugin.json").exists())
        self.assertFalse(
            (workspace / ".claude" / "docs" / "templates" / "project-init.md").exists()
        )
        self.assertFalse((workspace / ".claude" / "hooks" / "hooks.json").exists())

    def test_dream_drama_compatibility_conflict_fails_closed(self) -> None:
        self._register_named_plugin(
            "cpi-drama",
            "drama-forge@drama-studio",
            deck_id="deck-1",
        )
        self._register_named_plugin(
            "cpi-adapter",
            "ink-dream-story@platform-builtin",
            with_surfaces=True,
        )
        workspace = Path(self._tmp.name) / "ws-drama-conflict"
        workspace.mkdir()
        (workspace / "plugin.json").write_bytes(b"user-owned\n")

        with self.assertRaises(WorkspacePackError) as caught:
            pack_workspace_plugins(
                self.db,
                workspace=workspace,
                deck_id="deck-1",
                server_adapter_package_specs=("ink-dream-story@platform-builtin",),
            )

        self.assertEqual(caught.exception.code, "CLAUDE_PLUGIN_INIT_PROFILE_INVALID")
        self.assertEqual((workspace / "plugin.json").read_bytes(), b"user-owned\n")

    def test_dream_drama_compatibility_rejects_parent_symlink_escape(self) -> None:
        self._register_named_plugin(
            "cpi-drama",
            "drama-forge@drama-studio",
            deck_id="deck-1",
        )
        self._register_named_plugin(
            "cpi-adapter",
            "ink-dream-story@platform-builtin",
            with_surfaces=True,
        )
        workspace = Path(self._tmp.name) / "ws-drama-symlink"
        outside = Path(self._tmp.name) / "outside-fresh"
        workspace.mkdir()
        outside.mkdir()
        (workspace / ".claude").symlink_to(outside, target_is_directory=True)

        with self.assertRaises(WorkspacePackError) as caught:
            pack_workspace_plugins(
                self.db,
                workspace=workspace,
                deck_id="deck-1",
                server_adapter_package_specs=("ink-dream-story@platform-builtin",),
            )

        self.assertEqual(caught.exception.code, "CLAUDE_PLUGIN_INIT_PROFILE_INVALID")
        self.assertFalse((outside / "docs" / "templates" / "project-init.md").exists())
        self.assertFalse((outside / "hooks" / "hooks.json").exists())

    def test_dream_drama_compatibility_rejects_parent_swapped_to_symlink(self) -> None:
        self._register_named_plugin(
            "cpi-drama",
            "drama-forge@drama-studio",
            deck_id="deck-1",
        )
        self._register_named_plugin(
            "cpi-adapter",
            "ink-dream-story@platform-builtin",
            with_surfaces=True,
        )
        workspace = Path(self._tmp.name) / "ws-drama-symlink-swap"
        outside = Path(self._tmp.name) / "outside-fresh-swap"
        workspace.mkdir()
        (workspace / ".claude").mkdir()
        outside.mkdir()
        real_fsync = os.fsync
        swapped = False

        def fsync_then_swap(fd):  # noqa: ANN001
            nonlocal swapped
            real_fsync(fd)
            if not swapped:
                swapped = True
                (workspace / ".claude").rmdir()
                (workspace / ".claude").symlink_to(
                    outside,
                    target_is_directory=True,
                )

        with mock.patch(
            "services.claude_plugin.workspace_packer.os.fsync",
            side_effect=fsync_then_swap,
        ):
            with self.assertRaises(WorkspacePackError):
                pack_workspace_plugins(
                    self.db,
                    workspace=workspace,
                    deck_id="deck-1",
                    server_adapter_package_specs=("ink-dream-story@platform-builtin",),
                )

        self.assertTrue(swapped)
        self.assertEqual(
            (workspace / "plugin.json").read_bytes(),
            b'{"name":"drama-forge"}\n',
        )
        self.assertFalse((outside / "docs" / "templates" / "project-init.md").exists())
        self.assertFalse((outside / "hooks" / "hooks.json").exists())

    def test_dream_drama_partial_publish_is_safe_and_reentrant(self) -> None:
        self._register_named_plugin(
            "cpi-drama",
            "drama-forge@drama-studio",
            deck_id="deck-1",
        )
        self._register_named_plugin(
            "cpi-adapter",
            "ink-dream-story@platform-builtin",
            with_surfaces=True,
        )
        workspace = Path(self._tmp.name) / "ws-drama-partial"
        conflict = workspace / ".claude" / "docs" / "templates" / "project-init.md"
        conflict.parent.mkdir(parents=True)
        conflict.write_bytes(b"concurrent-conflict\n")

        with self.assertRaises(WorkspacePackError):
            pack_workspace_plugins(
                self.db,
                workspace=workspace,
                deck_id="deck-1",
                server_adapter_package_specs=("ink-dream-story@platform-builtin",),
            )

        self.assertEqual(
            (workspace / "plugin.json").read_bytes(),
            b'{"name":"drama-forge"}\n',
        )
        self.assertEqual(conflict.read_bytes(), b"concurrent-conflict\n")
        self.assertFalse((workspace / ".claude" / "hooks" / "hooks.json").exists())
        self.assertEqual(list(workspace.rglob("*.dream-compat-*")), [])

        conflict.unlink()
        receipt = pack_workspace_plugins(
            self.db,
            workspace=workspace,
            deck_id="deck-1",
            server_adapter_package_specs=("ink-dream-story@platform-builtin",),
        )
        self.assertEqual(receipt["surfaces"][0]["name"], "dream")
        self.assertEqual(conflict.read_bytes(), b"# Drama project init\n")
        self.assertEqual(
            (workspace / ".claude" / "hooks" / "hooks.json").read_bytes(),
            b'{"hooks":{}}\n',
        )

    def test_dream_drama_compatibility_rollback_preserves_concurrent_replacement(self) -> None:
        self._register_named_plugin(
            "cpi-drama",
            "drama-forge@drama-studio",
            deck_id="deck-1",
        )
        self._register_named_plugin(
            "cpi-adapter",
            "ink-dream-story@platform-builtin",
            with_surfaces=True,
        )
        workspace = Path(self._tmp.name) / "ws-drama-race"
        workspace.mkdir()
        real_link = os.link
        calls = 0

        def replace_then_fail(source, target, **kwargs):  # noqa: ANN001
            nonlocal calls
            calls += 1
            if calls == 1:
                real_link(source, target, **kwargs)
                published_target = Path(target)
                if not published_target.is_absolute():
                    published_target = workspace / published_target
                published_target.unlink()
                published_target.write_bytes(b"concurrent-owner\n")
                return
            raise OSError("simulated later publish failure")

        with mock.patch(
            "services.claude_plugin.workspace_packer.os.link",
            side_effect=replace_then_fail,
        ):
            with self.assertRaises(WorkspacePackError):
                pack_workspace_plugins(
                    self.db,
                    workspace=workspace,
                    deck_id="deck-1",
                    server_adapter_package_specs=("ink-dream-story@platform-builtin",),
                )

        self.assertEqual((workspace / "plugin.json").read_bytes(), b"concurrent-owner\n")
        self.assertFalse(
            (workspace / ".claude" / "docs" / "templates" / "project-init.md").exists()
        )
        self.assertFalse((workspace / ".claude" / "hooks" / "hooks.json").exists())
        self.assertEqual(list(workspace.rglob("*.dream-compat-*")), [])

    def test_server_adapter_declarations_are_deduplicated(self) -> None:
        self._register_named_plugin(
            "cpi-drama",
            "drama-forge@drama-studio",
            deck_id="deck-1",
        )
        self._register_named_plugin(
            "cpi-adapter",
            "ink-dream-story@platform-builtin",
            deck_id="deck-1",
            with_surfaces=True,
            order_index=1,
        )
        workspace = Path(self._tmp.name) / "ws-deduplicated"
        workspace.mkdir()

        receipt = pack_workspace_plugins(
            self.db,
            workspace=workspace,
            deck_id="deck-1",
            server_adapter_package_specs=(
                "ink-dream-story@platform-builtin",
                "ink-dream-story@platform-builtin",
            ),
        )

        package_specs = [entry["package_spec"] for entry in receipt["plugins"]]
        self.assertEqual(package_specs.count("ink-dream-story@platform-builtin"), 1)
        self.assertEqual(len(package_specs), 2)

    def test_server_adapter_missing_or_not_ready_fails_closed(self) -> None:
        self._register_named_plugin(
            "cpi-drama",
            "drama-forge@drama-studio",
            deck_id="deck-1",
        )
        self._register_named_plugin(
            "cpi-adapter-not-ready",
            "ink-dream-story@platform-builtin",
            with_surfaces=True,
            status="installing",
        )

        cases = (
            ("ink-dream-story@platform-builtin", "CLAUDE_PLUGIN_NOT_READY"),
            ("missing-adapter@platform-builtin", "CLAUDE_PLUGIN_NOT_FOUND"),
        )
        for index, (package_spec, expected_code) in enumerate(cases):
            with self.subTest(package_spec=package_spec):
                workspace = Path(self._tmp.name) / f"ws-fail-{index}"
                workspace.mkdir()
                with self.assertRaises(WorkspacePackError) as caught:
                    pack_workspace_plugins(
                        self.db,
                        workspace=workspace,
                        deck_id="deck-1",
                        server_adapter_package_specs=(package_spec,),
                    )
                self.assertEqual(caught.exception.code, expected_code)
                self.assertFalse(
                    (workspace / ".ink" / "launch-manifest.json").exists()
                )
                self.assertFalse((workspace / ".dream").exists())

    def test_frozen_workspace_does_not_append_late_server_adapter(self) -> None:
        self._register_named_plugin(
            "cpi-drama",
            "drama-forge@drama-studio",
            deck_id="deck-1",
        )
        self._register_named_plugin(
            "cpi-adapter",
            "ink-dream-story@platform-builtin",
            with_surfaces=True,
        )
        workspace = Path(self._tmp.name) / "ws-frozen-adapter"
        workspace.mkdir()
        first = pack_workspace_plugins(
            self.db,
            workspace=workspace,
            deck_id="deck-1",
        )
        first_manifest = (
            workspace / ".ink" / "launch-manifest.json"
        ).read_bytes()

        second = pack_workspace_plugins(
            self.db,
            workspace=workspace,
            deck_id="deck-1",
            server_adapter_package_specs=("ink-dream-story@platform-builtin",),
        )

        self.assertTrue(second["frozen"])
        self.assertEqual(
            [entry["package_spec"] for entry in second["plugins"]],
            [entry["package_spec"] for entry in first["plugins"]],
        )
        self.assertEqual(
            [entry["artifact_digest"] for entry in second["plugins"]],
            [entry["artifact_digest"] for entry in first["plugins"]],
        )
        self.assertEqual(
            (workspace / ".ink" / "launch-manifest.json").read_bytes(),
            first_manifest,
        )
        self.assertFalse((workspace / ".dream").exists())
        self.assertFalse((workspace / "plugin.json").exists())
        self.assertFalse((workspace / ".claude" / "hooks" / "hooks.json").exists())

    def test_frozen_dream_workspace_validates_but_never_repairs_drama_compatibility(self) -> None:
        self._register_named_plugin(
            "cpi-drama",
            "drama-forge@drama-studio",
            deck_id="deck-1",
        )
        self._register_named_plugin(
            "cpi-adapter",
            "ink-dream-story@platform-builtin",
            with_surfaces=True,
        )
        workspace = Path(self._tmp.name) / "ws-frozen-drama-compat"
        workspace.mkdir()
        pack_workspace_plugins(
            self.db,
            workspace=workspace,
            deck_id="deck-1",
            server_adapter_package_specs=("ink-dream-story@platform-builtin",),
        )
        plugin_json = workspace / "plugin.json"
        missing_hooks = workspace / ".claude" / "hooks" / "hooks.json"
        plugin_json.write_bytes(b"changed-after-freeze\n")
        missing_hooks.unlink()

        with self.assertRaises(WorkspacePackError) as caught:
            pack_workspace_plugins(
                self.db,
                workspace=workspace,
                deck_id="deck-1",
                server_adapter_package_specs=("ink-dream-story@platform-builtin",),
            )

        self.assertEqual(caught.exception.code, "CLAUDE_PLUGIN_INIT_PROFILE_INVALID")
        self.assertEqual(plugin_json.read_bytes(), b"changed-after-freeze\n")
        self.assertFalse(missing_hooks.exists())

        # Even after the conflicting file is restored, the frozen pack must
        # report the missing target instead of installing it late.
        plugin_json.write_bytes(b'{"name":"drama-forge"}\n')
        with self.assertRaises(WorkspacePackError) as missing_caught:
            pack_workspace_plugins(
                self.db,
                workspace=workspace,
                deck_id="deck-1",
                server_adapter_package_specs=("ink-dream-story@platform-builtin",),
            )
        self.assertEqual(
            missing_caught.exception.code,
            "CLAUDE_PLUGIN_INIT_PROFILE_INVALID",
        )
        self.assertIn("frozen workspace is missing", str(missing_caught.exception))
        self.assertFalse(missing_hooks.exists())

    def test_frozen_dream_workspace_rejects_parent_symlink_escape(self) -> None:
        self._register_named_plugin(
            "cpi-drama",
            "drama-forge@drama-studio",
            deck_id="deck-1",
        )
        self._register_named_plugin(
            "cpi-adapter",
            "ink-dream-story@platform-builtin",
            with_surfaces=True,
        )
        workspace = Path(self._tmp.name) / "ws-frozen-drama-symlink"
        outside = Path(self._tmp.name) / "outside-frozen"
        workspace.mkdir()
        pack_workspace_plugins(
            self.db,
            workspace=workspace,
            deck_id="deck-1",
            server_adapter_package_specs=("ink-dream-story@platform-builtin",),
        )

        project_init = workspace / ".claude" / "docs" / "templates" / "project-init.md"
        hooks_json = workspace / ".claude" / "hooks" / "hooks.json"
        project_init_content = project_init.read_bytes()
        hooks_content = hooks_json.read_bytes()
        project_init.unlink()
        hooks_json.unlink()
        project_init.parent.rmdir()
        project_init.parent.parent.rmdir()
        hooks_json.parent.rmdir()
        (workspace / ".claude").rmdir()
        (outside / "docs" / "templates").mkdir(parents=True)
        (outside / "hooks").mkdir()
        outside_project_init = outside / "docs" / "templates" / "project-init.md"
        outside_hooks = outside / "hooks" / "hooks.json"
        outside_project_init.write_bytes(project_init_content)
        outside_hooks.write_bytes(hooks_content)
        (workspace / ".claude").symlink_to(outside, target_is_directory=True)

        with self.assertRaises(WorkspacePackError) as caught:
            pack_workspace_plugins(
                self.db,
                workspace=workspace,
                deck_id="deck-1",
                server_adapter_package_specs=("ink-dream-story@platform-builtin",),
            )

        self.assertEqual(caught.exception.code, "CLAUDE_PLUGIN_INIT_PROFILE_INVALID")
        self.assertEqual(outside_project_init.read_bytes(), project_init_content)
        self.assertEqual(outside_hooks.read_bytes(), hooks_content)

    def test_frozen_dream_workspace_rejects_parent_swapped_to_symlink(self) -> None:
        self._register_named_plugin(
            "cpi-drama",
            "drama-forge@drama-studio",
            deck_id="deck-1",
        )
        self._register_named_plugin(
            "cpi-adapter",
            "ink-dream-story@platform-builtin",
            with_surfaces=True,
        )
        workspace = Path(self._tmp.name) / "ws-frozen-drama-symlink-swap"
        outside = Path(self._tmp.name) / "outside-frozen-swap"
        workspace.mkdir()
        pack_workspace_plugins(
            self.db,
            workspace=workspace,
            deck_id="deck-1",
            server_adapter_package_specs=("ink-dream-story@platform-builtin",),
        )
        project_content = (
            workspace / ".claude" / "docs" / "templates" / "project-init.md"
        ).read_bytes()
        hooks_content = (workspace / ".claude" / "hooks" / "hooks.json").read_bytes()
        (outside / "docs" / "templates").mkdir(parents=True)
        (outside / "hooks").mkdir()
        outside_project = outside / "docs" / "templates" / "project-init.md"
        outside_hook = outside / "hooks" / "hooks.json"
        outside_project.write_bytes(project_content)
        outside_hook.write_bytes(hooks_content)
        original_claude = workspace / ".claude-original"
        real_open = os.open
        swapped = False

        def open_parent_then_swap(path, flags, mode=0o777, *, dir_fd=None):  # noqa: ANN001
            nonlocal swapped
            if os.fspath(path) == ".claude" and dir_fd is not None and not swapped:
                swapped = True
                (workspace / ".claude").rename(original_claude)
                (workspace / ".claude").symlink_to(
                    outside,
                    target_is_directory=True,
                )
            return real_open(path, flags, mode, dir_fd=dir_fd)

        with mock.patch(
            "services.claude_plugin.workspace_packer.os.open",
            side_effect=open_parent_then_swap,
        ):
            with self.assertRaises(WorkspacePackError):
                pack_workspace_plugins(
                    self.db,
                    workspace=workspace,
                    deck_id="deck-1",
                    server_adapter_package_specs=("ink-dream-story@platform-builtin",),
                )

        self.assertTrue(swapped)
        self.assertEqual(outside_project.read_bytes(), project_content)
        self.assertEqual(outside_hook.read_bytes(), hooks_content)


if __name__ == "__main__":
    unittest.main()
