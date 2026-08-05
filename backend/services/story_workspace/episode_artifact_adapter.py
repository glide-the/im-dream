"""Safe read-only projection for Episode outline, script, and storyboard files."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import math
import re
from typing import Any, Iterable, Mapping, Sequence
from uuid import UUID, uuid5

import yaml
from yaml.events import AliasEvent, CollectionEndEvent, CollectionStartEvent, NodeEvent

from story_workspace.contracts import (
    StoryWorkspaceEpisodeAssociationCoverage,
    StoryWorkspaceEpisodeAssociationDiagnostics,
    StoryWorkspaceEpisodeAssociationStatus,
    StoryWorkspaceEpisodeCharacterBeat,
    StoryWorkspaceEpisodeDepthPlane,
    StoryWorkspaceEpisodeDialogueLine,
    StoryWorkspaceEpisodeDialogueType,
    StoryWorkspaceEpisodeMetricAvailability,
    StoryWorkspaceEpisodeNarrativeBeat,
    StoryWorkspaceEpisodeNarrativeProjection,
    StoryWorkspaceEpisodeOverview,
    StoryWorkspaceEpisodeScriptScene,
    StoryWorkspaceEpisodeShotCamera,
    StoryWorkspaceEpisodeShotCharacter,
    StoryWorkspaceEpisodeShotTiming,
    StoryWorkspaceEpisodeSourceArtifact,
    StoryWorkspaceEpisodeStoryboardDialogue,
    StoryWorkspaceEpisodeStoryboardShot,
)


STORY_WORKSPACE_EPISODE_MARKDOWN_MAX_BYTES = 1024 * 1024
STORY_WORKSPACE_EPISODE_YAML_MAX_BYTES = 2 * 1024 * 1024
STORY_WORKSPACE_EPISODE_MAX_SECTIONS = 256
STORY_WORKSPACE_EPISODE_MAX_YAML_DEPTH = 32
STORY_WORKSPACE_EPISODE_MAX_YAML_NODES = 20_000
STORY_WORKSPACE_EPISODE_MAX_SHOTS = 1000
STORY_WORKSPACE_EPISODE_MAX_LINE_CHARS = 16_384

_HTML_RE = re.compile(r"<!--|</?[A-Za-z][^>]*>")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_BEAT_HEADING_RE = re.compile(r"^SC-([0-9]{2,})\.\s*(.*?)\s*$", re.IGNORECASE)
_SCENE_HEADING_RE = re.compile(r"^S([0-9]{2,})\.\s+(.+?)\s*$")
_REGULAR_SHOT_RE = re.compile(
    r"^(S[0-9]{2,})-E[0-9]{2,3}-[0-9]{3}[a-z]?$",
    re.IGNORECASE,
)
_SOURCE_BEAT_RE = re.compile(r"^SC-[0-9]{2,}$", re.IGNORECASE)
_SOURCE_SCENE_RE = re.compile(r"^S[0-9]{2,}$", re.IGNORECASE)
_SHOT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_SCENE_REF_RE = re.compile(r"\[([^\]\r\n]{1,255})\]")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_SOURCE_REVISION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9:._-]{0,127}$")
_GENERATED_FROM_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9@._:-]{0,254}$")
_ABSOLUTE_PATH_RE = re.compile(
    r"(?i)(?:"
    r"(?<![A-Za-z0-9:/])/(?!/)(?:[A-Za-z0-9._~-]+/)+[^\s`]+|"
    r"(?<![A-Za-z0-9])[A-Z]:[\\/][^\s`]+|"
    r"(?<![A-Za-z0-9])\\\\[^\\\s]+\\[^\s`]+|"
    r"(?<![A-Za-z0-9])(?:~|\$HOME|\$\{HOME\}|"
    r"%(?:USERPROFILE|HOMEPATH)%|\$env:(?:USERPROFILE|HOME))"
    r"[\\/][^\s`]+"
    r")"
)
_CREDENTIAL_RE = re.compile(
    r"(?i)(?:"
    r"\b(?:[A-Z][A-Z0-9_]*_(?:API_KEY|TOKEN|SECRET|PASSWORD|"
    r"CREDENTIALS?|PRIVATE_KEY)|API_KEY|ACCESS_TOKEN|REFRESH_TOKEN|"
    r"PASSWORD|CREDENTIALS?)\b(?:\s*[:=]\s*[^\s`]+)?|"
    r"\b(?:api[\s_-]*keys?|access[\s_-]*tokens?|refresh[\s_-]*tokens?|"
    r"tokens?|secrets?|auth(?:orization)?|credentials?|passwords?)"
    r"\b\s*[:=]\s*[^\s`]+|"
    r"\bbearer\s+[A-Za-z0-9._-]{8,}|"
    r"(?<![A-Za-z0-9_-])(?:sk-(?:(?:ant|proj)-)?|"
    r"gh[pousr]_|xox[baprs]-)[A-Za-z0-9_-]{16,}(?![A-Za-z0-9_-])|"
    r"(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]{5,}\."
    r"eyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{8,}(?![A-Za-z0-9_-])|"
    r"(?<![A-Za-z0-9_-])AIza[A-Za-z0-9_-]{30,}(?![A-Za-z0-9_-])|"
    r"(?<![A-Z0-9])AKIA[A-Z0-9]{16}(?![A-Z0-9])|"
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
    r")"
)
_PRIVATE_MODEL_TEXT_RE = re.compile(
    r"(?i)(?:"
    r"\bchain[\s_-]*(?:of[\s_-]*)?thought\b|"
    r"\bhidden[\s_-]*reasoning\b|\binternal[\s_-]*reasoning\b|"
    r"\bsystem[\s_-]*prompt\b|隐藏推理|内部推理|思维链|系统提示词"
    r")"
)
_RAW_COMMAND_RE = re.compile(
    r"(?i)(?:^|[\s`\[({:])(?:"
    r"\$\s+|sudo\s+|curl\b|wget\b|"
    r"(?:ba|z|fi)?sh\b|python(?:3(?:\.\d+)?)?\b|node\b|"
    r"npm\b|npx\b|pnpm\b|yarn\b|git\b|claude\b|"
    r"rm\s+(?:--recursive(?:\s+--force)?|-[A-Za-z]*r[A-Za-z]*)\s+|"
    r"cat\s+(?:~?/\.ssh/|/etc/(?:passwd|shadow)|"
    r"\S*(?:credential|secret|token|private[_-]?key))|"
    r"dd\s+[^\n]{0,240}\bif=\S+[^\n]{0,240}\bof=\S+|"
    r"/drama-forge:[a-z0-9_-]+|"
    r"(?:tool(?:_name)?|renderer|raw_command|command(?:_line)?)\s*[:=]"
    r")"
)
_SENSITIVE_CLI_FLAG_RE = re.compile(
    r"(?i)(?<![A-Za-z0-9_-])--(?:api[-_]?key|token|secret|password|"
    r"credential|authorization)(?:[=\s]|$)"
)
_RAW_TOOL_CONTEXT_RE = re.compile(
    r"(?i)(?<![A-Za-z0-9_-])(?:tool|renderer)\b"
)
_CLI_OPTION_RE = re.compile(
    r"(?<![A-Za-z0-9_-])--[A-Za-z0-9][A-Za-z0-9_-]*"
)
_LONG_HEX_SECRET_RE = re.compile(
    r"(?<![A-Fa-f0-9])[A-Fa-f0-9]{32,}(?![A-Fa-f0-9])"
)
_LONG_TOKEN_CANDIDATE_RE = re.compile(
    r"(?<![A-Za-z0-9+/_=-])[A-Za-z0-9+/_-]{32,}={0,2}"
    r"(?![A-Za-z0-9+/_=-])"
)
_ASSIGNED_TOKEN_CANDIDATE_RE = re.compile(
    r"(?<![A-Za-z0-9_.-])[A-Za-z_][A-Za-z0-9_.-]{0,40}\s*[:=]\s*"
    r"([A-Za-z0-9+/_-]{16,}={0,2})"
)
_PUBLIC_DREAM_RUN_ID_RE = re.compile(r"run_[0-9a-f]{32}")
_PUBLIC_CHARACTER_BEAT_ID_RE = re.compile(r"ARC-[A-Z0-9-]{1,124}")


class StoryWorkspaceEpisodeArtifactParseError(ValueError):
    """Publicly safe parser error without echoing untrusted artifact content."""

    def __init__(self, artifact: str, reason: str) -> None:
        self.artifact = artifact
        self.reason = reason
        super().__init__(f"{artifact} artifact cannot be projected ({reason})")


@dataclass(frozen=True)
class _MarkdownDocument:
    metadata: Mapping[str, Any]
    body: str


@dataclass(frozen=True)
class _MarkdownSection:
    level: int
    title: str
    lines: tuple[str, ...]


@dataclass(frozen=True)
class _OutlineProjection:
    overview: StoryWorkspaceEpisodeOverview
    beats: list[StoryWorkspaceEpisodeNarrativeBeat]


class StoryWorkspaceEpisodeArtifactAdapter:
    """Project canonical Episode text into stable, evidence-backed view models."""

    def __init__(self, *, episode_uid: str) -> None:
        try:
            self._namespace = UUID(hex=episode_uid)
        except (ValueError, AttributeError) as exc:
            raise ValueError("episode_uid must be a 32-character UUID hex value") from exc
        if self._namespace.hex != episode_uid.lower():
            raise ValueError("episode_uid must be a 32-character UUID hex value")

    def project(
        self,
        *,
        outline: bytes | None,
        script: bytes | None,
        storyboard: bytes | None,
        outline_revision: str | None = None,
        script_revision: str | None = None,
        storyboard_revision: str | None = None,
    ) -> StoryWorkspaceEpisodeNarrativeProjection:
        outline_revision = _source_revision(outline_revision, "outline")
        script_revision = _source_revision(script_revision, "script")
        storyboard_revision = _source_revision(storyboard_revision, "storyboard")
        outline_projection = self._project_outline(outline, outline_revision)
        beats_by_key = {
            beat.source_key: beat for beat in outline_projection.beats
        }
        scenes, scene_missing, scene_orphans = self._project_script(
            script,
            beats_by_key,
            script_revision,
        )
        scenes_by_key = {scene.source_key: scene for scene in scenes}
        shots, shot_missing, shot_orphans = self._project_storyboard(
            storyboard,
            beats_by_key,
            scenes_by_key,
            storyboard_revision,
        )
        linked_scenes = sum(
            scene.association_status is StoryWorkspaceEpisodeAssociationStatus.LINKED
            for scene in scenes
        )
        linked_shots = sum(
            shot.association_status is StoryWorkspaceEpisodeAssociationStatus.LINKED
            for shot in shots
        )
        return StoryWorkspaceEpisodeNarrativeProjection(
            episode_id=self._view_id("episode", "episode"),
            story_arc_id=self._view_id("arc", "arc"),
            overview=outline_projection.overview,
            narrative_beats=outline_projection.beats,
            scenes=scenes,
            shots=shots,
            associations=StoryWorkspaceEpisodeAssociationDiagnostics(
                beat_scene_coverage=_coverage(linked_scenes, len(scenes)),
                scene_shot_coverage=_coverage(linked_shots, len(shots)),
                missing_links=scene_missing + shot_missing,
                orphan_artifacts=scene_orphans + shot_orphans,
            ),
        )

    def _view_id(self, kind: str, source_key: str) -> str:
        return uuid5(self._namespace, f"{kind}:{source_key}").hex

    def _project_outline(
        self,
        content: bytes | None,
        source_revision: str | None,
    ) -> _OutlineProjection:
        if content is None:
            return _OutlineProjection(
                overview=StoryWorkspaceEpisodeOverview(),
                beats=[],
            )
        document = _parse_markdown(content, "outline")
        sections = _markdown_sections(document.body)
        metadata = document.metadata
        generated_from = _generated_from(metadata.get("generated_from"), "outline")
        character_beats = self._character_beats(metadata.get("character_beats"))
        overview = StoryWorkspaceEpisodeOverview(
            title=_optional_scalar_text(metadata.get("title"), 500, "outline"),
            series=_optional_scalar_text(metadata.get("series"), 500, "outline"),
            story_goals=_story_goals(sections),
            core_conflict=_section_summary(
                sections,
                ("核心冲突", "core conflict"),
                labels=("一句话冲突", "one-line conflict"),
            ),
            hook=_section_summary(
                sections,
                ("集尾卡点", "集尾钩子", "cliffhanger", "hook"),
                labels=("卡点画面", "悬念钩子", "hook"),
            ),
            source_artifact=StoryWorkspaceEpisodeSourceArtifact.EPISODE_OUTLINE,
            source_revision=source_revision,
            generated_from=generated_from,
            character_beats=character_beats,
        )
        beats: list[StoryWorkspaceEpisodeNarrativeBeat] = []
        seen: set[str] = set()
        for section in sections:
            if section.level != 3:
                continue
            match = _BEAT_HEADING_RE.fullmatch(_plain_text(section.title))
            if match is None:
                continue
            source_key = f"SC-{match.group(1)}".upper()
            if source_key in seen:
                raise StoryWorkspaceEpisodeArtifactParseError(
                    "outline",
                    "duplicate_beat_key",
                )
            seen.add(source_key)
            heading_tail = match.group(2).strip()
            asset_match = _SCENE_REF_RE.search(heading_tail)
            asset_scene_ref = (
                _bounded_text(asset_match.group(1), 255)
                if asset_match is not None
                else None
            )
            title = _SCENE_REF_RE.sub("", heading_tail).strip(" .·-")
            beats.append(
                StoryWorkspaceEpisodeNarrativeBeat(
                    id=self._view_id("beat", source_key),
                    source_key=source_key,
                    title=_bounded_text(title or source_key, 500),
                    asset_scene_ref=asset_scene_ref,
                    narrative_function=_labeled_value(
                        section.lines,
                        ("叙事功能", "narrative function"),
                    ),
                    emotion_tone=_labeled_value(
                        section.lines,
                        ("情绪基调", "emotion tone"),
                    ),
                    summary=_labeled_block(
                        section.lines,
                        ("场景摘要", "scene summary"),
                    ),
                    scene_goals=_labeled_list(
                        section.lines,
                        ("场景目标", "scene goals"),
                    ),
                    key_dialogue_beats=_labeled_list(
                        section.lines,
                        ("关键对白节拍", "key dialogue beats"),
                    ),
                    source_revision=source_revision,
                    generated_from=generated_from,
                )
            )
        return _OutlineProjection(overview=overview, beats=beats)

    def _character_beats(self, value: Any) -> list[StoryWorkspaceEpisodeCharacterBeat]:
        if value is None:
            return []
        if not isinstance(value, list) or len(value) > 256:
            raise StoryWorkspaceEpisodeArtifactParseError("outline", "shape_limit")
        results: list[StoryWorkspaceEpisodeCharacterBeat] = []
        seen: set[str] = set()
        for item in value:
            if not isinstance(item, Mapping):
                raise StoryWorkspaceEpisodeArtifactParseError("outline", "invalid_shape")
            beat_key = _optional_scalar_text(item.get("beat_id"), 128, "outline")
            character_id = _optional_scalar_text(
                item.get("character_id"),
                128,
                "outline",
            )
            if beat_key is None or character_id is None:
                raise StoryWorkspaceEpisodeArtifactParseError(
                    "outline",
                    "missing_identity",
                )
            source_key = beat_key
            stable_key = f"{character_id}:{source_key}"
            if stable_key in seen:
                raise StoryWorkspaceEpisodeArtifactParseError(
                    "outline",
                    "duplicate_character_beat",
                )
            seen.add(stable_key)
            results.append(
                StoryWorkspaceEpisodeCharacterBeat(
                    id=self._view_id("character-beat", stable_key),
                    source_key=source_key,
                    character_id=character_id,
                    action=_optional_scalar_text(item.get("action"), 128, "outline"),
                    start_state=_optional_scalar_text(
                        item.get("start_state"), 2000, "outline"
                    ),
                    trigger=_optional_scalar_text(item.get("trigger"), 2000, "outline"),
                    choice=_optional_scalar_text(item.get("choice"), 2000, "outline"),
                    end_state=_optional_scalar_text(
                        item.get("end_state"), 2000, "outline"
                    ),
                    visible_evidence=_optional_scalar_text(
                        item.get("visible_evidence"), 2000, "outline"
                    ),
                )
            )
        return results

    def _project_script(
        self,
        content: bytes | None,
        beats_by_key: Mapping[str, StoryWorkspaceEpisodeNarrativeBeat],
        source_revision: str | None,
    ) -> tuple[list[StoryWorkspaceEpisodeScriptScene], list[str], list[str]]:
        if content is None:
            return [], [], []
        document = _parse_markdown(content, "script")
        generated_from = _generated_from(
            document.metadata.get("generated_from"),
            "script",
        )
        scene_sections = _script_scene_sections(document.body)
        scenes: list[StoryWorkspaceEpisodeScriptScene] = []
        missing_links: list[str] = []
        orphan_artifacts: list[str] = []
        seen: set[str] = set()
        for source_key, heading_tail, lines in scene_sections:
            if source_key in seen:
                raise StoryWorkspaceEpisodeArtifactParseError(
                    "script",
                    "duplicate_scene_key",
                )
            seen.add(source_key)
            explicit_ref = _standalone_ref(lines, "narrative_beat_ref", "SC-")
            fallback_ref = f"SC-{source_key[1:]}"
            target_key = explicit_ref or fallback_ref
            target = beats_by_key.get(target_key)
            if explicit_ref is not None and target is None:
                status = StoryWorkspaceEpisodeAssociationStatus.ORPHAN
                orphan_artifacts.append(
                    f"scene:{source_key}:narrative_beat:{explicit_ref}"
                )
            elif target is not None:
                status = StoryWorkspaceEpisodeAssociationStatus.LINKED
            else:
                status = StoryWorkspaceEpisodeAssociationStatus.UNLINKED
                missing_links.append(f"scene:{source_key}:narrative_beat")
            asset_match = _SCENE_REF_RE.search(heading_tail)
            asset_scene_ref = (
                _bounded_text(asset_match.group(1), 255)
                if asset_match is not None
                else None
            )
            title = _SCENE_REF_RE.sub("", heading_tail).strip(" .·-")
            actions, dialogue, camera_cues = _script_content(lines)
            scenes.append(
                StoryWorkspaceEpisodeScriptScene(
                    id=self._view_id("scene", source_key),
                    source_key=source_key,
                    title=_bounded_text(title or source_key, 500),
                    heading=_bounded_text(f"{source_key}. {heading_tail}", 1000),
                    asset_scene_ref=asset_scene_ref,
                    narrative_beat_id=(target.id if status.value == "linked" else None),
                    declared_narrative_beat_ref=explicit_ref,
                    association_status=status,
                    actions=actions,
                    dialogue=dialogue,
                    camera_cues=camera_cues,
                    source_revision=source_revision,
                    generated_from=generated_from,
                )
            )
        return scenes, missing_links, orphan_artifacts

    def _project_storyboard(
        self,
        content: bytes | None,
        beats_by_key: Mapping[str, StoryWorkspaceEpisodeNarrativeBeat],
        scenes_by_key: Mapping[str, StoryWorkspaceEpisodeScriptScene],
        source_revision: str | None,
    ) -> tuple[list[StoryWorkspaceEpisodeStoryboardShot], list[str], list[str]]:
        if content is None:
            return [], [], []
        text = _decode(
            content,
            "storyboard",
            STORY_WORKSPACE_EPISODE_YAML_MAX_BYTES,
        )
        documents = _safe_yaml_documents(
            text,
            "storyboard",
            max_documents=4,
        )
        _enforce_public_text_policy(text, "storyboard")
        shots_value: Any = None
        generated_from: str | None = None
        for document in documents:
            if document is None:
                continue
            if not isinstance(document, Mapping):
                raise StoryWorkspaceEpisodeArtifactParseError(
                    "storyboard",
                    "invalid_shape",
                )
            if generated_from is None and "generated_from" in document:
                generated_from = _generated_from(
                    document.get("generated_from"),
                    "storyboard",
                )
            if "shots" in document:
                if shots_value is not None:
                    raise StoryWorkspaceEpisodeArtifactParseError(
                        "storyboard",
                        "duplicate_shots_document",
                    )
                shots_value = document["shots"]
        if shots_value is None:
            shots_value = []
        if not isinstance(shots_value, list):
            raise StoryWorkspaceEpisodeArtifactParseError(
                "storyboard",
                "invalid_shape",
            )
        if len(shots_value) > STORY_WORKSPACE_EPISODE_MAX_SHOTS:
            raise StoryWorkspaceEpisodeArtifactParseError(
                "storyboard",
                "item_limit",
            )
        shots: list[StoryWorkspaceEpisodeStoryboardShot] = []
        missing_links: list[str] = []
        orphan_artifacts: list[str] = []
        seen: set[str] = set()
        for item in shots_value:
            if not isinstance(item, Mapping):
                raise StoryWorkspaceEpisodeArtifactParseError(
                    "storyboard",
                    "invalid_shape",
                )
            shot_id = _required_source_text(item.get("shot_id"), "storyboard")
            if _SHOT_ID_RE.fullmatch(shot_id) is None:
                raise StoryWorkspaceEpisodeArtifactParseError(
                    "storyboard",
                    "invalid_shot_id",
                )
            if shot_id in seen:
                raise StoryWorkspaceEpisodeArtifactParseError(
                    "storyboard",
                    "duplicate_shot_id",
                )
            seen.add(shot_id)
            explicit_scene = _normalized_source_ref(
                item.get("script_scene_ref"),
                _SOURCE_SCENE_RE,
                "storyboard",
            )
            explicit_beat = _normalized_source_ref(
                item.get("narrative_beat_ref"),
                _SOURCE_BEAT_RE,
                "storyboard",
            )
            regular_match = _REGULAR_SHOT_RE.fullmatch(shot_id)
            inferred_scene = (
                regular_match.group(1).upper() if regular_match is not None else None
            )
            target_scene_key = explicit_scene or inferred_scene
            target_scene = (
                scenes_by_key.get(target_scene_key)
                if target_scene_key is not None
                else None
            )
            target_beat = (
                beats_by_key.get(explicit_beat) if explicit_beat is not None else None
            )
            if explicit_beat is not None and target_beat is None:
                orphan_artifacts.append(
                    f"shot:{shot_id}:narrative_beat:{explicit_beat}"
                )
            if explicit_scene is not None and target_scene is None:
                orphan_artifacts.append(
                    f"shot:{shot_id}:script_scene:{explicit_scene}"
                )
                status = StoryWorkspaceEpisodeAssociationStatus.ORPHAN
            elif target_scene is not None:
                status = StoryWorkspaceEpisodeAssociationStatus.LINKED
                if (
                    explicit_beat is None
                    and target_scene.narrative_beat_id is not None
                ):
                    target_beat = next(
                        (
                            beat
                            for beat in beats_by_key.values()
                            if beat.id == target_scene.narrative_beat_id
                        ),
                        None,
                    )
            else:
                status = StoryWorkspaceEpisodeAssociationStatus.UNLINKED
                missing_links.append(f"shot:{shot_id}:script_scene")
            shots.append(
                StoryWorkspaceEpisodeStoryboardShot(
                    id=self._view_id("shot", shot_id),
                    shot_id=shot_id,
                    asset_scene_ref=_optional_scalar_text(
                        item.get("scene_ref"), 255, "storyboard"
                    ),
                    declared_script_scene_ref=explicit_scene,
                    declared_narrative_beat_ref=explicit_beat,
                    script_scene_id=(target_scene.id if target_scene is not None else None),
                    narrative_beat_id=(target_beat.id if target_beat is not None else None),
                    association_status=status,
                    shot_type=_optional_scalar_text(
                        item.get("shot_type"), 255, "storyboard"
                    ),
                    characters=_shot_characters(item.get("characters")),
                    camera=_shot_camera(item.get("camera")),
                    visual=_optional_scalar_text(
                        item.get("visual"), 4000, "storyboard"
                    ),
                    dialogue=_shot_dialogue(item.get("dialogue")),
                    timing=_shot_timing(item.get("timing")),
                    source_revision=source_revision,
                    generated_from=generated_from,
                )
            )
        return shots, missing_links, orphan_artifacts


def _coverage(linked: int, total: int) -> StoryWorkspaceEpisodeAssociationCoverage:
    if total == 0:
        return StoryWorkspaceEpisodeAssociationCoverage(
            availability=StoryWorkspaceEpisodeMetricAvailability.UNAVAILABLE,
            linked=0,
            total=0,
            ratio=None,
        )
    return StoryWorkspaceEpisodeAssociationCoverage(
        availability=StoryWorkspaceEpisodeMetricAvailability.AVAILABLE,
        linked=linked,
        total=total,
        ratio=linked / total,
    )


def _decode(content: bytes, artifact: str, max_bytes: int) -> str:
    if not isinstance(content, bytes):
        raise StoryWorkspaceEpisodeArtifactParseError(artifact, "invalid_input")
    if len(content) > max_bytes:
        raise StoryWorkspaceEpisodeArtifactParseError(artifact, "size_limit")
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise StoryWorkspaceEpisodeArtifactParseError(artifact, "invalid_utf8") from exc
    if _CONTROL_RE.search(text):
        raise StoryWorkspaceEpisodeArtifactParseError(artifact, "control_character")
    if any(len(line) > STORY_WORKSPACE_EPISODE_MAX_LINE_CHARS for line in text.splitlines()):
        raise StoryWorkspaceEpisodeArtifactParseError(artifact, "line_limit")
    if _HTML_RE.search(text):
        raise StoryWorkspaceEpisodeArtifactParseError(artifact, "unsafe_html")
    return text


def _enforce_public_text_policy(value: str, artifact: str) -> None:
    """Fail closed before any narrative artifact string can enter a public DTO."""

    if _ABSOLUTE_PATH_RE.search(value):
        raise StoryWorkspaceEpisodeArtifactParseError(artifact, "sensitive_text")
    if _CREDENTIAL_RE.search(value):
        raise StoryWorkspaceEpisodeArtifactParseError(
            artifact,
            "credential_forbidden",
        )
    if _PRIVATE_MODEL_TEXT_RE.search(value):
        raise StoryWorkspaceEpisodeArtifactParseError(artifact, "sensitive_text")
    if _looks_like_high_entropy_secret(value):
        raise StoryWorkspaceEpisodeArtifactParseError(
            artifact,
            "credential_forbidden",
        )
    if (
        _RAW_COMMAND_RE.search(value)
        or _SENSITIVE_CLI_FLAG_RE.search(value)
        or _contains_raw_tool_option(value)
    ):
        raise StoryWorkspaceEpisodeArtifactParseError(
            artifact,
            "raw_command_forbidden",
        )


def _contains_raw_tool_option(value: str) -> bool:
    for line in value.splitlines():
        context = _RAW_TOOL_CONTEXT_RE.search(line)
        if (
            context is not None
            and _CLI_OPTION_RE.search(line, context.end()) is not None
        ):
            return True
    return False


def _looks_like_high_entropy_secret(value: str) -> bool:
    def high_entropy(
        candidate: str,
        *,
        threshold: float,
        minimum_character_classes: int,
    ) -> bool:
        token = candidate.rstrip("=")
        if not token:
            return False
        counts = {character: token.count(character) for character in set(token)}
        entropy = -sum(
            (count / len(token)) * math.log2(count / len(token))
            for count in counts.values()
        )
        character_classes = sum((
            any(character.islower() for character in token),
            any(character.isupper() for character in token),
            any(character.isdigit() for character in token),
            any(character in "+/_-" for character in token),
        ))
        return (
            character_classes >= minimum_character_classes
            and entropy >= threshold
        )

    if any(
        high_entropy(
            match.group(0),
            threshold=3.0,
            minimum_character_classes=1,
        )
        for match in _LONG_HEX_SECRET_RE.finditer(value)
        if value[max(0, match.start() - 4) : match.start()].lower() != "run_"
    ):
        return True
    if any(
        high_entropy(
            match.group(1),
            threshold=3.0,
            minimum_character_classes=3,
        )
        for match in _ASSIGNED_TOKEN_CANDIDATE_RE.finditer(value)
        if _PUBLIC_CHARACTER_BEAT_ID_RE.fullmatch(match.group(1)) is None
    ):
        return True
    return any(
        high_entropy(
            match.group(0),
            threshold=3.5,
            minimum_character_classes=3,
        )
        for match in _LONG_TOKEN_CANDIDATE_RE.finditer(value)
        if _PUBLIC_DREAM_RUN_ID_RE.fullmatch(match.group(0)) is None
    )


def _source_revision(value: str | None, artifact: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or _SOURCE_REVISION_RE.fullmatch(value) is None:
        raise StoryWorkspaceEpisodeArtifactParseError(
            artifact,
            "invalid_source_revision",
        )
    return value


def _generated_from(value: Any, artifact: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or _GENERATED_FROM_RE.fullmatch(value) is None:
        raise StoryWorkspaceEpisodeArtifactParseError(
            artifact,
            "invalid_generated_from",
        )
    return value


def _parse_markdown(content: bytes, artifact: str) -> _MarkdownDocument:
    text = _decode(content, artifact, STORY_WORKSPACE_EPISODE_MARKDOWN_MAX_BYTES)
    lines = text.splitlines()
    metadata: Mapping[str, Any] = {}
    body_start = 0
    if lines and lines[0].strip() == "---":
        try:
            closing = next(
                index for index, line in enumerate(lines[1:], start=1)
                if line.strip() == "---"
            )
        except StopIteration as exc:
            raise StoryWorkspaceEpisodeArtifactParseError(
                artifact,
                "invalid_yaml",
            ) from exc
        frontmatter = "\n".join(lines[1:closing])
        documents = _safe_yaml_documents(frontmatter, artifact, max_documents=1)
        loaded = documents[0] if documents else None
        if loaded is not None and not isinstance(loaded, Mapping):
            raise StoryWorkspaceEpisodeArtifactParseError(artifact, "invalid_shape")
        metadata = loaded or {}
        body_start = closing + 1
    body = "\n".join(lines[body_start:])
    _enforce_public_text_policy(text, artifact)
    if sum(_HEADING_RE.match(line) is not None for line in body.splitlines()) > (
        STORY_WORKSPACE_EPISODE_MAX_SECTIONS
    ):
        raise StoryWorkspaceEpisodeArtifactParseError(artifact, "section_limit")
    return _MarkdownDocument(metadata=metadata, body=body)


def _safe_yaml_documents(
    text: str,
    artifact: str,
    *,
    max_documents: int,
) -> list[Any]:
    depth = 0
    nodes = 0
    try:
        for event in yaml.parse(text):
            if isinstance(event, AliasEvent):
                raise StoryWorkspaceEpisodeArtifactParseError(
                    artifact,
                    "yaml_alias_not_allowed",
                )
            if isinstance(event, CollectionStartEvent):
                depth += 1
                if depth > STORY_WORKSPACE_EPISODE_MAX_YAML_DEPTH:
                    raise StoryWorkspaceEpisodeArtifactParseError(
                        artifact,
                        "depth_limit",
                    )
            elif isinstance(event, CollectionEndEvent):
                depth -= 1
            if isinstance(event, NodeEvent):
                nodes += 1
                if nodes > STORY_WORKSPACE_EPISODE_MAX_YAML_NODES:
                    raise StoryWorkspaceEpisodeArtifactParseError(
                        artifact,
                        "node_limit",
                    )
        documents = list(yaml.safe_load_all(text))
    except StoryWorkspaceEpisodeArtifactParseError:
        raise
    except yaml.YAMLError as exc:
        raise StoryWorkspaceEpisodeArtifactParseError(artifact, "invalid_yaml") from exc
    if len(documents) > max_documents:
        raise StoryWorkspaceEpisodeArtifactParseError(artifact, "document_limit")
    _validate_loaded_yaml(documents, artifact)
    return documents


def _validate_loaded_yaml(values: Sequence[Any], artifact: str) -> None:
    seen_nodes: set[int] = set()

    def visit(value: Any, depth: int) -> None:
        if depth > STORY_WORKSPACE_EPISODE_MAX_YAML_DEPTH:
            raise StoryWorkspaceEpisodeArtifactParseError(artifact, "depth_limit")
        if isinstance(value, str):
            if len(value) > STORY_WORKSPACE_EPISODE_MAX_LINE_CHARS:
                raise StoryWorkspaceEpisodeArtifactParseError(artifact, "scalar_limit")
            if _HTML_RE.search(value) or _CONTROL_RE.search(value):
                raise StoryWorkspaceEpisodeArtifactParseError(artifact, "unsafe_html")
            return
        if isinstance(value, Mapping):
            identity = id(value)
            if identity in seen_nodes:
                raise StoryWorkspaceEpisodeArtifactParseError(
                    artifact,
                    "yaml_alias_not_allowed",
                )
            seen_nodes.add(identity)
            if len(value) > STORY_WORKSPACE_EPISODE_MAX_YAML_NODES:
                raise StoryWorkspaceEpisodeArtifactParseError(artifact, "node_limit")
            for key, child in value.items():
                if not isinstance(key, (str, int, float, bool)) and key is not None:
                    raise StoryWorkspaceEpisodeArtifactParseError(
                        artifact,
                        "invalid_shape",
                    )
                visit(key, depth + 1)
                visit(child, depth + 1)
            return
        if isinstance(value, list):
            identity = id(value)
            if identity in seen_nodes:
                raise StoryWorkspaceEpisodeArtifactParseError(
                    artifact,
                    "yaml_alias_not_allowed",
                )
            seen_nodes.add(identity)
            if len(value) > STORY_WORKSPACE_EPISODE_MAX_YAML_NODES:
                raise StoryWorkspaceEpisodeArtifactParseError(artifact, "node_limit")
            for child in value:
                visit(child, depth + 1)
            return
        if value is not None and not isinstance(
            value,
            (int, float, bool, date, datetime),
        ):
            raise StoryWorkspaceEpisodeArtifactParseError(artifact, "invalid_shape")

    for root in values:
        visit(root, 0)


def _markdown_sections(body: str) -> list[_MarkdownSection]:
    lines = body.splitlines()
    headings: list[tuple[int, int, str]] = []
    for index, line in enumerate(lines):
        match = _HEADING_RE.match(line)
        if match is not None:
            headings.append((index, len(match.group(1)), match.group(2)))
    sections: list[_MarkdownSection] = []
    for heading_index, (line_index, level, title) in enumerate(headings):
        end = len(lines)
        for next_line, next_level, _ in headings[heading_index + 1 :]:
            if next_level <= level:
                end = next_line
                break
        sections.append(
            _MarkdownSection(
                level=level,
                title=title,
                lines=tuple(lines[line_index + 1 : end]),
            )
        )
    return sections


def _script_scene_sections(body: str) -> list[tuple[str, str, tuple[str, ...]]]:
    lines = body.splitlines()
    starts: list[tuple[int, str, str]] = []
    for index, line in enumerate(lines):
        match = _SCENE_HEADING_RE.fullmatch(line.strip())
        if match is not None:
            starts.append((index, f"S{match.group(1)}".upper(), match.group(2)))
    results: list[tuple[str, str, tuple[str, ...]]] = []
    for position, (line_index, source_key, heading_tail) in enumerate(starts):
        end = starts[position + 1][0] if position + 1 < len(starts) else len(lines)
        results.append((source_key, heading_tail, tuple(lines[line_index + 1 : end])))
    return results


def _normalize_label(value: str) -> str:
    return re.sub(r"[\s*_`：:]", "", value).lower()


def _label_matches(line: str, labels: Iterable[str]) -> bool:
    normalized = _normalize_label(line)
    return any(normalized.startswith(_normalize_label(label)) for label in labels)


def _plain_text(value: str) -> str:
    text = value.strip()
    text = re.sub(r"^>\s*", "", text)
    text = re.sub(r"^[-*+]\s+", "", text)
    text = re.sub(r"^[0-9]+\.\s+", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = text.replace("**", "").replace("__", "").replace("`", "")
    return text.strip()


def _bounded_text(value: str, max_length: int) -> str:
    plain = _plain_text(value)
    if len(plain) <= max_length:
        return plain
    return plain[: max_length - 1].rstrip() + "…"


def _optional_scalar_text(
    value: Any,
    max_length: int,
    artifact: str,
) -> str | None:
    if value is None:
        return None
    if not isinstance(value, (str, int, float, bool)):
        raise StoryWorkspaceEpisodeArtifactParseError(artifact, "invalid_shape")
    text = _bounded_text(str(value), max_length)
    return text or None


def _required_source_text(value: Any, artifact: str) -> str:
    result = _optional_string_text(value, 128, artifact)
    if result is None:
        raise StoryWorkspaceEpisodeArtifactParseError(artifact, "missing_identity")
    return result


def _optional_string_text(
    value: Any,
    max_length: int,
    artifact: str,
) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise StoryWorkspaceEpisodeArtifactParseError(artifact, "invalid_shape")
    text = _bounded_text(value, max_length)
    return text or None


def _normalized_source_ref(
    value: Any,
    pattern: re.Pattern[str],
    artifact: str,
) -> str | None:
    result = _optional_string_text(value, 128, artifact)
    if result is None:
        return None
    normalized = result.upper()
    if pattern.fullmatch(normalized) is None:
        raise StoryWorkspaceEpisodeArtifactParseError(artifact, "invalid_reference")
    return normalized


def _story_goals(sections: Sequence[_MarkdownSection]) -> list[str]:
    section = next(
        (
            candidate
            for candidate in sections
            if candidate.level == 2
            and any(
                name in _plain_text(candidate.title).lower()
                for name in ("叙事目标", "story goals")
            )
        ),
        None,
    )
    if section is None:
        return []
    goals: list[str] = []
    pending_title: str | None = None
    pending_description = False
    for raw_line in section.lines:
        heading = _HEADING_RE.match(raw_line)
        if heading is not None and re.match(
            r"^G[0-9]+\.", _plain_text(heading.group(2)), re.IGNORECASE
        ):
            if pending_title and not pending_description:
                goals.append(pending_title)
            pending_title = re.sub(
                r"^G[0-9]+\.\s*",
                "",
                _plain_text(heading.group(2)),
                flags=re.IGNORECASE,
            )
            pending_description = False
            continue
        if _label_matches(raw_line, ("描述", "description")):
            value = _value_after_label(raw_line)
            if value:
                goals.append(_bounded_text(value, 1000))
                pending_description = True
            continue
        if re.match(r"^\s*[-*+]\s+", raw_line):
            plain = _plain_text(raw_line)
            if plain and not _label_matches(plain, ("驱动力", "验证方式", "优先级")):
                goals.append(_bounded_text(plain, 1000))
    if pending_title and not pending_description:
        goals.append(_bounded_text(pending_title, 1000))
    return list(dict.fromkeys(goals))[:32]


def _section_summary(
    sections: Sequence[_MarkdownSection],
    titles: Iterable[str],
    *,
    labels: Iterable[str],
) -> str | None:
    title_names = tuple(name.lower() for name in titles)
    section = next(
        (
            candidate
            for candidate in sections
            if candidate.level == 2
            and any(
                name in _plain_text(candidate.title).lower() for name in title_names
            )
        ),
        None,
    )
    if section is None:
        return None
    labeled = _labeled_value(section.lines, labels)
    if labeled:
        return _bounded_text(labeled, 4000)
    for line in section.lines:
        plain = _plain_text(line)
        if plain and not plain.startswith("|") and plain != "---":
            return _bounded_text(plain, 4000)
    return None


def _value_after_label(line: str) -> str:
    plain = _plain_text(line)
    parts = re.split(r"[：:]", plain, maxsplit=1)
    return parts[1].strip() if len(parts) == 2 else ""


def _labeled_value(lines: Sequence[str], labels: Iterable[str]) -> str | None:
    for raw_line in lines:
        if raw_line.strip().startswith("|"):
            cells = [cell.strip() for cell in raw_line.strip().strip("|").split("|")]
            if len(cells) >= 2 and _label_matches(cells[0], labels):
                value = _plain_text(cells[1])
                return _bounded_text(value, 500) if value else None
        if _label_matches(raw_line, labels):
            value = _value_after_label(raw_line)
            if value:
                return _bounded_text(value, 500)
    return None


def _label_index(lines: Sequence[str], labels: Iterable[str]) -> int | None:
    for index, line in enumerate(lines):
        if _label_matches(line, labels):
            return index
    return None


def _labeled_block(lines: Sequence[str], labels: Iterable[str]) -> str | None:
    start = _label_index(lines, labels)
    if start is None:
        return None
    same_line = _value_after_label(lines[start])
    values = [same_line] if same_line else []
    for line in lines[start + 1 :]:
        if _HEADING_RE.match(line) or re.match(r"^\s*\*\*[^*]+\*\*\s*[：:]", line):
            break
        plain = _plain_text(line)
        if plain and plain != "---" and not plain.startswith("|"):
            values.append(plain)
    text = " ".join(values)
    return _bounded_text(text, 4000) if text else None


def _labeled_list(lines: Sequence[str], labels: Iterable[str]) -> list[str]:
    start = _label_index(lines, labels)
    if start is None:
        return []
    values: list[str] = []
    same_line = _value_after_label(lines[start])
    if same_line:
        values.append(_bounded_text(same_line, 1000))
    for line in lines[start + 1 :]:
        if _HEADING_RE.match(line) or re.match(r"^\s*\*\*[^*]+\*\*\s*[：:]", line):
            break
        if re.match(r"^\s*(?:[-*+]|[0-9]+\.)\s+", line):
            plain = _plain_text(line)
            if plain:
                values.append(_bounded_text(plain, 1000))
    return values[:32]


def _standalone_ref(lines: Sequence[str], key: str, prefix: str) -> str | None:
    pattern = re.compile(
        rf"^\s*{re.escape(key)}\s*:\s*({re.escape(prefix)}[0-9]{{2,}})\s*$",
        re.IGNORECASE,
    )
    for line in lines:
        match = pattern.fullmatch(line)
        if match is not None:
            return match.group(1).upper()
    return None


def _script_content(
    lines: Sequence[str],
) -> tuple[list[str], list[StoryWorkspaceEpisodeDialogueLine], list[str]]:
    actions: list[str] = []
    dialogue: list[StoryWorkspaceEpisodeDialogueLine] = []
    camera_cues: list[str] = []
    index = 0
    speaker_re = re.compile(r"^([^#@\[\]|:：]{1,80}?)(?:[（(]([^）)]{1,80})[）)])?$")
    while index < len(lines):
        stripped = lines[index].strip()
        if stripped.startswith("[") and stripped.endswith("]") and len(stripped) > 2:
            actions.append(_bounded_text(stripped[1:-1], 2000))
        elif stripped.startswith("CAM:"):
            value = stripped.removeprefix("CAM:").strip()
            if value:
                camera_cues.append(_bounded_text(value, 1000))
        elif stripped and not stripped.startswith(("@", "TRANS:", "---")):
            speaker_match = speaker_re.fullmatch(stripped)
            if speaker_match is not None:
                next_index = index + 1
                while next_index < len(lines) and not lines[next_index].strip():
                    next_index += 1
                if next_index < len(lines):
                    spoken = lines[next_index].strip()
                    if (
                        spoken
                        and not spoken.startswith(("[", "CAM:", "@", "TRANS:", "---", "#"))
                        and _standalone_ref((stripped,), "narrative_beat_ref", "SC-") is None
                    ):
                        dialogue.append(
                            StoryWorkspaceEpisodeDialogueLine(
                                speaker=_bounded_text(speaker_match.group(1), 128),
                                qualifier=(
                                    _bounded_text(speaker_match.group(2), 255)
                                    if speaker_match.group(2)
                                    else None
                                ),
                                text=_bounded_text(spoken, 2000),
                            )
                        )
                        index = next_index
        index += 1
    return actions[:256], dialogue[:256], camera_cues[:256]


def _shot_characters(value: Any) -> list[StoryWorkspaceEpisodeShotCharacter]:
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > 128:
        raise StoryWorkspaceEpisodeArtifactParseError("storyboard", "shape_limit")
    results: list[StoryWorkspaceEpisodeShotCharacter] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise StoryWorkspaceEpisodeArtifactParseError("storyboard", "invalid_shape")
        ref = _required_source_text(item.get("ref"), "storyboard")
        results.append(
            StoryWorkspaceEpisodeShotCharacter(
                ref=ref,
                display_name=_optional_string_text(
                    item.get("display_name"),
                    255,
                    "storyboard",
                ),
                depth_plane=_shot_depth_plane(item.get("depth_plane")),
                action=_optional_string_text(item.get("action"), 2000, "storyboard"),
                emotion=_optional_string_text(
                    item.get("emotion"),
                    1000,
                    "storyboard",
                ),
            )
        )
    return results


def _shot_depth_plane(value: Any) -> StoryWorkspaceEpisodeDepthPlane | None:
    if value is None:
        return None
    text = _required_source_text(value, "storyboard").lower()
    try:
        return StoryWorkspaceEpisodeDepthPlane(text)
    except ValueError as exc:
        raise StoryWorkspaceEpisodeArtifactParseError(
            "storyboard",
            "invalid_depth_plane",
        ) from exc


def _shot_camera(value: Any) -> StoryWorkspaceEpisodeShotCamera:
    if value is None:
        return StoryWorkspaceEpisodeShotCamera()
    if not isinstance(value, Mapping):
        raise StoryWorkspaceEpisodeArtifactParseError("storyboard", "invalid_shape")
    return StoryWorkspaceEpisodeShotCamera(
        angle=_optional_scalar_text(value.get("angle"), 255, "storyboard"),
        height=_optional_scalar_text(value.get("height"), 255, "storyboard"),
        movement=_optional_scalar_text(value.get("movement"), 255, "storyboard"),
        lens=_optional_scalar_text(value.get("lens"), 255, "storyboard"),
    )


def _shot_dialogue(value: Any) -> list[StoryWorkspaceEpisodeStoryboardDialogue]:
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > 128:
        raise StoryWorkspaceEpisodeArtifactParseError("storyboard", "shape_limit")
    results: list[StoryWorkspaceEpisodeStoryboardDialogue] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise StoryWorkspaceEpisodeArtifactParseError(
                "storyboard",
                "invalid_shape",
            )
        speaker = _required_source_text(item.get("speaker"), "storyboard")
        line = _optional_string_text(item.get("line"), 2000, "storyboard")
        dialogue_type = _optional_string_text(item.get("type"), 32, "storyboard")
        if line is None or dialogue_type is None:
            raise StoryWorkspaceEpisodeArtifactParseError(
                "storyboard",
                "missing_dialogue_field",
            )
        try:
            canonical_type = StoryWorkspaceEpisodeDialogueType(dialogue_type.lower())
        except ValueError as exc:
            raise StoryWorkspaceEpisodeArtifactParseError(
                "storyboard",
                "invalid_dialogue_type",
            ) from exc
        results.append(
            StoryWorkspaceEpisodeStoryboardDialogue(
                speaker=speaker,
                line=line,
                type=canonical_type,
            )
        )
    return results


def _shot_timing(value: Any) -> StoryWorkspaceEpisodeShotTiming:
    if value is None:
        return StoryWorkspaceEpisodeShotTiming()
    if not isinstance(value, Mapping):
        raise StoryWorkspaceEpisodeArtifactParseError("storyboard", "invalid_shape")
    duration = value.get("duration_sec")
    if duration is not None and (
        isinstance(duration, bool) or not isinstance(duration, (int, float))
    ):
        raise StoryWorkspaceEpisodeArtifactParseError("storyboard", "invalid_shape")
    return StoryWorkspaceEpisodeShotTiming(
        duration_sec=float(duration) if duration is not None else None,
        transition_in=_optional_scalar_text(
            value.get("transition_in"), 255, "storyboard"
        ),
        transition_out=_optional_scalar_text(
            value.get("transition_out"), 255, "storyboard"
        ),
    )
