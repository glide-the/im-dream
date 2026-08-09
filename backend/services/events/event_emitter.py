"""Persist-first event emission with retry-safe at-least-once delivery."""

from __future__ import annotations

from psycopg import IntegrityError as PostgresIntegrityError

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
import inspect
import json
from typing import Any
from uuid import uuid4

from backend.models.events import CanonicalEventType, EventEnvelope


EnvelopePublisher = Callable[[EventEnvelope], None | Awaitable[None]]
ProjectionPublisher = Callable[[dict[str, Any]], None | Awaitable[None]]


class EventEmissionError(RuntimeError):
    """An event emission failure with explicit persistence semantics."""

    def __init__(self, message: str, *, event_id: str, persisted: bool) -> None:
        super().__init__(message)
        self.event_id = event_id
        self.persisted = persisted


class AggregateVersionConflict(EventEmissionError):
    pass


class EventEmitter:
    """Own audit persistence and adapter-neutral delivery fan-out."""

    def __init__(
        self,
        db: Any,
        *,
        workspace_id: str,
        queue_publisher: EnvelopePublisher | None = None,
        projection_publisher: ProjectionPublisher | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not workspace_id.strip():
            raise ValueError("workspace_id is required")
        if db.in_transaction:
            raise RuntimeError("event emitter requires a clean transaction boundary")
        self.db = db
        self.workspace_id = workspace_id
        self._queue_publisher = queue_publisher
        self._projection_publisher = projection_publisher
        self._clock = clock or (lambda: datetime.now(UTC))

    def build_envelope(
        self,
        event_type: CanonicalEventType | str,
        aggregate_id: str,
        payload: dict[str, Any],
        correlation_id: str,
        causation_id: str | None = None,
    ) -> EventEnvelope:
        """Build an envelope using the next persisted aggregate version."""

        row = self.db.execute(
            "SELECT COALESCE(MAX(aggregate_version), 0) AS version "
            "FROM events WHERE aggregate_id = %s",
            (aggregate_id,),
        ).fetchone()
        aggregate_version = int(row["version"] if row is not None else 0) + 1
        return EventEnvelope(
            event_id=f"evt_{uuid4().hex}",
            event_type=event_type,
            event_version=1,
            occurred_at=self._clock(),
            workspace_id=self.workspace_id,
            aggregate_id=aggregate_id,
            aggregate_version=aggregate_version,
            correlation_id=correlation_id,
            causation_id=causation_id,
            payload=payload,
        )

    async def emit(self, envelope: EventEnvelope) -> None:
        """Persist authoritatively, then deliver; retrying re-delivers the same ID."""

        if envelope.workspace_id != self.workspace_id:
            raise ValueError("event workspace does not match emitter workspace")
        if self.db.in_transaction:
            raise RuntimeError("event emission requires a clean transaction boundary")

        persisted = False
        try:
            self.db.execute("BEGIN")
            self.db.execute(
                """
                INSERT INTO events (
                    event_id, event_type, event_version, occurred_at,
                    workspace_id, aggregate_id, aggregate_version,
                    correlation_id, causation_id, payload_json
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    envelope.event_id,
                    envelope.event_type.value,
                    envelope.event_version,
                    self._serialize_datetime(envelope.occurred_at),
                    envelope.workspace_id,
                    envelope.aggregate_id,
                    envelope.aggregate_version,
                    envelope.correlation_id,
                    envelope.causation_id,
                    self._canonical_payload(envelope.payload),
                ),
            )
            self.db.commit()
            persisted = True
        except PostgresIntegrityError as exc:
            self.db.rollback()
            existing = self._load(envelope.event_id)
            if existing is None:
                raise AggregateVersionConflict(
                    "aggregate version already exists; rebuild the envelope",
                    event_id=envelope.event_id,
                    persisted=False,
                ) from exc
            if existing != envelope:
                raise EventEmissionError(
                    "event_id already exists with different content",
                    event_id=envelope.event_id,
                    persisted=True,
                ) from exc
            persisted = True
        except Exception:
            self.db.rollback()
            raise

        try:
            await self._publish(self._queue_publisher, envelope)
            await self._publish(
                self._projection_publisher,
                envelope.sanitized_projection(),
            )
        except Exception as exc:
            raise EventEmissionError(
                "event is persisted but delivery failed; retry the same envelope",
                event_id=envelope.event_id,
                persisted=persisted,
            ) from exc

    def _load(self, event_id: str) -> EventEnvelope | None:
        row = self.db.execute(
            "SELECT * FROM events WHERE event_id = %s",
            (event_id,),
        ).fetchone()
        if row is None:
            return None
        occurred_at_value = row["occurred_at"]
        occurred_at = (
            occurred_at_value
            if isinstance(occurred_at_value, datetime)
            else datetime.fromisoformat(str(occurred_at_value).replace("Z", "+00:00"))
        )
        return EventEnvelope(
            event_id=row["event_id"],
            event_type=row["event_type"],
            event_version=row["event_version"],
            occurred_at=occurred_at,
            workspace_id=row["workspace_id"],
            aggregate_id=row["aggregate_id"],
            aggregate_version=row["aggregate_version"],
            correlation_id=row["correlation_id"],
            causation_id=row["causation_id"],
            payload=json.loads(row["payload_json"]),
        )

    @staticmethod
    def _serialize_datetime(value: datetime) -> str:
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _canonical_payload(payload: dict[str, Any]) -> str:
        return json.dumps(
            payload,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )

    @staticmethod
    async def _publish(
        publisher: Callable[[Any], Any] | None,
        value: Any,
    ) -> None:
        if publisher is None:
            return
        result = publisher(value)
        if inspect.isawaitable(result):
            await result
