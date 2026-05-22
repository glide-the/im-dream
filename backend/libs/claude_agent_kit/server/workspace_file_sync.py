# [Input] Consume workspace_path from libs/claude_agent_kit/server/workspace.py.
# [Output] Provide sync_skills_symlinks and _clean_stale_skill_symlinks to
#          workspace.py and the API layer (api/workspace/files.py).
# [Pos] symlink-sync node in libs/claude_agent_kit/server
# [Sync] 2026-05-06: initial implementation — WSK-02 skills symlink sync

"""Skills symlink synchronisation for Claude Agent workspaces.

Maintains a 1-to-1 mapping from ``{workspace}/skills/*`` to
``{workspace}/.claude/skills/*`` using filesystem symbolic links so that
the Claude Agent always discovers skills at the canonical ``.claude/skills/``
location.

Rules
-----
- Only non-dot-prefixed entries in ``skills/`` are exposed.
- If a symlink in ``.claude/skills/`` already points to the correct source,
  it is left unchanged (no unnecessary re-creation).
- If the target slot is occupied by a symlink pointing elsewhere, or by a
  plain file/directory, the slot is cleared and the correct symlink is created.
- After syncing, any symlink in ``.claude/skills/`` whose source entry no
  longer exists in ``skills/`` is removed (stale-link cleanup).
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def sync_skills_symlinks(workspace_path: Path) -> None:
    """Synchronise ``{workspace}/skills/`` → ``{workspace}/.claude/skills/``.

    Creates, updates, and cleans up symbolic links so that every non-hidden
    entry in ``skills/`` has a matching symlink in ``.claude/skills/``.

    Raises ``OSError`` if the filesystem does not support symlinks (the error
    propagates so callers can log or surface it — no silent failure).
    """
    skills_src = workspace_path / "skills"
    skills_dst = workspace_path / ".claude" / "skills"

    if not skills_src.is_dir():
        logger.debug(
            "sync_skills_symlinks: skills source dir does not exist: %s", skills_src
        )
        return

    skills_dst.mkdir(parents=True, exist_ok=True)

    # Build set of current source entries (excluding dot-prefixed names).
    src_entries: dict[str, Path] = {}
    for entry in skills_src.iterdir():
        if not entry.name.startswith("."):
            src_entries[entry.name] = entry

    # -----------------------------------------------------------------------
    # Step 1: create / update symlinks for current source entries.
    # -----------------------------------------------------------------------
    for name, src in src_entries.items():
        dst_link = skills_dst / name
        _ensure_symlink(src, dst_link)

    # -----------------------------------------------------------------------
    # Step 2: remove stale symlinks (source entry was deleted or renamed).
    # -----------------------------------------------------------------------
    _clean_stale_skill_symlinks(skills_dst, src_entries)


def _ensure_symlink(src: Path, dst_link: Path) -> None:
    """Ensure *dst_link* is a symlink pointing to *src*.

    If *dst_link* already points to *src*, it is left unchanged.
    If *dst_link* exists but points elsewhere, or is a plain file/directory,
    it is removed and recreated.
    """
    # Use absolute path for the symlink target.
    target = src.resolve()

    if dst_link.is_symlink():
        try:
            existing_target = Path(os.readlink(dst_link)).resolve()
        except OSError:
            existing_target = None
        if existing_target == target:
            return  # already correct — nothing to do
        # Wrong target — remove and recreate.
        dst_link.unlink()
        logger.debug("Removed mismatched symlink: %s", dst_link)
    elif dst_link.exists():
        # Plain file or directory occupying the slot — clear it.
        import shutil as _shutil
        if dst_link.is_dir():
            _shutil.rmtree(dst_link)
        else:
            dst_link.unlink()
        logger.warning(
            "Removed non-symlink occupying .claude/skills slot: %s", dst_link
        )

    dst_link.symlink_to(target)
    logger.debug("Created symlink: %s → %s", dst_link, target)


def _clean_stale_skill_symlinks(
    skills_link_dir: Path,
    current_src_entries: dict[str, Path],
) -> None:
    """Remove symlinks in *skills_link_dir* whose source no longer exists.

    Only symbolic links are touched — real files or directories in
    ``.claude/skills/`` that were not created by this sync mechanism are
    left untouched to avoid data loss.
    """
    if not skills_link_dir.is_dir():
        return

    for entry in list(skills_link_dir.iterdir()):
        if not entry.is_symlink():
            continue  # never touch real files/directories
        if entry.name not in current_src_entries:
            entry.unlink()
            logger.debug("Removed stale symlink: %s", entry)
