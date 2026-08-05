"""Safe Episode outline/script/storyboard projection contract tests."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

import pytest

from services.story_workspace.episode_artifact_adapter import (
    STORY_WORKSPACE_EPISODE_MARKDOWN_MAX_BYTES,
    StoryWorkspaceEpisodeArtifactAdapter,
    StoryWorkspaceEpisodeArtifactParseError,
)
from story_workspace.contracts import (
    StoryWorkspaceEpisodeAssociationStatus,
    StoryWorkspaceEpisodeDialogueType,
    StoryWorkspaceEpisodeMetricAvailability,
    StoryWorkspaceEpisodeSourceArtifact,
)


EPISODE_UID = "1234567890abcdef1234567890abcdef"
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
VENDOR_STORIES = VENDOR_EPISODE.parents[2]


OUTLINE_WITH_BEATS = b"""---
series: Safe Series
episode: 1
title: Pilot
generated_from: master-outline@v2
character_beats:
  - beat_id: ARC-MC-01-SETUP
    character_id: mc-01
    action: setup
---
# Safe Series

## Story Goals
- Establish the driver
- Reveal the phone

## Core Conflict
**One-line conflict**: The driver needs money but distrusts the phone.

## Cliffhanger
The phone offers a hidden mission.

## Scene Sequence

### SC-01. Station [scene-station]

| Property | Value |
| --- | --- |
| **Narrative Function** | Setup |

**Scene Summary**:
The driver discovers the phone.

**Scene Goals**:
- Establish the debt.

**Key Dialogue Beats**:
1. Driver: Is this real?

### SC-02. Car [scene-car]

**Narrative Function**: Turn

**Scene Summary**:
The first passenger leaves a bag.
"""


SCRIPT_WITH_SCENES = b"""---
series: Safe Series
episode: 1
title: Pilot
version: 7
generated_from: episode-outline@v2
---
# Pilot

S01. Station [scene-station] - Night - Exterior

[The driver finds a phone.]

CAM: CU | PUSH_IN | phone | 3.0

Driver (quietly)
Is this real?

S02. Car [scene-car] - Night - Interior

narrative_beat_ref: SC-02

[A passenger leaves a bag.]

Passenger
Thank you.
"""


STORYBOARD_WITH_EXPLICIT_LINKS = b"""---
episode: EP01
total_shots: 3
generated_from: script@v1
---
shots:
  - shot_id: S01-E01-001
    scene_ref: scene-station
    shot_type: CU
    visual: Driver finds the phone.
    camera:
      movement: PUSH_IN
    timing:
      duration_sec: 3.0
  - shot_id: SUP-E01-001
    scene_ref: scene-station
    shot_type: ECU
    visual: A reaction insert.
  - shot_id: CUSTOM-E01-001
    scene_ref: scene-car
    script_scene_ref: S02
    narrative_beat_ref: SC-02
    shot_type: WS
    visual: The passenger exits.
    characters:
      - ref: passenger-01
        display_name: Passenger
        depth_plane: back
        action: Exits the car.
        emotion: Guarded
    dialogue:
      - speaker: passenger-01
        line: Thank you.
        type: spoken
