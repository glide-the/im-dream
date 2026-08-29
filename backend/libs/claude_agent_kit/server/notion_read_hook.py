# [Input] Runtime Read calls, thread-local Notion index, and thread-private credential projection.
# [Output] Redirect authorized `.notion/pages/<id>.json` reads to a private temporary live Markdown payload.
# [Pos] lazy Notion page-read hook in libs/claude_agent_kit/server.
# [Sync] 2026-08-28: establish index-only snapshot plus on-demand page body reads without exposing CLI/MCP credentials to the Agent.
# [Sync] 2026-08-29: export the Settings capability descriptor beside the real Read hook entrypoint so UI metadata cannot drift into a synthetic MCP inventory.

"""Lazy Notion page-content redirect for Claude Code's built-in Read tool."""
from __future__ import annotations

import json
import logging
import os
import re
import stat
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from notion.errors import (
    NotionAuthRequiredError,
    NotionCLIUnavailableError,
    NotionCredentialError,
    NotionOperationError,
    NotionPermissionError,
)
from notion.operations import NotionOperationClient

from .sdk_env import ensure_claude_code_tmpdir

logger = logging.getLogger(__name__)

_PAGE_ID_RE = re.compile(r"^[A-Za-z0-9-]{1,128}$")


def _safe_failure(exc: BaseException) -> dict[str, Any]:
    if isinstance(exc, (NotionAuthRequiredError, NotionCredentialError)):
        return {
            "ok": False,
            "code": "NOTION_AUTH_REQUIRED",
            "message": "Notion is not connected or its authorization expired.",
            "nextAction": "Reconnect Notion in Resource Links, then retry.",
        }
    if isinstance(exc, NotionPermissionError):
        return {
            "ok": False,
            "code": "NOTION_PERMISSION_DENIED",
            "message": "Notion denied access to this page.",
            "nextAction": "Grant this page to the Notion connection or reconnect Notion.",
        }
    if isinstance(exc, NotionCLIUnavailableError):
        return {
            "ok": False,
            "code": "NOTION_CAPABILITY_UNAVAILABLE",
            "message": "Notion page reading is temporarily unavailable.",
            "nextAction": "Retry later.",
        }
    if isinstance(exc, NotionOperationError):
        return {
            "ok": False,
            "code": "NOTION_REQUEST_FAILED",
            "message": "Notion could not read this page.",
            "nextAction": "Retry later; reconnect Notion if the problem continues.",
        }
    return {
        "ok": False,
        "code": "NOTION_REQUEST_FAILED",
        "message": "Notion could not read this page.",
        "nextAction": "Retry later.",
    }


def _page_target(raw_path: str, workspace: Path) -> tuple[Path, str] | None:
    candidate = Path(raw_path).expanduser()
    if not candidate.is_absolute():
        candidate = workspace / candidate
    try:
        pages_dir = workspace / ".notion" / "pages"
        pages_info = pages_dir.lstat()
        resolved_pages = pages_dir.resolve(strict=True)
        resolved_parent = candidate.parent.resolve(strict=True)
    except (FileNotFoundError, OSError, RuntimeError):
        return None
    if (
        stat.S_ISLNK(pages_info.st_mode)
        or not stat.S_ISDIR(pages_info.st_mode)
        or resolved_pages != workspace / ".notion" / "pages"
        or resolved_parent != resolved_pages
        or candidate.suffix != ".json"
        or not _PAGE_ID_RE.fullmatch(candidate.stem)
    ):
        return None
    return candidate, candidate.stem


def _load_index(workspace: Path) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    index_path = workspace / ".notion" / "index.json"
    snapshot_path = workspace / ".notion" / "snapshot.json"
    try:
        index_info = index_path.lstat()
        snapshot_info = snapshot_path.lstat()
        if (
            stat.S_ISLNK(index_info.st_mode)
            or stat.S_ISLNK(snapshot_info.st_mode)
            or not stat.S_ISREG(index_info.st_mode)
            or not stat.S_ISREG(snapshot_info.st_mode)
        ):
            raise NotionCredentialError("Notion thread index is unavailable.")
        index_raw = json.loads(index_path.read_text(encoding="utf-8"))
        snapshot_raw = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise NotionCredentialError("Notion thread index is unavailable.") from exc
    index_record = dict(index_raw) if isinstance(index_raw, Mapping) else {}
    snapshot = dict(snapshot_raw) if isinstance(snapshot_raw, Mapping) else {}
    pages: dict[str, dict[str, Any]] = {}
    for item in index_record.get("pages") or []:
        if not isinstance(item, Mapping):
            continue
        page_id = str(item.get("page_id") or "").strip()
        if _PAGE_ID_RE.fullmatch(page_id):
            pages[page_id] = dict(item)
    return pages, snapshot


