# [Input] Consume INK_AGENT resource-budget configuration plus Linux procfs/cgroup v2 metrics.
# [Output] Provide ClaudeAgentAdmissionController, ClaudeAgentAdmissionError,
#          AgentAdmissionConfig, AgentResourceSnapshot, and AgentAdmissionLease.
# [Pos] resource-admission node in backend/claude_agent; guards the existing turn runtime.
# [Sync] 2026-08-26: include conservative cgroup inactive-file and reclaimable-slab
#                    capacity so cache pressure does not reject safe Agent starts.
# [Sync] 2026-08-27: add atomic public config replacement for future acquisitions;
#                    active leases and the admission decision algorithm are unchanged.

"""Bounded, process-local resource admission for Claude Agent turns."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_MIB = 1024 * 1024
_DEFAULT_MAX_CONCURRENT_RUNS = 1
_DEFAULT_RUN_MEMORY_BUDGET_MIB = 512
_DEFAULT_MEMORY_RESERVE_MIB = 128
_DEFAULT_RETRY_AFTER_SECONDS = 60


def _read_int_env(name: str, default: int, *, minimum: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return value


@dataclass(frozen=True, slots=True)
class AgentAdmissionConfig:
    """Central resource-budget contract for one backend process."""

    max_concurrent_runs: int
    run_memory_budget_mib: int
    memory_reserve_mib: int
    retry_after_seconds: int

    @classmethod
    def from_env(cls) -> AgentAdmissionConfig:
        return cls(
            max_concurrent_runs=_read_int_env(
                "INK_AGENT_MAX_CONCURRENT_RUNS",
                _DEFAULT_MAX_CONCURRENT_RUNS,
                minimum=1,
            ),
            run_memory_budget_mib=_read_int_env(
                "INK_AGENT_RUN_MEMORY_BUDGET_MIB",
                _DEFAULT_RUN_MEMORY_BUDGET_MIB,
                minimum=1,
            ),
            memory_reserve_mib=_read_int_env(
                "INK_AGENT_MEMORY_RESERVE_MIB",
                _DEFAULT_MEMORY_RESERVE_MIB,
                minimum=0,
            ),
            retry_after_seconds=_read_int_env(
                "INK_AGENT_SWEEP_INTERVAL_S",
                _DEFAULT_RETRY_AFTER_SECONDS,
                minimum=1,
            ),
        )

    @property
    def required_headroom_bytes(self) -> int:
        return (self.run_memory_budget_mib + self.memory_reserve_mib) * _MIB


@dataclass(frozen=True, slots=True)
class AgentResourceSnapshot:
    """Numeric resource signals safe to expose in process diagnostics."""

    host_available_bytes: int | None = None
    cgroup_current_bytes: int | None = None
    cgroup_max_bytes: int | None = None
    cgroup_reclaimable_bytes: int | None = None

    @property
    def cgroup_raw_headroom_bytes(self) -> int | None:
        if self.cgroup_current_bytes is None or self.cgroup_max_bytes is None:
            return None
        return max(0, self.cgroup_max_bytes - self.cgroup_current_bytes)

    @property
    def cgroup_headroom_bytes(self) -> int | None:
        raw_headroom = self.cgroup_raw_headroom_bytes
        if raw_headroom is None or self.cgroup_max_bytes is None:
            return None
        reclaimable = max(0, self.cgroup_reclaimable_bytes or 0)
        return min(self.cgroup_max_bytes, raw_headroom + reclaimable)

    @property
    def metrics_available(self) -> bool:
        return (
            self.host_available_bytes is not None
            or self.cgroup_headroom_bytes is not None
        )


def _read_nonnegative_int(path: Path) -> int | None:
    try:
        value = int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None
    return value if value >= 0 else None


def _read_host_available_bytes() -> int | None:
    try:
        lines = Path("/proc/meminfo").read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for line in lines:
        if not line.startswith("MemAvailable:"):
            continue
        fields = line.split()
        if len(fields) < 2:
            return None
        try:
            kib = int(fields[1])
        except ValueError:
            return None
        return kib * 1024 if kib >= 0 else None
    return None


def _read_cgroup_reclaimable_bytes(cgroup_dir: Path) -> int | None:
    """Read cache classes the kernel can reclaim under cgroup pressure."""

    try:
        lines = (cgroup_dir / "memory.stat").read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    values: dict[str, int] = {}
    for line in lines:
        fields = line.split()
        if len(fields) != 2 or fields[0] not in {"inactive_file", "slab_reclaimable"}:
            continue
        try:
            value = int(fields[1])
        except ValueError:
            continue
        if value >= 0:
            values[fields[0]] = value
    if not values:
        return None
    return values.get("inactive_file", 0) + values.get("slab_reclaimable", 0)


def _cgroup_v2_directory() -> Path | None:
    root = Path("/sys/fs/cgroup")
    if (root / "memory.current").is_file():
        return root
    try:
        lines = Path("/proc/self/cgroup").read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for line in lines:
        if not line.startswith("0::"):
            continue
        relative = line.partition("::")[2].lstrip("/")
        candidate = root / relative
        if (candidate / "memory.current").is_file():
            return candidate
    return None


def read_agent_resource_snapshot() -> AgentResourceSnapshot:
    """Read host and cgroup v2 memory without inspecting process env or argv."""

    current: int | None = None
    maximum: int | None = None
    reclaimable: int | None = None
    cgroup_dir = _cgroup_v2_directory()
    if cgroup_dir is not None:
        current = _read_nonnegative_int(cgroup_dir / "memory.current")
        reclaimable = _read_cgroup_reclaimable_bytes(cgroup_dir)
        try:
            raw_max = (cgroup_dir / "memory.max").read_text(encoding="utf-8").strip()
        except OSError:
            raw_max = ""
        if raw_max and raw_max != "max":
            try:
                parsed_max = int(raw_max)
            except ValueError:
                parsed_max = -1
            if parsed_max >= 0:
                maximum = parsed_max
    return AgentResourceSnapshot(
        host_available_bytes=_read_host_available_bytes(),
        cgroup_current_bytes=current,
        cgroup_max_bytes=maximum,
        cgroup_reclaimable_bytes=reclaimable,
    )


class ClaudeAgentAdmissionError(RuntimeError):
    """Retryable business failure raised before spawning a Claude process tree."""

    def __init__(
        self,
        message: str,
        *,
        code: str,
        retry_after_seconds: int,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = True
        self.retry_after_seconds = retry_after_seconds


class AgentAdmissionLease:
    """Idempotent lease released after normal, cancelled, or failed turns."""

    def __init__(
        self,
        session_id: str,
        release: Callable[[str], None],
    ) -> None:
        self.session_id = session_id
        self._release = release
        self._released = False

    def release(self) -> None:
        if self._released:
            return
        self._released = True
        self._release(self.session_id)


class ClaudeAgentAdmissionController:
    """Admit turns from live memory signals and a process-local concurrency cap."""

    def __init__(
        self,
        config: AgentAdmissionConfig | None = None,
        *,
        snapshot_provider: Callable[[], AgentResourceSnapshot] | None = None,
    ) -> None:
        self.config = config or AgentAdmissionConfig.from_env()
        self._snapshot_provider = snapshot_provider or read_agent_resource_snapshot
        self._active_session_ids: set[str] = set()
        self._last_snapshot = AgentResourceSnapshot()
        self._capacity_denials = 0
        self._memory_denials = 0
        self._missing_metrics_logged = False

    def replace_config(self, config: AgentAdmissionConfig) -> AgentAdmissionConfig:
        """Atomically replace immutable limits used by subsequent acquisitions.

        Existing leases are deliberately untouched. The resource-policy provider
        owns the narrower Admin bounds; this public runtime boundary preserves the
        original AgentAdmissionConfig minima for backwards-compatible callers.
        """

        if not isinstance(config, AgentAdmissionConfig):
            raise TypeError("config must be an AgentAdmissionConfig")
        values = (
            config.max_concurrent_runs,
            config.run_memory_budget_mib,
            config.memory_reserve_mib,
            config.retry_after_seconds,
        )
        if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
            raise ValueError("config values must be integers")
        if (
            config.max_concurrent_runs < 1
            or config.run_memory_budget_mib < 1
            or config.memory_reserve_mib < 0
            or config.retry_after_seconds < 1
        ):
            raise ValueError("config values are outside Agent admission bounds")
        previous = self.config
        self.config = config
        return previous

    def try_acquire(self, session_id: str) -> AgentAdmissionLease:
        active = len(self._active_session_ids)
        if active >= self.config.max_concurrent_runs:
            self._capacity_denials += 1
            logger.warning(
                "Claude Agent admission denied: code=%s active_runs=%d max_runs=%d",
                "CLAUDE_AGENT_CAPACITY_EXHAUSTED",
                active,
                self.config.max_concurrent_runs,
            )
            raise ClaudeAgentAdmissionError(
                "已有 Claude 对话正在运行，请稍后重试。",
                code="CLAUDE_AGENT_CAPACITY_EXHAUSTED",
                retry_after_seconds=self.config.retry_after_seconds,
            )

        snapshot = self._snapshot_provider()
        self._last_snapshot = snapshot
        required = self.config.required_headroom_bytes
        low_host = (
            snapshot.host_available_bytes is not None
            and snapshot.host_available_bytes < required
        )
        cgroup_headroom = snapshot.cgroup_headroom_bytes
        low_cgroup = cgroup_headroom is not None and cgroup_headroom < required
        if low_host or low_cgroup:
            self._memory_denials += 1
            logger.warning(
                "Claude Agent admission denied: code=%s required_bytes=%d "
                "host_available_bytes=%s cgroup_raw_headroom_bytes=%s "
                "cgroup_reclaimable_bytes=%s cgroup_headroom_bytes=%s",
                "CLAUDE_AGENT_MEMORY_PRESSURE",
                required,
                snapshot.host_available_bytes,
                snapshot.cgroup_raw_headroom_bytes,
                snapshot.cgroup_reclaimable_bytes,
                cgroup_headroom,
            )
            raise ClaudeAgentAdmissionError(
                "服务器资源暂时不足，未启动 Claude 进程，请稍后重试。",
                code="CLAUDE_AGENT_MEMORY_PRESSURE",
                retry_after_seconds=self.config.retry_after_seconds,
            )
        if not snapshot.metrics_available and not self._missing_metrics_logged:
            self._missing_metrics_logged = True
            logger.warning(
                "Claude Agent memory metrics unavailable; retaining concurrency-only admission"
            )

        self._active_session_ids.add(session_id)
        logger.info(
            "Claude Agent admission granted: active_runs=%d max_runs=%d",
            len(self._active_session_ids),
            self.config.max_concurrent_runs,
        )
        return AgentAdmissionLease(session_id, self._release)

    def _release(self, session_id: str) -> None:
        if session_id not in self._active_session_ids:
            return
        self._active_session_ids.remove(session_id)
        logger.info(
            "Claude Agent admission released: active_runs=%d max_runs=%d",
            len(self._active_session_ids),
            self.config.max_concurrent_runs,
        )

    def stats(self) -> dict[str, Any]:
        snapshot = self._last_snapshot
        cgroup_headroom = snapshot.cgroup_headroom_bytes
        return {
            "active_runs": len(self._active_session_ids),
            "max_concurrent_runs": self.config.max_concurrent_runs,
            "run_memory_budget_mib": self.config.run_memory_budget_mib,
            "memory_reserve_mib": self.config.memory_reserve_mib,
            "host_available_mib": (
                snapshot.host_available_bytes // _MIB
                if snapshot.host_available_bytes is not None
                else None
            ),
            "cgroup_headroom_mib": (
                cgroup_headroom // _MIB if cgroup_headroom is not None else None
            ),
            "cgroup_raw_headroom_mib": (
                snapshot.cgroup_raw_headroom_bytes // _MIB
                if snapshot.cgroup_raw_headroom_bytes is not None
                else None
            ),
            "cgroup_reclaimable_mib": (
                snapshot.cgroup_reclaimable_bytes // _MIB
                if snapshot.cgroup_reclaimable_bytes is not None
                else None
            ),
            "capacity_denials": self._capacity_denials,
            "memory_denials": self._memory_denials,
            "metrics_available": snapshot.metrics_available,
        }


__all__ = [
    "AgentAdmissionConfig",
    "AgentAdmissionLease",
    "AgentResourceSnapshot",
    "ClaudeAgentAdmissionController",
    "ClaudeAgentAdmissionError",
    "read_agent_resource_snapshot",
]
