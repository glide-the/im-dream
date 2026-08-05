"""Safe read-only projection for Episode outline, script, and storyboard files."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
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
    StoryWorkspaceEpisodeDialogueLine,
    StoryWorkspaceEpisodeMetricAvailability,
    StoryWorkspaceEpisodeNarrativeBeat,
    StoryWorkspaceEpisodeNarrativeProjection,
    StoryWorkspaceEpisodeOverview,
    StoryWorkspaceEpisodeScriptScene,
    StoryWorkspaceEpisodeShotCamera,
    StoryWorkspaceEpisodeShotCharacter,
    StoryWorkspaceEpisodeShotTiming,
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
    ) -> StoryWorkspaceEpisodeNarrativeProjection:
        outline_projection = self._project_outline(outline)
        beats_by_key = {
            beat.source_key: beat for beat in outline_projection.beats
        }
        scenes, scene_missing, scene_orphans = self._project_script(
            script,
            beats_by_key,
        )
        scenes_by_key = {scene.source_key: scene for scene in scenes}
        shots, shot_missing, shot_orphans = self._project_storyboard(
            storyboard,
            beats_by_key,
            scenes_by_key,
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

    def _project_outline(self, content: bytes | None) -> _OutlineProjection:
        if content is None:
            return _OutlineProjection(
                overview=StoryWorkspaceEpisodeOverview(),
                beats=[],
            )
        document = _parse_markdown(content, "outline")
        sections = _markdown_sections(document.body)
        metadata = document.metadata
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
    ) -> tuple[list[StoryWorkspaceEpisodeScriptScene], list[str], list[str]]:
        if content is None:
            return [], [], []
        document = _parse_markdown(content, "script")
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
                )
            )
        return scenes, missing_links, orphan_artifacts

    def _project_storyboard(
        self,
        content: bytes | None,
        beats_by_key: Mapping[str, StoryWorkspaceEpisodeNarrativeBeat],
        scenes_by_key: Mapping[str, StoryWorkspaceEpisodeScriptScene],
    ) -> tuple[list[StoryWorkspaceEpisodeStoryboardShot], list[str], list[str]]:
        if content is None:
            return [], [], []
        documents = _safe_yaml_documents(
            _decode(content, "storyboard", STORY_WORKSPACE_EPISODE_YAML_MAX_BYTES),
            "storyboard",
            max_documents=4,
        )
        shots_value: Any = None
        for document in documents:
            if document is None:
                continue
            if not isinstance(document, Mapping):
                raise StoryWorkspaceEpisodeArtifactParseError(
                    "storyboard",
                    "invalid_shape",
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
            has_orphan = False
            if explicit_beat is not None and target_beat is None:
                orphan_artifacts.append(
                    f"shot:{shot_id}:narrative_beat:{explicit_beat}"
                )
                has_orphan = True
            if target_scene_key is not None and target_scene is None:
                if explicit_scene is not None or inferred_scene is not None:
                    orphan_artifacts.append(
                        f"shot:{shot_id}:script_scene:{target_scene_key}"
                    )
                    has_orphan = True
            if has_orphan:
                status = StoryWorkspaceEpisodeAssociationStatus.ORPHAN
                target_scene = None
                target_beat = None
            elif target_scene is not None:
                status = StoryWorkspaceEpisodeAssociationStatus.LINKED
                if target_beat is None and target_scene.narrative_beat_id is not None:
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
    result = _optional_scalar_text(value, 128, artifact)
    if result is None:
        raise StoryWorkspaceEpisodeArtifactParseError(artifact, "missing_identity")
    return result


def _normalized_source_ref(
    value: Any,
    pattern: re.Pattern[str],
    artifact: str,
) -> str | None:
    result = _optional_scalar_text(value, 128, artifact)
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
                action=_optional_scalar_text(item.get("action"), 2000, "storyboard"),
            )
        )
    return results


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


def _shot_dialogue(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > 128:
        raise StoryWorkspaceEpisodeArtifactParseError("storyboard", "shape_limit")
    results: list[str] = []
    for item in value:
        text = _optional_scalar_text(item, 2000, "storyboard")
        if text:
            results.append(text)
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
