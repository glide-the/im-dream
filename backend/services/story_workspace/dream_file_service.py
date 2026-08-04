"""Atomic, fail-closed reader/writer for the ``.dream/runtime`` protocol."""

from __future__ import annotations

import fcntl
import json
import os
import re
import stat
import threading
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from typing import Iterator, TypeVar
from uuid import uuid4

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

_THREAD_LOCKS_GUARD = threading.Lock()
_THREAD_LOCKS: dict[str, threading.RLock] = {}
_ModelT = TypeVar("_ModelT", bound=BaseModel)


class StoryWorkspaceDreamFileError(RuntimeError):
    """Base class for a malformed, unsafe, or inconsistent Dream file."""


class StoryWorkspaceDreamPathError(StoryWorkspaceDreamFileError):
    """A caller-controlled or on-disk path crossed the protocol boundary."""


class StoryWorkspaceDreamFileConflict(StoryWorkspaceDreamFileError):
    """The expected revision did not match the current file revision."""

    def __init__(self, expected_revision: int, current_revision: int) -> None:
        super().__init__(
            "Dream file revision conflict: "
            f"expected {expected_revision}, current {current_revision}"
        )
        self.expected_revision = expected_revision
        self.current_revision = current_revision


def _coerce_stage(stage: StoryWorkspaceDreamStage | str) -> StoryWorkspaceDreamStage:
    try:
        return StoryWorkspaceDreamStage(stage)
    except (TypeError, ValueError) as exc:
        raise StoryWorkspaceDreamFileError("unsupported Dream stage") from exc


def _validate_expected_revision(expected_revision: int) -> None:
    if (
        isinstance(expected_revision, bool)
        or not isinstance(expected_revision, int)
        or expected_revision < 0
    ):
        raise StoryWorkspaceDreamFileError(
            "expected_revision must be a non-negative integer"
        )


def _authoritative_context(
    workflow_run: WorkflowRun,
) -> tuple[str, StoryWorkspaceDreamSource]:
    if not isinstance(workflow_run, WorkflowRun):
        raise StoryWorkspaceDreamFileError(
            "Dream file operations require an authoritative WorkflowRun"
        )
    run_id = workflow_run.workflow_run_id
    if _RUN_ID_PATTERN.fullmatch(run_id) is None:
        raise StoryWorkspaceDreamFileError("authoritative workflow run id is invalid")
    try:
        source = StoryWorkspaceDreamSource(
            deck_plugin_binding_id=workflow_run.deck_plugin_binding_id,
            binding_revision=workflow_run.binding_revision,
            deck_plugin_version=workflow_run.deck_plugin_version,
            deck_runtime_snapshot_id=workflow_run.deck_runtime_snapshot_id,
            runtime_plugin_lock_id=workflow_run.runtime_plugin_lock_id,
        )
    except ValidationError as exc:
        raise StoryWorkspaceDreamFileError(
            "authoritative workflow run source is incomplete"
        ) from exc
    return run_id, source


def _validate_authoritative_thread(
    workflow_run: WorkflowRun,
    thread_id: str,
) -> None:
    authoritative_thread_id = _authoritative_thread_id(workflow_run)
    if authoritative_thread_id != thread_id:
        raise StoryWorkspaceDreamFileError(
            "thread_id does not match the authoritative WorkflowRun"
        )


def _authoritative_thread_id(workflow_run: WorkflowRun) -> str:
    if not isinstance(workflow_run, WorkflowRun):
        raise StoryWorkspaceDreamFileError(
            "Dream file operations require an authoritative WorkflowRun"
        )
    thread_id = workflow_run.source_voice_thread_id
    if not isinstance(thread_id, str) or not thread_id.strip():
        raise StoryWorkspaceDreamFileError(
            "authoritative WorkflowRun does not identify a Chat thread"
        )
    return thread_id


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


def _thread_lock(key: str) -> threading.RLock:
    with _THREAD_LOCKS_GUARD:
        return _THREAD_LOCKS.setdefault(key, threading.RLock())


