# [Input] Consume public admission config/snapshots, resource Observer counters, Linux cgroup v2,
#         and `/proc` status/executable metadata without reading process command lines.
# [Output] Provide an isolated sampler and an explicit, credential-free diagnostics DTO.
# [Pos] Read-only resource diagnostics node in backend/claude_agent.
# [Sync] 2026-08-27: add bounded Linux sampling, staleness, and process-scoped DTO projection.

"""Safe process-local diagnostics for Claude Agent resource admission."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from claude_agent.admission import (
    AgentAdmissionConfig,
    AgentResourceSnapshot,
    read_agent_resource_snapshot,
)
from claude_agent.resource_observer import (
    ClaudeAgentResourceObserver,
    ObservedClaudeAgentAdmissionController,
)


_MIB = 1024 * 1024
_SAMPLE_INTERVAL_SECONDS = 5.0
_SAMPLE_TIMEOUT_SECONDS = 1.0
_STALE_AFTER_SECONDS = 15.0
_CONFIG_ENV_NAMES = {
    "max_concurrent_runs": "INK_AGENT_MAX_CONCURRENT_RUNS",
    "run_memory_budget_mib": "INK_AGENT_RUN_MEMORY_BUDGET_MIB",
    "memory_reserve_mib": "INK_AGENT_MEMORY_RESERVE_MIB",
    "retry_after_seconds": "INK_AGENT_SWEEP_INTERVAL_S",
}


def _utc_now_text() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class ClaudeProcessSnapshot:
    available: bool
    count: int | None = None
    total_rss_bytes: int | None = None


@dataclass(frozen=True, slots=True)
class ResourceSample:
    memory: AgentResourceSnapshot
    claude_processes: ClaudeProcessSnapshot

    @property
    def metrics_available(self) -> bool:
        return self.memory.metrics_available or self.claude_processes.available


class ResourceSamplerSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["starting", "ok", "unavailable", "timeout", "error"]
    sampled_at: str | None
    age_seconds: float | None
    stale: bool
    error_code: str | None
    sample: ResourceSample | None


class ClaudeAgentResourceSampler:
    """Sample Linux metrics off-path with timeout and error isolation."""

    def __init__(
        self,
        *,
        proc_root: Path = Path("/proc"),
        backend_pid: int | None = None,
        claude_executable_names: tuple[str, ...] = ("ink-claude-code-dream", "claude"),
        interval_seconds: float = _SAMPLE_INTERVAL_SECONDS,
        timeout_seconds: float = _SAMPLE_TIMEOUT_SECONDS,
        stale_after_seconds: float = _STALE_AFTER_SECONDS,
    ) -> None:
        self._proc_root = proc_root
        self._backend_pid = backend_pid or os.getpid()
        self._claude_executable_names = frozenset(claude_executable_names)
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
            self._task = asyncio.create_task(
                self._run(),
                name="claude-agent-resource-sampler",
            )

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
            memory=read_agent_resource_snapshot(),
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
        stale = age is None or age > self._stale_after_seconds
        return ResourceSamplerSnapshot(
            status=self._status,
            sampled_at=self._sampled_at,
            age_seconds=round(age, 3) if age is not None else None,
            stale=stale,
            error_code=self._error_code,
            sample=self._sample,
        )


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
    """Aggregate direct/indirect backend descendants by executable identity."""

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


class AdmissionConfigValues(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_concurrent_runs: int
    run_memory_budget_mib: int
    memory_reserve_mib: int
    retry_after_seconds: int
    required_headroom_bytes: int


class AdmissionEnvironmentValues(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_concurrent_runs: int | None
    run_memory_budget_mib: int | None
    memory_reserve_mib: int | None
    retry_after_seconds: int | None


class ResourceConfigDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    defaults: AdmissionConfigValues
    environment: AdmissionEnvironmentValues
    effective: AdmissionConfigValues
    effective_version: str
    loaded_at: str
    restart_required: bool


class ResourceScopeDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    active_runs: Literal["process"] = "process"
    counters: Literal["process_lifetime"] = "process_lifetime"
    reset_on_restart: bool = True


class ResourceTurnsDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    started_total: int
    completed_total: int
    failed_total: int
    cancelled_total: int


class ResourceAdmissionDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    active_runs: int
    max_concurrent_runs: int
    granted_total: int
    capacity_denials_total: int
    memory_pressure_denials_total: int
    last_denial_type: Literal["capacity", "memory_pressure"] | None
    last_denial_at: str | None
    can_start_new_agent: bool


class ClaudeProcessesDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    available: bool
    count: int | None
    total_rss_bytes: int | None


class CgroupMemoryEventsDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    low: int | None
    high: int | None
    max: int | None
    oom: int | None
    oom_kill: int | None


class ResourceMemoryDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    host_available_bytes: int | None
    cgroup_current_bytes: int | None
    cgroup_max_bytes: int | None
    cgroup_raw_headroom_bytes: int | None
    inactive_file_bytes: int | None
    slab_reclaimable_bytes: int | None
    cgroup_reclaimable_bytes: int | None
    cgroup_effective_headroom_bytes: int | None
    required_headroom_bytes: int
    events: CgroupMemoryEventsDTO


class ResourceSampleDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["starting", "ok", "unavailable", "timeout", "error"]
    sampled_at: str | None
    age_seconds: float | None
    stale: bool
    error_code: str | None


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


def _config_values(config: AgentAdmissionConfig) -> AdmissionConfigValues:
    return AdmissionConfigValues(
        max_concurrent_runs=config.max_concurrent_runs,
        run_memory_budget_mib=config.run_memory_budget_mib,
        memory_reserve_mib=config.memory_reserve_mib,
        retry_after_seconds=config.retry_after_seconds,
        required_headroom_bytes=config.required_headroom_bytes,
    )


def _environment_values() -> AdmissionEnvironmentValues:
    values: dict[str, int | None] = {}
    for field, env_name in _CONFIG_ENV_NAMES.items():
        raw = os.getenv(env_name)
        try:
            values[field] = int(raw) if raw is not None and raw.strip() else None
        except ValueError:
            values[field] = None
    return AdmissionEnvironmentValues(**values)


class ClaudeAgentResourceDiagnostics:
    """Project Observer, admission, and sampler state into one closed DTO."""

    def __init__(
        self,
        *,
        admission: ObservedClaudeAgentAdmissionController,
        observer: ClaudeAgentResourceObserver,
        sampler: ClaudeAgentResourceSampler,
    ) -> None:
        self._admission = admission
        self._observer = observer
        self._sampler = sampler
        self._loaded_at = _utc_now_text()
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
        processes = (
            sampled.claude_processes
            if sampled is not None
            else ClaudeProcessSnapshot(available=False)
        )
        required = self._admission.config.required_headroom_bytes
        capacity_available = (
            int(admission_stats.get("active_runs", 0))
            < self._admission.config.max_concurrent_runs
        )
        host_sufficient = (
            memory.host_available_bytes is None
            or memory.host_available_bytes >= required
        )
        cgroup_sufficient = (
            memory.cgroup_headroom_bytes is None
            or memory.cgroup_headroom_bytes >= required
        )
        can_start = (
            capacity_available
            and host_sufficient
            and cgroup_sufficient
            and not sampler_snapshot.stale
        )
        environment = _environment_values()
        try:
            restart_required = AgentAdmissionConfig.from_env() != self._admission.config
        except ValueError:
            restart_required = True
        defaults = AgentAdmissionConfig.defaults()
        return ClaudeAgentResourceDiagnosticsDTO(
            scope=ResourceScopeDTO(),
            config=ResourceConfigDTO(
                defaults=_config_values(defaults),
                environment=environment,
                effective=_config_values(self._admission.config),
                effective_version=self._effective_version,
                loaded_at=self._loaded_at,
                restart_required=restart_required,
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
                inactive_file_bytes=memory.cgroup_inactive_file_bytes,
                slab_reclaimable_bytes=memory.cgroup_slab_reclaimable_bytes,
                cgroup_reclaimable_bytes=memory.cgroup_reclaimable_bytes,
                cgroup_effective_headroom_bytes=memory.cgroup_headroom_bytes,
                required_headroom_bytes=required,
                events=CgroupMemoryEventsDTO(
                    low=memory.cgroup_event_low,
                    high=memory.cgroup_event_high,
                    max=memory.cgroup_event_max,
                    oom=memory.cgroup_event_oom,
                    oom_kill=memory.cgroup_event_oom_kill,
                ),
            ),
            sample=ResourceSampleDTO(
                status=sampler_snapshot.status,
                sampled_at=sampler_snapshot.sampled_at,
                age_seconds=sampler_snapshot.age_seconds,
                stale=sampler_snapshot.stale,
                error_code=sampler_snapshot.error_code,
            ),
        )


__all__ = [
    "ClaudeAgentResourceDiagnostics",
    "ClaudeAgentResourceDiagnosticsDTO",
    "ClaudeAgentResourceSampler",
    "ClaudeProcessSnapshot",
    "ResourceSample",
    "read_claude_process_snapshot",
]
