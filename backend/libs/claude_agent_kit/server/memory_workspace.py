# [Input] None — reads partition memory_workspace_config from the voices DB table.
#          Template files for the four configurable prompts are sourced exclusively
#          from the partition config; .claude/memory/ is used ONLY for WORKFLOW.md.
# [Output] Provide init_memory_workspace, apply_memory_config, get_memory_context_block
#          to claude_agent/service.py (and any explicit file-interface callers).
# [Pos] memory-workspace node in libs/claude_agent_kit/server
# [Sync] 2026-06-05: initial implementation — Memory Workspace initialization,
#                    per-voice config application, and memory context injection.
# [Sync] 2026-06-05: template files now sourced exclusively from the partition (voice)
#                    configuration table (voices.memory_workspace_config).
#                    The filesystem fallback to .claude/memory/ is removed for the four
#                    configurable prompt files; only WORKFLOW.md still uses the filesystem
#                    source (shared workflow logic, never partition-specific).
#                    Memory workspace is classified as the "procedural" memory type.

"""Memory Workspace manager for Claude Agent session directories.

Memory workspace type: **procedural** — stores structured behavioural rules and
accumulated session history (prompts, long-term summary, event/preference JSON).

Each session workspace gains a ``memory/`` subdirectory that holds:

- Four prompt template files sourced exclusively from the partition (voice)
  configuration table (``voices.memory_workspace_config``).  Files absent from
  the partition config are simply not written — there is no fallback to the
  filesystem.
- ``WORKFLOW.md`` — always sourced from ``{project_root}/.claude/memory/``
  because it encodes shared workflow logic that is never partition-specific.
- A ``long_term_memory.md`` file (created/updated at runtime) that accumulates
  conversation summaries across sessions.
- A ``procedural/`` subdirectory containing structured JSON files for user
  preferences, important events, and a session timeline.

Per-voice configuration (``memory_workspace_config`` JSON from the ``voices``
DB table) is the sole source for the four configurable template files.  It maps
them via the keys also used by :func:`apply_memory_config`.

Usage::

    from libs.claude_agent_kit.server.memory_workspace import (
        init_memory_workspace,
        apply_memory_config,
        get_memory_context_block,
    )

    workspace = get_or_create_workspace(session_id)
    memory_config = database.get_voice_memory_config_by_thread(thread_id)
    init_memory_workspace(workspace, memory_config)
    block = get_memory_context_block(workspace)
"""
from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Names of the five prompt template files in the memory/ directory.
MEMORY_PROMPT_FILES: tuple[str, ...] = (
    "WORKFLOW.md",
    "MEMORY_QUERY_PROMPT.md",
    "MEMORY_Distiller_PROMPT.md",
    "MEMORY_ANSWER_PROMPT.md",
    "DEFAULT_UPDATE_MEMORY_PROMPT.md",
)

# Map from memory_workspace_config JSON key → file name in memory/.
_CONFIG_KEY_TO_FILE: dict[str, str] = {
    "query_prompt_override": "MEMORY_QUERY_PROMPT.md",
    "distiller_prompt_override": "MEMORY_Distiller_PROMPT.md",
    "answer_prompt_override": "MEMORY_ANSWER_PROMPT.md",
    "update_prompt_override": "DEFAULT_UPDATE_MEMORY_PROMPT.md",
}

# Reverse mapping: file name → config key (for the four configurable files).
_FILE_TO_CONFIG_KEY: dict[str, str] = {v: k for k, v in _CONFIG_KEY_TO_FILE.items()}

# Names of the runtime-generated procedural memory JSON files.
PROCEDURAL_MEMORY_FILES: tuple[str, ...] = (
    "user_preferences.json",
    "important_events.json",
    "timeline.json",
)

