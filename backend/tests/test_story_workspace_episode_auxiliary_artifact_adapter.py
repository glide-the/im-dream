"""Safe Episode prompt/render/review projection contract tests."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid5

import pytest
import yaml

from services.story_workspace.episode_auxiliary_artifact_adapter import (
    STORY_WORKSPACE_EPISODE_AUXILIARY_YAML_MAX_BYTES,
    StoryWorkspaceEpisodeAuxiliaryArtifactAdapter,
    StoryWorkspaceEpisodeAuxiliaryArtifactParseError,
)
from story_workspace.contracts import (
    StoryWorkspaceEpisodeAssociationStatus,
    StoryWorkspaceEpisodeMetricAvailability,
    StoryWorkspaceEpisodeReviewScope,
    StoryWorkspaceEpisodeReviewTargetKind,
)


EPISODE_UID = "1234567890abcdef1234567890abcdef"
REVISION_A = "sha256:" + "a" * 64
REVISION_B = "sha256:" + "b" * 64
MANIFEST_REVISION = "sha256:" + "c" * 64
VENDOR_EPISODE = (
    Path(__file__).resolve().parents[2]
    / "vendor"
    / "drama-forge"
    / "drama-forge"
    / "stories"
    / "didi-zhengzhou"
    / "episodes"
    / "EP01"
)


def _adapter() -> StoryWorkspaceEpisodeAuxiliaryArtifactAdapter:
    return StoryWorkspaceEpisodeAuxiliaryArtifactAdapter(episode_uid=EPISODE_UID)


def _project(
    *,
    prompts: dict[str, bytes] | None = None,
    render_guide: bytes | None = None,
    review_report: bytes | None = None,
    shot_ids: list[str] | None = None,
    narrative_beat_keys: list[str] | None = None,
    script_scene_keys: list[str] | None = None,
    prompt_cursor: str | None = None,
    render_queue_cursor: str | None = None,
    page_limit: int = 100,
    manifest_revision: str = MANIFEST_REVISION,
):
    prompt_revisions = {
        key: REVISION_A for key in (prompts or {})
    }
    return _adapter().project(
        prompts=prompts,
        prompt_revisions=prompt_revisions,
        render_guide=render_guide,
        render_revision=REVISION_B if render_guide is not None else None,
        review_report=review_report,
        review_revision=REVISION_A if review_report is not None else None,
        shot_ids=shot_ids or [],
        narrative_beat_keys=narrative_beat_keys or [],
        script_scene_keys=script_scene_keys or [],
        manifest_revision=manifest_revision,
        prompt_cursor=prompt_cursor,
        render_queue_cursor=render_queue_cursor,
        page_limit=page_limit,
    )


def _vendor_shot_ids() -> list[str]:
    documents = list(
        yaml.safe_load_all((VENDOR_EPISODE / "storyboard.yaml").read_text())
    )
    return [
        str(shot["shot_id"])
        for document in documents
        for shot in document.get("shots", [])
    ]


def test_projects_real_didi_prompts_queue_and_script_scoped_review() -> None:
    prompt_path = VENDOR_EPISODE / "prompts" / "ep001-prompts.yml"
    shot_ids = _vendor_shot_ids()

    projection = _project(
        prompts={"prompts/ep001-prompts.yml": prompt_path.read_bytes()},
        render_guide=(VENDOR_EPISODE / "renders" / "render-guide.md").read_bytes(),
        review_report=(VENDOR_EPISODE / "review-report.md").read_bytes(),
        shot_ids=shot_ids,
    )

    assert len(shot_ids) == 45
    assert projection.prompts.total == 45
    assert len(projection.prompts.items) == 45
    assert projection.render_guide is not None
    assert projection.render_guide.queue.total == 45
    assert len(projection.render_guide.queue.items) == 45
    assert all(
        prompt.association_status is StoryWorkspaceEpisodeAssociationStatus.LINKED
        for prompt in projection.prompts.items
    )
    assert all(
        entry.association_status is StoryWorkspaceEpisodeAssociationStatus.LINKED
        for entry in projection.render_guide.queue.items
    )
    assert all(UUID(hex=prompt.id) for prompt in projection.prompts.items)
    first_queue = projection.render_guide.queue.items[0]
    assert first_queue.id == uuid5(
        UUID(hex=EPISODE_UID),
        f"render-queue:{first_queue.shot_id}",
    ).hex
    assert projection.associations.shot_prompt_coverage.linked == 45
    assert projection.associations.shot_prompt_coverage.total == 45
    assert projection.associations.shot_render_queue_coverage.linked == 45
    assert projection.associations.shot_render_queue_coverage.total == 45
    assert projection.associations.orphan_prompts == []
    assert projection.associations.orphan_queue_entries == []
    assert projection.associations.duplicate_queue_shot_ids == []

    review = projection.review
    assert review is not None
    assert review.scope is StoryWorkspaceEpisodeReviewScope.SCRIPT
    assert review.overall_verdict == "CONDITIONAL_APPROVAL"
    assert review.reviewed_artifacts == ["script.md"]
    assert review.source_artifact == "review-report.md"
    assert review.source_revision == REVISION_A
    assert review.targets == []

    payload = projection.model_dump(by_alias=True)
    assert "promptRenderCoverage" not in payload["associations"]
    assert "promptRef" not in str(payload)
    assert "/Users/" not in str(payload)


def test_missing_auxiliary_artifacts_are_a_normal_empty_projection() -> None:
    projection = _project()

    assert projection.prompts.items == []
    assert projection.prompts.total == 0
    assert projection.prompts.next_cursor is None
    assert projection.render_guide is None
    assert projection.review is None
    assert projection.associations.total_prompts == 0
    assert projection.associations.total_queue_entries == 0
    assert projection.associations.shot_prompt_coverage.availability is (
        StoryWorkspaceEpisodeMetricAvailability.UNAVAILABLE
    )
    assert projection.associations.shot_render_queue_coverage.availability is (
        StoryWorkspaceEpisodeMetricAvailability.UNAVAILABLE
    )


def test_supports_multi_document_files_and_multiple_explicit_prompt_kinds() -> None:
    prompts = b"""meta:
  episode: EP01
