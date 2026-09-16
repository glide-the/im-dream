# [Input] Admin-backed Reflections engine, strict DTOs, and section RTA owner.
# [Output] Event durability, revision recovery, terminal restart, credential isolation, and shutdown tests.
# [Pos] Reflections runtime unit boundary; no PostgreSQL, HTTP server, or real model.
# [Sync] 2026-09-16: cover source-fenced Gateway grant composition for Reflections.
# [Sync] 2026-09-15: replace legacy SQLite flow tests with Admin consumer/runtime invariants.

from __future__ import annotations

import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

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
    ReflectionSectionBeginOutputDTO,
    ReflectionSectionStateDTO,
    ReflectionSessionSnapshotDTO,
    ReflectionStatsDTO,
    ReflectionTaskAdvanceOutputDTO,
    ReflectionTaskDTO,
    ReflectionTaskGetOutputDTO,
    ReflectionTaskPublicInputDTO,
    ReflectionWorkerLoadOutputDTO,
)
from services.admin_data.session_projection_broker import (
    SessionProjectionBrokerSettings,
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
                        current_user={},
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
