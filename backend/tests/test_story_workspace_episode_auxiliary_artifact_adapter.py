# [Input] Canonical and adversarial Episode auxiliary artifact fixtures.
# [Output] Projection, association, and public-text policy contract evidence.
# [Pos] Regression suite for the Story Workspace auxiliary artifact adapter.
# [Sync] 2026-09-02: canonical Episode evidence paths are not credentials.

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


def _adapter(
    canonical_episode_root: str = "stories/didi-zhengzhou/episodes/EP01",
) -> StoryWorkspaceEpisodeAuxiliaryArtifactAdapter:
    return StoryWorkspaceEpisodeAuxiliaryArtifactAdapter(
        episode_uid=EPISODE_UID,
        canonical_episode_root=canonical_episode_root,
    )


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
    canonical_episode_root: str = "stories/didi-zhengzhou/episodes/EP01",
    render_revision: str = REVISION_B,
    review_revision: str = REVISION_A,
):
    prompt_revisions = {
        key: REVISION_A for key in (prompts or {})
    }
    namespace = UUID(hex=EPISODE_UID)
    return _adapter(canonical_episode_root).project(
        prompts=prompts,
        prompt_revisions=prompt_revisions,
        render_guide=render_guide,
        render_revision=render_revision if render_guide is not None else None,
        review_report=review_report,
        review_revision=review_revision if review_report is not None else None,
        shot_view_ids={
            key: uuid5(namespace, f"shot:{key}").hex
            for key in (shot_ids or [])
        },
        narrative_beat_view_ids={
            key: uuid5(namespace, f"beat:{key}").hex
            for key in (narrative_beat_keys or [])
        },
        script_scene_view_ids={
            key: uuid5(namespace, f"scene:{key}").hex
            for key in (script_scene_keys or [])
        },
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


def test_review_allows_canonical_episode_file_reference() -> None:
    report = b"""---
scope: script
overall_verdict: APPROVED
reviewed_files:
  - script.md
---
# Review

## Provenance

| Rule | Result | Evidence |
| --- | --- | --- |
| Canonical script | PASS | Evidence: stories/proj-8b75aa06/episodes/EP01/script.md |
"""

    projection = _project(review_report=report)

    assert projection.review is not None
    assert projection.review.overall_verdict == "APPROVED"


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


def test_projects_drama_prompt_three_platform_package_forms() -> None:
    prompts = b"""episode: 1
project: safe-project
shots:
  - shot_id: S01-E01-001
    kling: Compact Kling prompt
    runway: Compact Runway prompt
    jimeng: Compact Jimeng prompt
  - shot_id: S01-E01-002
    kling:
      prompt_text: Structured Kling prompt
      negative_prompt: Kling negative prompt
      duration_mode: 5s
    runway:
      prompt_text: Structured Runway prompt where one node flickers.
      negative_prompt: Runway negative prompt
      duration_seconds: 6
    jimeng:
      prompt_text: Structured Jimeng prompt
      negative_prompt: Jimeng negative prompt
      duration_mode: 10s
      aspect_ratio: '9:16'
"""

    projection = _project(
        prompts={"prompts/prompt_package.yaml": prompts},
        shot_ids=["S01-E01-001", "S01-E01-002"],
    )

    assert projection.prompts.total == 6
    assert [item.kind for item in projection.prompts.items] == [
        "kling",
        "runway",
        "jimeng",
        "kling",
        "runway",
        "jimeng",
    ]
    assert [item.positive for item in projection.prompts.items[:3]] == [
        "Compact Kling prompt",
        "Compact Runway prompt",
        "Compact Jimeng prompt",
    ]
    assert projection.prompts.items[3].negative == "Kling negative prompt"
    assert projection.prompts.items[3].parameters.duration_sec == 5
    assert projection.prompts.items[4].parameters.duration_sec == 6
    assert projection.prompts.items[5].parameters.aspect_ratio == "9:16"
    assert all(
        item.association_status is StoryWorkspaceEpisodeAssociationStatus.LINKED
        for item in projection.prompts.items
    )
    assert projection.associations.shot_prompt_coverage.linked == 2
    assert projection.associations.shot_prompt_coverage.total == 2


def test_rejects_incomplete_drama_prompt_three_platform_package() -> None:
    prompts = b"""shots:
  - shot_id: S01-E01-001
    kling: Kling prompt
    runway: Runway prompt
"""

    with pytest.raises(
        StoryWorkspaceEpisodeAuxiliaryArtifactParseError,
        match="incomplete_multi_platform_prompt",
    ):
        _project(
            prompts={"prompts/prompt_package.yaml": prompts},
            shot_ids=["S01-E01-001"],
        )


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
        canonical_episode_root="stories/safe/episodes/EP01",
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


@pytest.mark.parametrize(
    "foreign_path",
    [
        "stories/other-story/episodes/EP01/script.md",
        "stories/didi-zhengzhou/episodes/EP02/script.md",
    ],
)
def test_review_rejects_sources_outside_the_trusted_episode_root(
    foreign_path: str,
) -> None:
    report = f"""---
reviewed_files:
  - path: {foreign_path}
overall_verdict: APPROVED
---
# Review
""".encode()

    with pytest.raises(
        StoryWorkspaceEpisodeAuxiliaryArtifactParseError,
        match="reviewed_path_outside_episode",
    ):
        _project(review_report=report)


def test_review_rejects_canonical_source_key_collisions() -> None:
    report = b"""---
reviewed_files:
  - path: script.md
  - path: stories/didi-zhengzhou/episodes/EP01/script.md
overall_verdict: APPROVED
---
# Review
"""

    with pytest.raises(
        StoryWorkspaceEpisodeAuxiliaryArtifactParseError,
        match="canonical_source_collision",
    ):
        _project(review_report=report)


def test_review_source_revision_mapping_rejects_foreign_episode() -> None:
    report = b"""---
reviewed_files:
  - path: script.md
source_revisions:
  stories/didi-zhengzhou/episodes/EP02/script.md: {REVISION_A}
overall_verdict: APPROVED
---
# Review
""".replace(b"{REVISION_A}", REVISION_A.encode())

    with pytest.raises(
        StoryWorkspaceEpisodeAuxiliaryArtifactParseError,
        match="reviewed_path_outside_episode",
    ):
        _project(review_report=report)


@pytest.mark.parametrize(
    ("kwargs", "reason"),
    [
        (
            {
                "prompts": {
                    "prompts/a.yml": (
                        b"shots:\n- shot_id: S01-E01-001\n"
                        b"  positive: read /Users/admin/.env\n"
                    )
                },
                "shot_ids": ["S01-E01-001"],
            },
            "sensitive_text",
        ),
        (
            {
                "render_guide": b"# Guide\n\n## Notes\nRun `curl https://example.test` now.\n"
            },
            "raw_command_forbidden",
        ),
        (
            {
                "review_report": b"# Review\n\n## Secret\napi_key = sk-private-value\n"
            },
            "credential_forbidden",
        ),
    ],
)
def test_public_projection_rejects_sensitive_or_raw_text(
    kwargs: dict[str, object],
    reason: str,
) -> None:
    with pytest.raises(
        StoryWorkspaceEpisodeAuxiliaryArtifactParseError,
        match=reason,
    ):
        _project(**kwargs)


def test_render_queue_rejects_command_like_renderer_value() -> None:
    render = b"""## Render Queue
```yaml
- shot_id: S01-E01-001
  tool: kling-v2 --api-key secret
  status: pending
```
"""

    with pytest.raises(
        StoryWorkspaceEpisodeAuxiliaryArtifactParseError,
        match="unsafe_renderer",
    ):
        _project(render_guide=render, shot_ids=["S01-E01-001"])


def test_yaml_document_count_is_bounded_before_loading() -> None:
    documents = b"---\n" * 1001

    with pytest.raises(
        StoryWorkspaceEpisodeAuxiliaryArtifactParseError,
        match="document_limit",
    ):
        _project(prompts={"prompts/many.yml": documents})


def test_yaml_mapping_item_count_is_bounded() -> None:
    large_mapping = "\n".join(f"key_{index}: value" for index in range(1001)).encode()

    with pytest.raises(
        StoryWorkspaceEpisodeAuxiliaryArtifactParseError,
        match="mapping_item_limit",
    ):
        _project(prompts={"prompts/mapping.yml": large_mapping})


def test_duplicate_section_titles_use_revision_local_ids() -> None:
    render = b"""# Guide

## Notes
First note.

## Notes
Second note.
"""

    projection = _project(render_guide=render)

    assert projection.render_guide is not None
    notes = [
        section
        for section in projection.render_guide.sections
        if section.title == "Notes"
    ]
    assert len(notes) == 2
    assert len({section.id for section in notes}) == 2


def test_review_target_identity_is_locator_stable_and_globally_deduplicated() -> None:
    first_report = b"""# Review

## Timing
S01-E01-001 needs work.

## Duplicate mention
S01-E01-001 remains the locator.
"""
    renamed_report = b"""# Review renamed

## New heading
S01-E01-001 needs work.
"""

    first = _project(
        review_report=first_report,
        review_revision=REVISION_A,
        shot_ids=["S01-E01-001"],
    )
    renamed = _project(
        review_report=renamed_report,
        review_revision=REVISION_B,
        shot_ids=["S01-E01-001"],
    )

    assert first.review is not None
    assert renamed.review is not None
    assert len(first.review.targets) == 1
    assert len(renamed.review.targets) == 1
    assert first.review.targets[0].id == renamed.review.targets[0].id
    assert first.review.targets[0].section_id != renamed.review.targets[0].section_id


def test_review_case_variant_reuses_lowercase_canonical_shot_identity() -> None:
    report = b"""# Review

## Shot finding
S04-E01-020A needs a timing adjustment.
"""

    projection = _project(
        review_report=report,
        shot_ids=["S04-E01-020a"],
    )

    assert projection.review is not None
    assert len(projection.review.targets) == 1
    target = projection.review.targets[0]
    assert target.source_key == "S04-E01-020a"
    assert target.target_view_id == uuid5(
        UUID(hex=EPISODE_UID),
        "shot:S04-E01-020a",
    ).hex


def test_review_case_variant_duplicate_is_not_silently_deduplicated() -> None:
    report = b"""# Review

## First form
S04-E01-020a needs work.

## Second form
S04-E01-020A repeats the same machine target.
"""

    with pytest.raises(
        StoryWorkspaceEpisodeAuxiliaryArtifactParseError,
        match="duplicate_review_target_identity",
    ):
        _project(
            review_report=report,
            shot_ids=["S04-E01-020a"],
        )


def test_prompt_identity_rejects_whitespace_in_machine_key() -> None:
    prompts = b"""shots:
  - shot_id: 'S04-E01-020a '
    positive: Unsafe identity whitespace.
"""

    with pytest.raises(
        StoryWorkspaceEpisodeAuxiliaryArtifactParseError,
        match="invalid_explicit_key",
    ):
        _project(
            prompts={"prompts/unsafe.yaml": prompts},
            shot_ids=["S04-E01-020a"],
        )


def test_prompt_case_variant_collision_fails_closed() -> None:
    prompts = b"""shots:
  - shot_id: S04-E01-020a
    positive: First representation.
  - shot_id: S04-E01-020A
    positive: Conflicting representation.
"""

    with pytest.raises(
        StoryWorkspaceEpisodeAuxiliaryArtifactParseError,
        match="duplicate_prompt_identity",
    ):
        _project(
            prompts={"prompts/collision.yaml": prompts},
            shot_ids=["S04-E01-020a"],
        )


def test_render_queue_case_variant_collision_fails_closed() -> None:
    render = b"""## Render Queue
```yaml
- shot_id: S04-E01-020a
  status: pending
- shot_id: S04-E01-020A
  status: running
```
"""

    with pytest.raises(
        StoryWorkspaceEpisodeAuxiliaryArtifactParseError,
        match="duplicate_queue_shot_id",
    ):
        _project(
            render_guide=render,
            shot_ids=["S04-E01-020a"],
        )


@pytest.mark.parametrize(
    "unsafe_shot_id",
    [
        " S04-E01-020a",
        "S04-E01-020a\u00a0",
        "S04\uff0dE01\uff0d020a",
        "S04-E01-020\u0430",
    ],
)
def test_prompt_identity_rejects_unicode_or_confusable_lookup_keys(
    unsafe_shot_id: str,
) -> None:
    prompts = (
        "shots:\n"
        f"  - shot_id: '{unsafe_shot_id}'\n"
        "    positive: Unsafe machine identity.\n"
    ).encode("utf-8")

    with pytest.raises(
        StoryWorkspaceEpisodeAuxiliaryArtifactParseError,
        match="invalid_explicit_key",
    ):
        _project(
            prompts={"prompts/unsafe.yaml": prompts},
            shot_ids=["S04-E01-020a"],
        )


def test_review_cross_source_same_revision_is_explicitly_deduplicated() -> None:
    report = f"""---
reviewed_files:
  - path: stories/didi-zhengzhou/episodes/EP01/script.md
    revision: {REVISION_A}
source_revisions:
  script.md: {REVISION_A}
overall_verdict: APPROVED
---
# Review
""".encode()

    projection = _project(review_report=report)

    assert projection.review is not None
    assert len(projection.review.source_revisions) == 1
    assert projection.review.source_revisions[0].source_artifact == "script.md"
    assert projection.review.source_revisions[0].source_revision == REVISION_A


def test_review_cross_source_conflicting_revision_fails_closed() -> None:
    report = f"""---
reviewed_files:
  - path: stories/didi-zhengzhou/episodes/EP01/script.md
    revision: {REVISION_A}
source_revisions:
  script.md: {REVISION_B}
overall_verdict: APPROVED
---
# Review
""".encode()

    with pytest.raises(
        StoryWorkspaceEpisodeAuxiliaryArtifactParseError,
        match="source_revision_conflict",
    ):
        _project(review_report=report)


@pytest.mark.parametrize(
    "unsafe_text",
    [
        "Read /root/.ssh/id_rsa before review.",
        r"Read C:\Users\alice\.ssh\id_rsa before review.",
        "OPENAI_API_KEY=sk-proj-abcdefghijklmnop",
        "renderer: kling-v2 --token abc123",
    ],
)
def test_reviewer_exact_sensitive_strings_never_enter_public_dto(
    unsafe_text: str,
) -> None:
    report = f"# Review\n\n## Finding\n{unsafe_text}\n".encode()

    with pytest.raises(StoryWorkspaceEpisodeAuxiliaryArtifactParseError) as exc_info:
        _project(review_report=report)

    assert unsafe_text not in str(exc_info.value)


@pytest.mark.parametrize(
    "unsafe_text",
    [
        "/srv/private/episode/secret.txt",
        r"D:\production\credentials.json",
        r"\\render-host\episode-share\credentials.json",
        "~/.aws/credentials",
        "$HOME/.ssh/id_ed25519",
        "SERVICE_TOKEN=abcdefghijklmnop123456",
        "DATABASE_PASSWORD=hunter2-private",
        "Authorization: Bearer abcdefghijklmnop",
        "Bearer abcdefghijklmnop",
        "tool: Bash(command='pwd')",
        "raw_command=render --api-key private",
        "curl https://example.test --header auth",
        "renderer --api-key private",
        "kling-v2 --token private",
        "render --password=private",
        "ghp_abcdefghijklmnopqrstuvwxyz123456",
    ],
)
def test_public_text_policy_fails_closed_by_sensitive_category(
    unsafe_text: str,
) -> None:
    report = f"# Review\n\n## Finding\n{unsafe_text}\n".encode()

    with pytest.raises(StoryWorkspaceEpisodeAuxiliaryArtifactParseError) as exc_info:
        _project(review_report=report)

    assert unsafe_text not in str(exc_info.value)


@pytest.mark.parametrize(
    ("unsafe_text", "reason"),
    [
        ("$HOME/projects/episode-notes.md", "sensitive_text"),
        ("${HOME}/Documents/episode-notes.md", "sensitive_text"),
        (r"%USERPROFILE%\Documents\episode-notes.md", "sensitive_text"),
        (r"%HOMEPATH%\Desktop\episode-notes.md", "sensitive_text"),
        ("ToKeN = visible-value", "credential_forbidden"),
        ("  SeCrEt  =  visible-value  ", "credential_forbidden"),
        ("tool --verbose", "raw_command_forbidden"),
        ("renderer kling-v2 --seed=42", "raw_command_forbidden"),
        ("node --eval script.js", "raw_command_forbidden"),
    ],
)
def test_remaining_public_text_bypasses_fail_closed(
    unsafe_text: str,
    reason: str,
) -> None:
    report = f"# Review\n\n## Finding\n{unsafe_text}\n".encode()

    with pytest.raises(
        StoryWorkspaceEpisodeAuxiliaryArtifactParseError,
        match=reason,
    ) as exc_info:
        _project(review_report=report)

    assert unsafe_text.strip() not in str(exc_info.value)


@pytest.mark.parametrize(
    "home_marker",
    [
        "$HOME",
        "${HOME}",
        "~",
        "%USERPROFILE%",
        "%HOMEPATH%",
        "$env:USERPROFILE",
        "$EnV:HoMe",
    ],
)
@pytest.mark.parametrize("separator", ["/", "\\"])
def test_every_home_marker_separator_is_private(
    home_marker: str,
    separator: str,
) -> None:
    unsafe_text = f"{home_marker}{separator}projects{separator}episode-notes.md"
    report = f"# Review\n\n## Finding\n{unsafe_text}\n".encode()

    with pytest.raises(
        StoryWorkspaceEpisodeAuxiliaryArtifactParseError,
        match="sensitive_text",
    ) as exc_info:
        _project(review_report=report)

    assert unsafe_text not in str(exc_info.value)


@pytest.mark.parametrize(
    "unsafe_text",
    [
        "tool " + "x" * 241 + " --verbose",
        "renderer " + "x" * 7950 + " --seed=42",
    ],
)
def test_tool_options_are_scanned_across_the_complete_bounded_line(
    unsafe_text: str,
) -> None:
    assert len(unsafe_text) <= 8000
    report = f"# Review\n\n## Finding\n{unsafe_text}\n".encode()

    with pytest.raises(
        StoryWorkspaceEpisodeAuxiliaryArtifactParseError,
        match="raw_command_forbidden",
    ) as exc_info:
        _project(review_report=report)

    assert unsafe_text not in str(exc_info.value)