shots:
  - shot_id: S01-E01-001
    prompt_kind: image
    positive: A still establishing frame
    negative: watermark
---
shots:
  - shot_id: S01-E01-001
    prompt_kind: video
    positive: A slow push in
    params:
      duration: 3
      camera_motion: push in
      raw_command: must-not-leak
"""

    projection = _project(
        prompts={"prompts/multi.yaml": prompts},
        shot_ids=["S01-E01-001"],
    )

    assert projection.prompts.total == 2
    assert [item.kind for item in projection.prompts.items] == ["image", "video"]
    assert len({item.id for item in projection.prompts.items}) == 2
    assert {item.shot_id for item in projection.prompts.items} == {"S01-E01-001"}
    assert projection.associations.shot_prompt_coverage.linked == 1
    assert projection.associations.total_prompts == 2
    assert "rawCommand" not in str(projection.model_dump(by_alias=True))


def test_orphans_are_reported_without_positional_or_prompt_render_pairing() -> None:
    prompts = b"""shots:
  - shot_id: S01-E01-001
    positive: Known shot
  - shot_id: ORPHAN-E01-999
    positive: Unknown shot
"""
    render = b"""# Guide

## Render Queue

```yaml
- shot_id: S01-E01-001
  status: pending
- shot_id: ORPHAN-E01-999
  status: pending
```
"""

    projection = _project(
        prompts={"prompts/prompts.yml": prompts},
        render_guide=render,
        shot_ids=["S01-E01-001"],
    )

    assert projection.associations.shot_prompt_coverage.linked == 1
    assert projection.associations.shot_render_queue_coverage.linked == 1
    assert projection.associations.orphan_prompts == [
        "prompt:ORPHAN-E01-999:default"
    ]
    assert projection.associations.orphan_queue_entries == [
        "render-queue:ORPHAN-E01-999"
    ]
    assert projection.prompts.items[1].association_status is (
        StoryWorkspaceEpisodeAssociationStatus.ORPHAN
    )
    assert projection.render_guide is not None
    assert projection.render_guide.queue.items[1].association_status is (
        StoryWorkspaceEpisodeAssociationStatus.ORPHAN
    )


def test_render_queue_duplicate_shot_id_invalidates_the_artifact() -> None:
    render = b"""## Render Queue
```yaml
- shot_id: S01-E01-001
  status: pending
- shot_id: S01-E01-001
  status: running
```
"""

    with pytest.raises(
        StoryWorkspaceEpisodeAuxiliaryArtifactParseError,
        match="duplicate_queue_shot_id",
    ) as exc_info:
        _project(render_guide=render, shot_ids=["S01-E01-001"])

    assert exc_info.value.artifact == "renders/render-guide.md"
    assert exc_info.value.reason == "duplicate_queue_shot_id"


def test_cursor_is_opaque_bounded_and_revision_bound() -> None:
    prompts = b"""shots:
  - shot_id: S01-E01-001
    positive: One
  - shot_id: S01-E01-002
    positive: Two
  - shot_id: S01-E01-003
    positive: Three
