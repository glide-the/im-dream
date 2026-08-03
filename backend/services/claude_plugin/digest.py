"""Re-export of the canonical plugin digest from the agent kit.

The implementation lives in ``libs.claude_agent_kit.server.plugin_digest``
so the Claude CLI launch boundary (agent runner) and the server-side artifact
store share one algorithm.  See that module for the verified reference value.
"""

from __future__ import annotations

try:
    from libs.claude_agent_kit.server.plugin_digest import (
        APPLEDOUBLE_FILE_PREFIX,
        DIGEST_PREFIX,
        EXCLUDED_DIR_NAMES,
        EXCLUDED_FILE_NAMES,
        PluginDigestError,
        compute_plugin_digest,
        digest_is_valid,
        entry_is_excluded,
    )
except ModuleNotFoundError:  # Support backend directory on PYTHONPATH.
    from backend.libs.claude_agent_kit.server.plugin_digest import (
        APPLEDOUBLE_FILE_PREFIX,
        DIGEST_PREFIX,
        EXCLUDED_DIR_NAMES,
        EXCLUDED_FILE_NAMES,
        PluginDigestError,
        compute_plugin_digest,
        digest_is_valid,
        entry_is_excluded,
    )

__all__ = [
    "APPLEDOUBLE_FILE_PREFIX",
    "DIGEST_PREFIX",
    "EXCLUDED_DIR_NAMES",
    "EXCLUDED_FILE_NAMES",
    "PluginDigestError",
    "compute_plugin_digest",
    "digest_is_valid",
    "entry_is_excluded",
]
