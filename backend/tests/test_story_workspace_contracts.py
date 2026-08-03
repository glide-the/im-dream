"""Focused regression coverage for Story Workspace canonical contracts."""

from __future__ import annotations

import importlib
import types
import unittest
from datetime import datetime
from pathlib import Path
from typing import Optional, get_type_hints

from pydantic import ValidationError


ROOT = Path(__file__).resolve().parents[1]

import story_workspace
from story_workspace import contracts
from story_workspace.contracts import (
    STORY_WORKSPACE_CONTRACT_VERSION,
    STORY_WORKSPACE_REVIEW_NOTES_MAX_LENGTH,
    StoryWorkspaceAgentStoryPayload,
    StoryWorkspaceAssetStatus,
    StoryWorkspaceBatchAction,
    StoryWorkspaceBatchReviewRequest,
    StoryWorkspaceCharacter,
    StoryWorkspaceContentStatus,
    StoryWorkspaceResourceType,
    StoryWorkspaceReviewActionRequest,
    StoryWorkspaceReviewStatus,
    StoryWorkspaceRoleType,
    StoryWorkspaceScene,
    StoryWorkspaceScenePatch,
    StoryWorkspaceStory,
    StoryWorkspaceStoryFilter,
    StoryWorkspaceStoryType,
)


