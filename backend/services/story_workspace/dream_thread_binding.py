# [Input] Authenticated actor, an already owner-scoped Chat thread, and workflow binding rows.
# [Output] Resolve the unique trusted Dream retry leaf into StoryWorkspaceDreamRunContext.
# [Pos] Server-only authorization seam between canonical Chat ingress and Dream runtime context.
# [Sync] 2026-08-31: separate immutable launch-Agent provenance from the mutable same-Deck next-turn Agent.

"""Resolve a Dream workflow binding from an authenticated Chat thread.

The browser deliberately sends only ``thread_id`` to the canonical Chat API.
This module reverse-resolves workflow authority from database facts and never
accepts a run, actor, Deck, or retry selector from the request body.
"""

from __future__ import annotations

import logging
import re
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable, Mapping

from pydantic import ValidationError

try:
    from models.workflow_run import RunStatus, TERMINAL_RUN_STATUSES
    from services.story_workspace.canonical_project_instruction import (
        story_workspace_canonical_project_fallback_slug,
    )
    from story_workspace.contracts import StoryWorkspaceDreamRunContext
except ModuleNotFoundError:  # pragma: no cover - package-style test imports
    from backend.models.workflow_run import RunStatus, TERMINAL_RUN_STATUSES
    from backend.services.story_workspace.canonical_project_instruction import (
        story_workspace_canonical_project_fallback_slug,
    )
    from backend.story_workspace.contracts import StoryWorkspaceDreamRunContext

logger = logging.getLogger(__name__)

_MAX_ATTEMPTS_PER_THREAD = 256
_RUN_ID = re.compile(r"^run_[0-9a-f]{32}$")
_ACTIVE_DREAM_RUN_STATUSES = frozenset(
    {
        RunStatus.QUEUED,
        RunStatus.RUNNING,
        RunStatus.OUTPUT_VALIDATING,
        RunStatus.PENDING_REVIEW,
        RunStatus.CONFIRMED,
    }
)
_RETRY_PARENT_STATUSES = frozenset(
    {RunStatus.FAILED, RunStatus.REJECTED, RunStatus.CANCELLED}
)


class DreamThreadBindingConflict(RuntimeError):
    """An owned thread has Dream rows that cannot identify one safe authority."""

    code = "DREAM_THREAD_BINDING_CONFLICT"
    status_code = 409
    public_message = "This conversation's Dream binding is unavailable."
    retryable = False

    def __init__(self, reason: str) -> None:
        # ``reason`` is an internal bounded classifier, not row data.  Routes
        # return only ``code`` so graph contents cannot leak to the browser.
        self.reason = reason[:80]
        super().__init__(self.code)


