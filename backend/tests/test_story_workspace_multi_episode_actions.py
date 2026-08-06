"""TDD coverage for server-owned multi-Episode action option projection."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from services.story_workspace.multi_episode_action_service import (  # noqa: E402
    StoryWorkspaceEpisodeActionSnapshot,
    StoryWorkspaceEpisodeDescriptor,
    StoryWorkspaceMultiEpisodeActionProjector,
)
from story_workspace.contracts import (  # noqa: E402
    StoryWorkspaceEpisodeAction,
    StoryWorkspaceEpisodeActionAvailability,
    StoryWorkspaceEpisodeActionDispatchState,
    StoryWorkspaceEpisodeActionOptionV2,
)


RUN_ID = "run_0123456789abcdef0123456789abcdef"
EP01_ID = "1" * 32
EP02_ID = "2" * 32
REVISION = "sha256:" + "a" * 64


def _episode(number: int, uid: str, *, relation: str) -> StoryWorkspaceEpisodeDescriptor:
    return StoryWorkspaceEpisodeDescriptor(
        opaque_episode_id=uid,
        episode_number=number,
        display_label=f"EP{number:02d}",
        relation=relation,
    )


def _snapshot(**overrides: object) -> StoryWorkspaceEpisodeActionSnapshot:
    values: dict[str, object] = {
        "run_id": RUN_ID,
        "current_episode": _episode(1, EP01_ID, relation="current"),
        "current_action": StoryWorkspaceEpisodeAction.GENERATE_PROMPTS,
        "current_can_dispatch": True,
        "current_input_revision": REVISION,
        "storyboard_current": True,
        "storyboard_can_regenerate": True,
        "validation_current": False,
        "render_guide_current": False,
        "next_episode": _episode(2, EP02_ID, relation="next"),
        "next_entry_action": StoryWorkspaceEpisodeAction.PLAN_EPISODE,
        "next_entry_can_dispatch": False,
        "project_has_next_episode": True,
        "next_input_revision": REVISION,
    }
    values.update(overrides)
    if values["next_episode"] is None:
        values["next_input_revision"] = None
    return StoryWorkspaceEpisodeActionSnapshot(**values)


def test_prompt_missing_projects_exact_two_plus_five_horizon() -> None:
    projection = StoryWorkspaceMultiEpisodeActionProjector().project(_snapshot())

    assert [option.action for option in projection.action_options] == [
        StoryWorkspaceEpisodeAction.GENERATE_PROMPTS,
        StoryWorkspaceEpisodeAction.REGENERATE_STORYBOARD,
        StoryWorkspaceEpisodeAction.REVIEW_FULL_CHAIN,
        StoryWorkspaceEpisodeAction.VALIDATE_EPISODE,
        StoryWorkspaceEpisodeAction.PREPARE_RENDER_GUIDE,
        StoryWorkspaceEpisodeAction.PLAN_EPISODE,
        StoryWorkspaceEpisodeAction.WRITE_SCRIPT,
    ]
    assert projection.recommended_action_id == projection.action_options[0].action_id
    assert sum(option.is_recommended for option in projection.action_options) == 1
    assert len(projection.action_options[:2]) == 2
    assert len(projection.action_options[2:]) == 5
    assert projection.action_options[0].label == "生成 EP01 Prompt 包"
    assert projection.action_options[1].label == "基于最新剧本更新 EP01 详细分镜"
    assert projection.action_options[5].label == "开始 EP02 分集规划"
    assert projection.action_options[5].availability is StoryWorkspaceEpisodeActionAvailability.BLOCKED
    assert projection.action_options[5].can_dispatch is False


def test_initial_current_suffix_has_no_next_horizon_and_caps_at_nine() -> None:
    projection = StoryWorkspaceMultiEpisodeActionProjector().project(_snapshot(
        current_action=StoryWorkspaceEpisodeAction.PLAN_EPISODE,
        storyboard_current=False,
        storyboard_can_regenerate=False,
    ))

    assert len(projection.action_options) == 9
    assert all(option.target_episode.relation == "current" for option in projection.action_options)
    assert [option.action for option in projection.action_options[:3]] == [
        StoryWorkspaceEpisodeAction.PLAN_EPISODE,
        StoryWorkspaceEpisodeAction.WRITE_SCRIPT,
        StoryWorkspaceEpisodeAction.REVIEW_SCRIPT,
    ]


def test_validation_current_recommends_next_entry_without_mixing_targets() -> None:
    projection = StoryWorkspaceMultiEpisodeActionProjector().project(_snapshot(
        current_action=StoryWorkspaceEpisodeAction.PREPARE_RENDER_GUIDE,
        validation_current=True,
        next_entry_can_dispatch=True,
    ))

    assert [option.action for option in projection.action_options] == [
        StoryWorkspaceEpisodeAction.PLAN_EPISODE,
        StoryWorkspaceEpisodeAction.REGENERATE_STORYBOARD,
        StoryWorkspaceEpisodeAction.PREPARE_RENDER_GUIDE,
        StoryWorkspaceEpisodeAction.WRITE_SCRIPT,
    ]
    assert projection.action_options[0].target_episode.display_label == "EP02"
    assert projection.action_options[0].can_dispatch is True
    assert projection.action_options[1].target_episode.display_label == "EP01"
    assert projection.action_options[2].target_episode.display_label == "EP01"
    assert projection.action_options[3].target_episode.display_label == "EP02"


def test_last_episode_recommends_render_then_projects_none_after_completion() -> None:
    projector = StoryWorkspaceMultiEpisodeActionProjector()
    render = projector.project(_snapshot(
        current_action=StoryWorkspaceEpisodeAction.PREPARE_RENDER_GUIDE,
        validation_current=True,
        next_episode=None,
        next_entry_action=None,
        project_has_next_episode=False,
    ))
    assert [option.action for option in render.action_options] == [
        StoryWorkspaceEpisodeAction.PREPARE_RENDER_GUIDE,
        StoryWorkspaceEpisodeAction.REGENERATE_STORYBOARD,
    ]
    assert render.action_options[0].is_recommended is True

    complete = projector.project(_snapshot(
        current_action=StoryWorkspaceEpisodeAction.NONE_IN_SCOPE,
        validation_current=True,
        render_guide_current=True,
        next_episode=None,
        next_entry_action=None,
        project_has_next_episode=False,
    ))
    assert complete.recommended_action_id is None
    assert complete.action_options == []


def test_action_ids_are_opaque_target_and_revision_specific() -> None:
    projector = StoryWorkspaceMultiEpisodeActionProjector()
    first = projector.project(_snapshot())
    second = projector.project(_snapshot(current_input_revision="sha256:" + "b" * 64))

    assert len({option.action_id for option in first.action_options}) == len(first.action_options)
    assert first.action_options[0].action_id != second.action_options[0].action_id
    for option in first.action_options:
        assert option.action_id.startswith("episode_action_")
        assert "EP01" not in option.action_id
        assert "EP02" not in option.action_id
        assert "/" not in option.action_id


def test_option_contract_rejects_impossible_preview_dispatch_and_duplicate_recommended() -> None:
    option = StoryWorkspaceMultiEpisodeActionProjector().project(_snapshot()).action_options[2]
    payload = option.model_dump(mode="json", by_alias=True)
    payload.update({"canDispatch": True})
    with pytest.raises(ValidationError):
        StoryWorkspaceEpisodeActionOptionV2.model_validate(payload)

    payload = option.model_dump(mode="json", by_alias=True)
    payload.update({"dispatchState": StoryWorkspaceEpisodeActionDispatchState.ACCEPTED})
    with pytest.raises(ValidationError):
        StoryWorkspaceEpisodeActionOptionV2.model_validate(payload)
