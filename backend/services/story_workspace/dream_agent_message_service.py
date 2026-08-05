"""Safe, run-bound Dream Agent message projections and dispatch claims.

The generic Claude Agent routes intentionally expose rich UI parts.  This
adapter is the only Story Workspace boundary that turns those parts/events
into the small text-only contract consumed by the Dream workbench.
"""

from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
import sqlite3
import math
import time
from typing import Any, AsyncGenerator, Callable, Optional
from uuid import uuid4

try:
    from story_workspace.contracts import (
        StoryWorkspaceDreamAgentMessage,
        StoryWorkspaceDreamAgentMessageAccepted,
        StoryWorkspaceDreamAgentMessageCommand,
        StoryWorkspaceDreamAgentMessageSnapshot,
        StoryWorkspaceDreamRunContext,
        STORY_WORKSPACE_DREAM_AGENT_MESSAGE_TEXT_MAX,
    )
    from services.story_workspace.dream_confirmation_service import (
        story_workspace_read_dream_confirmation_fact,
    )
except ModuleNotFoundError:
    from backend.story_workspace.contracts import (
        StoryWorkspaceDreamAgentMessage,
        StoryWorkspaceDreamAgentMessageAccepted,
        StoryWorkspaceDreamAgentMessageCommand,
        StoryWorkspaceDreamAgentMessageSnapshot,
        StoryWorkspaceDreamRunContext,
        STORY_WORKSPACE_DREAM_AGENT_MESSAGE_TEXT_MAX,
    )
    from backend.services.story_workspace.dream_confirmation_service import (
        story_workspace_read_dream_confirmation_fact,
    )


STORY_WORKSPACE_DREAM_AGENT_USER_KIND = "story-workspace-dream-agent-user"
STORY_WORKSPACE_DREAM_AGENT_SOURCE_KEY = "story_workspace_dream_source"
STORY_WORKSPACE_DREAM_AGENT_SOURCE_KINDS = frozenset({
    "story-workspace-dream-launch",
    "story-workspace-dream-confirmation",
    STORY_WORKSPACE_DREAM_AGENT_USER_KIND,
})
_CONFIRM_KIND = "story-workspace-dream-confirmation"
_ACTIVE = frozenset({"pending", "dispatching"})
_LEASE_SECONDS = 60
_LEASE_HEARTBEAT_SECONDS = 15


class StoryWorkspaceDreamAgentMessageError(RuntimeError):
    """An allowlisted HTTP-safe error at the Dream message boundary."""

    def __init__(self, code: str, status_code: int) -> None:
        super().__init__(code)
        self.code = code
        self.status_code = status_code


def story_workspace_guard_persisted_dream_agent_message_turn(
    db: sqlite3.Connection,
    *,
    thread_id: str,
    actor_id: str,
    message_id: str | None,
    metadata: Optional[dict],
) -> bool:
    """Keep a fresh widget claim from being overwritten by its queued runner.

    The client command has already been persisted under ``BEGIN IMMEDIATE``.
    A runner may begin later with a stale metadata copy, so the generic user
    persistence path must verify and preserve the database owner rather than
    replacing a renewed lease.
    """

    if not isinstance(message_id, str) or not message_id.startswith("dream_agent_"):
        return False
    row = db.execute(
        "SELECT message.thread_id, message.role, message.metadata, thread.user_id "
        "FROM chat_message AS message JOIN chat_thread AS thread "
        "ON thread.id = message.thread_id WHERE message.id = ?",
        (message_id,),
    ).fetchone()
    if row is None:
        return False
    stored = _decode(row["metadata"])
    if stored.get("kind") != STORY_WORKSPACE_DREAM_AGENT_USER_KIND:
        raise StoryWorkspaceDreamAgentMessageError("IDEMPOTENCY_CONFLICT", 409)
    if not (
        row["thread_id"] == thread_id
        and row["role"] == "user"
        and str(row["user_id"]) == str(actor_id)
        and isinstance(metadata, dict)
        and metadata.get("kind") == STORY_WORKSPACE_DREAM_AGENT_USER_KIND
        and metadata.get("story_workspace_run_id")
        == stored.get("story_workspace_run_id")
        and metadata.get("command_fingerprint")
        == stored.get("command_fingerprint")
    ):
        raise StoryWorkspaceDreamAgentMessageError("IDEMPOTENCY_CONFLICT", 409)
    return True


