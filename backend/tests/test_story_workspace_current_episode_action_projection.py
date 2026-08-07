"""Current Episode storyboard/Prompt projection against canonical revisions."""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from services.story_workspace.episode_action_service import (  # noqa: E402
    StoryWorkspaceEpisodeNextActionResolver,
)
from services.story_workspace.multi_episode_action_service import (  # noqa: E402
    StoryWorkspaceCurrentEpisodeActionSnapshotBuilder,
    StoryWorkspaceEpisodeDescriptor,
    StoryWorkspaceMultiEpisodeActionProjector,
)
from story_workspace.contracts import (  # noqa: E402
    StoryWorkspaceEpisodeAction,
    StoryWorkspaceEpisodeArtifactAvailability,
    StoryWorkspaceEpisodeArtifactConsumer,
    StoryWorkspaceEpisodeArtifactManifestEntry,
    StoryWorkspaceEpisodeProducerAction,
    StoryWorkspaceEpisodeReviewScope,
    StoryWorkspaceEpisodeWorkflowCompletion,
    StoryWorkspaceEpisodeWorkflowFile,
)


RUN_ID = "run_0123456789abcdef0123456789abcdef"
EP02_ID = "2" * 32
MANIFEST_REVISION = "sha256:" + "f" * 64
NOW = datetime(2026, 8, 6, tzinfo=UTC)

_SPECS = {
    "episode-outline.md": StoryWorkspaceEpisodeProducerAction.PLAN_EPISODE,
    "script.md": StoryWorkspaceEpisodeProducerAction.WRITE_SCRIPT,
    "storyboard.yaml": StoryWorkspaceEpisodeProducerAction.REGENERATE_STORYBOARD,
    "prompts/": StoryWorkspaceEpisodeProducerAction.GENERATE_PROMPTS,
    "renders/": StoryWorkspaceEpisodeProducerAction.PREPARE_RENDER_GUIDE,
    "review-report.md": StoryWorkspaceEpisodeProducerAction.REVIEW_FULL_CHAIN,
}


def _artifact(key: str, *, revision_digit: str | None) -> object:
    available = revision_digit is not None
    consumers = [
        StoryWorkspaceEpisodeArtifactConsumer.NARRATIVE_WORKBENCH,
        StoryWorkspaceEpisodeArtifactConsumer.SHOT_INSPECTOR,
    ]
    if key == "episode-outline.md":
        consumers = [
            StoryWorkspaceEpisodeArtifactConsumer.EPISODE_OVERVIEW,
            StoryWorkspaceEpisodeArtifactConsumer.STORYLINE_NAVIGATOR,
            StoryWorkspaceEpisodeArtifactConsumer.NARRATIVE_WORKBENCH,
        ]
    elif key == "prompts/":
        consumers = [
            StoryWorkspaceEpisodeArtifactConsumer.SHOT_INSPECTOR,
            StoryWorkspaceEpisodeArtifactConsumer.PROMPT_VIEW,
        ]
    elif key == "renders/":
        consumers = [
            StoryWorkspaceEpisodeArtifactConsumer.SHOT_INSPECTOR,
            StoryWorkspaceEpisodeArtifactConsumer.RENDER_VIEW,
        ]
    elif key == "review-report.md":
        consumers = [
            StoryWorkspaceEpisodeArtifactConsumer.REVIEW_VIEW,
            StoryWorkspaceEpisodeArtifactConsumer.SHOT_INSPECTOR,
        ]
    return StoryWorkspaceEpisodeArtifactManifestEntry(
        relativeKey=key,
        availability=(
            StoryWorkspaceEpisodeArtifactAvailability.AVAILABLE
            if available
            else StoryWorkspaceEpisodeArtifactAvailability.NOT_GENERATED
        ),
        contentRevision=("sha256:" + revision_digit * 64) if available else None,
        mtime=NOW if available else None,
        size=10 if available else None,
        producerAction=_SPECS[key],
        consumers=consumers,
    )


def _surface(
    *,
    script_digit: str = "2",
    reviewed_script_digit: str = "2",
    storyboard_digit: str | None = None,
    prompts_digit: str | None = None,
) -> object:
    artifacts = [
        _artifact("episode-outline.md", revision_digit="1"),
        _artifact("script.md", revision_digit=script_digit),
        _artifact("storyboard.yaml", revision_digit=storyboard_digit),
        _artifact("prompts/", revision_digit=prompts_digit),
        _artifact("renders/", revision_digit=None),
        _artifact("review-report.md", revision_digit="6"),
    ]
    review = SimpleNamespace(
        scope=StoryWorkspaceEpisodeReviewScope.SCRIPT,
        overall_verdict="APPROVED",
        source_revisions=[
            SimpleNamespace(
                source_artifact="script.md",
                source_revision="sha256:" + reviewed_script_digit * 64,
            )
        ],
    )
    return SimpleNamespace(
        run_id=RUN_ID,
        opaque_episode_id=EP02_ID,
        manifest_revision=MANIFEST_REVISION,
        artifacts=artifacts,
        auxiliary=SimpleNamespace(review=review),
    )


