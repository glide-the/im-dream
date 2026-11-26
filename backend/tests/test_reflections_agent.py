# [Input] Admin-backed Reflections engine, strict DTOs, and section RTA owner.
# [Output] Event durability, revision recovery, terminal restart, credential isolation, and shutdown tests.
# [Pos] Reflections runtime unit boundary; no PostgreSQL, HTTP server, or real model.
# [Sync] 2026-09-16: cover source-fenced Gateway grant composition for Reflections.
# [Sync] 2026-09-15: replace legacy SQLite flow tests with Admin consumer/runtime invariants.
# [Sync] 2026-10-13: include the current actor ID in the create fixture so the
#                    production preparation-cache cleanup boundary is exercised.
# [Sync] 2026-10-13: assert Reflections dispatches through the canonical normalized turn result and waits for the Factory owner.
# [Sync] 2026-11-26: exercise original-task start after worker loss, duplicate start, and stream closure on exit.
# [Sync] 2026-11-26: cover durable stop after worker loss and cancellation of the concrete child turn.

from __future__ import annotations

import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from fastapi import HTTPException

import reflections_agent as runtime
import routers.reflections as reflections_routes
from reflections_agent import (
    ReflectionEventBus,
    ReflectionsTaskEngine,
    TaskPersistenceObserver,
)
from services.admin_data.errors import AdminDataError
from services.admin_data.delegation import RuntimeHttpConfig
from services.admin_data.reflection_section_persistence import (
    AdminReflectionSectionPersistence,
)
from services.admin_data.reflection_task_models import (
    ReflectionAuthorityDTO,
    ReflectionEventDTO,
    ReflectionEventListOutputDTO,
    ReflectionLaunchSnapshotDTO,
    ReflectionPromptSnapshotDTO,
    ReflectionResultDTO,
    ReflectionSectionBeginOutputDTO,
    ReflectionSectionStateDTO,
    ReflectionSessionSnapshotDTO,
    ReflectionStatsDTO,
    ReflectionTaskAdvanceOutputDTO,
    ReflectionTaskDTO,
    ReflectionTaskGetOutputDTO,
    ReflectionTaskPublicInputDTO,
    ReflectionTaskStartOutputDTO,
    ReflectionWorkerLoadOutputDTO,
)
from services.admin_data.session_projection_broker import (
    SessionProjectionBrokerSettings,
)
from services.story_workspace.dream_lifecycle_observer import (
    NormalizedTurnOutcome,
    NormalizedTurnResult,
)


TASK_ID = "123e4567-e89b-42d3-a456-426614174000"
THREAD_ID = "223e4567-e89b-42d3-a456-426614174000"
RTA = "rta_" + "A" * 43


def _runtime_http_config() -> RuntimeHttpConfig:
    return RuntimeHttpConfig("https://admin.example", 1, 1024 * 1024)


def _run(coro):
    return asyncio.run(coro)


def _snapshot() -> ReflectionLaunchSnapshotDTO:
    return ReflectionLaunchSnapshotDTO(
        schema_version=1,
        task_id=TASK_ID,
        language="en",
        sessions=[ReflectionSessionSnapshotDTO(
            id="session-a",
            name="A",
            created_at="2026-09-14T01:00:00Z",
            updated_at="2026-09-14T02:00:00Z",
            labels=["one"],
            first_line="first",
            text="private body",
        )],
        custom_prompts=[ReflectionPromptSnapshotDTO(
            section="echoes", prompt_files_json=None
        )],
        stats=ReflectionStatsDTO(days=1, entries=1, words=2),
    )


