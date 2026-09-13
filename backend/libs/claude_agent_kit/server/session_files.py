# [Input] Consume CLAUDE_CONFIG_DIR / HOME process env and optional workspace cwd.
# [Output] Provide locate_session_file, read_session_messages,
#          parse_session_messages_from_jsonl to simple_cas_client.
# [Pos] utility node in libs/claude_agent_kit/server
# [Sync] 2026-05-01: initial Python port from server/utils/session-files.ts
# [Sync] 2026-09-13: separate strict current-project resume probes from history search.
# [Sync] 2026-08-03: get_projects_root honors CLAUDE_CONFIG_DIR and accepts an
#                    optional workspace cwd — apply_claude_config_home_to_options
#                    (sdk_env) points the SDK subprocess's config home at
#                    {cwd}/.claude-home, so transcripts land under
#                    {cwd}/.claude-home/projects/, not ~/.claude/projects.

"""Session file utilities.

Python translation of TypeScript:
  server/utils/session-files.ts

Session files are JSONL files stored at:
  {CLAUDE_CONFIG_DIR or ~/.claude or {cwd}/.claude-home}/projects/<project-dir>/<session-id>.jsonl
"""
from __future__ import annotations

import json
import os
import stat
import unicodedata
from pathlib import Path
from typing import Any, Optional, Union
from uuid import UUID

from .sdk_env import resolve_claude_config_home

SESSION_FILE_EXTENSION = ".jsonl"

# Runtime 0.1.9 src/utils/sessionStoragePortable.ts::sanitizePath. This is a
# storage-format boundary, not a business path-length limit.
_RUNTIME_PROJECT_NAME_LIMIT = 200


def _runtime_long_project_hash(value: str) -> str:
    """Bun.hash(canonical cwd).toString(36), only for long project paths.

    Runtime's sanitizePath uses seed-zero Wyhash, not the SDK's simpleHash.
    Source: ziglang/zig 0.14.1 lib/std/hash/wyhash.zig (Wyhash.hash/final2),
    based on the public-domain wangyi-fudan/wyhash algorithm. Kept local to
    this storage-format adapter; native Runtime regression verifies parity.
    """
    data = value.encode("utf-8")
    secret = (0xA0761D6478BD642F, 0xE7037ED1A0B428DB,
              0x8EBC6AF09C88C6E3, 0x589965CC75374CC3)
    mask = (1 << 64) - 1

    def mix(a: int, b: int) -> int:
        product = a * b
        return (product & mask) ^ (product >> 64)

    def read(offset: int) -> int:
        return int.from_bytes(data[offset:offset + 8], "little")

    state = [mix(secret[0], secret[1])] * 3
    offset = 0
    while offset + 48 < len(data):
        for index in range(3):
            start = offset + 16 * index
            state[index] = mix(read(start) ^ secret[index + 1], read(start + 8) ^ state[index])
        offset += 48
    seed = state[0] ^ state[1] ^ state[2]
    while offset + 16 < len(data):
        seed = mix(read(offset) ^ secret[1], read(offset + 8) ^ seed)
        offset += 16
    product = (read(len(data) - 16) ^ secret[1]) * (read(len(data) - 8) ^ seed)
    hashed = mix((product & mask) ^ secret[0] ^ len(data), (product >> 64) ^ secret[1])
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    encoded = ""
    while hashed:
        hashed, digit = divmod(hashed, 36)
        encoded = digits[digit] + encoded
    return encoded or "0"


class ClaudeResumeStorageError(RuntimeError):
    """Safe diagnostic: storage errors never authorize a fresh fallback."""