# Starter content for runtime-generated procedural files (first-init only).
_PROCEDURAL_DEFAULTS: dict[str, Any] = {
    "user_preferences.json": {
        "writing_style": None,
        "preferred_language": None,
        "active_hours": None,
        "response_length": None,
        "topics_of_interest": [],
        "avoid_topics": [],
        "updated_at": None,
    },
    "important_events.json": [],
    "timeline.json": [],
}

# Starter content for the long-term memory file (first-init only).
_LONG_TERM_MEMORY_DEFAULT = """\
# Long-term Memory

_No entries yet. This file will be populated by the memory distillation workflow._
"""

# Project root (four levels above this file: server/ → claude_agent_kit/ → libs/ → backend/ → project)
_PROJECT_ROOT: Path = Path(__file__).resolve().parents[4]


def _project_root() -> Path:
    return _PROJECT_ROOT


def _resolve_safe_memory_dir(workspace: Path) -> Optional[Path]:
    """Resolve and verify the ``memory/`` path is safely inside the workspace root.

    Returns the resolved absolute ``memory/`` Path, or ``None`` when:
    - the workspace cannot be resolved, or
    - the resolved workspace lies outside the configured workspace root.

    This follows the same guard pattern as ``_init_editor_index`` in workspace.py
    to prevent path-traversal attacks when *workspace* contains a user-controlled
    session_id component.
    """
    try:
        from .workspace import get_workspace_root  # local import avoids circular
        workspace_root_abs = get_workspace_root().resolve()
        workspace_abs = workspace.resolve()
        if not workspace_abs.is_relative_to(workspace_root_abs):
            logger.warning(
                "_resolve_safe_memory_dir: workspace %r is outside workspace root %r; aborting.",
                workspace_abs,
                workspace_root_abs,
            )
            return None
        # "memory" is a fixed subdirectory name — no user input involved.
        return workspace_abs / "memory"
    except Exception:  # noqa: BLE001
        logger.warning(
            "_resolve_safe_memory_dir: could not resolve workspace path; aborting.",
            exc_info=True,
        )
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def init_memory_workspace(workspace: Path, memory_config: Optional[dict[str, Any]] = None) -> Path:
    """Create (or repair) the ``memory/`` subdirectory in *workspace*.

    Memory workspace type: **procedural** — stores structured behavioural
    rules, prompt templates, and accumulated session history.

    Steps:
    1. Create ``memory/`` (idempotent).
    2. Sync prompt template files from *memory_config* (the partition's
       ``memory_workspace_config`` from the ``voices`` DB table).
       - Four configurable template files are written exclusively from
         *memory_config*; files absent from the config are simply skipped
         (no filesystem fallback).
       - ``WORKFLOW.md`` is always copied from
         ``{project_root}/.claude/memory/`` (shared workflow logic).
    3. Create ``memory/procedural/`` subdirectory (idempotent).
    4. Write starter procedural JSON files (first-init only — existing files
       are preserved to avoid losing runtime-accumulated memories).
    5. Write ``memory/long_term_memory.md`` starter (first-init only).

    Args:
        workspace:     Session workspace root directory.
        memory_config: Partition (voice) ``memory_workspace_config`` dict
                       fetched from the ``voices`` DB table.  The four
                       configurable template files are written only when
                       present in this config; missing keys are skipped.
                       When ``None`` only ``WORKFLOW.md`` is written (from
                       the shared filesystem source).

    Returns the absolute ``memory/`` directory path.
    Raises ``ValueError`` when *workspace* resolves outside the configured workspace root.
    """
    memory_dir = _resolve_safe_memory_dir(workspace)
    if memory_dir is None:
        raise ValueError(
            f"init_memory_workspace: workspace {workspace!r} is outside the configured "
            "workspace root or could not be resolved."
        )
    memory_dir.mkdir(exist_ok=True)

    # Sync prompt template files from partition config or .claude/memory/ fallback.
    _sync_memory_templates(memory_dir, memory_config)

    # Ensure procedural/ subdirectory exists.
    procedural_dir = memory_dir / "procedural"
    procedural_dir.mkdir(exist_ok=True)

    # Write starter procedural JSON files (first-init only).
    for filename, default_content in _PROCEDURAL_DEFAULTS.items():
        dest = procedural_dir / filename
        if dest.exists():
            continue
        try:
            dest.write_text(
                json.dumps(default_content, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            logger.debug("Created memory/procedural/%s", filename)
        except OSError:
            logger.warning(
                "Failed to create memory/procedural/%s; skipping.",
                filename,
                exc_info=True,
            )

    # Write long_term_memory.md starter (first-init only).
    long_term = memory_dir / "long_term_memory.md"
    if not long_term.exists():
        try:
            long_term.write_text(_LONG_TERM_MEMORY_DEFAULT, encoding="utf-8")
            logger.debug("Created memory/long_term_memory.md")
        except OSError:
            logger.warning(
                "Failed to create memory/long_term_memory.md; skipping.",
                exc_info=True,
            )

    logger.debug("Memory workspace initialised: %s", memory_dir)
    return memory_dir


def apply_memory_config(
    workspace: Path,
    memory_config: Optional[dict[str, Any]],
) -> None:
    """Apply per-voice ``memory_workspace_config`` overrides to *workspace*.

    When *memory_config* is ``None`` or empty, this function is a no-op.

    Supported override keys (all optional):
    - ``query_prompt_override``     → overwrites ``MEMORY_QUERY_PROMPT.md``
    - ``distiller_prompt_override`` → overwrites ``MEMORY_Distiller_PROMPT.md``
    - ``answer_prompt_override``    → overwrites ``MEMORY_ANSWER_PROMPT.md``
    - ``update_prompt_override``    → overwrites ``DEFAULT_UPDATE_MEMORY_PROMPT.md``

    The ``WORKFLOW.md`` file is never overridden — it defines the shared
    workflow logic and should remain consistent across all voices.
    """
    if not memory_config:
        return

    memory_dir = _resolve_safe_memory_dir(workspace)
    if memory_dir is None or not memory_dir.is_dir():
        logger.warning(
            "apply_memory_config: memory/ dir not reachable at %s; skipping.", workspace
        )
        return

    for config_key, filename in _CONFIG_KEY_TO_FILE.items():
        override_content = memory_config.get(config_key)
        if not override_content or not isinstance(override_content, str):
            continue
        # filename is from the fixed _CONFIG_KEY_TO_FILE dict — no user input involved.
        dest = memory_dir / filename
        try:
            dest.write_text(override_content.strip() + "\n", encoding="utf-8")
            logger.debug(
                "Applied memory_workspace_config override: %s → %s", config_key, filename
            )
        except OSError:
            logger.warning(
                "Failed to write memory config override %s; skipping.",
                filename,
                exc_info=True,
            )


def get_memory_context_block(workspace: Path) -> str:
    """Return a ``<memory_context>`` text block for injection into user messages.

    The block tells the agent about the memory workspace layout (type:
    **procedural**), the available prompt files, and whether runtime memory
    files (long_term_memory.md, procedural/*.json) exist so the agent can
    decide whether to read them.

    Returns an empty string when the ``memory/`` directory does not exist or
    when *workspace* resolves outside the configured workspace root.
    """
    memory_dir = _resolve_safe_memory_dir(workspace)
    if memory_dir is None or not memory_dir.is_dir():
        return ""

    long_term_exists = (memory_dir / "long_term_memory.md").is_file()
    procedural_dir = memory_dir / "procedural"
    procedural_files: list[str] = []
    if procedural_dir.is_dir():
        procedural_files = sorted(
            f.name
            for f in procedural_dir.iterdir()
            if f.is_file() and f.suffix == ".json"
        )

    lines: list[str] = [
        "<memory_context>",
        f"Memory workspace (type: procedural): {memory_dir}",
        "",
        "Memory prompt files (read for instructions):",
        "  memory/WORKFLOW.md                     — memory decision tree",
        "  memory/MEMORY_QUERY_PROMPT.md           — 7-category memory retrieval",
        "  memory/MEMORY_Distiller_PROMPT.md       — memory distillation",
        "  memory/MEMORY_ANSWER_PROMPT.md          — memory-informed responses",
        "  memory/DEFAULT_UPDATE_MEMORY_PROMPT.md  — memory update rules (ADD/UPDATE/DELETE/NO_CHANGE)",
        "",
    ]

    if long_term_exists:
        lines.append("Long-term memory: memory/long_term_memory.md (available — read for context)")
    else:
        lines.append("Long-term memory: not yet created")

    if procedural_files:
        files_list = ", ".join(procedural_files)
        lines.append(f"Procedural memory files: {files_list}")
        lines.append("  → Located in memory/procedural/  (read for user preferences and events)")
    else:
        lines.append("Procedural memory: not yet created")

    lines.append("</memory_context>")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _sync_memory_templates(
    memory_dir: Path,
    memory_config: Optional[dict[str, Any]] = None,
) -> None:
    """Write prompt template files into *memory_dir* from the partition config or filesystem.

    Template source rules:
    - ``WORKFLOW.md`` — always copied from ``{project_root}/.claude/memory/``
      (shared workflow logic, never partition-specific).
    - The four configurable files — written exclusively from *memory_config*
      when the corresponding override key is present and non-empty.  If the
      key is absent from the config the file is **not** written; there is no
      filesystem fallback.

    ``memory_config`` keys that map to template files:

    =========================  =====================================
    Config key                  File
    =========================  =====================================
    ``query_prompt_override``   ``MEMORY_QUERY_PROMPT.md``
    ``distiller_prompt_override`` ``MEMORY_Distiller_PROMPT.md``
    ``answer_prompt_override``  ``MEMORY_ANSWER_PROMPT.md``
    ``update_prompt_override``  ``DEFAULT_UPDATE_MEMORY_PROMPT.md``
    =========================  =====================================

    Runtime files (``long_term_memory.md``, ``procedural/``) are never touched
    by this function.
    """
    src_memory = _project_root() / ".claude" / "memory"

    for filename in MEMORY_PROMPT_FILES:
        dest = memory_dir / filename
        config_key = _FILE_TO_CONFIG_KEY.get(filename)

        if config_key is not None:
            # Configurable file: write from partition config only.
            content = (memory_config or {}).get(config_key)
            if content and isinstance(content, str):
                try:
                    dest.write_text(content.strip() + "\n", encoding="utf-8")
                    logger.debug(
                        "_sync_memory_templates: wrote %s from partition config key %s",
                        filename,
                        config_key,
                    )
                except OSError:
                    logger.warning(
                        "_sync_memory_templates: failed to write %s from partition config; "
                        "skipping (no filesystem fallback).",
                        filename,
                        exc_info=True,
                    )
            else:
                logger.debug(
                    "_sync_memory_templates: %s not present in partition config; skipping.",
                    filename,
                )
        else:
            # WORKFLOW.md: always sourced from the project filesystem.
            if not src_memory.is_dir():
                logger.debug(
                    "_sync_memory_templates: project .claude/memory/ not found; "
                    "cannot write %s.",
                    filename,
                )
                continue
            src = src_memory / filename
            if not src.is_file():
                logger.debug(
                    "_sync_memory_templates: template %s not found in .claude/memory/; skipping.",
                    filename,
                )
                continue
            try:
                shutil.copy2(str(src), str(dest))
                logger.debug("_sync_memory_templates: copied %s from .claude/memory/", filename)
            except OSError:
                logger.warning(
                    "_sync_memory_templates: failed to copy %s → %s; skipping.",
                    src,
                    dest,
                    exc_info=True,
                )


__all__ = [
    "init_memory_workspace",
    "apply_memory_config",
    "get_memory_context_block",
    "MEMORY_PROMPT_FILES",
    "PROCEDURAL_MEMORY_FILES",
]
