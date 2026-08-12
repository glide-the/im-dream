"""Durable internal Dream business-command dispatch on a canonical Chat thread.

This module is intentionally not a browser conversation boundary.  It retains
only the claim/lease/ack machinery used by server-authorized episode/workflow
commands.  Conversation history, live events, tool confirmations, reconnect
and Stop are owned by the canonical Claude Agent thread APIs.
"""

from __future__ import annotations

from psycopg import Error as PostgresError

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import inspect
import json
import logging
import math
import re
import time
from typing import Any, Callable
from uuid import uuid4

try:
    from story_workspace.contracts import (
        StoryWorkspaceDreamInternalCommand,
        StoryWorkspaceDreamInternalCommandAccepted,
        StoryWorkspaceDreamRunContext,
        StoryWorkspaceEpisodeAction,
    )
    from services.story_workspace.dream_confirmation_service import (
        story_workspace_read_dream_confirmation_fact,
    )
    from services.story_workspace.dream_lifecycle_observer import (
        drain_normalized_agent_turn,
    )
except ModuleNotFoundError:
    from backend.story_workspace.contracts import (
        StoryWorkspaceDreamInternalCommand,
        StoryWorkspaceDreamInternalCommandAccepted,
        StoryWorkspaceDreamRunContext,
        StoryWorkspaceEpisodeAction,
    )
    from backend.services.story_workspace.dream_confirmation_service import (
        story_workspace_read_dream_confirmation_fact,
    )
    from backend.services.story_workspace.dream_lifecycle_observer import (
        drain_normalized_agent_turn,
    )


# Keep the persisted discriminator stable so a server-authorized Episode command
# claimed before deployment can retain its lease/idempotency semantics. It has
# no HTTP or SSE surface and is not accepted from an untrusted request body.
STORY_WORKSPACE_DREAM_INTERNAL_COMMAND_KIND = "story-workspace-dream-agent-user"
_ACTIVE = frozenset({"pending", "dispatching"})
_LEASE_SECONDS = 60
_LEASE_HEARTBEAT_SECONDS = 15
_PROVENANCE_KEY = "story_workspace_episode_action"
_PROVENANCE_SCHEMA = "story-workspace-episode-action/v1"
_RECOVERY_ACTION = "recover_first_episode_binding"
_REVISION_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_EPISODE_PATTERN = re.compile(r"^[0-9a-f]{32}$")
_RUN_PATTERN = re.compile(r"^run_[0-9a-f]{32}$")
logger = logging.getLogger(__name__)


