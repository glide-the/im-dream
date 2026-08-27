# [Input] Consume public admission snapshots/stats, resource Observer counters, startup policy provenance,
#         Linux cgroup v2 `/proc` data, and safe publisher health counters.
# [Output] Provide an isolated sampler and the strict PostgreSQL resource snapshot JSON DTO.
# [Pos] Read-only Claude Agent resource diagnostics node; it never affects admission or Agent execution.
# [Sync] 2026-08-27: align producer-side timestamp, range, and literal validation with the Admin consumer contract.

"""Safe process-local diagnostics for Claude Agent resource admission."""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from claude_agent.admission import (
    AgentAdmissionConfig,
    AgentResourceSnapshot,
    read_agent_resource_snapshot,
)
from claude_agent.resource_observer import (
    ClaudeAgentResourceObserver,
    ObservedClaudeAgentAdmissionController,
)
from claude_agent.resource_policy import ResourcePolicyLoadResult, ResourcePolicyStatus
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, NonNegativeInt, PositiveInt

_SAMPLE_INTERVAL_SECONDS = 5.0
_SAMPLE_TIMEOUT_SECONDS = 1.0
_STALE_AFTER_SECONDS = 15.0
_CGROUP_ROOT = Path("/sys/fs/cgroup")
_PROC_ROOT = Path("/proc")
_CLAUDE_EXECUTABLE_NAMES = ("ink-claude-code-dream", "claude")
_MEMORY_EVENT_FIELDS = ("low", "high", "max", "oom", "oom_kill")


def _utc_now_text() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class ClaudeProcessSnapshot:
    available: bool
    count: int | None = None
    total_rss_bytes: int | None = None


@dataclass(frozen=True, slots=True)
class CgroupDetailSnapshot:
    inactive_file_bytes: int | None = None
    slab_reclaimable_bytes: int | None = None
    event_low: int | None = None
    event_high: int | None = None
    event_max: int | None = None
    event_oom: int | None = None
    event_oom_kill: int | None = None


@dataclass(frozen=True, slots=True)
class ResourceSample:
    memory: AgentResourceSnapshot
    claude_processes: ClaudeProcessSnapshot
    cgroup_details: CgroupDetailSnapshot = CgroupDetailSnapshot()

    @property
    def metrics_available(self) -> bool:
        return self.memory.metrics_available or self.claude_processes.available


@dataclass(frozen=True, slots=True)
class ResourcePipelineSnapshot:
    queue_dropped_total: int = 0
    write_errors_total: int = 0
    last_write_error_at: str | None = None


class ResourceSamplerSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    status: Literal["starting", "ok", "unavailable", "timeout", "error"]
    sampled_at: str | None
    stale: bool
    error_code: str | None
    sample: ResourceSample | None


def _read_proc_status(path: Path) -> tuple[int, int] | None:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    parent_pid: int | None = None
    rss_kib = 0
    for line in lines:
        if line.startswith("PPid:"):
            try:
                parent_pid = int(line.split()[1])
            except (IndexError, ValueError):
                return None
        elif line.startswith("VmRSS:"):
            try:
                rss_kib = max(0, int(line.split()[1]))
            except (IndexError, ValueError):
                rss_kib = 0
    if parent_pid is None:
        return None
    return parent_pid, rss_kib * 1024


def read_claude_process_snapshot(
    *,
    proc_root: Path,
    backend_pid: int,
    executable_names: frozenset[str] | set[str] | tuple[str, ...],
) -> ClaudeProcessSnapshot:
    """Aggregate backend descendants by executable identity without reading argv."""

    if not proc_root.is_dir():
        return ClaudeProcessSnapshot(available=False)
    if _read_proc_status(proc_root / str(backend_pid) / "status") is None:
        return ClaudeProcessSnapshot(available=False)
    process_rows: dict[int, tuple[int, int, str | None]] = {}
    try:
        entries = list(proc_root.iterdir())
    except OSError:
        return ClaudeProcessSnapshot(available=False)
    for entry in entries:
        if not entry.name.isdigit() or not entry.is_dir():
            continue
        status = _read_proc_status(entry / "status")
        if status is None:
            continue
        parent_pid, rss_bytes = status
        executable_name: str | None = None
        try:
            executable_name = Path(os.readlink(entry / "exe")).name
        except OSError:
            pass
        process_rows[int(entry.name)] = (parent_pid, rss_bytes, executable_name)

    children: dict[int, list[int]] = {}
    for pid, (parent_pid, _rss, _exe) in process_rows.items():
        children.setdefault(parent_pid, []).append(pid)
    descendants: set[int] = set()
    pending = list(children.get(backend_pid, ()))
    while pending:
        pid = pending.pop()
        if pid in descendants:
            continue
        descendants.add(pid)
        pending.extend(children.get(pid, ()))

    accepted_names = frozenset(executable_names)
    matched = [
        process_rows[pid]
        for pid in descendants
        if process_rows[pid][2] in accepted_names
    ]
    return ClaudeProcessSnapshot(
        available=True,
        count=len(matched),
        total_rss_bytes=sum(row[1] for row in matched),
    )


