# [Input] Installed notion-session/notion-cli packages plus connected/unconnected connector projections.
# [Output] Verify installed multi-Skill content plus real Hook/workspace capability states, stable file IDs, revisions, and symlink/path fail-closed behavior.
# [Pos] Focused unit test node for backend/notion/capabilities.py.
# [Sync] 2026-08-29: add coverage for the Settings capability and safe Skill Markdown projection contract.
# [Sync] 2026-08-29: require catalog operations to identify the real Read hook/workspace materializer and derive Skill title/files from disk.
# [Sync] 2026-08-30: require both built-in Notion packages, their distinct tool boundaries, and truthful CLI execution availability.

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from notion.capabilities import (  # noqa: E402
    NOTION_CLI_SKILL_ID,
    NOTION_SESSION_SKILL_ID,
    NOTION_SKILL_ID,
    NOTION_SKILL_IDS,
    NotionCapabilityNotFoundError,
    NotionCapabilityRevisionError,
    NotionCapabilityUnavailableError,
    build_notion_capability_catalog,
    get_notion_skill_detail,
    get_notion_skill_file,
)
from libs.claude_agent_kit.server.notion_read_hook import (  # noqa: E402
    apply_notion_page_read_redirect,
)
from notion.sync import materialize_workspace_snapshot  # noqa: E402


