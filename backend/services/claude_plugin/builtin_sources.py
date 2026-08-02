"""Server-declared platform-builtin plugin sources.

Platform-builtin plugins are repository-owned plugin directories declared
*here* (never accepted from a browser).  They go through the same
digest → immutable artifact → pack pipeline as marketplace installs; the real
CLI evidence for them is ``claude plugin validate`` plus the recorded file
inventory and digest (there is no marketplace install step for a
repository-owned directory).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, TypedDict


class BuiltinSourceDecl(TypedDict):
    package_name: str
    marketplace: str
    source_type: str
    repository_relative_path: str
    compatibility: dict[str, str]


_REPO_ROOT = Path(__file__).resolve().parents[3]

PLATFORM_BUILTIN_SOURCES: dict[str, BuiltinSourceDecl] = {
    "ink-dream-story@platform-builtin": {
        "package_name": "ink-dream-story",
        "marketplace": "platform-builtin",
        "source_type": "platform-builtin",
        "repository_relative_path": "plugins/ink-dream-story",
        "compatibility": {
            "claude_code": ">=1.0.0 <3.0.0",
            "platform": ">=1.0.0 <2.0.0",
        },
    },
}

# Official Anthropic marketplace shorthand → git repo (see
# https://code.claude.com/docs/zh-CN/discover-plugins).
KNOWN_MARKETPLACE_REPOS: dict[str, str] = {
    "claude-plugins-official": "anthropics/claude-plugins-official",
    "claude-community": "anthropics/claude-plugins-community",
}


def resolve_builtin_source(spec_canonical: str) -> Path | None:
    """Return the server-declared repository path for a builtin spec."""
    decl = PLATFORM_BUILTIN_SOURCES.get(spec_canonical)
    if decl is None:
        return None
    path = (_REPO_ROOT / decl["repository_relative_path"]).resolve()
    repo_root = _REPO_ROOT.resolve()
    try:
        path.relative_to(repo_root)
    except ValueError:
        return None
    return path if path.is_dir() else None


def get_builtin_declaration(spec_canonical: str) -> dict[str, Any] | None:
    decl = PLATFORM_BUILTIN_SOURCES.get(spec_canonical)
    if decl is None:
        return None
    return {
        "package_spec": spec_canonical,
        "source_type": decl["source_type"],
        "compatibility": dict(decl["compatibility"]),
    }
