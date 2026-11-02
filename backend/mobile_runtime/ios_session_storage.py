# [Input] The current Runtime cwd, thread-owned projects directory and original Session UUID.
# [Output] Exclusive directory relocation after an iOS application-container UUID change.
# [Pos] iOS filesystem compatibility; transcript bytes, Session identity and business records remain unchanged.
# [Sync] 2026-10-25: validate intermediate container UUIDs from exact Runtime project names after repeated app updates.
# [Sync] 2026-10-26: open owned directories from the application data root without listing protected system ancestors.
from __future__ import annotations

import ctypes
import json
import os
from pathlib import Path
import re
import stat
import sys
import unicodedata
from uuid import UUID


def _same_container_location(previous: str, current: str) -> bool:
    old, new = Path(previous).parts, Path(current).parts
    if (not Path(previous).is_absolute() or os.path.normpath(previous) != previous
            or len(old) != len(new)):
        return False
    differences = [index for index, pair in enumerate(zip(old, new)) if pair[0] != pair[1]]
    if len(differences) != 1:
        return False
    index = differences[0]
    if index < 3 or old[index - 3:index] not in {
        ("Containers", "Data", "Application"), ("Containers", "Bundle", "Application"),
    }:
        return False
    try:
        return UUID(old[index]) != UUID(new[index])
    except ValueError:
        return False


def _open_directory(path: Path) -> int:
    root = Path.home().resolve(strict=True)
    if (not path.is_absolute() or os.path.normpath(path) != str(path)
            or not path.is_relative_to(root)):
        raise ValueError("IOS_SESSION_LOCATION_OUTSIDE_APPLICATION")
    descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for component in path.relative_to(root).parts:
            following = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = following
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _record_cwd(directory: int, session_id: str) -> str | None:
    try:
        descriptor = os.open(session_id + ".jsonl", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    except FileNotFoundError:
        return None
    with os.fdopen(descriptor, encoding="utf-8") as transcript:
        if not stat.S_ISREG(os.fstat(transcript.fileno()).st_mode):
            raise ValueError("IOS_SESSION_RECORD_INVALID")
        for line in transcript:
            if not line.strip():
                continue
            record = json.loads(line)
            if not isinstance(record, dict):
                raise ValueError("IOS_SESSION_RECORD_INVALID")
            if (record.get("type") in {"user", "assistant"} and not record.get("isSidechain")
                    and record.get("uuid") and isinstance(record.get("message"), dict)):
                if record.get("sessionId") != session_id:
                    raise ValueError("IOS_SESSION_RECORD_ID_MISMATCH")
                value = record.get("cwd")
                return unicodedata.normalize("NFC", value) if isinstance(value, str) else None
    return None


def _rename_no_replace(parent: int, source: str, destination: str) -> None:
    # iPhoneOS SDK sys/stdio.h: renameatx_np is public since iOS 10.0;
    # RENAME_EXCL (0x4) refuses an existing destination atomically.
    rename = ctypes.CDLL(None, use_errno=True).renameatx_np
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    if rename(parent, os.fsencode(source), parent, os.fsencode(destination), 0x4) != 0:
        number = ctypes.get_errno()
        raise OSError(number, "IOS_SESSION_DIRECTORY_RELOCATION_FAILED")


def _project_matches_container_record(name: str, previous: str, current: str) -> bool:
    if not _same_container_location(previous, current):
        return False
    from libs.claude_agent_kit.server.session_files import _runtime_project_name
    if name == _runtime_project_name(previous):
        return True
    old, new = Path(previous).parts, Path(current).parts
    index = next(index for index, pair in enumerate(zip(old, new)) if pair[0] != pair[1])
    # A prior exclusive rename keeps JSONL bytes unchanged. Recover its container
    # UUID from the existing project name, then verify the entire Runtime name,
    # including its long-path suffix, against the original record's other parts.
    for match in re.finditer(r"[A-Fa-f0-9]{8}-(?:[A-Fa-f0-9]{4}-){3}[A-Fa-f0-9]{12}", name):
        candidate = str(Path(*old[:index], match.group(), *old[index + 1:]))
        if (_same_container_location(candidate, current)
                and name == _runtime_project_name(candidate)):
            return True
    return False


def relocate_current_runtime_project(projects_root: str, cwd: str, session_id: str) -> bool:
    """Relocate one verified project inside the caller's original config home.

    Only the UUID of the same iOS Data/Bundle application container may differ.
    No transcript rewrite, project merge, foreign cwd or Session fallback occurs.
    The original strict resume probe runs again against the resulting directory.
    """
    if sys.platform != "ios":
        return False
    if (str(UUID(session_id)) != session_id.lower() or not Path(projects_root).is_absolute()
            or os.path.normpath(projects_root) != projects_root):
        raise ValueError("IOS_SESSION_LOCATION_INVALID")
    from libs.claude_agent_kit.server.session_files import _runtime_project_name
    destination = _runtime_project_name(cwd)
    try:
        parent = _open_directory(Path(projects_root))
    except FileNotFoundError:
        return False
    try:
        try:
            os.stat(destination, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            return False
        candidate = None
        for name in os.listdir(parent):
            info = os.stat(name, dir_fd=parent, follow_symlinks=False)
            if not stat.S_ISDIR(info.st_mode):
                continue
            directory = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            try:
                previous = _record_cwd(directory, session_id)
                if previous is None or not _project_matches_container_record(name, previous, cwd):
                    continue
                if candidate is not None:
                    raise ValueError("IOS_SESSION_PROJECT_AMBIGUOUS")
                candidate = (name, os.fstat(directory))
            finally:
                os.close(directory)
        if candidate is None:
            return False
        name, identity = candidate
        current = os.stat(name, dir_fd=parent, follow_symlinks=False)
        if (current.st_dev, current.st_ino) != (identity.st_dev, identity.st_ino):
            raise ValueError("IOS_SESSION_PROJECT_CHANGED")
        _rename_no_replace(parent, name, destination)
        return True
    finally:
        os.close(parent)
