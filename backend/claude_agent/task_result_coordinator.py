# [Input] Admin-claimed task result, source-bound Runtime grants and the canonical Chat turn Factory.
# [Output] One source continuation and Admin-verified delivery or an explicit uncertain terminal.
# [Pos] Server-owned task-result reconciler; Admin owns rows, claims, grants and revision fences.
# [Sync] 2026-09-28: source-result turns do not inherit a browser Editor snapshot because their claim has no Editor grant.
# [Sync] 2026-09-28: retain the exact claim-next request ID while its Admin outcome remains unknown.
# [Sync] 2026-09-28: settle a claimed source result only after the Factory owner finishes any queued follow-up turns.
# [Sync] 2026-09-28: stop claiming before Factory shutdown and let active owners finish before settlement.
# [Sync] 2026-09-28: stream errors close source grants only after the Factory owner exits.
# [Sync] 2026-09-27: resume the source Claude session after a child Thread commits its final answer.
"""Resume a source conversation when an independent task produces a final result."""

from __future__ import annotations

import asyncio
import logging
import math
from typing import Any, Awaitable, Callable
from uuid import uuid4

from claude_agent.service import ClaudeAgentRunRequest
from services.admin_data.deck_chat_context_data import (
    AdminDeckChatContextData, DeckChatContextInputDTO,
)
from services.admin_data.errors import AdminDataError
from services.admin_data.task_session_result_data import (
    AdminTaskResultClaim, AdminTaskResultWorkerData, TaskResultSettleInputDTO,
)
from services.admin_gateway.models import GatewayModelCatalogClient
from services.admin_gateway.selection import resolve_platform_model
from services.deck.chat_context import DeckChatContextAssembler
from services.story_workspace.dream_lifecycle_observer import drain_chat_agent_turn

logger = logging.getLogger(__name__)