class StoryWorkspaceDreamInternalCommandError(RuntimeError):
    """Stable internal error mapped by the owning business API."""

    def __init__(self, code: str, status_code: int) -> None:
        super().__init__(code)
        self.code = code
        self.status_code = status_code


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _decode(value: Any) -> dict[str, Any]:
    try:
        loaded = json.loads(value) if isinstance(value, str) else value
    except (TypeError, ValueError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _validated_provenance(
    value: Any,
    *,
    run_id: str,
    thread_id: str,
    actor_id: str,
) -> dict[str, Any]:
    """Return one strict server-only Episode authorization envelope."""

    required = {
        "schema",
        "workflow_run_id",
        "thread_id",
        "actor_id",
        "action",
        "episode_uid",
        "input_revision",
        "expected_facts_revision",
        "expected_manifest_revision",
        "expected_workflow_revision",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise StoryWorkspaceDreamInternalCommandError(
            "WORKFLOW_PERMISSION_DENIED",
            403,
        )
    action = value.get("action")
    allowed_actions = {item.value for item in StoryWorkspaceEpisodeAction}
    allowed_actions.add(_RECOVERY_ACTION)
    episode_uid = value.get("episode_uid")
    if (
        value.get("schema") != _PROVENANCE_SCHEMA
        or value.get("workflow_run_id") != run_id
        or value.get("thread_id") != thread_id
        or str(value.get("actor_id") or "") != actor_id
        or _RUN_PATTERN.fullmatch(run_id) is None
        or action not in allowed_actions
        or (
            action == _RECOVERY_ACTION
            and episode_uid is not None
        )
        or (
            action != _RECOVERY_ACTION
            and (
                not isinstance(episode_uid, str)
                or _EPISODE_PATTERN.fullmatch(episode_uid) is None
            )
        )
    ):
        raise StoryWorkspaceDreamInternalCommandError(
            "WORKFLOW_PERMISSION_DENIED",
            403,
        )
    facts_revision = value.get("expected_facts_revision")
    if facts_revision is not None and (
        isinstance(facts_revision, bool)
        or not isinstance(facts_revision, int)
        or facts_revision < 0
    ):
        raise StoryWorkspaceDreamInternalCommandError(
            "WORKFLOW_PERMISSION_DENIED",
            403,
        )
    for field in (
        "input_revision",
        "expected_manifest_revision",
        "expected_workflow_revision",
    ):
        revision = value.get(field)
        if revision is not None and (
            not isinstance(revision, str)
            or _REVISION_PATTERN.fullmatch(revision) is None
        ):
            raise StoryWorkspaceDreamInternalCommandError(
                "WORKFLOW_PERMISSION_DENIED",
                403,
            )
    return dict(value)


def _run_is_owned(
    db: Any,
    *,
    run_id: str,
    thread_id: str,
    actor_id: str,
) -> bool:
    try:
        numeric_actor = int(actor_id)
        row = db.execute(
            "SELECT run.id FROM workflow_runs AS run "
            "JOIN story_workspace_workspaces AS workspace "
            "ON workspace.id = run.workspace_id "
            "WHERE run.id = %s AND run.source_voice_thread_id = %s "
            "AND run.created_by = %s AND workspace.owner_id = %s",
            (run_id, thread_id, actor_id, numeric_actor),
        ).fetchone()
    except Exception as exc:
        raise StoryWorkspaceDreamInternalCommandError(
            "DECK_RUNTIME_CONFIG_UNAVAILABLE",
            503,
        ) from exc
    return row is not None


def story_workspace_guard_persisted_dream_internal_command_turn(
    db: Any,
    *,
    thread_id: str,
    actor_id: str,
    message_id: str | None,
    parts: list[Any],
    metadata: dict[str, Any] | None,
) -> bool:
    """Fail closed unless the request owns the exact current durable claim."""

    if not isinstance(message_id, str) or not message_id.startswith("dream_agent_"):
        return False
    row = db.execute(
        "SELECT message.thread_id, message.role, message.parts, message.metadata, "
        "thread.user_id "
        "FROM chat_message AS message JOIN chat_thread AS thread "
        "ON thread.id = message.thread_id WHERE message.id = %s",
        (message_id,),
    ).fetchone()
    if row is None:
        raise StoryWorkspaceDreamInternalCommandError("IDEMPOTENCY_CONFLICT", 409)
    stored = _decode(row["metadata"])
    try:
        stored_parts = json.loads(row["parts"] or "[]")
    except (TypeError, ValueError) as exc:
        raise StoryWorkspaceDreamInternalCommandError(
            "IDEMPOTENCY_CONFLICT", 409
        ) from exc
    run_id = stored.get("story_workspace_run_id")
    key = stored.get("idempotency_key")
    claim_id = stored.get("dispatch_claim_id")
    request_claim_id = (
        metadata.get("dispatch_claim_id") if isinstance(metadata, dict) else None
    )
    stored_lease = stored.get("dispatch_claim_lease_until")
    request_lease = (
        metadata.get("dispatch_claim_lease_until")
        if isinstance(metadata, dict)
        else None
    )
    immutable_stored = {
        field: value
        for field, value in stored.items()
        if field != "dispatch_claim_lease_until"
    }
    immutable_request = {
        field: value
        for field, value in (metadata or {}).items()
        if field != "dispatch_claim_lease_until"
    }
    text = (
        stored_parts[0].get("text", "").strip()
        if isinstance(stored_parts, list)
        and len(stored_parts) == 1
        and isinstance(stored_parts[0], dict)
        and set(stored_parts[0]) == {"type", "text"}
        and stored_parts[0].get("type") == "text"
        and isinstance(stored_parts[0].get("text"), str)
        else ""
    )
    valid_lease = lambda value: (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and float(value) > 0
    )
    expected_metadata_fields = {
        "kind",
        "visibility",
        "story_workspace_run_id",
        "actor_id",
        "thread_id",
        "idempotency_key",
        "command_fingerprint",
        "dispatch_status",
        "dispatch_claim_id",
        "dispatch_claim_lease_until",
        _PROVENANCE_KEY,
    }
    valid = (
        row["thread_id"] == thread_id
        and row["role"] == "user"
        and str(row["user_id"]) == str(actor_id)
        and isinstance(parts, list)
        and isinstance(metadata, dict)
        and stored.get("kind") == STORY_WORKSPACE_DREAM_INTERNAL_COMMAND_KIND
        and metadata.get("kind") == STORY_WORKSPACE_DREAM_INTERNAL_COMMAND_KIND
        and stored.get("visibility") == "system-hidden"
        and metadata.get("visibility") == "system-hidden"
        and set(stored) == expected_metadata_fields
        and set(metadata) == expected_metadata_fields
        and stored.get("dispatch_status") == "dispatching"
        and metadata.get("dispatch_status") == "dispatching"
        and isinstance(run_id, str)
        and isinstance(key, str)
        and isinstance(claim_id, str)
        and bool(claim_id)
        and request_claim_id == claim_id
        and valid_lease(stored_lease)
        and valid_lease(request_lease)
        and float(stored_lease) > time.time()
        and float(request_lease) <= float(stored_lease)
        and immutable_stored == immutable_request
        and _json(stored_parts) == _json(parts)
        and bool(text)
        and message_id == _message_id(str(actor_id), run_id, key)
    )
    if not valid:
        raise StoryWorkspaceDreamInternalCommandError("IDEMPOTENCY_CONFLICT", 409)
    try:
        command = StoryWorkspaceDreamInternalCommand(
            text=text,
            idempotencyKey=key,
        )
    except Exception as exc:
        raise StoryWorkspaceDreamInternalCommandError(
            "IDEMPOTENCY_CONFLICT", 409
        ) from exc
    if stored.get("command_fingerprint") != _fingerprint(
        str(actor_id),
        run_id,
        command,
        _validated_provenance(
            stored.get(_PROVENANCE_KEY),
            run_id=run_id,
            thread_id=thread_id,
            actor_id=str(actor_id),
        ),
    ):
        raise StoryWorkspaceDreamInternalCommandError("IDEMPOTENCY_CONFLICT", 409)
    if not _run_is_owned(
        db,
        run_id=run_id,
        thread_id=thread_id,
        actor_id=str(actor_id),
    ):
        raise StoryWorkspaceDreamInternalCommandError(
            "WORKFLOW_PERMISSION_DENIED",
            403,
        )
    return True


@dataclass(frozen=True)
class StoryWorkspaceDreamInternalPendingDispatch:
    """Server-derived command envelope; never accepted from an HTTP body."""

    thread_id: str
    actor_id: str
    context: StoryWorkspaceDreamRunContext
    message_id: str
    parts: list[dict[str, str]]
    metadata: dict[str, Any]


class StoryWorkspaceDreamInternalCommandCoordinator:
    """Own dispatch tasks and reconcile expired durable claims after restart."""

    def __init__(
        self,
        dispatcher: Callable[[StoryWorkspaceDreamInternalPendingDispatch], Any],
        *,
        recoverer: Callable[[int], Any] | None = None,
        reconcile_interval_s: float = 2.0,
        max_dispatch_tasks: int = 8,
    ) -> None:
        self._dispatcher = dispatcher
        self._recoverer = recoverer
        self._reconcile_interval_s = max(float(reconcile_interval_s), 0.01)
        self._max_dispatch_tasks = max(1, int(max_dispatch_tasks))
        self._tasks: dict[tuple[str, str], asyncio.Task[Any]] = {}
        self._loop_task: asyncio.Task[None] | None = None
        self._stop_event: asyncio.Event | None = None
        self._accepting = True
        self._reconcile_lock = asyncio.Lock()

    def start(self) -> None:
        """Start the bounded recovery scan once an event loop is available."""

        self._accepting = True
        if self._recoverer is None:
            return
        if self._loop_task is not None and not self._loop_task.done():
            return
        self._stop_event = asyncio.Event()
        self._loop_task = asyncio.create_task(
            self._run_reconciler(),
            name="story-workspace-dream-command-reconciler",
        )

    def schedule(self, pending: StoryWorkspaceDreamInternalPendingDispatch) -> bool:
        claim_id = pending.metadata.get("dispatch_claim_id")
        if not isinstance(claim_id, str) or not claim_id or not self._accepting:
            return False
        key = (pending.message_id, claim_id)
        existing = self._tasks.get(key)
        if existing is not None and not existing.done():
            return False
        prior_tasks = [
            task
            for (message_id, other_claim_id), task in self._tasks.items()
            if message_id == pending.message_id
            and other_claim_id != claim_id
            and not task.done()
        ]
        running = sum(not task.done() for task in self._tasks.values())
        if not prior_tasks and running >= self._max_dispatch_tasks:
            return False

        async def dispatch_after_handoff() -> Any:
            if prior_tasks:
                for prior in prior_tasks:
                    prior.cancel()
                await asyncio.gather(*prior_tasks, return_exceptions=True)
            return await self._dispatcher(pending)

        task = asyncio.create_task(
            dispatch_after_handoff(),
            name=(
                "story-workspace-dream-command-"
                f"{pending.message_id}-{claim_id}"
            ),
        )
        self._tasks[key] = task
        task.add_done_callback(
            lambda completed, task_key=key: self._task_done(
                task_key,
                completed,
            )
        )
        return True

    def _task_done(
        self,
        key: tuple[str, str],
        task: asyncio.Task[Any],
    ) -> None:
        if self._tasks.get(key) is not task:
            return
        self._tasks.pop(key, None)
        if task.cancelled():
            return
        try:
            failure = task.exception()
        except asyncio.CancelledError:
            return
        if failure is not None:
            logger.error(
                "Dream internal command task failed message_id=%s",
                key[0],
                exc_info=(type(failure), failure, failure.__traceback__),
            )

    async def wait_for_idle(self) -> None:
        while self._tasks:
            snapshot = list(self._tasks.items())
            await asyncio.gather(
                *(task for _key, task in snapshot),
                return_exceptions=True,
            )
            # Do not depend on call_soon done callbacks receiving a scheduling
            # turn after gather returns already-completed Futures.
            for key, task in snapshot:
                if task.done():
                    self._task_done(key, task)

    async def reconcile_once(self) -> int:
        """Recover only server-authorized pending or expired-lease envelopes."""

        async with self._reconcile_lock:
            if self._recoverer is None:
                return 0
            if not self._accepting:
                return 0
            available = self._max_dispatch_tasks - sum(
                not task.done() for task in self._tasks.values()
            )
            if available <= 0:
                return 0
            recovered = self._recoverer(available)
            if inspect.isawaitable(recovered):
                recovered = await recovered
            if not isinstance(recovered, (list, tuple)):
                raise TypeError(
                    "Dream internal command recoverer must return a sequence"
                )
            return sum(
                1
                for pending in recovered
                if isinstance(pending, StoryWorkspaceDreamInternalPendingDispatch)
                and self.schedule(pending)
            )

    async def aclose(self) -> None:
        self._accepting = False
        stop_event = self._stop_event
        if stop_event is not None:
            stop_event.set()
        loop_task = self._loop_task
        if loop_task is not None and not loop_task.done():
            loop_task.cancel()
        if loop_task is not None:
            await asyncio.gather(loop_task, return_exceptions=True)
        self._loop_task = None
        self._stop_event = None

        tasks = list(self._tasks.values())
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.clear()

    def diagnostics(self) -> dict[str, int]:
        return {
            "owned_tasks": len(self._tasks),
            "running_tasks": sum(not task.done() for task in self._tasks.values()),
            "reconcile_tasks": int(
                self._loop_task is not None and not self._loop_task.done()
            ),
        }

    async def _run_reconciler(self) -> None:
        try:
            while True:
                try:
                    await self.reconcile_once()
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.exception("Dream internal command reconciliation scan failed")
                stop_event = self._stop_event
                if stop_event is None:
                    return
                try:
                    await asyncio.wait_for(
                        stop_event.wait(),
                        timeout=self._reconcile_interval_s,
                    )
                    return
                except asyncio.TimeoutError:
                    continue
        except asyncio.CancelledError:
            raise


def _message_id(actor_id: str, run_id: str, key: str) -> str:
    digest = hashlib.sha256(f"{actor_id}\n{run_id}\n{key}".encode("utf-8")).hexdigest()
    return f"dream_agent_{digest}"


def _fingerprint(
    actor_id: str,
    run_id: str,
    command: StoryWorkspaceDreamInternalCommand,
    provenance: dict[str, Any],
) -> str:
    value = (
        f"{actor_id}\n{run_id}\n{command.idempotency_key}\n"
        f"{command.text.strip()}\n{_json(provenance)}"
    )
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class StoryWorkspaceDreamInternalCommandService:
    """Claim and drain internal business commands on the shared thread runtime."""

    def __init__(
        self,
        db: Any,
        *,
        thread_factory: Any | None = None,
        db_factory: Callable[[], Any] | None = None,
    ) -> None:
        self._db = db
        self._thread_factory = thread_factory
        self._db_factory = db_factory

    def claim_message(
        self,
        *,
        run_id: str,
        thread_id: str,
        actor_id: str,
        context: StoryWorkspaceDreamRunContext,
        command: StoryWorkspaceDreamInternalCommand,
        provenance: dict[str, Any],
    ) -> tuple[
        StoryWorkspaceDreamInternalCommandAccepted,
        StoryWorkspaceDreamInternalPendingDispatch | None,
    ]:
        """Atomically claim one server-authorized business command."""

        if (
            context.workflow_run_id != run_id
            or context.thread_id != thread_id
            or not isinstance(actor_id, str)
            or not actor_id
        ):
            raise StoryWorkspaceDreamInternalCommandError("WORKFLOW_PERMISSION_DENIED", 403)
        trusted_provenance = _validated_provenance(
            provenance,
            run_id=run_id,
            thread_id=thread_id,
            actor_id=actor_id,
        )
        accepted, dispatched = story_workspace_read_dream_confirmation_fact(
            self._db,
            actor_id=actor_id,
            thread_id=thread_id,
            run_id=run_id,
        )
        running = bool(
            self._thread_factory
            and (
                self._thread_factory.session_snapshot(thread_id) or {}
            ).get("lifecycle")
            == "running"
        )
        if not accepted or not dispatched or running:
            raise StoryWorkspaceDreamInternalCommandError(
                "DREAM_AGENT_MESSAGE_NOT_READY",
                409,
            )

        message_id = _message_id(actor_id, run_id, command.idempotency_key)
        fingerprint = _fingerprint(
            actor_id,
            run_id,
            command,
            trusted_provenance,
        )
        now = time.time()
        try:
            self._db.execute("BEGIN")
            existing = self._db.execute(
                "SELECT metadata FROM chat_message WHERE id = %s",
                (message_id,),
            ).fetchone()
            if existing is not None:
                metadata = _decode(existing["metadata"])
                if (
                    metadata.get("command_fingerprint") != fingerprint
                    or metadata.get("kind")
                    != STORY_WORKSPACE_DREAM_INTERNAL_COMMAND_KIND
                    or metadata.get(_PROVENANCE_KEY) != trusted_provenance
                ):
                    raise StoryWorkspaceDreamInternalCommandError(
                        "IDEMPOTENCY_CONFLICT",
                        409,
                    )
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
                        "UPDATE chat_message SET metadata = %s "
                        "WHERE id = %s AND metadata = %s",
                        (_json(metadata), message_id, previous_metadata),
                    )
                    if handoff.rowcount != 1:
                        raise StoryWorkspaceDreamInternalCommandError(
                            "DREAM_AGENT_MESSAGE_BUSY",
                            409,
                        )
                    self._db.commit()
                    pending = StoryWorkspaceDreamInternalPendingDispatch(
                        thread_id=thread_id,
                        actor_id=actor_id,
                        context=context,
                        message_id=message_id,
                        parts=[{"type": "text", "text": command.text.strip()}],
                        metadata=metadata,
                    )
                    return (
                        StoryWorkspaceDreamInternalCommandAccepted(
                            story_workspace_run_id=run_id,
                            message_id=message_id,
                        ),
                        pending,
                    )
                self._db.commit()
                return (
                    StoryWorkspaceDreamInternalCommandAccepted(
                        story_workspace_run_id=run_id,
                        message_id=message_id,
                    ),
                    None,
                )

            rows = self._db.execute(
                "SELECT metadata FROM chat_message "
                "WHERE thread_id = %s AND role = 'user'",
                (thread_id,),
            ).fetchall()
            for row in rows:
                metadata = _decode(row["metadata"])
                if (
                    metadata.get("kind")
                    == STORY_WORKSPACE_DREAM_INTERNAL_COMMAND_KIND
                    and metadata.get("story_workspace_run_id") == run_id
                    and str(metadata.get("actor_id") or "") == actor_id
                    and metadata.get("dispatch_status") in _ACTIVE
                ):
                    raise StoryWorkspaceDreamInternalCommandError(
                        "DREAM_AGENT_MESSAGE_BUSY",
                        409,
                    )

            metadata = {
                "kind": STORY_WORKSPACE_DREAM_INTERNAL_COMMAND_KIND,
                "visibility": "system-hidden",
                "story_workspace_run_id": run_id,
                "actor_id": actor_id,
                "thread_id": thread_id,
                "idempotency_key": command.idempotency_key,
                "command_fingerprint": fingerprint,
                "dispatch_status": "dispatching",
                "dispatch_claim_id": str(uuid4()),
                "dispatch_claim_lease_until": now + _LEASE_SECONDS,
                _PROVENANCE_KEY: trusted_provenance,
            }
            parts = [{"type": "text", "text": command.text.strip()}]
            self._db.execute(
                "INSERT INTO chat_message "
                "(id, thread_id, role, parts, metadata) "
                "VALUES (%s, %s, 'user', %s, %s)",
                (message_id, thread_id, _json(parts), _json(metadata)),
            )
            self._db.execute(
                "UPDATE chat_thread SET updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                (thread_id,),
            )
            self._db.commit()
        except StoryWorkspaceDreamInternalCommandError:
            if self._db.in_transaction:
                self._db.rollback()
            raise
        except PostgresError as exc:
            if self._db.in_transaction:
                self._db.rollback()
            raise StoryWorkspaceDreamInternalCommandError(
                "DECK_RUNTIME_CONFIG_UNAVAILABLE",
                503,
            ) from exc

        pending = StoryWorkspaceDreamInternalPendingDispatch(
            thread_id=thread_id,
            actor_id=actor_id,
            context=context,
            message_id=message_id,
            parts=parts,
            metadata=metadata,
        )
        return (
            StoryWorkspaceDreamInternalCommandAccepted(
                story_workspace_run_id=run_id,
                message_id=message_id,
            ),
            pending,
        )

    async def dispatch(self, pending: StoryWorkspaceDreamInternalPendingDispatch) -> bool:
        """Drain one claimed command through canonical ``factory.run_events``."""

        claim_id = str(pending.metadata.get("dispatch_claim_id") or "")
        if self._thread_factory is None or not claim_id:
            self._release_claim(pending.message_id, claim_id)
            return False
        heartbeat: asyncio.Task[bool] | None = None
        turn_task: asyncio.Task[Any] | None = None
        try:
            try:
                from claude_agent.service import ClaudeAgentRunRequest
            except ModuleNotFoundError:
                from backend.claude_agent.service import ClaudeAgentRunRequest

            request = ClaudeAgentRunRequest(
                user_id=pending.actor_id,
                thread_id=pending.thread_id,
                resume=True,
                message_id=pending.message_id,
                message_parts=pending.parts,
                message_metadata=pending.metadata,
            )
            heartbeat = asyncio.create_task(
                self._heartbeat_claim(pending.message_id, claim_id),
                name=f"story-workspace-dream-command-lease-{pending.message_id}",
            )
            turn_task = asyncio.create_task(
                drain_normalized_agent_turn(self._thread_factory, request),
                name=f"story-workspace-dream-command-turn-{pending.message_id}",
            )
            done, _pending = await asyncio.wait(
                {heartbeat, turn_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            if heartbeat in done and turn_task not in done:
                # A failed renewal means this process no longer owns the
                # durable claim.  Stop its in-flight turn before another owner
                # can safely take over the same message id.
                turn_task.cancel()
                await asyncio.gather(turn_task, return_exceptions=True)
                return False
            result = await turn_task
            if not result.completed:
                self._release_claim(pending.message_id, claim_id)
                return False
            return self._mark_dispatched(pending.message_id, claim_id)
        except asyncio.CancelledError:
            # Shutdown leaves the durable dispatching lease intact. A later
            # owner replay of the same idempotency key can reclaim it after
            # expiry; marking it failed here would permanently lose the work.
            raise
        except Exception:
            self._release_claim(pending.message_id, claim_id)
            return False
        finally:
            for task in (turn_task, heartbeat):
                if task is not None and not task.done():
                    task.cancel()
            owned = [task for task in (turn_task, heartbeat) if task is not None]
            if owned:
                await asyncio.gather(*owned, return_exceptions=True)

    async def _heartbeat_claim(self, message_id: str, claim_id: str) -> bool:
        while True:
            await asyncio.sleep(_LEASE_HEARTBEAT_SECONDS)
            renewed = await asyncio.to_thread(
                self._renew_claim,
                message_id,
                claim_id,
            )
            if not renewed:
                return False

    def _renew_claim(self, message_id: str, claim_id: str) -> bool:
        db = self._db_factory() if self._db_factory is not None else self._db
        close_after = db is not self._db
        try:
            db.execute("BEGIN")
            row = db.execute(
                "SELECT metadata FROM chat_message WHERE id = %s",
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
                "UPDATE chat_message SET metadata = %s "
                "WHERE id = %s AND metadata = %s",
                (_json(metadata), message_id, previous_metadata),
            )
            if renewed.rowcount != 1:
                db.rollback()
                return False
            db.commit()
            return True
        except PostgresError:
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

    def _update_claim(
        self,
        message_id: str,
        claim_id: str,
        *,
        dispatched: bool,
    ) -> bool:
        db = self._db_factory() if self._db_factory is not None else self._db
        close_after = db is not self._db
        try:
            db.execute("BEGIN")
            row = db.execute(
                "SELECT metadata FROM chat_message WHERE id = %s",
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
            metadata["dispatch_status"] = "dispatched" if dispatched else "failed"
            metadata["dispatch_claim_lease_until"] = 0
            if dispatched:
                metadata.pop("dispatch_error_code", None)
                metadata.pop("dispatch_failed_at", None)
            else:
                metadata["dispatch_error_code"] = "DREAM_AGENT_DISPATCH_FAILED"
                metadata["dispatch_failed_at"] = datetime.now(UTC).isoformat()
            updated = db.execute(
                "UPDATE chat_message SET metadata = %s "
                "WHERE id = %s AND metadata = %s",
                (_json(metadata), message_id, previous_metadata),
            )
            if updated.rowcount != 1:
                db.rollback()
                return False
            db.commit()
            return True
        except PostgresError:
            if db.in_transaction:
                db.rollback()
            return False
        finally:
            if close_after:
                db.close()


__all__ = [
    "STORY_WORKSPACE_DREAM_INTERNAL_COMMAND_KIND",
    "StoryWorkspaceDreamInternalCommandCoordinator",
    "StoryWorkspaceDreamInternalCommandError",
    "StoryWorkspaceDreamInternalCommandService",
    "StoryWorkspaceDreamInternalPendingDispatch",
    "story_workspace_guard_persisted_dream_internal_command_turn",
]
