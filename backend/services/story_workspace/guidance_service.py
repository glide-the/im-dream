# [Input] One Admin-persisted Registry115 dispatch plus current OAuth actor and Registry133 DTO clients.
# [Output] Exact Workflow/Deck/persistence owner composition and same-Thread Agent Runtime scheduling.
# [Pos] Dream guidance execution seam; Admin owns authorization, delegation, ORM and persistence.
# [Sync] 2026-09-16: inject a complete Admin turn owner and remove the last Guidance-triggered database fallback.
"""Story Workspace guidance Runtime dispatcher retained by Dream."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import logging
from typing import Callable
from uuid import uuid4

from services.admin_data.deck_chat_context_data import (
    AdminDeckChatContextData,
    AdminDeckChatContextResolution,
    DeckChatContextInputDTO,
)
from services.admin_data.errors import invalid_response
from services.admin_data.request_auth import AdminRequestActor, AdminRequestAuth
from services.admin_data.turn_persistence import AdminTurnPersistence
from services.admin_data.workflow_data import AdminWorkflowResolution


logger = logging.getLogger(__name__)

@dataclass(frozen=True, slots=True)
class StoryWorkspaceGuidanceTurnOwner:
    """Server-only immutable objects required by one Guidance Agent turn."""

    workflow: AdminWorkflowResolution
    persistence: AdminTurnPersistence
    deck: AdminDeckChatContextResolution

    def context_for(self, *, workflow_run_id: str):
        context = self.workflow.context_for(
            actor_id=self.workflow.canonical_user_id,
            thread_id=self.workflow.thread_id,
        )
        if context is None or context.workflow_run_id != workflow_run_id:
            raise invalid_response(write=True)
        self.deck.context_for(
            actor_id=self.workflow.canonical_user_id,
            deck_id=context.deck_id,
            voice_id=context.agent_id,
        )
        return context


GuidanceDispatcher = Callable[
    [StoryWorkspaceGuidanceTurnOwner, str, str, list, dict],
    bool,
]


async def prepare_guidance_turn_owner(
    *,
    request_auth: AdminRequestAuth,
    actor: AdminRequestActor,
    thread_id: str,
    workflow_run_id: str,
) -> StoryWorkspaceGuidanceTurnOwner:
    """Resolve and bind the existing DTO owners for one committed command."""

    workflow = await asyncio.to_thread(
        request_auth.workflow_context,
        actor,
        thread_id,
        str(uuid4()),
    )
    context = workflow.context_for(
        actor_id=actor.canonical_user_id,
        thread_id=thread_id,
    )
    if context is None or context.workflow_run_id != workflow_run_id:
        raise invalid_response(write=True)
    deck = await asyncio.to_thread(
        AdminDeckChatContextData(
            request_auth.client,
            canonical_user_id=actor.canonical_user_id,
        ).resolve,
        DeckChatContextInputDTO(
            deck_id=context.deck_id,
            voice_id=context.agent_id,
        ),
        str(uuid4()),
        access_token=actor.access_token,
    )
    persistence = await asyncio.to_thread(
        request_auth.turn_persistence,
        actor,
        workflow,
        str(uuid4()),
    )
    try:
        owner = StoryWorkspaceGuidanceTurnOwner(
            workflow=workflow,
            persistence=persistence,
            deck=deck,
        )
        owner.context_for(workflow_run_id=workflow_run_id)
        return owner
    except BaseException:
        await asyncio.to_thread(persistence.close)
        raise


def build_thread_turn_dispatcher() -> GuidanceDispatcher:
    """Hand one already-persisted guidance message to the same Thread.

    There is no mid-turn injection channel. When the Thread is already running,
    the durable Admin-owned message remains available and this seam reports
    ``False`` without changing persistence or Runtime state.
    """

    def dispatch(
        owner: StoryWorkspaceGuidanceTurnOwner,
        workflow_run_id: str,
        message_id: str,
        parts: list,
        metadata: dict,
    ) -> bool:
        try:
            from agent_factory import claude_agent_thread_factory
            from claude_agent.service import ClaudeAgentRunRequest
            from services.admin_gateway import resolve_platform_model_alias

            context = owner.context_for(workflow_run_id=workflow_run_id)
            thread_id = context.thread_id
            actor_id = owner.workflow.canonical_user_id
            snapshot = claude_agent_thread_factory.session_snapshot(thread_id)
            if snapshot and snapshot.get("lifecycle") == "running":
                logger.info(
                    "Guidance turn deferred: thread %s already has an in-flight turn; "
                    "guidance message %s remains persisted.",
                    thread_id,
                    message_id,
                )
                owner.persistence.close()
                return False

            request = ClaudeAgentRunRequest(
                user_id=str(actor_id),
                thread_id=thread_id,
                resume=True,
                model=resolve_platform_model_alias(actor_id),
                message_id=message_id,
                message_parts=parts,
                message_metadata=metadata,
                admin_workflow_resolution=owner.workflow,
                admin_turn_persistence=owner.persistence,
                admin_deck_chat_context=owner.deck,
            )

            async def _drain() -> None:
                try:
                    async for _frame in claude_agent_thread_factory.run_streaming(request):
                        pass
                except Exception:
                    logger.exception(
                        "Guidance turn failed for thread_id=%s message_id=%s",
                        thread_id,
                        message_id,
                    )
                finally:
                    await asyncio.to_thread(owner.persistence.close)

            asyncio.create_task(
                _drain(),
                name=f"story-workspace-guidance-{thread_id}-{message_id}",
            )
        except BaseException:
            owner.persistence.close()
            raise
        return True

    return dispatch
