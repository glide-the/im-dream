# [Input] Apple's process memory headroom and the existing Agent resource snapshot contract.
# [Output] Remaining application memory bytes for the original admission comparisons.
# [Pos] iOS resource sampler; no quota overrides, cgroup emulation or admission algorithm.
from __future__ import annotations

import sys

from claude_agent.admission import AgentResourceSnapshot


def read_ios_resource_snapshot() -> AgentResourceSnapshot:
    if sys.platform != "ios":
        raise RuntimeError("DREAM_IOS_MEMORY_TARGET_REQUIRED")
    from _dream_native import available_memory
    # Apple returns zero when the application has exhausted its memory limit.
    # Preserve that observation for the original low-memory admission check.
    return AgentResourceSnapshot(host_available_bytes=available_memory())