"""


def _adapter() -> StoryWorkspaceEpisodeArtifactAdapter:
    return StoryWorkspaceEpisodeArtifactAdapter(episode_uid=EPISODE_UID)


def test_projects_explicit_outline_beats_script_scenes_and_shot_links() -> None:
    projection = _adapter().project(
        outline=OUTLINE_WITH_BEATS,
        script=SCRIPT_WITH_SCENES,
        storyboard=STORYBOARD_WITH_EXPLICIT_LINKS,
        outline_revision="sha256:" + "1" * 64,
        script_revision="sha256:" + "2" * 64,
        storyboard_revision="sha256:" + "3" * 64,
    )

    assert projection.episode_id != EPISODE_UID
    assert UUID(hex=projection.episode_id)
    assert UUID(hex=projection.story_arc_id)
    assert projection.overview.title == "Pilot"
    assert projection.overview.series == "Safe Series"
    assert projection.overview.story_goals == [
        "Establish the driver",
        "Reveal the phone",
    ]
    assert projection.overview.core_conflict == (
        "The driver needs money but distrusts the phone."
    )
    assert projection.overview.hook == "The phone offers a hidden mission."
    assert projection.overview.source_artifact is (
        StoryWorkspaceEpisodeSourceArtifact.EPISODE_OUTLINE
    )
    assert projection.overview.source_revision == "sha256:" + "1" * 64
    assert projection.overview.generated_from == "master-outline@v2"
    assert [beat.source_key for beat in projection.narrative_beats] == [
        "SC-01",
        "SC-02",
    ]
    assert projection.narrative_beats[0].narrative_function == "Setup"
    assert projection.narrative_beats[0].summary == (
        "The driver discovers the phone."
    )
    assert projection.narrative_beats[0].scene_goals == ["Establish the debt."]
    assert projection.narrative_beats[0].key_dialogue_beats == [
        "Driver: Is this real?"
    ]
    assert [scene.source_key for scene in projection.scenes] == ["S01", "S02"]
    assert projection.scenes[0].association_status is (
        StoryWorkspaceEpisodeAssociationStatus.LINKED
    )
    assert projection.scenes[0].narrative_beat_id == projection.narrative_beats[0].id
    assert projection.scenes[0].actions == ["The driver finds a phone."]
    assert projection.scenes[0].camera_cues == ["CU | PUSH_IN | phone | 3.0"]
    assert projection.scenes[0].dialogue[0].speaker == "Driver"
    assert projection.scenes[0].dialogue[0].text == "Is this real?"
    assert projection.scenes[0].source_artifact is (
        StoryWorkspaceEpisodeSourceArtifact.SCRIPT
    )
    assert projection.scenes[0].source_revision == "sha256:" + "2" * 64
    assert projection.scenes[0].generated_from == "episode-outline@v2"

    regular, supplemental, explicit = projection.shots
    assert regular.association_status is StoryWorkspaceEpisodeAssociationStatus.LINKED
    assert regular.script_scene_id == projection.scenes[0].id
    assert regular.asset_scene_ref == "scene-station"
    assert supplemental.association_status is (
        StoryWorkspaceEpisodeAssociationStatus.UNLINKED
    )
    assert supplemental.script_scene_id is None
    assert explicit.association_status is StoryWorkspaceEpisodeAssociationStatus.LINKED
    assert explicit.script_scene_id == projection.scenes[1].id
    assert explicit.narrative_beat_id == projection.narrative_beats[1].id
    assert explicit.source_artifact is StoryWorkspaceEpisodeSourceArtifact.STORYBOARD
    assert explicit.source_revision == "sha256:" + "3" * 64
    assert explicit.generated_from == "script@v1"
    assert explicit.characters[0].ref == "passenger-01"
    assert explicit.characters[0].display_name == "Passenger"
    assert explicit.characters[0].depth_plane.value == "back"
    assert explicit.characters[0].action == "Exits the car."
    assert explicit.characters[0].emotion == "Guarded"
    assert explicit.dialogue[0].speaker == "passenger-01"
    assert explicit.dialogue[0].line == "Thank you."
    assert explicit.dialogue[0].type is StoryWorkspaceEpisodeDialogueType.SPOKEN

    assert projection.associations.beat_scene_coverage.linked == 2
    assert projection.associations.beat_scene_coverage.total == 2
    assert projection.associations.beat_scene_coverage.ratio == 1.0
    assert projection.associations.scene_shot_coverage.linked == 2
    assert projection.associations.scene_shot_coverage.total == 3
    assert projection.associations.scene_shot_coverage.ratio == pytest.approx(2 / 3)
    assert projection.associations.missing_links == ["shot:SUP-E01-001:script_scene"]
    assert projection.associations.orphan_artifacts == []


def test_real_vendor_episode_has_no_invented_narrative_beats() -> None:
    projection = _adapter().project(
        outline=(VENDOR_EPISODE / "episode-outline.md").read_bytes(),
        script=(VENDOR_EPISODE / "script.md").read_bytes(),
        storyboard=(VENDOR_EPISODE / "storyboard.yaml").read_bytes(),
    )

    assert projection.narrative_beats == []
    assert len(projection.overview.character_beats) == 1
    assert len(projection.scenes) == 2
    assert len(projection.shots) == 45
    assert len({shot.shot_id for shot in projection.shots}) == 45
    assert sum(
        shot.association_status is StoryWorkspaceEpisodeAssociationStatus.LINKED
        for shot in projection.shots
    ) == 31
    assert sum(
        shot.association_status is StoryWorkspaceEpisodeAssociationStatus.UNLINKED
        for shot in projection.shots
    ) == 14
    assert projection.associations.beat_scene_coverage.availability is (
        StoryWorkspaceEpisodeMetricAvailability.AVAILABLE
    )
    assert projection.associations.beat_scene_coverage.ratio == 0.0
    assert projection.associations.scene_shot_coverage.linked == 31
    assert projection.associations.scene_shot_coverage.total == 45
    assert len(projection.associations.missing_links) == 16
    assert projection.associations.orphan_artifacts == []


def test_storyboard_only_treats_regular_prefix_as_missing_not_orphan() -> None:
    projection = _adapter().project(
        outline=None,
        script=None,
        storyboard=(VENDOR_EPISODE / "storyboard.yaml").read_bytes(),
    )

    assert len(projection.shots) == 45
    assert all(
        shot.association_status is StoryWorkspaceEpisodeAssociationStatus.UNLINKED
        for shot in projection.shots
    )
    assert len(projection.associations.missing_links) == 45
    assert projection.associations.orphan_artifacts == []


def test_real_ep21_preserves_canonical_dialogue_and_character_fields() -> None:
    episode = VENDOR_STORIES / "didi-zhengzhou" / "episodes" / "EP21"
    projection = _adapter().project(
        outline=(episode / "episode-outline.md").read_bytes(),
        script=(episode / "script.md").read_bytes(),
        storyboard=(episode / "storyboard.yaml").read_bytes(),
    )

    assert len(projection.shots) == 52
    assert sum(len(shot.dialogue) for shot in projection.shots) == 11
    assert any(character.emotion for shot in projection.shots for character in shot.characters)
    assert {
        line.type
        for shot in projection.shots
        for line in shot.dialogue
    } == {
        StoryWorkspaceEpisodeDialogueType.SPOKEN,
        StoryWorkspaceEpisodeDialogueType.INNER,
    }


def test_all_vendor_storyboards_match_the_bounded_canonical_dtos() -> None:
    storyboards = sorted(VENDOR_STORIES.glob("*/episodes/*/storyboard.yaml"))
    projected_shots = 0
    for storyboard in storyboards:
        projection = _adapter().project(
            outline=None,
            script=None,
            storyboard=storyboard.read_bytes(),
        )
        projected_shots += len(projection.shots)

    assert len(storyboards) == 85
    assert projected_shots == 3832


def test_stable_ids_survive_insertion_and_reordering() -> None:
    adapter = _adapter()
    original = adapter.project(
        outline=OUTLINE_WITH_BEATS,
        script=SCRIPT_WITH_SCENES,
        storyboard=STORYBOARD_WITH_EXPLICIT_LINKS,
    )
    reordered = adapter.project(
        outline=OUTLINE_WITH_BEATS.replace(
            b"### SC-01. Station [scene-station]",
            b"### SC-09. Prologue [scene-prologue]\n\n**Scene Summary**:\nOpen.\n\n"
            b"### SC-01. Station [scene-station]",
        ),
        script=SCRIPT_WITH_SCENES.replace(
            b"S01. Station [scene-station] - Night - Exterior",
            b"S09. Prologue [scene-prologue] - Night - Exterior\n\n[Open.]\n\n"
            b"S01. Station [scene-station] - Night - Exterior",
        ),
        storyboard=STORYBOARD_WITH_EXPLICIT_LINKS.replace(
            b"shots:\n",
            b"shots:\n  - shot_id: S09-E01-001\n    visual: Open.\n",
        ).replace(
            b"  - shot_id: S01-E01-001\n",
            b"  - shot_id: CUSTOM-E01-001\n"
            b"    scene_ref: scene-car\n"
            b"    script_scene_ref: S02\n"
            b"    narrative_beat_ref: SC-02\n"
            b"    shot_type: WS\n"
            b"    visual: The passenger exits.\n"
            b"  - shot_id: S01-E01-001\n",
        ).replace(
            b"  - shot_id: CUSTOM-E01-001\n"
            b"    scene_ref: scene-car\n"
            b"    script_scene_ref: S02\n"
            b"    narrative_beat_ref: SC-02\n"
            b"    shot_type: WS\n"
            b"    visual: The passenger exits.\n",
            b"",
            1,
        ),
    )

    assert {beat.source_key: beat.id for beat in original.narrative_beats}.items() <= {
        beat.source_key: beat.id for beat in reordered.narrative_beats
    }.items()
    assert {scene.source_key: scene.id for scene in original.scenes}.items() <= {
        scene.source_key: scene.id for scene in reordered.scenes
    }.items()
    assert {shot.shot_id: shot.id for shot in original.shots}.items() <= {
        shot.shot_id: shot.id for shot in reordered.shots
    }.items()

    revised = adapter.project(
        outline=OUTLINE_WITH_BEATS,
        script=SCRIPT_WITH_SCENES,
        storyboard=STORYBOARD_WITH_EXPLICIT_LINKS,
        outline_revision="sha256:" + "a" * 64,
        script_revision="sha256:" + "b" * 64,
        storyboard_revision="sha256:" + "c" * 64,
    )
    assert [beat.id for beat in original.narrative_beats] == [
        beat.id for beat in revised.narrative_beats
    ]
    assert [scene.id for scene in original.scenes] == [scene.id for scene in revised.scenes]
    assert [shot.id for shot in original.shots] == [shot.id for shot in revised.shots]


def test_missing_inputs_produce_empty_unavailable_projection() -> None:
    projection = _adapter().project(outline=None, script=None, storyboard=None)

    assert projection.narrative_beats == []
    assert projection.scenes == []
    assert projection.shots == []
    assert projection.associations.beat_scene_coverage.availability is (
        StoryWorkspaceEpisodeMetricAvailability.UNAVAILABLE
    )
    assert projection.associations.scene_shot_coverage.availability is (
        StoryWorkspaceEpisodeMetricAvailability.UNAVAILABLE
    )


@pytest.mark.parametrize(
    ("artifact", "content", "reason"),
    [
        ("outline", b"---\ntitle: [unterminated\n---\n# Bad\n", "invalid_yaml"),
        ("script", b"# Bad\n<script>alert('x')</script>\n", "unsafe_html"),
        (
            "storyboard",
            b"shots:\n  - &shot\n    shot_id: S01-E01-001\n"
            b"  - *shot\n",
            "yaml_alias_not_allowed",
        ),
        (
            "storyboard",
            b"shots:\n  - shot_id: S01-E01-001\n"
            b"  - shot_id: S01-E01-001\n",
            "duplicate_shot_id",
        ),
        (
            "storyboard",
            b"shots:\n  - shot_id: S01-E01-001\n"
            b"    dialogue:\n"
            b"      - speaker: mc-01\n"
            b"        line: Unsafe enum expansion.\n"
            b"        type: tool\n",
            "invalid_dialogue_type",
        ),
        (
            "storyboard",
            b"shots:\n  - shot_id: S01-E01-001\n"
            b"    dialogue:\n"
            b"      - legacy scalar dialogue\n",
            "invalid_shape",
        ),
    ],
)
def test_rejects_malformed_malicious_or_duplicate_content(
    artifact: str,
    content: bytes,
    reason: str,
) -> None:
    inputs = {"outline": None, "script": None, "storyboard": None}
    inputs[artifact] = content

    with pytest.raises(StoryWorkspaceEpisodeArtifactParseError) as captured:
        _adapter().project(**inputs)

    assert captured.value.artifact == artifact
    assert captured.value.reason == reason
    assert "<script" not in str(captured.value).lower()


def test_unsafe_yaml_tag_is_not_executed(tmp_path: Path) -> None:
    sentinel = tmp_path / "must-not-exist"
    payload = (
        "shots: !!python/object/apply:pathlib.Path.touch\n"
        f"  - {sentinel}\n"
    ).encode()

    with pytest.raises(StoryWorkspaceEpisodeArtifactParseError) as captured:
        _adapter().project(outline=None, script=None, storyboard=payload)

    assert captured.value.reason == "invalid_yaml"
    assert not sentinel.exists()


def test_rejects_markdown_size_section_and_yaml_depth_limits() -> None:
    oversized = b"# Outline\n" + b"x" * STORY_WORKSPACE_EPISODE_MARKDOWN_MAX_BYTES
    with pytest.raises(StoryWorkspaceEpisodeArtifactParseError) as size_error:
        _adapter().project(outline=oversized, script=None, storyboard=None)
    assert size_error.value.reason == "size_limit"

    too_many_sections = b"\n".join(
        f"## Section {index}".encode() for index in range(300)
    )
    with pytest.raises(StoryWorkspaceEpisodeArtifactParseError) as section_error:
        _adapter().project(outline=too_many_sections, script=None, storyboard=None)
    assert section_error.value.reason == "section_limit"

    deeply_nested = ("shots: " + "[" * 80 + "x" + "]" * 80).encode()
    with pytest.raises(StoryWorkspaceEpisodeArtifactParseError) as depth_error:
        _adapter().project(outline=None, script=None, storyboard=deeply_nested)
    assert depth_error.value.reason == "depth_limit"


def test_link_level_diagnostics_do_not_destroy_a_valid_scene_link() -> None:
    storyboard = b"""shots:
  - shot_id: CUSTOM-E01-001
    scene_ref: S01
    visual: Asset refs do not link script scenes.
  - shot_id: CUSTOM-E01-002
    script_scene_ref: S01
    narrative_beat_ref: SC-99
    visual: Scene is valid while beat is absent.
  - shot_id: CUSTOM-E01-003
    script_scene_ref: S99
    visual: Explicit scene target is absent.
  - shot_id: SUP-E01-001
    scene_ref: scene-station
    visual: Supplemental shot has no hierarchy reference.
