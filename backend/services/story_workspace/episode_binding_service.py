"""Fail-closed run-scoped binding for the first canonical Episode."""

from __future__ import annotations

import json
import os
import re
import stat
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator
from uuid import uuid4

import fcntl
from pydantic import ValidationError

try:
    from story_workspace.contracts import (
        StoryWorkspaceEpisodeBindingAvailability,
        StoryWorkspaceEpisodeBindingEntry,
        StoryWorkspaceEpisodeBindingFile,
        StoryWorkspaceEpisodeBindingRecovery,
        StoryWorkspaceEpisodeRegistryFile,
    )
except ModuleNotFoundError:  # Support repository-root package imports.
    from backend.story_workspace.contracts import (
        StoryWorkspaceEpisodeBindingAvailability,
        StoryWorkspaceEpisodeBindingEntry,
        StoryWorkspaceEpisodeBindingFile,
        StoryWorkspaceEpisodeBindingRecovery,
        StoryWorkspaceEpisodeRegistryFile,
    )


_RUN_ID_PATTERN = re.compile(r"^run_[0-9a-f]{32}$")
_STORY_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_BINDING_MAX_BYTES = 16 * 1024
_PROJECT_MAX_BYTES = 256 * 1024
_PROJECT_ID_PATTERN = re.compile(
    r"(?m)^project_id:[ \t]*"
    r"(?P<quote>['\"]?)"
    r"(?P<value>[a-z0-9]+(?:-[a-z0-9]+)*)"
    r"(?P=quote)[ \t]*(?:\r\n|\n|\Z)"
)
_PROJECT_ID_DECLARATION_PATTERN = re.compile(
    r"(?m)^[ \t]*project_id[ \t]*:"
)
_PROJECT_MAPPING_HEADER_PATTERN = re.compile(r"^project:[ \t]*$")
_PROJECT_MAPPING_ID_PATTERN = re.compile(
    r"^  project_id:[ \t]*"
    r"(?P<quote>['\"]?)"
    r"(?P<value>[a-z0-9]+(?:-[a-z0-9]+)*)"
    r"(?P=quote)[ \t]*$"
)
_TOTAL_EPISODES_PATTERN = re.compile(
    r"(?m)^  total_episodes:[ \t]*(?P<value>[1-9][0-9]?)[ \t]*(?:\r\n|\n|\Z)"
)
_TOTAL_EPISODES_DECLARATION_PATTERN = re.compile(
    r"(?m)^[ \t]*total_episodes[ \t]*:"
)
_PROJECT_NAME_DECLARATION_PATTERN = re.compile(
    r"(?m)^(?:  )?project_name[ \t]*:[ \t]*(?P<value>[^\r\n]*)$"
)
_PROJECT_NAME_SECRET_PATTERN = re.compile(
    r"(?:\bBearer\s+\S+|(?:^|[^A-Za-z0-9_-])(?:sk-(?:ant-|proj-)?|"
    r"gh[pousr]_|xox[baprs]-)[A-Za-z0-9_-]{12,}|"
    r"\b[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\b)",
    re.IGNORECASE,
)


class StoryWorkspaceEpisodeBindingError(RuntimeError):
    """Base public error for Episode binding operations."""


class StoryWorkspaceEpisodeBindingContractError(StoryWorkspaceEpisodeBindingError):
    """Trusted inputs or persisted JSON violate the binding contract."""


class StoryWorkspaceEpisodeBindingIdentityConflict(
    StoryWorkspaceEpisodeBindingContractError
):
    """An existing run binding cannot be rebound to another identity."""


class StoryWorkspaceEpisodeBindingPathError(StoryWorkspaceEpisodeBindingError):
    """A symlink, path component, or inode violates containment."""


@dataclass(frozen=True)
class StoryWorkspaceEpisodeBindingContext:
    """Independent trusted facts supplied after outer authorization succeeds."""

    workflow_run_id: str
    trusted_project_story_slug: str | None
    locked_context_story_slug: str | None
    run_provenance_story_slug: str | None
    episode_uid: str | None = None


@dataclass(frozen=True)
class StoryWorkspaceEpisodeBindingResolution:
    """Internal resolution result used to build the public Episode surface."""

    binding_availability: StoryWorkspaceEpisodeBindingAvailability
    recovery: StoryWorkspaceEpisodeBindingRecovery
    binding: StoryWorkspaceEpisodeBindingFile | None = None