class _StoryWorkspaceDreamFilesystem:
    def __init__(self, workspace_root: str | os.PathLike[str]) -> None:
        supplied_root = Path(workspace_root)
        try:
            resolved_root = supplied_root.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise StoryWorkspaceDreamPathError("workspace root does not exist") from exc
        if not resolved_root.is_dir():
            raise StoryWorkspaceDreamPathError("workspace root must be a directory")
        self.workspace_root = resolved_root
        self.dream_root = resolved_root / ".dream"

    @staticmethod
    def _open_directory(path: Path) -> int:
        flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
        flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(path, flags)
        except OSError as exc:
            raise StoryWorkspaceDreamPathError(
                f"unsafe Dream protocol directory: {path.name}"
            ) from exc
        if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
            os.close(descriptor)
            raise StoryWorkspaceDreamPathError(
                "Dream protocol component is not a directory"
            )
        return descriptor

    def _validate_directory(self, path: Path, *, within: Path) -> None:
        try:
            metadata = path.lstat()
            resolved = path.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise StoryWorkspaceDreamPathError(
                f"Dream protocol directory is unavailable: {path.name}"
            ) from exc
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise StoryWorkspaceDreamPathError(
                f"Dream protocol directory is unsafe: {path.name}"
            )
        try:
            contained = resolved.is_relative_to(within.resolve(strict=True))
        except (OSError, RuntimeError) as exc:
            raise StoryWorkspaceDreamPathError(
                "unable to resolve Dream directory"
            ) from exc
        if not contained:
            raise StoryWorkspaceDreamPathError(
                "Dream protocol directory escaped workspace"
            )
        descriptor = self._open_directory(path)
        os.close(descriptor)

    def _validate_dream_root(self) -> None:
        self._validate_directory(self.dream_root, within=self.workspace_root)

    def _ensure_directory(self, path: Path, *, within: Path) -> None:
        try:
            path.mkdir(mode=0o700)
        except FileExistsError:
            pass
        except OSError as exc:
            raise StoryWorkspaceDreamPathError(
                f"unable to create Dream protocol directory: {path.name}"
            ) from exc
        self._validate_directory(path, within=within)

    def _run_directory(self, run_id: str, *, create: bool) -> Path:
        if _RUN_ID_PATTERN.fullmatch(run_id) is None:
            raise StoryWorkspaceDreamPathError("unsafe workflow run directory name")
        self._validate_dream_root()
        runtime = self.dream_root / "runtime"
        runs = runtime / "runs"
        run_directory = runs / run_id
        if create:
            self._ensure_directory(runtime, within=self.dream_root)
            self._ensure_directory(runs, within=runtime)
            self._ensure_directory(run_directory, within=runs)
        else:
            self._validate_directory(runtime, within=self.dream_root)
            self._validate_directory(runs, within=runtime)
            self._validate_directory(run_directory, within=runs)
        return run_directory

    def _optional_run_directory(self, run_id: str) -> Path | None:
        """Resolve an existing run tree without creating any path component."""

        if _RUN_ID_PATTERN.fullmatch(run_id) is None:
            raise StoryWorkspaceDreamPathError("unsafe workflow run directory name")
        self._validate_dream_root()
        runtime = self.dream_root / "runtime"
        runs = runtime / "runs"
        run_directory = runs / run_id
        for path, within in (
            (runtime, self.dream_root),
            (runs, runtime),
            (run_directory, runs),
        ):
            try:
                path.lstat()
            except FileNotFoundError:
                return None
            except OSError as exc:
                raise StoryWorkspaceDreamPathError(
                    f"Dream protocol directory is unavailable: {path.name}"
                ) from exc
            self._validate_directory(path, within=within)
        return run_directory

    @contextmanager
    def _locked_run(self, run_id: str, *, create: bool) -> Iterator[Path]:
        key = f"{self.workspace_root}:{run_id}"
        with _thread_lock(key):
            run_directory = self._run_directory(run_id, create=create)
            descriptor = self._open_directory(run_directory)
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX)
                yield run_directory
            finally:
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_UN)
                finally:
                    os.close(descriptor)

    def _stages_directory(self, run_directory: Path, *, create: bool) -> Path:
        stages = run_directory / "stages"
        if create:
            self._ensure_directory(stages, within=run_directory)
        else:
            self._validate_directory(stages, within=run_directory)
        return stages

    @staticmethod
    def _read_model(
        directory: Path,
        filename: str,
        model: type[_ModelT],
        *,
        required: bool,
    ) -> _ModelT | None:
        directory_descriptor = _StoryWorkspaceDreamFilesystem._open_directory(directory)
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0)
        try:
            try:
                descriptor = os.open(filename, flags, dir_fd=directory_descriptor)
            except FileNotFoundError:
                if required:
                    raise StoryWorkspaceDreamFileError(
                        f"required Dream file is missing: {filename}"
                    )
                return None
            except OSError as exc:
                raise StoryWorkspaceDreamPathError(
                    f"unsafe Dream file target: {filename}"
                ) from exc
            try:
                metadata = os.fstat(descriptor)
                if not stat.S_ISREG(metadata.st_mode):
                    raise StoryWorkspaceDreamPathError(
                        f"Dream file is not a regular file: {filename}"
                    )
                if metadata.st_size > STORY_WORKSPACE_DREAM_FILE_MAX_BYTES:
                    raise StoryWorkspaceDreamFileError(
                        f"Dream file exceeds size limit: {filename}"
                    )
                with os.fdopen(descriptor, "rb", closefd=True) as handle:
                    descriptor = -1
                    payload = handle.read(STORY_WORKSPACE_DREAM_FILE_MAX_BYTES + 1)
                if len(payload) > STORY_WORKSPACE_DREAM_FILE_MAX_BYTES:
                    raise StoryWorkspaceDreamFileError(
                        f"Dream file exceeds size limit: {filename}"
                    )
            finally:
                if descriptor >= 0:
                    os.close(descriptor)
        finally:
            os.close(directory_descriptor)

        try:
            return model.model_validate_json(payload)
        except (ValidationError, ValueError) as exc:
            raise StoryWorkspaceDreamFileError(
                f"Dream file schema is invalid: {filename}"
            ) from exc

    @staticmethod
    def _existing_bytes(directory_descriptor: int, filename: str) -> bytes | None:
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(filename, flags, dir_fd=directory_descriptor)
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise StoryWorkspaceDreamPathError(
                f"unsafe Dream file target: {filename}"
            ) from exc
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode):
                raise StoryWorkspaceDreamPathError(
                    f"Dream file is not regular: {filename}"
                )
            with os.fdopen(descriptor, "rb", closefd=True) as handle:
                descriptor = -1
                return handle.read(STORY_WORKSPACE_DREAM_FILE_MAX_BYTES + 1)
        finally:
            if descriptor >= 0:
                os.close(descriptor)

    @staticmethod
    def _write_temp(
        directory_descriptor: int,
        temporary_name: str,
        payload: bytes,
    ) -> None:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
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

    @classmethod
    def _restore_after_durability_error(
        cls,
        directory_descriptor: int,
        filename: str,
        old_payload: bytes | None,
    ) -> None:
        try:
            if old_payload is None:
                os.unlink(filename, dir_fd=directory_descriptor)
            else:
                rollback_name = f".{filename}.{uuid4().hex}.rollback.tmp"
                try:
                    cls._write_temp(directory_descriptor, rollback_name, old_payload)
                    os.replace(
                        rollback_name,
                        filename,
                        src_dir_fd=directory_descriptor,
                        dst_dir_fd=directory_descriptor,
                    )
                finally:
                    try:
                        os.unlink(rollback_name, dir_fd=directory_descriptor)
                    except FileNotFoundError:
                        pass
            try:
                os.fsync(directory_descriptor)
            except OSError:
                pass
        except OSError:
            # The original durability error remains the public failure. This
            # best-effort branch only runs after replace already succeeded.
            pass

    @classmethod
    def _atomic_replace(cls, directory: Path, filename: str, payload: bytes) -> None:
        if len(payload) > STORY_WORKSPACE_DREAM_FILE_MAX_BYTES:
            raise StoryWorkspaceDreamFileError(
                "serialized Dream file exceeds size limit"
            )
        directory_descriptor = cls._open_directory(directory)
        temporary_name = f".{filename}.{uuid4().hex}.tmp"
        replaced = False
        old_payload: bytes | None = None
        try:
            old_payload = cls._existing_bytes(directory_descriptor, filename)
            if (
                old_payload is not None
                and len(old_payload) > STORY_WORKSPACE_DREAM_FILE_MAX_BYTES
            ):
                raise StoryWorkspaceDreamFileError(
                    "existing Dream file exceeds size limit"
                )
            try:
                cls._write_temp(directory_descriptor, temporary_name, payload)
                os.replace(
                    temporary_name,
                    filename,
                    src_dir_fd=directory_descriptor,
                    dst_dir_fd=directory_descriptor,
                )
                replaced = True
                os.fsync(directory_descriptor)
            except Exception:
                # A syscall wrapper may report an error after the kernel has
                # already completed the atomic rename. Re-read the target so
                # every surfaced write exception still restores the previous
                # visible bytes, not merely failures known to occur pre-rename.
                target_changed = replaced
                if not target_changed:
                    try:
                        target_changed = (
                            cls._existing_bytes(directory_descriptor, filename)
                            != old_payload
                        )
                    except StoryWorkspaceDreamFileError:
                        target_changed = True
                if target_changed:
                    cls._restore_after_durability_error(
                        directory_descriptor,
                        filename,
                        old_payload,
                    )
                raise
            finally:
                try:
                    os.unlink(temporary_name, dir_fd=directory_descriptor)
                except FileNotFoundError:
                    pass
        finally:
            os.close(directory_descriptor)

    def _validate_source_file(self, relative_path: str) -> None:
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
        candidate = self.workspace_root.joinpath(*pure_path.parts)
        try:
            resolved = candidate.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise StoryWorkspaceDreamPathError(
                f"source file does not exist: {relative_path}"
            ) from exc
        if not resolved.is_relative_to(self.workspace_root) or not resolved.is_file():
            raise StoryWorkspaceDreamPathError(
                f"source file escaped workspace: {relative_path}"
            )

    def _validate_source_files(self, stage_file: StoryWorkspaceDreamStageFile) -> None:
        for source_file in stage_file.source_files:
            self._validate_source_file(source_file)