class StoryWorkspaceCanonicalContractTest(unittest.TestCase):
    def test_canonical_owner_and_public_prefixes(self) -> None:
        self.assertEqual(STORY_WORKSPACE_CONTRACT_VERSION, "1.2.0")
        self.assertTrue(contracts.__all__)
        self.assertTrue(
            all(
                name.startswith("StoryWorkspace")
                or name.startswith("STORY_WORKSPACE_")
                for name in contracts.__all__
            )
        )
        self.assertEqual(len(contracts.__all__), len(set(contracts.__all__)))
        self.assertTrue(all(hasattr(contracts, name) for name in contracts.__all__))

        old_public_names = {
            "TYPE_CONTRACT_VERSION",
            "ReviewStatus",
            "ContentStatus",
            "StoryType",
            "RoleType",
            "BatchAction",
            "ResourceType",
            "PaginationInfo",
            "PaginatedResponse",
            "StoryFilter",
            "CharacterFilter",
            "SceneFilter",
            "ReviewActionRequest",
            "BatchReviewRequest",
            "BatchReviewResponse",
            "WorkspaceStats",
            "AgentCharacterOutput",
            "AgentSceneOutput",
            "AgentStoryOutput",
            "AgentOutputRequest",
            "Agent" + "CharacterPayload",
            "Agent" + "ScenePayload",
            "Agent" + "StoryPayload",
            "Workspace" + "Patch",
            "Story" + "Patch",
            "Character" + "Patch",
            "Scene" + "Patch",
        }
        self.assertTrue(all(not hasattr(contracts, name) for name in old_public_names))

    def test_story_workspace_review_contract_v1_1(self) -> None:
        self.assertEqual(STORY_WORKSPACE_CONTRACT_VERSION, "1.2.0")
        self.assertEqual(STORY_WORKSPACE_REVIEW_NOTES_MAX_LENGTH, 2000)
        self.assertEqual(
            [item.value for item in StoryWorkspaceAssetStatus],
            ["active", "archived"],
        )
        self.assertEqual(
            [item.value for item in StoryWorkspaceContentStatus],
            ["draft", "published", "archived"],
        )
        self.assertIn("STORY_WORKSPACE_REVIEW_NOTES_MAX_LENGTH", contracts.__all__)
        self.assertIn("StoryWorkspaceAssetStatus", contracts.__all__)

        for resource_type, resource in (
            (
                StoryWorkspaceCharacter,
                StoryWorkspaceCharacter(
                    id="character-1", identifier="character-1", name="Character"
                ),
            ),
            (
                StoryWorkspaceScene,
                StoryWorkspaceScene(id="scene-1", identifier="scene-1", name="Scene"),
            ),
        ):
            with self.subTest(resource=resource_type.__name__):
                hints = get_type_hints(resource_type)
                self.assertIs(hints["status"], StoryWorkspaceAssetStatus)
                self.assertEqual(hints["review_notes"], Optional[str])
                self.assertEqual(hints["confirmed_at"], Optional[datetime])
                self.assertEqual(hints["archived_at"], Optional[datetime])
                self.assertEqual(resource.status, StoryWorkspaceAssetStatus.ACTIVE)
                self.assertIsNone(resource.review_notes)
                self.assertIsNone(resource.confirmed_at)
                self.assertIsNone(resource.archived_at)

    def test_story_workspace_review_request_notes_boundary(self) -> None:
        valid_notes = "界" * STORY_WORKSPACE_REVIEW_NOTES_MAX_LENGTH
        invalid_notes = "界" * (STORY_WORKSPACE_REVIEW_NOTES_MAX_LENGTH + 1)

        for review_notes in (None, valid_notes):
            with self.subTest(kind="single", length=None if review_notes is None else len(review_notes)):
                request = StoryWorkspaceReviewActionRequest(review_notes=review_notes)
                self.assertEqual(request.review_notes, review_notes)
            with self.subTest(kind="batch", length=None if review_notes is None else len(review_notes)):
                request = StoryWorkspaceBatchReviewRequest(
                    action=StoryWorkspaceBatchAction.REJECT,
                    ids=["character-1"],
                    resource_type=StoryWorkspaceResourceType.CHARACTER,
                    review_notes=review_notes,
                )
                self.assertEqual(request.review_notes, review_notes)

        with self.assertRaises(ValueError):
            StoryWorkspaceReviewActionRequest(review_notes=invalid_notes)
        with self.assertRaises(ValueError):
            StoryWorkspaceBatchReviewRequest(
                action=StoryWorkspaceBatchAction.REJECT,
                ids=["scene-1"],
                resource_type=StoryWorkspaceResourceType.SCENE,
                review_notes=invalid_notes,
            )

    def test_package_marker_does_not_reexport_business_contracts(self) -> None:
        self.assertFalse(hasattr(story_workspace, "StoryWorkspaceStory"))

    def test_values_defaults_and_mutable_factories_are_preserved(self) -> None:
        self.assertEqual(
            [item.value for item in StoryWorkspaceReviewStatus],
            ["pending", "confirmed", "rejected"],
        )
        self.assertEqual(
            [item.value for item in StoryWorkspaceContentStatus],
            ["draft", "published", "archived"],
        )
        self.assertEqual(
            [item.value for item in StoryWorkspaceStoryType],
            ["short", "long", "script", "outline"],
        )
        self.assertEqual(
            [item.value for item in StoryWorkspaceRoleType],
            ["protagonist", "supporting", "extra"],
        )
        self.assertEqual(
            [item.value for item in StoryWorkspaceBatchAction],
            ["confirm", "reject", "archive"],
        )

        story = StoryWorkspaceStory(id="story-1", identifier="story-1", title="Title")
        self.assertEqual(story.status, StoryWorkspaceContentStatus.DRAFT)
        self.assertEqual(story.review_status, StoryWorkspaceReviewStatus.PENDING)
        self.assertEqual(story.type, StoryWorkspaceStoryType.SHORT)
        self.assertTrue(story.agent_generated)

        first = StoryWorkspaceCharacter(id="char-1", identifier="char-1", name="One")
        second = StoryWorkspaceCharacter(id="char-2", identifier="char-2", name="Two")
        first.tags.append("lead")
        self.assertEqual(second.tags, [])

        first_filter = StoryWorkspaceStoryFilter()
        second_filter = StoryWorkspaceStoryFilter()
        first_filter.review_status.append(StoryWorkspaceReviewStatus.PENDING)
        self.assertEqual(second_filter.review_status, [])

    def test_pydantic_payload_and_patch_semantics_are_preserved(self) -> None:
        payload = StoryWorkspaceAgentStoryPayload(
            title="  标题  ",
            characters=[{"name": " 角色 "}],
            scenes=[{"name": " 场景 ", "order_index": 1}],
            future_field="ignored",
        )
        self.assertEqual(payload.title, "标题")
        self.assertEqual(payload.characters[0].name, "角色")
        self.assertEqual(payload.scenes[0].name, "场景")
        self.assertNotIn("future_field", payload.model_dump())

        with self.assertRaises(ValidationError):
            StoryWorkspaceAgentStoryPayload(description="missing title")
        with self.assertRaises(ValidationError):
            StoryWorkspaceScenePatch(unknown_field="forbidden")
        self.assertEqual(StoryWorkspaceScenePatch().model_dump(exclude_unset=True), {})

    def test_stdlib_types_and_old_owner_path(self) -> None:
        self.assertTrue(hasattr(types, "ModuleType"))
        self.assertIs(importlib.import_module("types"), types)
        self.assertNotEqual(Path(types.__file__).resolve().parent, ROOT / "types")
        self.assertFalse((ROOT / "types").exists())


if __name__ == "__main__":
    unittest.main()