def _task(root: str, *, status: str = "ASSEMBLING",
    revision: int = 2) -> ReflectionTaskDTO:
    terminal = status in {"COMPLETED", "PARTIAL_FAILED", "FAILED"}
    section_status = "COMPLETED" if status == "COMPLETED" else "PENDING"
    return ReflectionTaskDTO(
        id=TASK_ID,
        task_id=TASK_ID,
        status=status,
        sections=["echoes"],
        input_snapshot=ReflectionTaskPublicInputDTO(
            session_ids=["session-a"],
            start_date=None,
            end_date=None,
            language="en",
            language_label="English",
            session_count=1,
        ),
        workspace_path=str(Path(root) / TASK_ID / "memory"),
        agent_contract_version="reflections-agent-v1",
        error_summary=None,
        revision=revision,
        created_at="2026-09-15T00:00:00Z",
        started_at="2026-09-15T00:00:10Z" if terminal else None,
        completed_at="2026-09-15T00:01:00Z" if terminal else None,
        updated_at="2026-09-15T00:01:00Z",
        section_states=[ReflectionSectionStateDTO(
            section="echoes",
            status=section_status,
            result_count=1 if terminal else 0,
            revision=1,
            started_at="2026-09-15T00:00:10Z" if terminal else None,
            completed_at="2026-09-15T00:00:50Z" if terminal else None,
            error_summary=None,
        )],
    )


def _load(root: str, *, status: str = "ASSEMBLING",
    revision: int = 2, high_water: int = 0) -> ReflectionWorkerLoadOutputDTO:
    return ReflectionWorkerLoadOutputDTO(
        task=_task(root, status=status, revision=revision),
        launch_snapshot=_snapshot(),
        last_event_sequence=high_water,
    )


def _begin() -> ReflectionSectionBeginOutputDTO:
    authority = ReflectionAuthorityDTO(
        token=RTA,
        purpose="reflections-worker",
        task_id=TASK_ID,
        section="echoes",
        thread_id=THREAD_ID,
        scopes=("dream:read", "dream:write"),
        expires_at="2099-01-01T00:00:00Z",
        maximum_expires_at="2099-01-02T00:00:00Z",
    )
    return ReflectionSectionBeginOutputDTO(
        section="echoes",
        thread_id=THREAD_ID,
        status="RUNNING",
        revision=2,
        authority=authority,
    )


class _AppendWorker:
    def __init__(self, error: AdminDataError | None = None) -> None:
        self.error = error
        self.events = []

    def append_event(self, input_dto, request_id):
        self.events.append((input_dto, request_id))
        if self.error is not None:
            raise self.error
        return object()


class ReflectionEventBusTest(unittest.TestCase):
    def tearDown(self) -> None:
        runtime._BUSES.clear()
        runtime._RUNNING_TASKS.clear()
        runtime._TASK_LOCKS.clear()

    def test_append_failure_does_not_broadcast_or_advance(self):
        async def case():
            worker = _AppendWorker(AdminDataError("ADMIN_UNAVAILABLE", 503))
            bus = ReflectionEventBus(
                TASK_ID,
                initial_sequence=7,
                observers=[TaskPersistenceObserver(worker)],
            )
            token = await bus.subscribe()
            with self.assertRaises(AdminDataError):
                await bus.publish("reflection.task.started", {})
            self.assertEqual(bus.sequence, 7)
            self.assertTrue(token.empty())
            await bus.unsubscribe(token)

        _run(case())


class CanonicalTurnDispatchTest(unittest.IsolatedAsyncioTestCase):
    async def test_reflections_reuses_canonical_turn_result_and_owner_wait(self):
        import agent_factory

        calls = []
        factory = object()
        request = object()

        async def drain(selected_factory, selected_request, **kwargs):
            calls.append((selected_factory, selected_request, kwargs))
            return NormalizedTurnResult(
                outcome=NormalizedTurnOutcome.COMPLETED,
                saw_message_final=True,
                saw_finish=True,
                finish_reason="stop",
            )

        with patch.object(agent_factory, "claude_agent_thread_factory", factory), \
                patch("services.story_workspace.dream_lifecycle_observer.drain_chat_agent_turn", drain):
            result = await runtime._run_claude_agent_turn(request)

        self.assertEqual(result.outcome, NormalizedTurnOutcome.COMPLETED)
        self.assertEqual(calls, [(factory, request, {"wait_for_factory_owner": True})])


