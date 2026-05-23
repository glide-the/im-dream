# [Input] None — pure constant / helper module with no external dependencies.
# [Output] Provide EDITOR_INDEX_DIR, EDITOR_RESOURCES, is_editor_index_path,
#          resolve_editor_resource, get_editor_resource_data to workspace.py
#          and agent_runner.py.
# [Pos] editor-index-constants node in libs/claude_agent_kit/server
# [Sync] 2026-05-23: initial implementation — virtual EditorState index adapter.

"""Virtual EditorState index path conventions.

Each Ink & Memory workspace contains a ``.editor/`` directory with lightweight
placeholder files.  These files are **never** written with real content;
instead, any ``Read`` tool call whose path falls inside ``.editor/`` is
intercepted by the ``PreToolUse`` hook in ``agent_runner.py`` and redirected
to a transient tempfile populated from the live ``EditorState`` snapshot that
was attached to the current agent run.

Resource mapping
----------------
============================  ============================
Virtual path                  EditorState key(s)
============================  ============================
``.editor/cells.json``        ``cells``
``.editor/commentors.json``   ``commentors``
``.editor/tasks.json``        ``tasks``
``.editor/session.json``      ``id``, ``selectedState``, ``createdAt``
``.editor/full_state.json``   entire EditorState dict
============================  ============================

The same keys are used as tool names in the EditorEngine MCP server
(``mcp__editor__read_{resource}``).
"""
from __future__ import annotations

import os
from pathlib import PurePosixPath
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EDITOR_INDEX_DIR = ".editor"

#: Mapping of virtual filename stem → EditorState field name(s).
#: The special value ``"__full__"`` means "return the entire state dict".
EDITOR_RESOURCES: dict[str, str] = {
    "cells": "cells",
    "commentors": "commentors",
    "tasks": "tasks",
    "session": "__session__",
    "full_state": "__full__",
}

#: Canonical placeholder JSON written to disk so Claude can discover the files.
EDITOR_INDEX_PLACEHOLDER = "{}\n"

#: README content placed inside ``.editor/`` to document the virtual index.
EDITOR_INDEX_README = """\
# .editor — Virtual EditorState Index

Files in this directory are **virtual placeholders** maintained by the
Ink & Memory EditorEngine adapter.  Their on-disk content is always empty
JSON (``{}``); any ``Read`` tool call against one of these paths is
intercepted at the ``PreToolUse`` hook level and redirected to a temporary
file populated with the live ``EditorState`` snapshot for the current session.

## Available resources

| File              | EditorState content              |
|-------------------|----------------------------------|
| cells.json        | Text and widget cells array      |
| commentors.json   | Voice commentor annotations      |
| tasks.json        | In-progress analysis tasks       |
| session.json      | Session metadata (id, state, ts) |
| full_state.json   | Complete EditorState snapshot    |

You can also read these resources directly via the MCP tool
``mcp__editor__read_full_state`` (no path argument needed).
"""

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def is_editor_index_path(path: str) -> bool:
    """Return True when *path* falls inside the ``.editor/`` virtual directory.

    Accepts both POSIX and Windows-style separators and handles relative paths
    such as ``.editor/cells.json`` as well as workspace-absolute paths that end
    with ``/.editor/cells.json``.
    """
    if not path:
        return False
    # Normalise to forward slashes for consistent matching.
    normalised = path.replace("\\", "/")
    # Strip any leading absolute prefix and workspace-root components so that
    # ``/some/workspace/.editor/cells.json`` also matches.
    try:
        parts = PurePosixPath(normalised).parts
    except ValueError:  # noqa: BLE001
        return False
    return EDITOR_INDEX_DIR in parts


def resolve_editor_resource(path: str) -> Optional[str]:
    """Return the resource stem for a virtual ``.editor/`` path.

    Examples::

        >>> resolve_editor_resource(".editor/cells.json")
        'cells'
        >>> resolve_editor_resource("/workspace/abc/.editor/full_state.json")
        'full_state'
        >>> resolve_editor_resource("files/regular.txt")
        None
    """
    if not is_editor_index_path(path):
        return None
    normalised = path.replace("\\", "/")
    basename = os.path.basename(normalised)
    stem, _ = os.path.splitext(basename)
    return stem if stem in EDITOR_RESOURCES else None


def get_editor_resource_data(
    editor_state: dict[str, Any],
    resource: str,
) -> Any:
    """Extract the sub-section of *editor_state* identified by *resource*.

    Returns the raw Python value (list or dict) ready to be JSON-serialised
    into the intercepted tempfile.  Unknown or missing resources return an
    empty dict so that ``Read`` always succeeds gracefully.
    """
    field = EDITOR_RESOURCES.get(resource)
    if field is None:
        return {}
    if field == "__full__":
        return editor_state
    if field == "__session__":
        return {
            "id": editor_state.get("id"),
            "selectedState": editor_state.get("selectedState"),
            "createdAt": editor_state.get("createdAt"),
        }
    return editor_state.get(field, [])


__all__ = [
    "EDITOR_INDEX_DIR",
    "EDITOR_RESOURCES",
    "EDITOR_INDEX_PLACEHOLDER",
    "EDITOR_INDEX_README",
    "is_editor_index_path",
    "resolve_editor_resource",
    "get_editor_resource_data",
]