@dataclass(frozen=True)
class _DreamAttempt:
    workflow_run_id: str
    retry_of_run_id: str | None
    status: str
    workspace_id: str
    created_by: str
    source_voice_thread_id: str
    source_message_id: object
    source_message_time: object
    source_message_thread_id: str
    source_message_role: str
    source_message_metadata: dict[str, Any]
    input_hash: str
    workflow_definition_ref: str
    deck_plugin_manifest_hash: str
    deck_plugin_id: str
    deck_plugin_version: str
    deck_plugin_binding_id: str
    binding_revision: int
    deck_runtime_snapshot_id: str
    runtime_plugin_lock_id: str
    workspace_owner_id: object
    binding_deck_id: object
    binding_workspace_id: object
    binding_deck_plugin_id: object
    binding_deck_plugin_version: object
    binding_revision_actual: object

    @classmethod
    def from_row(cls, row: Any) -> "_DreamAttempt":
        try:
            def required_text(key: str) -> str:
                value = row[key]
                if not isinstance(value, str) or not value.strip():
                    raise TypeError(key)
                return value

            revision = row["binding_revision"]
            if isinstance(revision, bool) or not isinstance(revision, int):
                raise TypeError("binding_revision")
            source_message_time = row["source_message_time"]
            if (
                not isinstance(source_message_time, (str, datetime))
                or (
                    isinstance(source_message_time, str)
                    and not source_message_time.strip()
                )
            ):
                raise TypeError("source_message_time")
            source_metadata_raw = row["source_message_metadata"]
            if isinstance(source_metadata_raw, str):
                source_metadata = json.loads(source_metadata_raw)
            else:
                source_metadata = source_metadata_raw
            if not isinstance(source_metadata, dict):
                raise TypeError("source_message_metadata")
            return cls(
                workflow_run_id=required_text("workflow_run_id"),
                retry_of_run_id=(
                    required_text("retry_of_run_id")
                    if row["retry_of_run_id"] is not None
                    else None
                ),
                status=required_text("status"),
                workspace_id=required_text("workspace_id"),
                created_by=str(row["created_by"]),
                source_voice_thread_id=required_text("source_voice_thread_id"),
                source_message_id=required_text("source_message_id"),
                source_message_time=source_message_time,
                source_message_thread_id=required_text(
                    "source_message_thread_id"
                ),
                source_message_role=required_text("source_message_role"),
                source_message_metadata=dict(source_metadata),
                input_hash=required_text("input_hash"),
                workflow_definition_ref=required_text("workflow_definition_ref"),
                deck_plugin_manifest_hash=required_text("deck_plugin_manifest_hash"),
                deck_plugin_id=required_text("deck_plugin_id"),
                deck_plugin_version=required_text("deck_plugin_version"),
                deck_plugin_binding_id=required_text("deck_plugin_binding_id"),
                binding_revision=revision,
                deck_runtime_snapshot_id=required_text("deck_runtime_snapshot_id"),
                runtime_plugin_lock_id=required_text("runtime_plugin_lock_id"),
                workspace_owner_id=row["workspace_owner_id"],
                binding_deck_id=row["binding_deck_id"],
                binding_workspace_id=row["binding_workspace_id"],
                binding_deck_plugin_id=row["binding_deck_plugin_id"],
                binding_deck_plugin_version=row["binding_deck_plugin_version"],
                binding_revision_actual=row["binding_revision_actual"],
            )
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            raise DreamThreadBindingConflict("malformed_attempt") from exc

    def frozen_source(self) -> tuple[object, ...]:
        """Fields that ``WorkflowRunService.retry_run`` must preserve."""

        return (
            self.workspace_id,
            self.deck_plugin_id,
            self.deck_plugin_version,
            self.workflow_definition_ref,
            self.deck_runtime_snapshot_id,
            self.deck_plugin_manifest_hash,
            self.deck_plugin_binding_id,
            self.binding_revision,
            self.runtime_plugin_lock_id,
            self.input_hash,
            self.source_voice_thread_id,
            self.source_message_id,
            str(self.source_message_time) if self.source_message_time is not None else None,
            self.source_message_thread_id,
            self.source_message_role,
            json.dumps(
                self.source_message_metadata,
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            ),
        )