class StoryWorkspaceDreamFileWriter(_StoryWorkspaceDreamFilesystem):
    """CAS writer that derives run identity/provenance from ``WorkflowRun``."""

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
        with self._locked_run(run_id, create=True) as run_directory:
            current = self._read_model(
                run_directory,
                "run.json",
                StoryWorkspaceDreamRunFile,
                required=False,
            )
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
            next_file = StoryWorkspaceDreamRunFile(
                workflow_run_id=run_id,
                thread_id=thread_id,
                source=source,
                projection_entry=(
                    f"/api/story-workspace/workflow-runs/{run_id}/dream-files"
                ),
                revision=current_revision + 1,
            )
            self._atomic_replace(
                run_directory,
                "run.json",
                self._serialize(next_file),
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
        candidate = StoryWorkspaceDreamStageFile(
            workflow_run_id=run_id,
            stage=canonical_stage,
            revision=expected_revision + 1,
            source_files=source_files,
            page=_stage_page(canonical_stage, run_id),
            items=items,
        )

        with self._locked_run(run_id, create=False) as run_directory:
            run_file = self._read_model(
                run_directory,
                "run.json",
                StoryWorkspaceDreamRunFile,
                required=True,
            )
            assert run_file is not None
            self._validate_run_authority(
                run_file,
                run_id=run_id,
                source=source,
                thread_id=thread_id,
            )
            # Authorization must precede resolve/stat of caller-provided paths;
            # otherwise a cross-thread caller could use validation errors as a
            # workspace path-existence oracle.
            self._validate_source_files(candidate)
            stages_directory = self._stages_directory(run_directory, create=True)
            current = self._read_model(
                stages_directory,
                canonical_filename,
                StoryWorkspaceDreamStageFile,
                required=False,
            )
            if current is not None:
                self._validate_stage_identity(current, run_id, canonical_stage)
                self._validate_source_files(current)
            current_revision = current.revision if current is not None else 0
            if expected_revision != current_revision:
                raise StoryWorkspaceDreamFileConflict(
                    expected_revision,
                    current_revision,
                )
            if candidate.revision != current_revision + 1:
                candidate = candidate.model_copy(
                    update={"revision": current_revision + 1}
                )
            self._atomic_replace(
                stages_directory,
                canonical_filename,
                self._serialize(candidate),
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
            raise StoryWorkspaceDreamFileError(
                "Dream file contains non-JSON values"
            ) from exc
        if len(payload) > STORY_WORKSPACE_DREAM_FILE_MAX_BYTES:
            raise StoryWorkspaceDreamFileError(
                "serialized Dream file exceeds size limit"
            )
        return payload

    @staticmethod
    def _validate_run_authority(
        run_file: StoryWorkspaceDreamRunFile,
        *,
        run_id: str,
        source: StoryWorkspaceDreamSource,
        thread_id: str | None,
    ) -> None:
        if run_file.workflow_run_id != run_id:
            raise StoryWorkspaceDreamFileError("run.json workflow run mismatch")
        if run_file.source != source:
            raise StoryWorkspaceDreamFileError(
                "run.json source does not match authoritative WorkflowRun"
            )
        if thread_id is not None and run_file.thread_id != thread_id:
            raise StoryWorkspaceDreamFileError(
                "run.json thread does not match authoritative context"
            )

    @staticmethod
    def _validate_stage_identity(
        stage_file: StoryWorkspaceDreamStageFile,
        run_id: str,
        stage: StoryWorkspaceDreamStage,
    ) -> None:
        if stage_file.workflow_run_id != run_id or stage_file.stage is not stage:
            raise StoryWorkspaceDreamFileError(
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
        with self._locked_run(run_id, create=False) as run_directory:
            run_file = self._read_model(
                run_directory,
                "run.json",
                StoryWorkspaceDreamRunFile,
                required=True,
            )
            assert run_file is not None
            StoryWorkspaceDreamFileWriter._validate_run_authority(
                run_file,
                run_id=run_id,
                source=source,
                thread_id=thread_id,
            )
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
        with self._locked_run(run_id, create=False) as run_directory:
            self._read_and_validate_run(
                run_directory,
                run_id,
                source,
                thread_id=thread_id,
            )
            try:
                stages = self._stages_directory(run_directory, create=False)
            except StoryWorkspaceDreamPathError:
                if not (run_directory / "stages").exists():
                    return None
                raise
            stage_file = self._read_model(
                stages,
                _STAGE_FILENAMES[canonical_stage],
                StoryWorkspaceDreamStageFile,
                required=False,
            )
            if stage_file is None:
                return None
            self._validate_stage(stage_file, run_id, canonical_stage)
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
            raise StoryWorkspaceDreamPathError("filename is not a canonical stage file")
        return self.read_stage(workflow_run, stage=matches[0])

    def read(
        self,
        workflow_run: WorkflowRun,
        *,
        thread_id: str,
    ) -> StoryWorkspaceDreamFilesResponse:
        _validate_authoritative_thread(workflow_run, thread_id)
        run_id, source = _authoritative_context(workflow_run)
        if self._optional_run_directory(run_id) is None:
            return self._waiting_response(run_id, thread_id, source)
        with self._locked_run(run_id, create=False) as run_directory:
            run_file = self._read_model(
                run_directory,
                "run.json",
                StoryWorkspaceDreamRunFile,
                required=False,
            )
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
            stages_path = run_directory / "stages"
            if stages_path.exists() or stages_path.is_symlink():
                stages = self._stages_directory(run_directory, create=False)
                for stage in STORY_WORKSPACE_DREAM_REQUIRED_STAGES:
                    stage_file = self._read_model(
                        stages,
                        _STAGE_FILENAMES[stage],
                        StoryWorkspaceDreamStageFile,
                        required=False,
                    )
                    if stage_file is None:
                        continue
                    self._validate_stage(stage_file, run_id, stage)
                    stage_responses[stage] = StoryWorkspaceDreamStageResponse(
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
            complete = set(stage_responses) == set(
                STORY_WORKSPACE_DREAM_REQUIRED_STAGES
            )
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

    @staticmethod
    def _waiting_response(
        run_id: str,
        thread_id: str,
        source: StoryWorkspaceDreamSource,
    ) -> StoryWorkspaceDreamFilesResponse:
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

    def _read_and_validate_run(
        self,
        run_directory: Path,
        run_id: str,
        source: StoryWorkspaceDreamSource,
        *,
        thread_id: str | None,
    ) -> StoryWorkspaceDreamRunFile:
        run_file = self._read_model(
            run_directory,
            "run.json",
            StoryWorkspaceDreamRunFile,
            required=True,
        )
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
    ) -> None:
        StoryWorkspaceDreamFileWriter._validate_stage_identity(
            stage_file,
            run_id,
            stage,
        )
        self._validate_source_files(stage_file)


__all__ = [
    "StoryWorkspaceDreamFileConflict",
    "StoryWorkspaceDreamFileError",
    "StoryWorkspaceDreamFileReader",
    "StoryWorkspaceDreamFileWriter",
    "StoryWorkspaceDreamPathError",
]