def _resolve_cgroup_v2_directory(*, proc_root: Path, cgroup_root: Path) -> Path | None:
    if (cgroup_root / "memory.current").is_file():
        return cgroup_root
    try:
        lines = (proc_root / "self" / "cgroup").read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for line in lines:
        if not line.startswith("0::"):
            continue
        relative = line.partition("::")[2].lstrip("/")
        candidate = cgroup_root / relative
        if (candidate / "memory.current").is_file():
            return candidate
    return None


def _nonnegative_fields(path: Path, accepted: tuple[str, ...]) -> dict[str, int]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}
    values: dict[str, int] = {}
    for line in lines:
        fields = line.split()
        if len(fields) != 2 or fields[0] not in accepted:
            continue
        try:
            parsed = int(fields[1])
        except ValueError:
            continue
        if parsed >= 0:
            values[fields[0]] = parsed
    return values


def read_cgroup_detail_snapshot(cgroup_dir: Path | None) -> CgroupDetailSnapshot:
    """Read diagnostics-only cgroup fields without extending admission state."""

    if cgroup_dir is None:
        return CgroupDetailSnapshot()
    stats = _nonnegative_fields(
        cgroup_dir / "memory.stat",
        ("inactive_file", "slab_reclaimable"),
    )
    events = _nonnegative_fields(cgroup_dir / "memory.events", _MEMORY_EVENT_FIELDS)
    return CgroupDetailSnapshot(
        inactive_file_bytes=stats.get("inactive_file"),
        slab_reclaimable_bytes=stats.get("slab_reclaimable"),
        event_low=events.get("low"),
        event_high=events.get("high"),
        event_max=events.get("max"),
        event_oom=events.get("oom"),
        event_oom_kill=events.get("oom_kill"),
    )


class ClaudeAgentResourceSampler:
    """Sample Linux metrics off-path with timeout, staleness, and error isolation."""

    def __init__(
        self,
        *,
        proc_root: Path = _PROC_ROOT,
        cgroup_root: Path = _CGROUP_ROOT,
        cgroup_dir: Path | None = None,
        backend_pid: int | None = None,
        claude_executable_names: tuple[str, ...] = _CLAUDE_EXECUTABLE_NAMES,
        interval_seconds: float = _SAMPLE_INTERVAL_SECONDS,
        timeout_seconds: float = _SAMPLE_TIMEOUT_SECONDS,
        stale_after_seconds: float = _STALE_AFTER_SECONDS,
        memory_snapshot_provider: Callable[[], AgentResourceSnapshot] = read_agent_resource_snapshot,
    ) -> None:
        self._proc_root = proc_root
        self._cgroup_dir = cgroup_dir or _resolve_cgroup_v2_directory(
            proc_root=proc_root,
            cgroup_root=cgroup_root,
        )
        self._backend_pid = backend_pid or os.getpid()
        self._claude_executable_names = frozenset(claude_executable_names)
        self._memory_snapshot_provider = memory_snapshot_provider
        self._interval_seconds = max(0.01, float(interval_seconds))
        self._timeout_seconds = max(0.05, float(timeout_seconds))
        self._stale_after_seconds = max(self._interval_seconds, float(stale_after_seconds))
        self._status: Literal["starting", "ok", "unavailable", "timeout", "error"] = "starting"
        self._sampled_at: str | None = None
        self._sampled_monotonic: float | None = None
        self._error_code: str | None = None
        self._sample: ResourceSample | None = None
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run(), name="claude-agent-resource-sampler")

    async def stop(self) -> None:
        task = self._task
        self._task = None
        if task is None or task.done():
            return
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    async def _run(self) -> None:
        while True:
            try:
                await self.sample_once()
                await asyncio.sleep(self._interval_seconds)
            except asyncio.CancelledError:
                raise
            except Exception:
                self._status = "error"
                self._error_code = "sample_loop_error"
                await asyncio.sleep(self._interval_seconds)

    async def sample_once(self) -> None:
        try:
            sample = await asyncio.wait_for(
                asyncio.to_thread(self._sample_sync),
                timeout=self._timeout_seconds,
            )
        except asyncio.TimeoutError:
            self._status = "timeout"
            self._error_code = "sample_timeout"
            return
        except Exception:
            self._status = "error"
            self._error_code = "sample_error"
            return
        self._sample = sample
        self._sampled_at = _utc_now_text()
        self._sampled_monotonic = time.monotonic()
        self._error_code = None if sample.metrics_available else "metrics_unavailable"
        self._status = "ok" if sample.metrics_available else "unavailable"

    def _sample_sync(self) -> ResourceSample:
        return ResourceSample(
            memory=self._memory_snapshot_provider(),
            cgroup_details=read_cgroup_detail_snapshot(self._cgroup_dir),
            claude_processes=read_claude_process_snapshot(
                proc_root=self._proc_root,
                backend_pid=self._backend_pid,
                executable_names=self._claude_executable_names,
            ),
        )

    def snapshot(self) -> ResourceSamplerSnapshot:
        age: float | None = None
        if self._sampled_monotonic is not None:
            age = max(0.0, time.monotonic() - self._sampled_monotonic)
        return ResourceSamplerSnapshot(
            status=self._status,
            sampled_at=self._sampled_at,
            stale=age is None or age > self._stale_after_seconds,
            error_code=self._error_code,
            sample=self._sample,
        )


