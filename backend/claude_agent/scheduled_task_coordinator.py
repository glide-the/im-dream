# [Input] Admin v3 dispatch claims with Thread/model snapshots, source-limited grants and the canonical Chat Factory.
# [Output] One lease-fenced unattended source-resume or new-Thread turn with tool policy and crash reconciliation.
# [Pos] Independent scheduled Chat composition root; no database schema, browser bearer or alternate model runtime.
# [Sync] 2026-10-07: dispatch v3 source/new Thread modes with immutable model selection through the public Chat path.
"""Consume Admin scheduled triggers without adding a second Chat execution path."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
import logging
from uuid import NAMESPACE_URL, uuid4, uuid5

from claude_agent.chat_stream_adapter import ChatStreamAdapter
from services.story_workspace.dream_lifecycle_observer import NormalizedAgentTurnClassifier
from services.admin_data.chat_data import AdminChatData
from services.admin_data.chat_models import MessageDetailInputDTO
from services.admin_data.client import AdminDataClient
from services.admin_data.delegation import AdminDelegationCreator, AdminRuntimeClient, DelegationCreateInputDTO
from services.admin_data.gateway_runtime import AdminGatewayRuntime
from services.admin_data.editor_runtime import AdminEditorRuntime, EditorLoadInputDTO
from services.admin_data.request_auth import AdminRequestActor, AdminRequestAuth
from services.admin_data.scheduled_task_data import (
    AdminScheduledTaskData, CLAIM_TRIGGER_V3, PREPARE_TRIGGER_V3, RENEW_TRIGGER_V3,
    START_TRIGGER_V3, FINISH_TRIGGER_V3, RECONCILE_TRIGGER_V3, RESOLVE_AUTHORITY_V3,
    ClaimScheduledTriggerInputDTO, TriggerClaimInputDTO, StartScheduledTriggerInputDTO,
    FinishScheduledTriggerInputDTO, ReconcileScheduledTriggerInputDTO,
    ResolveScheduledAuthorityInputDTO, ScheduledTriggerV3DTO,
)
from libs.claude_agent_kit.types import ToolApprovalPolicy, ToolApprovalViolation
from services.admin_data.turn_persistence import AdminTurnPersistence
from services.admin_data.workflow_data import AdminWorkflowData
from services.admin_data.errors import AdminDataError

logger = logging.getLogger(__name__)

SCHEDULED_TOOL_APPROVAL_POLICY = ToolApprovalPolicy(
    overrides=(
        ("mcp__editor__write_segment", "auto"),
        ("mcp__editor__insert_widget", "auto"),
        ("mcp__editor__delete_segment", "manual"),
        ("mcp__editor__reply_to_comment", "manual"),
        ("mcp__editor__switch_editor", "manual"),
        ("AskUserQuestion", "manual"),
        ("mcp__user__ask_user", "manual"),
    ),
    deny_unresolved=True,
    ignore_full_access=True,
)


@dataclass(frozen=True, slots=True)
class ScheduledDispatchContext:
    trigger: ScheduledTriggerV3DTO
    claim_id: str
    canonical_user_id: str
    turn_id: str
    turn_persistence: AdminTurnPersistence
    gateway_runtime: AdminGatewayRuntime
    editor_runtime: AdminEditorRuntime | None
    editor_state: dict | None
    resume_existing_thread: bool
    tool_approval_policy: ToolApprovalPolicy
    tool_approval_violation: ToolApprovalViolation


class ScheduledTaskCoordinator:
    """Poll one Admin claim at a time and keep each claim's owner independent."""

    def __init__(self, owner: AdminRequestAuth, *, poll_interval_seconds: float):
        self._owner = owner
        self._data = AdminScheduledTaskData(owner.client)
        self._poll_interval_seconds = poll_interval_seconds
        self._stop = asyncio.Event()
        self._poll_task: asyncio.Task | None = None
        self._in_flight: set[asyncio.Task] = set()
        self._pending_claim_request_id: str | None = None
        self._last_error: str | None = None

    def start(self) -> None:
        if self._poll_task is None or self._poll_task.done():
            self._stop.clear()
            self._poll_task = asyncio.create_task(self._poll(), name="scheduled-chat-worker")

    async def stop(self) -> None:
        self._stop.set()
        if self._poll_task is not None:
            await self._poll_task
            self._poll_task = None
        await asyncio.gather(*tuple(self._in_flight), return_exceptions=True)

    async def _execute(self, operation, input_dto, request_id: str):
        return await asyncio.to_thread(self._data.execute, operation, input_dto, request_id)

    async def _poll(self) -> None:
        while not self._stop.is_set():
            try:
                request_id = self._pending_claim_request_id or str(uuid4())
                self._pending_claim_request_id = request_id
                claimed = await self._execute(CLAIM_TRIGGER_V3, ClaimScheduledTriggerInputDTO(), request_id)
                self._pending_claim_request_id = None
                self._last_error = None
                if claimed.action == "reconcile" and claimed.trigger_id is not None:
                    await self._reconcile(claimed.trigger_id)
                    continue
                if claimed.action == "dispatch" and claimed.trigger is not None and claimed.claim_id is not None:
                    work = asyncio.create_task(self._dispatch(claimed.trigger, claimed.claim_id),
                                               name=f"scheduled-chat-{claimed.trigger.id}")
                    self._in_flight.add(work)
                    work.add_done_callback(self._in_flight.discard)
                    continue
            except asyncio.CancelledError:
                raise
            except AdminDataError as exc:
                if not exc.outcome_unknown:
                    self._pending_claim_request_id = None
                if exc.code != self._last_error:
                    logger.warning("Scheduled Chat claim unavailable: code=%s", exc.code)
                self._last_error = exc.code
            except Exception:
                logger.exception("Scheduled Chat claim failed")
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self._poll_interval_seconds)
            except asyncio.TimeoutError:
                pass

    async def _reconcile(self, trigger_id: str) -> None:
        try:
            await self._execute(RECONCILE_TRIGGER_V3, ReconcileScheduledTriggerInputDTO(trigger_id=trigger_id), str(uuid4()))
        except Exception:
            logger.exception("Scheduled Chat reconciliation failed for trigger=%s", trigger_id)

    async def _renew_until_done(self, trigger_id: str, claim_id: str,
                                expires_at: str, done: asyncio.Event) -> bool:
        expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        while not done.is_set():
            remaining = max(1.0, expiry.timestamp() - datetime.now(expiry.tzinfo).timestamp())
            try:
                await asyncio.wait_for(done.wait(), timeout=remaining / 2)
                return True
            except asyncio.TimeoutError:
                pass
            try:
                result = await self._execute(RENEW_TRIGGER_V3,
                    TriggerClaimInputDTO(trigger_id=trigger_id, claim_id=claim_id), str(uuid4()))
            except AdminDataError as exc:
                logger.warning("Scheduled Chat lease renewal failed: trigger=%s code=%s", trigger_id, exc.code)
                return False
            except Exception:
                logger.exception("Scheduled Chat lease renewal failed: trigger=%s", trigger_id)
                return False
            expiry = datetime.fromisoformat(result.authority_expires_at.replace("Z", "+00:00"))
        return True

    async def _finish(self, trigger_id: str, claim_id: str, status: str,
                      final_message_id: str | None, error_code: str | None) -> None:
        input_dto = FinishScheduledTriggerInputDTO(
            trigger_id=trigger_id, claim_id=claim_id, status=status,
            final_message_id=final_message_id, error_code=error_code,
        )
        request_id = str(uuid4())
        try:
            await self._execute(FINISH_TRIGGER_V3, input_dto, request_id)
        except AdminDataError as exc:
            if exc.outcome_unknown:
                # Receipt-bearing Admin writes are idempotent under their original ID.
                try:
                    await self._execute(FINISH_TRIGGER_V3, input_dto, request_id)
                    return
                except AdminDataError:
                    pass
            await self._reconcile(trigger_id)
            raise

    async def _start(self, trigger_id: str, claim_id: str, turn_id: str):
        input_dto = StartScheduledTriggerInputDTO(
            trigger_id=trigger_id, claim_id=claim_id, target_turn_id=turn_id,
        )
        request_id = str(uuid4())
        try:
            return await self._execute(START_TRIGGER_V3, input_dto, request_id)
        except AdminDataError as exc:
            if not exc.outcome_unknown:
                raise
            # A lost HTTP response may follow a committed start. Replay only
            # the original receipt; never issue a new turn binding.
            return await self._execute(START_TRIGGER_V3, input_dto, request_id)

    async def _dispatch(self, trigger: ScheduledTriggerV3DTO, claim_id: str) -> None:
        claim_input = TriggerClaimInputDTO(trigger_id=trigger.id, claim_id=claim_id)
        dispatch: ScheduledDispatchContext | None = None
        started = False
        start_uncertain = False
        stream_entered = False
        owner_completion: asyncio.Future | None = None
        renewal_done = asyncio.Event()
        renewal_task: asyncio.Task | None = None
        editor_runtime: AdminEditorRuntime | None = None
        turn_persistence: AdminTurnPersistence | None = None
        gateway_runtime: AdminGatewayRuntime | None = None
        try:
            prepared = await self._execute(PREPARE_TRIGGER_V3, claim_input, str(uuid4()))
            if not prepared.prepared:
                return
            if (prepared.authority_token is None or prepared.authority_expires_at is None
                or prepared.target_thread_id is None or prepared.input_message_id is None
                or prepared.resume_existing_thread is None):
                raise AdminDataError("SCHEDULE_PREPARE_INVALID", 503)
            authority = await asyncio.to_thread(
                self._data.execute, RESOLVE_AUTHORITY_V3, ResolveScheduledAuthorityInputDTO(),
                str(uuid4()), access_token=prepared.authority_token,
            )
            if (authority.trigger_id != trigger.id or authority.claim_id != claim_id
                or authority.target_thread_id != prepared.target_thread_id):
                raise AdminDataError("SCHEDULE_AUTHORITY_MISMATCH", 403)
            creator = AdminDelegationCreator(self._owner.client)
            persistence_grant = await asyncio.to_thread(
                creator.create,
                DelegationCreateInputDTO(purpose="server-persistence", thread_id=authority.target_thread_id,
                                         run_id=None, editor_session_id=None, scopes=["dream:read", "dream:write"]),
                access_token=prepared.authority_token, request_id=str(uuid4()),
            )
            gateway_grant = await asyncio.to_thread(
                creator.create,
                DelegationCreateInputDTO(purpose="gateway-cli", thread_id=authority.target_thread_id,
                                         run_id=None, editor_session_id=None,
                                         scopes=["messages:create", "messages:count_tokens", "models:list"]),
                access_token=prepared.authority_token, request_id=str(uuid4()),
            )
            workflow = await asyncio.to_thread(
                AdminWorkflowData(self._owner.client).resolve, authority.target_thread_id, str(uuid4()),
                access_token=persistence_grant.token, canonical_user_id=authority.canonical_user_id,
            )
            turn_persistence = AdminTurnPersistence(
                workflow, persistence_grant, self._owner.client,
                runtime_client_factory=lambda: AdminRuntimeClient(self._owner.runtime_http_config),
                session_broker_settings=self._owner.session_broker_settings,
            )
            gateway_runtime = AdminGatewayRuntime(
                gateway_grant, AdminRuntimeClient(self._owner.runtime_http_config),
            )
            scheduled_message = await asyncio.to_thread(
                AdminChatData(self._owner.client).process_detail,
                MessageDetailInputDTO(thread_id=authority.target_thread_id,
                                      message_id=prepared.input_message_id),
                str(uuid4()), access_token=persistence_grant.token,
            )
            if scheduled_message.message is None or scheduled_message.message.role != "user":
                raise AdminDataError("SCHEDULE_INPUT_UNAVAILABLE", 409)
            editor_state = None
            if authority.target_editor_session_id is not None:
                editor_runtime = AdminEditorRuntime(
                    workflow,
                    actor_id=authority.canonical_user_id,
                    access_token=prepared.authority_token,
                    delegation_creator=creator,
                    runtime_http_config=self._owner.runtime_http_config,
                    initial_session_id=authority.target_editor_session_id,
                    initial_request_id=str(uuid4()),
                    runtime_client_factory=lambda: AdminRuntimeClient(self._owner.runtime_http_config),
                )
                await asyncio.to_thread(editor_runtime.start)
                loaded = await asyncio.to_thread(
                    editor_runtime.load,
                    EditorLoadInputDTO(session_id=authority.target_editor_session_id),
                    str(uuid4()),
                )
                if loaded.editor_state is None:
                    raise AdminDataError("SCHEDULE_EDITOR_TARGET_UNAVAILABLE", 409)
                editor_state = loaded.editor_state.model_dump(mode="python", exclude_unset=True)
            turn_id = str(uuid4())
            tool_violation = ToolApprovalViolation()
            dispatch = ScheduledDispatchContext(prepared.trigger, claim_id,
                                                authority.canonical_user_id, turn_id,
                                                turn_persistence, gateway_runtime,
                                                editor_runtime, editor_state,
                                                prepared.resume_existing_thread,
                                                SCHEDULED_TOOL_APPROVAL_POLICY, tool_violation)
            issued_at = int(datetime.fromisoformat(authority.issued_at.replace("Z", "+00:00")).timestamp())
            expires_at = int(datetime.fromisoformat(authority.expires_at.replace("Z", "+00:00")).timestamp())
            actor = AdminRequestActor(authority.subject, authority.canonical_user_id,
                                      authority.client_id, frozenset(authority.scopes),
                                      issued_at, expires_at, persistence_grant.token)
            user = actor.current_user_projection()
            from routers.claude_agent import ClaudeAgentRequestBody, _claude_agent_stream_impl
            response = await _claude_agent_stream_impl(
                ClaudeAgentRequestBody(
                    thread_id=authority.target_thread_id,
                    resume=prepared.resume_existing_thread,
                    model=prepared.model_alias,
                    message={"id": prepared.input_message_id, "role": "user",
                             "parts": scheduled_message.message.parts},
                ), user, AdminChatData(self._owner.client), self._owner,
                scheduled_dispatch=dispatch,
            )
            # The response generator has not begun. Commit the same turn ID before
            # the Factory can launch the model or persist an assistant message.
            try:
                started_row = await self._start(trigger.id, claim_id, turn_id)
            except AdminDataError as exc:
                start_uncertain = exc.outcome_unknown
                raise
            if started_row.trigger.target_turn_id != turn_id:
                raise AdminDataError("SCHEDULE_TURN_CONFLICT", 409)
            started = True
            renewal_task = asyncio.create_task(self._renew_until_done(
                trigger.id, claim_id, prepared.authority_expires_at, renewal_done))
            classifier = NormalizedAgentTurnClassifier()
            adapter = ChatStreamAdapter()
            owner_completion = getattr(response, "scheduled_owner_completion", None)
            stream_entered = True
            async for frame in response.body_iterator:
                if isinstance(frame, bytes):
                    frame = frame.decode("utf-8")
                classifier.observe(adapter.decode(frame))
            if isinstance(owner_completion, asyncio.Future):
                await asyncio.shield(owner_completion)
            final_id = str(uuid5(NAMESPACE_URL, f"scheduled-final:{authority.target_thread_id}:{turn_id}"))
            violation_code = tool_violation.code()
            if violation_code is not None:
                await self._finish(trigger.id, claim_id, "failed", None, violation_code)
            elif renewal_task.done() and not renewal_task.result():
                await self._finish(trigger.id, claim_id, "state_unknown", None, "SCHEDULE_RENEW_FAILED")
            elif classifier.result().completed:
                await self._finish(trigger.id, claim_id, "succeeded", final_id, None)
            else:
                await self._finish(trigger.id, claim_id, "state_unknown", None, "SCHEDULE_RESULT_UNKNOWN")
        except asyncio.CancelledError:
            if stream_entered and isinstance(owner_completion, asyncio.Future):
                await asyncio.shield(owner_completion)
            if started:
                await self._reconcile(trigger.id)
            raise
        except Exception:
            logger.exception("Scheduled Chat dispatch failed for trigger=%s", trigger.id)
            try:
                if stream_entered and isinstance(owner_completion, asyncio.Future):
                    await asyncio.shield(owner_completion)
                if start_uncertain:
                    # A committed start without its receipt must not be
                    # overwritten with a preflight failure or rerun a model.
                    await self._reconcile(trigger.id)
                elif started:
                    await self._finish(trigger.id, claim_id, "state_unknown", None, "SCHEDULE_RESULT_UNKNOWN")
                else:
                    await self._finish(trigger.id, claim_id, "failed", None, "SCHEDULE_PREFLIGHT_FAILED")
            except Exception:
                await self._reconcile(trigger.id)
        finally:
            renewal_done.set()
            if renewal_task is not None:
                await asyncio.gather(renewal_task, return_exceptions=True)
            if dispatch is not None:
                if dispatch.editor_runtime is not None:
                    await asyncio.to_thread(dispatch.editor_runtime.close)
                await asyncio.to_thread(dispatch.gateway_runtime.close)
                await asyncio.to_thread(dispatch.turn_persistence.close)
            elif editor_runtime is not None:
                await asyncio.to_thread(editor_runtime.close)
                if gateway_runtime is not None:
                    await asyncio.to_thread(gateway_runtime.close)
                if turn_persistence is not None:
                    await asyncio.to_thread(turn_persistence.close)
            else:
                if gateway_runtime is not None:
                    await asyncio.to_thread(gateway_runtime.close)
                if turn_persistence is not None:
                    await asyncio.to_thread(turn_persistence.close)
