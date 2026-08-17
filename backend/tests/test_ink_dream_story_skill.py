"""Contract checks for the built-in Dream Agent workspace workflow.

Sync 2026-08-13: align the plugin checks with host-owned artifact sync and
artifact-association build terminology while preserving identity safeguards.
"""

from __future__ import annotations

from pathlib import Path
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_ROOT = REPOSITORY_ROOT / "plugins" / "ink-dream-story"


class InkDreamStorySkillTests(unittest.TestCase):
    def test_skill_routes_the_host_synced_artifact_lifecycle_to_the_reference(
        self,
    ) -> None:
        skill = (PLUGIN_ROOT / "skills" / "dream-story-workflow" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Agent output", skill)
        self.assertIn("page rendering", skill)
        self.assertIn("one confirmation", skill)
        self.assertIn("same-Agent continuation", skill)
        self.assertIn("Agent 构建 canonical 产物", skill)
        self.assertIn("同一 Chat Agent 构建首集产物工作台", skill)
        self.assertIn("references/dream-file-sync.md", skill)
        self.assertNotIn("Return exactly one JSON object", skill)

    def test_reference_defines_host_validation_sync_and_association_build(self) -> None:
        reference = (PLUGIN_ROOT / "references" / "dream-file-sync.md").read_text(
            encoding="utf-8"
        )
        for expected in (
            "mcp__story_workspace__write_dream_run",
            "mcp__story_workspace__write_dream_stage",
            "assets/characters/",
            "assets/scenes/",
            "storyboard.yaml",
            "构建以下工作台产物",
            "读取并校验 canonical 产物",
            "Project/Episode 产物同步",
            "宿主校验四项产物",
            "构建 EP01 产物关联",
            "不得猜测最近 Run",
            "禁止用 Write、Edit 或 Bash 写 `.dream/**`",
            "不再次询问确认",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, reference)
        for forbidden in (
            "尚未建立可信的第一集关联",
            "恢复可信 Episode 关联",
            "签发 EP01 绑定",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, reference)

    def test_reference_has_no_dream_rejection_or_second_gate_workflow(self) -> None:
        reference = (PLUGIN_ROOT / "references" / "dream-file-sync.md").read_text(
            encoding="utf-8"
        ).lower()
        for forbidden in (
            "reject the dream",
            "retry the dream",
            "archive the dream",
            "second confirmation",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, reference)


if __name__ == "__main__":
    unittest.main()
