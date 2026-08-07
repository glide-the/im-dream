"""Opaque action selection and trusted multi-Episode instruction tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from services.story_workspace.episode_workflow_instruction import (  # noqa: E402
    StoryWorkspaceEpisodeActionSelectionError,
    StoryWorkspaceTrustedEpisodeAction,
    StoryWorkspaceTrustedEpisodeActionSelector,
    story_workspace_trusted_episode_action_instruction,
)
from services.story_workspace.multi_episode_action_service import (  # noqa: E402
    StoryWorkspaceEpisodeActionSnapshot,
    StoryWorkspaceEpisodeDescriptor,
    StoryWorkspaceMultiEpisodeActionProjector,
)
from story_workspace.contracts import (  # noqa: E402
    StoryWorkspaceEpisodeAction,
    StoryWorkspaceEpisodeActionContinueCommandV2,
)


RUN_ID = "run_0123456789abcdef0123456789abcdef"
EP01_ID = "1" * 32
EP02_ID = "2" * 32
CURRENT_REVISION = "sha256:" + "a" * 64
NEXT_REVISION = "sha256:" + "b" * 64


def _projection():
    snapshot = StoryWorkspaceEpisodeActionSnapshot(
        run_id=RUN_ID,
        current_episode=StoryWorkspaceEpisodeDescriptor(
            opaque_episode_id=EP01_ID,
            episode_number=1,
            display_label="EP01",
            relation="current",
        ),
        current_action=StoryWorkspaceEpisodeAction.GENERATE_PROMPTS,
        current_can_dispatch=True,
        current_input_revision=CURRENT_REVISION,
        storyboard_current=True,
        storyboard_can_regenerate=True,
        validation_current=False,
        render_guide_current=False,
        next_episode=StoryWorkspaceEpisodeDescriptor(
            opaque_episode_id=EP02_ID,
            episode_number=2,
            display_label="EP02",
            relation="next",
        ),
        next_entry_action=StoryWorkspaceEpisodeAction.PLAN_EPISODE,
        next_entry_can_dispatch=False,
        project_has_next_episode=True,
        next_input_revision=NEXT_REVISION,
    )
    return StoryWorkspaceMultiEpisodeActionProjector.project(snapshot)


def _full_chain_projection():
    snapshot = StoryWorkspaceEpisodeActionSnapshot(
        run_id=RUN_ID,
        current_episode=StoryWorkspaceEpisodeDescriptor(
            opaque_episode_id=EP01_ID,
            episode_number=1,
            display_label="EP01",
            relation="current",
        ),
        current_action=StoryWorkspaceEpisodeAction.REVIEW_FULL_CHAIN,
        current_can_dispatch=True,
        current_input_revision=CURRENT_REVISION,
        storyboard_current=True,
        storyboard_can_regenerate=True,
        validation_current=False,
        render_guide_current=False,
        next_episode=None,
        next_entry_action=None,
        next_entry_can_dispatch=False,
        project_has_next_episode=False,
    )
    return StoryWorkspaceMultiEpisodeActionProjector.project(snapshot)


def test_continue_v2_accepts_only_opaque_action_identity() -> None:
    action_id = _projection().action_options[0].action_id
    command = StoryWorkspaceEpisodeActionContinueCommandV2(
        actionId=action_id,
        idempotencyKey="episode-action-key",
        userGuidance="保留当前镜头节奏",
    )

    assert command.action_id == action_id
    assert "episodeId" not in command.model_dump(mode="json", by_alias=True)
    assert "action" not in command.model_dump(mode="json", by_alias=True)

    with pytest.raises(ValidationError):
        StoryWorkspaceEpisodeActionContinueCommandV2.model_validate(
            {
                "actionId": action_id,
                "episodeId": EP01_ID,
                "action": "generate_prompts",
                "idempotencyKey": "episode-action-key",
            }
        )


def test_selector_resolves_exact_executable_option_and_input_revision() -> None:
    projection = _projection()
    selected = StoryWorkspaceTrustedEpisodeActionSelector.select(
        run_id=RUN_ID,
        action_id=projection.action_options[0].action_id,
        projection=projection,
    )

    assert selected.action is StoryWorkspaceEpisodeAction.GENERATE_PROMPTS
    assert selected.episode_code == "EP01"
    assert selected.target_episode_uid == EP01_ID
    assert selected.input_revision == CURRENT_REVISION


def test_selector_rejects_unknown_and_preview_actions() -> None:
    projection = _full_chain_projection()
    rejected_ids = (
        "episode_action_" + "f" * 64,
        projection.action_options[2].action_id,
        projection.action_options[3].action_id,
    )

    for action_id in rejected_ids:
        with pytest.raises(StoryWorkspaceEpisodeActionSelectionError):
            StoryWorkspaceTrustedEpisodeActionSelector.select(
                run_id=RUN_ID,
                action_id=action_id,
                projection=projection,
            )


@pytest.mark.parametrize("number", [1, 2, 3])
def test_storyboard_instruction_uses_only_trusted_episode_code(number: int) -> None:
    descriptor = StoryWorkspaceEpisodeDescriptor(
        opaque_episode_id=str(number) * 32,
        episode_number=number,
        display_label=f"EP{number:02d}",
        relation="current",
    )
    snapshot = StoryWorkspaceEpisodeActionSnapshot(
        run_id=RUN_ID,
        current_episode=descriptor,
        current_action=StoryWorkspaceEpisodeAction.REGENERATE_STORYBOARD,
        current_can_dispatch=True,
        current_input_revision=CURRENT_REVISION,
        storyboard_current=False,
        storyboard_can_regenerate=True,
        validation_current=False,
        render_guide_current=False,
        next_episode=None,
        next_entry_action=None,
        next_entry_can_dispatch=False,
        project_has_next_episode=False,
    )
    projection = StoryWorkspaceMultiEpisodeActionProjector.project(snapshot)
    selected = StoryWorkspaceTrustedEpisodeActionSelector.select(
        run_id=RUN_ID,
        action_id=projection.action_options[0].action_id,
        projection=projection,
    )

    instruction = story_workspace_trusted_episode_action_instruction(selected)

    assert f"/drama-storyboard (EP{number:02d})" in instruction
    for other in {1, 2, 3} - {number}:
        assert f"/drama-storyboard (EP{other:02d})" not in instruction
    assert "stories/" not in instruction
    assert "/Users/" not in instruction


def test_full_chain_instruction_names_the_canonical_report_contract() -> None:
    selected = StoryWorkspaceTrustedEpisodeAction(
        run_id=RUN_ID,
        action_id="episode_action_" + "1" * 64,
        action=StoryWorkspaceEpisodeAction.REVIEW_FULL_CHAIN,
        input_revision=CURRENT_REVISION,
        episode_code="EP02",
        target_episode_uid=EP02_ID,
        candidate_id=None,
    )

    instruction = story_workspace_trusted_episode_action_instruction(selected)

    assert "唯一规范输出：review-report.md" in instruction
    assert "禁止创建 full-chain-review-report.md" in instruction
    assert "scope: full-chain" in instruction
    assert "overall_verdict: APPROVED" in instruction
    assert "episode-outline.md" in instruction
    assert "script.md" in instruction
    assert "storyboard.yaml" in instruction
    assert "prompts/" in instruction
    assert "source_revisions" in instruction
    assert "不得把 review-report.md 自身列入 reviewed_files" in instruction
    assert "不得根据 total_shots" in instruction
    assert "不得记录完成事实" in instruction
    assert "EP02" in instruction
    assert "stories/" not in instruction
    assert "/Users/" not in instruction


def test_script_review_instruction_names_the_canonical_report_contract() -> None:
    selected = StoryWorkspaceTrustedEpisodeAction(
        run_id=RUN_ID,
        action_id="episode_action_" + "2" * 64,
        action=StoryWorkspaceEpisodeAction.REVIEW_SCRIPT,
        input_revision=CURRENT_REVISION,
        episode_code="EP02",
        target_episode_uid=EP02_ID,
        candidate_id=None,
    )

    instruction = story_workspace_trusted_episode_action_instruction(selected)

    assert "唯一规范输出：review-report.md" in instruction
    assert "scope: script" in instruction
    assert "reviewed_files 只能包含 script.md" in instruction
    assert "source_revisions" in instruction
    assert "当前 script.md" in instruction
    assert "不得记录完成事实" in instruction
    assert "EP02" in instruction
    assert "stories/" not in instruction
    assert "/Users/" not in instruction


def test_current_and_next_options_expose_distinct_server_input_revisions() -> None:
    snapshot = StoryWorkspaceEpisodeActionSnapshot(
        run_id=RUN_ID,
        current_episode=StoryWorkspaceEpisodeDescriptor(
            opaque_episode_id=EP01_ID,
            episode_number=1,
            display_label="EP01",
            relation="current",
        ),
        current_action=StoryWorkspaceEpisodeAction.PREPARE_RENDER_GUIDE,
        current_can_dispatch=True,
        current_input_revision=CURRENT_REVISION,
        storyboard_current=True,
        storyboard_can_regenerate=True,
        validation_current=True,
        render_guide_current=False,
        next_episode=StoryWorkspaceEpisodeDescriptor(
            opaque_episode_id=EP02_ID,
            episode_number=2,
            display_label="EP02",
            relation="next",
        ),
        next_entry_action=StoryWorkspaceEpisodeAction.PLAN_EPISODE,
        next_entry_can_dispatch=True,
        project_has_next_episode=True,
        next_input_revision=NEXT_REVISION,
    )
    projection = StoryWorkspaceMultiEpisodeActionProjector.project(snapshot)
    current = next(
        option
        for option in projection.action_options
        if option.target_episode.relation == "current"
    )
    next_option = next(
        option
        for option in projection.action_options
        if option.target_episode.relation == "next"
    )

    assert current.input_revision == CURRENT_REVISION
    assert next_option.input_revision == NEXT_REVISION
