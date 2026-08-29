# [Input] Server-installed notion-session/notion-cli Skill packages, real Read-hook/workspace-materializer descriptors, and the current actor's optional Notion connector projection.
# [Output] Bounded, credential-free multi-Skill and system-operation catalog plus safe Markdown/file projections for Settings.
# [Pos] Read-only Notion capability metadata node in backend/notion; it never executes MCP, CLI, Read, or connector writes.
# [Sync] 2026-08-29: add the server-owned notion-session catalog, parsed SKILL.md body, stable file IDs, package revision, and fail-closed file reads.
# [Sync] 2026-08-29: derive the Skill title/files from its installed package and operations from the real Read hook/workspace materializer descriptors.
# [Sync] 2026-08-30: expose notion-session and notion-cli from their installed packages with per-package revisions while keeping CLI credential execution unavailable.

"""Read-only product metadata for the installed Notion Skill package."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

import yaml

from libs.claude_agent_kit.server.notion_read_hook import NOTION_READ_HOOK_OPERATION

from .sync import NOTION_WORKSPACE_MATERIALIZE_OPERATION


NOTION_SESSION_SKILL_ID = "notion-session"
NOTION_CLI_SKILL_ID = "notion-cli"
NOTION_SKILL_IDS = (NOTION_SESSION_SKILL_ID, NOTION_CLI_SKILL_ID)
# Backward-compatible name for callers that mean the index-first default Skill.
NOTION_SKILL_ID = NOTION_SESSION_SKILL_ID
_SKILL_TOOL_BOUNDARIES: Mapping[str, list[str]] = {
    NOTION_SESSION_SKILL_ID: ["Read"],
    NOTION_CLI_SKILL_ID: ["Bash"],
}
_BUILTIN_SKILLS_ROOT = Path(__file__).resolve().parents[1] / "builtin_skills"
_MAX_MARKDOWN_BYTES = 256 * 1024
_FRONTMATTER_PATTERN = re.compile(
    r"\A---[ \t]*\r?\n(?P<frontmatter>.*?)\r?\n---[ \t]*(?:\r?\n|\Z)(?P<body>.*)\Z",
    re.DOTALL,
)
_MARKDOWN_TITLE_PATTERN = re.compile(r"^#\s+(?P<title>.+?)\s*$", re.MULTILINE)
_PUBLIC_FILE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


class NotionCapabilityError(RuntimeError):
    """Base class for safe capability-package failures."""


class NotionCapabilityNotFoundError(NotionCapabilityError):
    """Requested Skill or public file ID is not part of the installed package."""


class NotionCapabilityRevisionError(NotionCapabilityError):
    """The caller's package revision is stale."""


class NotionCapabilityUnavailableError(NotionCapabilityError):
    """The installed package cannot be projected safely."""


@dataclass(frozen=True)
class _PublicSkillFile:
    id: str
    relative_path: str
    media_type: str = "text/markdown"


_SYSTEM_OPERATIONS: tuple[Mapping[str, str], ...] = (
    NOTION_READ_HOOK_OPERATION,
    NOTION_WORKSPACE_MATERIALIZE_OPERATION,
)


def _require_skill_id(skill_id: str) -> str:
    if skill_id not in NOTION_SKILL_IDS:
        raise NotionCapabilityNotFoundError("Notion Skill was not found.")
    return skill_id


def _skill_root(skill_id: str, skills_root: Path | None = None) -> Path:
    return (skills_root or _BUILTIN_SKILLS_ROOT) / _require_skill_id(skill_id)


def _safe_markdown_path(root: Path, relative_path: str) -> Path:
    root_resolved = root.resolve(strict=False)
    candidate = root / relative_path
    current = root
    for part in Path(relative_path).parts:
        current = current / part
        if current.is_symlink():
            raise NotionCapabilityUnavailableError("Notion Skill file is unavailable.")
    resolved = candidate.resolve(strict=False)
    if not resolved.is_relative_to(root_resolved) or not candidate.is_file():
        raise NotionCapabilityUnavailableError("Notion Skill file is unavailable.")
    if resolved.suffix.lower() != ".md":
        raise NotionCapabilityUnavailableError("Notion Skill file type is unavailable.")
    if resolved.stat().st_size > _MAX_MARKDOWN_BYTES:
        raise NotionCapabilityUnavailableError("Notion Skill file is too large to display.")
    return resolved