class TestNotionCapabilities(unittest.TestCase):
    def test_unconnected_catalog_is_inspectable_and_never_claims_mcp(self):
        catalog = build_notion_capability_catalog(None)

        self.assertEqual(catalog["schema_version"], 3)
        self.assertEqual(catalog["mcp_inventory"]["status"], "not_integrated")
        self.assertEqual(catalog["mcp_inventory"]["read_status"], "not_integrated")
        self.assertEqual(catalog["mcp_inventory"]["write_status"], "not_integrated")
        self.assertEqual(
            [skill["id"] for skill in catalog["skills"]],
            list(NOTION_SKILL_IDS),
        )
        self.assertEqual(
            {skill["availability"] for skill in catalog["skills"]},
            {"requires_connection"},
        )
        self.assertEqual(len(catalog["operations"]), 2)
        self.assertEqual(
            {operation["source"] for operation in catalog["operations"]},
            {"runtime_hook", "workspace_materializer"},
        )
        self.assertEqual(
            {operation["entrypoint"] for operation in catalog["operations"]},
            {
                apply_notion_page_read_redirect.__name__,
                materialize_workspace_snapshot.__name__,
            },
        )
        self.assertEqual(
            {operation["kind"] for operation in catalog["operations"]},
            {"read", "write"},
        )
        self.assertEqual(
            {operation["availability"] for operation in catalog["operations"]},
            {"requires_connection"},
        )
        self.assertNotIn("path", str(catalog).lower())
        self.assertNotIn("execute", str(catalog).lower())

    def test_connected_catalog_derives_scope_without_provider_calls(self):
        catalog = build_notion_capability_catalog(
            {
                "auth_status": "authenticated",
                "last_synced_at": "2026-08-29T08:00:00Z",
                "sources": [
                    {"resource_type": "notion_database", "external_id": "db-safe"},
                    {"resource_type": "notion_page", "external_id": "page-safe"},
                ],
            }
        )

        self.assertEqual(
            {skill["id"]: skill["availability"] for skill in catalog["skills"]},
            {
                NOTION_SESSION_SKILL_ID: "available",
                NOTION_CLI_SKILL_ID: "unavailable",
            },
        )
        self.assertEqual(
            {operation["availability"] for operation in catalog["operations"]},
            {"available"},
        )

    def test_skill_body_and_discovered_reference_files_use_revisioned_stable_ids(self):
        detail = get_notion_skill_detail(NOTION_SKILL_ID, None)

        self.assertNotIn("---", detail["skill"]["body"][:8])
        self.assertEqual(detail["skill"]["tools"], ["Read"])
        self.assertEqual(
            [item["id"] for item in detail["files"]],
            ["notion-db-query", "notion-page-read", "notion-search"],
        )
        self.assertTrue(
            all(not Path(item["relative_path"]).is_absolute() for item in detail["files"])
        )

        response = get_notion_skill_file(
            NOTION_SKILL_ID,
            "notion-search",
            expected_revision=detail["package_revision"],
        )
        self.assertEqual(response["file"]["media_type"], "text/markdown")
        self.assertIn("Notion 搜索参考", response["file"]["content"])
        self.assertNotIn(str(ROOT), str(response))

        with self.assertRaises(NotionCapabilityRevisionError):
            get_notion_skill_file(
                NOTION_SKILL_ID,
                "notion-search",
                expected_revision="stale-revision",
            )
        with self.assertRaises(NotionCapabilityNotFoundError):
            get_notion_skill_file(NOTION_SKILL_ID, "../../secrets")

    def test_cli_skill_is_read_from_renamed_upstream_package(self):
        detail = get_notion_skill_detail(
            NOTION_CLI_SKILL_ID,
            {"auth_status": "authenticated"},
        )

        self.assertEqual(detail["skill"]["id"], "notion-cli")
        self.assertEqual(detail["skill"]["tools"], ["Bash"])
        self.assertEqual(detail["skill"]["availability"], "unavailable")
        self.assertIn("Notion CLI 工作空间数据助手", detail["skill"]["body"])
        self.assertIn("ntn api v1/search", detail["skill"]["body"])
        self.assertEqual(
            [item["id"] for item in detail["files"]],
            ["notion-db-query", "notion-page-read", "notion-search"],
        )
        response = get_notion_skill_file(
            NOTION_CLI_SKILL_ID,
            "notion-search",
            expected_revision=detail["package_revision"],
        )
        self.assertIn("ntn api v1/search", response["file"]["content"])

    def test_symlinked_public_file_is_rejected(self):
        source_root = ROOT / "builtin_skills"
        with tempfile.TemporaryDirectory() as temporary_directory:
            skills_root = Path(temporary_directory) / "skills"
            shutil.copytree(source_root, skills_root)
            public_file = (
                skills_root
                / NOTION_SKILL_ID
                / "references"
                / "notion-search.md"
            )
            outside_file = Path(temporary_directory) / "outside.md"
            outside_file.write_text("private", encoding="utf-8")
            public_file.unlink()
            public_file.symlink_to(outside_file)

            with self.assertRaises(NotionCapabilityUnavailableError):
                get_notion_skill_detail(
                    NOTION_SKILL_ID,
                    None,
                    skills_root=skills_root,
                )

    def test_skill_title_description_files_and_revision_come_from_installed_package(self):
        source_root = ROOT / "builtin_skills"
        with tempfile.TemporaryDirectory() as temporary_directory:
            skills_root = Path(temporary_directory) / "skills"
            shutil.copytree(source_root, skills_root)
            before = get_notion_skill_detail(
                NOTION_SKILL_ID,
                None,
                skills_root=skills_root,
            )
            skill_path = skills_root / NOTION_SKILL_ID / "SKILL.md"
            content = skill_path.read_text(encoding="utf-8")
            content = "\n".join(
                "description: 从安装包读取的测试说明。"
                if line.startswith("description:")
                else line
                for line in content.splitlines()
            ).replace(
                "# Notion 工作空间助手",
                "# 安装包中的 Notion Skill 标题",
                1,
            )
            skill_path.write_text(content, encoding="utf-8")
            extra_reference = (
                skills_root / NOTION_SKILL_ID / "references" / "workspace-stage.md"
            )
            extra_reference.write_text("# Workspace stage\n", encoding="utf-8")

            after = get_notion_skill_detail(
                NOTION_SKILL_ID,
                None,
                skills_root=skills_root,
            )

            self.assertEqual(after["skill"]["title"], "安装包中的 Notion Skill 标题")
            self.assertEqual(after["skill"]["description"], "从安装包读取的测试说明。")
            self.assertIn("workspace-stage", [item["id"] for item in after["files"]])
            self.assertNotEqual(before["package_revision"], after["package_revision"])


if __name__ == "__main__":
    unittest.main()
