"""Next Episode identity horizon and action projection tests."""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from services.story_workspace.multi_episode_action_service import (  # noqa: E402
    StoryWorkspaceEpisodeActionSnapshot,
    StoryWorkspaceEpisodeRegistryActionContext,
    StoryWorkspaceMultiEpisodeActionProjector,
    StoryWorkspaceNextEpisodeActionPlanner,
)
from story_workspace.contracts import (  # noqa: E402
    StoryWorkspaceEpisodeAction,
    StoryWorkspaceEpisodeArtifactAvailability,
    StoryWorkspaceEpisodeBindingEntry,
    StoryWorkspaceEpisodeRegistryFile,
    StoryWorkspaceEpisodeWorkflowFile,
)


RUN_ID = "run_0123456789abcdef0123456789abcdef"
EP01_ID = "1" * 32
EP02_ID = "2" * 32
REVISION = "sha256:" + "a" * 64
NOW = datetime(2026, 8, 6, tzinfo=UTC)


def _entry(number: int, uid: str) -> StoryWorkspaceEpisodeBindingEntry:
    code = f"EP{number:02d}"
    return StoryWorkspaceEpisodeBindingEntry(
        episode_uid=uid,
        episode_number=number,
        episode_code=code,
        episode_root=f"stories/demo/episodes/{code}",
        created_at=NOW,
    )


def _registry(
    *entries: StoryWorkspaceEpisodeBindingEntry,
    active_uid: str,
    revision: int,
) -> StoryWorkspaceEpisodeRegistryFile:
    return StoryWorkspaceEpisodeRegistryFile(
        workflow_run_id=RUN_ID,
        story_slug="demo",
        active_episode_uid=active_uid,
        episodes=list(entries),
        revision=revision,
        updated_at=NOW,
    )


def _current_snapshot(
    current_episode: object,
    *,
    validated: bool,
) -> StoryWorkspaceEpisodeActionSnapshot:
    return StoryWorkspaceEpisodeActionSnapshot(
        run_id=RUN_ID,
        current_episode=current_episode,
        current_action=(
            StoryWorkspaceEpisodeAction.PREPARE_RENDER_GUIDE
            if validated
            else StoryWorkspaceEpisodeAction.GENERATE_PROMPTS
        ),
        current_can_dispatch=True,
        current_input_revision=REVISION,
        storyboard_current=True,
        storyboard_can_regenerate=True,
        validation_current=validated,
        render_guide_current=False,
        next_episode=None,
        next_entry_action=None,
        next_entry_can_dispatch=False,
        project_has_next_episode=False,
    )


def _next_surface(episode_uid: str, *, outline_available: bool) -> object:
    artifacts = [
        SimpleNamespace(
            relative_key="episode-outline.md",
            availability=(
                StoryWorkspaceEpisodeArtifactAvailability.AVAILABLE
                if outline_available
                else StoryWorkspaceEpisodeArtifactAvailability.NOT_GENERATED
            ),
            content_revision=("sha256:" + "b" * 64) if outline_available else None,
        ),
        SimpleNamespace(
            relative_key="script.md",
            availability=StoryWorkspaceEpisodeArtifactAvailability.NOT_GENERATED,
            content_revision=None,
        ),
    ]
    return SimpleNamespace(
        run_id=RUN_ID,
        opaque_episode_id=episode_uid,
        artifacts=artifacts,
        auxiliary=SimpleNamespace(review=None),
    )


def _empty_facts(episode_uid: str) -> StoryWorkspaceEpisodeWorkflowFile:
    return StoryWorkspaceEpisodeWorkflowFile(
        workflow_run_id=RUN_ID,
        episode_uid=episode_uid,
        revision=0,
        completions=[],
        updated_at=NOW,
    )


def test_validated_ep01_recommends_server_candidate_ep02_plan() -> None:
    context = StoryWorkspaceEpisodeRegistryActionContext.build(
        _registry(_entry(1, EP01_ID), active_uid=EP01_ID, revision=1),
        total_episodes=3,
    )
    snapshot = StoryWorkspaceNextEpisodeActionPlanner().attach(
        _current_snapshot(context.current_episode, validated=True),
        context=context,
    )
    projection = StoryWorkspaceMultiEpisodeActionProjector.project(snapshot)

    assert context.next_episode is not None
    assert context.next_episode.display_label == "EP02"
    assert context.next_episode.candidate_id is not None
    assert projection.action_options[0].label == "开始 EP02 分集规划"
    assert projection.action_options[0].can_dispatch is True
    assert projection.action_options[0].target_episode.relation == "next"
    assert projection.action_options[1].target_episode.display_label == "EP01"


def test_unvalidated_current_episode_does_not_project_next_episode_actions() -> None:
    context = StoryWorkspaceEpisodeRegistryActionContext.build(
        _registry(_entry(1, EP01_ID), active_uid=EP01_ID, revision=1),
        total_episodes=3,
    )
    snapshot = StoryWorkspaceNextEpisodeActionPlanner().attach(
        _current_snapshot(context.current_episode, validated=False),
        context=context,
    )
    projection = StoryWorkspaceMultiEpisodeActionProjector.project(snapshot)

    assert all(
        item.target_episode.relation == "current"
        for item in projection.action_options
    )


def test_bound_ep02_outline_changes_next_entry_to_write_script() -> None:
    context = StoryWorkspaceEpisodeRegistryActionContext.build(
        _registry(
            _entry(1, EP01_ID),
            _entry(2, EP02_ID),
            active_uid=EP01_ID,
            revision=2,
        ),
        total_episodes=3,
    )
    snapshot = StoryWorkspaceNextEpisodeActionPlanner().attach(
        _current_snapshot(context.current_episode, validated=True),
        context=context,
        next_surface=_next_surface(EP02_ID, outline_available=True),
        next_facts=_empty_facts(EP02_ID),
    )
    projection = StoryWorkspaceMultiEpisodeActionProjector.project(snapshot)

    assert projection.action_options[0].action is StoryWorkspaceEpisodeAction.WRITE_SCRIPT
    assert projection.action_options[0].label == "创作 EP02 剧本"
    assert projection.action_options[0].target_episode.opaque_episode_id == EP02_ID


def test_active_ep02_projects_ep03_and_terminal_plan_projects_no_next() -> None:
    registry = _registry(
        _entry(1, EP01_ID),
        _entry(2, EP02_ID),
        active_uid=EP02_ID,
        revision=3,
    )
    with_ep03 = StoryWorkspaceEpisodeRegistryActionContext.build(
        registry,
        total_episodes=3,
    )
    terminal = StoryWorkspaceEpisodeRegistryActionContext.build(
        registry,
        total_episodes=2,
    )

    assert with_ep03.current_episode.display_label == "EP02"
    assert with_ep03.next_episode is not None
    assert with_ep03.next_episode.display_label == "EP03"
    assert terminal.next_episode is None