"""
    kwargs = {
        "prompts": {"prompts/prompts.yml": prompts},
        "shot_ids": ["S01-E01-001", "S01-E01-002", "S01-E01-003"],
        "page_limit": 1,
    }
    first = _project(**kwargs)

    assert len(first.prompts.items) == 1
    assert first.prompts.total == 3
    assert first.prompts.next_cursor is not None
    assert "S01-E01" not in first.prompts.next_cursor
    second = _project(prompt_cursor=first.prompts.next_cursor, **kwargs)
    assert len(second.prompts.items) == 1
    assert second.prompts.items[0].shot_id != first.prompts.items[0].shot_id

    with pytest.raises(
        StoryWorkspaceEpisodeAuxiliaryArtifactParseError,
        match="stale_cursor",
    ):
        _project(
            prompt_cursor=first.prompts.next_cursor,
            manifest_revision="sha256:" + "d" * 64,
            **kwargs,
        )

    with pytest.raises(
        StoryWorkspaceEpisodeAuxiliaryArtifactParseError,
        match="invalid_cursor",
    ):
        _project(prompt_cursor=first.prompts.next_cursor + "x", **kwargs)

    with pytest.raises(ValueError, match="less than or equal to 100"):
        _project(page_limit=101)


def test_review_targets_require_explicit_machine_keys() -> None:
    report = b"""---
reviewed_files:
  - path: stories/safe/episodes/EP01/script.md
    revision: sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
  - path: stories/safe/episodes/EP01/storyboard.yaml
    revision: sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
overall_verdict: APPROVED
scope: full-chain
---
# Review

## Explicit findings
SC-01 and S01 require timing alignment at S01-E01-001.

## Narrative prose
The station opening resembles the first scene, but contains no machine key.
"""

    projection = _project(
        review_report=report,
        shot_ids=["S01-E01-001"],
        narrative_beat_keys=["SC-01"],
        script_scene_keys=["S01"],
    )
    review = projection.review
    assert review is not None
    assert review.scope is StoryWorkspaceEpisodeReviewScope.FULL_CHAIN
    assert [target.kind for target in review.targets] == [
        StoryWorkspaceEpisodeReviewTargetKind.NARRATIVE_BEAT,
        StoryWorkspaceEpisodeReviewTargetKind.SCRIPT_SCENE,
        StoryWorkspaceEpisodeReviewTargetKind.SHOT,
    ]
    assert [target.source_key for target in review.targets] == [
        "SC-01",
        "S01",
        "S01-E01-001",
    ]
    assert all(
        target.association_status is StoryWorkspaceEpisodeAssociationStatus.LINKED
        for target in review.targets
    )
    assert review.reviewed_artifacts == ["script.md", "storyboard.yaml"]
    assert review.source_revisions[0].source_artifact == "script.md"
    assert len(review.sections) == 3


@pytest.mark.parametrize(
    ("prompts", "path", "reason"),
    [
        (b"shots: !!python/object/apply:os.system ['id']\n", "prompts/a.yml", "invalid_yaml"),
        (
            b"shared: &shared hacked\nshots:\n- shot_id: S01-E01-001\n  positive: *shared\n",
            "prompts/a.yml",
            "yaml_alias_forbidden",
        ),
        (
            b"shots:\n- shot_id: S01-E01-001\n  positive: <script>alert(1)</script>\n",
            "prompts/a.yml",
            "html_forbidden",
        ),
        (b"shots: []\n", "prompts/../evil.yml", "invalid_artifact_path"),
        (
            b"x" * (STORY_WORKSPACE_EPISODE_AUXILIARY_YAML_MAX_BYTES + 1),
            "prompts/a.yml",
            "byte_limit",
        ),
    ],
)
def test_rejects_malicious_or_unbounded_prompt_inputs(
    prompts: bytes,
    path: str,
    reason: str,
) -> None:
    with pytest.raises(
        StoryWorkspaceEpisodeAuxiliaryArtifactParseError,
        match=reason,
    ) as exc_info:
        _project(prompts={path: prompts})

    assert exc_info.value.reason == reason
    assert str(prompts[:30]) not in str(exc_info.value)


@pytest.mark.parametrize(
    ("field", "content", "reason"),
    [
        (
            "render_guide",
            b"## Render Queue\n<script>alert(1)</script>\n",
            "html_forbidden",
        ),
        (
            "review_report",
            b"---\noverall_verdict: APPROVED\n---\n# Review\n<img src=x>\n",
            "html_forbidden",
        ),
    ],
)
def test_rejects_html_in_markdown_auxiliary_artifacts(
    field: str,
    content: bytes,
    reason: str,
) -> None:
    with pytest.raises(
        StoryWorkspaceEpisodeAuxiliaryArtifactParseError,
        match=reason,
    ):
        _project(**{field: content})