class _RouteOwner:
    def __init__(self, worker) -> None:
        self.worker = worker
        self.data = _RouteData()
        self.client = object()
        self.session_broker_settings = SessionProjectionBrokerSettings(
            timeout_seconds=1, max_bytes=1024
        )
        self.runtime_http_config = _runtime_http_config()

    def reflections_data(self):
        return self.data

    def reflections_worker_data(self):
        return self.worker


class _RouteData:
    def create(self, input_dto, request_id, *, access_token):
        raise AssertionError("patched invocation expected")

    def events(self, input_dto, request_id, *, access_token):
        raise AssertionError("patched invocation expected")

    def start(self, input_dto, request_id, *, access_token):
        raise AssertionError("patched invocation expected")

    def get(self, input_dto, request_id, *, access_token):
        raise AssertionError("patched invocation expected")


class ReflectionsPrestartSseTest(unittest.TestCase):
    def tearDown(self) -> None:
        runtime._BUSES.clear()
        runtime._RUNNING_TASKS.clear()
        runtime._TASK_LOCKS.clear()

    def test_create_then_subscribe_then_live_start_has_no_duplicates(self):
        async def case():
            with tempfile.TemporaryDirectory() as root:
                root = str(Path(root).resolve())
                worker = _AppendWorker()
                owner = _RouteOwner(worker)
                created = ReflectionTaskGetOutputDTO(
                    task=_task(root, status="CREATED", revision=1),
                    results=[],
                )
                with patch.object(
                    reflections_routes,
                    "invoke_admin_operation",
                    AsyncMock(return_value=created),
                ):
                    response = await reflections_routes.create_reflections_task_endpoint(
                        reflections_routes.ReflectionsTaskCreateRequest(
                            sections=["echoes"], auto_start=False
                        ),
                        current_user={"user_id": "7"},
                        owner=owner,
                    )
                self.assertEqual(response.status_code, 202)
                bus = await runtime.get_reflection_event_bus(TASK_ID)
                self.assertIsNotNone(bus)
                first = await bus.publish(
                    "reflection.task.created", {"task_id": TASK_ID}
                )
                history = ReflectionEventListOutputDTO(events=[ReflectionEventDTO(
                    task_id=TASK_ID,
                    id=first.id,
                    sequence=first.sequence,
                    type=first.type,
                    created_at=first.created_at,
                    payload=first.payload,
                )])
                with patch.object(
                    reflections_routes,
                    "invoke_admin_operation",
                    AsyncMock(return_value=history),
                ):
                    stream = await reflections_routes.stream_reflections_task_events_endpoint(
                        TASK_ID,
                        current_user={},
                        owner=owner,
                        last_event_id=None,
                    )
                await bus.publish("reflection.task.started", {})
                await bus.publish("reflection.task.completed", {})
                frames: list[str] = []
                async for frame in stream.body_iterator:
                    frames.append(frame.decode() if isinstance(frame, bytes) else frame)
                joined = "".join(frames)
                self.assertEqual(joined.count("event: reflection.task.created\n"), 1)
                self.assertEqual(joined.count("event: reflection.task.started\n"), 1)
                self.assertEqual(joined.count("event: reflection.task.completed\n"), 1)

        _run(case())

    def test_stop_settles_the_original_task_after_restart_and_keeps_results(self):
        async def case():
            owner = _RouteOwner(Mock())
            active = _task("/fixture", status="RUNNING", revision=7)
            stopped = _task("/fixture", status="COMPLETED", revision=8).model_copy(update={
                "status": "PARTIAL_FAILED", "error_summary": runtime.REFLECTION_TASK_STOPPED,
            })
            result = ReflectionResultDTO(
                id=THREAD_ID, task_id=TASK_ID, section="echoes", title="Saved result", description="",
                related_session_ids=[], evidence="", confidence="low", created_at=stopped.completed_at,
            )
            owner.worker.advance.return_value = ReflectionTaskAdvanceOutputDTO(status="PARTIAL_FAILED", revision=8)
            with patch.object(reflections_routes, "invoke_admin_operation", AsyncMock(side_effect=[
                ReflectionTaskStartOutputDTO(task=active, terminal=False, report_missing=False),
                ReflectionTaskGetOutputDTO(task=stopped, results=[result]),
            ])) as invoke:
                response = await reflections_routes.stop_reflections_task_endpoint(TASK_ID, current_user={}, owner=owner)
            self.assertEqual(response["error_summary"], runtime.REFLECTION_TASK_STOPPED)
            self.assertEqual(response["results"][0]["id"], THREAD_ID)
            self.assertEqual(invoke.await_args_list[0].args[1], owner.data.start)
            advance = owner.worker.advance.call_args.args[0]
            self.assertEqual((advance.task_id, advance.action, advance.expected_revision), (TASK_ID, "finalize", 7))
            owner.worker.ensure_report.assert_called_once()
            self.assertNotIn(TASK_ID, runtime._RUNNING_TASKS)

        _run(case())

    def test_stop_requires_owner_authorization(self):
        async def case():
            owner = _RouteOwner(Mock())
            with patch.object(reflections_routes, "invoke_admin_operation", AsyncMock(side_effect=HTTPException(404))), \
                    patch.object(reflections_routes, "stop_reflections_task_worker", AsyncMock()) as stop:
                with self.assertRaises(HTTPException) as failure:
                    await reflections_routes.stop_reflections_task_endpoint(TASK_ID, current_user={}, owner=owner)
            self.assertEqual(failure.exception.status_code, 404)
            owner.worker.advance.assert_not_called()
            stop.assert_not_awaited()

        _run(case())

    def test_stopping_a_local_worker_reaches_the_current_child_turn(self):
        async def case():
            running = asyncio.Event()
            async def drain(*args, **kwargs):
                running.set()
                await asyncio.Future()

            factory = Mock(stop_thread=AsyncMock())
            request = Mock(thread_id=THREAD_ID)
            with patch("claude_agent.runtime_owner.get_thread_factory", return_value=factory), \
                    patch("services.story_workspace.dream_lifecycle_observer.drain_chat_agent_turn", drain):
                worker = asyncio.create_task(runtime._run_claude_agent_turn(request))
                runtime._RUNNING_TASKS[TASK_ID] = worker
                await asyncio.wait_for(running.wait(), timeout=1)
                await runtime.stop_reflections_task_worker(TASK_ID)
            factory.stop_thread.assert_awaited_once_with(THREAD_ID)
            self.assertTrue(worker.cancelled())
            self.assertNotIn(TASK_ID, runtime._RUNNING_TASKS)

        _run(case())

    def test_existing_bus_requires_exact_admin_high_water(self):
        async def case():
            worker = _AppendWorker()
            bus = await runtime._get_or_create_reflection_event_bus(
                TASK_ID, initial_sequence=4, worker=worker
            )
            self.assertEqual(bus.sequence, 4)
            with self.assertRaises(AdminDataError):
                await runtime._get_or_create_reflection_event_bus(
                    TASK_ID, initial_sequence=3, worker=worker
                )
            with self.assertRaises(AdminDataError):
                await runtime._get_or_create_reflection_event_bus(
                    TASK_ID, initial_sequence=5, worker=worker
                )

        _run(case())

    def test_restart_replays_history_and_reuses_the_original_task(self):
        async def case():
            with tempfile.TemporaryDirectory() as root:
                root = str(Path(root).resolve())
                worker = _AppendWorker()
                load = _load(root, status="RUNNING", revision=4, high_water=2)
                worker.worker_load = lambda lookup, _: load
                owner = _RouteOwner(worker)
                event = ReflectionEventDTO(
                    task_id=TASK_ID, id=runtime.reflection_event_id(TASK_ID, 2),
                    sequence=2, type="reflection.task.started", created_at=load.task.updated_at,
                    payload={},
                )
                invoke = AsyncMock(side_effect=[
                    ReflectionEventListOutputDTO(events=[event]),
                    ReflectionTaskStartOutputDTO(task=load.task, terminal=False, report_missing=False),
                    ReflectionTaskStartOutputDTO(task=load.task, terminal=False, report_missing=False),
                ])
                running = asyncio.Event()
                finish = asyncio.Event()

                async def execute(context, bus):
                    running.set()
                    await finish.wait()
                    raise AdminDataError("ADMIN_WRITE_RESULT_UNKNOWN", 503, outcome_unknown=True)

                with patch.object(reflections_routes, "invoke_admin_operation", invoke), patch.object(
                    ReflectionsTaskEngine, "_execute_sections", side_effect=execute,
                ) as execution, patch.dict(os.environ, {"AGENT_CWD": root, "DREAM_REFLECTIONS_WORKSPACE_ROOT": root}):
                    stream = await reflections_routes.stream_reflections_task_events_endpoint(
                        TASK_ID, current_user={}, owner=owner, last_event_id=None,
                    )
                    frames = [frame async for frame in stream.body_iterator]
                    self.assertIn('"worker_missing": true', frames[0])
                    self.assertIn(event.id, frames[1])
                    await reflections_routes.start_reflections_task_endpoint(TASK_ID, current_user={}, owner=owner)
                    task = runtime._RUNNING_TASKS[TASK_ID]
                    await asyncio.wait_for(running.wait(), timeout=1)
                    bus = await runtime.get_reflection_event_bus(TASK_ID)
                    self.assertEqual(bus.sequence, 2)
                    token = await bus.subscribe(event.id)
                    try:
                        await asyncio.wait_for(reflections_routes.start_reflections_task_endpoint(
                            TASK_ID, current_user={}, owner=owner,
                        ), timeout=1)
                        self.assertIs(runtime._RUNNING_TASKS[TASK_ID], task)
                    finally:
                        finish.set()
                        await task
                    self.assertEqual([event async for event in bus.read(token)], [])
                    self.assertTrue(bus.is_done)
                    self.assertNotIn(TASK_ID, runtime._RUNNING_TASKS)
                    execution.assert_awaited_once()
                    self.assertEqual(worker.events, [])

        _run(case())


