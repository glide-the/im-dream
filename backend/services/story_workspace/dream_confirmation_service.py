"""Validate Dream files and deliver Admin-owned confirmation work to Runtime."""

# [Input] Registry120 confirmation DTOs, shared-file projection and same-Thread Runtime dispatcher.
# [Output] DB-free projection validation plus claim/lease/ack reconciliation through Admin.
# [Pos] Dream business orchestration; Admin owns all confirmation SQL, lifecycle and durable state.
# [Sync] 2026-09-16: replace PostgreSQL access with strict Admin DTO operations.

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import hashlib
import json
import logging
import math
import time
from typing import Any, Awaitable, Callable, Optional
from uuid import uuid4

try:
    from story_workspace.contracts import (
        STORY_WORKSPACE_DREAM_RELATIONS_MAX,
        STORY_WORKSPACE_DREAM_REQUIRED_STAGES,
        StoryWorkspaceDreamConfirmationAccepted,
        StoryWorkspaceDreamConfirmationCommand,
        StoryWorkspaceDreamFilesResponse,
    )
    from services.admin_data.story_workspace_confirmation_data import (
        AdminStoryWorkspaceConfirmationWorkerData,
        StoryWorkspaceConfirmationAckInputDTO,
        StoryWorkspaceConfirmationClaimInputDTO,
        StoryWorkspaceConfirmationDispatchDTO,
        StoryWorkspaceConfirmationLeaseInputDTO,
        StoryWorkspaceConfirmationMetadataDTO,
        StoryWorkspaceConfirmationSubmitOutputDTO,
        canonical_confirmation_command,
    )
    from services.story_workspace.dream_lifecycle_observer import drain_chat_agent_turn
except ModuleNotFoundError:  # Support repository-root package imports.
    from backend.story_workspace.contracts import (
        STORY_WORKSPACE_DREAM_RELATIONS_MAX,
        STORY_WORKSPACE_DREAM_REQUIRED_STAGES,
        StoryWorkspaceDreamConfirmationAccepted,
        StoryWorkspaceDreamConfirmationCommand,
        StoryWorkspaceDreamFilesResponse,
    )
    from backend.services.admin_data.story_workspace_confirmation_data import (
        AdminStoryWorkspaceConfirmationWorkerData,
        StoryWorkspaceConfirmationAckInputDTO,
        StoryWorkspaceConfirmationClaimInputDTO,
        StoryWorkspaceConfirmationDispatchDTO,
        StoryWorkspaceConfirmationLeaseInputDTO,
        StoryWorkspaceConfirmationMetadataDTO,
        StoryWorkspaceConfirmationSubmitOutputDTO,
        canonical_confirmation_command,
    )
    from backend.services.story_workspace.dream_lifecycle_observer import drain_chat_agent_turn


_logger = logging.getLogger(__name__)
STORY_WORKSPACE_DREAM_CONFIRMATION_METADATA_KIND = "story-workspace-dream-confirmation"
STORY_WORKSPACE_DREAM_CONFIRMATION_DISPATCH_PENDING = "pending"
STORY_WORKSPACE_DREAM_CONFIRMATION_DISPATCHING = "dispatching"
STORY_WORKSPACE_DREAM_CONFIRMATION_DISPATCHED = "dispatched"
_EDITABLE_FIELDS = frozenset({"displayName", "summary", "relations"})


class StoryWorkspaceDreamConfirmationError(RuntimeError):
    """Allowlisted public failure for the Dream confirmation boundary."""

    def __init__(self, code: str, status_code: int) -> None:
        super().__init__(code)
        self.code = code
        self.status_code = status_code


StoryWorkspaceDreamConfirmationDispatcher = Callable[
    [str, str, str, list, dict], Awaitable[bool]
]