def _validated_home(raw_home: str | None, workspace: Path) -> Path:
    if not raw_home:
        raise NotionCredentialError("Notion credential projection is unavailable.")
    supplied = Path(raw_home)
    try:
        home_info = supplied.lstat()
        home = supplied.resolve(strict=True)
        auth_path = home / "auth.json"
        auth_info = auth_path.lstat()
    except (FileNotFoundError, OSError, RuntimeError) as exc:
        raise NotionCredentialError("Notion credential projection is unavailable.") from exc
    if (
        not supplied.is_absolute()
        or supplied.is_symlink()
        or not stat.S_ISDIR(home_info.st_mode)
        or home.parent != workspace
        or home.name != ".notion-home"
        or home_info.st_mode & 0o777 != 0o700
        or stat.S_ISLNK(auth_info.st_mode)
        or not stat.S_ISREG(auth_info.st_mode)
        or auth_info.st_mode & 0o777 != 0o600
    ):
        raise NotionCredentialError("Notion credential projection is unavailable.")
    return home


def _write_redirect(
    payload: Mapping[str, Any],
    *,
    tmp_workspace: str | None,
    workspace: Path,
    tmp_paths: list[str],
) -> dict[str, Any]:
    tmp_root = Path(ensure_claude_code_tmpdir(tmp_workspace or workspace))
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".json",
        delete=False,
        prefix="notion-read-",
        dir=tmp_root,
        encoding="utf-8",
    ) as handle:
        json.dump(dict(payload), handle, ensure_ascii=False)
        tmp_path = handle.name
    os.chmod(tmp_path, 0o600, follow_symlinks=False)
    tmp_paths.append(tmp_path)
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "updatedInput": {"file_path": tmp_path},
        }
    }


async def apply_notion_page_read_redirect(
    tool_name: str,
    tool_input: dict[str, Any],
    *,
    workspace_path: str | None,
    credential_home: str | None,
    tmp_workspace: str | None,
    tmp_paths: list[str],
) -> dict[str, Any] | None:
    """Resolve an authorized Notion page only when Claude calls ``Read``."""

    if tool_name != "Read" or not workspace_path:
        return None
    try:
        workspace = Path(workspace_path).resolve(strict=True)
    except (FileNotFoundError, OSError, RuntimeError):
        return None
    raw_path = str(tool_input.get("file_path") or "").strip()
    target = _page_target(raw_path, workspace)
    if target is None:
        return None
    _candidate, page_id = target

    try:
        pages, snapshot = _load_index(workspace)
        index_entry = pages.get(page_id)
        if index_entry is None:
            payload: dict[str, Any] = {
                "ok": False,
                "code": "NOTION_RESOURCE_NOT_SELECTED",
                "message": "This page is not present in the thread's Notion index.",
                "nextAction": "Select the page or its database in Resource Links and sync the index.",
                "page_id": page_id,
                "snapshot": snapshot,
            }
        else:
            home = _validated_home(credential_home, workspace)
            result = await NotionOperationClient(home).get_page_markdown(page_id)
            payload = {
                "ok": True,
                **index_entry,
                "markdown": str((result.data or {}).get("markdown") or ""),
                "snapshot": snapshot,
            }
    except Exception as exc:
        payload = {**_safe_failure(exc), "page_id": page_id}
        logger.warning("Notion lazy page read failed safely; Agent turn continues.")

    try:
        return _write_redirect(
            payload,
            tmp_workspace=tmp_workspace,
            workspace=workspace,
            tmp_paths=tmp_paths,
        )
    except Exception:  # noqa: BLE001 - do not expose paths or content through the hook
        logger.warning("Notion lazy page redirect failed safely; Agent turn continues.")
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "Notion page content is temporarily unavailable.",
            }
        }


NOTION_READ_HOOK_OPERATION: Mapping[str, str] = {
    "id": "notion-page-read-hook",
    "title": "按需读取页面正文",
    "description": "只在回答需要时校验已选范围，并读取一个页面的最新 Markdown。",
    "kind": "read",
    "source": "runtime_hook",
    "requirement": "index",
    "entrypoint": apply_notion_page_read_redirect.__name__,
}


__all__ = ["NOTION_READ_HOOK_OPERATION", "apply_notion_page_read_redirect"]