"""
    projection = _adapter().project(
        outline=OUTLINE_WITH_BEATS,
        script=SCRIPT_WITH_SCENES,
        storyboard=storyboard,
    )

    assert projection.shots[0].association_status is (
        StoryWorkspaceEpisodeAssociationStatus.UNLINKED
    )
    assert projection.shots[1].association_status is (
        StoryWorkspaceEpisodeAssociationStatus.LINKED
    )
    assert projection.shots[1].script_scene_id == projection.scenes[0].id
    assert projection.shots[1].narrative_beat_id is None
    assert projection.shots[2].association_status is (
        StoryWorkspaceEpisodeAssociationStatus.ORPHAN
    )
    assert projection.shots[3].association_status is (
        StoryWorkspaceEpisodeAssociationStatus.UNLINKED
    )
    assert projection.associations.missing_links == [
        "shot:CUSTOM-E01-001:script_scene",
        "shot:SUP-E01-001:script_scene",
    ]
    assert projection.associations.orphan_artifacts == [
        "shot:CUSTOM-E01-002:narrative_beat:SC-99",
        "shot:CUSTOM-E01-003:script_scene:S99",
    ]


def test_ids_are_namespaced_by_episode_uid() -> None:
    first = _adapter().project(
        outline=OUTLINE_WITH_BEATS,
        script=SCRIPT_WITH_SCENES,
        storyboard=STORYBOARD_WITH_EXPLICIT_LINKS,
    )
    second = StoryWorkspaceEpisodeArtifactAdapter(
        episode_uid="fedcba0987654321fedcba0987654321"
    ).project(
        outline=OUTLINE_WITH_BEATS,
        script=SCRIPT_WITH_SCENES,
        storyboard=STORYBOARD_WITH_EXPLICIT_LINKS,
    )

    assert first.episode_id != second.episode_id
    assert first.story_arc_id != second.story_arc_id
    assert first.narrative_beats[0].id != second.narrative_beats[0].id
    assert first.scenes[0].id != second.scenes[0].id
    assert first.shots[0].id != second.shots[0].id


def test_contract_rejects_impossible_coverage() -> None:
    from pydantic import ValidationError
    from story_workspace.contracts import StoryWorkspaceEpisodeAssociationCoverage

    with pytest.raises(ValidationError):
        StoryWorkspaceEpisodeAssociationCoverage(
            availability=StoryWorkspaceEpisodeMetricAvailability.AVAILABLE,
            linked=2,
            total=1,
            ratio=2.0,
        )

    with pytest.raises(ValidationError):
        StoryWorkspaceEpisodeAssociationCoverage(
            availability=StoryWorkspaceEpisodeMetricAvailability.UNAVAILABLE,
            linked=0,
            total=0,
            ratio=0.0,
        )