def _sha256_json(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _validate_source_message_provenance(
    attempts: tuple[_DreamAttempt, ...],
    *,
    root_run_id: str,
    actor_id: str,
    thread_id: str,
    workspace_id: str,
    deck_id: str,
) -> None:
    """Prove the retry graph still originates from one server launch row.

    ``workflow_runs.input_hash`` is the preflight hash of ``{"goal": ...}``,
    while the source row's ``requestFingerprint`` also binds the Deck and
    optional voice.  Recomputing both hashes links the two records without
    assuming those deliberately different digests are equal.
    """

    expected_metadata: str | None = None
    for attempt in attempts:
        metadata = attempt.source_message_metadata
        canonical = json.dumps(
            metadata,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        if expected_metadata is None:
            expected_metadata = canonical
        elif canonical != expected_metadata:
            raise DreamThreadBindingConflict("source_metadata_mismatch")

        goal = metadata.get("goal")
        agent_id = metadata.get("agentId")
        launch_agent_is_valid = agent_id is None or (
            isinstance(agent_id, str)
            and bool(agent_id)
            and agent_id == agent_id.strip()
        )
        fingerprint_payload: dict[str, Any] = {
            "deck_id": deck_id,
            "goal": goal,
        }
        if agent_id is not None:
            fingerprint_payload["agent_id"] = agent_id
        valid = (
            attempt.source_message_thread_id == thread_id
            and attempt.source_message_role == "user"
            and metadata.get("kind") == "story-workspace-dream-launch"
            and metadata.get("schemaVersion")
            == "story-workspace-dream-launch/v1"
            and metadata.get("visibility") == "system-hidden"
            and metadata.get("actorId") == actor_id
            and metadata.get("workspaceId") == workspace_id
            and metadata.get("deckId") == deck_id
            and metadata.get("threadId") == thread_id
            and metadata.get("workflowRunId") == root_run_id
            and isinstance(goal, str)
            and bool(goal.strip())
            and metadata.get("projectStorySlug")
            in {None, story_workspace_canonical_project_fallback_slug(goal)}
            and metadata.get("requestFingerprint")
            == _sha256_json(fingerprint_payload)
            and attempt.input_hash == _sha256_json({"goal": goal})
            and launch_agent_is_valid
        )
        if not valid:
            raise DreamThreadBindingConflict("source_message_provenance_mismatch")


def _mapping_value(mapping: Mapping[str, Any] | Any, key: str) -> Any:
    if isinstance(mapping, Mapping):
        return mapping.get(key)
    try:
        return mapping[key]
    except (KeyError, IndexError, TypeError):
        return None


def _select_retry_leaf(attempts: Iterable[_DreamAttempt]) -> _DreamAttempt:
    """Validate one complete linear retry graph and return its sole leaf."""

    rows = tuple(attempts)
    if not rows:
        raise DreamThreadBindingConflict("empty_attempt_graph")
    by_id = {row.workflow_run_id: row for row in rows}
    if len(by_id) != len(rows):
        raise DreamThreadBindingConflict("duplicate_run_id")
    if any(_RUN_ID.fullmatch(run_id) is None for run_id in by_id):
        raise DreamThreadBindingConflict("invalid_run_id")

    children: dict[str, list[str]] = {run_id: [] for run_id in by_id}
    roots: list[str] = []
    for row in rows:
        parent_id = row.retry_of_run_id
        if parent_id is None:
            roots.append(row.workflow_run_id)
            continue
        if parent_id not in by_id:
            raise DreamThreadBindingConflict("missing_retry_parent")
        children[parent_id].append(row.workflow_run_id)

    if len(roots) != 1:
        # Zero roots is a cycle; multiple roots are independent attempts.
        raise DreamThreadBindingConflict(
            "retry_cycle" if not roots else "multiple_retry_roots"
        )
    if any(len(items) > 1 for items in children.values()):
        raise DreamThreadBindingConflict("branched_retry_graph")

    visited: set[str] = set()
    cursor = roots[0]
    while True:
        if cursor in visited:
            raise DreamThreadBindingConflict("retry_cycle")
        visited.add(cursor)
        next_ids = children[cursor]
        if not next_ids:
            break
        cursor = next_ids[0]
    if len(visited) != len(rows):
        raise DreamThreadBindingConflict("disconnected_retry_graph")

    frozen = rows[0].frozen_source()
    if any(row.frozen_source() != frozen for row in rows[1:]):
        raise DreamThreadBindingConflict("frozen_source_mismatch")
    return by_id[cursor]


class DreamRunBindingResolver:
    """Database-backed actor/thread resolver for canonical Chat ingress."""

    def __init__(self, db: Any) -> None:
        self._db = db

    def resolve(
        self,
        *,
        actor_id: str | int,
        thread_id: str,
        owned_thread: Mapping[str, Any] | Any,
    ) -> StoryWorkspaceDreamRunContext | None:
        # This resolver runs for generic Chat ingress too.  The narrow
        # idx_workflow_runs_source_voice_thread index is therefore part of the
        # canonical request-path contract, not an optional Dream optimization.
        rows = self._db.execute(
            """
            SELECT run.id AS workflow_run_id,
                   run.retry_of_run_id AS retry_of_run_id,
                   run.status AS status,
                   run.workspace_id AS workspace_id,
                   run.created_by AS created_by,
                   run.source_voice_thread_id AS source_voice_thread_id,
                   run.source_message_id AS source_message_id,
                   run.source_message_time AS source_message_time,
                   source.thread_id AS source_message_thread_id,
                   source.role AS source_message_role,
                   source.metadata AS source_message_metadata,
                   run.input_hash AS input_hash,
                   run.workflow_definition_ref AS workflow_definition_ref,
                   run.deck_plugin_manifest_hash AS deck_plugin_manifest_hash,
                   run.deck_plugin_id AS deck_plugin_id,
                   run.deck_plugin_version AS deck_plugin_version,
                   run.deck_plugin_binding_id AS deck_plugin_binding_id,
                   run.binding_revision AS binding_revision,
                   run.deck_runtime_snapshot_id AS deck_runtime_snapshot_id,
                   run.runtime_plugin_lock_id AS runtime_plugin_lock_id,
                   workspace.owner_id AS workspace_owner_id,
                   binding.deck_id AS binding_deck_id,
                   binding.workspace_id AS binding_workspace_id,
                   binding.deck_plugin_id AS binding_deck_plugin_id,
                   binding.deck_plugin_version AS binding_deck_plugin_version,
                   binding.binding_revision AS binding_revision_actual
            FROM workflow_runs AS run
            LEFT JOIN story_workspace_workspaces AS workspace
              ON workspace.id = run.workspace_id
            LEFT JOIN deck_plugin_bindings AS binding
              ON binding.deck_plugin_binding_id = run.deck_plugin_binding_id
            LEFT JOIN chat_message AS source
              ON source.id = run.source_message_id
            WHERE run.source_voice_thread_id = %s
            LIMIT 257
            """,
            (thread_id,),
        ).fetchall()
        if not rows:
            return None
        if len(rows) > _MAX_ATTEMPTS_PER_THREAD:
            return self._conflict(thread_id, "attempt_capacity")

        try:
            attempts = tuple(_DreamAttempt.from_row(row) for row in rows)
            actor = str(actor_id)
            thread_owner = _mapping_value(owned_thread, "user_id")
            thread_deck_id = _mapping_value(owned_thread, "deck_id")
            thread_agent_id = _mapping_value(owned_thread, "voice_id")
            if thread_agent_id is not None and (
                not isinstance(thread_agent_id, str)
                or not thread_agent_id
                or thread_agent_id != thread_agent_id.strip()
            ):
                raise DreamThreadBindingConflict("thread_current_agent_invalid")
            if (
                str(_mapping_value(owned_thread, "id") or "") != thread_id
                or thread_owner is None
                or str(thread_owner) != actor
                or not isinstance(thread_deck_id, str)
                or not thread_deck_id
            ):
                raise DreamThreadBindingConflict("thread_ownership_or_deck_mismatch")

            for attempt in attempts:
                if (
                    attempt.created_by != actor
                    or attempt.source_voice_thread_id != thread_id
                    or str(attempt.workspace_owner_id) != actor
                    or attempt.binding_deck_id != thread_deck_id
                    or attempt.binding_workspace_id != attempt.workspace_id
                    or attempt.binding_deck_plugin_id != attempt.deck_plugin_id
                    or attempt.binding_deck_plugin_version
                    != attempt.deck_plugin_version
                    or isinstance(attempt.binding_revision_actual, bool)
                    or attempt.binding_revision_actual != attempt.binding_revision
                ):
                    raise DreamThreadBindingConflict("frozen_binding_mismatch")

            leaf = _select_retry_leaf(attempts)
            root = next(
                attempt for attempt in attempts if attempt.retry_of_run_id is None
            )
            _validate_source_message_provenance(
                attempts,
                root_run_id=root.workflow_run_id,
                actor_id=actor,
                thread_id=thread_id,
                workspace_id=leaf.workspace_id,
                deck_id=thread_deck_id,
            )
            try:
                leaf_status = RunStatus(leaf.status)
                parent_statuses = {
                    RunStatus(attempt.status)
                    for attempt in attempts
                    if attempt.workflow_run_id != leaf.workflow_run_id
                }
            except ValueError as exc:
                raise DreamThreadBindingConflict("invalid_leaf_status") from exc
            if not parent_statuses.issubset(_RETRY_PARENT_STATUSES):
                raise DreamThreadBindingConflict("invalid_retry_parent_status")
            if leaf_status in TERMINAL_RUN_STATUSES:
                # Workflow completion is business truth only. After all binding
                # facts have been proven, an ordinary message on the durable
                # thread must continue as canonical Chat without Dream runtime
                # activation authority.
                return None
            if leaf_status not in _ACTIVE_DREAM_RUN_STATUSES:
                raise DreamThreadBindingConflict("invalid_leaf_status")
            return StoryWorkspaceDreamRunContext.model_validate(
                {
                    "workflow_run_id": leaf.workflow_run_id,
                    "thread_id": thread_id,
                    "deck_id": thread_deck_id,
                    "agent_id": (
                        thread_agent_id
                        if isinstance(thread_agent_id, str) and thread_agent_id
                        else None
                    ),
                    "deck_plugin_id": leaf.deck_plugin_id,
                    "deck_plugin_version": leaf.deck_plugin_version,
                    "deck_plugin_binding_id": leaf.deck_plugin_binding_id,
                    "binding_revision": leaf.binding_revision,
                    "deck_runtime_snapshot_id": leaf.deck_runtime_snapshot_id,
                    "runtime_plugin_lock_id": leaf.runtime_plugin_lock_id,
                }
            )
        except (DreamThreadBindingConflict, ValidationError, TypeError, ValueError) as exc:
            reason = exc.reason if isinstance(exc, DreamThreadBindingConflict) else "context_contract_invalid"
            return self._conflict(thread_id, reason, cause=exc)

    @staticmethod
    def canonical_message_metadata(
        context: StoryWorkspaceDreamRunContext,
        *,
        actor_id: str | int,
    ) -> dict[str, str]:
        """Server-authored metadata for a visible human Dream message."""

        return {
            "kind": "story-workspace-dream-agent-user",
            "story_workspace_run_id": context.workflow_run_id,
            "thread_id": context.thread_id,
            "actor_id": str(actor_id),
        }

    @staticmethod
    def _conflict(
        thread_id: str,
        reason: str,
        *,
        cause: BaseException | None = None,
    ) -> Any:
        logger.warning(
            "Dream thread binding integrity failure: reason=%s thread_id=%s",
            reason[:80],
            thread_id[:255],
        )
        conflict = DreamThreadBindingConflict(reason)
        if cause is not None:
            raise conflict from cause
        raise conflict


class DreamThreadContextMapper:
    """Resolve internal Dream authority from one actor-owned canonical Thread.

    This is the only adapter used by ``ClaudeAgentService.assemble_context``.
    It deliberately accepts no run selector and returns ``None`` for ordinary
    Chat threads or a fully terminal Dream retry chain.
    """

    def __init__(
        self,
        *,
        db_factory: Any | None = None,
        thread_loader: Any | None = None,
    ) -> None:
        if db_factory is None or thread_loader is None:
            try:
                import database as database_module
            except ModuleNotFoundError:  # pragma: no cover - package imports
                from backend import database as database_module
            db_factory = db_factory or database_module.get_db
            thread_loader = thread_loader or database_module.get_chat_thread
        self._db_factory = db_factory
        self._thread_loader = thread_loader

    def resolve(
        self,
        *,
        actor_id: str | int,
        thread_id: str,
    ) -> StoryWorkspaceDreamRunContext | None:
        try:
            numeric_actor_id = int(actor_id)
        except (TypeError, ValueError) as exc:
            raise DreamThreadBindingConflict("invalid_actor") from exc
        owned_thread = self._thread_loader(thread_id, numeric_actor_id)
        if owned_thread is None:
            # Public Chat ingress and internal Dream dispatchers already prove
            # Thread ownership. A direct service/test call with no durable
            # Thread has no Dream binding and must not gain Dream authority.
            return None
        db = self._db_factory()
        try:
            return DreamRunBindingResolver(db).resolve(
                actor_id=numeric_actor_id,
                thread_id=thread_id,
                owned_thread=owned_thread,
            )
        finally:
            db.close()


__all__ = [
    "DreamRunBindingResolver",
    "DreamThreadContextMapper",
    "DreamThreadBindingConflict",
]
