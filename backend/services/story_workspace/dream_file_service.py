"""Atomic, fail-closed reader/writer for the ``.dream/runtime`` protocol.

The runtime protocol deliberately requires Unix ``flock`` plus secure
``dir_fd``/``O_NOFOLLOW`` primitives. Every operation pins the directory inode
chain from ``.dream`` through the run/stages directory and performs all JSON
I/O relative to those descriptors. Paths are used only to establish and later
verify the pinned identities; they are never reopened after the run lock.
"""

from __future__ import annotations

import errno
import inspect
import json
import os
import re
import stat
import sys
import threading
import warnings
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Callable, Iterator, TypeVar
from uuid import uuid4

try:  # Import-safe on Windows; construction fails with a public exception.
    import fcntl
except ImportError:  # pragma: no cover - exercised by capability simulation.
    fcntl = None  # type: ignore[assignment]

from pydantic import BaseModel, ValidationError

try:
    from models.workflow_run import WorkflowRun
    from story_workspace.contracts import (
        STORY_WORKSPACE_DREAM_FILE_MAX_BYTES,
        STORY_WORKSPACE_DREAM_REQUIRED_STAGES,
        StoryWorkspaceDreamFilesResponse,
        StoryWorkspaceDreamRunFile,
        StoryWorkspaceDreamSource,
        StoryWorkspaceDreamSourceResponse,
        StoryWorkspaceDreamStage,
        StoryWorkspaceDreamStageFile,
        StoryWorkspaceDreamStageItem,
        StoryWorkspaceDreamStageItemResponse,
        StoryWorkspaceDreamStagePage,
        StoryWorkspaceDreamStagePageResponse,
        StoryWorkspaceDreamStageResponse,
    )
except ModuleNotFoundError:  # Support repository-root package imports.
    from backend.models.workflow_run import WorkflowRun
    from backend.story_workspace.contracts import (
        STORY_WORKSPACE_DREAM_FILE_MAX_BYTES,
        STORY_WORKSPACE_DREAM_REQUIRED_STAGES,
        StoryWorkspaceDreamFilesResponse,
        StoryWorkspaceDreamRunFile,
        StoryWorkspaceDreamSource,
        StoryWorkspaceDreamSourceResponse,
        StoryWorkspaceDreamStage,
        StoryWorkspaceDreamStageFile,
        StoryWorkspaceDreamStageItem,
        StoryWorkspaceDreamStageItemResponse,
        StoryWorkspaceDreamStagePage,
        StoryWorkspaceDreamStagePageResponse,
        StoryWorkspaceDreamStageResponse,
    )


_RUN_ID_PATTERN = re.compile(r"^run_[0-9a-f]{32}$")
_STAGE_FILENAMES = {
    StoryWorkspaceDreamStage.CHARACTERS: "characters.json",
    StoryWorkspaceDreamStage.SCENES: "scenes.json",
    StoryWorkspaceDreamStage.STORYBOARDS: "storyboards.json",
}
_STAGE_TITLES = {
    StoryWorkspaceDreamStage.CHARACTERS: "人物",
    StoryWorkspaceDreamStage.SCENES: "场景",
    StoryWorkspaceDreamStage.STORYBOARDS: "分镜",
}
_ModelT = TypeVar("_ModelT", bound=BaseModel)


class StoryWorkspaceDreamFileError(RuntimeError):
    """Base public failure for Dream runtime files."""


class StoryWorkspaceDreamContractError(StoryWorkspaceDreamFileError):
    """A request or on-disk JSON payload violated the canonical contract."""


class StoryWorkspaceDreamPathError(StoryWorkspaceDreamFileError):
    """A path, symlink, or directory inode violated containment."""


class StoryWorkspaceDreamIOError(StoryWorkspaceDreamFileError):
    """An I/O operation failed before a durable state was established."""


class StoryWorkspaceDreamPlatformUnsupported(StoryWorkspaceDreamFileError):
    """The host lacks the primitives required by the Dream file protocol."""


class StoryWorkspaceDreamDurabilityIndeterminate(StoryWorkspaceDreamIOError):
    """The pinned and visible trees do not establish one trustworthy outcome."""

    def __init__(
        self,
        observed_revision: int | None,
        state_hint: str,
        *,
        visible_observed_revision: int | None = None,
    ) -> None:
        super().__init__(
            "Dream file durability is indeterminate; re-read the file before "
            "retrying "
            f"(pinned_revision={observed_revision}, "
            f"visible_revision={visible_observed_revision}, state={state_hint})"
        )
        self.observed_revision = observed_revision
        self.pinned_observed_revision = observed_revision
        self.visible_observed_revision = visible_observed_revision
        self.state_hint = state_hint


class StoryWorkspaceDreamFileConflict(StoryWorkspaceDreamFileError):
    """The expected revision did not match the current file revision."""

    def __init__(self, expected_revision: int, current_revision: int) -> None:
        super().__init__(
            "Dream file revision conflict: "
            f"expected {expected_revision}, current {current_revision}"
        )
        self.expected_revision = expected_revision
        self.current_revision = current_revision


def _platform_capability_reason() -> str | None:
    if fcntl is None or not callable(getattr(fcntl, "flock", None)):
        return "fcntl.flock is unavailable"
    for flag_name in ("O_DIRECTORY", "O_NOFOLLOW"):
        if not hasattr(os, flag_name):
            return f"os.{flag_name} is unavailable"
    for function in (os.open, os.stat, os.mkdir, os.unlink):
        if function not in os.supports_dir_fd:
            return f"{function.__name__} lacks dir_fd support"
    if os.stat not in os.supports_follow_symlinks:
        return "stat lacks follow_symlinks support"
    try:
        replace_parameters = inspect.signature(os.replace).parameters
    except (TypeError, ValueError):
        return "os.replace signature cannot be inspected"
    if not {"src_dir_fd", "dst_dir_fd"}.issubset(replace_parameters):
        return "os.replace lacks source/destination dir_fd support"
    return None


STORY_WORKSPACE_DREAM_PLATFORM_SUPPORTED = _platform_capability_reason() is None


def _require_platform() -> None:
    reason = _platform_capability_reason()
    if reason is not None:
        raise StoryWorkspaceDreamPlatformUnsupported(
            f"Dream runtime file protocol is unsupported on this platform: {reason}"
        )