class _EngineWorker:
    def __init__(self, *, fail_context_event: bool = False) -> None:
        self.fail_context_event = fail_context_event
        self.advances = []
        self.events = []
        self.reports = []

    def append_event(self, input_dto, request_id):
        self.events.append(input_dto)
        if self.fail_context_event and input_dto.event_type == "reflection.context.ready":
            raise AdminDataError("ADMIN_RESPONSE_INVALID", 503, request_id)
        return object()

    def advance(self, input_dto, request_id):
        self.advances.append(input_dto)
        if input_dto.action == "context-ready":
            return ReflectionTaskAdvanceOutputDTO(status="QUEUED", revision=3)
        if input_dto.action == "fatal-fail":
            return ReflectionTaskAdvanceOutputDTO(status="FAILED", revision=4)
        raise AssertionError(input_dto.action)

    def ensure_report(self, input_dto, request_id):
        self.reports.append(input_dto.task_id)
        return object()


class ReflectionsTaskEngineRecoveryTest(unittest.TestCase):
    def tearDown(self) -> None:
        runtime._BUSES.clear()
        runtime._RUNNING_TASKS.clear()
        runtime._TASK_LOCKS.clear()

    def test_advance_then_known_event_failure_uses_new_revision(self):
        with tempfile.TemporaryDirectory() as root:
            root = str(Path(root).resolve())
            worker = _EngineWorker(fail_context_event=True)
            engine = ReflectionsTaskEngine(
                worker, object(), SessionProjectionBrokerSettings(
                    timeout_seconds=1, max_bytes=1024
                ), _runtime_http_config()
            )
            with patch.dict(os.environ, {
                "AGENT_CWD": root,
                "DREAM_REFLECTIONS_WORKSPACE_ROOT": root,
            }):
                _run(engine.run(TASK_ID, load=_load(root)))
            self.assertEqual(
                [(item.action, item.expected_revision) for item in worker.advances],
                [("context-ready", 2), ("fatal-fail", 3)],
            )

    def test_terminal_restart_ensures_report_without_appending_event(self):
        with tempfile.TemporaryDirectory() as root:
            root = str(Path(root).resolve())
            worker = _EngineWorker()
            engine = ReflectionsTaskEngine(
                worker, object(), SessionProjectionBrokerSettings(
                    timeout_seconds=1, max_bytes=1024
                ), _runtime_http_config()
            )
            _run(engine.run(TASK_ID, load=_load(root, status="COMPLETED")))
            self.assertEqual(worker.reports, [TASK_ID])
            self.assertEqual(worker.events, [])
            self.assertIsNone(_run(runtime.get_reflection_event_bus(TASK_ID)))

    def test_recovery_finalizes_an_interrupted_section_with_expired_authority(self):
        async def case(root):
            load = _load(root, status="RUNNING", revision=4, high_water=5)
            completed = load.task.section_states[0].model_copy(update={
                "status": "COMPLETED", "revision": 3, "result_count": 1,
            })
            interrupted = ReflectionSectionStateDTO(
                section="traits", status="RUNNING", result_count=0, revision=2,
                started_at=load.task.created_at, completed_at=None, error_summary=None,
            )
            load = load.model_copy(update={
                "task": load.task.model_copy(update={
                    "sections": ["echoes", "traits"], "section_states": [completed, interrupted],
                }),
                "launch_snapshot": load.launch_snapshot.model_copy(update={
                    "custom_prompts": [*load.launch_snapshot.custom_prompts,
                                       ReflectionPromptSnapshotDTO(section="traits", prompt_files_json=None)],
                }),
            })

            class Worker(_EngineWorker):
                def begin(self, input_dto, request_id):
                    self.begun = input_dto
                    raise AdminDataError("REFLECTION_AUTHORITY_REQUIRED", 401, request_id)

                def finish(self, input_dto, request_id):
                    self.finished = input_dto

                def advance(self, input_dto, request_id):
                    self.advances.append(input_dto)
                    return ReflectionTaskAdvanceOutputDTO(status="PARTIAL_FAILED", revision=5)

            worker = Worker()
            engine = ReflectionsTaskEngine(
                worker, object(), SessionProjectionBrokerSettings(timeout_seconds=1, max_bytes=1024),
                _runtime_http_config(),
            )
            with patch.dict(os.environ, {"AGENT_CWD": root, "DREAM_REFLECTIONS_WORKSPACE_ROOT": root}):
                await engine.run(TASK_ID, load=load)
            self.assertEqual(worker.begun.section, "traits")
            self.assertEqual((worker.finished.section, worker.finished.expected_revision, worker.finished.outcome),
                             ("traits", 2, "failed"))
            self.assertEqual([(item.action, item.expected_revision) for item in worker.advances], [("finalize", 4)])
            self.assertEqual(worker.reports, [TASK_ID])
            self.assertEqual([event.sequence for event in worker.events], [6, 7])
            self.assertEqual(worker.events[-1].payload, {
                "completed_sections": ["echoes"], "failed_sections": ["traits"], "result_count": 1,
            })

        with tempfile.TemporaryDirectory() as root:
            _run(case(str(Path(root).resolve())))