def _read_markdown(root: Path, relative_path: str) -> tuple[str, int]:
    path = _safe_markdown_path(root, relative_path)
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise NotionCapabilityUnavailableError("Notion Skill file is unavailable.") from exc
    return content, path.stat().st_size


def _public_skill_files(
    skill_id: str,
    skills_root: Path | None = None,
) -> tuple[_PublicSkillFile, ...]:
    root = _skill_root(skill_id, skills_root)
    references = root / "references"
    try:
        if references.is_symlink() or not references.is_dir():
            raise NotionCapabilityUnavailableError("Notion Skill files are unavailable.")
        candidates = sorted(references.iterdir(), key=lambda item: item.name)
    except OSError as exc:
        raise NotionCapabilityUnavailableError("Notion Skill files are unavailable.") from exc

    public_files: list[_PublicSkillFile] = []
    seen_ids: set[str] = set()
    for candidate in candidates:
        if candidate.suffix.lower() != ".md":
            continue
        file_id = candidate.stem
        if not _PUBLIC_FILE_ID_PATTERN.fullmatch(file_id) or file_id in seen_ids:
            raise NotionCapabilityUnavailableError("Notion Skill file metadata is unavailable.")
        relative_path = candidate.relative_to(root).as_posix()
        _safe_markdown_path(root, relative_path)
        public_files.append(_PublicSkillFile(file_id, relative_path))
        seen_ids.add(file_id)
    return tuple(public_files)


def _skill_document(
    skill_id: str,
    skills_root: Path | None = None,
) -> tuple[dict[str, Any], str]:
    content, _size = _read_markdown(_skill_root(skill_id, skills_root), "SKILL.md")
    match = _FRONTMATTER_PATTERN.match(content)
    if match is None:
        raise NotionCapabilityUnavailableError("Notion Skill metadata is unavailable.")
    try:
        metadata = yaml.safe_load(match.group("frontmatter"))
    except yaml.YAMLError as exc:
        raise NotionCapabilityUnavailableError("Notion Skill metadata is unavailable.") from exc
    if not isinstance(metadata, dict) or metadata.get("name") != skill_id:
        raise NotionCapabilityUnavailableError("Notion Skill metadata is unavailable.")
    description = metadata.get("description")
    tools = metadata.get("tools")
    if not isinstance(description, str) or not description.strip():
        raise NotionCapabilityUnavailableError("Notion Skill metadata is unavailable.")
    expected_tools = _SKILL_TOOL_BOUNDARIES[skill_id]
    if tools != expected_tools:
        raise NotionCapabilityUnavailableError("Notion Skill tool boundary is unavailable.")
    body = match.group("body").strip()
    title_match = _MARKDOWN_TITLE_PATTERN.search(body)
    if title_match is None or not title_match.group("title").strip():
        raise NotionCapabilityUnavailableError("Notion Skill title is unavailable.")
    return {
        "name": skill_id,
        "title": title_match.group("title").strip(),
        "description": description.strip(),
        "tools": list(expected_tools),
    }, body


def _file_descriptors(
    skill_id: str,
    skills_root: Path | None = None,
) -> list[dict[str, Any]]:
    root = _skill_root(skill_id, skills_root)
    descriptors: list[dict[str, Any]] = []
    for public_file in _public_skill_files(skill_id, skills_root):
        _content, size_bytes = _read_markdown(root, public_file.relative_path)
        descriptors.append(
            {
                "id": public_file.id,
                "relative_path": public_file.relative_path,
                "media_type": public_file.media_type,
                "size_bytes": size_bytes,
            }
        )
    return descriptors


