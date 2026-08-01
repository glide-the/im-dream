"""Focused canonical event persistence, delivery, ordering, and safety tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import sqlite3
import tempfile
import unittest

from pydantic import ValidationError

from backend.database import create_event_tables
from backend.models.events import (
    CANONICAL_EVENT_TYPES,
    CanonicalEventType,
    EventEnvelope,
)
from backend.services.events.event_consumer import EventConsumer
from backend.services.events.event_emitter import EventEmissionError, EventEmitter


NOW = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)
WORKSPACE_ID = "workspace-events-test"


PAYLOADS = {
    CanonicalEventType.DECK_PLUGIN_RELEASE_PUBLISHED: {
        "plugin_id": "voice-decks.story-dramatize",
        "plugin_version": "3.1.0",
        "manifest_hash": "sha256:" + "a" * 64,
        "runtime_plugin_lock_id": "rpl_test",
    },
    CanonicalEventType.DECK_PLUGIN_INSTALLATION_STATUS_CHANGED: {
        "installation_id": "dpi_test",
        "old_status": "installing",
        "new_status": "ready",
        "error_code": None,
    },
    CanonicalEventType.RUNTIME_PLUGIN_MATERIALIZATION_STATUS_CHANGED: {
        "materialization_id": "rpm_test",
        "runtime_plugin_id": "ink-dream-tools",
        "runtime_plugin_version": "1.4.2",
        "declared_status": "required",
        "materialized_status": "ready",
    },
    CanonicalEventType.DECK_PLUGIN_BINDING_CHANGED: {
        "deck_id": "deck_test",
        "old_exact_release": None,
        "new_exact_release": "voice-decks.story-dramatize@3.1.0",
        "binding_revision": 1,
        "actor_id": "actor_test",
    },
    CanonicalEventType.WORKFLOW_PREFLIGHT_STATUS_CHANGED: {
        "workflow_preflight_id": "pf_test",
        "status": "passed",
        "failed_check": None,
        "error_code": None,
        "expires_at": "2026-08-01T12:05:00Z",
    },
    CanonicalEventType.WORKFLOW_RUN_CREATED: {
        "workflow_run_id": "run_test",
        "source_voice_thread_id": "thread_test",
        "source_message_id": "message_test",
        "source_message_time": "2026-08-01T12:00:00Z",
        "runtime_plugin_lock_id": "rpl_test",
        "runtime_load_receipt_id": None,
    },
    CanonicalEventType.WORKFLOW_RUN_STATUS_CHANGED: {
        "workflow_run_id": "run_test",
        "old_status": "queued",
        "new_status": "running",
        "failed_step": None,
        "error_code": None,
    },
    CanonicalEventType.WORKFLOW_RUN_STEP_PROGRESSED: {
        "workflow_run_id": "run_test",
        "step_id": "draft",
        "progress": 0.5,
        "safe_summary": "Draft normalized",
    },
    CanonicalEventType.WORKFLOW_RESULT_PERSISTED: {
        "workflow_run_id": "run_test",
        "result_refs": ["result_test"],
        "result_schema_version": 1,
    },
    CanonicalEventType.WORKFLOW_RUN_SECURITY_CANCELLED: {
        "workflow_run_id": "run_test",
        "revocation_policy_ref": "policy_test",
        "safe_reason": "Release revoked",
    },
}


class EventFixture:
    def __init__(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self.temp_dir.name) / "events.db"
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.queue_events: list[EventEnvelope] = []
        self.projections: list[dict] = []
        self.emitter = EventEmitter(
            self.db,
            workspace_id=WORKSPACE_ID,
            queue_publisher=self.queue_events.append,
            projection_publisher=self.projections.append,
            clock=lambda: NOW,
        )

    def close(self) -> None:
        self.db.close()
        self.temp_dir.cleanup()

    def build(
        self,
        aggregate_id: str = "run_test",
        event_type: CanonicalEventType = CanonicalEventType.WORKFLOW_RUN_CREATED,
    ) -> EventEnvelope:
        return self.emitter.build_envelope(
            event_type,
            aggregate_id,
            PAYLOADS[event_type],
            "operation_test",
        )


class EventEnvelopeTests(unittest.TestCase):
    def test_all_ten_canonical_event_contracts_validate(self) -> None:
        fixture = EventFixture()
        try:
            envelopes = [
                fixture.emitter.build_envelope(
                    event_type,
                    f"aggregate-{index}",
                    payload,
                    "operation_test",
                )
                for index, (event_type, payload) in enumerate(PAYLOADS.items())
            ]
            self.assertEqual(10, len(CANONICAL_EVENT_TYPES))
            self.assertEqual(CANONICAL_EVENT_TYPES, {e.event_type.value for e in envelopes})
            self.assertTrue(all(e.event_id.startswith("evt_") for e in envelopes))
            self.assertTrue(all(e.event_version == 1 for e in envelopes))
            self.assertTrue(all(e.aggregate_version == 1 for e in envelopes))
            self.assertTrue(all(e.occurred_at == NOW for e in envelopes))
        finally:
            fixture.close()

    def test_payload_requires_minimum_contract_fields(self) -> None:
        fixture = EventFixture()
        try:
            payload = dict(PAYLOADS[CanonicalEventType.WORKFLOW_RUN_STEP_PROGRESSED])
            payload.pop("safe_summary")
            with self.assertRaisesRegex(ValidationError, "safe_summary"):
                fixture.emitter.build_envelope(
                    CanonicalEventType.WORKFLOW_RUN_STEP_PROGRESSED,
                    "run_test",
                    payload,
                    "operation_test",
                )
        finally:
            fixture.close()

    def test_sensitive_keys_and_email_values_are_rejected_recursively(self) -> None:
        fixture = EventFixture()
        try:
            base = dict(PAYLOADS[CanonicalEventType.WORKFLOW_RUN_STEP_PROGRESSED])
            for unsafe in (
                {"prompt_excerpt": "write a private scene"},
                {"nested": {"secret": "plaintext"}},
                {"preflight_token": "opaque-token"},
                {"settings_json": {"model": "private"}},
                {"actor": "private@example.com"},
            ):
                with self.subTest(unsafe=unsafe):
                    with self.assertRaises(ValidationError):
                        fixture.emitter.build_envelope(
                            CanonicalEventType.WORKFLOW_RUN_STEP_PROGRESSED,
                            "run_test",
                            {**base, **unsafe},
                            "operation_test",
                        )
            safe = fixture.emitter.build_envelope(
                CanonicalEventType.WORKFLOW_RUN_STEP_PROGRESSED,
                "run_test",
                {**base, "prompt_ref": "prm_123", "settings_hash": "sha256:safe"},
                "operation_test",
            )
            self.assertEqual("prm_123", safe.payload["prompt_ref"])
        finally:
            fixture.close()


class EventEmitterTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.fixture = EventFixture()

    async def asyncTearDown(self) -> None:
        self.fixture.close()

    async def test_persist_first_delivery_and_sanitized_projection(self) -> None:
        envelope = self.fixture.build()
        await self.fixture.emitter.emit(envelope)

        row = self.fixture.db.execute(
            "SELECT * FROM events WHERE event_id = ?", (envelope.event_id,)
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(envelope.event_type.value, row["event_type"])
        self.assertEqual(1, row["aggregate_version"])
        self.assertEqual([envelope], self.fixture.queue_events)
        self.assertEqual(envelope.event_id, self.fixture.projections[0]["event_id"])
        self.assertEqual(envelope.payload, self.fixture.projections[0]["payload"])

    async def test_retry_same_id_redelivers_without_duplicate_audit_row(self) -> None:
        envelope = self.fixture.build()
        await self.fixture.emitter.emit(envelope)
        await self.fixture.emitter.emit(envelope)

        count = self.fixture.db.execute(
            "SELECT COUNT(*) FROM events WHERE event_id = ?", (envelope.event_id,)
        ).fetchone()[0]
        self.assertEqual(1, count)
        self.assertEqual([envelope, envelope], self.fixture.queue_events)

    async def test_delivery_failure_retains_authoritative_row_for_retry(self) -> None:
        attempts = 0

        def fail_once(_: EventEnvelope) -> None:
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise RuntimeError("queue unavailable")

        self.fixture.emitter._queue_publisher = fail_once
        envelope = self.fixture.build()
        with self.assertRaises(EventEmissionError) as caught:
            await self.fixture.emitter.emit(envelope)
        self.assertTrue(caught.exception.persisted)
        self.assertEqual(1, self.fixture.db.execute("SELECT COUNT(*) FROM events").fetchone()[0])

        await self.fixture.emitter.emit(envelope)
        self.assertEqual(2, attempts)
        self.assertEqual(1, self.fixture.db.execute("SELECT COUNT(*) FROM events").fetchone()[0])

    async def test_aggregate_versions_follow_persisted_authority(self) -> None:
        first = self.fixture.build()
        await self.fixture.emitter.emit(first)
        second = self.fixture.build()
        await self.fixture.emitter.emit(second)
        self.assertEqual((1, 2), (first.aggregate_version, second.aggregate_version))

    async def test_database_events_are_append_only(self) -> None:
        envelope = self.fixture.build()
        await self.fixture.emitter.emit(envelope)
        with self.assertRaisesRegex(sqlite3.IntegrityError, "append-only"):
            self.fixture.db.execute(
                "UPDATE events SET correlation_id = 'changed' WHERE event_id = ?",
                (envelope.event_id,),
            )
        self.fixture.db.rollback()
        with self.assertRaisesRegex(sqlite3.IntegrityError, "append-only"):
            self.fixture.db.execute(
                "DELETE FROM events WHERE event_id = ?", (envelope.event_id,)
            )
        self.fixture.db.rollback()

    async def test_schema_initialization_is_idempotent(self) -> None:
        create_event_tables(self.fixture.db)
        create_event_tables(self.fixture.db)
        self.fixture.db.commit()
        index_names = {
            row[0]
            for row in self.fixture.db.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index' AND tbl_name = 'events'"
            )
        }
        self.assertTrue(
            {
                "idx_events_aggregate",
                "idx_events_type",
                "idx_events_correlation",
            }.issubset(index_names)
        )


class EventConsumerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.fixture = EventFixture()

    def tearDown(self) -> None:
        self.fixture.close()

    async def test_duplicate_delivery_is_processed_once(self) -> None:
        handled: list[str] = []
        consumer = EventConsumer(lambda event: handled.append(event.event_id))
        envelope = self.fixture.build()

        self.assertTrue(await consumer.consume(envelope))
        self.assertFalse(await consumer.consume(envelope))
        self.assertEqual([envelope.event_id], handled)

    async def test_out_of_order_events_are_buffered_and_drained(self) -> None:
        handled: list[int] = []
        consumer = EventConsumer(lambda event: handled.append(event.aggregate_version))
        first = self.fixture.build()
        second = first.model_copy(
            update={
                "event_id": "evt_" + "2" * 32,
                "aggregate_version": 2,
                "causation_id": first.event_id,
            }
        )

        self.assertFalse(await consumer.consume(second))
        self.assertEqual([], handled)
        self.assertTrue(await consumer.consume(first))
        self.assertEqual([1, 2], handled)
        self.assertEqual(3, consumer.next_expected_version(first.aggregate_id))

    async def test_missing_predecessor_emits_one_timeout_alert(self) -> None:
        now = 10.0
        alerts = []
        consumer = EventConsumer(
            lambda _: None,
            gap_timeout_seconds=5,
            alert_handler=alerts.append,
            monotonic_clock=lambda: now,
        )
        second = self.fixture.build().model_copy(
            update={
                "event_id": "evt_" + "2" * 32,
                "aggregate_version": 2,
            }
        )
        await consumer.consume(second)
        now = 16.0

        emitted = await consumer.check_timeouts()
        self.assertEqual(1, len(emitted))
        self.assertEqual(1, emitted[0].expected_version)
        self.assertEqual(2, emitted[0].next_buffered_version)
        self.assertEqual(emitted, alerts)
        self.assertEqual([], await consumer.check_timeouts())


if __name__ == "__main__":
    unittest.main()