@dataclass(frozen=True)
class StoryWorkspaceDreamConfirmationDispatch:
    thread_id: str
    actor_id: str
    message_id: str
    parts: list
    metadata: dict

    @classmethod
    def from_admin(
        cls, value: StoryWorkspaceConfirmationDispatchDTO
    ) -> "StoryWorkspaceDreamConfirmationDispatch":
        try:
            parts = json.loads(value.parts_json)
            metadata = StoryWorkspaceConfirmationMetadataDTO.model_validate_json(
                value.metadata_json
            ).model_dump(mode="json", exclude_none=True)
        except (TypeError, ValueError) as exc:
            raise StoryWorkspaceDreamConfirmationError(
                "DECK_RUNTIME_CONFIG_UNAVAILABLE", 503
            ) from exc
        if not isinstance(parts, list) or not isinstance(metadata, dict):
            raise StoryWorkspaceDreamConfirmationError(
                "DECK_RUNTIME_CONFIG_UNAVAILABLE", 503
            )
        return cls(value.thread_id, value.actor_id, value.message_id, parts, metadata)

    @property
    def claim_id(self) -> str:
        value = self.metadata.get("dispatch_claim_id")
        if not isinstance(value, str) or not value:
            raise StoryWorkspaceDreamConfirmationError(
                "DECK_RUNTIME_CONFIG_UNAVAILABLE", 503
            )
        return value


@dataclass(frozen=True)
class StoryWorkspacePersistedDreamConfirmation:
    accepted: StoryWorkspaceDreamConfirmationAccepted
    dispatch: Optional[StoryWorkspaceDreamConfirmationDispatch]


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"), sort_keys=True)


