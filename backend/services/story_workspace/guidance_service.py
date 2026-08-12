"""Story Workspace guidance command service (Dream Surface Task 3).

Contract source: design_004 §5.3 / DEC-032.

- Persistence: guidance is stored as a ``chat_message`` user row marked
  ``metadata.kind == "story-workspace-guidance"``. The same metadata carries
  the ReviewEvent action=``guide`` audit fields (actor / run / request ID /
  idempotency key / command kind / text summary). Zero DDL: the ``metadata``
  column and ``save_chat_message(..., metadata=...)`` already exist.
- Idempotency: the message id derives from the client idempotency key
  (``guide_<key>``). The service SELECTs first: same key + same content →
  202 replay (no duplicate injection); same key + different content → 409.
  The database helper repeats that check atomically, closing concurrent claims
  without overwriting or reparenting the winning message.
- Injection (review note R5): there is no mid-turn injection channel, so the
  guidance message is handed to the runner as a *new user turn on the same
  chat thread* (``source_voice_thread_id`` of the run). The dispatcher seam
  below triggers that turn best-effort; the row is already persisted either
  way (202 Accepted semantics).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from typing import Any, Callable, Optional
from uuid import uuid4

import database

try:
    from models.workflow_run import RunStatus, WorkflowRun
    from story_workspace.contracts import (
        StoryWorkspaceGuidanceCommandPayload,
        StoryWorkspaceGuidanceKind,
        StoryWorkspaceReviewEventAction,
    )
except ModuleNotFoundError:  # Support package imports from repository root.
    from backend.models.workflow_run import RunStatus, WorkflowRun
    from backend.story_workspace.contracts import (
        StoryWorkspaceGuidanceCommandPayload,
        StoryWorkspaceGuidanceKind,
        StoryWorkspaceReviewEventAction,
    )


logger = logging.getLogger(__name__)

GUIDANCE_METADATA_KIND = "story-workspace-guidance"
GUIDANCE_MESSAGE_ID_PREFIX = "guide_"
GUIDANCE_TEXT_SUMMARY_MAX_LENGTH = 200

# Confirmed runs accept guidance after business review; failed runs accept the
# sidebar-controlled "retry failed step" command (design_004 §5.2/§5.4).
GUIDABLE_RUN_STATUSES = frozenset({RunStatus.CONFIRMED, RunStatus.FAILED})

RunReader = Callable[[str], WorkflowRun]
GuidanceDispatcher = Callable[[str, str, str, list, dict], bool]


class StoryWorkspaceGuidanceError(RuntimeError):
    """Known guidance failure carrying a client-safe code and status."""

    def __init__(self, code: str, status_code: int) -> None:
        super().__init__(code)
        self.code = code
        self.status_code = status_code


def guidance_message_id(idempotency_key: str) -> str:
    return f"{GUIDANCE_MESSAGE_ID_PREFIX}{idempotency_key}"


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _command_fingerprint(payload: StoryWorkspaceGuidanceCommandPayload, run_id: str) -> str:
    content = {
        "story_workspace_run_id": run_id,
        "actor": payload.actor,
        "command_kind": payload.kind.value,
        "text": payload.text,
        "step_id": payload.step_id,
    }
    return "sha256:" + hashlib.sha256(_canonical_json(content).encode("utf-8")).hexdigest()


def _guidance_turn_text(payload: StoryWorkspaceGuidanceCommandPayload, run_id: str) -> str:
    prefix = f"[story-workspace guidance · run {run_id}]"
    if payload.kind == StoryWorkspaceGuidanceKind.RETRY_STEP:
        text = f"{prefix} retry step {payload.step_id}"
        if payload.text and payload.text.strip():
            text += f": {payload.text.strip()}"
        return text
    return f"{prefix} {payload.text.strip() if payload.text else ''}"


def _text_summary(payload: StoryWorkspaceGuidanceCommandPayload) -> str:
    if payload.kind == StoryWorkspaceGuidanceKind.RETRY_STEP:
        summary = f"retry-step {payload.step_id}"
        if payload.text and payload.text.strip():
            summary += f": {payload.text.strip()}"
    else:
        summary = (payload.text or "").strip()
    return summary[:GUIDANCE_TEXT_SUMMARY_MAX_LENGTH]


def build_thread_turn_dispatcher() -> GuidanceDispatcher:
    """Default dispatcher: hand the guidance to the runner as a new user turn.

    Uses the shared ClaudeAgentThreadFactory. When the thread already has an
    in-flight turn there is no mid-turn channel (R5): the guidance row stays
    persisted and the dispatcher reports ``delivered=False`` so the response
    can surface ``dispatched: false`` while still returning 202.
    """

    def dispatch(
        thread_id: str,
        actor_id: str,
        message_id: str,
        parts: list,
        metadata: dict,
    ) -> bool:
        from agent_factory import claude_agent_thread_factory
        from claude_agent.service import ClaudeAgentRunRequest
        from services.admin_gateway import resolve_platform_model_alias

        snapshot = claude_agent_thread_factory.session_snapshot(thread_id)
        if snapshot and snapshot.get("lifecycle") == "running":
            logger.info(
                "Guidance turn deferred: thread %s already has an in-flight turn; "
                "guidance message %s remains persisted for the next turn.",
                thread_id,
                message_id,
            )
            return False

        request = ClaudeAgentRunRequest(
            user_id=str(actor_id),
            thread_id=thread_id,
            resume=True,
            model=resolve_platform_model_alias(actor_id),
            message_id=message_id,
            message_parts=parts,
            message_metadata=metadata,
        )

        async def _drain() -> None:
            try:
                async for _frame in claude_agent_thread_factory.run_streaming(request):
                    pass  # frames are persisted by the service callbacks
            except Exception:
                logger.exception(
                    "Guidance turn failed for thread_id=%s message_id=%s",
                    thread_id,
                    message_id,
                )

        asyncio.create_task(_drain())
        return True

    return dispatch


class StoryWorkspaceGuidanceService:
    """Submit guidance commands for guidable workflow runs."""

    def __init__(
        self,
        db: Any,
        *,
        run_reader: RunReader,
        dispatcher: Optional[GuidanceDispatcher] = None,
        request_id_factory: Callable[[], str] = lambda: str(uuid4()),
    ) -> None:
        self._db = db
        self._run_reader = run_reader
        self._dispatcher = dispatcher or (lambda *_args: False)
        self._request_id_factory = request_id_factory

    def submit_guidance(
        self,
        run_id: str,
        payload: StoryWorkspaceGuidanceCommandPayload,
        *,
        actor_id: str,
    ) -> dict[str, Any]:
        if payload.actor != actor_id:
            raise StoryWorkspaceGuidanceError("WORKFLOW_PERMISSION_DENIED", 403)

        run = self._run_reader(run_id)  # raises RunNotFound (WorkflowRunError)
        if run.status not in GUIDABLE_RUN_STATUSES:
            raise StoryWorkspaceGuidanceError("WORKFLOW_RUN_NOT_GUIDABLE", 409)

        thread_id = run.source_voice_thread_id
        if not thread_id or not self._thread_owned_by(thread_id, actor_id):
            # Guidance reuses the chat thread that initiated the run as its
            # transport channel (DEC-032); without it the run is not guidable.
            raise StoryWorkspaceGuidanceError("WORKFLOW_RUN_NOT_GUIDABLE", 409)

        message_id = guidance_message_id(payload.idempotency_key)
        fingerprint = _command_fingerprint(payload, run_id)
        existing = self._select_guidance_message(message_id)
        if existing is not None:
            existing_metadata = existing["metadata"] or {}
            if existing_metadata.get("command_fingerprint") == fingerprint:
                return {
                    "message_id": message_id,
                    "story_workspace_run_id": run_id,
                    "review_action": StoryWorkspaceReviewEventAction.GUIDE.value,
                    "status": "accepted",
                    "replayed": True,
                    "dispatched": False,
                    "request_id": existing_metadata.get("request_id"),
                }
            raise StoryWorkspaceGuidanceError("IDEMPOTENCY_CONFLICT", 409)

        request_id = self._request_id_factory()
        turn_text = _guidance_turn_text(payload, run_id)
        parts = [{"type": "text", "text": turn_text}]
        metadata = {
            "kind": GUIDANCE_METADATA_KIND,
            "story_workspace_run_id": run_id,
            "actor": actor_id,
            "request_id": request_id,
            "idempotency_key": payload.idempotency_key,
            "command_kind": payload.kind.value,
            "step_id": payload.step_id,
            "text_summary": _text_summary(payload),
            "review_action": StoryWorkspaceReviewEventAction.GUIDE.value,
            "command_fingerprint": fingerprint,
        }
        try:
            database.save_chat_message(
                thread_id,
                "user",
                parts=parts,
                message_id=message_id,
                metadata=metadata,
            )
        except database.ChatMessageIdentityConflict as exc:
            raise StoryWorkspaceGuidanceError("IDEMPOTENCY_CONFLICT", 409) from exc

        dispatched = False
        try:
            dispatched = bool(
                self._dispatcher(thread_id, actor_id, message_id, parts, metadata)
            )
        except Exception:
            logger.exception(
                "Guidance dispatch failed for run_id=%s message_id=%s",
                run_id,
                message_id,
            )

        logger.info(
            "story_workspace_guidance",
            extra={
                "id": request_id,
                "user_id": actor_id,
                "story_workspace_run_id": run_id,
                "action": StoryWorkspaceReviewEventAction.GUIDE.value,
                "command_kind": payload.kind.value,
                "idempotency_key": payload.idempotency_key,
                "message_id": message_id,
                "dispatched": dispatched,
            },
        )
        return {
            "message_id": message_id,
            "story_workspace_run_id": run_id,
            "review_action": StoryWorkspaceReviewEventAction.GUIDE.value,
            "status": "accepted",
            "replayed": False,
            "dispatched": dispatched,
            "request_id": request_id,
        }

    def _thread_owned_by(self, thread_id: str, actor_id: str) -> bool:
        row = self._db.execute(
            "SELECT user_id FROM chat_thread WHERE id = %s",
            (thread_id,),
        ).fetchone()
        return row is not None and str(row["user_id"]) == str(actor_id)

    def _select_guidance_message(self, message_id: str) -> Optional[dict[str, Any]]:
        row = self._db.execute(
            "SELECT id, metadata FROM chat_message WHERE id = %s",
            (message_id,),
        ).fetchone()
        if row is None:
            return None
        metadata_raw = row["metadata"]
        try:
            metadata = json.loads(metadata_raw) if metadata_raw else None
        except (TypeError, ValueError):
            metadata = None
        return {"id": row["id"], "metadata": metadata}
