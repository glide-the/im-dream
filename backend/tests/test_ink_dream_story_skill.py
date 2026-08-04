"""Contract checks for the built-in Dream Agent workspace workflow."""

from __future__ import annotations

from pathlib import Path
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_ROOT = REPOSITORY_ROOT / "plugins" / "ink-dream-story"


class InkDreamStorySkillTests(unittest.TestCase):
    def test_skill_routes_the_four_stage_lifecycle_to_the_reference(self) -> None:
        skill = (PLUGIN_ROOT / "skills" / "dream-story-workflow" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Agent output", skill)
        self.assertIn("page rendering", skill)
        self.assertIn("one confirmation", skill)
        self.assertIn("same Chat Agent continues", skill)
        self.assertIn("references/dream-file-sync.md", skill)
        self.assertNotIn("Return exactly one JSON object", skill)

    def test_reference_defines_each_canonical_write_then_dream_sync_point(self) -> None:
        reference = (PLUGIN_ROOT / "references" / "dream-file-sync.md").read_text(
            encoding="utf-8"
        )
        for expected in (
            "mcp__story_workspace__write_dream_run",
            "mcp__story_workspace__write_dream_stage",
            "assets/characters/",
            "assets/scenes/",
            "storyboard.yaml",
            "characters",
            "scenes",
            "storyboards",
            "expectedRevision",
            "sourceFiles",
            "Do not guess",
            "Do not write `.dream` with Write, Edit, or Bash",
            "Do not ask for another confirmation",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, reference)

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
