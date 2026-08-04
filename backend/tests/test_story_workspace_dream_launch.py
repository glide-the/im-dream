"""Focused contract and orchestration tests for starting a Dream run."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
import unittest

from pydantic import ValidationError

from services.story_workspace.dream_launch_service import (
    StoryWorkspaceDreamLaunchIdempotencyConflict,
    StoryWorkspaceDreamLaunchProvenanceError,
    StoryWorkspaceDreamLaunchService,
    StoryWorkspaceDreamLaunchSource,
)
from story_workspace.contracts import (
    StoryWorkspaceDreamLaunchCommand,
    StoryWorkspaceDreamRunContext,
)


ACTOR_ID = "41"
WORKSPACE_ID = "workspace-dream-launch"
DECK_ID = "deck-dream-launch"
RUN_ID = "run_" + "a" * 32
PREFLIGHT_ID = "pf_" + "b" * 32
BINDING_ID = "dpb_" + "c" * 32
SNAPSHOT_ID = "drs_" + "d" * 32
LOCK_ID = "rpl_" + "e" * 32
MESSAGE_TIME = datetime(2026, 8, 4, 15, 0, tzinfo=UTC)


def command(**overrides: object) -> StoryWorkspaceDreamLaunchCommand:
    payload: dict[str, object] = {
        "deckId": DECK_ID,
        "goal": "创作一个发生在雨夜车站的短篇故事",
        "idempotencyKey": "dream-launch-1",
    }
    payload.update(overrides)
    return StoryWorkspaceDreamLaunchCommand.model_validate(payload)


class RecordingSourceAdapter:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []
        self.created_sources: dict[
            tuple[str, str, str], StoryWorkspaceDreamLaunchSource
        ] = {}
        self.fingerprints: dict[tuple[str, str, str], str] = {}

    async def ensure_source(self, **values: object) -> StoryWorkspaceDreamLaunchSource:
        self.calls.append(values)
        scope = (
            str(values["workspace_id"]),
            str(values["actor_id"]),
            str(values["idempotency_key"]),
        )
        fingerprint = str(values["request_fingerprint"])
        existing_fingerprint = self.fingerprints.get(scope)
        if existing_fingerprint is not None and existing_fingerprint != fingerprint:
            raise StoryWorkspaceDreamLaunchIdempotencyConflict()
        existing = self.created_sources.get(scope)
        if existing is not None:
            return StoryWorkspaceDreamLaunchSource(
                thread_id=existing.thread_id,
                message_id=existing.message_id,
                message_time=existing.message_time,
                request_fingerprint=existing.request_fingerprint,
                created=False,
            )
        created = StoryWorkspaceDreamLaunchSource(
            thread_id=str(values["thread_id"]),
            message_id=str(values["message_id"]),
            message_time=MESSAGE_TIME,
            request_fingerprint=fingerprint,
            created=True,
        )
        self.fingerprints[scope] = fingerprint
        self.created_sources[scope] = created
        return created


class DreamLaunchFixture:
    def __init__(self) -> None:
        self.source_adapter = RecordingSourceAdapter()
        self.binding_calls: list[dict[str, object]] = []
        self.preflight_calls: list[dict[str, object]] = []
        self.run_calls: list[dict[str, object]] = []
        self.dispatcher = RecordingDispatcher()
        self.created_runs: dict[tuple[str, str, str], SimpleNamespace] = {}
        self.binding_error: Exception | None = None
        self.run_overrides: dict[str, object] = {}
        self.service = StoryWorkspaceDreamLaunchService(
            source_adapter=self.source_adapter,
            binding_resolver=self.resolve_binding,
            preflight_creator=self.create_preflight,
            run_creator=self.create_run,
            dispatcher=self.dispatcher,
        )

    async def resolve_binding(self, **values: object) -> SimpleNamespace:
        self.binding_calls.append(values)
        if self.binding_error is not None:
            raise self.binding_error
        return SimpleNamespace(
            deck_plugin_id="ink-dream-story",
            deck_plugin_version="1.2.0",
            deck_plugin_binding_id=BINDING_ID,
            binding_revision=7,
        )

    async def create_preflight(self, **values: object) -> SimpleNamespace:
        self.preflight_calls.append(values)
        return SimpleNamespace(
            workflow_preflight_id=PREFLIGHT_ID,
            preflight_token="trusted-preflight-token",
            deck_id=DECK_ID,
            deck_plugin_id="ink-dream-story",
            deck_plugin_version="1.2.0",
            binding_revision=7,
            deck_runtime_snapshot_id=SNAPSHOT_ID,
            runtime_plugin_lock_id=LOCK_ID,
        )

    async def create_run(self, **values: object) -> SimpleNamespace:
        self.run_calls.append(values)
        scope = (
            str(values["workspace_id"]),
            str(values["actor_id"]),
            str(values["idempotency_key"]),
        )
        existing = self.created_runs.get(scope)
        if existing is not None:
            return existing
        run_values: dict[str, object] = {
            "workflow_run_id": RUN_ID,
            "source_voice_thread_id": values["source_thread_id"],
            "source_message_id": values["source_message_id"],
            "source_message_time": values["source_message_time"],
            "workspace_id": WORKSPACE_ID,
            "created_by": ACTOR_ID,
            "deck_plugin_id": "ink-dream-story",
            "deck_plugin_version": "1.2.0",
            "deck_plugin_binding_id": BINDING_ID,
            "binding_revision": 7,
            "deck_runtime_snapshot_id": SNAPSHOT_ID,
            "runtime_plugin_lock_id": LOCK_ID,
            "workflow_preflight_id": PREFLIGHT_ID,
        }
        run_values.update(self.run_overrides)
        created = SimpleNamespace(**run_values)
        self.created_runs[scope] = created
        return created


class RecordingDispatcher:
    """Model the gateway's durable message-id dispatch claim."""

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []
        self.dispatched_messages: set[str] = set()
        self.failures_remaining = 0

    def __call__(self, **values: object) -> bool:
        self.calls.append(values)
        if self.failures_remaining:
            self.failures_remaining -= 1
            raise RuntimeError("dispatch unavailable")
        source = values["source"]
        assert isinstance(source, StoryWorkspaceDreamLaunchSource)
        if source.message_id in self.dispatched_messages:
            return False
        self.dispatched_messages.add(source.message_id)
        return True


