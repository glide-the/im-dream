"""Trusted orchestration core for starting a Dream workspace run.

Persistence, workflow services, and Agent dispatch are injected at the service
boundary.  This keeps the launch contract independent from router request
models and lets the gateway provide the existing SQLite-backed adapters.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from typing import Any, Awaitable, Callable, Protocol
import uuid

try:
    from story_workspace.contracts import (
        StoryWorkspaceDreamLaunchCommand,
        StoryWorkspaceDreamRunContext,
    )
except ModuleNotFoundError:  # Support package imports from repository root.
    from backend.story_workspace.contracts import (
        StoryWorkspaceDreamLaunchCommand,
        StoryWorkspaceDreamRunContext,
    )


DREAM_LAUNCH_IDEMPOTENCY_CONFLICT = "DREAM_LAUNCH_IDEMPOTENCY_CONFLICT"
DREAM_LAUNCH_PROVENANCE_INVALID = "DREAM_LAUNCH_PROVENANCE_INVALID"


class StoryWorkspaceDreamLaunchError(RuntimeError):
    """Base error exposed by the gateway-facing launch service."""

    code = "DREAM_LAUNCH_INVALID"

    def __init__(self, summary: str) -> None:
        super().__init__(summary)


class StoryWorkspaceDreamLaunchIdempotencyConflict(
    StoryWorkspaceDreamLaunchError
):
    code = DREAM_LAUNCH_IDEMPOTENCY_CONFLICT

    def __init__(self) -> None:
        super().__init__("idempotency key was reused with different Dream content")


class StoryWorkspaceDreamLaunchProvenanceError(StoryWorkspaceDreamLaunchError):
    code = DREAM_LAUNCH_PROVENANCE_INVALID

    def __init__(self, field: str) -> None:
        self.field = field
        super().__init__(f"Dream launch returned mismatched provenance: {field}")


@dataclass(frozen=True)
class StoryWorkspaceDreamLaunchSource:
    """Atomically ensured Deck-bound thread and hidden launch message."""

    thread_id: str
    message_id: str
    message_time: datetime
    request_fingerprint: str
    created: bool

    def __post_init__(self) -> None:
        if not self.thread_id or not self.message_id:
            raise ValueError("Dream launch source identifiers must not be blank")
        if self.message_time.tzinfo is None:
            raise ValueError("Dream launch source time must include a timezone")
        if not self.request_fingerprint.startswith("sha256:"):
            raise ValueError("Dream launch source fingerprint must be sha256")


class StoryWorkspaceDreamLaunchSourceAdapter(Protocol):
    """Persistence seam that atomically creates or replays a launch source."""

    async def ensure_source(
        self,
        *,
        actor_id: str,
        workspace_id: str,
        deck_id: str,
        goal: str,
        idempotency_key: str,
        request_fingerprint: str,
        thread_id: str,
        message_id: str,
    ) -> StoryWorkspaceDreamLaunchSource:
        ...


StoryWorkspaceDreamLaunchAsyncSeam = Callable[..., Awaitable[Any]]
StoryWorkspaceDreamLaunchDispatcher = Callable[..., Any]


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _sha256(value: Any) -> str:
    digest = hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()
    return "sha256:" + digest


def _field(value: Any, name: str) -> Any:
    if isinstance(value, dict):
        return value.get(name)
    return getattr(value, name, None)


class StoryWorkspaceDreamLaunchService:
    """Create one idempotent Dream source/run and dispatch its first turn."""

    def __init__(
        self,
        *,
        source_adapter: StoryWorkspaceDreamLaunchSourceAdapter,
        binding_resolver: StoryWorkspaceDreamLaunchAsyncSeam,
        preflight_creator: StoryWorkspaceDreamLaunchAsyncSeam,
        run_creator: StoryWorkspaceDreamLaunchAsyncSeam,
        dispatcher: StoryWorkspaceDreamLaunchDispatcher,
    ) -> None:
        self._source_adapter = source_adapter
        self._binding_resolver = binding_resolver
        self._preflight_creator = preflight_creator
        self._run_creator = run_creator
        self._dispatcher = dispatcher

    async def launch(
        self,
        command: StoryWorkspaceDreamLaunchCommand,
        *,
        actor_id: str,
        workspace_id: str,
    ) -> StoryWorkspaceDreamRunContext:
        """Start or replay one launch without accepting client provenance."""

        actor_id = actor_id.strip()
        workspace_id = workspace_id.strip()
        if not actor_id or not workspace_id:
            raise StoryWorkspaceDreamLaunchError(
                "trusted actor and workspace identifiers are required"
            )

        fingerprint = _sha256({
            "deck_id": command.deck_id,
            "goal": command.goal,
        })
        thread_id, message_id = self._deterministic_source_ids(
            actor_id=actor_id,
            workspace_id=workspace_id,
            idempotency_key=command.idempotency_key,
        )
        source = await self._source_adapter.ensure_source(
            actor_id=actor_id,
            workspace_id=workspace_id,
            deck_id=command.deck_id,
            goal=command.goal,
            idempotency_key=command.idempotency_key,
            request_fingerprint=fingerprint,
            thread_id=thread_id,
            message_id=message_id,
        )
        self._require_equal("source.thread_id", source.thread_id, thread_id)
        self._require_equal("source.message_id", source.message_id, message_id)
        self._require_equal(
            "source.request_fingerprint",
            source.request_fingerprint,
            fingerprint,
        )

        binding = await self._binding_resolver(
            deck_id=command.deck_id,
            actor_id=actor_id,
            workspace_id=workspace_id,
        )
        binding_revision = _field(binding, "binding_revision")
        if isinstance(binding_revision, bool) or not isinstance(binding_revision, int):
            raise StoryWorkspaceDreamLaunchProvenanceError(
                "binding.binding_revision"
            )
        if binding_revision < 1:
            raise StoryWorkspaceDreamLaunchProvenanceError(
                "binding.binding_revision"
            )

        preflight = await self._preflight_creator(
            deck_id=command.deck_id,
            binding_revision=binding_revision,
            input_data={"goal": command.goal},
            actor_id=actor_id,
            workspace_id=workspace_id,
        )
        self._validate_preflight(
            preflight,
            deck_id=command.deck_id,
            binding=binding,
        )
        preflight_id = _field(preflight, "workflow_preflight_id")
        preflight_token = _field(preflight, "preflight_token")
        if not isinstance(preflight_id, str) or not preflight_id:
            raise StoryWorkspaceDreamLaunchProvenanceError(
                "preflight.workflow_preflight_id"
            )
        if not isinstance(preflight_token, str) or not preflight_token:
            raise StoryWorkspaceDreamLaunchProvenanceError(
                "preflight.preflight_token"
            )

        run = await self._run_creator(
            preflight_id=preflight_id,
            preflight_token=preflight_token,
            idempotency_key=command.idempotency_key,
            source_thread_id=source.thread_id,
            source_message_id=source.message_id,
            source_message_time=source.message_time,
            actor_id=actor_id,
            workspace_id=workspace_id,
        )
        self._validate_run(
            run,
            source=source,
            actor_id=actor_id,
            workspace_id=workspace_id,
            binding=binding,
            preflight=preflight,
        )
        context = StoryWorkspaceDreamRunContext(
            workflow_run_id=_field(run, "workflow_run_id"),
            thread_id=source.thread_id,
            deck_id=command.deck_id,
            deck_plugin_id=_field(run, "deck_plugin_id"),
            deck_plugin_version=_field(run, "deck_plugin_version"),
            deck_plugin_binding_id=_field(run, "deck_plugin_binding_id"),
            binding_revision=_field(run, "binding_revision"),
            deck_runtime_snapshot_id=_field(run, "deck_runtime_snapshot_id"),
            runtime_plugin_lock_id=_field(run, "runtime_plugin_lock_id"),
        )
        if source.created:
            self._dispatcher(
                actor_id=actor_id,
                goal=command.goal,
                source=source,
                context=context,
            )
        return context

    @staticmethod
    def _deterministic_source_ids(
        *,
        actor_id: str,
        workspace_id: str,
        idempotency_key: str,
    ) -> tuple[str, str]:
        scope = _canonical_json({
            "actor_id": actor_id,
            "workspace_id": workspace_id,
            "idempotency_key": idempotency_key,
        })
        return (
            str(uuid.uuid5(uuid.NAMESPACE_URL, f"ink-dream:thread:{scope}")),
            str(uuid.uuid5(uuid.NAMESPACE_URL, f"ink-dream:message:{scope}")),
        )

    @classmethod
    def _validate_preflight(
        cls,
        preflight: Any,
        *,
        deck_id: str,
        binding: Any,
    ) -> None:
        cls._require_equal("preflight.deck_id", _field(preflight, "deck_id"), deck_id)
        for name in (
            "binding_revision",
            "deck_plugin_id",
            "deck_plugin_version",
        ):
            cls._require_equal(
                f"preflight.{name}",
                _field(preflight, name),
                _field(binding, name),
            )
        for name in ("deck_runtime_snapshot_id", "runtime_plugin_lock_id"):
            if not isinstance(_field(preflight, name), str) or not _field(
                preflight, name
            ):
                raise StoryWorkspaceDreamLaunchProvenanceError(
                    f"preflight.{name}"
                )

    @classmethod
    def _validate_run(
        cls,
        run: Any,
        *,
        source: StoryWorkspaceDreamLaunchSource,
        actor_id: str,
        workspace_id: str,
        binding: Any,
        preflight: Any,
    ) -> None:
        expected = {
            "source_voice_thread_id": source.thread_id,
            "source_message_id": source.message_id,
            "source_message_time": source.message_time,
            "created_by": actor_id,
            "workspace_id": workspace_id,
            "workflow_preflight_id": _field(preflight, "workflow_preflight_id"),
            "deck_plugin_id": _field(binding, "deck_plugin_id"),
            "deck_plugin_version": _field(binding, "deck_plugin_version"),
            "deck_plugin_binding_id": _field(binding, "deck_plugin_binding_id"),
            "binding_revision": _field(binding, "binding_revision"),
            "deck_runtime_snapshot_id": _field(
                preflight, "deck_runtime_snapshot_id"
            ),
            "runtime_plugin_lock_id": _field(preflight, "runtime_plugin_lock_id"),
        }
        for name, value in expected.items():
            cls._require_equal(f"run.{name}", _field(run, name), value)
        run_id = _field(run, "workflow_run_id")
        if not isinstance(run_id, str) or not run_id:
            raise StoryWorkspaceDreamLaunchProvenanceError(
                "run.workflow_run_id"
            )

    @staticmethod
    def _require_equal(field: str, actual: Any, expected: Any) -> None:
        if actual != expected:
            raise StoryWorkspaceDreamLaunchProvenanceError(field)