def _facts_with_current_completions(
    surface: object,
    *actions: StoryWorkspaceEpisodeAction,
) -> StoryWorkspaceEpisodeWorkflowFile:
    resolver = StoryWorkspaceEpisodeNextActionResolver()
    facts = StoryWorkspaceEpisodeWorkflowFile(
        workflow_run_id=RUN_ID,
        episode_uid=EP02_ID,
        revision=0,
        completions=[],
        updated_at=NOW,
    )
    for action in actions:
        completion = StoryWorkspaceEpisodeWorkflowCompletion(
            action=action,
            input_revision=resolver.action_input_revision(action, surface, facts),
            manifest_revision=MANIFEST_REVISION,
            message_id="dream_agent_" + str(len(facts.completions) + 1) * 64,
            recorded_at=NOW,
        )
        facts = StoryWorkspaceEpisodeWorkflowFile(
            workflow_run_id=RUN_ID,
            episode_uid=EP02_ID,
            revision=facts.revision + 1,
            completions=[*facts.completions, completion],
            updated_at=NOW,
        )
    return facts


def _descriptor() -> StoryWorkspaceEpisodeDescriptor:
    return StoryWorkspaceEpisodeDescriptor(
        opaque_episode_id=EP02_ID,
        episode_number=2,
        display_label="EP02",
        relation="current",
    )


def test_latest_review_and_assets_enable_current_episode_storyboard() -> None:
    surface = _surface()
    facts = _facts_with_current_completions(
        surface,
        StoryWorkspaceEpisodeAction.REFRESH_ASSETS,
    )

    snapshot = StoryWorkspaceCurrentEpisodeActionSnapshotBuilder().build(
        surface=surface,
        facts=facts,
        current_episode=_descriptor(),
    )
    projection = StoryWorkspaceMultiEpisodeActionProjector.project(snapshot)

    assert snapshot.current_action is StoryWorkspaceEpisodeAction.REGENERATE_STORYBOARD
    assert snapshot.current_can_dispatch is True
    assert projection.action_options[0].label == "生成 EP02 详细分镜"
    assert projection.action_options[0].can_dispatch is True


def test_current_storyboard_enables_prompt_and_safe_update_option() -> None:
    surface = _surface(storyboard_digit="3")
    facts = _facts_with_current_completions(
        surface,
        StoryWorkspaceEpisodeAction.REFRESH_ASSETS,
        StoryWorkspaceEpisodeAction.REGENERATE_STORYBOARD,
    )

    snapshot = StoryWorkspaceCurrentEpisodeActionSnapshotBuilder().build(
        surface=surface,
        facts=facts,
        current_episode=_descriptor(),
    )
    projection = StoryWorkspaceMultiEpisodeActionProjector.project(snapshot)

    assert snapshot.current_action is StoryWorkspaceEpisodeAction.GENERATE_PROMPTS
    assert snapshot.storyboard_current is True
    assert snapshot.storyboard_can_regenerate is True
    assert [item.label for item in projection.action_options[:2]] == [
        "生成 EP02 Prompt 包",
        "基于最新剧本更新 EP02 详细分镜",
    ]


def test_new_script_revision_invalidates_review_and_hides_storyboard_update() -> None:
    surface = _surface(
        script_digit="9",
        reviewed_script_digit="2",
        storyboard_digit="3",
    )
    facts = _facts_with_current_completions(surface)

    snapshot = StoryWorkspaceCurrentEpisodeActionSnapshotBuilder().build(
        surface=surface,
        facts=facts,
        current_episode=_descriptor(),
    )
    projection = StoryWorkspaceMultiEpisodeActionProjector.project(snapshot)

    assert snapshot.current_action is StoryWorkspaceEpisodeAction.REVIEW_SCRIPT
    assert snapshot.storyboard_can_regenerate is False
    assert all("更新 EP02 详细分镜" not in item.label for item in projection.action_options)


def test_invalid_script_review_projects_a_recommended_repair_action() -> None:
    surface = _surface(storyboard_digit="3")
    report = next(
        item
        for item in surface.artifacts
        if item.relative_key == "review-report.md"
    )
    object.__setattr__(
        report,
        "availability",
        StoryWorkspaceEpisodeArtifactAvailability.INVALID,
    )
    object.__setattr__(report, "content_revision", None)
    object.__setattr__(report, "mtime", None)
    object.__setattr__(report, "size", None)
    surface.auxiliary.review = None
    facts = _facts_with_current_completions(surface)

    snapshot = StoryWorkspaceCurrentEpisodeActionSnapshotBuilder().build(
        surface=surface,
        facts=facts,
        current_episode=_descriptor(),
    )
    projection = StoryWorkspaceMultiEpisodeActionProjector.project(snapshot)

    assert snapshot.current_action is StoryWorkspaceEpisodeAction.REVIEW_SCRIPT
    assert snapshot.current_can_dispatch is True
    assert projection.recommended_action_id == projection.action_options[0].action_id
    assert projection.action_options[0].label == "审阅 EP02 剧本"
    assert projection.action_options[0].can_dispatch is True


def test_stale_asset_completion_requires_refresh_before_storyboard_update() -> None:
    original_surface = _surface(script_digit="2", reviewed_script_digit="2")
    facts = _facts_with_current_completions(
        original_surface,
        StoryWorkspaceEpisodeAction.REFRESH_ASSETS,
    )
    revised_surface = _surface(
        script_digit="8",
        reviewed_script_digit="8",
        storyboard_digit="3",
    )

    snapshot = StoryWorkspaceCurrentEpisodeActionSnapshotBuilder().build(
        surface=revised_surface,
        facts=facts,
        current_episode=_descriptor(),
    )

    assert snapshot.current_action is StoryWorkspaceEpisodeAction.REFRESH_ASSETS
    assert snapshot.storyboard_can_regenerate is False
