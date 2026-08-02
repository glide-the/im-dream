"""Deterministic SHA-256 digest over a plugin directory (kit-owned).

This is the single canonical digest implementation shared by the server-side
plugin artifact store (``services.claude_plugin``) and the Claude CLI launch
boundary in this kit.  The digest covers every regular file under the plugin
root except volatile CLI runtime state (``.git/`` and the CLI's per-process
``.in_use/`` PID markers — observed in the real Claude Code 2.1.220 cache).

Verified reference value: a real ``superpowers@claude-plugins-official``
6.2.0 cache tree (181 entries including the relative in-tree symlink
``AGENTS.md -> CLAUDE.md``) digests to
``sha256:285f0772167b0e050cc75b9be331137b7212d10ffadb5c461c59955620ba79ea``.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

DIGEST_PREFIX = "sha256:"
# Directories excluded from the digest: VCS metadata and the CLI's volatile
# in-use markers (PID files created per running process).
EXCLUDED_DIR_NAMES = frozenset({".git", ".in_use"})


class PluginDigestError(ValueError):
    """Raised when a plugin directory cannot be digested."""


def compute_plugin_digest(root: Path) -> str:
    """Return ``sha256:<hex>`` for the plugin tree at *root*.

    Symlinks are not followed: a symlink entry is hashed by its target path
    string so artifacts can never silently smuggle out-of-tree content into
    the digest (the artifact store rejects symlinks outright).
    """
    root = Path(root).resolve()
    if not root.is_dir():
        raise PluginDigestError(f"plugin directory is missing: {root}")
    entries: list[tuple[str, bytes]] = []
    for item in sorted(root.rglob("*")):
        relative = item.relative_to(root)
        if any(part in EXCLUDED_DIR_NAMES for part in relative.parts):
            continue
        rel_text = relative.as_posix()
        if item.is_symlink():
            # Hash the link itself (type marker + target string), never the
            # target content.
            entries.append((rel_text, b"L" + os.readlink(item).encode("utf-8")))
            continue
        if not item.is_file():
            continue
        entries.append((rel_text, item.read_bytes()))
    if not entries:
        raise PluginDigestError(f"plugin directory is empty: {root}")
    digest = hashlib.sha256()
    for rel_text, content in entries:
        rel_encoded = rel_text.encode("utf-8")
        digest.update(len(rel_encoded).to_bytes(4, "big"))
        digest.update(rel_encoded)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return DIGEST_PREFIX + digest.hexdigest()


def digest_is_valid(value: str) -> bool:
    """Return True when *value* looks like a digest produced here."""
    if not isinstance(value, str) or not value.startswith(DIGEST_PREFIX):
        return False
    hexpart = value[len(DIGEST_PREFIX):]
    if len(hexpart) != 64:
        return False
    try:
        int(hexpart, 16)
    except ValueError:
        return False
    return True