class StoryWorkspaceDreamLaunchContractTest(unittest.TestCase):
    def test_request_accepts_only_the_three_public_fields(self) -> None:
        parsed = command()

        self.assertEqual(parsed.deck_id, DECK_ID)
        self.assertEqual(parsed.idempotency_key, "dream-launch-1")
        with self.assertRaises(ValidationError):
            command(threadId="client-controlled-thread")
        with self.assertRaises(ValidationError):
            command(workflowRunId=RUN_ID)
        with self.assertRaises(ValidationError):
            command(goal="   ")


class StoryWorkspaceDreamLaunchServiceTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.fixture = DreamLaunchFixture()

    async def test_launch_derives_source_and_returns_trusted_run_context(self) -> None:
        result = await self.fixture.service.launch(
            command(),
            actor_id=ACTOR_ID,
            workspace_id=WORKSPACE_ID,
        )

        self.assertIsInstance(result, StoryWorkspaceDreamRunContext)
        self.assertEqual(
            result,
            StoryWorkspaceDreamRunContext(
                workflow_run_id=RUN_ID,
                thread_id=result.thread_id,
                deck_id=DECK_ID,
                deck_plugin_id="ink-dream-story",
                deck_plugin_version="1.2.0",
                deck_plugin_binding_id=BINDING_ID,
                binding_revision=7,
                deck_runtime_snapshot_id=SNAPSHOT_ID,
                runtime_plugin_lock_id=LOCK_ID,
            ),
        )
        source_call = self.fixture.source_adapter.calls[0]
        self.assertEqual(source_call["actor_id"], ACTOR_ID)
        self.assertEqual(source_call["workspace_id"], WORKSPACE_ID)
        self.assertEqual(source_call["deck_id"], DECK_ID)
        self.assertEqual(source_call["goal"], command().goal)
        self.assertTrue(str(source_call["request_fingerprint"]).startswith("sha256:"))
        self.assertEqual(
            self.fixture.preflight_calls,
            [{
                "deck_id": DECK_ID,
                "binding_revision": 7,
                "input_data": {"goal": command().goal},
                "actor_id": ACTOR_ID,
                "workspace_id": WORKSPACE_ID,
            }],
        )
        run_call = self.fixture.run_calls[0]
        self.assertEqual(run_call["source_thread_id"], result.thread_id)
        self.assertEqual(run_call["source_message_time"], MESSAGE_TIME)
        self.assertEqual(run_call["preflight_id"], PREFLIGHT_ID)
        self.assertEqual(run_call["preflight_token"], "trusted-preflight-token")
        self.assertEqual(len(self.fixture.dispatcher.calls), 1)
        self.assertIs(self.fixture.dispatcher.calls[0]["context"], result)

    async def test_same_request_replays_without_duplicate_source_run_or_dispatch(
        self,
    ) -> None:
        first = await self.fixture.service.launch(
            command(), actor_id=ACTOR_ID, workspace_id=WORKSPACE_ID
        )
        second = await self.fixture.service.launch(
            command(), actor_id=ACTOR_ID, workspace_id=WORKSPACE_ID
        )

        self.assertEqual(second, first)
        self.assertEqual(len(self.fixture.source_adapter.created_sources), 1)
        self.assertEqual(len(self.fixture.created_runs), 1)
        self.assertEqual(len(self.fixture.dispatcher.calls), 2)
        self.assertEqual(len(self.fixture.dispatcher.dispatched_messages), 1)
        self.assertEqual(
            self.fixture.source_adapter.calls[0]["thread_id"],
            self.fixture.source_adapter.calls[1]["thread_id"],
        )
        self.assertEqual(
            self.fixture.source_adapter.calls[0]["message_id"],
            self.fixture.source_adapter.calls[1]["message_id"],
        )

    async def test_same_key_with_different_content_conflicts_before_workflow_creation(
        self,
    ) -> None:
        await self.fixture.service.launch(
            command(), actor_id=ACTOR_ID, workspace_id=WORKSPACE_ID
        )

        with self.assertRaises(StoryWorkspaceDreamLaunchIdempotencyConflict):
            await self.fixture.service.launch(
                command(goal="改成一个太空喜剧"),
                actor_id=ACTOR_ID,
                workspace_id=WORKSPACE_ID,
            )

        self.assertEqual(len(self.fixture.binding_calls), 2)
        self.assertEqual(len(self.fixture.preflight_calls), 1)
        self.assertEqual(len(self.fixture.created_runs), 1)
        self.assertEqual(len(self.fixture.dispatcher.dispatched_messages), 1)

    async def test_mismatched_authoritative_run_provenance_is_rejected(self) -> None:
        self.fixture.run_overrides["runtime_plugin_lock_id"] = "rpl_wrong"

        with self.assertRaises(StoryWorkspaceDreamLaunchProvenanceError):
            await self.fixture.service.launch(
                command(), actor_id=ACTOR_ID, workspace_id=WORKSPACE_ID
            )

        self.assertEqual(self.fixture.dispatcher.calls, [])

    async def test_binding_denial_creates_no_backing_source(self) -> None:
        self.fixture.binding_error = PermissionError("Deck not found")

        with self.assertRaises(PermissionError):
            await self.fixture.service.launch(
                command(), actor_id=ACTOR_ID, workspace_id=WORKSPACE_ID
            )

        self.assertEqual(self.fixture.source_adapter.calls, [])
        self.assertEqual(self.fixture.preflight_calls, [])
        self.assertEqual(self.fixture.run_calls, [])
        self.assertEqual(self.fixture.dispatcher.calls, [])

    async def test_dispatch_failure_replays_pending_source_and_existing_run(self) -> None:
        self.fixture.dispatcher.failures_remaining = 1

        with self.assertRaisesRegex(RuntimeError, "dispatch unavailable"):
            await self.fixture.service.launch(
                command(), actor_id=ACTOR_ID, workspace_id=WORKSPACE_ID
            )
        self.assertEqual(len(self.fixture.source_adapter.created_sources), 1)
        self.assertEqual(len(self.fixture.created_runs), 1)
        self.assertEqual(self.fixture.dispatcher.dispatched_messages, set())

        replayed = await self.fixture.service.launch(
            command(), actor_id=ACTOR_ID, workspace_id=WORKSPACE_ID
        )
        repeated = await self.fixture.service.launch(
            command(), actor_id=ACTOR_ID, workspace_id=WORKSPACE_ID
        )

        self.assertEqual(replayed, repeated)
        self.assertEqual(len(self.fixture.source_adapter.created_sources), 1)
        self.assertEqual(len(self.fixture.created_runs), 1)
        self.assertEqual(len(self.fixture.dispatcher.calls), 3)
        self.assertEqual(len(self.fixture.dispatcher.dispatched_messages), 1)


if __name__ == "__main__":
    unittest.main()