class _OwnerWorker:
    def __init__(self, *, revoke_error: bool = False) -> None:
        self.revoke_error = revoke_error
        self.revokes = 0

    def revoke_authority(self, input_dto, request_id):
        self.revokes += 1
        if self.revoke_error:
            raise AdminDataError("ADMIN_UNAVAILABLE", 503, request_id)
        return object()


class _FailingBroker:
    def __init__(self) -> None:
        self.closed = 0

    def close(self):
        self.closed += 1
        raise RuntimeError("broker-close")


class _TrackingKeeper:
    def __init__(self) -> None:
        self.closed = 0

    def close(self):
        self.closed += 1


class ReflectionSectionPersistenceTest(unittest.TestCase):
    @staticmethod
    def _owner(worker: _OwnerWorker) -> AdminReflectionSectionPersistence:
        return AdminReflectionSectionPersistence(
            _begin(),
            _snapshot(),
            object(),
            worker,
            session_broker_settings=SessionProjectionBrokerSettings(
                timeout_seconds=1, max_bytes=1024 * 1024
            ),
        )

    def test_rta_never_enters_child_env_workspace_or_logs(self):
        with tempfile.TemporaryDirectory() as root:
            root = str(Path(root).resolve())
            worker = _OwnerWorker(revoke_error=True)
            owner = self._owner(worker)
            owner.start()
            child_env = owner.session_projection_child_env()
            self.assertNotIn(RTA, json_text(child_env))
            with patch.dict(os.environ, {
                "AGENT_CWD": root,
                "DREAM_REFLECTIONS_WORKSPACE_ROOT": root,
            }):
                memory = runtime._prepare_section_workspace(_load(root), _begin())
            contents = "\n".join(
                path.read_text(encoding="utf-8")
                for path in memory.rglob("*")
                if path.is_file()
            )
            self.assertNotIn(RTA, contents)
            with self.assertLogs(
                "services.admin_data.reflection_section_persistence", level="ERROR"
            ) as captured:
                owner.close()
            self.assertNotIn(RTA, "\n".join(captured.output))
            self.assertEqual(worker.revokes, 1)

    def test_gateway_exchange_uses_rta_only_at_admin_dto_boundary(self):
        owner = self._owner(_OwnerWorker())
        grant = object()
        runtime_client = object()
        gateway_owner = object()
        with patch(
            "services.admin_data.reflection_section_persistence.AdminDelegationCreator"
        ) as creator_type, patch(
            "services.admin_data.reflection_section_persistence.AdminRuntimeClient",
            return_value=runtime_client,
        ), patch(
            "services.admin_data.reflection_section_persistence.AdminGatewayRuntime",
            return_value=gateway_owner,
        ) as gateway_type:
            creator_type.return_value.create.return_value = grant
            result = owner.gateway_runtime(_runtime_http_config(), "gateway-request")
        self.assertIs(result, gateway_owner)
        request = creator_type.return_value.create.call_args.args[0]
        self.assertEqual(request.purpose, "gateway-cli")
        self.assertEqual(request.thread_id, THREAD_ID)
        self.assertIsNone(request.run_id)
        self.assertEqual(
            request.scopes,
            ["messages:create", "messages:count_tokens", "models:list"],
        )
        self.assertEqual(
            creator_type.return_value.create.call_args.kwargs,
            {"access_token": RTA, "request_id": "gateway-request"},
        )
        gateway_type.assert_called_once_with(grant, runtime_client)

    def test_close_failure_still_stops_keeper_and_attempts_revoke(self):
        worker = _OwnerWorker()
        owner = self._owner(worker)
        broker = _FailingBroker()
        keeper = _TrackingKeeper()
        owner._session_broker = broker
        owner._keeper = keeper
        with self.assertRaisesRegex(RuntimeError, "broker-close"):
            owner.close()
        self.assertEqual(broker.closed, 1)
        self.assertEqual(keeper.closed, 1)
        self.assertEqual(worker.revokes, 1)


def json_text(value) -> str:
    import json
    return json.dumps(value, sort_keys=True)


if __name__ == "__main__":
    unittest.main()
