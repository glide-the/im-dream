"""Safe read-only projection for Episode prompts, render guide, and review."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import date, datetime
import hashlib
import hmac
import json
import math
from pathlib import PurePosixPath
import re
from typing import Any, Mapping, Sequence
from uuid import UUID, uuid5

import yaml
from yaml.events import (
    AliasEvent,
    CollectionEndEvent,
    CollectionStartEvent,
    DocumentStartEvent,
    MappingStartEvent,
    NodeEvent,
    ScalarEvent,
)

from story_workspace.contracts import (
    StoryWorkspaceEpisodeArtifactSection,
    StoryWorkspaceEpisodeAssociationCoverage,
    StoryWorkspaceEpisodeAssociationStatus,
    StoryWorkspaceEpisodeAuxiliaryAssociationDiagnostics,
    StoryWorkspaceEpisodeAuxiliaryProjection,
    StoryWorkspaceEpisodeMetricAvailability,
    StoryWorkspaceEpisodePrompt,
    StoryWorkspaceEpisodePromptGenerability,
    StoryWorkspaceEpisodePromptPage,
    StoryWorkspaceEpisodePromptParameters,
    StoryWorkspaceEpisodeRenderGuide,
    StoryWorkspaceEpisodeRenderQueueEntry,
    StoryWorkspaceEpisodeRenderQueuePage,
    StoryWorkspaceEpisodeReviewedSourceRevision,
    StoryWorkspaceEpisodeReviewReport,
    StoryWorkspaceEpisodeReviewScope,
    StoryWorkspaceEpisodeReviewTarget,
    StoryWorkspaceEpisodeReviewTargetKind,
)


STORY_WORKSPACE_EPISODE_AUXILIARY_MARKDOWN_MAX_BYTES = 1024 * 1024
STORY_WORKSPACE_EPISODE_AUXILIARY_YAML_MAX_BYTES = 2 * 1024 * 1024
STORY_WORKSPACE_EPISODE_AUXILIARY_COLLECTION_MAX_BYTES = 8 * 1024 * 1024
STORY_WORKSPACE_EPISODE_AUXILIARY_MAX_FILES = 128
STORY_WORKSPACE_EPISODE_AUXILIARY_MAX_ITEMS = 1000
STORY_WORKSPACE_EPISODE_AUXILIARY_MAX_SECTIONS = 128
STORY_WORKSPACE_EPISODE_AUXILIARY_MAX_YAML_DEPTH = 32
STORY_WORKSPACE_EPISODE_AUXILIARY_MAX_YAML_NODES = 20_000
STORY_WORKSPACE_EPISODE_AUXILIARY_MAX_YAML_DOCUMENTS = 128
STORY_WORKSPACE_EPISODE_AUXILIARY_MAX_MAPPING_ITEMS = 1000
STORY_WORKSPACE_EPISODE_AUXILIARY_MAX_SCALAR_CHARS = 16_384
STORY_WORKSPACE_EPISODE_AUXILIARY_PAGE_MAX = 100

_HTML_RE = re.compile(r"<!--|</?[A-Za-z][^>]*>")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_YAML_FENCE_RE = re.compile(r"```ya?ml\s*\n(.*?)```", re.IGNORECASE | re.DOTALL)
_SHOT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_PROMPT_KIND_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_REVISION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9:._-]{0,127}$")
_MANIFEST_REVISION_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_CANONICAL_EPISODE_ROOT_RE = re.compile(
    r"^stories/[A-Za-z0-9][A-Za-z0-9._-]{0,127}/episodes/EP[0-9]{2,3}$"
)
_RENDERER_IDENTITY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
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
    r"(?i)(?:^|[\s`])(?:"
    r"\$\s+|sudo\s+|curl\b|wget\b|"
    r"(?:ba|z|fi)?sh\b|python(?:3(?:\.\d+)?)?\b|node\b|"
    r"npm\b|npx\b|pnpm\b|yarn\b|git\b|claude\b|"
    r"rm\s+(?:--recursive(?:\s+--force)?|-[A-Za-z]*r[A-Za-z]*)\s+|"
    r"cat\s+(?:~?/\.ssh/|/etc/(?:passwd|shadow)|\S*(?:credential|secret|token|private[_-]?key))|"
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
_BEAT_KEY_RE = re.compile(r"(?<![A-Za-z0-9_-])(SC-[0-9]{2,})(?![A-Za-z0-9_-])", re.IGNORECASE)
_SCENE_KEY_RE = re.compile(
    r"(?<![A-Za-z0-9_-])(S[0-9]{2,})(?!-E[0-9])(?![A-Za-z0-9_-])",
    re.IGNORECASE,
)
_EXPLICIT_SHOT_RE = re.compile(
    r"(?<![A-Za-z0-9_-])([A-Za-z0-9][A-Za-z0-9._-]*-E[0-9]{2,3}-[0-9]{3}[a-z]?)(?![A-Za-z0-9_-])",
    re.IGNORECASE,
)
_VIEW_ID_RE = re.compile(r"^[0-9a-f]{32}$")


class StoryWorkspaceEpisodeAuxiliaryArtifactParseError(ValueError):
    """Safe parse failure that never echoes untrusted artifact content."""

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
class _CanonicalTarget:
    source_key: str
    view_id: str


class StoryWorkspaceEpisodeAuxiliaryArtifactAdapter:
    """Project auxiliary artifacts using explicit identifiers only."""

    def __init__(self, *, episode_uid: str, canonical_episode_root: str) -> None:
        try:
            self._namespace = UUID(hex=episode_uid)
        except (ValueError, AttributeError) as exc:
            raise ValueError("episode_uid must be a 32-character UUID hex value") from exc
        if self._namespace.hex != episode_uid.lower():
            raise ValueError("episode_uid must be a 32-character UUID hex value")
        if (
            not isinstance(canonical_episode_root, str)
            or not _CANONICAL_EPISODE_ROOT_RE.fullmatch(canonical_episode_root)
        ):
            raise ValueError("canonical_episode_root must identify one trusted Episode")
        self._canonical_episode_root = canonical_episode_root
        self._cursor_key = hashlib.sha256(
            b"story-workspace-episode-cursor\x00" + self._namespace.bytes
        ).digest()

    def project(
        self,
        *,
        prompts: Mapping[str, bytes] | None,
        prompt_revisions: Mapping[str, str] | None,
        render_guide: bytes | None,
        render_revision: str | None,
        review_report: bytes | None,
        review_revision: str | None,
        shot_view_ids: Mapping[str, str],
        narrative_beat_view_ids: Mapping[str, str],
        script_scene_view_ids: Mapping[str, str],
        manifest_revision: str,
        prompt_cursor: str | None = None,
        render_queue_cursor: str | None = None,
        page_limit: int = STORY_WORKSPACE_EPISODE_AUXILIARY_PAGE_MAX,
    ) -> StoryWorkspaceEpisodeAuxiliaryProjection:
        if not _MANIFEST_REVISION_RE.fullmatch(manifest_revision):
            raise ValueError("manifest_revision must be a sha256 revision")
        if page_limit < 1:
            raise ValueError("page_limit must be greater than or equal to 1")
        if page_limit > STORY_WORKSPACE_EPISODE_AUXILIARY_PAGE_MAX:
            raise ValueError("page_limit must be less than or equal to 100")

        known_shots = _canonical_targets(
            shot_view_ids,
            _SHOT_ID_RE,
            "shot_view_ids",
        )
        known_beats = _canonical_targets(
            narrative_beat_view_ids,
            re.compile(r"^SC-[0-9]{2,}$", re.IGNORECASE),
            "narrative_beat_view_ids",
        )
        known_scenes = _canonical_targets(
            script_scene_view_ids,
            re.compile(r"^S[0-9]{2,}$", re.IGNORECASE),
            "script_scene_view_ids",
        )
        prompt_items = self._project_prompts(
            prompts or {},
            prompt_revisions or {},
            known_shots,
        )
        render_sections: list[StoryWorkspaceEpisodeArtifactSection] = []
        queue_items: list[StoryWorkspaceEpisodeRenderQueueEntry] = []
        render_source_revision: str | None = None
        if render_guide is not None:
            render_source_revision = _source_revision(
                render_revision,
                render_guide,
                "renders/render-guide.md",
            )
            render_sections, queue_items = self._project_render_guide(
                render_guide,
                render_source_revision,
                known_shots,
            )
        review = (
            self._project_review(
                review_report,
                _source_revision(
                    review_revision,
                    review_report,
                    "review-report.md",
                ),
                known_beats,
                known_scenes,
                known_shots,
            )
            if review_report is not None
            else None
        )

        prompt_page = self._page_prompts(
            prompt_items,
            prompt_cursor,
            manifest_revision,
            page_limit,
        )
        queue_page = self._page_queue(
            queue_items,
            render_queue_cursor,
            manifest_revision,
            page_limit,
        )
        render = (
            StoryWorkspaceEpisodeRenderGuide(
                sections=render_sections,
                queue=queue_page,
                source_revision=render_source_revision,
            )
            if render_source_revision is not None
            else None
        )
        linked_prompt_shots = {
            item.shot_id
            for item in prompt_items
            if item.association_status is StoryWorkspaceEpisodeAssociationStatus.LINKED
        }
        linked_queue_shots = {
            item.shot_id
            for item in queue_items
            if item.association_status is StoryWorkspaceEpisodeAssociationStatus.LINKED
        }
        return StoryWorkspaceEpisodeAuxiliaryProjection(
            manifest_revision=manifest_revision,
            prompts=prompt_page,
            render_guide=render,
            review=review,
            associations=StoryWorkspaceEpisodeAuxiliaryAssociationDiagnostics(
                shot_prompt_coverage=_coverage(
                    len(linked_prompt_shots),
                    len(known_shots),
                ),
                shot_render_queue_coverage=_coverage(
                    len(linked_queue_shots),
                    len(known_shots),
                ),
                total_prompts=len(prompt_items),
                total_queue_entries=len(queue_items),
                orphan_prompts=sorted(
                    f"prompt:{item.shot_id}:{item.kind}"
                    for item in prompt_items
                    if item.association_status is StoryWorkspaceEpisodeAssociationStatus.ORPHAN
                ),
                orphan_queue_entries=sorted(
                    f"render-queue:{item.shot_id}"
                    for item in queue_items
                    if item.association_status is StoryWorkspaceEpisodeAssociationStatus.ORPHAN
                ),
                duplicate_queue_shot_ids=[],
            ),
        )

    def _view_id(self, kind: str, source_key: str) -> str:
        return uuid5(self._namespace, f"{kind}:{source_key}").hex

    def _project_prompts(
        self,
        files: Mapping[str, bytes],
        revisions: Mapping[str, str],
        known_shots: Mapping[str, _CanonicalTarget],
    ) -> list[StoryWorkspaceEpisodePrompt]:
        if len(files) > STORY_WORKSPACE_EPISODE_AUXILIARY_MAX_FILES:
            raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
                "prompts/",
                "file_limit",
            )
        if sum(len(content) for content in files.values()) > (
            STORY_WORKSPACE_EPISODE_AUXILIARY_COLLECTION_MAX_BYTES
        ):
            raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
                "prompts/",
                "byte_limit",
            )
        items: list[StoryWorkspaceEpisodePrompt] = []
        seen: set[tuple[str, str]] = set()
        for source_artifact in sorted(files):
            if not _valid_prompt_path(source_artifact):
                raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
                    "prompts/",
                    "invalid_artifact_path",
                )
            content = files[source_artifact]
            if not isinstance(content, bytes):
                raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
                    source_artifact,
                    "invalid_bytes",
                )
            source_revision = _source_revision(
                revisions.get(source_artifact),
                content,
                source_artifact,
            )
            documents = _safe_yaml_documents(
                content,
                source_artifact,
                max_bytes=STORY_WORKSPACE_EPISODE_AUXILIARY_YAML_MAX_BYTES,
            )
            for document in documents:
                if document is None:
                    continue
                if not isinstance(document, Mapping):
                    raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
                        source_artifact,
                        "invalid_shape",
                    )
                shots = document.get("shots", [])
                if not isinstance(shots, list):
                    raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
                        source_artifact,
                        "invalid_shape",
                    )
                for raw in shots:
                    if not isinstance(raw, Mapping):
                        raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
                            source_artifact,
                            "invalid_shape",
                        )
                    shot_id = _required_key(raw.get("shot_id"), _SHOT_ID_RE, source_artifact)
                    raw_kind = raw.get("prompt_kind", raw.get("kind", "default"))
                    kind = _required_key(raw_kind, _PROMPT_KIND_RE, source_artifact).lower()
                    target = known_shots.get(_ascii_lookup_key(shot_id))
                    canonical_shot_id = (
                        target.source_key if target is not None else shot_id
                    )
                    identity = (_ascii_lookup_key(canonical_shot_id), kind)
                    if identity in seen:
                        raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
                            source_artifact,
                            "duplicate_prompt_identity",
                        )
                    seen.add(identity)
                    params = _mapping(raw.get("params"), source_artifact)
                    generability = _mapping(raw.get("generability"), source_artifact)
                    items.append(
                        StoryWorkspaceEpisodePrompt(
                            id=self._view_id(
                                "prompt",
                                f"{canonical_shot_id}:{kind}",
                            ),
                            shot_id=canonical_shot_id,
                            kind=kind,
                            shot_view_id=(
                                target.view_id if target is not None else None
                            ),
                            association_status=(
                                StoryWorkspaceEpisodeAssociationStatus.LINKED
                                if target is not None
                                else StoryWorkspaceEpisodeAssociationStatus.ORPHAN
                            ),
                            positive=_required_text(
                                raw.get("positive"),
                                8000,
                                source_artifact,
                            ),
                            negative=_optional_text(
                                raw.get("negative"),
                                4000,
                                source_artifact,
                            ),
                            parameters=StoryWorkspaceEpisodePromptParameters(
                                model=_optional_text(params.get("model"), 128, source_artifact),
                                mode=_optional_text(params.get("mode"), 128, source_artifact),
                                duration_sec=_optional_number(
                                    params.get("duration"),
                                    source_artifact,
                                ),
                                motion_strength=_optional_number(
                                    params.get("motion_strength"),
                                    source_artifact,
                                ),
                                camera_motion=_optional_text(
                                    params.get("camera_motion"),
                                    255,
                                    source_artifact,
                                ),
                                aspect_ratio=_optional_text(
                                    params.get("aspect_ratio"),
                                    32,
                                    source_artifact,
                                ),
                            ),
                            generability=StoryWorkspaceEpisodePromptGenerability(
                                character_anchor=_optional_text(
                                    generability.get("character_anchor"),
                                    128,
                                    source_artifact,
                                ),
                                motion_feasibility=_optional_text(
                                    generability.get("motion_feasibility"),
                                    128,
                                    source_artifact,
                                ),
                                duration_budget=_optional_text(
                                    generability.get("duration_budget"),
                                    128,
                                    source_artifact,
                                ),
                                notes=_optional_text(
                                    generability.get("notes"),
                                    2000,
                                    source_artifact,
                                    empty_is_none=False,
                                ),
                            ),
                            source_artifact=source_artifact,
                            source_revision=source_revision,
                        )
                    )
                    if len(items) > STORY_WORKSPACE_EPISODE_AUXILIARY_MAX_ITEMS:
                        raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
                            "prompts/",
                            "item_limit",
                        )
        return items

    def _project_render_guide(
        self,
        content: bytes,
        source_revision: str,
        known_shots: Mapping[str, _CanonicalTarget],
    ) -> tuple[
        list[StoryWorkspaceEpisodeArtifactSection],
        list[StoryWorkspaceEpisodeRenderQueueEntry],
    ]:
        artifact = "renders/render-guide.md"
        document = _parse_markdown(content, artifact)
        raw_sections = _markdown_sections(document.body, artifact)
        sections = self._artifact_sections(raw_sections, artifact, source_revision)
        queue: list[StoryWorkspaceEpisodeRenderQueueEntry] = []
        seen: set[str] = set()
        for section in raw_sections:
            if _normalized_title(section.title) not in {
                "渲染队列",
                "render queue",
            }:
                continue
            for match in _YAML_FENCE_RE.finditer("\n".join(section.lines)):
                documents = _safe_yaml_documents(
                    match.group(1).encode("utf-8"),
                    artifact,
                    max_bytes=STORY_WORKSPACE_EPISODE_AUXILIARY_YAML_MAX_BYTES,
                )
                for loaded in documents:
                    rows = loaded.get("queue") if isinstance(loaded, Mapping) else loaded
                    if not isinstance(rows, list):
                        raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
                            artifact,
                            "invalid_queue_shape",
                        )
                    for raw in rows:
                        if not isinstance(raw, Mapping):
                            raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
                                artifact,
                                "invalid_queue_shape",
                            )
                        shot_id = _required_key(raw.get("shot_id"), _SHOT_ID_RE, artifact)
                        target = known_shots.get(_ascii_lookup_key(shot_id))
                        canonical_shot_id = (
                            target.source_key if target is not None else shot_id
                        )
                        identity = _ascii_lookup_key(canonical_shot_id)
                        if identity in seen:
                            raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
                                artifact,
                                "duplicate_queue_shot_id",
                            )
                        seen.add(identity)
                        queue.append(
                            StoryWorkspaceEpisodeRenderQueueEntry(
                                id=self._view_id(
                                    "render-queue",
                                    canonical_shot_id,
                                ),
                                shot_id=canonical_shot_id,
                                shot_view_id=(
                                    target.view_id if target is not None else None
                                ),
                                association_status=(
                                    StoryWorkspaceEpisodeAssociationStatus.LINKED
                                    if target is not None
                                    else StoryWorkspaceEpisodeAssociationStatus.ORPHAN
                                ),
                                duration_sec=_duration_seconds(raw.get("duration"), artifact),
                                risk=_optional_text(raw.get("risk"), 128, artifact),
                                priority=_optional_text(raw.get("priority"), 64, artifact),
                                renderer=_renderer_identity(raw.get("tool"), artifact),
                                status=_optional_text(raw.get("status"), 64, artifact),
                                source_revision=source_revision,
                            )
                        )
                        if len(queue) > STORY_WORKSPACE_EPISODE_AUXILIARY_MAX_ITEMS:
                            raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
                                artifact,
                                "item_limit",
                            )
        return sections, queue

    def _project_review(
        self,
        content: bytes,
        source_revision: str,
        known_beats: Mapping[str, _CanonicalTarget],
        known_scenes: Mapping[str, _CanonicalTarget],
        known_shots: Mapping[str, _CanonicalTarget],
    ) -> StoryWorkspaceEpisodeReviewReport:
        artifact = "review-report.md"
        document = _parse_markdown(content, artifact)
        raw_sections = _markdown_sections(document.body, artifact)
        sections = self._artifact_sections(raw_sections, artifact, source_revision)
        reviewed_artifacts, reviewed_revisions = _reviewed_sources(
            document.metadata.get("reviewed_files"),
            artifact,
            self._canonical_episode_root,
        )
        explicit_revisions = _reviewed_revision_mapping(
            document.metadata.get("source_revisions"),
            artifact,
            self._canonical_episode_root,
        )
        merged_source_revisions = _merge_reviewed_source_revisions(
            reviewed_revisions,
            explicit_revisions,
            artifact,
        )
        scope = _review_scope(document.metadata.get("scope"), reviewed_artifacts, artifact)
        targets: list[StoryWorkspaceEpisodeReviewTarget] = []
        seen_targets: dict[
            tuple[StoryWorkspaceEpisodeReviewTargetKind, str],
            str,
        ] = {}
        for raw_section, section in zip(raw_sections, sections, strict=True):
            searchable = f"{raw_section.title}\n{'\n'.join(raw_section.lines)}"
            target_specs = (
                (
                    StoryWorkspaceEpisodeReviewTargetKind.NARRATIVE_BEAT,
                    _ordered_matches(_BEAT_KEY_RE, searchable),
                    known_beats,
                ),
                (
                    StoryWorkspaceEpisodeReviewTargetKind.SCRIPT_SCENE,
                    _ordered_matches(_SCENE_KEY_RE, searchable),
                    known_scenes,
                ),
                (
                    StoryWorkspaceEpisodeReviewTargetKind.SHOT,
                    _ordered_matches(_EXPLICIT_SHOT_RE, searchable),
                    known_shots,
                ),
            )
            for kind, keys, known in target_specs:
                for source_key in keys:
                    lookup_key = _ascii_lookup_key(source_key)
                    locator = (kind, lookup_key)
                    previous = seen_targets.get(locator)
                    if previous is not None:
                        if previous == source_key:
                            continue
                        raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
                            artifact,
                            "duplicate_review_target_identity",
                        )
                    seen_targets[locator] = source_key
                    target = known.get(lookup_key)
                    canonical_source_key = (
                        target.source_key if target is not None else source_key
                    )
                    targets.append(
                        StoryWorkspaceEpisodeReviewTarget(
                            id=self._view_id(
                                "review-target",
                                f"{kind.value}:{canonical_source_key}",
                            ),
                            kind=kind,
                            source_key=canonical_source_key,
                            target_view_id=(
                                target.view_id if target is not None else None
                            ),
                            association_status=(
                                StoryWorkspaceEpisodeAssociationStatus.LINKED
                                if target is not None
                                else StoryWorkspaceEpisodeAssociationStatus.ORPHAN
                            ),
                            section_id=section.id,
                            source_revision=source_revision,
                        )
                    )
        verdict = _optional_text(
            document.metadata.get("overall_verdict"),
            64,
            artifact,
        )
        if verdict is not None:
            verdict = verdict.upper()
        return StoryWorkspaceEpisodeReviewReport(
            scope=scope,
            overall_verdict=verdict,
            reviewed_artifacts=reviewed_artifacts,
            source_revisions=merged_source_revisions,
            sections=sections,
            targets=targets,
            source_revision=source_revision,
        )

    def _artifact_sections(
        self,
        raw_sections: Sequence[_MarkdownSection],
        artifact: str,
        source_revision: str,
    ) -> list[StoryWorkspaceEpisodeArtifactSection]:
        sections: list[StoryWorkspaceEpisodeArtifactSection] = []
        kind = "render-section" if artifact.startswith("renders/") else "review-section"
        for ordinal, raw in enumerate(raw_sections):
            sections.append(
                StoryWorkspaceEpisodeArtifactSection(
                    id=self._view_id(
                        f"{kind}-revision",
                        f"{source_revision}:{ordinal}",
                    ),
                    level=raw.level,
                    title=_bounded_text(raw.title, 500, artifact),
                    text=_section_plain_text(raw.lines, artifact),
                    source_artifact=artifact,
                    source_revision=source_revision,
                )
            )
        return sections

    def _page_prompts(
        self,
        items: Sequence[StoryWorkspaceEpisodePrompt],
        cursor: str | None,
        manifest_revision: str,
        limit: int,
    ) -> StoryWorkspaceEpisodePromptPage:
        page, next_cursor = self._page(
            items,
            cursor,
            "prompts",
            manifest_revision,
            limit,
        )
        return StoryWorkspaceEpisodePromptPage(
            items=page,
            total=len(items),
            next_cursor=next_cursor,
        )

    def _page_queue(
        self,
        items: Sequence[StoryWorkspaceEpisodeRenderQueueEntry],
        cursor: str | None,
        manifest_revision: str,
        limit: int,
    ) -> StoryWorkspaceEpisodeRenderQueuePage:
        page, next_cursor = self._page(
            items,
            cursor,
            "render-queue",
            manifest_revision,
            limit,
        )
        return StoryWorkspaceEpisodeRenderQueuePage(
            items=page,
            total=len(items),
            next_cursor=next_cursor,
        )

    def _page(
        self,
        items: Sequence[Any],
        cursor: str | None,
        kind: str,
        manifest_revision: str,
        limit: int,
    ) -> tuple[list[Any], str | None]:
        start = 0
        if cursor is not None:
            after = self._decode_cursor(cursor, kind, manifest_revision)
            matching = [index for index, item in enumerate(items) if item.id == after]
            if len(matching) != 1:
                raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
                    kind,
                    "invalid_cursor",
                )
            start = matching[0] + 1
        page = list(items[start : start + limit])
        next_cursor = None
        if page and start + len(page) < len(items):
            next_cursor = self._encode_cursor(kind, manifest_revision, page[-1].id)
        return page, next_cursor

    def _encode_cursor(self, kind: str, revision: str, after: str) -> str:
        payload = json.dumps(
            {"v": 1, "kind": kind, "revision": revision, "after": after},
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        encoded = base64.urlsafe_b64encode(payload).rstrip(b"=")
        signature = hmac.new(self._cursor_key, encoded, hashlib.sha256).digest()
        return (
            base64.urlsafe_b64encode(signature).rstrip(b"=").decode("ascii")
            + "."
            + encoded.decode("ascii")
        )

    def _decode_cursor(self, cursor: str, kind: str, revision: str) -> str:
        try:
            encoded_signature, encoded = cursor.split(".", 1)
            signature = _base64url_decode(encoded_signature)
            expected = hmac.new(
                self._cursor_key,
                encoded.encode("ascii"),
                hashlib.sha256,
            ).digest()
            if not hmac.compare_digest(signature, expected):
                raise ValueError
            raw = _base64url_decode(encoded)
            payload = json.loads(raw.decode("utf-8"))
            if (
                not isinstance(payload, dict)
                or payload.get("v") != 1
                or payload.get("kind") != kind
                or not isinstance(payload.get("after"), str)
            ):
                raise ValueError
        except (ValueError, TypeError, UnicodeError, json.JSONDecodeError) as exc:
            raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
                kind,
                "invalid_cursor",
            ) from exc
        if payload.get("revision") != revision:
            raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
                kind,
                "stale_cursor",
            )
        return payload["after"]


def _base64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _ascii_lookup_key(value: str) -> str:
    return value.upper()


def _canonical_targets(
    values: Mapping[str, str],
    pattern: re.Pattern[str],
    field: str,
) -> dict[str, _CanonicalTarget]:
    if not isinstance(values, Mapping):
        raise ValueError(f"{field} must be a source-key-to-view-ID mapping")
    targets: dict[str, _CanonicalTarget] = {}
    for source_key, view_id in values.items():
        if (
            not isinstance(source_key, str)
            or not source_key.isascii()
            or source_key != source_key.strip()
            or pattern.fullmatch(source_key) is None
            or not isinstance(view_id, str)
            or _VIEW_ID_RE.fullmatch(view_id) is None
        ):
            raise ValueError(f"{field} contains an invalid canonical target")
        lookup_key = _ascii_lookup_key(source_key)
        if lookup_key in targets:
            raise ValueError(f"{field} contains a canonical key collision")
        targets[lookup_key] = _CanonicalTarget(
            source_key=source_key,
            view_id=view_id,
        )
    return targets


def _valid_prompt_path(value: str) -> bool:
    if not isinstance(value, str) or "\\" in value or "\x00" in value:
        return False
    path = PurePosixPath(value)
    return (
        not path.is_absolute()
        and len(path.parts) == 2
        and path.parts[0] == "prompts"
        and path.parts[1] not in {"", ".", ".."}
        and path.suffix.lower() in {".yml", ".yaml"}
        and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,254}", path.name)
        is not None
    )


def _source_revision(value: str | None, content: bytes, artifact: str) -> str:
    revision = value or "sha256:" + hashlib.sha256(content).hexdigest()
    if not isinstance(revision, str) or not _REVISION_RE.fullmatch(revision):
        raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
            artifact,
            "invalid_source_revision",
        )
    return revision


def _safe_yaml_documents(
    content: bytes,
    artifact: str,
    *,
    max_bytes: int,
) -> list[Any]:
    if len(content) > max_bytes:
        raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(artifact, "byte_limit")
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
            artifact,
            "invalid_utf8",
        ) from exc
    if _HTML_RE.search(text):
        raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
            artifact,
            "html_forbidden",
        )
    try:
        depth = 0
        nodes = 0
        collection_kinds: list[str] = []
        collection_direct_nodes: list[int] = []
        documents_seen = 0
        for event in yaml.parse(text):
            if isinstance(event, DocumentStartEvent):
                documents_seen += 1
                if (
                    documents_seen
                    > STORY_WORKSPACE_EPISODE_AUXILIARY_MAX_YAML_DOCUMENTS
                ):
                    raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
                        artifact,
                        "document_limit",
                    )
            if isinstance(event, AliasEvent):
                raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
                    artifact,
                    "yaml_alias_forbidden",
                )
            if isinstance(event, CollectionStartEvent):
                if collection_direct_nodes:
                    collection_direct_nodes[-1] += 1
                collection_kinds.append(
                    "mapping" if isinstance(event, MappingStartEvent) else "sequence"
                )
                collection_direct_nodes.append(0)
                depth += 1
                if depth > STORY_WORKSPACE_EPISODE_AUXILIARY_MAX_YAML_DEPTH:
                    raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
                        artifact,
                        "depth_limit",
                    )
            elif isinstance(event, CollectionEndEvent):
                kind = collection_kinds.pop()
                direct_nodes = collection_direct_nodes.pop()
                if (
                    kind == "mapping"
                    and direct_nodes // 2
                    > STORY_WORKSPACE_EPISODE_AUXILIARY_MAX_MAPPING_ITEMS
                ):
                    raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
                        artifact,
                        "mapping_item_limit",
                    )
                depth -= 1
            elif isinstance(event, ScalarEvent) and collection_direct_nodes:
                collection_direct_nodes[-1] += 1
            if isinstance(event, NodeEvent):
                nodes += 1
                if nodes > STORY_WORKSPACE_EPISODE_AUXILIARY_MAX_YAML_NODES:
                    raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
                        artifact,
                        "node_limit",
                    )
        documents = list(yaml.safe_load_all(text))
    except StoryWorkspaceEpisodeAuxiliaryArtifactParseError:
        raise
    except yaml.YAMLError as exc:
        raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
            artifact,
            "invalid_yaml",
        ) from exc
    if len(documents) > STORY_WORKSPACE_EPISODE_AUXILIARY_MAX_YAML_DOCUMENTS:
        raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
            artifact,
            "document_limit",
        )
    _validate_loaded_yaml(documents, artifact)
    return documents


def _validate_loaded_yaml(values: Sequence[Any], artifact: str) -> None:
    def visit(value: Any, depth: int) -> None:
        if depth > STORY_WORKSPACE_EPISODE_AUXILIARY_MAX_YAML_DEPTH:
            raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
                artifact,
                "depth_limit",
            )
        if isinstance(value, str):
            if len(value) > STORY_WORKSPACE_EPISODE_AUXILIARY_MAX_SCALAR_CHARS:
                raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
                    artifact,
                    "scalar_limit",
                )
            if _HTML_RE.search(value):
                raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
                    artifact,
                    "html_forbidden",
                )
            if _CONTROL_RE.search(value):
                raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
                    artifact,
                    "control_character",
                )
            return
        if isinstance(value, Mapping):
            if len(value) > STORY_WORKSPACE_EPISODE_AUXILIARY_MAX_MAPPING_ITEMS:
                raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
                    artifact,
                    "mapping_item_limit",
                )
            for key, child in value.items():
                if not isinstance(key, (str, int, float, bool)) and key is not None:
                    raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
                        artifact,
                        "invalid_shape",
                    )
                visit(key, depth + 1)
                visit(child, depth + 1)
            return
        if isinstance(value, list):
            if len(value) > STORY_WORKSPACE_EPISODE_AUXILIARY_MAX_ITEMS:
                raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
                    artifact,
                    "item_limit",
                )
            for child in value:
                visit(child, depth + 1)
            return
        if value is not None and not isinstance(
            value,
            (int, float, bool, date, datetime),
        ):
            raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
                artifact,
                "invalid_shape",
            )

    for document in values:
        visit(document, 0)


def _parse_markdown(content: bytes, artifact: str) -> _MarkdownDocument:
    if len(content) > STORY_WORKSPACE_EPISODE_AUXILIARY_MARKDOWN_MAX_BYTES:
        raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(artifact, "byte_limit")
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
            artifact,
            "invalid_utf8",
        ) from exc
    if _HTML_RE.search(text):
        raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
            artifact,
            "html_forbidden",
        )
    if _CONTROL_RE.search(text):
        raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
            artifact,
            "control_character",
        )
    metadata: Mapping[str, Any] = {}
    body = text
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end < 0:
            raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
                artifact,
                "invalid_frontmatter",
            )
        documents = _safe_yaml_documents(
            text[4:end].encode("utf-8"),
            artifact,
            max_bytes=STORY_WORKSPACE_EPISODE_AUXILIARY_MARKDOWN_MAX_BYTES,
        )
        if len(documents) != 1 or not isinstance(documents[0], Mapping):
            raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
                artifact,
                "invalid_frontmatter",
            )
        metadata = documents[0]
        body = text[end + 5 :]
    return _MarkdownDocument(metadata=metadata, body=body)


def _markdown_sections(body: str, artifact: str) -> list[_MarkdownSection]:
    sections: list[_MarkdownSection] = []
    level: int | None = None
    title: str | None = None
    lines: list[str] = []
    for line in body.splitlines():
        if len(line) > STORY_WORKSPACE_EPISODE_AUXILIARY_MAX_SCALAR_CHARS:
            raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
                artifact,
                "line_limit",
            )
        match = _HEADING_RE.fullmatch(line)
        if match is None:
            if title is not None:
                lines.append(line)
            continue
        if title is not None and level is not None:
            sections.append(_MarkdownSection(level, title, tuple(lines)))
        level = len(match.group(1))
        title = _bounded_text(match.group(2), 500, artifact)
        lines = []
    if title is not None and level is not None:
        sections.append(_MarkdownSection(level, title, tuple(lines)))
    if len(sections) > STORY_WORKSPACE_EPISODE_AUXILIARY_MAX_SECTIONS:
        raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
            artifact,
            "section_limit",
        )
    return sections


def _section_plain_text(lines: Sequence[str], artifact: str) -> str:
    safe_lines: list[str] = []
    in_fence = False
    for line in lines:
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        safe_lines.append(line)
    value = "\n".join(safe_lines).strip()
    return _bounded_text(value, 8000, artifact, empty_allowed=True)


def _normalized_title(value: str) -> str:
    return " ".join(value.casefold().split())


def _mapping(value: Any, artifact: str) -> Mapping[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
            artifact,
            "invalid_shape",
        )
    return value


def _required_key(value: Any, pattern: re.Pattern[str], artifact: str) -> str:
    if (
        not isinstance(value, str)
        or not value.isascii()
        or value != value.strip()
        or not pattern.fullmatch(value)
    ):
        raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
            artifact,
            "invalid_explicit_key",
        )
    return value


def _required_text(value: Any, limit: int, artifact: str) -> str:
    result = _optional_text(value, limit, artifact)
    if result is None:
        raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
            artifact,
            "required_text_missing",
        )
    return result


def _optional_text(
    value: Any,
    limit: int,
    artifact: str,
    *,
    empty_is_none: bool = True,
) -> str | None:
    if value is None:
        return None
    if not isinstance(value, (str, int, float, bool, date, datetime)):
        raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
            artifact,
            "invalid_scalar",
        )
    result = str(value).strip()
    if not result and empty_is_none:
        return None
    return _bounded_text(result, limit, artifact, empty_allowed=not empty_is_none)


def _bounded_text(
    value: str,
    limit: int,
    artifact: str,
    *,
    empty_allowed: bool = False,
) -> str:
    if not value and not empty_allowed:
        raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(artifact, "text_limit")
    if len(value) > limit:
        raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(artifact, "text_limit")
    if _HTML_RE.search(value):
        raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
            artifact,
            "html_forbidden",
        )
    if _CONTROL_RE.search(value):
        raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
            artifact,
            "control_character",
        )
    if _ABSOLUTE_PATH_RE.search(value):
        raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
            artifact,
            "sensitive_text",
        )
    if _CREDENTIAL_RE.search(value):
        raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
            artifact,
            "credential_forbidden",
        )
    if _PRIVATE_MODEL_TEXT_RE.search(value):
        raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
            artifact,
            "sensitive_text",
        )
    if _looks_like_high_entropy_secret(value):
        raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
            artifact,
            "credential_forbidden",
        )
    if (
        _RAW_COMMAND_RE.search(value)
        or _SENSITIVE_CLI_FLAG_RE.search(value)
        or _contains_raw_tool_option(value)
    ):
        raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
            artifact,
            "raw_command_forbidden",
        )
    return value


def _contains_raw_tool_option(value: str) -> bool:
    """Scan each bounded line linearly without a distance window or wildcard."""

    for line in value.splitlines():
        context = _RAW_TOOL_CONTEXT_RE.search(line)
        if (
            context is not None
            and _CLI_OPTION_RE.search(line, context.end()) is not None
        ):
            return True
    return False


def _looks_like_high_entropy_secret(value: str) -> bool:
    """Mirror the Dream Agent public-text entropy guard at file boundaries."""

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


def _optional_number(value: Any, artifact: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
            artifact,
            "invalid_number",
        )
    return float(value)


def _duration_seconds(value: Any, artifact: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, str):
        match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)s", value.strip())
        if match is None:
            raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
                artifact,
                "invalid_duration",
            )
        return float(match.group(1))
    return _optional_number(value, artifact)


def _renderer_identity(value: Any, artifact: str) -> str | None:
    if value is None:
        return None
    if (
        not isinstance(value, str)
        or not _RENDERER_IDENTITY_RE.fullmatch(value.strip())
    ):
        raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
            artifact,
            "unsafe_renderer",
        )
    return value.strip()


def _reviewed_sources(
    value: Any,
    artifact: str,
    canonical_episode_root: str,
) -> tuple[list[str], list[StoryWorkspaceEpisodeReviewedSourceRevision]]:
    if value is None:
        return [], []
    if not isinstance(value, list) or len(value) > 256:
        raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
            artifact,
            "invalid_reviewed_files",
        )
    keys: list[str] = []
    revisions: list[StoryWorkspaceEpisodeReviewedSourceRevision] = []
    for raw in value:
        revision: Any = None
        if isinstance(raw, str):
            path = raw
        elif isinstance(raw, Mapping):
            path = raw.get("path")
            revision = raw.get("revision")
        else:
            raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
                artifact,
                "invalid_reviewed_files",
            )
        key = _canonical_reviewed_artifact(
            path,
            artifact,
            canonical_episode_root,
        )
        if key in keys:
            raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
                artifact,
                "canonical_source_collision",
            )
        keys.append(key)
        if revision is not None:
            revisions.append(
                StoryWorkspaceEpisodeReviewedSourceRevision(
                    source_artifact=key,
                    source_revision=_explicit_revision(revision, artifact),
                )
            )
    return keys, revisions


def _reviewed_revision_mapping(
    value: Any,
    artifact: str,
    canonical_episode_root: str,
) -> list[StoryWorkspaceEpisodeReviewedSourceRevision]:
    if value is None:
        return []
    if not isinstance(value, Mapping) or len(value) > 256:
        raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
            artifact,
            "invalid_source_revisions",
        )
    results: list[StoryWorkspaceEpisodeReviewedSourceRevision] = []
    seen: set[str] = set()
    for path, revision in value.items():
        key = _canonical_reviewed_artifact(
            path,
            artifact,
            canonical_episode_root,
        )
        if key in seen:
            raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
                artifact,
                "canonical_source_collision",
            )
        seen.add(key)
        results.append(
            StoryWorkspaceEpisodeReviewedSourceRevision(
                source_artifact=key,
                source_revision=_explicit_revision(revision, artifact),
            )
        )
    return results


def _merge_reviewed_source_revisions(
    reviewed_revisions: Sequence[StoryWorkspaceEpisodeReviewedSourceRevision],
    explicit_revisions: Sequence[StoryWorkspaceEpisodeReviewedSourceRevision],
    artifact: str,
) -> list[StoryWorkspaceEpisodeReviewedSourceRevision]:
    """Deduplicate equal canonical facts and reject conflicting provenance."""

    merged: dict[str, StoryWorkspaceEpisodeReviewedSourceRevision] = {}
    for item in (*reviewed_revisions, *explicit_revisions):
        existing = merged.get(item.source_artifact)
        if existing is None:
            merged[item.source_artifact] = item
            continue
        if existing.source_revision != item.source_revision:
            raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
                artifact,
                "source_revision_conflict",
            )
    return sorted(merged.values(), key=lambda item: item.source_artifact)


def _canonical_reviewed_artifact(
    value: Any,
    artifact: str,
    canonical_episode_root: str,
) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value.startswith("/")
        or "\\" in value
        or "\x00" in value
    ):
        raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
            artifact,
            "unsafe_reviewed_path",
        )
    path = PurePosixPath(value)
    if ".." in path.parts:
        raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
            artifact,
            "unsafe_reviewed_path",
        )
    value_path = path.as_posix()
    root_prefix = canonical_episode_root + "/"
    if value_path.startswith(root_prefix):
        relative = value_path[len(root_prefix) :]
    elif value_path.startswith("stories/"):
        raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
            artifact,
            "reviewed_path_outside_episode",
        )
    else:
        relative = value_path
    relative_path = PurePosixPath(relative)
    if relative_path.name in {
        "episode-outline.md",
        "script.md",
        "storyboard.yaml",
    } and len(relative_path.parts) == 1:
        return relative_path.name
    if (
        len(relative_path.parts) == 2
        and relative_path.parts[0] == "prompts"
        and relative_path.suffix.lower() in {
        ".yml",
        ".yaml",
        }
        and re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9._-]{0,254}",
            relative_path.name,
        )
    ):
        return f"prompts/{relative_path.name}"
    if relative_path.parts == ("renders", "render-guide.md"):
        return "renders/render-guide.md"
    raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
        artifact,
        "invalid_reviewed_file",
    )


def _explicit_revision(value: Any, artifact: str) -> str:
    if not isinstance(value, str) or not _REVISION_RE.fullmatch(value):
        raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
            artifact,
            "invalid_source_revision",
        )
    return value


def _review_scope(
    value: Any,
    reviewed_artifacts: Sequence[str],
    artifact: str,
) -> StoryWorkspaceEpisodeReviewScope:
    if value is not None:
        if not isinstance(value, str):
            raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
                artifact,
                "invalid_review_scope",
            )
        normalized = value.strip().casefold().replace("_", "-")
        if normalized == "script":
            return StoryWorkspaceEpisodeReviewScope.SCRIPT
        if normalized == "full-chain":
            return StoryWorkspaceEpisodeReviewScope.FULL_CHAIN
        if normalized not in {"", "unknown"}:
            raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
                artifact,
                "invalid_review_scope",
            )
    reviewed = set(reviewed_artifacts)
    if reviewed == {"script.md"}:
        return StoryWorkspaceEpisodeReviewScope.SCRIPT
    if {
        "episode-outline.md",
        "script.md",
        "storyboard.yaml",
    }.issubset(reviewed) and any(key.startswith("prompts/") for key in reviewed):
        return StoryWorkspaceEpisodeReviewScope.FULL_CHAIN
    return StoryWorkspaceEpisodeReviewScope.UNKNOWN


def _ordered_matches(pattern: re.Pattern[str], value: str) -> list[str]:
    seen: set[str] = set()
    results: list[str] = []
    for match in pattern.finditer(value):
        key = match.group(1)
        if key not in seen:
            seen.add(key)
            results.append(key)
    return results


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
