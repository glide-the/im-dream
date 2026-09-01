# [Input] A bounded token candidate from an Episode public-text projection.
# [Output] Whether the token is a strict canonical workspace-relative reference.
# [Pos] Shared allowlist policy for narrative and auxiliary Episode adapters.
# [Sync] 2026-09-02: centralize canonical assets/** and stories/** references.

"""Shared public-text allowlist for canonical Episode workspace references."""

from __future__ import annotations

import re


_PUBLIC_WORKSPACE_RELATIVE_REFERENCE_RE = re.compile(
    r"(?:"
    r"assets/(?:characters|scenes|props)/[A-Za-z0-9][A-Za-z0-9._-]{0,127}|"
    r"stories/[a-z0-9]+(?:-[a-z0-9]+)*/episodes/EP[0-9]{2}/"
    r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}"
    r")",
    re.IGNORECASE,
)


def is_story_workspace_episode_public_relative_reference(value: str) -> bool:
    """Return true only for the two canonical public workspace path families."""

    return _PUBLIC_WORKSPACE_RELATIVE_REFERENCE_RE.fullmatch(value) is not None
