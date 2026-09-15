# [Input] One immutable Reflections worker-load snapshot and server-owned Agent workspace configuration.
# [Output] Snapshot-only Session provider plus canonical, symlink-rejecting Reflections workspace writes.
# [Pos] Reflections Runtime composition helper; no Admin/RTA credential, SQL or MCP behavior.
# [Sync] 2026-09-15: bind every Reflections workspace to the configured Agent thread root with 0700 ownership.
"""Server-owned helpers for composing a Reflections child Agent turn."""

from __future__ import annotations

from datetime import date
import os
from pathlib import Path

from .errors import AdminDataError
from .reflection_task_models import (
    ReflectionLaunchSnapshotDTO,
    ReflectionTaskId,
)
from .session_models import (
    SessionListInputDTO,
    SessionListResultDTO,
    SessionPreviewDTO,
)


def reflection_workspace_root() -> Path:
    """Return the one configured Agent/Reflections thread workspace root."""

    agent_raw = os.environ.get("AGENT_CWD", "").strip()
    if not agent_raw or not Path(agent_raw).is_absolute():
        raise AdminDataError("ADMIN_CONFIGURATION_INVALID", 503)
    agent_path = Path(agent_raw)
    if agent_path.is_symlink():
        raise AdminDataError("REFLECTION_WORKSPACE_SYMLINK_FORBIDDEN", 409)
    root = agent_path.resolve()
    reflection_raw = os.environ.get("DREAM_REFLECTIONS_WORKSPACE_ROOT", "").strip()
    if reflection_raw:
        candidate = Path(reflection_raw)
        if (not candidate.is_absolute() or candidate.is_symlink()
                or candidate.resolve() != root):
            raise AdminDataError("ADMIN_CONFIGURATION_INVALID", 503)
    return root


class ReflectionSnapshotSessionProjectionProvider:
    """Serve only Sessions frozen into one Admin worker-load snapshot."""

    def __init__(self, snapshot: ReflectionLaunchSnapshotDTO) -> None:
        if type(snapshot) is not ReflectionLaunchSnapshotDTO:
            raise AdminDataError("ADMIN_OPERATION_INPUT_INVALID", 400)
        self._snapshot = snapshot

    @staticmethod
    def _session_date(created_at: str | None, updated_at: str | None) -> date | None:
        raw = created_at or updated_at
        return date.fromisoformat(raw[:10]) if raw else None

    def list_sessions(
        self, input_dto: SessionListInputDTO, request_id: str
    ) -> SessionListResultDTO:
        if type(input_dto) is not SessionListInputDTO:
            raise AdminDataError(
                "ADMIN_OPERATION_INPUT_INVALID", 400, request_id
            )
        start = date.fromisoformat(input_dto.start_date) if input_dto.start_date else None
        end = date.fromisoformat(input_dto.end_date) if input_dto.end_date else None
        sessions: list[SessionPreviewDTO] = []
        for item in self._snapshot.sessions:
            item_date = self._session_date(item.created_at, item.updated_at)
            if start is not None and (item_date is None or item_date < start):
                continue
            if end is not None and (item_date is None or item_date > end):
                continue
            sessions.append(
                SessionPreviewDTO(
                    id=item.id,
                    name=item.name,
                    labels=list(item.labels),
                    created_at=item.created_at,
                    updated_at=item.updated_at,
                    first_line=item.first_line,
                    text=item.text if input_dto.include_text else None,
                )
            )
        return SessionListResultDTO(sessions=sessions)