class StoryWorkspaceEpisodeBindingService:
    """Creates or resolves immutable ``dream-episode/v1`` identity bindings."""

    def __init__(self, workspace_root: str | os.PathLike[str]) -> None:
        supplied_root = Path(workspace_root)
        try:
            supplied_metadata = os.lstat(supplied_root)
            resolved_root = supplied_root.resolve(strict=True)
            resolved_metadata = os.stat(resolved_root, follow_symlinks=False)
        except (OSError, RuntimeError) as exc:
            raise StoryWorkspaceEpisodeBindingPathError(
                "workspace root is unavailable"
            ) from exc
        if stat.S_ISLNK(supplied_metadata.st_mode):
            raise StoryWorkspaceEpisodeBindingPathError(
                "workspace root must not be a symlink"
            )
        if not stat.S_ISDIR(resolved_metadata.st_mode):
            raise StoryWorkspaceEpisodeBindingPathError(
                "workspace root must be a directory"
            )
        self.workspace_root = resolved_root
        self._workspace_identity = (
            resolved_metadata.st_dev,
            resolved_metadata.st_ino,
        )

    @staticmethod
    def _directory_flags() -> int:
        return os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(
            os, "O_CLOEXEC", 0
        )

    @staticmethod
    def _file_flags() -> int:
        return os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)

    def _open_workspace(self) -> int:
        try:
            descriptor = os.open(self.workspace_root, self._directory_flags())
            metadata = os.fstat(descriptor)
        except OSError as exc:
            raise StoryWorkspaceEpisodeBindingPathError(
                "workspace root cannot be opened safely"
            ) from exc
        if (metadata.st_dev, metadata.st_ino) != self._workspace_identity:
            os.close(descriptor)
            raise StoryWorkspaceEpisodeBindingPathError(
                "workspace root identity changed"
            )
        return descriptor

    @classmethod
    def _open_child_directory(
        cls,
        parent_descriptor: int,
        name: str,
        *,
        create: bool,
        optional: bool = False,
    ) -> int | None:
        if not name or "/" in name or "\\" in name or name in {".", ".."}:
            raise StoryWorkspaceEpisodeBindingContractError(
                "directory component is not a safe segment"
            )
        if create:
            try:
                os.mkdir(name, mode=0o700, dir_fd=parent_descriptor)
            except FileExistsError:
                pass
            except OSError as exc:
                raise StoryWorkspaceEpisodeBindingPathError(
                    "binding directory cannot be created safely"
                ) from exc
        try:
            descriptor = os.open(
                name,
                cls._directory_flags(),
                dir_fd=parent_descriptor,
            )
        except FileNotFoundError:
            if optional:
                return None
            raise StoryWorkspaceEpisodeBindingPathError(
                "required binding directory is unavailable"
            ) from None
        except OSError as exc:
            raise StoryWorkspaceEpisodeBindingPathError(
                "binding directory cannot be opened safely"
            ) from exc
        try:
            pinned = os.fstat(descriptor)
            visible = os.stat(
                name,
                dir_fd=parent_descriptor,
                follow_symlinks=False,
            )
        except OSError as exc:
            os.close(descriptor)
            raise StoryWorkspaceEpisodeBindingPathError(
                "binding directory identity is unavailable"
            ) from exc
        if (
            not stat.S_ISDIR(pinned.st_mode)
            or stat.S_ISLNK(visible.st_mode)
            or not stat.S_ISDIR(visible.st_mode)
            or (pinned.st_dev, pinned.st_ino) != (visible.st_dev, visible.st_ino)
        ):
            os.close(descriptor)
            raise StoryWorkspaceEpisodeBindingPathError(
                "binding directory is unsafe"
            )
        return descriptor

    @staticmethod
    def _validate_run_id(run_id: object) -> str:
        if not isinstance(run_id, str) or _RUN_ID_PATTERN.fullmatch(run_id) is None:
            raise StoryWorkspaceEpisodeBindingContractError(
                "authoritative workflow run id is invalid"
            )
        return run_id

    @staticmethod
    def _validate_story_slug(value: object) -> str:
        if not isinstance(value, str) or _STORY_SLUG_PATTERN.fullmatch(value) is None:
            raise StoryWorkspaceEpisodeBindingContractError(
                "trusted story identity is not a safe slug"
            )
        return value

    @staticmethod
    def _validate_episode_uid(value: object) -> str:
        if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{32}", value) is None:
            raise StoryWorkspaceEpisodeBindingContractError(
                "trusted Episode identity is invalid"
            )
        return value

    def _proved_story_slug(
        self,
        context: StoryWorkspaceEpisodeBindingContext,
        *,
        allow_unproven: bool,
    ) -> str | None:
        if not isinstance(context, StoryWorkspaceEpisodeBindingContext):
            raise StoryWorkspaceEpisodeBindingContractError(
                "binding requires a trusted Episode context"
            )
        self._validate_run_id(context.workflow_run_id)
        evidence = (
            context.trusted_project_story_slug,
            context.locked_context_story_slug,
            context.run_provenance_story_slug,
        )
        if any(value is None for value in evidence):
            if allow_unproven:
                return None
            raise StoryWorkspaceEpisodeBindingContractError(
                "trusted Episode identity evidence is incomplete"
            )
        validated = tuple(self._validate_story_slug(value) for value in evidence)
        if len(set(validated)) != 1:
            if allow_unproven:
                return None
            raise StoryWorkspaceEpisodeBindingContractError(
                "trusted Episode identity evidence does not agree"
            )
        return validated[0]

    @contextmanager
    def _locked_run_directory(self, run_id: str) -> Iterator[int]:
        descriptors: list[int] = []
        lock_descriptor = -1
        try:
            workspace_descriptor = self._open_workspace()
            descriptors.append(workspace_descriptor)
            parent = workspace_descriptor
            for name, create in (
                (".dream", False),
                ("runtime", True),
                ("runs", True),
                (run_id, True),
            ):
                child = self._open_child_directory(
                    parent,
                    name,
                    create=create,
                )
                assert child is not None
                descriptors.append(child)
                parent = child
            try:
                lock_descriptor = os.open(
                    ".episode.lock",
                    os.O_WRONLY
                    | os.O_CREAT
                    | os.O_NOFOLLOW
                    | getattr(os, "O_CLOEXEC", 0),
                    0o600,
                    dir_fd=parent,
                )
                lock_metadata = os.fstat(lock_descriptor)
            except OSError as exc:
                raise StoryWorkspaceEpisodeBindingPathError(
                    "Episode binding lock is unavailable"
                ) from exc
            if not stat.S_ISREG(lock_metadata.st_mode):
                raise StoryWorkspaceEpisodeBindingPathError(
                    "Episode binding lock is unsafe"
                )
            fcntl.flock(lock_descriptor, fcntl.LOCK_EX)
            yield parent
        finally:
            if lock_descriptor >= 0:
                try:
                    fcntl.flock(lock_descriptor, fcntl.LOCK_UN)
                finally:
                    os.close(lock_descriptor)
            for descriptor in reversed(descriptors):
                os.close(descriptor)

    def _validate_episode_root(self, story_slug: str) -> None:
        descriptors: list[int] = []
        try:
            workspace_descriptor = self._open_workspace()
            descriptors.append(workspace_descriptor)
            parent = workspace_descriptor
            components = ("stories", story_slug, "episodes", "EP01")
            for index, component in enumerate(components):
                child = self._open_child_directory(
                    parent,
                    component,
                    create=False,
                    optional=index == len(components) - 1,
                )
                if child is None:
                    return
                descriptors.append(child)
                parent = child
        finally:
            for descriptor in reversed(descriptors):
                os.close(descriptor)

    @classmethod
    def _read_legacy_project_mapping_id(cls, text: str) -> str | None:
        """Read the one direct ``project.project_id`` compatibility shape."""

        lines = text.splitlines()
        project_headers = [
            index
            for index, line in enumerate(lines)
            if _PROJECT_MAPPING_HEADER_PATTERN.fullmatch(line) is not None
        ]
        if len(project_headers) != 1:
            return None
        for line in lines[project_headers[0] + 1 :]:
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if not line.startswith((" ", "\t")):
                return None
            match = _PROJECT_MAPPING_ID_PATTERN.fullmatch(line)
            if match is not None:
                return match.group("value")
        return None

    @classmethod
    def read_canonical_project_id_from_text(
        cls,
        text: str,
        *,
        candidate: str,
    ) -> str:
        """Validate one project identity through the shared lexical contract."""

        canonical_candidate = cls._validate_story_slug(candidate)
        matches = [
            match.group("value")
            for match in _PROJECT_ID_PATTERN.finditer(text)
        ]
        declarations = _PROJECT_ID_DECLARATION_PATTERN.findall(text)
        legacy_project_id = cls._read_legacy_project_mapping_id(text)
        if len(declarations) != 1 or (
            matches != [canonical_candidate]
            and legacy_project_id != canonical_candidate
        ):
            raise StoryWorkspaceEpisodeBindingContractError(
                "canonical project identity does not match"
            )
        return canonical_candidate

    @classmethod
    def _read_project_text_from_story_directory(
        cls,
        story_descriptor: int,
        *,
        optional: bool,
    ) -> str | None:
        descriptor = -1
        try:
            descriptor = os.open(
                "project.yaml",
                cls._file_flags(),
                dir_fd=story_descriptor,
            )
        except FileNotFoundError:
            if optional:
                return None
            raise StoryWorkspaceEpisodeBindingPathError(
                "canonical project identity is unavailable"
            ) from None
        except OSError as exc:
            raise StoryWorkspaceEpisodeBindingPathError(
                "canonical project identity cannot be opened safely"
            ) from exc
        try:
            pinned = os.fstat(descriptor)
            visible = os.stat(
                "project.yaml",
                dir_fd=story_descriptor,
                follow_symlinks=False,
            )
            if (
                not stat.S_ISREG(pinned.st_mode)
                or stat.S_ISLNK(visible.st_mode)
                or not stat.S_ISREG(visible.st_mode)
                or (pinned.st_dev, pinned.st_ino) != (visible.st_dev, visible.st_ino)
                or pinned.st_size > _PROJECT_MAX_BYTES
            ):
                raise StoryWorkspaceEpisodeBindingPathError(
                    "canonical project identity is unsafe"
                )
            payload = bytearray()
            while len(payload) <= _PROJECT_MAX_BYTES:
                chunk = os.read(
                    descriptor,
                    min(8192, _PROJECT_MAX_BYTES + 1 - len(payload)),
                )
                if not chunk:
                    break
                payload.extend(chunk)
            if len(payload) > _PROJECT_MAX_BYTES:
                raise StoryWorkspaceEpisodeBindingContractError(
                    "canonical project identity exceeds the size limit"
                )
            try:
                text = payload.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise StoryWorkspaceEpisodeBindingContractError(
                    "canonical project identity is unreadable"
                ) from exc
            return text
        except OSError as exc:
            raise StoryWorkspaceEpisodeBindingPathError(
                "canonical project identity cannot be read safely"
            ) from exc
        finally:
            if descriptor >= 0:
                os.close(descriptor)

    @classmethod
    def _read_project_id_from_story_directory(
        cls,
        story_descriptor: int,
        *,
        candidate: str,
        optional: bool,
    ) -> str | None:
        text = cls._read_project_text_from_story_directory(
            story_descriptor,
            optional=optional,
        )
        if text is None:
            return None
        return cls.read_canonical_project_id_from_text(
            text,
            candidate=candidate,
        )

    def discover_unique_canonical_project_story_slug(self) -> str | None:
        """Return the sole server-proven project identity, never an Agent choice."""

        descriptors: list[int] = []
        try:
            workspace_descriptor = self._open_workspace()
            descriptors.append(workspace_descriptor)
            stories_descriptor = self._open_child_directory(
                workspace_descriptor,
                "stories",
                create=False,
                optional=True,
            )
            if stories_descriptor is None:
                return None
            descriptors.append(stories_descriptor)
            candidates: list[str] = []
            try:
                names = os.listdir(stories_descriptor)
            except OSError as exc:
                raise StoryWorkspaceEpisodeBindingPathError(
                    "canonical project directory cannot be listed safely"
                ) from exc
            for name in sorted(names):
                if _STORY_SLUG_PATTERN.fullmatch(name) is None:
                    continue
                story_descriptor = self._open_child_directory(
                    stories_descriptor,
                    name,
                    create=False,
                    optional=False,
                )
                assert story_descriptor is not None
                try:
                    project_id = self._read_project_id_from_story_directory(
                        story_descriptor,
                        candidate=name,
                        optional=True,
                    )
                finally:
                    os.close(story_descriptor)
                if project_id is not None:
                    candidates.append(project_id)
            return candidates[0] if len(candidates) == 1 else None
        finally:
            for descriptor in reversed(descriptors):
                os.close(descriptor)

    def read_canonical_project_story_slug(self, story_slug: str) -> str:
        """Read one exact project.yaml identity through pinned, no-follow FDs."""

        candidate = self._validate_story_slug(story_slug)
        descriptors: list[int] = []
        try:
            parent = self._open_workspace()
            descriptors.append(parent)
            for component in ("stories", candidate):
                child = self._open_child_directory(
                    parent,
                    component,
                    create=False,
                )
                assert child is not None
                descriptors.append(child)
                parent = child
            project_id = self._read_project_id_from_story_directory(
                parent,
                candidate=candidate,
                optional=False,
            )
            assert project_id is not None
            return project_id
        finally:
            for opened in reversed(descriptors):
                os.close(opened)

    def read_canonical_project_total_episodes(self, story_slug: str) -> int | None:
        """Read the optional trusted Drama Forge Episode horizon from project.yaml."""

        candidate = self._validate_story_slug(story_slug)
        descriptors: list[int] = []
        try:
            parent = self._open_workspace()
            descriptors.append(parent)
            for component in ("stories", candidate):
                child = self._open_child_directory(parent, component, create=False)
                assert child is not None
                descriptors.append(child)
                parent = child
            text = self._read_project_text_from_story_directory(
                parent,
                optional=False,
            )
            assert text is not None
            self.read_canonical_project_id_from_text(text, candidate=candidate)
            declarations = _TOTAL_EPISODES_DECLARATION_PATTERN.findall(text)
            matches = [
                int(match.group("value"))
                for match in _TOTAL_EPISODES_PATTERN.finditer(text)
            ]
            if not declarations:
                return None
            if len(declarations) != 1 or len(matches) != 1:
                raise StoryWorkspaceEpisodeBindingContractError(
                    "canonical project Episode count is ambiguous"
                )
            return matches[0]
        finally:
            for opened in reversed(descriptors):
                os.close(opened)

    def read_canonical_project_name(self, story_slug: str) -> str | None:
        """Read one bounded display name through the pinned project.yaml FD.

        Project identity remains the directory/project_id slug.  The optional
        name is display-only and deliberately uses a conservative lexical
        parser so arbitrary YAML objects, tags, paths, or credential-looking
        values never reach a public Story title.
        """

        candidate = self._validate_story_slug(story_slug)
        descriptors: list[int] = []
        try:
            parent = self._open_workspace()
            descriptors.append(parent)
            for component in ("stories", candidate):
                child = self._open_child_directory(parent, component, create=False)
                assert child is not None
                descriptors.append(child)
                parent = child
            text = self._read_project_text_from_story_directory(
                parent,
                optional=False,
            )
            assert text is not None
            self.read_canonical_project_id_from_text(text, candidate=candidate)
            matches = [
                match.group("value").strip()
                for match in _PROJECT_NAME_DECLARATION_PATTERN.finditer(text)
            ]
            if len(matches) != 1:
                return None
            value = matches[0]
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                value = value[1:-1].strip()
            if (
                not value
                or len(value) > 255
                or value in {".", ".."}
                or value.startswith(("/", "~/", "./", "../"))
                or re.match(r"^[A-Za-z]:[\\/]", value) is not None
                or "/" in value
                or "\\" in value
                or "://" in value
                or any(ord(character) < 32 or ord(character) == 127 for character in value)
                or _PROJECT_NAME_SECRET_PATTERN.search(value) is not None
            ):
                return None
            return value
        finally:
            for opened in reversed(descriptors):
                os.close(opened)

    @classmethod
    def _read_binding_payload(
        cls,
        run_descriptor: int,
    ) -> dict[str, object] | None:
        try:
            descriptor = os.open(
                "episode.json",
                cls._file_flags(),
                dir_fd=run_descriptor,
            )
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise StoryWorkspaceEpisodeBindingPathError(
                "Episode binding cannot be opened safely"
            ) from exc
        try:
            pinned = os.fstat(descriptor)
            visible = os.stat(
                "episode.json",
                dir_fd=run_descriptor,
                follow_symlinks=False,
            )
            if (
                not stat.S_ISREG(pinned.st_mode)
                or stat.S_ISLNK(visible.st_mode)
                or not stat.S_ISREG(visible.st_mode)
                or (pinned.st_dev, pinned.st_ino)
                != (visible.st_dev, visible.st_ino)
            ):
                raise StoryWorkspaceEpisodeBindingPathError(
                    "Episode binding is unsafe"
                )
            if pinned.st_size > _BINDING_MAX_BYTES:
                raise StoryWorkspaceEpisodeBindingContractError(
                    "Episode binding exceeds the size limit"
                )
            chunks: list[bytes] = []
            total = 0
            while True:
                chunk = os.read(descriptor, min(8192, _BINDING_MAX_BYTES + 1 - total))
                if not chunk:
                    break
                chunks.append(chunk)
                total += len(chunk)
                if total > _BINDING_MAX_BYTES:
                    raise StoryWorkspaceEpisodeBindingContractError(
                        "Episode binding exceeds the size limit"
                    )
        except OSError as exc:
            raise StoryWorkspaceEpisodeBindingPathError(
                "Episode binding cannot be read safely"
            ) from exc
        finally:
            os.close(descriptor)
        try:
            payload = json.loads(b"".join(chunks))
            if not isinstance(payload, dict):
                raise TypeError("Episode binding payload must be an object")
            return payload
        except (json.JSONDecodeError, UnicodeDecodeError, TypeError) as exc:
            raise StoryWorkspaceEpisodeBindingContractError(
                "Episode binding is not a valid JSON object"
            ) from exc

    @classmethod
    def _read_binding(
        cls,
        run_descriptor: int,
    ) -> StoryWorkspaceEpisodeBindingFile | None:
        payload = cls._read_binding_payload(run_descriptor)
        if payload is None:
            return None
        try:
            return StoryWorkspaceEpisodeBindingFile.model_validate(payload)
        except ValidationError as exc:
            raise StoryWorkspaceEpisodeBindingContractError(
                "Episode binding violates dream-episode/v1"
            ) from exc

    @classmethod
    def _read_registry(
        cls,
        run_descriptor: int,
    ) -> StoryWorkspaceEpisodeRegistryFile | None:
        payload = cls._read_binding_payload(run_descriptor)
        if payload is None:
            return None
        try:
            if payload.get("schema_version") == "dream-episode/v1":
                legacy = StoryWorkspaceEpisodeBindingFile.model_validate(payload)
                return StoryWorkspaceEpisodeRegistryFile(
                    workflow_run_id=legacy.workflow_run_id,
                    story_slug=legacy.story_slug,
                    active_episode_uid=legacy.episode_uid,
                    episodes=[
                        StoryWorkspaceEpisodeBindingEntry(
                            episode_uid=legacy.episode_uid,
                            episode_number=1,
                            episode_code=legacy.episode_code,
                            episode_root=legacy.episode_root,
                            created_at=legacy.updated_at,
                        )
                    ],
                    revision=legacy.revision,
                    updated_at=legacy.updated_at,
                )
            return StoryWorkspaceEpisodeRegistryFile.model_validate(payload)
        except ValidationError as exc:
            raise StoryWorkspaceEpisodeBindingContractError(
                "Episode binding violates the supported registry contract"
            ) from exc

    @staticmethod
    def _validate_binding_authority(
        binding: StoryWorkspaceEpisodeBindingFile,
        *,
        workflow_run_id: str,
        story_slug: str,
        episode_uid: str | None = None,
    ) -> None:
        if binding.workflow_run_id != workflow_run_id:
            raise StoryWorkspaceEpisodeBindingIdentityConflict(
                "Episode binding run identity cannot be changed"
            )
        if binding.story_slug != story_slug:
            raise StoryWorkspaceEpisodeBindingIdentityConflict(
                "Episode binding story identity cannot be changed"
            )
        if episode_uid is not None and binding.episode_uid != episode_uid:
            raise StoryWorkspaceEpisodeBindingIdentityConflict(
                "Episode binding opaque identity cannot be changed"
            )

    @staticmethod
    def _binding_identity(
        binding: StoryWorkspaceEpisodeBindingFile,
    ) -> tuple[str, str, str, str, str, str]:
        return (
            binding.schema_version,
            binding.workflow_run_id,
            binding.episode_uid,
            binding.story_slug,
            binding.episode_code,
            binding.episode_root,
        )

    @classmethod
    def _write_first_binding(
        cls,
        run_descriptor: int,
        binding: StoryWorkspaceEpisodeBindingFile,
    ) -> StoryWorkspaceEpisodeBindingFile:
        temporary_name = f".episode.{uuid4().hex}.tmp"
        descriptor = -1
        try:
            descriptor = os.open(
                temporary_name,
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
                | os.O_NOFOLLOW
                | getattr(os, "O_CLOEXEC", 0),
                0o600,
                dir_fd=run_descriptor,
            )
            payload = (binding.model_dump_json() + "\n").encode("utf-8")
            view = memoryview(payload)
            while view:
                written = os.write(descriptor, view)
                if written <= 0:
                    raise OSError("short write")
                view = view[written:]
            os.fsync(descriptor)
            os.close(descriptor)
            descriptor = -1
            try:
                os.link(
                    temporary_name,
                    "episode.json",
                    src_dir_fd=run_descriptor,
                    dst_dir_fd=run_descriptor,
                    follow_symlinks=False,
                )
            except FileExistsError:
                current = cls._read_binding(run_descriptor)
                if current is None:
                    raise StoryWorkspaceEpisodeBindingPathError(
                        "Episode binding CAS target disappeared"
                    ) from None
                if cls._binding_identity(current) != cls._binding_identity(binding):
                    raise StoryWorkspaceEpisodeBindingIdentityConflict(
                        "Episode binding identity won a competing first commit"
                    ) from None
                return current
            os.fsync(run_descriptor)
            return binding
        except OSError as exc:
            raise StoryWorkspaceEpisodeBindingPathError(
                "Episode binding cannot be committed safely"
            ) from exc
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            try:
                os.unlink(temporary_name, dir_fd=run_descriptor)
            except FileNotFoundError:
                pass
            except OSError:
                pass
            else:
                try:
                    os.fsync(run_descriptor)
                except OSError:
                    pass

    @classmethod
    def _replace_registry(
        cls,
        run_descriptor: int,
        registry: StoryWorkspaceEpisodeRegistryFile,
    ) -> StoryWorkspaceEpisodeRegistryFile:
        """Atomically replace a registry after its revision was checked under lock."""

        temporary_name = f".episode.{uuid4().hex}.tmp"
        descriptor = -1
        try:
            descriptor = os.open(
                temporary_name,
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
                | os.O_NOFOLLOW
                | getattr(os, "O_CLOEXEC", 0),
                0o600,
                dir_fd=run_descriptor,
            )
            payload = (registry.model_dump_json() + "\n").encode("utf-8")
            if len(payload) > _BINDING_MAX_BYTES:
                raise StoryWorkspaceEpisodeBindingContractError(
                    "Episode registry exceeds the size limit"
                )
            view = memoryview(payload)
            while view:
                written = os.write(descriptor, view)
                if written <= 0:
                    raise OSError("short write")
                view = view[written:]
            os.fsync(descriptor)
            os.close(descriptor)
            descriptor = -1
            os.replace(
                temporary_name,
                "episode.json",
                src_dir_fd=run_descriptor,
                dst_dir_fd=run_descriptor,
            )
            os.fsync(run_descriptor)
            return registry
        except StoryWorkspaceEpisodeBindingContractError:
            raise
        except OSError as exc:
            raise StoryWorkspaceEpisodeBindingPathError(
                "Episode registry cannot be committed safely"
            ) from exc
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            try:
                os.unlink(temporary_name, dir_fd=run_descriptor)
            except FileNotFoundError:
                pass
            except OSError:
                pass

    @staticmethod
    def _validate_registry_authority(
        registry: StoryWorkspaceEpisodeRegistryFile,
        *,
        workflow_run_id: str,
        story_slug: str,
    ) -> None:
        if registry.workflow_run_id != workflow_run_id:
            raise StoryWorkspaceEpisodeBindingIdentityConflict(
                "Episode registry run identity cannot be changed"
            )
        if registry.story_slug != story_slug:
            raise StoryWorkspaceEpisodeBindingIdentityConflict(
                "Episode registry story identity cannot be changed"
            )

    @staticmethod
    def _validate_registry_revision(value: object) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise StoryWorkspaceEpisodeBindingContractError(
                "expected Episode registry revision is invalid"
            )
        return value

    @staticmethod
    def _validate_total_episodes(value: object) -> int:
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 1
            or value > 99
        ):
            raise StoryWorkspaceEpisodeBindingContractError(
                "trusted total Episode count is invalid"
            )
        return value

    def read_episode_registry(
        self,
        context: StoryWorkspaceEpisodeBindingContext,
    ) -> StoryWorkspaceEpisodeRegistryFile:
        """Read v2 identity facts, projecting legacy EP01 without rewriting it."""

        story_slug = self._proved_story_slug(context, allow_unproven=False)
        assert story_slug is not None
        run_id = self._validate_run_id(context.workflow_run_id)
        with self._locked_run_directory(run_id) as run_descriptor:
            registry = self._read_registry(run_descriptor)
            if registry is None:
                raise StoryWorkspaceEpisodeBindingContractError(
                    "Episode registry has not been bound"
                )
            self._validate_registry_authority(
                registry,
                workflow_run_id=run_id,
                story_slug=story_slug,
            )
            return registry

    def read_episode_registry_read_only(
        self,
        context: StoryWorkspaceEpisodeBindingContext,
    ) -> StoryWorkspaceEpisodeRegistryFile:
        """Read an existing registry without creating run directories or locks."""

        story_slug = self._proved_story_slug(context, allow_unproven=False)
        assert story_slug is not None
        run_id = self._validate_run_id(context.workflow_run_id)
        descriptors: list[int] = []
        try:
            parent = self._open_workspace()
            descriptors.append(parent)
            for name in (".dream", "runtime", "runs", run_id):
                child = self._open_child_directory(
                    parent,
                    name,
                    create=False,
                    optional=False,
                )
                assert child is not None
                descriptors.append(child)
                parent = child
            registry = self._read_registry(parent)
            if registry is None:
                raise StoryWorkspaceEpisodeBindingContractError(
                    "Episode registry has not been bound"
                )
            self._validate_registry_authority(
                registry,
                workflow_run_id=run_id,
                story_slug=story_slug,
            )
            return registry
        finally:
            for descriptor in reversed(descriptors):
                os.close(descriptor)

    def ensure_next_episode(
        self,
        context: StoryWorkspaceEpisodeBindingContext,
        *,
        expected_revision: int,
        total_episodes: int,
    ) -> StoryWorkspaceEpisodeRegistryFile:
        """CAS-create the active Episode's next server-numbered binding."""

        story_slug = self._proved_story_slug(context, allow_unproven=False)
        assert story_slug is not None
        run_id = self._validate_run_id(context.workflow_run_id)
        expected = self._validate_registry_revision(expected_revision)
        trusted_total = self._validate_total_episodes(total_episodes)
        with self._locked_run_directory(run_id) as run_descriptor:
            current = self._read_registry(run_descriptor)
            if current is None:
                raise StoryWorkspaceEpisodeBindingContractError(
                    "Episode registry has not been bound"
                )
            self._validate_registry_authority(
                current,
                workflow_run_id=run_id,
                story_slug=story_slug,
            )
            active = next(
                episode
                for episode in current.episodes
                if episode.episode_uid == current.active_episode_uid
            )
            next_number = active.episode_number + 1
            existing_next = next(
                (
                    episode
                    for episode in current.episodes
                    if episode.episode_number == next_number
                ),
                None,
            )
            if current.revision != expected:
                if current.revision == expected + 1 and existing_next is not None:
                    return current
                raise StoryWorkspaceEpisodeBindingContractError(
                    "Episode registry revision is stale"
                )
            if existing_next is not None:
                return current
            if next_number > trusted_total:
                raise StoryWorkspaceEpisodeBindingContractError(
                    "next Episode exceeds the trusted project plan"
                )
            episode_code = f"EP{next_number:02d}"
            now = datetime.now(timezone.utc)
            updated = StoryWorkspaceEpisodeRegistryFile(
                workflow_run_id=current.workflow_run_id,
                story_slug=current.story_slug,
                active_episode_uid=current.active_episode_uid,
                episodes=[
                    *current.episodes,
                    StoryWorkspaceEpisodeBindingEntry(
                        episode_uid=uuid4().hex,
                        episode_number=next_number,
                        episode_code=episode_code,
                        episode_root=(
                            f"stories/{current.story_slug}/episodes/{episode_code}"
                        ),
                        created_at=now,
                    ),
                ],
                revision=current.revision + 1,
                updated_at=now,
            )
            return self._replace_registry(run_descriptor, updated)

    def activate_episode(
        self,
        context: StoryWorkspaceEpisodeBindingContext,
        *,
        episode_uid: str,
        expected_revision: int,
    ) -> StoryWorkspaceEpisodeRegistryFile:
        """CAS-select a registry member by opaque identity, never by list index."""

        story_slug = self._proved_story_slug(context, allow_unproven=False)
        assert story_slug is not None
        run_id = self._validate_run_id(context.workflow_run_id)
        target_uid = self._validate_episode_uid(episode_uid)
        expected = self._validate_registry_revision(expected_revision)
        with self._locked_run_directory(run_id) as run_descriptor:
            current = self._read_registry(run_descriptor)
            if current is None:
                raise StoryWorkspaceEpisodeBindingContractError(
                    "Episode registry has not been bound"
                )
            self._validate_registry_authority(
                current,
                workflow_run_id=run_id,
                story_slug=story_slug,
            )
            if current.revision != expected:
                raise StoryWorkspaceEpisodeBindingContractError(
                    "Episode registry revision is stale"
                )
            if not any(
                episode.episode_uid == target_uid for episode in current.episodes
            ):
                raise StoryWorkspaceEpisodeBindingIdentityConflict(
                    "target Episode is not bound to this registry"
                )
            if current.active_episode_uid == target_uid:
                return current
            now = datetime.now(timezone.utc)
            updated = StoryWorkspaceEpisodeRegistryFile(
                workflow_run_id=current.workflow_run_id,
                story_slug=current.story_slug,
                active_episode_uid=target_uid,
                episodes=current.episodes,
                revision=current.revision + 1,
                updated_at=now,
            )
            return self._replace_registry(run_descriptor, updated)

    def bind_first_episode(
        self,
        context: StoryWorkspaceEpisodeBindingContext,
    ) -> StoryWorkspaceEpisodeBindingFile:
        """CAS-create EP01 or return the identical immutable binding."""

        story_slug = self._proved_story_slug(context, allow_unproven=False)
        assert story_slug is not None
        run_id = self._validate_run_id(context.workflow_run_id)
        with self._locked_run_directory(run_id) as run_descriptor:
            payload = self._read_binding_payload(run_descriptor)
            if payload is not None and payload.get("schema_version") == "dream-episode/v2":
                registry = self._read_registry(run_descriptor)
                assert registry is not None
                self._validate_registry_authority(
                    registry,
                    workflow_run_id=run_id,
                    story_slug=story_slug,
                )
                requested_uid = (
                    self._validate_episode_uid(context.episode_uid)
                    if context.episode_uid is not None
                    else registry.episodes[0].episode_uid
                )
                first = registry.episodes[0]
                if requested_uid != first.episode_uid:
                    raise StoryWorkspaceEpisodeBindingIdentityConflict(
                        "legacy first-Episode binding view requires EP01 authority"
                    )
                return StoryWorkspaceEpisodeBindingFile(
                    workflow_run_id=registry.workflow_run_id,
                    episode_uid=first.episode_uid,
                    story_slug=registry.story_slug,
                    episode_code="EP01",
                    episode_root=first.episode_root,
                    revision=1,
                    updated_at=first.created_at,
                )
            current = self._read_binding(run_descriptor)
            if current is not None:
                self._validate_binding_authority(
                    current,
                    workflow_run_id=run_id,
                    story_slug=story_slug,
                    episode_uid=context.episode_uid,
                )
                return current
            self._validate_episode_root(story_slug)
            binding = StoryWorkspaceEpisodeBindingFile(
                workflow_run_id=run_id,
                episode_uid=(
                    self._validate_episode_uid(context.episode_uid)
                    if context.episode_uid is not None
                    else uuid4().hex
                ),
                story_slug=story_slug,
                episode_code="EP01",
                episode_root=f"stories/{story_slug}/episodes/EP01",
                revision=1,
                updated_at=datetime.now(timezone.utc),
            )
            committed = self._write_first_binding(run_descriptor, binding)
            self._validate_binding_authority(
                committed,
                workflow_run_id=run_id,
                story_slug=story_slug,
                episode_uid=context.episode_uid,
            )
            return committed

    def resolve_or_repair_binding(
        self,
        context: StoryWorkspaceEpisodeBindingContext,
    ) -> StoryWorkspaceEpisodeBindingResolution:
        """Repair a provable legacy binding without guessing or artifact probing."""

        story_slug = self._proved_story_slug(context, allow_unproven=True)
        if story_slug is None:
            return StoryWorkspaceEpisodeBindingResolution(
                binding_availability=StoryWorkspaceEpisodeBindingAvailability.UNBOUND,
                recovery=StoryWorkspaceEpisodeBindingRecovery(
                    autoRepairAttempted=True,
                    canDispatch=True,
                    publicReason="episode_binding_unproven",
                ),
            )
        binding = self.bind_first_episode(context)
        return StoryWorkspaceEpisodeBindingResolution(
            binding_availability=StoryWorkspaceEpisodeBindingAvailability.BOUND,
            recovery=StoryWorkspaceEpisodeBindingRecovery(
                autoRepairAttempted=True,
                canDispatch=False,
            ),
            binding=binding,
        )