class AdmissionConfigValues(BaseModel):
    model_config = ConfigDict(extra="forbid")
    max_concurrent_runs: PositiveInt
    run_memory_budget_mib: NonNegativeInt
    memory_reserve_mib: NonNegativeInt
    retry_after_seconds: NonNegativeInt
    required_headroom_bytes: NonNegativeInt


class ResourceConfigDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    defaults: AdmissionConfigValues
    effective: AdmissionConfigValues
    effective_version: str = Field(min_length=1, max_length=128)
    loaded_at: AwareDatetime
    policy_status: ResourcePolicyStatus
    policy_revision: PositiveInt | None
    policy_updated_at: AwareDatetime | None


class ResourceScopeDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    active_runs: Literal["process"] = "process"
    counters: Literal["process_lifetime"] = "process_lifetime"
    reset_on_restart: Literal[True] = True


class ResourceTurnsDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    started_total: NonNegativeInt
    completed_total: NonNegativeInt
    failed_total: NonNegativeInt
    cancelled_total: NonNegativeInt


class ResourceAdmissionDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    active_runs: NonNegativeInt
    max_concurrent_runs: PositiveInt
    granted_total: NonNegativeInt
    capacity_denials_total: NonNegativeInt
    memory_pressure_denials_total: NonNegativeInt
    last_denial_type: Literal["capacity", "memory_pressure"] | None
    last_denial_at: AwareDatetime | None
    can_start_new_agent: bool | None


class ClaudeProcessesDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    available: bool
    count: NonNegativeInt | None
    total_rss_bytes: NonNegativeInt | None


class CgroupMemoryEventsDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    low: NonNegativeInt | None
    high: NonNegativeInt | None
    max: NonNegativeInt | None
    oom: NonNegativeInt | None
    oom_kill: NonNegativeInt | None


class ResourceMemoryDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    host_available_bytes: NonNegativeInt | None
    cgroup_current_bytes: NonNegativeInt | None
    cgroup_max_bytes: NonNegativeInt | None
    cgroup_raw_headroom_bytes: NonNegativeInt | None
    inactive_file_bytes: NonNegativeInt | None
    slab_reclaimable_bytes: NonNegativeInt | None
    cgroup_reclaimable_bytes: NonNegativeInt | None
    cgroup_effective_headroom_bytes: NonNegativeInt | None
    required_headroom_bytes: NonNegativeInt
    events: CgroupMemoryEventsDTO


class ResourceSampleDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["starting", "ok", "unavailable", "timeout", "error"]
    sampled_at: AwareDatetime | None
    stale: bool
    error_code: str | None = Field(default=None, min_length=1, max_length=160)


class ResourcePipelineDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    queue_dropped_total: NonNegativeInt
    write_errors_total: NonNegativeInt
    last_write_error_at: AwareDatetime | None


class ClaudeAgentResourceDiagnosticsDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    backend_status: Literal["ok"] = "ok"
    scope: ResourceScopeDTO
    config: ResourceConfigDTO
    turns: ResourceTurnsDTO
    admission: ResourceAdmissionDTO
    claude_processes: ClaudeProcessesDTO
    memory: ResourceMemoryDTO
    sample: ResourceSampleDTO
    pipeline: ResourcePipelineDTO


def _config_values(config: AgentAdmissionConfig) -> AdmissionConfigValues:
    return AdmissionConfigValues(
        max_concurrent_runs=config.max_concurrent_runs,
        run_memory_budget_mib=config.run_memory_budget_mib,
        memory_reserve_mib=config.memory_reserve_mib,
        retry_after_seconds=config.retry_after_seconds,
        required_headroom_bytes=config.required_headroom_bytes,
    )