def _coerce_stage(stage: StoryWorkspaceDreamStage | str) -> StoryWorkspaceDreamStage:
    try:
        return StoryWorkspaceDreamStage(stage)
    except (TypeError, ValueError) as exc:
        raise StoryWorkspaceDreamContractError("unsupported Dream stage") from exc


def _validate_expected_revision(expected_revision: int) -> None:
    if (
        isinstance(expected_revision, bool)
        or not isinstance(expected_revision, int)
        or expected_revision < 0
    ):
        raise StoryWorkspaceDreamContractError(
            "expected_revision must be a non-negative integer"
        )


def _authoritative_context(
    workflow_run: WorkflowRun,
) -> tuple[str, StoryWorkspaceDreamSource]:
    if not isinstance(workflow_run, WorkflowRun):
        raise StoryWorkspaceDreamContractError(
            "Dream file operations require an authoritative WorkflowRun"
        )
    run_id = workflow_run.workflow_run_id
    if _RUN_ID_PATTERN.fullmatch(run_id) is None:
        raise StoryWorkspaceDreamContractError(
            "authoritative workflow run id is invalid"
        )
    try:
        source = StoryWorkspaceDreamSource(
            deck_plugin_binding_id=workflow_run.deck_plugin_binding_id,
            binding_revision=workflow_run.binding_revision,
            deck_plugin_version=workflow_run.deck_plugin_version,
            deck_runtime_snapshot_id=workflow_run.deck_runtime_snapshot_id,
            runtime_plugin_lock_id=workflow_run.runtime_plugin_lock_id,
        )
    except ValidationError as exc:
        raise StoryWorkspaceDreamContractError(
            "authoritative workflow run source is incomplete"
        ) from exc
    return run_id, source


def _authoritative_thread_id(workflow_run: WorkflowRun) -> str:
    if not isinstance(workflow_run, WorkflowRun):
        raise StoryWorkspaceDreamContractError(
            "Dream file operations require an authoritative WorkflowRun"
        )
    thread_id = workflow_run.source_voice_thread_id
    if not isinstance(thread_id, str) or not thread_id.strip():
        raise StoryWorkspaceDreamContractError(
            "authoritative WorkflowRun does not identify a Chat thread"
        )
    return thread_id


def _validate_authoritative_thread(
    workflow_run: WorkflowRun,
    thread_id: str,
) -> None:
    if _authoritative_thread_id(workflow_run) != thread_id:
        raise StoryWorkspaceDreamContractError(
            "thread_id does not match the authoritative WorkflowRun"
        )


def _stage_page(
    stage: StoryWorkspaceDreamStage,
    run_id: str,
) -> StoryWorkspaceDreamStagePage:
    routes = {
        StoryWorkspaceDreamStage.CHARACTERS: (
            f"/story-workspace/characters?run={run_id}"
        ),
        StoryWorkspaceDreamStage.SCENES: f"/story-workspace/scenes?run={run_id}",
        StoryWorkspaceDreamStage.STORYBOARDS: (
            f"/story-workspace/runs/{run_id}/execution"
        ),
    }
    return StoryWorkspaceDreamStagePage(
        title=_STAGE_TITLES[stage],
        entry_route=routes[stage],
    )


@dataclass
class _LocalLockEntry:
    lock: threading.RLock
    references: int = 0


_THREAD_LOCKS_GUARD = threading.Lock()
_THREAD_LOCKS: dict[str, _LocalLockEntry] = {}


@contextmanager
def _local_run_lock(key: str) -> Iterator[None]:
    with _THREAD_LOCKS_GUARD:
        entry = _THREAD_LOCKS.get(key)
        if entry is None:
            entry = _LocalLockEntry(lock=threading.RLock())
            _THREAD_LOCKS[key] = entry
        entry.references += 1
    entry.lock.acquire()
    try:
        yield
    finally:
        entry.lock.release()
        with _THREAD_LOCKS_GUARD:
            entry.references -= 1
            if entry.references == 0 and _THREAD_LOCKS.get(key) is entry:
                del _THREAD_LOCKS[key]


@dataclass(frozen=True)
class _PinnedDirectory:
    descriptor: int
    parent_descriptor: int
    name: str


@dataclass(frozen=True)
class _PinnedRun:
    workspace_descriptor: int
    dream_descriptor: int
    runtime_descriptor: int
    runs_descriptor: int
    run_descriptor: int
    run_id: str

    @property
    def directory(self) -> _PinnedDirectory:
        return _PinnedDirectory(
            descriptor=self.run_descriptor,
            parent_descriptor=self.runs_descriptor,
            name=self.run_id,
        )


def _add_cleanup_note(primary: BaseException, cleanup: BaseException) -> None:
    try:
        primary.add_note(f"suppressed cleanup failure: {cleanup!r}")
    except AttributeError:  # pragma: no cover - Python 3.10 fallback.
        pass


