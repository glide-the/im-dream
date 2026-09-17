# [Input] Repository-owned Dream Story plugin files and a controlled source reference.
# [Output] Canonical local path and content digest for Admin-planned artifact verification.
# [Pos] Dream shared-filesystem verifier; Admin owns release/lock/ref persistence through DTO/ORM.
# [Sync] 2026-09-16: remove zero-caller release seeding and legacy repair SQL after Registry183-184.
"""Resolve the repository-owned Dream Story Claude SDK plugin."""

from __future__ import annotations

import hashlib
from pathlib import Path


BUILTIN_DECK_PLUGIN_ID = "ink.dream.story-workflow"
BUILTIN_DECK_PLUGIN_VERSION = "1.0.0"
BUILTIN_CLAUDE_PLUGIN_ID = "ink-dream-story@platform-builtin"
BUILTIN_SOURCE_REF = "builtin://ink-dream-story"


def builtin_plugin_path() -> Path:
    return Path(__file__).resolve().parents[3] / "plugins" / "ink-dream-story"


def plugin_artifact_digest(path: Path | None = None) -> str:
    root = (path or builtin_plugin_path()).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Dream Story plugin directory is missing: {root}")
    digest = hashlib.sha256()
    files = sorted(item for item in root.rglob("*") if item.is_file())
    if not files:
        raise ValueError("Dream Story plugin directory is empty")
    for item in files:
        relative = item.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        content = item.read_bytes()
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return "sha256:" + digest.hexdigest()


def resolve_builtin_source(source_ref: str) -> Path | None:
    if source_ref != BUILTIN_SOURCE_REF:
        return None
    return builtin_plugin_path().resolve()