def locate_resumable_session(
    session_id: str,
    *,
    cwd: str,
    config_home: Optional[str] = None,
) -> Optional[str]:
    """Probe only the project read by Runtime's ID-based resume.

    Unlike history search, this must not accept a clean-room SHA256 directory
    or another cwd. Read metadata without exposing transcript contents. Missing
    paths/empty transcripts return None; corruption and access errors fail closed.
    """
    try:
        if str(UUID(session_id)) != session_id.lower():
            raise ValueError
    except (ValueError, AttributeError, TypeError):
        raise ClaudeResumeStorageError("CLAUDE_RESUME_INVALID_SESSION_ID") from None

    try:
        runtime_cwd = unicodedata.normalize("NFC", str(Path(cwd).resolve(strict=True)))
    except (OSError, ValueError):
        raise ClaudeResumeStorageError("CLAUDE_RESUME_INVALID_CWD") from None
    try:
        if not Path(runtime_cwd).is_dir():
            raise ClaudeResumeStorageError("CLAUDE_RESUME_INVALID_CWD")
        # JS's non-Unicode regex replaces each UTF-16 code unit, not each
        # Python Unicode codepoint (astral characters therefore yield '--').
        units = runtime_cwd.encode("utf-16-le")
        project_name = "".join(
            chr(unit) if (48 <= unit <= 57 or 65 <= unit <= 90 or 97 <= unit <= 122) else "-"
            for unit in (int.from_bytes(units[i:i + 2], "little") for i in range(0, len(units), 2))
        )
        if len(project_name) > _RUNTIME_PROJECT_NAME_LIMIT:
            project_name = f"{project_name[:_RUNTIME_PROJECT_NAME_LIMIT]}-{_runtime_long_project_hash(runtime_cwd)}"
        projects_root = (
            str(Path(config_home) / "projects")
            if config_home else get_projects_root(None)
        )
        if not projects_root or not Path(projects_root).is_absolute():
            raise ClaudeResumeStorageError("CLAUDE_RESUME_INVALID_CONFIG_HOME")
        if os.path.normpath(projects_root) != projects_root:
            raise ClaudeResumeStorageError("CLAUDE_RESUME_INVALID_CONFIG_HOME")
        target = Path(projects_root) / project_name / f"{session_id}.jsonl"
        # Walk with directory descriptors: O_NOFOLLOW covers both links already
        # present and links swapped into the path between check and open.
        fd = os.open(target.anchor, os.O_RDONLY | os.O_DIRECTORY)
        try:
            for component in target.parts[1:-1]:
                next_fd = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = next_fd
            transcript_fd = os.open(target.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        finally:
            os.close(fd)
        with os.fdopen(transcript_fd, encoding="utf-8") as transcript:
            if not stat.S_ISREG(os.fstat(transcript.fileno()).st_mode):
                raise ClaudeResumeStorageError("CLAUDE_RESUME_INVALID_RECORD")
            for line in transcript:
                if not line.strip():
                    continue
                record = json.loads(line)
                if not isinstance(record, dict):
                    raise ClaudeResumeStorageError("CLAUDE_RESUME_INVALID_RECORD")
                if (
                    record.get("type") in {"user", "assistant"}
                    and not record.get("isSidechain")
                    and record.get("uuid")
                    and isinstance(record.get("message"), dict)
                ):
                    if record.get("sessionId") != session_id:
                        raise ClaudeResumeStorageError("CLAUDE_RESUME_RECORD_ID_MISMATCH")
                    return str(target)
        return None
    except FileNotFoundError:
        return None
    except ClaudeResumeStorageError:
        raise
    except (OSError, ValueError, UnicodeError):
        raise ClaudeResumeStorageError("CLAUDE_RESUME_STORAGE_UNAVAILABLE") from None


def get_projects_root(cwd: Optional[Union[str, Path]] = None) -> Optional[str]:
    """Return the Claude projects root directory.

    Maps to TypeScript ``getProjectsRoot``.

    Resolution order (delegates to ``sdk_env.resolve_claude_config_home``):
      1. ``CLAUDE_CONFIG_DIR`` process env → ``{CLAUDE_CONFIG_DIR}/projects``.
      2. *cwd* provided (Workspace Mode) → ``{cwd}/.claude-home/projects``,
         mirroring ``sdk_env.apply_claude_config_home_to_options`` which
         injects ``CLAUDE_CONFIG_DIR={cwd}/.claude-home`` into the SDK
         subprocess (claude-plan §5.1).  The backend process itself does not
         carry that env var, so callers that know the thread workspace must
         pass it in.
      3. Fallback ``~/.claude/projects``.
    """
    config_home = resolve_claude_config_home(cwd)
    if config_home:
        return str(Path(config_home) / "projects")
    home_dir = os.environ.get("HOME") or os.environ.get("USERPROFILE")
    if not home_dir:
        return None
    return str(Path(home_dir) / ".claude" / "projects")


def normalize_session_id(value: str) -> str:
    """Strip the ``.jsonl`` extension from a session ID if present.

    Maps to TypeScript ``normalizeSessionId``.
    """
    if value.lower().endswith(SESSION_FILE_EXTENSION):
        return value[: -len(SESSION_FILE_EXTENSION)]
    return value


async def locate_session_file(
    projects_root: str,
    session_id: str,
) -> Optional[str]:
    """Search for the JSONL session file across all project sub-directories.

    Maps to TypeScript ``locateSessionFile``.
    Returns the absolute path to the file, or ``None`` if not found.
    """
    candidate_dirs = await _collect_candidate_project_dirs(projects_root)
    for project_dir in candidate_dirs:
        session_path = str(Path(project_dir) / f"{session_id}{SESSION_FILE_EXTENSION}")
        if os.path.isfile(session_path):
            return session_path
    return None


async def read_session_messages(file_path: str) -> list[Any]:
    """Read and parse session messages from a JSONL file on disk.

    Maps to TypeScript ``readSessionMessages``.
    """
    try:
        with open(file_path, encoding="utf-8") as fh:
            file_content = fh.read()
    except FileNotFoundError:
        return []

    if not file_content:
        return []

    return parse_session_messages_from_jsonl(file_content)


def parse_session_messages_from_jsonl(file_content: str) -> list[Any]:
    """Parse session messages from raw JSONL text.

    Maps to TypeScript ``parseSessionMessagesFromJsonl``.
    """
    if not file_content:
        return []

    messages: list[Any] = []
    for raw_line in file_content.splitlines():
        trimmed = raw_line.strip()
        if not trimmed:
            continue
        try:
            parsed = json.loads(trimmed)
            message = _normalize_session_log_entry(parsed)
            if message is not None:
                messages.append(message)
        except json.JSONDecodeError:
            continue

    return messages


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _collect_candidate_project_dirs(projects_root: str) -> list[str]:
    """Enumerate sub-directories inside ``projects_root`` as candidates.

    Maps to TypeScript ``collectCandidateProjectDirs``.
    """
    root_path = Path(projects_root)
    if not root_path.is_dir():
        return []

    candidates: list[str] = []
    seen: set[str] = set()
    try:
        for entry in root_path.iterdir():
            if entry.is_dir():
                full_path = str(entry)
                if full_path not in seen:
                    candidates.append(full_path)
                    seen.add(full_path)
    except PermissionError:
        return []

    return candidates


def _normalize_session_log_entry(entry: Any) -> Optional[dict[str, Any]]:
    """Normalize a raw JSONL record into a canonical message dict.

    Maps to TypeScript ``normalizeSessionLogEntry``.
    Returns ``None`` for records that should be skipped (summaries, malformed).
    """
    if not entry or not isinstance(entry, dict):
        return None

    raw_type = entry.get("type")
    if not isinstance(raw_type, str):
        return None

    if raw_type.lower() == "summary":
        return None

    normalized: dict[str, Any] = {}
    for key, value in entry.items():
        # Rename camelCase key kept by some older session files
        if key == "sessionId":
            normalized["session_id"] = value
        else:
            normalized[key] = value

    if "message" not in normalized:
        return None

    message_value = normalized["message"]
    if not isinstance(message_value, (str, dict)):
        return None

    if _is_summary_message(message_value):
        return None

    normalized["type"] = raw_type
    return normalized


def _is_summary_message(value: Any) -> bool:
    """Return ``True`` if *value* looks like a summary message.

    Maps to TypeScript ``isSummaryMessage``.
    """
    if not value or not isinstance(value, dict):
        return False
    raw_type = value.get("type")
    return isinstance(raw_type, str) and raw_type.lower() == "summary"