def _package_revision(skill_id: str, skills_root: Path | None = None) -> str:
    root = _skill_root(skill_id, skills_root)
    digest = sha256()
    for relative_path in (
        "SKILL.md",
        *[item.relative_path for item in _public_skill_files(skill_id, skills_root)],
    ):
        content, _size = _read_markdown(root, relative_path)
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(content.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def _catalog_revision(skills_root: Path | None = None) -> str:
    digest = sha256()
    for skill_id in NOTION_SKILL_IDS:
        digest.update(skill_id.encode("utf-8"))
        digest.update(b"\0")
        digest.update(_package_revision(skill_id, skills_root).encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def _connector_state(connector: Mapping[str, Any] | None) -> dict[str, Any]:
    if connector is None:
        return {
            "connected": False,
            "has_index": False,
            "has_database": False,
        }
    sources_value = connector.get("sources")
    sources: Sequence[Any] = sources_value if isinstance(sources_value, list) else ()
    connected = str(connector.get("auth_status") or "").lower() == "authenticated"
    has_index = connected and bool(connector.get("last_synced_at")) and bool(sources)
    has_database = has_index and any(
        isinstance(source, Mapping)
        and str(source.get("resource_type") or source.get("type") or "")
        in {"notion_database", "database"}
        for source in sources
    )
    return {
        "connected": connected,
        "has_index": has_index,
        "has_database": has_database,
    }


def _availability(requirement: str, state: Mapping[str, Any]) -> str:
    if not state["connected"]:
        return "requires_connection"
    if requirement == "connection":
        return "available"
    if requirement == "database" and not state["has_database"]:
        return "requires_scope"
    if requirement == "index" and not state["has_index"]:
        return "requires_scope"
    return "available"


def _skill_availability(skill_id: str, state: Mapping[str, Any]) -> str:
    if not state["connected"]:
        return "requires_connection"
    if skill_id == NOTION_CLI_SKILL_ID:
        # The package is synchronized for discovery and inspection, but Dream
        # intentionally does not merge actor-owned NOTION_HOME into Bash.
        return "unavailable"
    return "available"


def build_notion_capability_catalog(
    connector: Mapping[str, Any] | None,
    *,
    skills_root: Path | None = None,
) -> dict[str, Any]:
    """Project current product capabilities without executing any provider tool."""

    skill_metadata = {
        skill_id: _skill_document(skill_id, skills_root)[0]
        for skill_id in NOTION_SKILL_IDS
    }
    state = _connector_state(connector)
    return {
        "schema_version": 3,
        "package_revision": _catalog_revision(skills_root),
        "mcp_inventory": {
            "status": "not_integrated",
            "revision": None,
            "read_status": "not_integrated",
            "write_status": "not_integrated",
        },
        "skills": [
            {
                "id": skill_id,
                "title": skill_metadata[skill_id]["title"],
                "description": skill_metadata[skill_id]["description"],
                "source": "builtin",
                "availability": _skill_availability(skill_id, state),
            }
            for skill_id in NOTION_SKILL_IDS
        ],
        "operations": [
            {
                "id": operation["id"],
                "title": operation["title"],
                "description": operation["description"],
                "kind": operation["kind"],
                "source": operation["source"],
                "entrypoint": operation["entrypoint"],
                "availability": _availability(operation["requirement"], state),
            }
            for operation in _SYSTEM_OPERATIONS
        ],
    }


def get_notion_skill_detail(
    skill_id: str,
    connector: Mapping[str, Any] | None,
    *,
    skills_root: Path | None = None,
) -> dict[str, Any]:
    _require_skill_id(skill_id)
    metadata, body = _skill_document(skill_id, skills_root)
    state = _connector_state(connector)
    return {
        "package_revision": _package_revision(skill_id, skills_root),
        "skill": {
            "id": skill_id,
            "title": metadata["title"],
            "description": metadata["description"],
            "source": "builtin",
            "availability": _skill_availability(skill_id, state),
            "tools": metadata["tools"],
            "body": body,
        },
        "files": _file_descriptors(skill_id, skills_root),
    }


def get_notion_skill_file(
    skill_id: str,
    file_id: str,
    *,
    expected_revision: str | None = None,
    skills_root: Path | None = None,
) -> dict[str, Any]:
    _require_skill_id(skill_id)
    public_file = next(
        (
            item
            for item in _public_skill_files(skill_id, skills_root)
            if item.id == file_id
        ),
        None,
    )
    if public_file is None:
        raise NotionCapabilityNotFoundError("Notion Skill file was not found.")
    revision = _package_revision(skill_id, skills_root)
    if expected_revision is not None and expected_revision != revision:
        raise NotionCapabilityRevisionError("Notion Skill package changed. Reload and retry.")
    content, size_bytes = _read_markdown(
        _skill_root(skill_id, skills_root),
        public_file.relative_path,
    )
    return {
        "package_revision": revision,
        "file": {
            "id": public_file.id,
            "relative_path": public_file.relative_path,
            "media_type": public_file.media_type,
            "size_bytes": size_bytes,
            "content": content,
        },
    }