class ClaudeAgentResourceDiagnostics:
    """Project public Observer/admission/sampler state into one strict DTO."""

    def __init__(
        self,
        *,
        admission: ObservedClaudeAgentAdmissionController,
        observer: ClaudeAgentResourceObserver,
        sampler: ClaudeAgentResourceSampler,
        policy: ResourcePolicyLoadResult,
        pipeline_snapshot: Callable[[], ResourcePipelineSnapshot] = ResourcePipelineSnapshot,
    ) -> None:
        self._admission = admission
        self._observer = observer
        self._sampler = sampler
        self._policy = policy
        self._pipeline_snapshot = pipeline_snapshot
        encoded = json.dumps(
            _config_values(admission.config).model_dump(),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        self._effective_version = hashlib.sha256(encoded).hexdigest()

    def snapshot(self) -> ClaudeAgentResourceDiagnosticsDTO:
        counters = self._observer.snapshot()
        admission_stats = self._admission.stats()
        sampler_snapshot = self._sampler.snapshot()
        sampled = sampler_snapshot.sample
        memory = sampled.memory if sampled is not None else AgentResourceSnapshot()
        details = sampled.cgroup_details if sampled is not None else CgroupDetailSnapshot()
        processes = sampled.claude_processes if sampled is not None else ClaudeProcessSnapshot(False)
        required = self._admission.config.required_headroom_bytes
        capacity_available = int(admission_stats.get("active_runs", 0)) < self._admission.config.max_concurrent_runs
        host_sufficient = memory.host_available_bytes is None or memory.host_available_bytes >= required
        cgroup_sufficient = memory.cgroup_headroom_bytes is None or memory.cgroup_headroom_bytes >= required
        if sampler_snapshot.stale or sampler_snapshot.status in {"starting", "timeout", "error"}:
            can_start: bool | None = None
        else:
            can_start = capacity_available and host_sufficient and cgroup_sufficient
        pipeline = self._pipeline_snapshot()
        return ClaudeAgentResourceDiagnosticsDTO(
            scope=ResourceScopeDTO(),
            config=ResourceConfigDTO(
                defaults=_config_values(self._policy.defaults),
                effective=_config_values(self._admission.config),
                effective_version=self._effective_version,
                loaded_at=self._policy.loaded_at,
                policy_status=self._policy.status,
                policy_revision=self._policy.revision,
                policy_updated_at=self._policy.updated_at,
            ),
            turns=ResourceTurnsDTO(
                started_total=counters.turn_started_total,
                completed_total=counters.turn_completed_total,
                failed_total=counters.turn_failed_total,
                cancelled_total=counters.turn_cancelled_total,
            ),
            admission=ResourceAdmissionDTO(
                active_runs=int(admission_stats.get("active_runs", 0)),
                max_concurrent_runs=self._admission.config.max_concurrent_runs,
                granted_total=counters.admission_granted_total,
                capacity_denials_total=counters.capacity_denials_total,
                memory_pressure_denials_total=counters.memory_pressure_denials_total,
                last_denial_type=counters.last_denial_type,
                last_denial_at=counters.last_denial_at,
                can_start_new_agent=can_start,
            ),
            claude_processes=ClaudeProcessesDTO(
                available=processes.available,
                count=processes.count,
                total_rss_bytes=processes.total_rss_bytes,
            ),
            memory=ResourceMemoryDTO(
                host_available_bytes=memory.host_available_bytes,
                cgroup_current_bytes=memory.cgroup_current_bytes,
                cgroup_max_bytes=memory.cgroup_max_bytes,
                cgroup_raw_headroom_bytes=memory.cgroup_raw_headroom_bytes,
                inactive_file_bytes=details.inactive_file_bytes,
                slab_reclaimable_bytes=details.slab_reclaimable_bytes,
                cgroup_reclaimable_bytes=memory.cgroup_reclaimable_bytes,
                cgroup_effective_headroom_bytes=memory.cgroup_headroom_bytes,
                required_headroom_bytes=required,
                events=CgroupMemoryEventsDTO(
                    low=details.event_low,
                    high=details.event_high,
                    max=details.event_max,
                    oom=details.event_oom,
                    oom_kill=details.event_oom_kill,
                ),
            ),
            sample=ResourceSampleDTO(
                status=sampler_snapshot.status,
                sampled_at=sampler_snapshot.sampled_at,
                stale=sampler_snapshot.stale,
                error_code=sampler_snapshot.error_code,
            ),
            pipeline=ResourcePipelineDTO(
                queue_dropped_total=pipeline.queue_dropped_total,
                write_errors_total=pipeline.write_errors_total,
                last_write_error_at=pipeline.last_write_error_at,
            ),
        )


__all__ = [
    "CgroupDetailSnapshot",
    "ClaudeAgentResourceDiagnostics",
    "ClaudeAgentResourceDiagnosticsDTO",
    "ClaudeAgentResourceSampler",
    "ClaudeProcessSnapshot",
    "ResourcePipelineSnapshot",
    "ResourceSample",
    "read_cgroup_detail_snapshot",
    "read_claude_process_snapshot",
]
