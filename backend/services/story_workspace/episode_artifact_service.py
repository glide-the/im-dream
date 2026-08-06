"""Pinned, allowlisted Episode artifact reader and aggregate surface builder."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Mapping

from pydantic import ValidationError

try:
    from services.story_workspace.episode_artifact_adapter import (
        STORY_WORKSPACE_EPISODE_MARKDOWN_MAX_BYTES,
        STORY_WORKSPACE_EPISODE_YAML_MAX_BYTES,
        StoryWorkspaceEpisodeArtifactAdapter,
        StoryWorkspaceEpisodeArtifactParseError,
    )
    from services.story_workspace.episode_auxiliary_artifact_adapter import (
        STORY_WORKSPACE_EPISODE_AUXILIARY_COLLECTION_MAX_BYTES,
        STORY_WORKSPACE_EPISODE_AUXILIARY_MARKDOWN_MAX_BYTES,
        STORY_WORKSPACE_EPISODE_AUXILIARY_MAX_FILES,
        STORY_WORKSPACE_EPISODE_AUXILIARY_YAML_MAX_BYTES,
        StoryWorkspaceEpisodeAuxiliaryArtifactAdapter,
        StoryWorkspaceEpisodeAuxiliaryArtifactParseError,
    )
    from story_workspace.contracts import (
        StoryWorkspaceEpisodeArtifactAvailability,
        StoryWorkspaceEpisodeArtifactConsumer,
        StoryWorkspaceEpisodeArtifactManifestEntry,
        StoryWorkspaceEpisodeArtifactSurface,
        StoryWorkspaceEpisodeBindingAvailability,
        StoryWorkspaceEpisodeBindingFile,
        StoryWorkspaceEpisodeBindingRecovery,
        StoryWorkspaceEpisodeProducerAction,
        StoryWorkspaceEpisodeReviewScope,
    )
except ModuleNotFoundError:  # Support repository-root package imports.
    from backend.services.story_workspace.episode_artifact_adapter import (
        STORY_WORKSPACE_EPISODE_MARKDOWN_MAX_BYTES,
        STORY_WORKSPACE_EPISODE_YAML_MAX_BYTES,
        StoryWorkspaceEpisodeArtifactAdapter,
        StoryWorkspaceEpisodeArtifactParseError,
    )
    from backend.services.story_workspace.episode_auxiliary_artifact_adapter import (
        STORY_WORKSPACE_EPISODE_AUXILIARY_COLLECTION_MAX_BYTES,
        STORY_WORKSPACE_EPISODE_AUXILIARY_MARKDOWN_MAX_BYTES,
        STORY_WORKSPACE_EPISODE_AUXILIARY_MAX_FILES,
        STORY_WORKSPACE_EPISODE_AUXILIARY_YAML_MAX_BYTES,
        StoryWorkspaceEpisodeAuxiliaryArtifactAdapter,
        StoryWorkspaceEpisodeAuxiliaryArtifactParseError,
    )
    from backend.story_workspace.contracts import (
        StoryWorkspaceEpisodeArtifactAvailability,
        StoryWorkspaceEpisodeArtifactConsumer,
        StoryWorkspaceEpisodeArtifactManifestEntry,
        StoryWorkspaceEpisodeArtifactSurface,
        StoryWorkspaceEpisodeBindingAvailability,
        StoryWorkspaceEpisodeBindingFile,
        StoryWorkspaceEpisodeBindingRecovery,
        StoryWorkspaceEpisodeProducerAction,
        StoryWorkspaceEpisodeReviewScope,
    )


_RUN_ID_RE = re.compile(r"^run_[0-9a-f]{32}$")
_STORY_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_PROJECT_ID_RE = re.compile(
    r"^project_id:\s*(?:['\"])?([a-z0-9]+(?:-[a-z0-9]+)*)(?:['\"])?\s*$",
    re.MULTILINE,
)
_SAFE_DIRECTORY_ENTRY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,254}$")
_BINDING_MAX_BYTES = 16 * 1024
_PROJECT_MAX_BYTES = 256 * 1024
_EPISODE_AUTHORITY_SCHEMA = "story-workspace-episode-authority/v1"


class StoryWorkspaceEpisodeArtifactError(RuntimeError):
    """Base safe error for the actor-authorized Episode file projection."""


class StoryWorkspaceEpisodeArtifactPathError(StoryWorkspaceEpisodeArtifactError):
    """A path, symlink, or pinned inode violated the trusted root."""


class StoryWorkspaceEpisodeArtifactContractError(StoryWorkspaceEpisodeArtifactError):
    """A persisted binding or bounded artifact violates its public contract."""

    def __init__(self, message: str, *, fact_revision: str | None = None) -> None:
        self.fact_revision = fact_revision
        super().__init__(message)


class StoryWorkspaceEpisodeArtifactUnavailableError(StoryWorkspaceEpisodeArtifactError):
    """A verified artifact root had a bounded transient content-read failure."""

    def __init__(self, relative_key: str) -> None:
        self.relative_key = relative_key
        super().__init__("verified artifact content is temporarily unavailable")


@dataclass(frozen=True)
class StoryWorkspaceEpisodeAuthority:
    """Frozen launch-message authority; never derived from Episode files."""

    workflow_run_id: str
    episode_uid: str
    story_slug: str
    episode_code: str

    @classmethod
    def parse(
        cls,
        value: object,
        *,
        expected_run_id: str,
    ) -> "StoryWorkspaceEpisodeAuthority | None":
        if isinstance(value, cls):
            value = {
                "schema": _EPISODE_AUTHORITY_SCHEMA,
                "workflow_run_id": value.workflow_run_id,
                "episode_uid": value.episode_uid,
                "story_slug": value.story_slug,
                "episode_code": value.episode_code,
            }
        if not isinstance(value, Mapping) or set(value) != {
            "schema",
            "workflow_run_id",
            "episode_uid",
            "story_slug",
            "episode_code",
        }:
            return None
        if (
            value.get("schema") != _EPISODE_AUTHORITY_SCHEMA
            or value.get("workflow_run_id") != expected_run_id
            or not isinstance(value.get("episode_uid"), str)
            or re.fullmatch(r"[0-9a-f]{32}", value["episode_uid"]) is None
            or not isinstance(value.get("story_slug"), str)
            or _STORY_SLUG_RE.fullmatch(value["story_slug"]) is None
            or value.get("episode_code") != "EP01"
        ):
            return None
        return cls(
            workflow_run_id=expected_run_id,
            episode_uid=value["episode_uid"],
            story_slug=value["story_slug"],
            episode_code="EP01",
        )


@dataclass(frozen=True)
class _FileFact:
    relative_key: str
    content: bytes
    content_revision: str
    mtime: datetime
    size: int


@dataclass(frozen=True)
class _DirectoryFact:
    relative_key: str
    files: Mapping[str, _FileFact]
    content_revision: str | None
    mtime: datetime | None
    size: int | None


@dataclass(frozen=True)
class _EpisodeReads:
    outline: _FileFact | None
    script: _FileFact | None
    storyboard: _FileFact | None
    prompts: _DirectoryFact | None
    renders: _DirectoryFact | None
    review: _FileFact | None
    invalid_revisions: Mapping[str, str]
    unavailable_roots: frozenset[str]


_TRANSIENT_ARTIFACT_ERRNOS = frozenset(
    value
    for name in ("EAGAIN", "EBUSY", "EIO", "ESTALE")
    if isinstance((value := getattr(errno, name, None)), int)
)


_ARTIFACT_PRESENTATION = {
    "episode-outline.md": (
        StoryWorkspaceEpisodeProducerAction.PLAN_EPISODE,
        [
            StoryWorkspaceEpisodeArtifactConsumer.EPISODE_OVERVIEW,
            StoryWorkspaceEpisodeArtifactConsumer.STORYLINE_NAVIGATOR,
            StoryWorkspaceEpisodeArtifactConsumer.NARRATIVE_WORKBENCH,
        ],
    ),
    "script.md": (
        StoryWorkspaceEpisodeProducerAction.WRITE_SCRIPT,
        [
            StoryWorkspaceEpisodeArtifactConsumer.NARRATIVE_WORKBENCH,
            StoryWorkspaceEpisodeArtifactConsumer.SHOT_INSPECTOR,
        ],
    ),
    "storyboard.yaml": (
        StoryWorkspaceEpisodeProducerAction.REGENERATE_STORYBOARD,
        [
            StoryWorkspaceEpisodeArtifactConsumer.NARRATIVE_WORKBENCH,
            StoryWorkspaceEpisodeArtifactConsumer.SHOT_INSPECTOR,
        ],
    ),
    "prompts/": (
        StoryWorkspaceEpisodeProducerAction.GENERATE_PROMPTS,
        [
            StoryWorkspaceEpisodeArtifactConsumer.SHOT_INSPECTOR,
            StoryWorkspaceEpisodeArtifactConsumer.PROMPT_VIEW,
        ],
    ),
    "renders/": (
        StoryWorkspaceEpisodeProducerAction.PREPARE_RENDER_GUIDE,
        [
            StoryWorkspaceEpisodeArtifactConsumer.SHOT_INSPECTOR,
            StoryWorkspaceEpisodeArtifactConsumer.RENDER_VIEW,
        ],
    ),
    "review-report.md": (
        StoryWorkspaceEpisodeProducerAction.REVIEW_FULL_CHAIN,
        [
            StoryWorkspaceEpisodeArtifactConsumer.REVIEW_VIEW,
            StoryWorkspaceEpisodeArtifactConsumer.SHOT_INSPECTOR,
        ],
    ),
}


class StoryWorkspaceEpisodeArtifactService:
    """Read one pre-authorized run without accepting browser-owned paths."""

    def __init__(self, workspace_root: str | os.PathLike[str]) -> None:
        supplied = Path(workspace_root)
        try:
            visible = os.lstat(supplied)
            resolved = supplied.resolve(strict=True)
            pinned = os.stat(resolved, follow_symlinks=False)
        except (OSError, RuntimeError) as exc:
            raise StoryWorkspaceEpisodeArtifactPathError(
                "workspace root is unavailable"
            ) from exc
        if (
            stat.S_ISLNK(visible.st_mode)
            or not stat.S_ISDIR(pinned.st_mode)
        ):
            raise StoryWorkspaceEpisodeArtifactPathError(
                "workspace root must be a real directory"
            )
        self.workspace_root = resolved
        self._workspace_identity = (pinned.st_dev, pinned.st_ino)

    @staticmethod
    def _directory_flags() -> int:
        return os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(
            os,
            "O_CLOEXEC",
            0,
        )

    @staticmethod
    def _file_flags() -> int:
        return os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)

    @staticmethod
    def _metadata_revision(
        relative_key: str,
        metadata: os.stat_result,
        *,
        extra: object | None = None,
    ) -> str:
        payload = json.dumps(
            [
                relative_key,
                metadata.st_dev,
                metadata.st_ino,
                metadata.st_size,
                metadata.st_mtime_ns,
                metadata.st_ctime_ns,
                stat.S_IFMT(metadata.st_mode),
                extra,
            ],
            ensure_ascii=True,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(payload).hexdigest()

    def _open_workspace(self) -> int:
        try:
            descriptor = os.open(self.workspace_root, self._directory_flags())
            metadata = os.fstat(descriptor)
        except OSError as exc:
            raise StoryWorkspaceEpisodeArtifactPathError(
                "workspace root cannot be pinned"
            ) from exc
        if (metadata.st_dev, metadata.st_ino) != self._workspace_identity:
            os.close(descriptor)
            raise StoryWorkspaceEpisodeArtifactPathError(
                "workspace root identity changed"
            )
        return descriptor

    @classmethod
    def _open_child_directory(
        cls,
        parent: int,
        name: str,
        *,
        optional: bool,
    ) -> int | None:
        if not name or "/" in name or "\\" in name or name in {".", ".."}:
            raise StoryWorkspaceEpisodeArtifactContractError(
                "directory component is not a safe segment"
            )
        try:
            descriptor = os.open(name, cls._directory_flags(), dir_fd=parent)
        except FileNotFoundError:
            if optional:
                return None
            raise StoryWorkspaceEpisodeArtifactPathError(
                "required canonical directory is unavailable"
            ) from None
        except OSError as exc:
            raise StoryWorkspaceEpisodeArtifactPathError(
                "canonical directory cannot be opened safely"
            ) from exc
        try:
            pinned = os.fstat(descriptor)
            visible = os.stat(name, dir_fd=parent, follow_symlinks=False)
        except OSError as exc:
            os.close(descriptor)
            raise StoryWorkspaceEpisodeArtifactPathError(
                "canonical directory identity is unavailable"
            ) from exc
        if (
            not stat.S_ISDIR(pinned.st_mode)
            or stat.S_ISLNK(visible.st_mode)
            or not stat.S_ISDIR(visible.st_mode)
            or (pinned.st_dev, pinned.st_ino) != (visible.st_dev, visible.st_ino)
        ):
            os.close(descriptor)
            raise StoryWorkspaceEpisodeArtifactPathError(
                "canonical directory is unsafe"
            )
        return descriptor

    @classmethod
    def _read_file(
        cls,
        parent: int,
        name: str,
        *,
        relative_key: str,
        max_bytes: int,
        optional: bool,
    ) -> _FileFact | None:
        if _SAFE_DIRECTORY_ENTRY_RE.fullmatch(name) is None:
            raise StoryWorkspaceEpisodeArtifactContractError(
                "artifact filename is not allowlisted"
            )
        try:
            descriptor = os.open(name, cls._file_flags(), dir_fd=parent)
        except FileNotFoundError:
            if optional:
                return None
            raise StoryWorkspaceEpisodeArtifactPathError(
                "required canonical file is unavailable"
            ) from None
        except OSError as exc:
            raise StoryWorkspaceEpisodeArtifactPathError(
                "artifact cannot be opened safely"
            ) from exc
        identity_verified = False
        try:
            pinned = os.fstat(descriptor)
            visible = os.stat(name, dir_fd=parent, follow_symlinks=False)
            if (
                not stat.S_ISREG(pinned.st_mode)
                or stat.S_ISLNK(visible.st_mode)
                or not stat.S_ISREG(visible.st_mode)
                or (pinned.st_dev, pinned.st_ino)
                != (visible.st_dev, visible.st_ino)
            ):
                raise StoryWorkspaceEpisodeArtifactPathError(
                    "artifact inode is unsafe"
                )
            identity_verified = True
            if pinned.st_size > max_bytes:
                raise StoryWorkspaceEpisodeArtifactContractError(
                    "artifact exceeds its byte limit",
                    fact_revision=cls._metadata_revision(relative_key, pinned),
                )
            chunks: list[bytes] = []
            total = 0
            while True:
                chunk = os.read(descriptor, min(65536, max_bytes + 1 - total))
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise StoryWorkspaceEpisodeArtifactContractError(
                        "artifact exceeds its byte limit",
                        fact_revision=cls._metadata_revision(relative_key, pinned),
                    )
                chunks.append(chunk)
        except OSError as exc:
            if identity_verified and exc.errno in _TRANSIENT_ARTIFACT_ERRNOS:
                raise StoryWorkspaceEpisodeArtifactUnavailableError(
                    relative_key
                ) from None
            raise StoryWorkspaceEpisodeArtifactPathError(
                "artifact cannot be read safely"
            ) from exc
        finally:
            os.close(descriptor)
        content = b"".join(chunks)
        return _FileFact(
            relative_key=relative_key,
            content=content,
            content_revision="sha256:" + hashlib.sha256(content).hexdigest(),
            mtime=datetime.fromtimestamp(pinned.st_mtime, tz=UTC),
            size=len(content),
        )

    @classmethod
    def _read_directory(
        cls,
        episode_descriptor: int,
        name: str,
        *,
        approved_extensions: frozenset[str],
        per_file_max_bytes: int,
    ) -> _DirectoryFact | None:
        descriptor = cls._open_child_directory(
            episode_descriptor,
            name,
            optional=True,
        )
        if descriptor is None:
            return None
        try:
            try:
                entries = sorted(os.listdir(descriptor))
            except OSError as exc:
                if exc.errno in _TRANSIENT_ARTIFACT_ERRNOS:
                    raise StoryWorkspaceEpisodeArtifactUnavailableError(
                        f"{name}/"
                    ) from None
                raise StoryWorkspaceEpisodeArtifactPathError(
                    "artifact directory cannot be listed safely"
                ) from exc
            entry_facts: list[list[object]] = []
            non_regular_entry = False
            for entry in entries:
                try:
                    metadata = os.stat(
                        entry,
                        dir_fd=descriptor,
                        follow_symlinks=False,
                    )
                except OSError as exc:
                    raise StoryWorkspaceEpisodeArtifactPathError(
                        "artifact directory entry identity is unavailable"
                    ) from exc
                if stat.S_ISLNK(metadata.st_mode):
                    raise StoryWorkspaceEpisodeArtifactPathError(
                        "artifact directory entry is unsafe"
                    )
                if not stat.S_ISREG(metadata.st_mode):
                    non_regular_entry = True
                entry_facts.append(
                    [
                        entry,
                        metadata.st_dev,
                        metadata.st_ino,
                        metadata.st_size,
                        metadata.st_mtime_ns,
                        metadata.st_ctime_ns,
                        stat.S_IFMT(metadata.st_mode),
                    ]
                )
            invalid_directory_revision = "sha256:" + hashlib.sha256(
                json.dumps(
                    [f"{name}/", entry_facts],
                    ensure_ascii=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
            if non_regular_entry:
                raise StoryWorkspaceEpisodeArtifactContractError(
                    "artifact directory contains an unapproved entry",
                    fact_revision=invalid_directory_revision,
                )
            if len(entries) > STORY_WORKSPACE_EPISODE_AUXILIARY_MAX_FILES:
                raise StoryWorkspaceEpisodeArtifactContractError(
                    "artifact directory exceeds its entry limit",
                    fact_revision=invalid_directory_revision,
                )
            files: dict[str, _FileFact] = {}
            total = 0
            for entry in entries:
                if (
                    _SAFE_DIRECTORY_ENTRY_RE.fullmatch(entry) is None
                    or Path(entry).suffix.lower() not in approved_extensions
                ):
                    raise StoryWorkspaceEpisodeArtifactContractError(
                        "artifact directory contains an unapproved entry",
                        fact_revision=invalid_directory_revision,
                    )
                try:
                    fact = cls._read_file(
                        descriptor,
                        entry,
                        relative_key=f"{name}/{entry}",
                        max_bytes=per_file_max_bytes,
                        optional=False,
                    )
                except StoryWorkspaceEpisodeArtifactContractError as exc:
                    raise StoryWorkspaceEpisodeArtifactContractError(
                        "artifact directory contains an invalid file",
                        fact_revision=exc.fact_revision or invalid_directory_revision,
                    ) from exc
                assert fact is not None
                total += fact.size
                if total > STORY_WORKSPACE_EPISODE_AUXILIARY_COLLECTION_MAX_BYTES:
                    raise StoryWorkspaceEpisodeArtifactContractError(
                        "artifact directory exceeds its byte limit",
                        fact_revision=invalid_directory_revision,
                    )
                files[fact.relative_key] = fact
            if not files:
                return _DirectoryFact(
                    relative_key=f"{name}/",
                    files={},
                    content_revision=None,
                    mtime=None,
                    size=None,
                )
            revision_payload = [
                [key, fact.content_revision, fact.size]
                for key, fact in sorted(files.items())
            ]
            revision = "sha256:" + hashlib.sha256(
                json.dumps(
                    revision_payload,
                    ensure_ascii=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
            return _DirectoryFact(
                relative_key=f"{name}/",
                files=files,
                content_revision=revision,
                mtime=max(fact.mtime for fact in files.values()),
                size=total,
            )
        finally:
            os.close(descriptor)

    def _read_existing_binding(
        self,
        workflow_run_id: str,
    ) -> StoryWorkspaceEpisodeBindingFile | None:
        descriptors: list[int] = []
        try:
            parent = self._open_workspace()
            descriptors.append(parent)
            for component in (".dream", "runtime", "runs", workflow_run_id):
                child = self._open_child_directory(parent, component, optional=True)
                if child is None:
                    return None
                descriptors.append(child)
                parent = child
            try:
                fact = self._read_file(
                    parent,
                    "episode.json",
                    relative_key="episode.json",
                    max_bytes=_BINDING_MAX_BYTES,
                    optional=True,
                )
            except StoryWorkspaceEpisodeArtifactContractError:
                return None
            if fact is None:
                return None
            try:
                binding = StoryWorkspaceEpisodeBindingFile.model_validate_json(
                    fact.content
                )
            except ValidationError:
                return None
            return binding
        finally:
            for descriptor in reversed(descriptors):
                os.close(descriptor)

    def _read_bound_episode(
        self,
        binding: StoryWorkspaceEpisodeBindingFile,
    ) -> _EpisodeReads:
        if (
            _STORY_SLUG_RE.fullmatch(binding.story_slug) is None
            or binding.episode_root
            != f"stories/{binding.story_slug}/episodes/EP01"
        ):
            raise StoryWorkspaceEpisodeArtifactPathError(
                "Episode binding root identity is invalid"
            )
        descriptors: list[int] = []
        try:
            parent = self._open_workspace()
            descriptors.append(parent)
            for component in ("stories", binding.story_slug):
                child = self._open_child_directory(parent, component, optional=False)
                assert child is not None
                descriptors.append(child)
                parent = child
            try:
                project = self._read_file(
                    parent,
                    "project.yaml",
                    relative_key="project.yaml",
                    max_bytes=_PROJECT_MAX_BYTES,
                    optional=False,
                )
            except StoryWorkspaceEpisodeArtifactContractError as exc:
                raise StoryWorkspaceEpisodeArtifactPathError(
                    "canonical project identity is invalid"
                ) from exc
            assert project is not None
            try:
                project_text = project.content.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise StoryWorkspaceEpisodeArtifactPathError(
                    "canonical project identity is unreadable"
                ) from exc
            project_ids = _PROJECT_ID_RE.findall(project_text)
            if project_ids != [binding.story_slug]:
                raise StoryWorkspaceEpisodeArtifactPathError(
                    "canonical project identity does not match the binding"
                )
            episodes = self._open_child_directory(parent, "episodes", optional=False)
            assert episodes is not None
            descriptors.append(episodes)
            episode = self._open_child_directory(episodes, "EP01", optional=True)
            if episode is None:
                return _EpisodeReads(
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    {},
                    frozenset(),
                )
            descriptors.append(episode)
            invalid_revisions: dict[str, str] = {}
            unavailable_roots: set[str] = set()

            def read_root_file(
                name: str,
                *,
                max_bytes: int,
            ) -> _FileFact | None:
                try:
                    return self._read_file(
                        episode,
                        name,
                        relative_key=name,
                        max_bytes=max_bytes,
                        optional=True,
                    )
                except StoryWorkspaceEpisodeArtifactUnavailableError:
                    unavailable_roots.add(name)
                    return None
                except StoryWorkspaceEpisodeArtifactContractError as exc:
                    invalid_revisions[name] = (
                        exc.fact_revision
                        or self._invalid_error_revision(name, "contract")
                    )
                    return None

            def read_root_directory(
                name: str,
                *,
                approved_extensions: frozenset[str],
                per_file_max_bytes: int,
            ) -> _DirectoryFact | None:
                key = f"{name}/"
                try:
                    return self._read_directory(
                        episode,
                        name,
                        approved_extensions=approved_extensions,
                        per_file_max_bytes=per_file_max_bytes,
                    )
                except StoryWorkspaceEpisodeArtifactUnavailableError:
                    unavailable_roots.add(key)
                    return None
                except StoryWorkspaceEpisodeArtifactContractError as exc:
                    invalid_revisions[key] = (
                        exc.fact_revision
                        or self._invalid_error_revision(key, "contract")
                    )
                    return None

            return _EpisodeReads(
                outline=read_root_file(
                    "episode-outline.md",
                    max_bytes=STORY_WORKSPACE_EPISODE_MARKDOWN_MAX_BYTES,
                ),
                script=read_root_file(
                    "script.md",
                    max_bytes=STORY_WORKSPACE_EPISODE_MARKDOWN_MAX_BYTES,
                ),
                storyboard=read_root_file(
                    "storyboard.yaml",
                    max_bytes=STORY_WORKSPACE_EPISODE_YAML_MAX_BYTES,
                ),
                prompts=read_root_directory(
                    "prompts",
                    approved_extensions=frozenset({".yaml", ".yml"}),
                    per_file_max_bytes=STORY_WORKSPACE_EPISODE_AUXILIARY_YAML_MAX_BYTES,
                ),
                renders=read_root_directory(
                    "renders",
                    approved_extensions=frozenset({".md", ".json"}),
                    per_file_max_bytes=STORY_WORKSPACE_EPISODE_AUXILIARY_MARKDOWN_MAX_BYTES,
                ),
                review=read_root_file(
                    "review-report.md",
                    max_bytes=STORY_WORKSPACE_EPISODE_AUXILIARY_MARKDOWN_MAX_BYTES,
                ),
                invalid_revisions=invalid_revisions,
                unavailable_roots=frozenset(unavailable_roots),
            )
        finally:
            for descriptor in reversed(descriptors):
                os.close(descriptor)

    @staticmethod
    def _invalid_error_revision(relative_key: str, reason: str) -> str:
        return "sha256:" + hashlib.sha256(
            f"invalid:{relative_key}:{reason}".encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _root_revision(
        revisions: Mapping[str, str],
        relative_key: str,
    ) -> str:
        return "sha256:" + hashlib.sha256(
            json.dumps(
                [relative_key, sorted(revisions.items())],
                ensure_ascii=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _manifest_revision(
        facts: Mapping[str, tuple[str, str | None]],
        association_payload: object,
    ) -> str:
        value = {
            "artifacts": [
                [key, availability, revision]
                for key, (availability, revision) in sorted(facts.items())
            ],
            "associations": association_payload,
        }
        encoded = json.dumps(
            value,
            ensure_ascii=True,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def unbound_surface(
        workflow_run_id: str,
    ) -> StoryWorkspaceEpisodeArtifactSurface:
        return StoryWorkspaceEpisodeArtifactSurface(
            runId=workflow_run_id,
            bindingAvailability=StoryWorkspaceEpisodeBindingAvailability.UNBOUND,
            bindingRecovery=StoryWorkspaceEpisodeBindingRecovery(
                autoRepairAttempted=False,
                canDispatch=True,
                publicReason="episode_binding_unproven",
            ),
        )

    def read_surface(
        self,
        workflow_run_id: str,
        *,
        episode_authority: object,
    ) -> StoryWorkspaceEpisodeArtifactSurface:
        """Return an honest aggregate after the caller completed DB authorization."""

        if _RUN_ID_RE.fullmatch(workflow_run_id) is None:
            raise StoryWorkspaceEpisodeArtifactContractError(
                "workflow run identity is invalid"
            )
        authority = StoryWorkspaceEpisodeAuthority.parse(
            episode_authority,
            expected_run_id=workflow_run_id,
        )
        if authority is None:
            return self.unbound_surface(workflow_run_id)
        binding = self._read_existing_binding(workflow_run_id)
        if binding is None:
            return self.unbound_surface(workflow_run_id)
        if (
            binding.workflow_run_id != authority.workflow_run_id
            or binding.episode_uid != authority.episode_uid
            or binding.story_slug != authority.story_slug
            or binding.episode_code != authority.episode_code
            or binding.episode_root
            != f"stories/{authority.story_slug}/episodes/{authority.episode_code}"
        ):
            return self.unbound_surface(workflow_run_id)

        reads = self._read_bound_episode(binding)
        narrative_adapter = StoryWorkspaceEpisodeArtifactAdapter(
            episode_uid=binding.episode_uid
        )
        invalid: dict[str, str] = dict(reads.invalid_revisions)

        narrative_inputs: dict[str, _FileFact | None] = {
            "outline": reads.outline,
            "script": reads.script,
            "storyboard": reads.storyboard,
        }
        for key, fact in list(narrative_inputs.items()):
            if fact is None:
                continue
            isolated = {"outline": None, "script": None, "storyboard": None}
            isolated[key] = fact.content
            try:
                narrative_adapter.project(
                    outline=isolated["outline"],
                    script=isolated["script"],
                    storyboard=isolated["storyboard"],
                    outline_revision=(fact.content_revision if key == "outline" else None),
                    script_revision=(fact.content_revision if key == "script" else None),
                    storyboard_revision=(fact.content_revision if key == "storyboard" else None),
                )
            except StoryWorkspaceEpisodeArtifactParseError:
                invalid[fact.relative_key] = fact.content_revision
                narrative_inputs[key] = None

        narrative = narrative_adapter.project(
            outline=(
                narrative_inputs["outline"].content
                if narrative_inputs["outline"] is not None
                else None
            ),
            script=(
                narrative_inputs["script"].content
                if narrative_inputs["script"] is not None
                else None
            ),
            storyboard=(
                narrative_inputs["storyboard"].content
                if narrative_inputs["storyboard"] is not None
                else None
            ),
            outline_revision=(
                narrative_inputs["outline"].content_revision
                if narrative_inputs["outline"] is not None
                else None
            ),
            script_revision=(
                narrative_inputs["script"].content_revision
                if narrative_inputs["script"] is not None
                else None
            ),
            storyboard_revision=(
                narrative_inputs["storyboard"].content_revision
                if narrative_inputs["storyboard"] is not None
                else None
            ),
        )

        prompt_files = (
            {key: fact.content for key, fact in reads.prompts.files.items()}
            if reads.prompts is not None
            else {}
        )
        prompt_revisions = (
            {key: fact.content_revision for key, fact in reads.prompts.files.items()}
            if reads.prompts is not None
            else {}
        )
        render_guide = (
            reads.renders.files.get("renders/render-guide.md")
            if reads.renders is not None
            else None
        )
        review = reads.review
        auxiliary_adapter = StoryWorkspaceEpisodeAuxiliaryArtifactAdapter(
            episode_uid=binding.episode_uid,
            canonical_episode_root=binding.episode_root,
        )

        raw_facts = self._raw_manifest_facts(reads, invalid)
        preliminary_revision = self._manifest_revision(raw_facts, {})
        prompt_files, prompt_revisions, render_guide, review = self._validated_auxiliary_inputs(
            auxiliary_adapter,
            prompt_files,
            prompt_revisions,
            render_guide,
            review,
            narrative,
            preliminary_revision,
            invalid,
        )
        raw_facts = self._raw_manifest_facts(reads, invalid)
        preliminary = auxiliary_adapter.project(
            prompts=prompt_files,
            prompt_revisions=prompt_revisions,
            render_guide=render_guide.content if render_guide is not None else None,
            render_revision=(
                render_guide.content_revision if render_guide is not None else None
            ),
            review_report=review.content if review is not None else None,
            review_revision=review.content_revision if review is not None else None,
            shot_view_ids={shot.shot_id: shot.id for shot in narrative.shots},
            narrative_beat_view_ids={
                beat.source_key: beat.id for beat in narrative.narrative_beats
            },
            script_scene_view_ids={
                scene.source_key: scene.id for scene in narrative.scenes
            },
            manifest_revision=preliminary_revision,
        )
        association_payload = {
            "narrative": narrative.associations.model_dump(mode="json", by_alias=True),
            "auxiliary": preliminary.associations.model_dump(mode="json", by_alias=True),
        }
        manifest_revision = self._manifest_revision(raw_facts, association_payload)
        auxiliary = auxiliary_adapter.project(
            prompts=prompt_files,
            prompt_revisions=prompt_revisions,
            render_guide=render_guide.content if render_guide is not None else None,
            render_revision=(
                render_guide.content_revision if render_guide is not None else None
            ),
            review_report=review.content if review is not None else None,
            review_revision=review.content_revision if review is not None else None,
            shot_view_ids={shot.shot_id: shot.id for shot in narrative.shots},
            narrative_beat_view_ids={
                beat.source_key: beat.id for beat in narrative.narrative_beats
            },
            script_scene_view_ids={
                scene.source_key: scene.id for scene in narrative.scenes
            },
            manifest_revision=manifest_revision,
        )

        review_producer = (
            StoryWorkspaceEpisodeProducerAction.REVIEW_SCRIPT
            if auxiliary.review is not None
            and auxiliary.review.scope is StoryWorkspaceEpisodeReviewScope.SCRIPT
            else StoryWorkspaceEpisodeProducerAction.REVIEW_FULL_CHAIN
        )
        artifacts = self._manifest_entries(
            reads,
            invalid,
            review_producer=review_producer,
        )
        return StoryWorkspaceEpisodeArtifactSurface(
            runId=workflow_run_id,
            opaqueEpisodeId=binding.episode_uid,
            manifestRevision=manifest_revision,
            etag=manifest_revision,
            bindingAvailability=StoryWorkspaceEpisodeBindingAvailability.BOUND,
            bindingRecovery=StoryWorkspaceEpisodeBindingRecovery(
                autoRepairAttempted=False,
                canDispatch=False,
            ),
            artifacts=artifacts,
            narrative=narrative,
            auxiliary=auxiliary,
        )

    @staticmethod
    def _validated_auxiliary_inputs(
        adapter: StoryWorkspaceEpisodeAuxiliaryArtifactAdapter,
        prompt_files: dict[str, bytes],
        prompt_revisions: dict[str, str],
        render_guide: _FileFact | None,
        review: _FileFact | None,
        narrative: object,
        manifest_revision: str,
        invalid: dict[str, str],
    ) -> tuple[dict[str, bytes], dict[str, str], _FileFact | None, _FileFact | None]:
        values = {
            "prompts": bool(prompt_files),
            "render": render_guide is not None,
            "review": review is not None,
        }
        for kind, present in values.items():
            if not present:
                continue
            try:
                projection = adapter.project(
                    prompts=prompt_files if kind == "prompts" else {},
                    prompt_revisions=prompt_revisions if kind == "prompts" else {},
                    render_guide=(
                        render_guide.content
                        if kind == "render" and render_guide is not None
                        else None
                    ),
                    render_revision=(
                        render_guide.content_revision
                        if kind == "render" and render_guide is not None
                        else None
                    ),
                    review_report=(
                        review.content
                        if kind == "review" and review is not None
                        else None
                    ),
                    review_revision=(
                        review.content_revision
                        if kind == "review" and review is not None
                        else None
                    ),
                    shot_view_ids={shot.shot_id: shot.id for shot in narrative.shots},
                    narrative_beat_view_ids={
                        beat.source_key: beat.id for beat in narrative.narrative_beats
                    },
                    script_scene_view_ids={
                        scene.source_key: scene.id for scene in narrative.scenes
                    },
                    manifest_revision=manifest_revision,
                )
                StoryWorkspaceEpisodeArtifactService._assert_auxiliary_same_entry(
                    projection,
                    narrative,
                    root=kind,
                )
            except StoryWorkspaceEpisodeAuxiliaryArtifactParseError:
                if kind == "prompts":
                    invalid["prompts/"] = StoryWorkspaceEpisodeArtifactService._root_revision(
                        prompt_revisions,
                        "prompts/",
                    )
                    prompt_files = {}
                    prompt_revisions = {}
                elif kind == "render":
                    invalid["renders/"] = (
                        render_guide.content_revision
                        if render_guide is not None
                        else StoryWorkspaceEpisodeArtifactService._invalid_error_revision(
                            "renders/",
                            "parse",
                        )
                    )
                    render_guide = None
                else:
                    invalid["review-report.md"] = (
                        review.content_revision
                        if review is not None
                        else StoryWorkspaceEpisodeArtifactService._invalid_error_revision(
                            "review-report.md",
                            "parse",
                        )
                    )
                    review = None
        return prompt_files, prompt_revisions, render_guide, review

    @staticmethod
    def _assert_auxiliary_same_entry(
        auxiliary: object,
        narrative: object,
        *,
        root: str,
    ) -> None:
        shots = {
            shot.shot_id.upper(): (shot.shot_id, shot.id)
            for shot in narrative.shots
        }
        beats = {
            beat.source_key.upper(): (beat.source_key, beat.id)
            for beat in narrative.narrative_beats
        }
        scenes = {
            scene.source_key.upper(): (scene.source_key, scene.id)
            for scene in narrative.scenes
        }

        def matches(
            mapping: Mapping[str, tuple[str, str]],
            source_key: str,
            view_id: str | None,
        ) -> bool:
            entry = mapping.get(source_key.upper())
            return entry == (source_key, view_id)

        if root == "prompts" and any(
            item.association_status.value == "linked"
            and not matches(shots, item.shot_id, item.shot_view_id)
            for item in auxiliary.prompts.items
        ):
            raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
                "prompts/",
                "canonical_link_mismatch",
            )
        if root == "render" and auxiliary.render_guide is not None and any(
            item.association_status.value == "linked"
            and not matches(shots, item.shot_id, item.shot_view_id)
            for item in auxiliary.render_guide.queue.items
        ):
            raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
                "renders/render-guide.md",
                "canonical_link_mismatch",
            )
        if root == "review" and auxiliary.review is not None:
            target_maps = {
                "narrative-beat": beats,
                "script-scene": scenes,
                "shot": shots,
            }
            if any(
                target.association_status.value == "linked"
                and not matches(
                    target_maps[target.kind.value],
                    target.source_key,
                    target.target_view_id,
                )
                for target in auxiliary.review.targets
            ):
                raise StoryWorkspaceEpisodeAuxiliaryArtifactParseError(
                    "review-report.md",
                    "canonical_link_mismatch",
                )

    @staticmethod
    def _raw_manifest_facts(
        reads: _EpisodeReads,
        invalid: Mapping[str, str],
    ) -> dict[str, tuple[str, str | None]]:
        values: dict[str, _FileFact | _DirectoryFact | None] = {
            "episode-outline.md": reads.outline,
            "script.md": reads.script,
            "storyboard.yaml": reads.storyboard,
            "prompts/": reads.prompts,
            "renders/": reads.renders,
            "review-report.md": reads.review,
        }
        facts: dict[str, tuple[str, str | None]] = {}
        for key, value in values.items():
            revision = value.content_revision if value is not None else None
            if key in invalid:
                facts[key] = (
                    StoryWorkspaceEpisodeArtifactAvailability.INVALID.value,
                    invalid[key],
                )
            elif key in reads.unavailable_roots:
                facts[key] = (
                    StoryWorkspaceEpisodeArtifactAvailability.UNAVAILABLE.value,
                    None,
                )
            elif value is None or revision is None:
                facts[key] = (
                    StoryWorkspaceEpisodeArtifactAvailability.NOT_GENERATED.value,
                    None,
                )
            else:
                facts[key] = (
                    StoryWorkspaceEpisodeArtifactAvailability.AVAILABLE.value,
                    revision,
                )
        return facts

    @staticmethod
    def _manifest_entries(
        reads: _EpisodeReads,
        invalid: Mapping[str, str],
        *,
        review_producer: StoryWorkspaceEpisodeProducerAction,
    ) -> list[StoryWorkspaceEpisodeArtifactManifestEntry]:
        values: dict[str, _FileFact | _DirectoryFact | None] = {
            "episode-outline.md": reads.outline,
            "script.md": reads.script,
            "storyboard.yaml": reads.storyboard,
            "prompts/": reads.prompts,
            "renders/": reads.renders,
            "review-report.md": reads.review,
        }
        entries: list[StoryWorkspaceEpisodeArtifactManifestEntry] = []
        for key, value in values.items():
            producer, consumers = _ARTIFACT_PRESENTATION[key]
            if key == "review-report.md":
                producer = review_producer
            available = (
                value is not None
                and value.content_revision is not None
                and key not in invalid
            )
            availability = (
                StoryWorkspaceEpisodeArtifactAvailability.INVALID
                if key in invalid
                else (
                    StoryWorkspaceEpisodeArtifactAvailability.UNAVAILABLE
                    if key in reads.unavailable_roots
                    else (
                        StoryWorkspaceEpisodeArtifactAvailability.AVAILABLE
                        if available
                        else StoryWorkspaceEpisodeArtifactAvailability.NOT_GENERATED
                    )
                )
            )
            entries.append(
                StoryWorkspaceEpisodeArtifactManifestEntry(
                    relativeKey=key,
                    availability=availability,
                    contentRevision=(value.content_revision if available else None),
                    mtime=(value.mtime if available else None),
                    size=(value.size if available else None),
                    producerAction=producer,
                    consumers=consumers,
                )
            )
        return entries


__all__ = [
    "StoryWorkspaceEpisodeArtifactContractError",
    "StoryWorkspaceEpisodeArtifactError",
    "StoryWorkspaceEpisodeArtifactPathError",
    "StoryWorkspaceEpisodeArtifactUnavailableError",
    "StoryWorkspaceEpisodeArtifactService",
    "StoryWorkspaceEpisodeAuthority",
]