@dataclass(frozen=True)
class StoryWorkspaceDreamAgentPendingDispatch:
    thread_id: str
    actor_id: str
    context: StoryWorkspaceDreamRunContext
    message_id: str
    parts: list[dict[str, str]]
    metadata: dict[str, Any]


class StoryWorkspaceDreamAgentMessageCoordinator:
    """Coalesce durable pending-claim delivery attempts by message identity."""

    def __init__(
        self,
        dispatcher: Callable[[StoryWorkspaceDreamAgentPendingDispatch], Any],
    ) -> None:
        self._dispatcher = dispatcher
        self._tasks: dict[str, asyncio.Task[Any]] = {}

    def schedule(self, pending: StoryWorkspaceDreamAgentPendingDispatch) -> bool:
        existing = self._tasks.get(pending.message_id)
        if existing is not None and not existing.done():
            return False
        task = asyncio.create_task(
            self._dispatcher(pending),
            name=f"story-workspace-dream-agent-dispatch-{pending.message_id}",
        )
        self._tasks[pending.message_id] = task
        task.add_done_callback(
            lambda completed, message_id=pending.message_id: (
                self._tasks.pop(message_id, None)
                if self._tasks.get(message_id) is completed
                else None
            )
        )
        return True


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _decode(value: Any) -> dict[str, Any]:
    try:
        loaded = json.loads(value) if isinstance(value, str) else value
    except (TypeError, ValueError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _parts_text(parts: Any) -> tuple[str, bool]:
    if not isinstance(parts, list):
        return "", False
    text = "".join(
        part.get("text", "")
        for part in parts
        if isinstance(part, dict)
        and part.get("type") == "text"
        and isinstance(part.get("text"), str)
    )
    normalized = text.strip()
    return (
        normalized[:STORY_WORKSPACE_DREAM_AGENT_MESSAGE_TEXT_MAX],
        len(normalized) > STORY_WORKSPACE_DREAM_AGENT_MESSAGE_TEXT_MAX,
    )


def _message_id(actor_id: str, run_id: str, key: str) -> str:
    digest = hashlib.sha256(_json({"actor": actor_id, "run": run_id, "key": key}).encode()).hexdigest()
    return f"dream_agent_{digest}"


def _fingerprint(actor_id: str, run_id: str, command: StoryWorkspaceDreamAgentMessageCommand) -> str:
    return "sha256:" + hashlib.sha256(
        _json({"actor": actor_id, "run": run_id, "text": command.text, "key": command.idempotency_key}).encode()
    ).hexdigest()


def _parse_sse(frame: str) -> tuple[str, dict[str, Any]] | None:
    event = "message"
    raw_data: list[str] = []
    for line in frame.splitlines():
        if line.startswith("event:"):
            event = line[6:].strip()
        elif line.startswith("data:"):
            raw_data.append(line[5:].strip())
    if not raw_data:
        return None
    try:
        data = json.loads("\n".join(raw_data))
    except ValueError:
        return None
    return (event, data) if isinstance(data, dict) else None


def _has_data_frame(frame: str) -> bool:
    """Whether an upstream SSE frame consumes one stable raw ordinal."""

    return any(line.startswith("data:") for line in frame.splitlines())


class StoryWorkspaceDreamAgentMessageService:
    """Owns safe projections while callers retain run authorization/context."""

    def __init__(
        self,
        db: sqlite3.Connection,
        *,
        thread_factory: Any | None = None,
        db_factory: Callable[[], sqlite3.Connection] | None = None,
    ) -> None:
        self._db = db
        self._thread_factory = thread_factory
        self._db_factory = db_factory

    def snapshot(
        self, *, run_id: str, thread_id: str, actor_id: str
    ) -> StoryWorkspaceDreamAgentMessageSnapshot:
        confirmation_accepted, confirmation_dispatched = story_workspace_read_dream_confirmation_fact(
            self._db, actor_id=actor_id, thread_id=thread_id, run_id=run_id
        )
        session = self._thread_factory.session_snapshot(thread_id) if self._thread_factory else None
        running = bool(session and session.get("lifecycle") == "running")
        active_turn_id = str(session.get("current_turn_id")) if running and session.get("current_turn_id") else None
        has_active_claim = self._has_active_claim(
            run_id=run_id,
            thread_id=thread_id,
            actor_id=actor_id,
        )
        if has_active_claim:
            reason: str | None = "busy"
        elif running:
            reason: str | None = "busy" if confirmation_dispatched else (
                "continuing" if confirmation_accepted else "generating"
            )
        elif not confirmation_accepted:
            reason = "waiting_confirmation"
        elif not confirmation_dispatched:
            reason = "continuing"
        else:
            reason = None
        return StoryWorkspaceDreamAgentMessageSnapshot(
            story_workspace_run_id=run_id,
            lifecycle="streaming" if running else "idle",
            active_turn_id=active_turn_id,
            can_send=reason is None,
            send_block_reason=reason,
            messages=self._safe_messages(
                run_id=run_id, thread_id=thread_id, actor_id=actor_id
            ),
            snapshot_at=datetime.now(UTC),
        )

    def _safe_messages(
        self,
        *,
        run_id: str,
        thread_id: str,
        actor_id: str,
    ) -> list[StoryWorkspaceDreamAgentMessage]:
        rows = self._db.execute(
            "SELECT id, thread_id, role, parts, metadata, created_at FROM chat_message "
            "WHERE thread_id = ? ORDER BY created_at ASC, id ASC", (thread_id,)
        ).fetchall()
        source_rows = {
            str(row["id"]): row
            for row in rows
            if row["role"] == "user"
        }
        safe: list[StoryWorkspaceDreamAgentMessage] = []
        for row in rows:
            metadata = _decode(row["metadata"])
            kind = metadata.get("kind")
            # Only explicit widget user messages are public.  Assistant text is
            # public only after the run source and never when tied to a control turn.
            if row["role"] == "user":
                if (
                    kind != STORY_WORKSPACE_DREAM_AGENT_USER_KIND
                    or metadata.get("story_workspace_run_id") != run_id
                    or str(metadata.get("actor_id") or "") != actor_id
                ):
                    continue
            elif row["role"] == "assistant":
                if not self._assistant_has_authorized_source(
                    metadata,
                    source_rows=source_rows,
                    run_id=run_id,
                    thread_id=thread_id,
                    actor_id=actor_id,
                ):
                    continue
            else:
                continue
            try:
                parts = json.loads(row["parts"]) if row["parts"] else []
            except (TypeError, ValueError):
                continue
            text, truncated = _parts_text(parts)
            if not text:
                continue
            created = row["created_at"]
            if isinstance(created, str):
                try:
                    created = datetime.fromisoformat(created.replace("Z", "+00:00"))
                except ValueError:
                    continue
            if not isinstance(created, datetime):
                continue
            safe.append(StoryWorkspaceDreamAgentMessage(
                id=str(row["id"]),
                role=row["role"],
                text=text,
                truncated=truncated,
                created_at=created,
            ))
        return safe

    def _has_active_claim(
        self,
        *,
        run_id: str,
        thread_id: str,
        actor_id: str,
    ) -> bool:
        """A durable pending/leased command blocks a second visible send."""

        rows = self._db.execute(
            "SELECT metadata FROM chat_message WHERE thread_id = ? AND role = 'user'",
            (thread_id,),
        ).fetchall()
        for row in rows:
            metadata = _decode(row["metadata"])
            if (
                metadata.get("kind") == STORY_WORKSPACE_DREAM_AGENT_USER_KIND
                and metadata.get("story_workspace_run_id") == run_id
                and str(metadata.get("actor_id") or "") == actor_id
                and metadata.get("dispatch_status") in _ACTIVE
            ):
                return True
        return False

    @staticmethod
    def _assistant_has_authorized_source(
        metadata: dict[str, Any],
        *,
        source_rows: dict[str, Any],
        run_id: str,
        thread_id: str,
        actor_id: str,
    ) -> bool:
        """Prove an assistant reply descends from a permitted Dream user turn."""

        source = metadata.get(STORY_WORKSPACE_DREAM_AGENT_SOURCE_KEY)
        if not isinstance(source, dict):
            return False
        source_id = source.get("message_id")
        source_kind = source.get("kind")
        if not (
            isinstance(source_id, str)
            and source_kind in STORY_WORKSPACE_DREAM_AGENT_SOURCE_KINDS
            and source.get("run_id") == run_id
            and source.get("thread_id") == thread_id
            and str(source.get("actor_id") or "") == actor_id
        ):
            return False
        row = source_rows.get(source_id)
        if row is None or row["thread_id"] != thread_id:
            return False
        source_metadata = _decode(row["metadata"])
        if source_metadata.get("kind") != source_kind:
            return False
        if source_kind == "story-workspace-dream-launch":
            return (
                source_metadata.get("workflowRunId") == run_id
                and source_metadata.get("threadId") == thread_id
                and str(source_metadata.get("actorId") or "") == actor_id
            )
        return (
            source_metadata.get("story_workspace_run_id") == run_id
            and str(source_metadata.get("thread_id") or "") == thread_id
            and str(source_metadata.get("actor_id") or source_metadata.get("actor") or "")
            == actor_id
        )

    async def events(
        self,
        *,
        thread_id: str,
        run_id: str,
        actor_id: str,
        after: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """Normalize only text deltas/final markers; raw frames never escape."""
        if self._thread_factory is None:
            yield "event: status\ndata: {\"lifecycle\":\"idle\"}\n\n"
            return
        snapshot = self._thread_factory.session_snapshot(thread_id)
        if not snapshot or snapshot.get("lifecycle") != "running":
            yield "event: status\ndata: {\"lifecycle\":\"idle\"}\n\n"
            return
        turn_id = str(snapshot.get("current_turn_id") or "")
        turn_matcher = getattr(
            self._thread_factory,
            "is_expected_story_workspace_dream_turn",
            None,
        )
        if callable(turn_matcher) and not turn_matcher(
            thread_id, turn_id, run_id, actor_id
        ):
            yield "event: status\ndata: {\"lifecycle\":\"idle\"}\n\n"
            return
        after_turn, _, after_ordinal = (after or "").partition(":")
        try:
            after_number = int(after_ordinal) if after_turn == turn_id else -1
        except ValueError:
            after_number = -1
        ordinal = -1
        yield f"event: status\ndata: {_json({'lifecycle': 'streaming'})}\n\n"
        # A comment is transport-only: it cannot alter raw-frame ordinals and
        # proves intermediary/proxy connections remain alive without leaking a
        # generic Claude Agent frame.
        yield ": keepalive\n\n"
        try:
            subscribe_expected = getattr(
                self._thread_factory,
                "subscribe_expected_stream",
                None,
            )
            stream = (
                subscribe_expected(thread_id, turn_id)
                if callable(subscribe_expected)
                else self._thread_factory.subscribe_stream(thread_id)
            )
            async for frame in stream:
                if isinstance(frame, str) and frame.lstrip().startswith(":"):
                    yield ": keepalive\n\n"
                    continue
                if not isinstance(frame, str) or not _has_data_frame(frame):
                    continue
                ordinal += 1
                parsed = _parse_sse(frame)
                if parsed is None:
                    continue
                _event, data = parsed
                if ordinal <= after_number:
                    continue
                frame_type = data.get("type")
                if frame_type == "text-delta" and isinstance(data.get("delta"), str):
                    payload = {"turnId": turn_id, "delta": data["delta"]}
                    yield f"id: {turn_id}:{ordinal}\nevent: assistant_text_delta\ndata: {_json(payload)}\n\n"
                elif frame_type == "message-final":
                    payload = {"turnId": turn_id}
                    yield f"id: {turn_id}:{ordinal}\nevent: assistant_message_committed\ndata: {_json(payload)}\n\n"
        finally:
            yield "event: status\ndata: {\"lifecycle\":\"idle\"}\n\n"

    def claim_message(
        self,
        *,
        run_id: str,
        thread_id: str,
        actor_id: str,
        context: StoryWorkspaceDreamRunContext,
        command: StoryWorkspaceDreamAgentMessageCommand,
    ) -> tuple[StoryWorkspaceDreamAgentMessageAccepted, StoryWorkspaceDreamAgentPendingDispatch | None]:
        """Atomically persist/replay one command and prevent a second live turn."""
        if (
            context.workflow_run_id != run_id
            or context.thread_id != thread_id
            or not isinstance(actor_id, str)
            or not actor_id
        ):
            raise StoryWorkspaceDreamAgentMessageError("WORKFLOW_PERMISSION_DENIED", 403)
        accepted, dispatched = story_workspace_read_dream_confirmation_fact(
            self._db, actor_id=actor_id, thread_id=thread_id, run_id=run_id
        )
        running = bool(self._thread_factory and (self._thread_factory.session_snapshot(thread_id) or {}).get("lifecycle") == "running")
        if not accepted or not dispatched or running:
            raise StoryWorkspaceDreamAgentMessageError("DREAM_AGENT_MESSAGE_NOT_READY", 409)
        message_id = _message_id(actor_id, run_id, command.idempotency_key)
        fingerprint = _fingerprint(actor_id, run_id, command)
        now = time.time()
        try:
            self._db.execute("BEGIN IMMEDIATE")
            existing = self._db.execute("SELECT metadata FROM chat_message WHERE id = ?", (message_id,)).fetchone()
            if existing is not None:
                metadata = _decode(existing["metadata"])
                if metadata.get("command_fingerprint") != fingerprint:
                    raise StoryWorkspaceDreamAgentMessageError("IDEMPOTENCY_CONFLICT", 409)
                if metadata.get("kind") != STORY_WORKSPACE_DREAM_AGENT_USER_KIND:
                    raise StoryWorkspaceDreamAgentMessageError("IDEMPOTENCY_CONFLICT", 409)
                status = metadata.get("dispatch_status")
                lease_until = metadata.get("dispatch_claim_lease_until", 0)
                lease_expired = (
                    not isinstance(lease_until, (int, float))
                    or isinstance(lease_until, bool)
                    or not math.isfinite(float(lease_until))
                    or float(lease_until) <= now
                )
                if status in _ACTIVE and lease_expired:
                    previous_metadata = existing["metadata"]
                    metadata["dispatch_status"] = "dispatching"
                    metadata["dispatch_claim_id"] = str(uuid4())
                    metadata["dispatch_claim_lease_until"] = now + _LEASE_SECONDS
                    handoff = self._db.execute(
                        "UPDATE chat_message SET metadata = ? WHERE id = ? AND metadata = ?",
                        (_json(metadata), message_id, previous_metadata),
                    )
                    if handoff.rowcount != 1:
                        raise StoryWorkspaceDreamAgentMessageError("DREAM_AGENT_MESSAGE_BUSY", 409)
                    self._db.commit()
                    pending = StoryWorkspaceDreamAgentPendingDispatch(
                        thread_id, actor_id, context, message_id,
                        [{"type": "text", "text": command.text.strip()}], metadata,
                    )
                    return StoryWorkspaceDreamAgentMessageAccepted(
                        story_workspace_run_id=run_id, message_id=message_id
                    ), pending
                self._db.commit()
                return StoryWorkspaceDreamAgentMessageAccepted(story_workspace_run_id=run_id, message_id=message_id), None
            rows = self._db.execute("SELECT metadata FROM chat_message WHERE thread_id = ? AND role = 'user'", (thread_id,)).fetchall()
            for row in rows:
                metadata = _decode(row["metadata"])
                if (
                    metadata.get("kind") == STORY_WORKSPACE_DREAM_AGENT_USER_KIND
                    and metadata.get("story_workspace_run_id") == run_id
                    and str(metadata.get("actor_id") or "") == actor_id
                    and metadata.get("dispatch_status") in _ACTIVE
                ):
                    raise StoryWorkspaceDreamAgentMessageError("DREAM_AGENT_MESSAGE_BUSY", 409)
            metadata = {
                "kind": STORY_WORKSPACE_DREAM_AGENT_USER_KIND,
                "story_workspace_run_id": run_id,
                "actor_id": actor_id,
                "thread_id": thread_id,
                "idempotency_key": command.idempotency_key,
                "command_fingerprint": fingerprint,
                "dispatch_status": "dispatching",
                "dispatch_claim_id": str(uuid4()),
                "dispatch_claim_lease_until": now + _LEASE_SECONDS,
            }
            parts = [{"type": "text", "text": command.text.strip()}]
            self._db.execute(
                "INSERT INTO chat_message (id, thread_id, role, parts, metadata) VALUES (?, ?, 'user', ?, ?)",
                (message_id, thread_id, _json(parts), _json(metadata)),
            )
            self._db.execute("UPDATE chat_thread SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (thread_id,))
            self._db.commit()
        except StoryWorkspaceDreamAgentMessageError:
            if self._db.in_transaction:
                self._db.rollback()
            raise
        except sqlite3.Error as exc:
            if self._db.in_transaction:
                self._db.rollback()
            raise StoryWorkspaceDreamAgentMessageError("DECK_RUNTIME_CONFIG_UNAVAILABLE", 503) from exc
        pending = StoryWorkspaceDreamAgentPendingDispatch(thread_id, actor_id, context, message_id, parts, metadata)
        return StoryWorkspaceDreamAgentMessageAccepted(story_workspace_run_id=run_id, message_id=message_id), pending

    async def dispatch(self, pending: StoryWorkspaceDreamAgentPendingDispatch) -> bool:
        """Run the already claimed source message on the authoritative thread."""
        if self._thread_factory is None:
            self._release_claim(pending.message_id, pending.metadata["dispatch_claim_id"])
            return False
        heartbeat = asyncio.create_task(
            self._heartbeat_claim(
                pending.message_id,
                pending.metadata["dispatch_claim_id"],
            ),
            name=f"story-workspace-dream-agent-lease-{pending.message_id}",
        )
        try:
            try:
                from claude_agent.service import ClaudeAgentRunRequest
            except ModuleNotFoundError:
                from backend.claude_agent.service import ClaudeAgentRunRequest
            request = ClaudeAgentRunRequest(
                user_id=pending.actor_id, thread_id=pending.thread_id, resume=True,
                message_id=pending.message_id, message_parts=pending.parts,
                message_metadata=pending.metadata, story_workspace_dream_context=pending.context,
            )
            saw_final = False
            finished = False
            async for frame in self._thread_factory.run_streaming(request):
                parsed = _parse_sse(frame) if isinstance(frame, str) else None
                if parsed is None:
                    continue
                _event, event = parsed
                if event.get("type") == "error":
                    break
                if event.get("type") == "message-final":
                    saw_final = True
                if event.get("type") == "finish":
                    finished = event.get("finishReason") != "error"
                    break
            if not (saw_final and finished):
                self._release_claim(pending.message_id, pending.metadata["dispatch_claim_id"])
                return False
            self._mark_dispatched(pending.message_id, pending.metadata["dispatch_claim_id"])
            return True
        except Exception:
            self._release_claim(pending.message_id, pending.metadata["dispatch_claim_id"])
            return False
        finally:
            heartbeat.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await heartbeat

    async def _heartbeat_claim(self, message_id: str, claim_id: str) -> None:
        """Renew a live dispatch lease; database writes always use a fresh DB."""

        while True:
            await asyncio.sleep(_LEASE_HEARTBEAT_SECONDS)
            renewed = await asyncio.to_thread(self._renew_claim, message_id, claim_id)
            if not renewed:
                return

    def _renew_claim(self, message_id: str, claim_id: str) -> bool:
        db = self._db_factory() if self._db_factory is not None else self._db
        close_after = db is not self._db
        try:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT metadata FROM chat_message WHERE id = ?",
                (message_id,),
            ).fetchone()
            previous_metadata = row["metadata"] if row else None
            metadata = _decode(previous_metadata) if previous_metadata else {}
            if (
                metadata.get("dispatch_claim_id") != claim_id
                or metadata.get("dispatch_status") != "dispatching"
            ):
                db.rollback()
                return False
            metadata["dispatch_claim_lease_until"] = time.time() + _LEASE_SECONDS
            renewed = db.execute(
                "UPDATE chat_message SET metadata = ? WHERE id = ? AND metadata = ?",
                (_json(metadata), message_id, previous_metadata),
            )
            if renewed.rowcount != 1:
                db.rollback()
                return False
            db.commit()
            return True
        except sqlite3.Error:
            if db.in_transaction:
                db.rollback()
            return False
        finally:
            if close_after:
                db.close()

    def _mark_dispatched(self, message_id: str, claim_id: str) -> bool:
        return self._update_claim(message_id, claim_id, dispatched=True)

    def _release_claim(self, message_id: str, claim_id: str) -> bool:
        return self._update_claim(message_id, claim_id, dispatched=False)

    def _update_claim(self, message_id: str, claim_id: str, *, dispatched: bool) -> bool:
        db = self._db_factory() if self._db_factory is not None else self._db
        close_after = db is not self._db
        try:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT metadata FROM chat_message WHERE id = ?", (message_id,)).fetchone()
            previous_metadata = row["metadata"] if row else None
            metadata = _decode(previous_metadata) if previous_metadata else {}
            if (
                metadata.get("dispatch_claim_id") != claim_id
                or metadata.get("dispatch_status") != "dispatching"
            ):
                db.rollback()
                return False
            metadata["dispatch_status"] = "dispatched" if dispatched else "pending"
            metadata["dispatch_claim_lease_until"] = 0
            updated = db.execute(
                "UPDATE chat_message SET metadata = ? WHERE id = ? AND metadata = ?",
                (_json(metadata), message_id, previous_metadata),
            )
            if updated.rowcount != 1:
                db.rollback()
                return False
            db.commit()
            return True
        except sqlite3.Error:
            if db.in_transaction:
                db.rollback()
            return False
        finally:
            if close_after:
                db.close()