def _sha256(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def story_workspace_dream_confirmation_message_id(actor_id: str, run_id: str, idempotency_key: str) -> str:
    digest = hashlib.sha256(_canonical_json({
        "actor": str(actor_id), "storyWorkspaceRunId": run_id, "idempotencyKey": idempotency_key,
    }).encode("utf-8")).hexdigest()
    return f"dream_confirm_{digest}"


def story_workspace_confirmation_command_json(payload: StoryWorkspaceDreamConfirmationCommand) -> str:
    return canonical_confirmation_command(payload)


def story_workspace_confirmation_fingerprint(actor_id: str, payload: StoryWorkspaceDreamConfirmationCommand) -> str:
    return _sha256({"actor": str(actor_id), "command": payload.model_dump(mode="json", by_alias=True)})


def _validate_edit_value(field: str, value: Any) -> None:
    if field == "displayName":
        if not isinstance(value, str) or not value.strip() or len(value) > 200:
            raise StoryWorkspaceDreamConfirmationError("OUTPUT_CONTRACT_INVALID", 422)
        return
    if field == "summary":
        if value is not None and (not isinstance(value, str) or len(value) > 4000):
            raise StoryWorkspaceDreamConfirmationError("OUTPUT_CONTRACT_INVALID", 422)
        return
    if field == "relations":
        if not isinstance(value, list) or len(value) > STORY_WORKSPACE_DREAM_RELATIONS_MAX:
            raise StoryWorkspaceDreamConfirmationError("OUTPUT_CONTRACT_INVALID", 422)
        if any(not isinstance(item, str) or not item.strip() or len(item) > 128 for item in value):
            raise StoryWorkspaceDreamConfirmationError("OUTPUT_CONTRACT_INVALID", 422)
        return
    raise StoryWorkspaceDreamConfirmationError("OUTPUT_CONTRACT_INVALID", 422)


def story_workspace_validate_confirmation_projection(
    projection: StoryWorkspaceDreamFilesResponse,
    payload: StoryWorkspaceDreamConfirmationCommand,
) -> None:
    if projection.story_workspace_run_id != payload.story_workspace_run_id or projection.thread_id != payload.thread_id:
        raise StoryWorkspaceDreamConfirmationError("CONFIG_VERSION_DRIFT", 409)
    required = set(STORY_WORKSPACE_DREAM_REQUIRED_STAGES)
    if set(projection.stages) != required:
        raise StoryWorkspaceDreamConfirmationError("CONFIG_VERSION_DRIFT", 409)
    revisions = {stage: projection.stages[stage].revision for stage in required}
    if revisions != payload.base_revisions:
        raise StoryWorkspaceDreamConfirmationError("CONFIG_VERSION_DRIFT", 409)
    entity_ids = {stage: {item.entity_id for item in projection.stages[stage].items} for stage in required}
    for edit in payload.edits:
        if edit.entity_id not in entity_ids[edit.stage] or set(edit.fields) - _EDITABLE_FIELDS:
            raise StoryWorkspaceDreamConfirmationError("OUTPUT_CONTRACT_INVALID", 422)
        for field, value in edit.fields.items():
            _validate_edit_value(field, value)


def story_workspace_persisted_confirmation(
    result: StoryWorkspaceConfirmationSubmitOutputDTO,
) -> StoryWorkspacePersistedDreamConfirmation:
    accepted = StoryWorkspaceDreamConfirmationAccepted(
        message_id=result.message_id,
        story_workspace_run_id=result.story_workspace_run_id,
        thread_id=result.thread_id,
        status=result.status,
        replayed=result.replayed,
        dispatched=result.dispatched,
        request_id=result.request_id,
    )
    return StoryWorkspacePersistedDreamConfirmation(
        accepted=accepted,
        dispatch=None if result.dispatch is None else StoryWorkspaceDreamConfirmationDispatch.from_admin(result.dispatch),
    )


def story_workspace_build_dream_confirmation_turn_dispatcher(
    factory: Any | None = None,
    *,
    request_factory: Callable[..., Any] | None = None,
) -> StoryWorkspaceDreamConfirmationDispatcher:
    """Queue a resumed turn behind the existing per-Thread Runtime lock."""

    async def consume(thread_id: str, actor_id: str, message_id: str, parts: list, metadata: dict) -> bool:
        try:
            selected_factory = factory
            if selected_factory is None:
                from agent_factory import claude_agent_thread_factory
                selected_factory = claude_agent_thread_factory
            selected_request_factory = request_factory
            if selected_request_factory is None:
                from claude_agent.service import ClaudeAgentRunRequest
                selected_request_factory = ClaudeAgentRunRequest
            request = selected_request_factory(
                user_id=str(actor_id), thread_id=thread_id, resume=True,
                message_id=message_id, message_parts=parts, message_metadata=metadata,
                user_message_pre_persisted=True,
            )
            result = await drain_chat_agent_turn(selected_factory, request)
            return result.completed
        except asyncio.CancelledError:
            raise
        except Exception:
            _logger.exception("Dream confirmation turn failed for thread_id=%s message_id=%s", thread_id, message_id)
            return False

    def dispatch(thread_id: str, actor_id: str, message_id: str, parts: list, metadata: dict) -> Awaitable[bool]:
        return asyncio.create_task(
            consume(thread_id, actor_id, message_id, parts, metadata),
            name=f"dream-confirmation-turn-{message_id}",
        )
    return dispatch


@dataclass(frozen=True)
class _StoryWorkspaceDreamRetryState:
    failures: int
    not_before: float


class StoryWorkspaceDreamConfirmationCoordinator:
    """Drive Admin-owned durable claims through the existing Dream Runtime."""

    def __init__(
        self,
        worker: AdminStoryWorkspaceConfirmationWorkerData | None = None,
        *,
        dispatcher_factory: Callable[[], StoryWorkspaceDreamConfirmationDispatcher] = story_workspace_build_dream_confirmation_turn_dispatcher,
        reconcile_interval_s: float = 2.0,
        clock: Callable[[], float] = time.monotonic,
        lease_renew_interval_s: float = 30.0,
        claim_id_factory: Callable[[], str] = lambda: uuid4().hex,
        request_id_factory: Callable[[], str] = lambda: uuid4().hex,
        retry_base_s: float = 2.0,
        retry_max_s: float = 60.0,
    ) -> None:
        if not math.isfinite(reconcile_interval_s) or reconcile_interval_s <= 0:
            raise ValueError("reconcile_interval_s must be finite and positive")
        if not math.isfinite(lease_renew_interval_s) or lease_renew_interval_s <= 0:
            raise ValueError("lease_renew_interval_s must be finite and positive")
        self._worker = worker
        self._dispatcher_factory = dispatcher_factory
        self._reconcile_interval_s = float(reconcile_interval_s)
        self._clock = clock
        self._lease_renew_interval_s = float(lease_renew_interval_s)
        self._claim_id_factory = claim_id_factory
        self._request_id_factory = request_id_factory
        self._retry_base_s = max(float(retry_base_s), 0.01)
        self._retry_max_s = max(float(retry_max_s), self._retry_base_s)
        self._in_flight: dict[str, asyncio.Task[None]] = {}
        self._retry_state: dict[str, _StoryWorkspaceDreamRetryState] = {}
        self._loop_task: Optional[asyncio.Task[None]] = None
        self._stop_event: Optional[asyncio.Event] = None

    def bind_worker(self, worker: AdminStoryWorkspaceConfirmationWorkerData) -> None:
        if self._loop_task is not None and not self._loop_task.done():
            raise RuntimeError("Cannot replace a running confirmation worker")
        self._worker = worker

    def _require_worker(self) -> AdminStoryWorkspaceConfirmationWorkerData:
        if self._worker is None:
            raise StoryWorkspaceDreamConfirmationError("DECK_RUNTIME_CONFIG_UNAVAILABLE", 503)
        return self._worker

    def start(self) -> None:
        self._require_worker()
        if self._loop_task is not None and not self._loop_task.done():
            return
        self._stop_event = asyncio.Event()
        self._loop_task = asyncio.create_task(self._run(), name="dream-confirmation-reconciler")

    async def stop(self) -> None:
        if self._stop_event is not None:
            self._stop_event.set()
        if self._loop_task is not None and not self._loop_task.done():
            self._loop_task.cancel()
        tasks = list(self._in_flight.values())
        for task in tasks:
            task.cancel()
        if self._loop_task is not None:
            await asyncio.gather(self._loop_task, return_exceptions=True)
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._loop_task = None
        self._stop_event = None

    def _claim(self, message_id: str | None) -> StoryWorkspaceDreamConfirmationDispatch | None:
        result = self._require_worker().claim(
            StoryWorkspaceConfirmationClaimInputDTO(message_id=message_id, claim_id=self._claim_id_factory()),
            self._request_id_factory(),
        )
        return None if result.dispatch is None else StoryWorkspaceDreamConfirmationDispatch.from_admin(result.dispatch)

    def schedule(self, dispatch: Optional[StoryWorkspaceDreamConfirmationDispatch]) -> bool:
        if dispatch is None or dispatch.message_id in self._in_flight:
            return False
        retry = self._retry_state.get(dispatch.message_id)
        if retry is not None and self._clock() < retry.not_before:
            return False
        return self._schedule_claimed(self._claim(dispatch.message_id))

    def _schedule_claimed(self, claimed: StoryWorkspaceDreamConfirmationDispatch | None) -> bool:
        if claimed is None or claimed.message_id in self._in_flight:
            return False
        retry = self._retry_state.get(claimed.message_id)
        if retry is not None and self._clock() < retry.not_before:
            self._set_claim_lease(claimed, max(retry.not_before - self._clock(), 0.0))
            return False
        task = asyncio.create_task(self._consume_and_ack(claimed), name=f"dream-confirmation-{claimed.message_id}")
        self._in_flight[claimed.message_id] = task
        return True

    async def reconcile_once(self) -> int:
        scheduled = 0
        while True:
            claimed = await asyncio.to_thread(self._claim, None)
            if claimed is None:
                return scheduled
            scheduled += int(self._schedule_claimed(claimed))

    async def wait_for_idle(self) -> None:
        while self._in_flight:
            await asyncio.gather(*list(self._in_flight.values()), return_exceptions=True)

    def _set_claim_lease(self, dispatch: StoryWorkspaceDreamConfirmationDispatch, duration_seconds: float | None) -> bool:
        result = self._require_worker().lease(
            StoryWorkspaceConfirmationLeaseInputDTO(
                message_id=dispatch.message_id, claim_id=dispatch.claim_id, duration_seconds=duration_seconds,
            ),
            self._request_id_factory(),
        )
        return result.renewed

    def _mark_dispatched(self, dispatch: StoryWorkspaceDreamConfirmationDispatch) -> bool:
        result = self._require_worker().ack(
            StoryWorkspaceConfirmationAckInputDTO(message_id=dispatch.message_id, claim_id=dispatch.claim_id),
            self._request_id_factory(),
        )
        return result.acked

    def _record_retry(self, message_id: str) -> float:
        previous = self._retry_state.get(message_id)
        failures = 1 if previous is None else previous.failures + 1
        delay = min(self._retry_max_s, self._retry_base_s * (2 ** min(failures - 1, 30)))
        self._retry_state[message_id] = _StoryWorkspaceDreamRetryState(failures, self._clock() + delay)
        return delay

    async def _defer_owned_claim(self, dispatch: StoryWorkspaceDreamConfirmationDispatch, delay_s: float) -> None:
        try:
            await asyncio.to_thread(self._set_claim_lease, dispatch, max(float(delay_s), 0.0))
        except Exception:
            _logger.exception("Dream confirmation claim lease update failed for message_id=%s", dispatch.message_id)

    async def _renew_owned_claim(self, dispatch: StoryWorkspaceDreamConfirmationDispatch) -> bool:
        while True:
            await asyncio.sleep(self._lease_renew_interval_s)
            try:
                renewed = await asyncio.to_thread(self._set_claim_lease, dispatch, None)
            except asyncio.CancelledError:
                raise
            except Exception:
                _logger.exception("Dream confirmation claim renewal failed for message_id=%s", dispatch.message_id)
                continue
            if not renewed:
                return False

    async def _consume_and_ack(self, dispatch: StoryWorkspaceDreamConfirmationDispatch) -> None:
        completion_observed = False
        heartbeat: Optional[asyncio.Task[bool]] = None
        turn_task: Optional[asyncio.Task[bool]] = None

        async def stop_heartbeat() -> None:
            nonlocal heartbeat
            if heartbeat is not None:
                heartbeat.cancel()
                await asyncio.gather(heartbeat, return_exceptions=True)
                heartbeat = None

        try:
            heartbeat = asyncio.create_task(
                self._renew_owned_claim(dispatch), name=f"dream-confirmation-lease-{dispatch.message_id}"
            )
            turn_task = asyncio.ensure_future(self._dispatcher_factory()(
                dispatch.thread_id, dispatch.actor_id, dispatch.message_id, dispatch.parts, dispatch.metadata,
            ))
            turn_task.set_name(f"dream-confirmation-turn-{dispatch.message_id}")
            done, _ = await asyncio.wait({heartbeat, turn_task}, return_when=asyncio.FIRST_COMPLETED)
            if heartbeat in done and turn_task not in done:
                turn_task.cancel()
                await asyncio.gather(turn_task, return_exceptions=True)
                return
            completed = await turn_task
            if completed:
                completion_observed = True
                await stop_heartbeat()
                if await asyncio.to_thread(self._mark_dispatched, dispatch):
                    self._retry_state.pop(dispatch.message_id, None)
                else:
                    _logger.warning("Dream confirmation ACK lost ownership for message_id=%s", dispatch.message_id)
            else:
                await self._defer_owned_claim(dispatch, self._record_retry(dispatch.message_id))
            await stop_heartbeat()
        except asyncio.CancelledError:
            await stop_heartbeat()
            self._record_retry(dispatch.message_id)
            if not completion_observed:
                await self._defer_owned_claim(dispatch, 0.0)
            raise
        except Exception:
            await stop_heartbeat()
            delay = self._record_retry(dispatch.message_id)
            if not completion_observed:
                await self._defer_owned_claim(dispatch, delay)
            _logger.exception(
                "Dream confirmation remains pending for thread_id=%s message_id=%s",
                dispatch.thread_id, dispatch.message_id,
            )
        finally:
            await stop_heartbeat()
            if turn_task is not None and not turn_task.done():
                turn_task.cancel()
                await asyncio.gather(turn_task, return_exceptions=True)
            if self._in_flight.get(dispatch.message_id) is asyncio.current_task():
                self._in_flight.pop(dispatch.message_id, None)

    async def _run(self) -> None:
        try:
            while True:
                try:
                    await self.reconcile_once()
                except asyncio.CancelledError:
                    raise
                except Exception:
                    _logger.exception("Dream confirmation reconciliation scan failed")
                if self._stop_event is None:
                    return
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=self._reconcile_interval_s)
                    return
                except asyncio.TimeoutError:
                    continue
        except asyncio.CancelledError:
            raise