def canonical_reflection_workspace(
    *, task_id: ReflectionTaskId, advertised_path: str, workspace_root: str
) -> Path:
    """Validate Admin's task workspace locator against Dream's configured root."""

    configured_root = Path(workspace_root)
    if not configured_root.is_absolute():
        raise AdminDataError("ADMIN_CONFIGURATION_INVALID", 503)
    root = configured_root.resolve()
    expected = root / task_id / "memory"
    advertised = Path(advertised_path)
    normalized_advertised = Path(os.path.abspath(advertised))
    if not advertised.is_absolute() or normalized_advertised != expected:
        raise AdminDataError("REFLECTION_WORKSPACE_BINDING_CONFLICT", 409)
    try:
        expected.relative_to(root)
    except ValueError:
        raise AdminDataError("ADMIN_CONFIGURATION_INVALID", 503) from None
    return expected


def reject_reflection_workspace_symlinks(
    workspace_path: Path, *, workspace_root: str
) -> None:
    """Reject existing symlinks below the normalized configured workspace root."""

    configured_root = Path(workspace_root)
    if not configured_root.is_absolute():
        raise AdminDataError("ADMIN_CONFIGURATION_INVALID", 503)
    root = configured_root.resolve()
    try:
        relative = workspace_path.relative_to(root)
    except ValueError:
        raise AdminDataError("REFLECTION_WORKSPACE_BINDING_CONFLICT", 409) from None
    current = root
    for component in relative.parts:
        current = current / component
        if current.is_symlink():
            raise AdminDataError("REFLECTION_WORKSPACE_SYMLINK_FORBIDDEN", 409)


def prepare_reflection_memory_workspace(*, identifier: str,
    advertised_path: str) -> Path:
    """Validate and create one exact ``{AGENT_CWD}/{id}/memory`` directory."""

    root = reflection_workspace_root()
    memory = canonical_reflection_workspace(
        task_id=identifier,
        advertised_path=advertised_path,
        workspace_root=str(root),
    )
    reject_reflection_workspace_symlinks(memory, workspace_root=str(root))
    memory.mkdir(parents=True, exist_ok=True)
    memory.parent.chmod(0o700)
    reject_reflection_workspace_symlinks(memory, workspace_root=str(root))
    if not memory.is_dir() or memory.parent.parent != root:
        raise AdminDataError("REFLECTION_WORKSPACE_BINDING_CONFLICT", 409)
    return memory


def prepare_reflection_workspace_directory(directory: Path) -> Path:
    """Create a directory below ``AGENT_CWD`` without following existing links."""

    root = reflection_workspace_root()
    reject_reflection_workspace_symlinks(directory, workspace_root=str(root))
    directory.mkdir(parents=True, exist_ok=True)
    reject_reflection_workspace_symlinks(directory, workspace_root=str(root))
    if not directory.is_dir():
        raise AdminDataError("REFLECTION_WORKSPACE_BINDING_CONFLICT", 409)
    return directory


def validate_reflection_workspace_path(path: Path) -> None:
    """Validate an existing or prospective path below the configured root."""

    root = reflection_workspace_root()
    reject_reflection_workspace_symlinks(path, workspace_root=str(root))


def write_reflection_workspace_text(path: Path, content: str) -> None:
    """Write one UTF-8 file below ``AGENT_CWD`` after checking every component."""

    root = reflection_workspace_root()
    reject_reflection_workspace_symlinks(path, workspace_root=str(root))
    if not path.parent.is_dir():
        raise AdminDataError("REFLECTION_WORKSPACE_BINDING_CONFLICT", 409)
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o666)
    except OSError as exc:
        raise AdminDataError("REFLECTION_WORKSPACE_WRITE_FAILED", 500) from exc
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content)
    except OSError as exc:
        raise AdminDataError("REFLECTION_WORKSPACE_WRITE_FAILED", 500) from exc
    reject_reflection_workspace_symlinks(path, workspace_root=str(root))


__all__ = [
    "ReflectionSnapshotSessionProjectionProvider",
    "canonical_reflection_workspace",
    "prepare_reflection_memory_workspace",
    "prepare_reflection_workspace_directory",
    "reflection_workspace_root",
    "reject_reflection_workspace_symlinks",
    "validate_reflection_workspace_path",
    "write_reflection_workspace_text",
]