class TaskResultCoordinator:
    """Poll the Admin outbox and hand each claim to the existing Chat Factory."""

    def __init__(self, worker: AdminTaskResultWorkerData, factory: Any, *,
                 poll_interval_s: float = 2.0,
                 request_id_factory: Callable[[], str] = lambda: str(uuid4()),
                 request_preparer: Callable[[AdminTaskResultClaim], Awaitable[tuple[Any, ClaudeAgentRunRequest]]] | None = None) -> None:
        if not math.isfinite(poll_interval_s) or poll_interval_s <= 0:
            raise ValueError("poll_interval_s must be finite and positive")
        self._worker = worker
        self._factory = factory
        self._poll_interval_s = poll_interval_s
        self._request_id_factory = request_id_factory
        self._request_preparer = request_preparer or self._prepare_request
        self._loop_task: asyncio.Task[None] | None = None
        self._in_flight: set[asyncio.Task[None]] = set()
        self._claim_stop = asyncio.Event()
        self._last_poll_error: str | None = None

    def start(self) -> None:
        if self._loop_task is not None and not self._loop_task.done():
            return
        self._claim_stop.clear()
        self._loop_task = asyncio.create_task(self._poll(), name="task-result-reconciler")

    async def stop_claiming(self) -> None:
        """Finish a pending Admin claim response without claiming another result."""
        self._claim_stop.set()
        if self._loop_task is not None:
            await self._loop_task
            self._loop_task = None

    async def stop(self) -> None:
        """Drain dispatches after their Factory owners have exited."""
        await self.stop_claiming()
        await asyncio.gather(
            *tuple(self._in_flight),
            return_exceptions=True,
        )
        self._in_flight.clear()

    async def _poll(self) -> None:
        claim_request_id: str | None = None
        claim_outcome_unknown = False
        try:
            while not self._claim_stop.is_set():
                try:
                    if claim_request_id is None:
                        claim_request_id = self._request_id_factory()
                    claim = await asyncio.to_thread(
                        self._worker.claim_next, claim_request_id,
                    )
                    # A definite claim or empty receipt closes this request.
                    # An uncertain transport outcome must retry the same key:
                    # a fresh one cannot recover the original Admin claim.
                    claim_request_id = None
                    claim_outcome_unknown = False
                    self._last_poll_error = None
                    if claim is not None:
                        task = asyncio.create_task(
                            self._dispatch(claim),
                            name=f"task-result-{claim.result.notification_id}",
                        )
                        self._in_flight.add(task)
                        task.add_done_callback(self._in_flight.discard)
                        continue
                except asyncio.CancelledError:
                    raise
                except AdminDataError as exc:
                    if exc.outcome_unknown:
                        claim_outcome_unknown = True
                    elif (not claim_outcome_unknown or exc.code in (
                        "TASK_SESSION_RETURN_STATE_UNKNOWN", "OPERATION_REQUEST_CONFLICT",
                    )):
                        # A capability/scope precheck can fail before the
                        # original claim is replayed. Keep that key until the
                        # original operation has a definite result.
                        claim_request_id = None
                        claim_outcome_unknown = False
                    # A deployment without the exact Admin capability remains
                    # usable for ordinary Chat; this worker cannot invent rows.
                    if exc.code != self._last_poll_error:
                        logger.warning("Task-result poll unavailable: code=%s", exc.code)
                    self._last_poll_error = exc.code
                except Exception:
                    logger.exception("Task-result poll failed")
                try:
                    await asyncio.wait_for(
                        self._claim_stop.wait(), timeout=self._poll_interval_s,
                    )
                except asyncio.TimeoutError:
                    pass
        except asyncio.CancelledError:
            return

    async def _prepare_request(self, claim: AdminTaskResultClaim):
        owner = await asyncio.to_thread(
            self._worker.turn_owner, claim, self._request_id_factory(),
        )
        actor_id = claim.actor_id
        thread_id = claim.result.source_thread_id
        try:
            source = await asyncio.to_thread(
                owner.persistence.thread, actor_id=actor_id, thread_id=thread_id,
            )
            if source is None or source.claude_session_id != claim.source_session_id:
                raise AdminDataError("TASK_SESSION_RETURN_SESSION_CHANGED", 409)
            context = owner.workflow.context_for(actor_id=actor_id, thread_id=thread_id)
            if context is not None and (
                context.deck_id != source.deck_id or context.agent_id != source.voice_id
            ):
                raise AdminDataError("DREAM_THREAD_BINDING_CONFLICT", 409)
            config = await asyncio.to_thread(
                owner.persistence.system_config, actor_id=actor_id, thread_id=thread_id,
            )
            model = await asyncio.to_thread(
                resolve_platform_model, actor_id,
                catalog_client_factory=lambda _actor: GatewayModelCatalogClient(
                    access_token=owner.gateway_runtime.access_token(),
                ),
                system_config_reader=lambda _actor: config,
            )
            deck_snapshot = None
            system_prompt = None
            if source.deck_id:
                grant = owner.persistence.current_grant(
                    actor_id=actor_id, thread_id=thread_id,
                )
                deck_snapshot = await asyncio.to_thread(
                    AdminDeckChatContextData(
                        self._worker.client, canonical_user_id=actor_id,
                    ).resolve,
                    DeckChatContextInputDTO(
                        deck_id=source.deck_id, voice_id=source.voice_id,
                    ),
                    self._request_id_factory(), access_token=grant.token,
                )
                deck_context = await DeckChatContextAssembler(
                    deck_snapshot.context_for(
                        actor_id=actor_id, deck_id=source.deck_id,
                        voice_id=source.voice_id,
                    ),
                    selected_voice_id=source.voice_id,
                ).resolve()
                system_prompt = deck_context.system_prompt
            request = ClaudeAgentRunRequest(
                user_id=actor_id, thread_id=thread_id, resume=True,
                message_id=claim.source_input_message_id,
                message_parts=[{"type": "text", "text": claim.source_input_text}],
                message_metadata={
                    "kind": "task-session-result",
                    "taskResultNotificationId": claim.result.notification_id,
                    "taskId": claim.result.task_id,
                    "targetTurnId": claim.result.target_turn_id,
                    "claimId": claim.result.claim_id,
                    "sourceTurnId": claim.result.source_turn_id,
                },
                user_message_pre_persisted=True,
                task_result_turn_id=claim.result.source_turn_id,
                model=model.model_alias,
                model_runtime_env=model.claude_code_runtime_env(),
                admin_workflow_resolution=owner.workflow,
                admin_turn_persistence=owner.persistence,
                admin_gateway_runtime=owner.gateway_runtime,
                inherit_cached_editor_state=False,
                admin_deck_chat_context=deck_snapshot,
                system_prompt=system_prompt,
            )
            return owner, request
        except BaseException:
            try:
                await asyncio.to_thread(owner.gateway_runtime.close)
            finally:
                await asyncio.to_thread(owner.persistence.close)
            raise

    async def _settle(self, claim: AdminTaskResultClaim, action: str, error_code: str | None) -> None:
        result = claim.result
        if not result.claim_id:
            raise RuntimeError("Admin task-result claim is missing a claim ID")
        await asyncio.to_thread(
            self._worker.settle,
            TaskResultSettleInputDTO(
                notification_id=result.notification_id,
                expected_revision=result.revision,
                claim_id=result.claim_id,
                action=action,
                error_code=error_code,
            ),
            self._request_id_factory(),
        )

    async def _dispatch(self, claim: AdminTaskResultClaim) -> None:
        entered_factory = False
        settle_on_exit = True
        owner = None
        action = "failed"
        error_code: str | None = "TASK_SESSION_RETURN_NOT_SUBMITTED"
        try:
            owner, request = await self._request_preparer(claim)
            # Keep short-lived source grants renewable while a prior turn holds
            # the existing per-Thread lock. Factory also starts them idempotently.
            await asyncio.to_thread(owner.persistence.start)
            await asyncio.to_thread(owner.gateway_runtime.start)
            entered_factory = True
            result = await drain_chat_agent_turn(
                self._factory, request, wait_for_factory_owner=True,
            )
            if result.completed:
                action, error_code = "delivered", None
            else:
                action, error_code = "mark_unknown", "TASK_SESSION_RETURN_STATE_UNKNOWN"
        except asyncio.CancelledError:
            if entered_factory:
                # Cancellation of this observer does not prove the Factory
                # owner stopped. Keep the claim grants live; Admin reconciles
                # after they expire using the persisted source final, if any.
                settle_on_exit = False
            raise
        except Exception:
            logger.exception("Task-result source turn failed: notification_id=%s", claim.result.notification_id)
            if entered_factory:
                # The canonical drain waits for owner_completion on a stream
                # error. Close idempotent grants here as well when Factory
                # rejected the stream before adopting the owner.
                try:
                    try:
                        await asyncio.to_thread(owner.gateway_runtime.close)
                    finally:
                        await asyncio.to_thread(owner.persistence.close)
                except Exception:
                    logger.exception("Task-result source owner cleanup failed: notification_id=%s", claim.result.notification_id)
                action, error_code = "mark_unknown", "TASK_SESSION_RETURN_STATE_UNKNOWN"
        finally:
            if owner is not None and not entered_factory:
                try:
                    try:
                        await asyncio.to_thread(owner.gateway_runtime.close)
                    finally:
                        await asyncio.to_thread(owner.persistence.close)
                except Exception:
                    logger.exception("Task-result prelaunch owner cleanup failed: notification_id=%s", claim.result.notification_id)
            if settle_on_exit:
                try:
                    await self._settle(claim, action, error_code)
                except Exception:
                    logger.exception("Task-result settlement failed: notification_id=%s", claim.result.notification_id)