class _StoryWorkspaceDreamFilesystem:
    def __init__(self, workspace_root: str | os.PathLike[str]) -> None:
        _require_platform()
        supplied_root = Path(workspace_root)
        try:
            resolved_root = supplied_root.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise StoryWorkspaceDreamPathError("workspace root does not exist") from exc
        if not resolved_root.is_dir():
            raise StoryWorkspaceDreamPathError("workspace root must be a directory")
        try:
            workspace_metadata = os.stat(resolved_root, follow_symlinks=False)
        except OSError as exc:
            raise StoryWorkspaceDreamPathError(
                "workspace root identity is unavailable"
            ) from exc
        self.workspace_root = resolved_root
        self.dream_root = resolved_root / ".dream"
        self._workspace_identity = (
            workspace_metadata.st_dev,
            workspace_metadata.st_ino,
        )

    @staticmethod
    def _directory_flags() -> int:
        return os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(
            os, "O_CLOEXEC", 0
        )

    @staticmethod
    def _file_flags() -> int:
        return os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)

    @staticmethod
    def _verify_directory_descriptor(descriptor: int) -> os.stat_result:
        try:
            metadata = os.fstat(descriptor)
        except OSError as exc:
            raise StoryWorkspaceDreamIOError(
                "unable to inspect Dream directory descriptor"
            ) from exc
        if not stat.S_ISDIR(metadata.st_mode):
            raise StoryWorkspaceDreamPathError(
                "Dream protocol component is not a directory"
            )
        return metadata

    @classmethod
    def _verify_child_identity(
        cls,
        parent_descriptor: int,
        name: str,
        child_descriptor: int,
    ) -> None:
        child_metadata = cls._verify_directory_descriptor(child_descriptor)
        try:
            visible_metadata = os.stat(
                name,
                dir_fd=parent_descriptor,
                follow_symlinks=False,
            )
        except OSError as exc:
            raise StoryWorkspaceDreamPathError(
                f"Dream directory identity is unavailable: {name}"
            ) from exc
        if stat.S_ISLNK(visible_metadata.st_mode) or not stat.S_ISDIR(
            visible_metadata.st_mode
        ):
            raise StoryWorkspaceDreamPathError(
                f"Dream protocol directory is unsafe: {name}"
            )
        if (visible_metadata.st_dev, visible_metadata.st_ino) != (
            child_metadata.st_dev,
            child_metadata.st_ino,
        ):
            raise StoryWorkspaceDreamPathError(
                f"Dream directory inode changed during operation: {name}"
            )

    def _verify_workspace_identity(self, descriptor: int) -> None:
        descriptor_metadata = self._verify_directory_descriptor(descriptor)
        if (descriptor_metadata.st_dev, descriptor_metadata.st_ino) != (
            self._workspace_identity
        ):
            raise StoryWorkspaceDreamPathError(
                "workspace root inode changed during operation"
            )
        try:
            visible_metadata = os.stat(self.workspace_root, follow_symlinks=False)
        except OSError as exc:
            raise StoryWorkspaceDreamPathError(
                "workspace root identity is unavailable"
            ) from exc
        if (visible_metadata.st_dev, visible_metadata.st_ino) != (
            descriptor_metadata.st_dev,
            descriptor_metadata.st_ino,
        ):
            raise StoryWorkspaceDreamPathError(
                "workspace root inode changed during operation"
            )

    @classmethod
    def _open_child_directory(
        cls,
        parent_descriptor: int,
        name: str,
        *,
        create: bool,
        optional: bool = False,
    ) -> int | None:
        if create:
            try:
                os.mkdir(name, mode=0o700, dir_fd=parent_descriptor)
            except FileExistsError:
                pass
            except OSError as exc:
                raise StoryWorkspaceDreamIOError(
                    f"unable to create Dream directory: {name}"
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
            raise StoryWorkspaceDreamContractError(
                f"required Dream directory is missing: {name}"
            )
        except OSError as exc:
            raise StoryWorkspaceDreamPathError(
                f"unsafe Dream protocol directory: {name}"
            ) from exc
        try:
            cls._verify_child_identity(parent_descriptor, name, descriptor)
            return descriptor
        except BaseException:
            try:
                os.close(descriptor)
            except OSError:
                pass
            raise

    def _open_workspace_descriptor(self) -> int:
        """Open an absolute workspace one component at a time from ``/``."""

        anchor = self.workspace_root.anchor
        parts = self.workspace_root.parts
        if not anchor or not parts or parts[0] != anchor:
            raise StoryWorkspaceDreamPathError(
                "workspace root must be an absolute path"
            )
        descriptor = -1
        try:
            descriptor = os.open(anchor, self._directory_flags())
            self._verify_directory_descriptor(descriptor)
            for component in parts[1:]:
                child_descriptor = self._open_child_directory(
                    descriptor,
                    component,
                    create=False,
                )
                assert child_descriptor is not None
                os.close(descriptor)
                descriptor = child_descriptor
        except BaseException as exc:
            if descriptor >= 0:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
            if not isinstance(exc, Exception):
                raise
            if isinstance(exc, StoryWorkspaceDreamPathError):
                raise
            raise StoryWorkspaceDreamPathError(
                "workspace root cannot be opened safely"
            ) from exc
        try:
            self._verify_workspace_identity(descriptor)
            return descriptor
        except BaseException:
            try:
                os.close(descriptor)
            except OSError:
                pass
            raise

    @staticmethod
    def _cleanup_descriptors(
        descriptors: list[int],
        primary: BaseException | None,
    ) -> None:
        first_cleanup_error: OSError | None = None
        for descriptor in reversed(descriptors):
            try:
                os.close(descriptor)
            except OSError as exc:
                if primary is not None:
                    _add_cleanup_note(primary, exc)
                elif first_cleanup_error is None:
                    first_cleanup_error = exc
        if first_cleanup_error is not None:
            raise StoryWorkspaceDreamIOError(
                "failed to close a Dream directory descriptor"
            ) from first_cleanup_error

    def _verify_run(self, run: _PinnedRun) -> None:
        self._verify_workspace_identity(run.workspace_descriptor)
        self._verify_child_identity(
            run.workspace_descriptor,
            ".dream",
            run.dream_descriptor,
        )
        self._verify_child_identity(
            run.dream_descriptor,
            "runtime",
            run.runtime_descriptor,
        )
        self._verify_child_identity(
            run.runtime_descriptor,
            "runs",
            run.runs_descriptor,
        )
        self._verify_child_identity(
            run.runs_descriptor,
            run.run_id,
            run.run_descriptor,
        )

    @contextmanager
    def _locked_run(
        self,
        run_id: str,
        *,
        create: bool,
        exclusive: bool,
    ) -> Iterator[_PinnedRun | None]:
        if _RUN_ID_PATTERN.fullmatch(run_id) is None:
            raise StoryWorkspaceDreamPathError("unsafe workflow run directory name")
        key = f"{self.workspace_root}:{run_id}"
        with _local_run_lock(key):
            descriptors: list[int] = []
            locked_descriptor: int | None = None
            primary: BaseException | None = None
            try:
                workspace_descriptor = self._open_workspace_descriptor()
                descriptors.append(workspace_descriptor)
                dream_descriptor = self._open_child_directory(
                    workspace_descriptor,
                    ".dream",
                    create=False,
                    optional=not create,
                )
                if dream_descriptor is None:
                    yield None
                    return
                assert dream_descriptor is not None
                descriptors.append(dream_descriptor)
                runtime_descriptor = self._open_child_directory(
                    dream_descriptor,
                    "runtime",
                    create=create,
                    optional=not create,
                )
                if runtime_descriptor is None:
                    yield None
                    return
                descriptors.append(runtime_descriptor)
                runs_descriptor = self._open_child_directory(
                    runtime_descriptor,
                    "runs",
                    create=create,
                    optional=not create,
                )
                if runs_descriptor is None:
                    yield None
                    return
                descriptors.append(runs_descriptor)
                run_descriptor = self._open_child_directory(
                    runs_descriptor,
                    run_id,
                    create=create,
                    optional=not create,
                )
                if run_descriptor is None:
                    yield None
                    return
                descriptors.append(run_descriptor)
                lock_operation = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
                try:
                    fcntl.flock(run_descriptor, lock_operation)
                except OSError as exc:
                    raise StoryWorkspaceDreamIOError(
                        "unable to acquire Dream run file lock"
                    ) from exc
                locked_descriptor = run_descriptor
                run = _PinnedRun(
                    workspace_descriptor=workspace_descriptor,
                    dream_descriptor=dream_descriptor,
                    runtime_descriptor=runtime_descriptor,
                    runs_descriptor=runs_descriptor,
                    run_descriptor=run_descriptor,
                    run_id=run_id,
                )
                self._verify_run(run)
                try:
                    yield run
                except BaseException as exc:
                    primary = exc
                    raise
            except BaseException as exc:
                if primary is None:
                    primary = exc
                raise
            finally:
                unlock_failure: StoryWorkspaceDreamIOError | None = None
                if locked_descriptor is not None:
                    try:
                        fcntl.flock(locked_descriptor, fcntl.LOCK_UN)
                    except OSError as exc:
                        if primary is not None:
                            _add_cleanup_note(primary, exc)
                        else:
                            unlock_failure = StoryWorkspaceDreamIOError(
                                "unable to release Dream run file lock"
                            )
                            unlock_failure.__cause__ = exc
                try:
                    self._cleanup_descriptors(
                        descriptors,
                        primary or unlock_failure,
                    )
                except StoryWorkspaceDreamIOError:
                    if primary is None and unlock_failure is None:
                        raise
                if primary is None and unlock_failure is not None:
                    raise unlock_failure

    @contextmanager
    def _stages_directory(
        self,
        run: _PinnedRun,
        *,
        create: bool,
    ) -> Iterator[_PinnedDirectory | None]:
        descriptor = self._open_child_directory(
            run.run_descriptor,
            "stages",
            create=create,
            optional=not create,
        )
        if descriptor is None:
            yield None
            return
        pinned = _PinnedDirectory(
            descriptor=descriptor,
            parent_descriptor=run.run_descriptor,
            name="stages",
        )
        primary: BaseException | None = None
        try:
            self._verify_run(run)
            self._verify_child_identity(
                pinned.parent_descriptor,
                pinned.name,
                pinned.descriptor,
            )
            try:
                yield pinned
            except BaseException as exc:
                primary = exc
                raise
        finally:
            try:
                os.close(descriptor)
            except OSError as exc:
                if primary is not None or sys.exc_info()[0] is not None:
                    _add_cleanup_note(primary or sys.exc_info()[1], exc)  # type: ignore[arg-type]
                else:
                    raise StoryWorkspaceDreamIOError(
                        "failed to close Dream stages descriptor"
                    ) from exc

    @classmethod
    def _read_bytes(
        cls,
        directory_descriptor: int,
        filename: str,
        *,
        required: bool,
    ) -> bytes | None:
        try:
            descriptor = os.open(
                filename,
                cls._file_flags(),
                dir_fd=directory_descriptor,
            )
        except FileNotFoundError:
            if required:
                raise StoryWorkspaceDreamContractError(
                    f"required Dream file is missing: {filename}"
                )
            return None
        except OSError as exc:
            error_class = (
                StoryWorkspaceDreamPathError
                if exc.errno in {errno.ELOOP, errno.ENOTDIR}
                else StoryWorkspaceDreamIOError
            )
            raise error_class(f"unable to open Dream file: {filename}") from exc
        try:
            try:
                metadata = os.fstat(descriptor)
            except OSError as exc:
                raise StoryWorkspaceDreamIOError(
                    f"unable to inspect Dream file: {filename}"
                ) from exc
            if not stat.S_ISREG(metadata.st_mode):
                raise StoryWorkspaceDreamPathError(
                    f"Dream file is not regular: {filename}"
                )
            if metadata.st_size > STORY_WORKSPACE_DREAM_FILE_MAX_BYTES:
                raise StoryWorkspaceDreamContractError(
                    f"Dream file exceeds size limit: {filename}"
                )
            try:
                with os.fdopen(descriptor, "rb", closefd=True) as handle:
                    descriptor = -1
                    payload = handle.read(STORY_WORKSPACE_DREAM_FILE_MAX_BYTES + 1)
            except OSError as exc:
                raise StoryWorkspaceDreamIOError(
                    f"unable to read Dream file: {filename}"
                ) from exc
            if len(payload) > STORY_WORKSPACE_DREAM_FILE_MAX_BYTES:
                raise StoryWorkspaceDreamContractError(
                    f"Dream file exceeds size limit: {filename}"
                )
            return payload
        finally:
            if descriptor >= 0:
                try:
                    os.close(descriptor)
                except OSError:
                    pass

    @classmethod
    def _read_model(
        cls,
        directory_descriptor: int,
        filename: str,
        model: type[_ModelT],
        *,
        required: bool,
    ) -> _ModelT | None:
        payload = cls._read_bytes(
            directory_descriptor,
            filename,
            required=required,
        )
        if payload is None:
            return None
        try:
            return model.model_validate_json(payload)
        except (ValidationError, ValueError) as exc:
            raise StoryWorkspaceDreamContractError(
                f"Dream file schema is invalid: {filename}"
            ) from exc

    @classmethod
    def _existing_bytes(
        cls,
        directory_descriptor: int,
        filename: str,
    ) -> bytes | None:
        return cls._read_bytes(directory_descriptor, filename, required=False)

    @staticmethod
    def _write_temp(
        directory_descriptor: int,
        temporary_name: str,
        payload: bytes,
    ) -> None:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
        flags |= getattr(os, "O_CLOEXEC", 0)
        descriptor = os.open(
            temporary_name,
            flags,
            0o600,
            dir_fd=directory_descriptor,
        )
        try:
            with os.fdopen(descriptor, "wb", closefd=True) as handle:
                descriptor = -1
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
        finally:
            if descriptor >= 0:
                os.close(descriptor)

    @staticmethod
    def _payload_revision(payload: bytes | None) -> int | None:
        if payload is None:
            return None
        try:
            revision = json.loads(payload).get("revision")
        except (AttributeError, TypeError, ValueError):
            return None
        if isinstance(revision, bool) or not isinstance(revision, int):
            return None
        return revision

    @classmethod
    def _observe_revision(
        cls,
        directory_descriptor: int,
        filename: str,
    ) -> int | None:
        try:
            return cls._payload_revision(
                cls._existing_bytes(directory_descriptor, filename)
            )
        except StoryWorkspaceDreamFileError:
            return None

    def _observe_root_visible_revision(
        self,
        run_id: str,
        filename: str,
        *,
        in_stages_directory: bool,
    ) -> int | None:
        descriptors: list[int] = []
        pinned_children: list[tuple[int, str, int]] = []
        try:
            workspace_descriptor = self._open_workspace_descriptor()
            descriptors.append(workspace_descriptor)
            parent_descriptor = workspace_descriptor
            component_names = [".dream", "runtime", "runs", run_id]
            if in_stages_directory:
                component_names.append("stages")
            for component_name in component_names:
                child_descriptor = self._open_child_directory(
                    parent_descriptor,
                    component_name,
                    create=False,
                    optional=True,
                )
                if child_descriptor is None:
                    return None
                descriptors.append(child_descriptor)
                pinned_children.append(
                    (parent_descriptor, component_name, child_descriptor)
                )
                parent_descriptor = child_descriptor
            observed_revision = self._observe_revision(
                parent_descriptor,
                filename,
            )
            self._verify_workspace_identity(workspace_descriptor)
            for parent, name, child in pinned_children:
                self._verify_child_identity(parent, name, child)
            return observed_revision
        except StoryWorkspaceDreamFileError:
            return None
        finally:
            for descriptor in reversed(descriptors):
                try:
                    os.close(descriptor)
                except OSError:
                    pass

    @staticmethod
    def _cleanup_names(
        directory_descriptor: int,
        names: list[str],
        primary: BaseException | None,
    ) -> None:
        first_error: OSError | None = None
        for name in names:
            try:
                os.unlink(name, dir_fd=directory_descriptor)
            except FileNotFoundError:
                continue
            except OSError as exc:
                if primary is not None:
                    _add_cleanup_note(primary, exc)
                elif first_error is None:
                    first_error = exc
        if first_error is not None:
            raise StoryWorkspaceDreamIOError(
                "unable to clean Dream temporary file"
            ) from first_error

    @staticmethod
    def _normalize_operation_error(
        error: Exception,
        context: str,
    ) -> StoryWorkspaceDreamFileError:
        if isinstance(error, StoryWorkspaceDreamFileError):
            return error
        if isinstance(error, ValidationError):
            return StoryWorkspaceDreamContractError(context)
        if isinstance(error, OSError):
            return StoryWorkspaceDreamIOError(context)
        return StoryWorkspaceDreamFileError(context)

    @classmethod
    def _atomic_replace(
        cls,
        directory: _PinnedDirectory,
        filename: str,
        payload: bytes,
        *,
        previous_revision: int,
        next_revision: int,
        verify_context: Callable[[], None],
        observe_root_visible_revision: Callable[[], int | None],
    ) -> None:
        if len(payload) > STORY_WORKSPACE_DREAM_FILE_MAX_BYTES:
            raise StoryWorkspaceDreamContractError(
                "serialized Dream file exceeds size limit"
            )
        temporary_name = f".{filename}.{uuid4().hex}.tmp"
        rollback_name = f".{filename}.{uuid4().hex}.rollback.tmp"
        cleanup_names = [temporary_name, rollback_name]
        old_payload: bytes | None = None
        replace_attempted = False
        replaced = False
        durable = False
        try:
            verify_context()
            old_payload = cls._existing_bytes(directory.descriptor, filename)
            cls._write_temp(directory.descriptor, temporary_name, payload)
            verify_context()
            replace_attempted = True
            os.replace(
                temporary_name,
                filename,
                src_dir_fd=directory.descriptor,
                dst_dir_fd=directory.descriptor,
            )
            replaced = True
            verify_context()
            os.fsync(directory.descriptor)
            durable = True
            verify_context()
        except Exception as operation_error:
            if durable:
                pinned_observed_revision = cls._observe_revision(
                    directory.descriptor,
                    filename,
                )
                visible_observed_revision = observe_root_visible_revision()
                state_hint = "durable-commit-context-changed"
                if visible_observed_revision is None:
                    state_hint = "pinned-commit-root-visible-unavailable"
                elif (
                    pinned_observed_revision == next_revision
                    and visible_observed_revision == previous_revision
                ):
                    state_hint = "pinned-commit-visible-directory-replaced"
                indeterminate = StoryWorkspaceDreamDurabilityIndeterminate(
                    pinned_observed_revision,
                    state_hint,
                    visible_observed_revision=visible_observed_revision,
                )
                _add_cleanup_note(indeterminate, operation_error)
                cls._cleanup_names(
                    directory.descriptor,
                    cleanup_names,
                    indeterminate,
                )
                raise indeterminate from operation_error
            if replace_attempted and not replaced:
                try:
                    replaced = (
                        cls._existing_bytes(directory.descriptor, filename)
                        != old_payload
                    )
                except StoryWorkspaceDreamFileError:
                    replaced = False
            if replaced:
                rollback_error: Exception | None = None
                try:
                    verify_context()
                    if old_payload is None:
                        os.unlink(filename, dir_fd=directory.descriptor)
                    else:
                        cls._write_temp(
                            directory.descriptor,
                            rollback_name,
                            old_payload,
                        )
                        verify_context()
                        os.replace(
                            rollback_name,
                            filename,
                            src_dir_fd=directory.descriptor,
                            dst_dir_fd=directory.descriptor,
                        )
                    verify_context()
                    os.fsync(directory.descriptor)
                except Exception as exc:
                    rollback_error = exc
                if rollback_error is not None:
                    observed_revision = cls._observe_revision(
                        directory.descriptor,
                        filename,
                    )
                    visible_observed_revision = observe_root_visible_revision()
                    if visible_observed_revision is None:
                        state_hint = (
                            "rollback-failed-root-visible-unavailable"
                        )
                    elif observed_revision == next_revision:
                        state_hint = "replacement-visible-rollback-failed"
                    elif observed_revision == previous_revision:
                        state_hint = "rollback-visible-durability-unknown"
                    else:
                        state_hint = "final-state-unknown"
                    indeterminate = StoryWorkspaceDreamDurabilityIndeterminate(
                        observed_revision,
                        state_hint,
                        visible_observed_revision=visible_observed_revision,
                    )
                    _add_cleanup_note(indeterminate, operation_error)
                    cls._cleanup_names(
                        directory.descriptor,
                        cleanup_names,
                        indeterminate,
                    )
                    raise indeterminate from rollback_error
            public_error = cls._normalize_operation_error(
                operation_error,
                "Dream file atomic replacement failed",
            )
            cls._cleanup_names(
                directory.descriptor,
                cleanup_names,
                public_error,
            )
            if public_error is operation_error:
                raise public_error
            raise public_error from operation_error
        try:
            cls._cleanup_names(directory.descriptor, cleanup_names, None)
        except StoryWorkspaceDreamIOError as cleanup_error:
            try:
                warnings.warn(
                    "Dream file commit is durable, but temporary-file cleanup "
                    f"failed: {cleanup_error}",
                    RuntimeWarning,
                    stacklevel=2,
                )
            except Exception:
                # Warning policy or hooks must not turn a durable commit into a
                # reported operation failure.
                pass

    def _validate_source_file(
        self,
        relative_path: str,
        workspace_descriptor: int,
    ) -> None:
        if not isinstance(relative_path, str) or not relative_path:
            raise StoryWorkspaceDreamPathError("source file path must be non-blank")
        if "\\" in relative_path:
            raise StoryWorkspaceDreamPathError(
                "source file path must use POSIX separators"
            )
        pure_path = PurePosixPath(relative_path)
        if pure_path.is_absolute() or any(
            part in {"", ".", ".."} for part in pure_path.parts
        ):
            raise StoryWorkspaceDreamPathError(
                "source file path must be safely relative"
            )
        directory_descriptors: list[int] = []
        pinned_children: list[tuple[int, str, int]] = []
        file_descriptor = -1
        try:
            parent_descriptor = workspace_descriptor
            for component in pure_path.parts[:-1]:
                child_descriptor = self._open_child_directory(
                    parent_descriptor,
                    component,
                    create=False,
                )
                assert child_descriptor is not None
                directory_descriptors.append(child_descriptor)
                pinned_children.append(
                    (parent_descriptor, component, child_descriptor)
                )
                parent_descriptor = child_descriptor
            filename = pure_path.parts[-1]
            file_descriptor = os.open(
                filename,
                self._file_flags(),
                dir_fd=parent_descriptor,
            )
            file_metadata = os.fstat(file_descriptor)
            visible_metadata = os.stat(
                filename,
                dir_fd=parent_descriptor,
                follow_symlinks=False,
            )
            if (
                not stat.S_ISREG(file_metadata.st_mode)
                or stat.S_ISLNK(visible_metadata.st_mode)
                or not stat.S_ISREG(visible_metadata.st_mode)
                or (file_metadata.st_dev, file_metadata.st_ino)
                != (visible_metadata.st_dev, visible_metadata.st_ino)
            ):
                raise StoryWorkspaceDreamPathError(
                    f"source file is unsafe: {relative_path}"
                )
            self._verify_workspace_identity(workspace_descriptor)
            for parent, name, child in pinned_children:
                self._verify_child_identity(parent, name, child)
        except StoryWorkspaceDreamPathError:
            raise
        except (OSError, RuntimeError, StoryWorkspaceDreamFileError) as exc:
            raise StoryWorkspaceDreamPathError(
                f"source file cannot be opened safely: {relative_path}"
            ) from exc
        finally:
            if file_descriptor >= 0:
                try:
                    os.close(file_descriptor)
                except OSError:
                    pass
            for descriptor in reversed(directory_descriptors):
                try:
                    os.close(descriptor)
                except OSError:
                    pass

    def _validate_source_files(
        self,
        stage_file: StoryWorkspaceDreamStageFile,
        workspace_descriptor: int,
    ) -> None:
        for source_file in stage_file.source_files:
            self._validate_source_file(source_file, workspace_descriptor)


class StoryWorkspaceDreamFileWriter(_StoryWorkspaceDreamFilesystem):
    """CAS writer deriving run identity/provenance from ``WorkflowRun``."""

    def write_run(
        self,
        workflow_run: WorkflowRun,
        *,
        thread_id: str,
        expected_revision: int,
    ) -> StoryWorkspaceDreamRunFile:
        _validate_expected_revision(expected_revision)
        _validate_authoritative_thread(workflow_run, thread_id)
        run_id, source = _authoritative_context(workflow_run)
        with self._locked_run(run_id, create=True, exclusive=True) as run:
            assert run is not None
            self._verify_run(run)
            current = self._read_model(
                run.run_descriptor,
                "run.json",
                StoryWorkspaceDreamRunFile,
                required=False,
            )
            self._verify_run(run)
            if current is not None:
                self._validate_run_authority(
                    current,
                    run_id=run_id,
                    source=source,
                    thread_id=thread_id,
                )
            current_revision = current.revision if current is not None else 0
            if expected_revision != current_revision:
                raise StoryWorkspaceDreamFileConflict(
                    expected_revision,
                    current_revision,
                )
            try:
                next_file = StoryWorkspaceDreamRunFile(
                    workflow_run_id=run_id,
                    thread_id=thread_id,
                    source=source,
                    projection_entry=(
                        f"/api/story-workspace/workflow-runs/{run_id}/dream-files"
                    ),
                    revision=current_revision + 1,
                )
            except ValidationError as exc:
                raise StoryWorkspaceDreamContractError(
                    "Dream run file payload is invalid"
                ) from exc
            self._atomic_replace(
                run.directory,
                "run.json",
                self._serialize(next_file),
                previous_revision=current_revision,
                next_revision=next_file.revision,
                verify_context=lambda: self._verify_run(run),
                observe_root_visible_revision=lambda: (
                    self._observe_root_visible_revision(
                        run_id,
                        "run.json",
                        in_stages_directory=False,
                    )
                ),
            )
            return next_file

    def write_stage(
        self,
        workflow_run: WorkflowRun,
        *,
        stage: StoryWorkspaceDreamStage | str,
        source_files: list[str],
        items: list[dict[str, object] | StoryWorkspaceDreamStageItem],
        expected_revision: int,
        filename: str | None = None,
    ) -> StoryWorkspaceDreamStageFile:
        _validate_expected_revision(expected_revision)
        thread_id = _authoritative_thread_id(workflow_run)
        canonical_stage = _coerce_stage(stage)
        canonical_filename = _STAGE_FILENAMES[canonical_stage]
        if filename is not None and filename != canonical_filename:
            raise StoryWorkspaceDreamPathError("stage filename does not match stage")
        run_id, source = _authoritative_context(workflow_run)
        try:
            candidate = StoryWorkspaceDreamStageFile(
                workflow_run_id=run_id,
                stage=canonical_stage,
                revision=expected_revision + 1,
                source_files=source_files,
                page=_stage_page(canonical_stage, run_id),
                items=items,
            )
        except ValidationError as exc:
            raise StoryWorkspaceDreamContractError(
                "Dream stage file payload is invalid"
            ) from exc

        with self._locked_run(run_id, create=False, exclusive=True) as run:
            if run is None:
                raise StoryWorkspaceDreamContractError("Dream run has not been created")
            self._verify_run(run)
            run_file = self._read_model(
                run.run_descriptor,
                "run.json",
                StoryWorkspaceDreamRunFile,
                required=True,
            )
            assert run_file is not None
            self._verify_run(run)
            self._validate_run_authority(
                run_file,
                run_id=run_id,
                source=source,
                thread_id=thread_id,
            )
            self._validate_source_files(candidate, run.workspace_descriptor)
            with self._stages_directory(run, create=True) as stages:
                assert stages is not None

                def verify_stage_context() -> None:
                    self._verify_run(run)
                    self._verify_child_identity(
                        stages.parent_descriptor,
                        stages.name,
                        stages.descriptor,
                    )

                verify_stage_context()
                current = self._read_model(
                    stages.descriptor,
                    canonical_filename,
                    StoryWorkspaceDreamStageFile,
                    required=False,
                )
                verify_stage_context()
                if current is not None:
                    self._validate_stage_identity(
                        current,
                        run_id,
                        canonical_stage,
                    )
                    self._validate_source_files(current, run.workspace_descriptor)
                current_revision = current.revision if current is not None else 0
                if expected_revision != current_revision:
                    raise StoryWorkspaceDreamFileConflict(
                        expected_revision,
                        current_revision,
                    )
                self._atomic_replace(
                    stages,
                    canonical_filename,
                    self._serialize(candidate),
                    previous_revision=current_revision,
                    next_revision=candidate.revision,
                    verify_context=verify_stage_context,
                    observe_root_visible_revision=lambda: (
                        self._observe_root_visible_revision(
                            run_id,
                            canonical_filename,
                            in_stages_directory=True,
                        )
                    ),
                )
                return candidate

    @staticmethod
    def _serialize(model: BaseModel) -> bytes:
        try:
            payload = json.dumps(
                model.model_dump(mode="json", by_alias=False),
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8") + b"\n"
        except (TypeError, ValueError) as exc:
            raise StoryWorkspaceDreamContractError(
                "Dream file contains non-JSON values"
            ) from exc
        if len(payload) > STORY_WORKSPACE_DREAM_FILE_MAX_BYTES:
            raise StoryWorkspaceDreamContractError(
                "serialized Dream file exceeds size limit"
            )
        return payload

    @staticmethod
    def _validate_run_authority(
        run_file: StoryWorkspaceDreamRunFile,
        *,
        run_id: str,
        source: StoryWorkspaceDreamSource,
        thread_id: str,
    ) -> None:
        if run_file.workflow_run_id != run_id:
            raise StoryWorkspaceDreamContractError(
                "run.json workflow run mismatch"
            )
        if run_file.source != source:
            raise StoryWorkspaceDreamContractError(
                "run.json source does not match authoritative WorkflowRun"
            )
        if run_file.thread_id != thread_id:
            raise StoryWorkspaceDreamContractError(
                "run.json thread does not match authoritative context"
            )

    @staticmethod
    def _validate_stage_identity(
        stage_file: StoryWorkspaceDreamStageFile,
        run_id: str,
        stage: StoryWorkspaceDreamStage,
    ) -> None:
        if stage_file.workflow_run_id != run_id or stage_file.stage is not stage:
            raise StoryWorkspaceDreamContractError(
                "Dream stage file does not match run directory and filename"
            )


class StoryWorkspaceDreamFileReader(_StoryWorkspaceDreamFilesystem):
    """Read-only snapshot loader; missing stages are a legal waiting state."""

    def read_run(
        self,
        workflow_run: WorkflowRun,
        *,
        thread_id: str,
    ) -> StoryWorkspaceDreamRunFile:
        _validate_authoritative_thread(workflow_run, thread_id)
        run_id, source = _authoritative_context(workflow_run)
        with self._locked_run(run_id, create=False, exclusive=False) as run:
            if run is None:
                raise StoryWorkspaceDreamContractError("Dream run has not been created")
            run_file = self._read_and_validate_run(
                run,
                run_id,
                source,
                thread_id=thread_id,
            )
            self._verify_run(run)
            return run_file

    def read_stage(
        self,
        workflow_run: WorkflowRun,
        *,
        stage: StoryWorkspaceDreamStage | str,
    ) -> StoryWorkspaceDreamStageFile | None:
        thread_id = _authoritative_thread_id(workflow_run)
        canonical_stage = _coerce_stage(stage)
        run_id, source = _authoritative_context(workflow_run)
        with self._locked_run(run_id, create=False, exclusive=False) as run:
            if run is None:
                raise StoryWorkspaceDreamContractError("Dream run has not been created")
            self._read_and_validate_run(
                run,
                run_id,
                source,
                thread_id=thread_id,
            )
            with self._stages_directory(run, create=False) as stages:
                if stages is None:
                    return None
                self._verify_read_context(run, stages)
                stage_file = self._read_model(
                    stages.descriptor,
                    _STAGE_FILENAMES[canonical_stage],
                    StoryWorkspaceDreamStageFile,
                    required=False,
                )
                self._verify_read_context(run, stages)
                if stage_file is None:
                    return None
                self._validate_stage(
                    stage_file,
                    run_id,
                    canonical_stage,
                    run.workspace_descriptor,
                )
                return stage_file

    def read_stage_file(
        self,
        workflow_run: WorkflowRun,
        *,
        filename: str,
    ) -> StoryWorkspaceDreamStageFile | None:
        matches = [
            stage for stage, name in _STAGE_FILENAMES.items() if name == filename
        ]
        if len(matches) != 1:
            raise StoryWorkspaceDreamPathError(
                "filename is not a canonical stage file"
            )
        return self.read_stage(workflow_run, stage=matches[0])

    def read(
        self,
        workflow_run: WorkflowRun,
        *,
        thread_id: str,
    ) -> StoryWorkspaceDreamFilesResponse:
        _validate_authoritative_thread(workflow_run, thread_id)
        run_id, source = _authoritative_context(workflow_run)
        with self._locked_run(run_id, create=False, exclusive=False) as run:
            if run is None:
                return self._waiting_response(run_id, thread_id, source)
            run_file = self._read_model(
                run.run_descriptor,
                "run.json",
                StoryWorkspaceDreamRunFile,
                required=False,
            )
            self._verify_run(run)
            if run_file is None:
                return self._waiting_response(run_id, thread_id, source)
            StoryWorkspaceDreamFileWriter._validate_run_authority(
                run_file,
                run_id=run_id,
                source=source,
                thread_id=thread_id,
            )
            stage_responses: dict[
                StoryWorkspaceDreamStage, StoryWorkspaceDreamStageResponse
            ] = {}
            with self._stages_directory(run, create=False) as stages:
                if stages is not None:
                    for stage in STORY_WORKSPACE_DREAM_REQUIRED_STAGES:
                        self._verify_read_context(run, stages)
                        stage_file = self._read_model(
                            stages.descriptor,
                            _STAGE_FILENAMES[stage],
                            StoryWorkspaceDreamStageFile,
                            required=False,
                        )
                        self._verify_read_context(run, stages)
                        if stage_file is None:
                            continue
                        self._validate_stage(
                            stage_file,
                            run_id,
                            stage,
                            run.workspace_descriptor,
                        )
                        stage_responses[stage] = self._stage_response(stage_file)
            complete = set(stage_responses) == set(
                STORY_WORKSPACE_DREAM_REQUIRED_STAGES
            )
            try:
                return StoryWorkspaceDreamFilesResponse(
                    story_workspace_run_id=run_id,
                    thread_id=run_file.thread_id,
                    source=StoryWorkspaceDreamSourceResponse.model_validate(
                        run_file.source.model_dump()
                    ),
                    required_stages=list(run_file.required_stages),
                    run_revision=run_file.revision,
                    stages=stage_responses,
                    can_confirm=complete,
                )
            except ValidationError as exc:
                raise StoryWorkspaceDreamContractError(
                    "Dream response projection is invalid"
                ) from exc

    def _verify_read_context(
        self,
        run: _PinnedRun,
        stages: _PinnedDirectory,
    ) -> None:
        self._verify_run(run)
        self._verify_child_identity(
            stages.parent_descriptor,
            stages.name,
            stages.descriptor,
        )

    @staticmethod
    def _stage_response(
        stage_file: StoryWorkspaceDreamStageFile,
    ) -> StoryWorkspaceDreamStageResponse:
        try:
            return StoryWorkspaceDreamStageResponse(
                stage=stage_file.stage,
                revision=stage_file.revision,
                source_files=stage_file.source_files,
                page=StoryWorkspaceDreamStagePageResponse.model_validate(
                    stage_file.page.model_dump()
                ),
                items=[
                    StoryWorkspaceDreamStageItemResponse.model_validate(
                        item.model_dump()
                    )
                    for item in stage_file.items
                ],
            )
        except ValidationError as exc:
            raise StoryWorkspaceDreamContractError(
                "Dream stage response projection is invalid"
            ) from exc

    @staticmethod
    def _waiting_response(
        run_id: str,
        thread_id: str,
        source: StoryWorkspaceDreamSource,
    ) -> StoryWorkspaceDreamFilesResponse:
        try:
            return StoryWorkspaceDreamFilesResponse(
                story_workspace_run_id=run_id,
                thread_id=thread_id,
                source=StoryWorkspaceDreamSourceResponse.model_validate(
                    source.model_dump()
                ),
                required_stages=list(STORY_WORKSPACE_DREAM_REQUIRED_STAGES),
                run_revision=0,
                stages={},
                can_confirm=False,
            )
        except ValidationError as exc:
            raise StoryWorkspaceDreamContractError(
                "Dream waiting response projection is invalid"
            ) from exc

    def _read_and_validate_run(
        self,
        run: _PinnedRun,
        run_id: str,
        source: StoryWorkspaceDreamSource,
        *,
        thread_id: str,
    ) -> StoryWorkspaceDreamRunFile:
        self._verify_run(run)
        run_file = self._read_model(
            run.run_descriptor,
            "run.json",
            StoryWorkspaceDreamRunFile,
            required=True,
        )
        self._verify_run(run)
        assert run_file is not None
        StoryWorkspaceDreamFileWriter._validate_run_authority(
            run_file,
            run_id=run_id,
            source=source,
            thread_id=thread_id,
        )
        return run_file

    def _validate_stage(
        self,
        stage_file: StoryWorkspaceDreamStageFile,
        run_id: str,
        stage: StoryWorkspaceDreamStage,
        workspace_descriptor: int,
    ) -> None:
        StoryWorkspaceDreamFileWriter._validate_stage_identity(
            stage_file,
            run_id,
            stage,
        )
        self._validate_source_files(stage_file, workspace_descriptor)


__all__ = [
    "STORY_WORKSPACE_DREAM_PLATFORM_SUPPORTED",
    "StoryWorkspaceDreamContractError",
    "StoryWorkspaceDreamDurabilityIndeterminate",
    "StoryWorkspaceDreamFileConflict",
    "StoryWorkspaceDreamFileError",
    "StoryWorkspaceDreamFileReader",
    "StoryWorkspaceDreamFileWriter",
    "StoryWorkspaceDreamIOError",
    "StoryWorkspaceDreamPathError",
    "StoryWorkspaceDreamPlatformUnsupported",
]
