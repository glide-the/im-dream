"""Deterministic Deck Plugin disable and security-revocation orchestration.

This module owns the frozen DECK-019 domain contract but deliberately does not
reach into the Workflow Run state machine or an identity service.  Those
boundaries are injected through an authorizer, impact resolver, and run
coordinator.  The provided in-memory adapters are development/test fixtures;
production must replace them with durable transactional adapters and pass the
separate Stage 4 evidence/reviewer/rollout gates.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
import hashlib
import inspect
import json
import re
import sqlite3
from typing import Any, Literal
import uuid


SECURITY_REVOCATION = "SECURITY_REVOCATION"
REVOCATION_AUTHORIZATION_DENIED = "REVOCATION_AUTHORIZATION_DENIED"
REVOCATION_SCOPE_APPROVAL_REQUIRED = "REVOCATION_SCOPE_APPROVAL_REQUIRED"
REVOCATION_INCIDENT_REQUIRED = "REVOCATION_INCIDENT_REQUIRED"
REVOCATION_GRACE_OUT_OF_RANGE = "REVOCATION_GRACE_OUT_OF_RANGE"
REVOCATION_TARGET_INVALID = "REVOCATION_TARGET_INVALID"
REVOCATION_IDEMPOTENCY_CONFLICT = "REVOCATION_IDEMPOTENCY_CONFLICT"
RUN_TERMINAL_CONFLICT = "RUN_TERMINAL_CONFLICT"
SECURITY_TERMINATION_UNCONFIRMED = "SECURITY_TERMINATION_UNCONFIRMED"

REVOCATION_POLICY_REVISION = "security-revocation/v1"
MAX_REVOKE_GRACE_SECONDS = 300
DEFAULT_REVOKE_GRACE_SECONDS = 60
BREAK_GLASS_MAX_SECONDS = 15 * 60
EMERGENCY_RATIFICATION_SECONDS = 30 * 60
NOTIFICATION_RETRY_OFFSETS_SECONDS = (0, 30, 120, 600, 1800, 7200)

_DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_TARGET_ALIASES = {
    "release": "deck_plugin_release",
    "digest": "runtime_plugin_digest",
}
_TARGET_TYPES = frozenset(
    {
        "deck_plugin_release",
        "runtime_plugin_digest",
        "signing_identity",
        "capability_policy",
    }
)
_TERMINAL_RUN_STATES = frozenset(
    {"completed", "cancelled", "failed", "rejected"}
)


class RevocationLevel(str, Enum):
    DISABLE = "disable"
    REVOKE = "revoke"
    EMERGENCY = "emergency"


_LEVEL_STRENGTH = {
    RevocationLevel.DISABLE: 1,
    RevocationLevel.REVOKE: 2,
    RevocationLevel.EMERGENCY: 3,
}


class RevocationServiceError(ValueError):
    def __init__(
        self, code: str, summary: str, *, details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(summary)
        self.code = code
        self.summary = summary
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "summary": self.summary,
                "details": self.details,
            }
        }


@dataclass(frozen=True)
class RevocationRequest:
    idempotency_key: str
    level: RevocationLevel
    target_type: str
    target_key: str
    environment_ids: tuple[str, ...]
    tenant_or_project_ids: tuple[str, ...]
    reason_code: str
    incident_id: str | None
    requested_by: str
    approved_by: str | None
    requested_grace_seconds: int | None

    def semantic_fingerprint(self) -> str:
        payload = asdict(self)
        payload["level"] = self.level.value
        return _sha256_json(payload)


@dataclass(frozen=True)
class RevocationAuthorization:
    """Server-resolved authorization; callers cannot self-assert this object."""

    allowed: bool
    actor_role: str
    actor_permissions: frozenset[str]
    allowed_environment_ids: frozenset[str]
    allowed_tenant_or_project_ids: frozenset[str]
    allowed_targets: frozenset[tuple[str, str]]
    executor_id: str
    executor_is_machine: bool
    reviewer_id: str
    approver_role: str | None = None
    approver_permissions: frozenset[str] = frozenset()
    break_glass_expires_at: datetime | None = None
    global_scope_approved: bool = False
    denial_reason: str | None = None


@dataclass(frozen=True)
class ImpactResolution:
    release_ids: tuple[str, ...] = ()
    digest_ids: tuple[str, ...] = ()
    policy_ids: tuple[str, ...] = ()
    installation_ids: tuple[str, ...] = ()
    binding_ids: tuple[str, ...] = ()
    runtime_lock_ids: tuple[str, ...] = ()
    snapshot_ids: tuple[str, ...] = ()
    workflow_run_ids: tuple[str, ...] = ()
    session_ids: tuple[str, ...] = ()
    runtime_node_ids: tuple[str, ...] = ()
    resolved_environment_ids: tuple[str, ...] = ()
    resolved_tenant_or_project_ids: tuple[str, ...] = ()
    resolver_revision: str = "fixture/v1"

    def canonical(self) -> dict[str, Any]:
        return {
            name: sorted(set(value)) if isinstance(value, tuple) else value
            for name, value in asdict(self).items()
        }


@dataclass(frozen=True)
class RevocationImpactManifest:
    impact_manifest_id: str
    manifest_sha256: str
    target_type: str
    target_key: str
    resolved_at: datetime
    resolution: ImpactResolution
    counts: tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class SecurityRevocationRecord:
    revocation_id: str
    idempotency_key: str
    request_fingerprint: str
    revocation_sequence: int
    level: RevocationLevel
    target_type: str
    target_key: str
    environment_ids: tuple[str, ...]
    tenant_or_project_ids: tuple[str, ...]
    requested_by: str
    approved_by: str | None
    executor_id: str
    reviewer_id: str
    reason_code: str
    incident_id: str | None
    effective_at: datetime
    effective_grace_seconds: int | None
    grace_deadline_at: datetime | None
    revocation_policy_revision: str
    impact_manifest_id: str
    manifest_sha256: str
    extends_revocation_id: str | None = None
    ratification_deadline_at: datetime | None = None


@dataclass(frozen=True)
class CancellationCommand:
    command_id: str
    revocation_id: str
    workflow_run_id: str
    impact_manifest_id: str
    created_at: datetime


@dataclass(frozen=True)
class AuditEvent:
    event_id: str
    event_type: str
    occurred_at: datetime
    revocation_id: str
    workflow_run_id: str | None = None
    command_id: str | None = None
    delivery_attempt: int | None = None
    termination_mode: str | None = None
    before_state: str | None = None
    after_state: str | None = None
    receipt_id: str | None = None
    details: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class Incident:
    incident_id: str
    incident_type: str
    revocation_id: str
    workflow_run_id: str | None
    created_at: datetime
    details: tuple[tuple[str, str], ...] = ()


@dataclass
class NotificationOutboxEntry:
    notification_id: str
    revocation_id: str
    workflow_run_id: str | None
    recipient_id: str
    notification_phase: str
    created_at: datetime
    attempt_count: int = 0
    delivered_at: datetime | None = None
    provider_receipt_id: str | None = None
    next_attempt_at: datetime | None = None
    last_error_code: str | None = None


@dataclass(frozen=True)
class NotificationDeliveryResult:
    delivered: bool
    provider_receipt_id: str | None = None
    error_code: str | None = None


@dataclass(frozen=True)
class RevocationResult:
    revocation_id: str
    impact_manifest_id: str
    manifest_sha256: str
    effective_at: datetime
    effective_grace_seconds: int | None
    grace_deadline_at: datetime | None
    processed_workflow_run_ids: tuple[str, ...]
    already_covered_by_revocation_id: str | None = None
    replayed: bool = False


@dataclass
class InMemoryRun:
    workflow_run_id: str
    status: str
    status_version: int = 1
    owner_id: str = "run-owner"
    started_by_user_id: str = "run-starter"
    primary_revocation_id: str | None = None
    primary_level: RevocationLevel | None = None
    related_revocation_ids: list[str] = field(default_factory=list)
    grace_deadline_at: datetime | None = None
    termination_mode: Literal["graceful", "hard"] | None = None
    termination_receipt_id: str | None = None
    isolation_receipt_id: str | None = None
    terminal_reason_code: str | None = None


@dataclass(frozen=True)
class CancellationClaim:
    outcome: Literal["claimed", "escalated", "suppressed", "terminal"]
    before_state: str
    after_state: str


@dataclass(frozen=True)
class TerminationObservation:
    outcome: Literal["cancelled", "failed", "unconfirmed"]
    receipt_id: str | None
    isolation_receipt_id: str | None
    inbox_receipt_id: str
    before_state: str
    after_state: str


@dataclass(frozen=True)
class RuntimeCommandReceipt:
    runtime_command_receipt_id: str
    revocation_id: str
    workflow_run_id: str
    command_id: str
    termination_mode: Literal["graceful", "hard"]
    inbox_receipt_id: str
    termination_receipt_id: str | None
    isolation_receipt_id: str | None
    outcome: Literal["cancelled", "failed", "unconfirmed"]
    observed_at: datetime


@dataclass(frozen=True)
class EvidenceCase:
    case_name: str
    test_case_id: str
    evidence_ids: tuple[str, ...]
    observed_at: datetime


@dataclass(frozen=True)
class Stage4RevocationEvidencePack:
    evidence_pack_id: str
    design_decision_id: str
    revocation_policy_revision: str
    tested_release_or_commit: str
    test_environment: str
    test_run_id: str
    generated_at: datetime
    independent_reviewer_id: str | None
    independent_reviewer_signature: str | None
    rollout_approval_id: str | None
    cases: tuple[EvidenceCase, ...]
    evidence_manifest_sha256: str
    production_gate_satisfied: bool


EVIDENCE_CASE_NAMES = (
    "three_level_authorization_and_behavior",
    "four_target_impact_resolution",
    "scope_expansion_replay_and_concurrency",
    "disable_does_not_terminate",
    "revoke_grace_to_hard_stop",
    "emergency_immediate_hard_stop",
    "at_least_once_cancellation",
    "terminal_mapping_and_conflict_guard",
    "append_only_audit",
    "notification_timing_and_failure",
    "quarantine_and_superseding_recovery",
)


def _sha256_json(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), default=str
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


async def _resolve(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


class InMemoryRevocationRepository:
    """Append-only development repository with deterministic replay indexes."""

    def __init__(self) -> None:
        self.records: list[SecurityRevocationRecord] = []
        self.manifests: dict[str, RevocationImpactManifest] = {}
        self.commands: dict[tuple[str, str], CancellationCommand] = {}
        self.audit_events: list[AuditEvent] = []
        self.incidents: list[Incident] = []
        self.runtime_receipts: dict[tuple[str, str], RuntimeCommandReceipt] = {}
        self.notifications: dict[tuple[str, str | None, str, str], NotificationOutboxEntry] = {}
        self.quarantined_targets: set[tuple[str, str]] = set()
        self._by_idempotency: dict[str, SecurityRevocationRecord] = {}

    def next_sequence(self) -> int:
        return len(self.records) + 1

    def find_idempotency(self, key: str) -> SecurityRevocationRecord | None:
        return self._by_idempotency.get(key)

    def get_record(self, revocation_id: str) -> SecurityRevocationRecord:
        return next(item for item in self.records if item.revocation_id == revocation_id)

    def commit_revocation(
        self,
        record: SecurityRevocationRecord,
        manifest: RevocationImpactManifest,
        commands: Iterable[CancellationCommand],
        notifications: Iterable[NotificationOutboxEntry],
        effective_event: AuditEvent,
    ) -> None:
        """Commit barrier, manifest, cancellation outbox and notifications together."""

        if record.idempotency_key in self._by_idempotency:
            raise RevocationServiceError(
                REVOCATION_IDEMPOTENCY_CONFLICT,
                "idempotency key was concurrently committed",
            )
        self.records.append(record)
        self.manifests[manifest.impact_manifest_id] = manifest
        self._by_idempotency[record.idempotency_key] = record
        for command in commands:
            self.commands[(command.revocation_id, command.workflow_run_id)] = command
        for item in notifications:
            key = (
                item.revocation_id,
                item.workflow_run_id,
                item.recipient_id,
                item.notification_phase,
            )
            self.notifications.setdefault(key, item)
        self.audit_events.append(effective_event)
        if record.level in {RevocationLevel.REVOKE, RevocationLevel.EMERGENCY}:
            self.quarantined_targets.add((record.target_type, record.target_key))

    def append_audit(self, event: AuditEvent) -> None:
        self.audit_events.append(event)

    def append_incident(self, incident: Incident) -> None:
        self.incidents.append(incident)

    def append_runtime_receipt(self, receipt: RuntimeCommandReceipt) -> None:
        self.runtime_receipts.setdefault(
            (receipt.command_id, receipt.termination_mode), receipt
        )

    def save_notification(self, _entry: NotificationOutboxEntry) -> None:
        # Entries are mutable values held by ``self.notifications``.
        return None

    def find_covering(self, request: RevocationRequest) -> SecurityRevocationRecord | None:
        candidates = [
            item
            for item in self.records
            if item.target_type == request.target_type
            and item.target_key == request.target_key
            and _LEVEL_STRENGTH[item.level] >= _LEVEL_STRENGTH[request.level]
            and set(item.environment_ids).issuperset(request.environment_ids)
            and set(item.tenant_or_project_ids).issuperset(
                request.tenant_or_project_ids
            )
        ]
        return min(candidates, key=lambda item: item.revocation_sequence, default=None)

    def find_extension_base(self, request: RevocationRequest) -> SecurityRevocationRecord | None:
        candidates = [
            item
            for item in self.records
            if item.target_type == request.target_type
            and item.target_key == request.target_key
            and (
                set(request.environment_ids).issuperset(item.environment_ids)
                or set(request.tenant_or_project_ids).issuperset(
                    item.tenant_or_project_ids
                )
            )
        ]
        return max(candidates, key=lambda item: item.revocation_sequence, default=None)


class SQLiteRevocationRepository:
    """Durable append-only repository owned entirely by the revocation domain."""

    _APPEND_ONLY_TABLES = (
        "security_revocations",
        "revocation_impact_manifests",
        "revocation_cancel_commands",
        "revocation_audit_events",
        "revocation_incidents",
        "revocation_runtime_receipts",
        "revocation_quarantined_targets",
    )

    def __init__(self, db: sqlite3.Connection) -> None:
        if db.in_transaction:
            raise RuntimeError("revocation repository requires a clean transaction boundary")
        self.db = db
        self.db.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        statements = (
            """
            CREATE TABLE IF NOT EXISTS security_revocations (
                revocation_id TEXT PRIMARY KEY,
                idempotency_key TEXT NOT NULL UNIQUE,
                request_fingerprint TEXT NOT NULL,
                revocation_sequence INTEGER NOT NULL UNIQUE,
                level TEXT NOT NULL,
                target_type TEXT NOT NULL,
                target_key TEXT NOT NULL,
                environment_ids_json TEXT NOT NULL,
                tenant_or_project_ids_json TEXT NOT NULL,
                record_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS revocation_impact_manifests (
                impact_manifest_id TEXT PRIMARY KEY,
                revocation_id TEXT NOT NULL UNIQUE,
                manifest_sha256 TEXT NOT NULL,
                manifest_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (revocation_id) REFERENCES security_revocations(revocation_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS revocation_cancel_commands (
                command_id TEXT PRIMARY KEY,
                revocation_id TEXT NOT NULL,
                workflow_run_id TEXT NOT NULL,
                command_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(revocation_id, workflow_run_id),
                FOREIGN KEY (revocation_id) REFERENCES security_revocations(revocation_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS revocation_audit_events (
                event_id TEXT PRIMARY KEY,
                revocation_id TEXT NOT NULL,
                workflow_run_id TEXT,
                event_type TEXT NOT NULL,
                event_json TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                FOREIGN KEY (revocation_id) REFERENCES security_revocations(revocation_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS revocation_incidents (
                incident_id TEXT PRIMARY KEY,
                revocation_id TEXT NOT NULL,
                workflow_run_id TEXT,
                incident_type TEXT NOT NULL,
                incident_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (revocation_id) REFERENCES security_revocations(revocation_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS revocation_runtime_receipts (
                runtime_command_receipt_id TEXT PRIMARY KEY,
                revocation_id TEXT NOT NULL,
                workflow_run_id TEXT NOT NULL,
                command_id TEXT NOT NULL,
                termination_mode TEXT NOT NULL,
                inbox_receipt_id TEXT NOT NULL,
                receipt_json TEXT NOT NULL,
                observed_at TEXT NOT NULL,
                UNIQUE(command_id, termination_mode),
                FOREIGN KEY (revocation_id) REFERENCES security_revocations(revocation_id),
                FOREIGN KEY (command_id) REFERENCES revocation_cancel_commands(command_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS revocation_notification_outbox (
                notification_id TEXT PRIMARY KEY,
                revocation_id TEXT NOT NULL,
                workflow_run_id TEXT,
                recipient_id TEXT NOT NULL,
                notification_phase TEXT NOT NULL,
                created_at TEXT NOT NULL,
                attempt_count INTEGER NOT NULL DEFAULT 0 CHECK(attempt_count BETWEEN 0 AND 6),
                delivered_at TEXT,
                provider_receipt_id TEXT,
                next_attempt_at TEXT,
                last_error_code TEXT,
                UNIQUE(revocation_id, workflow_run_id, recipient_id, notification_phase),
                FOREIGN KEY (revocation_id) REFERENCES security_revocations(revocation_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS revocation_quarantined_targets (
                target_type TEXT NOT NULL,
                target_key TEXT NOT NULL,
                revocation_id TEXT NOT NULL,
                quarantined_at TEXT NOT NULL,
                PRIMARY KEY(target_type, target_key, revocation_id),
                FOREIGN KEY (revocation_id) REFERENCES security_revocations(revocation_id)
            )
            """,
        )
        for statement in statements:
            self.db.execute(statement)
        for table in self._APPEND_ONLY_TABLES:
            for operation in ("UPDATE", "DELETE"):
                trigger = f"{table}_no_{operation.lower()}"
                self.db.execute(
                    f"""
                    CREATE TRIGGER IF NOT EXISTS {trigger}
                    BEFORE {operation} ON {table}
                    BEGIN
                        SELECT RAISE(ABORT, '{table} is append-only');
                    END
                    """
                )
        self.db.execute(
            """
            CREATE TRIGGER IF NOT EXISTS revocation_notification_outbox_no_delete
            BEFORE DELETE ON revocation_notification_outbox
            BEGIN
                SELECT RAISE(ABORT, 'revocation_notification_outbox is append-only');
            END
            """
        )
        self.db.commit()

    @property
    def records(self) -> list[SecurityRevocationRecord]:
        rows = self.db.execute(
            "SELECT record_json FROM security_revocations ORDER BY revocation_sequence"
        ).fetchall()
        return [self._record(json.loads(row["record_json"])) for row in rows]

    @property
    def manifests(self) -> dict[str, RevocationImpactManifest]:
        rows = self.db.execute(
            "SELECT manifest_json FROM revocation_impact_manifests"
        ).fetchall()
        values = [self._manifest(json.loads(row["manifest_json"])) for row in rows]
        return {item.impact_manifest_id: item for item in values}

    @property
    def commands(self) -> dict[tuple[str, str], CancellationCommand]:
        rows = self.db.execute(
            "SELECT command_json FROM revocation_cancel_commands"
        ).fetchall()
        values = [self._command(json.loads(row["command_json"])) for row in rows]
        return {(item.revocation_id, item.workflow_run_id): item for item in values}

    @property
    def audit_events(self) -> list[AuditEvent]:
        rows = self.db.execute(
            "SELECT event_json FROM revocation_audit_events ORDER BY rowid"
        ).fetchall()
        return [self._audit_event(json.loads(row["event_json"])) for row in rows]

    @property
    def incidents(self) -> list[Incident]:
        rows = self.db.execute(
            "SELECT incident_json FROM revocation_incidents ORDER BY rowid"
        ).fetchall()
        return [self._incident(json.loads(row["incident_json"])) for row in rows]

    @property
    def runtime_receipts(self) -> dict[tuple[str, str], RuntimeCommandReceipt]:
        rows = self.db.execute(
            "SELECT receipt_json FROM revocation_runtime_receipts ORDER BY rowid"
        ).fetchall()
        values = [
            self._runtime_receipt(json.loads(row["receipt_json"])) for row in rows
        ]
        return {(item.command_id, item.termination_mode): item for item in values}

    @property
    def notifications(self) -> dict[tuple[str, str | None, str, str], NotificationOutboxEntry]:
        rows = self.db.execute(
            "SELECT * FROM revocation_notification_outbox ORDER BY rowid"
        ).fetchall()
        values = [self._notification(row) for row in rows]
        return {
            (
                item.revocation_id,
                item.workflow_run_id,
                item.recipient_id,
                item.notification_phase,
            ): item
            for item in values
        }

    @property
    def quarantined_targets(self) -> set[tuple[str, str]]:
        return {
            (row["target_type"], row["target_key"])
            for row in self.db.execute(
                "SELECT target_type, target_key FROM revocation_quarantined_targets"
            )
        }

    def next_sequence(self) -> int:
        row = self.db.execute(
            "SELECT COALESCE(MAX(revocation_sequence), 0) + 1 AS value FROM security_revocations"
        ).fetchone()
        return int(row["value"])

    def find_idempotency(self, key: str) -> SecurityRevocationRecord | None:
        row = self.db.execute(
            "SELECT record_json FROM security_revocations WHERE idempotency_key = ?",
            (key,),
        ).fetchone()
        return self._record(json.loads(row["record_json"])) if row else None

    def get_record(self, revocation_id: str) -> SecurityRevocationRecord:
        row = self.db.execute(
            "SELECT record_json FROM security_revocations WHERE revocation_id = ?",
            (revocation_id,),
        ).fetchone()
        if row is None:
            raise KeyError(revocation_id)
        return self._record(json.loads(row["record_json"]))

    def commit_revocation(
        self,
        record: SecurityRevocationRecord,
        manifest: RevocationImpactManifest,
        commands: Iterable[CancellationCommand],
        notifications: Iterable[NotificationOutboxEntry],
        effective_event: AuditEvent,
    ) -> None:
        try:
            with self.db:
                self.db.execute(
                    """
                    INSERT INTO security_revocations (
                        revocation_id, idempotency_key, request_fingerprint,
                        revocation_sequence, level, target_type, target_key,
                        environment_ids_json, tenant_or_project_ids_json,
                        record_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.revocation_id,
                        record.idempotency_key,
                        record.request_fingerprint,
                        record.revocation_sequence,
                        record.level.value,
                        record.target_type,
                        record.target_key,
                        json.dumps(record.environment_ids),
                        json.dumps(record.tenant_or_project_ids),
                        self._dump(record),
                        record.effective_at.isoformat(),
                    ),
                )
                self.db.execute(
                    """
                    INSERT INTO revocation_impact_manifests
                    (impact_manifest_id, revocation_id, manifest_sha256, manifest_json, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        manifest.impact_manifest_id,
                        record.revocation_id,
                        manifest.manifest_sha256,
                        self._dump(manifest),
                        manifest.resolved_at.isoformat(),
                    ),
                )
                for command in commands:
                    self.db.execute(
                        """
                        INSERT INTO revocation_cancel_commands
                        (command_id, revocation_id, workflow_run_id, command_json, created_at)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            command.command_id,
                            command.revocation_id,
                            command.workflow_run_id,
                            self._dump(command),
                            command.created_at.isoformat(),
                        ),
                    )
                for item in notifications:
                    self._insert_notification(item)
                self._insert_audit(effective_event)
                if record.level in {RevocationLevel.REVOKE, RevocationLevel.EMERGENCY}:
                    self.db.execute(
                        """
                        INSERT INTO revocation_quarantined_targets
                        (target_type, target_key, revocation_id, quarantined_at)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            record.target_type,
                            record.target_key,
                            record.revocation_id,
                            record.effective_at.isoformat(),
                        ),
                    )
        except sqlite3.IntegrityError as exc:
            raise RevocationServiceError(
                REVOCATION_IDEMPOTENCY_CONFLICT,
                "revocation commit conflicted with an existing immutable record",
            ) from exc

    def append_audit(self, event: AuditEvent) -> None:
        with self.db:
            self._insert_audit(event)

    def append_incident(self, incident: Incident) -> None:
        with self.db:
            self.db.execute(
                """
                INSERT INTO revocation_incidents
                (incident_id, revocation_id, workflow_run_id, incident_type,
                 incident_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    incident.incident_id,
                    incident.revocation_id,
                    incident.workflow_run_id,
                    incident.incident_type,
                    self._dump(incident),
                    incident.created_at.isoformat(),
                ),
            )

    def append_runtime_receipt(self, receipt: RuntimeCommandReceipt) -> None:
        with self.db:
            self.db.execute(
                """
                INSERT OR IGNORE INTO revocation_runtime_receipts (
                    runtime_command_receipt_id, revocation_id, workflow_run_id,
                    command_id, termination_mode, inbox_receipt_id,
                    receipt_json, observed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    receipt.runtime_command_receipt_id,
                    receipt.revocation_id,
                    receipt.workflow_run_id,
                    receipt.command_id,
                    receipt.termination_mode,
                    receipt.inbox_receipt_id,
                    self._dump(receipt),
                    receipt.observed_at.isoformat(),
                ),
            )

    def save_notification(self, entry: NotificationOutboxEntry) -> None:
        with self.db:
            cursor = self.db.execute(
                """
                UPDATE revocation_notification_outbox
                SET attempt_count = ?, delivered_at = ?, provider_receipt_id = ?,
                    next_attempt_at = ?, last_error_code = ?
                WHERE notification_id = ?
                """,
                (
                    entry.attempt_count,
                    self._iso(entry.delivered_at),
                    entry.provider_receipt_id,
                    self._iso(entry.next_attempt_at),
                    entry.last_error_code,
                    entry.notification_id,
                ),
            )
        if cursor.rowcount != 1:
            raise KeyError(entry.notification_id)

    def find_covering(self, request: RevocationRequest) -> SecurityRevocationRecord | None:
        candidates = [
            item
            for item in self.records
            if item.target_type == request.target_type
            and item.target_key == request.target_key
            and _LEVEL_STRENGTH[item.level] >= _LEVEL_STRENGTH[request.level]
            and set(item.environment_ids).issuperset(request.environment_ids)
            and set(item.tenant_or_project_ids).issuperset(request.tenant_or_project_ids)
        ]
        return min(candidates, key=lambda item: item.revocation_sequence, default=None)

    def find_extension_base(self, request: RevocationRequest) -> SecurityRevocationRecord | None:
        candidates = [
            item
            for item in self.records
            if item.target_type == request.target_type
            and item.target_key == request.target_key
            and (
                set(request.environment_ids).issuperset(item.environment_ids)
                or set(request.tenant_or_project_ids).issuperset(
                    item.tenant_or_project_ids
                )
            )
        ]
        return max(candidates, key=lambda item: item.revocation_sequence, default=None)

    def _insert_notification(self, item: NotificationOutboxEntry) -> None:
        self.db.execute(
            """
            INSERT INTO revocation_notification_outbox (
                notification_id, revocation_id, workflow_run_id, recipient_id,
                notification_phase, created_at, attempt_count, delivered_at,
                provider_receipt_id, next_attempt_at, last_error_code
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item.notification_id,
                item.revocation_id,
                item.workflow_run_id,
                item.recipient_id,
                item.notification_phase,
                item.created_at.isoformat(),
                item.attempt_count,
                self._iso(item.delivered_at),
                item.provider_receipt_id,
                self._iso(item.next_attempt_at),
                item.last_error_code,
            ),
        )

    def _insert_audit(self, event: AuditEvent) -> None:
        self.db.execute(
            """
            INSERT INTO revocation_audit_events
            (event_id, revocation_id, workflow_run_id, event_type, event_json, occurred_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.revocation_id,
                event.workflow_run_id,
                event.event_type,
                self._dump(event),
                event.occurred_at.isoformat(),
            ),
        )

    @staticmethod
    def _dump(value: Any) -> str:
        return json.dumps(asdict(value), default=SQLiteRevocationRepository._json_default)

    @staticmethod
    def _json_default(value: Any) -> str:
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, Enum):
            return value.value
        raise TypeError(f"cannot encode {type(value)!r}")

    @staticmethod
    def _record(value: dict[str, Any]) -> SecurityRevocationRecord:
        value["level"] = RevocationLevel(value["level"])
        for key in ("effective_at", "grace_deadline_at", "ratification_deadline_at"):
            value[key] = SQLiteRevocationRepository._datetime(value.get(key))
        value["environment_ids"] = tuple(value["environment_ids"])
        value["tenant_or_project_ids"] = tuple(value["tenant_or_project_ids"])
        return SecurityRevocationRecord(**value)

    @staticmethod
    def _manifest(value: dict[str, Any]) -> RevocationImpactManifest:
        resolution = value["resolution"]
        for key, item in tuple(resolution.items()):
            if isinstance(item, list):
                resolution[key] = tuple(item)
        value["resolution"] = ImpactResolution(**resolution)
        value["resolved_at"] = SQLiteRevocationRepository._datetime(value["resolved_at"])
        value["counts"] = tuple(tuple(item) for item in value["counts"])
        return RevocationImpactManifest(**value)

    @staticmethod
    def _command(value: dict[str, Any]) -> CancellationCommand:
        value["created_at"] = SQLiteRevocationRepository._datetime(value["created_at"])
        return CancellationCommand(**value)

    @staticmethod
    def _audit_event(value: dict[str, Any]) -> AuditEvent:
        value["occurred_at"] = SQLiteRevocationRepository._datetime(value["occurred_at"])
        value["details"] = tuple(tuple(item) for item in value["details"])
        return AuditEvent(**value)

    @staticmethod
    def _incident(value: dict[str, Any]) -> Incident:
        value["created_at"] = SQLiteRevocationRepository._datetime(value["created_at"])
        value["details"] = tuple(tuple(item) for item in value["details"])
        return Incident(**value)

    @staticmethod
    def _runtime_receipt(value: dict[str, Any]) -> RuntimeCommandReceipt:
        value["observed_at"] = SQLiteRevocationRepository._datetime(
            value["observed_at"]
        )
        return RuntimeCommandReceipt(**value)

    @staticmethod
    def _notification(row: sqlite3.Row) -> NotificationOutboxEntry:
        return NotificationOutboxEntry(
            notification_id=row["notification_id"],
            revocation_id=row["revocation_id"],
            workflow_run_id=row["workflow_run_id"],
            recipient_id=row["recipient_id"],
            notification_phase=row["notification_phase"],
            created_at=SQLiteRevocationRepository._datetime(row["created_at"]),
            attempt_count=row["attempt_count"],
            delivered_at=SQLiteRevocationRepository._datetime(row["delivered_at"]),
            provider_receipt_id=row["provider_receipt_id"],
            next_attempt_at=SQLiteRevocationRepository._datetime(row["next_attempt_at"]),
            last_error_code=row["last_error_code"],
        )

    @staticmethod
    def _datetime(value: str | datetime | None) -> datetime | None:
        if value is None or isinstance(value, datetime):
            return value
        return datetime.fromisoformat(value)

    @staticmethod
    def _iso(value: datetime | None) -> str | None:
        return value.isoformat() if value else None


class InMemoryRunCoordinator:
    """Development coordinator that models CAS, idempotent kill, and terminal mapping."""

    def __init__(
        self,
        runs: Iterable[InMemoryRun] = (),
        *,
        termination_outcomes: dict[tuple[str, str], str] | None = None,
    ) -> None:
        self.runs = {item.workflow_run_id: item for item in runs}
        self.termination_outcomes = termination_outcomes or {}
        self.dispatch_counts: dict[tuple[str, str], int] = {}
        self.receipts: dict[tuple[str, str], TerminationObservation] = {}

    def get(self, workflow_run_id: str) -> InMemoryRun:
        return self.runs[workflow_run_id]

    async def claim_cancellation(
        self, run_id: str, record: SecurityRevocationRecord
    ) -> CancellationClaim:
        run = self.runs[run_id]
        before = run.status
        if run.status in _TERMINAL_RUN_STATES:
            return CancellationClaim("terminal", before, before)
        if record.revocation_id not in run.related_revocation_ids:
            run.related_revocation_ids.append(record.revocation_id)
        if run.primary_revocation_id is None:
            run.primary_revocation_id = record.revocation_id
            run.primary_level = record.level
            run.grace_deadline_at = record.grace_deadline_at
            run.status = "cancelling"
            run.status_version += 1
            return CancellationClaim("claimed", before, run.status)

        assert run.primary_level is not None
        if _LEVEL_STRENGTH[record.level] > _LEVEL_STRENGTH[run.primary_level]:
            run.primary_revocation_id = record.revocation_id
            run.primary_level = record.level
            if record.grace_deadline_at is not None:
                if run.grace_deadline_at is None:
                    run.grace_deadline_at = record.grace_deadline_at
                else:
                    run.grace_deadline_at = min(
                        run.grace_deadline_at, record.grace_deadline_at
                    )
            return CancellationClaim("escalated", before, run.status)
        return CancellationClaim("suppressed", before, run.status)

    async def dispatch_termination(
        self,
        run_id: str,
        command_id: str,
        mode: Literal["graceful", "hard"],
    ) -> TerminationObservation:
        key = (command_id, mode)
        if key in self.receipts:
            return self.receipts[key]
        self.dispatch_counts[key] = self.dispatch_counts.get(key, 0) + 1
        run = self.runs[run_id]
        before = run.status
        outcome = self.termination_outcomes.get((run_id, mode), "unconfirmed")
        receipt_id: str | None = None
        isolation_receipt_id: str | None = None
        if outcome == "ack":
            run.status = "cancelled"
            run.status_version += 1
            run.termination_mode = mode
            run.terminal_reason_code = SECURITY_REVOCATION
            receipt_id = "trr_" + hashlib.sha256(key[0].encode()).hexdigest()[:32]
            run.termination_receipt_id = receipt_id
            observed = "cancelled"
        elif outcome == "isolated_failure":
            run.status = "failed"
            run.status_version += 1
            run.termination_mode = mode
            run.terminal_reason_code = SECURITY_REVOCATION
            isolation_receipt_id = "irr_" + hashlib.sha256(
                (key[0] + mode).encode()
            ).hexdigest()[:32]
            run.isolation_receipt_id = isolation_receipt_id
            observed = "failed"
        else:
            run.termination_mode = mode
            observed = "unconfirmed"
        result = TerminationObservation(
            outcome=observed,
            receipt_id=receipt_id,
            isolation_receipt_id=isolation_receipt_id,
            inbox_receipt_id="inr_"
            + hashlib.sha256(f"{command_id}|{mode}|inbox".encode()).hexdigest()[:32],
            before_state=before,
            after_state=run.status,
        )
        self.receipts[key] = result
        return result


Authorizer = Callable[
    [RevocationRequest], RevocationAuthorization | Awaitable[RevocationAuthorization]
]
ImpactResolver = Callable[
    [RevocationRequest], ImpactResolution | Awaitable[ImpactResolution]
]
NotificationSender = Callable[
    [NotificationOutboxEntry],
    NotificationDeliveryResult | Awaitable[NotificationDeliveryResult],
]


class RevocationService:
    def __init__(
        self,
        repository: InMemoryRevocationRepository | SQLiteRevocationRepository,
        run_coordinator: InMemoryRunCoordinator,
        *,
        authorizer: Authorizer,
        impact_resolver: ImpactResolver,
        notification_sender: NotificationSender | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.repository = repository
        self.run_coordinator = run_coordinator
        self._authorizer = authorizer
        self._impact_resolver = impact_resolver
        self._notification_sender = notification_sender
        self._clock = clock or (lambda: datetime.now(UTC))

    async def revoke(
        self,
        idempotency_key: str,
        level: RevocationLevel,
        target_type: str,
        target_key: str,
        environment_ids: list[str],
        tenant_or_project_ids: list[str],
        reason_code: str,
        incident_id: str | None,
        requested_by: str,
        approved_by: str | None,
        requested_grace_seconds: int | None,
    ) -> RevocationResult:
        request = self._request(
            idempotency_key,
            level,
            target_type,
            target_key,
            environment_ids,
            tenant_or_project_ids,
            reason_code,
            incident_id,
            requested_by,
            approved_by,
            requested_grace_seconds,
        )
        replay = self.repository.find_idempotency(request.idempotency_key)
        if replay is not None:
            if replay.request_fingerprint != request.semantic_fingerprint():
                raise RevocationServiceError(
                    REVOCATION_IDEMPOTENCY_CONFLICT,
                    "idempotency key was reused with different request semantics",
                )
            return self._result(replay, replayed=True)

        now = self._now()
        authorization = await _resolve(self._authorizer(request))
        self._validate_authorization(request, authorization, now)
        resolution = await _resolve(self._impact_resolver(request))
        self._validate_resolution_scope(request, resolution)

        covered = self.repository.find_covering(request)
        if covered is not None:
            result = self._result(covered, replayed=False)
            return RevocationResult(
                **{
                    **asdict(result),
                    "already_covered_by_revocation_id": covered.revocation_id,
                }
            )

        manifest = self._impact_manifest(request, resolution, now)
        grace, deadline = self._time_contract(request, now)
        sequence = self.repository.next_sequence()
        revocation_id = f"rev_{uuid.uuid4().hex}"
        extension = self.repository.find_extension_base(request)
        record = SecurityRevocationRecord(
            revocation_id=revocation_id,
            idempotency_key=request.idempotency_key,
            request_fingerprint=request.semantic_fingerprint(),
            revocation_sequence=sequence,
            level=request.level,
            target_type=request.target_type,
            target_key=request.target_key,
            environment_ids=request.environment_ids,
            tenant_or_project_ids=request.tenant_or_project_ids,
            requested_by=request.requested_by,
            approved_by=request.approved_by,
            executor_id=authorization.executor_id,
            reviewer_id=authorization.reviewer_id,
            reason_code=request.reason_code,
            incident_id=request.incident_id,
            effective_at=now,
            effective_grace_seconds=grace,
            grace_deadline_at=deadline,
            revocation_policy_revision=REVOCATION_POLICY_REVISION,
            impact_manifest_id=manifest.impact_manifest_id,
            manifest_sha256=manifest.manifest_sha256,
            extends_revocation_id=(extension.revocation_id if extension else None),
            ratification_deadline_at=(
                now + timedelta(seconds=EMERGENCY_RATIFICATION_SECONDS)
                if request.level is RevocationLevel.EMERGENCY
                and request.approved_by is None
                else None
            ),
        )
        commands = tuple(
            CancellationCommand(
                command_id=self._command_id(revocation_id, run_id),
                revocation_id=revocation_id,
                workflow_run_id=run_id,
                impact_manifest_id=manifest.impact_manifest_id,
                created_at=now,
            )
            for run_id in resolution.workflow_run_ids
            if request.level is not RevocationLevel.DISABLE
        )
        notifications = self._notifications(record, resolution)
        effective_event = self._audit(
            "security.revocation.effective", record, occurred_at=now
        )
        self.repository.commit_revocation(
            record, manifest, commands, notifications, effective_event
        )

        if request.level is not RevocationLevel.DISABLE:
            await self._cancel_running_runs(
                revocation_id,
                manifest.impact_manifest_id,
                request.level,
                now,
                deadline,
            )
        if self._notification_sender is not None:
            await self.deliver_due_notifications(now)
        return self._result(record)

    async def _cancel_running_runs(
        self,
        revocation_id: str,
        impact_manifest_id: str,
        level: RevocationLevel,
        effective_at: datetime,
        grace_deadline_at: datetime | None,
    ) -> None:
        record = self.repository.get_record(revocation_id)
        manifest = self.repository.manifests[impact_manifest_id]
        for run_id in manifest.resolution.workflow_run_ids:
            command = self.repository.commands[(revocation_id, run_id)]
            claim = await self.run_coordinator.claim_cancellation(run_id, record)
            if claim.outcome in {"suppressed", "terminal"}:
                self.repository.append_audit(
                    self._audit(
                        "workflow.run.security_cancellation_suppressed",
                        record,
                        run_id=run_id,
                        command_id=command.command_id,
                        before=claim.before_state,
                        after=claim.after_state,
                    )
                )
                continue
            self.repository.append_audit(
                self._audit(
                    "workflow.run.security_cancellation_requested",
                    record,
                    run_id=run_id,
                    command_id=command.command_id,
                    termination_mode=(
                        "hard"
                        if level is RevocationLevel.EMERGENCY
                        or grace_deadline_at == effective_at
                        else "graceful"
                    ),
                    before=claim.before_state,
                    after=claim.after_state,
                )
            )
            if level is RevocationLevel.EMERGENCY or grace_deadline_at == effective_at:
                await self._dispatch(record, command, "hard", effective_at)
            else:
                await self._dispatch(record, command, "graceful", effective_at)

    async def process_due_hard_stops(self, now: datetime | None = None) -> tuple[str, ...]:
        observed_at = self._as_utc(now or self._now())
        dispatched: list[str] = []
        for record in self.repository.records:
            if record.level is RevocationLevel.DISABLE:
                continue
            if record.grace_deadline_at is None or observed_at < record.grace_deadline_at:
                continue
            manifest = self.repository.manifests[record.impact_manifest_id]
            for run_id in manifest.resolution.workflow_run_ids:
                run = self.run_coordinator.get(run_id)
                if run.status in _TERMINAL_RUN_STATES:
                    continue
                command = self.repository.commands[(record.revocation_id, run_id)]
                await self._dispatch(record, command, "hard", observed_at)
                dispatched.append(command.command_id)
        return tuple(dispatched)

    def process_unconfirmed_terminations(
        self, now: datetime | None = None
    ) -> tuple[str, ...]:
        """Escalate only after ten seconds without termination or isolation ack."""

        observed_at = self._as_utc(now or self._now())
        created: list[str] = []
        for event in self.repository.audit_events:
            if event.event_type != "workflow.run.security_hard_stop_requested":
                continue
            if observed_at < event.occurred_at + timedelta(seconds=10):
                continue
            assert event.workflow_run_id is not None and event.command_id is not None
            run = self.run_coordinator.get(event.workflow_run_id)
            if run.status in {"cancelled", "failed"}:
                continue
            record = self.repository.get_record(event.revocation_id)
            command = self.repository.commands[
                (event.revocation_id, event.workflow_run_id)
            ]
            before = len(self.repository.incidents)
            self._append_unconfirmed_incident(record, command, observed_at)
            if len(self.repository.incidents) > before:
                created.append(self.repository.incidents[-1].incident_id)
        return tuple(created)

    async def _dispatch(
        self,
        record: SecurityRevocationRecord,
        command: CancellationCommand,
        mode: Literal["graceful", "hard"],
        occurred_at: datetime,
    ) -> TerminationObservation:
        if mode == "hard":
            self.repository.append_audit(
                self._audit(
                    "workflow.run.security_hard_stop_requested",
                    record,
                    run_id=command.workflow_run_id,
                    command_id=command.command_id,
                    termination_mode=mode,
                    occurred_at=occurred_at,
                )
            )
        observation = await self.run_coordinator.dispatch_termination(
            command.workflow_run_id, command.command_id, mode
        )
        self.repository.append_runtime_receipt(
            RuntimeCommandReceipt(
                runtime_command_receipt_id="rcr_"
                + hashlib.sha256(f"{command.command_id}|{mode}".encode()).hexdigest()[:32],
                revocation_id=record.revocation_id,
                workflow_run_id=command.workflow_run_id,
                command_id=command.command_id,
                termination_mode=mode,
                inbox_receipt_id=observation.inbox_receipt_id,
                termination_receipt_id=observation.receipt_id,
                isolation_receipt_id=observation.isolation_receipt_id,
                outcome=observation.outcome,
                observed_at=occurred_at,
            )
        )
        if observation.outcome == "cancelled":
            event_type = "workflow.run.security_cancelled"
        elif observation.outcome == "failed":
            event_type = "workflow.run.security_failed"
        else:
            return observation
        self.repository.append_audit(
            self._audit(
                event_type,
                record,
                run_id=command.workflow_run_id,
                command_id=command.command_id,
                termination_mode=mode,
                before=observation.before_state,
                after=observation.after_state,
                receipt_id=observation.receipt_id or observation.isolation_receipt_id,
                occurred_at=occurred_at,
            )
        )
        return observation

    def guard_terminal_transition(self, workflow_run_id: str, desired_status: str) -> bool:
        run = self.run_coordinator.get(workflow_run_id)
        if run.primary_revocation_id is None or desired_status != "completed":
            return True
        record = self.repository.get_record(run.primary_revocation_id)
        self.repository.append_audit(
            self._audit(
                RUN_TERMINAL_CONFLICT,
                record,
                run_id=workflow_run_id,
                before=run.status,
                after=desired_status,
            )
        )
        return False

    def is_new_operation_blocked(
        self,
        *,
        target_type: str,
        target_key: str,
        environment_id: str,
        tenant_or_project_id: str,
    ) -> bool:
        """Evaluate the committed barrier for installation/binding/preflight/run."""

        normalized_type = _TARGET_ALIASES.get(target_type, target_type)
        return any(
            item.target_type == normalized_type
            and item.target_key == target_key
            and environment_id in item.environment_ids
            and tenant_or_project_id in item.tenant_or_project_ids
            for item in self.repository.records
        )

    async def deliver_due_notifications(
        self, now: datetime | None = None
    ) -> tuple[str, ...]:
        if self._notification_sender is None:
            return ()
        observed_at = self._as_utc(now or self._now())
        delivered: list[str] = []
        for entry in self.repository.notifications.values():
            if entry.delivered_at is not None or entry.attempt_count >= 6:
                continue
            if entry.next_attempt_at is not None and observed_at < entry.next_attempt_at:
                continue
            result = await _resolve(self._notification_sender(entry))
            entry.attempt_count += 1
            record = self.repository.get_record(entry.revocation_id)
            if result.delivered:
                entry.delivered_at = observed_at
                entry.provider_receipt_id = result.provider_receipt_id
                entry.next_attempt_at = None
                delivered.append(entry.notification_id)
                self.repository.append_audit(
                    self._audit(
                        "security.notification.delivered",
                        record,
                        run_id=entry.workflow_run_id,
                        delivery_attempt=entry.attempt_count,
                        receipt_id=result.provider_receipt_id,
                        occurred_at=observed_at,
                    )
                )
                self.repository.save_notification(entry)
                continue
            entry.last_error_code = result.error_code or "NOTIFICATION_PROVIDER_ERROR"
            if entry.attempt_count >= 6:
                entry.next_attempt_at = None
                incident = Incident(
                    incident_id=f"inc_{uuid.uuid4().hex}",
                    incident_type="security.notification.delivery_failed",
                    revocation_id=entry.revocation_id,
                    workflow_run_id=entry.workflow_run_id,
                    created_at=observed_at,
                    details=(("notification_id", entry.notification_id),),
                )
                self.repository.append_incident(incident)
                self.repository.append_audit(
                    self._audit(
                        "security.notification.delivery_failed",
                        record,
                        run_id=entry.workflow_run_id,
                        delivery_attempt=entry.attempt_count,
                        occurred_at=observed_at,
                    )
                )
            else:
                entry.next_attempt_at = entry.created_at + timedelta(
                    seconds=NOTIFICATION_RETRY_OFFSETS_SECONDS[entry.attempt_count]
                )
            self.repository.save_notification(entry)
        return tuple(delivered)

    def process_overdue_emergency_ratifications(
        self, now: datetime | None = None
    ) -> tuple[str, ...]:
        observed_at = self._as_utc(now or self._now())
        created: list[str] = []
        existing = {
            (item.revocation_id, item.incident_type) for item in self.repository.incidents
        }
        for record in self.repository.records:
            if (
                record.ratification_deadline_at is None
                or observed_at <= record.ratification_deadline_at
                or (record.revocation_id, "EMERGENCY_RATIFICATION_OVERDUE") in existing
            ):
                continue
            incident = Incident(
                incident_id=f"inc_{uuid.uuid4().hex}",
                incident_type="EMERGENCY_RATIFICATION_OVERDUE",
                revocation_id=record.revocation_id,
                workflow_run_id=None,
                created_at=observed_at,
                details=(("freeze_break_glass_principal", record.requested_by),),
            )
            self.repository.append_incident(incident)
            created.append(incident.incident_id)
        return tuple(created)

    @staticmethod
    def build_evidence_pack(
        cases: Iterable[EvidenceCase],
        *,
        tested_release_or_commit: str,
        test_environment: str,
        test_run_id: str,
        generated_at: datetime,
        independent_reviewer_id: str | None = None,
        independent_reviewer_signature: str | None = None,
        rollout_approval_id: str | None = None,
    ) -> Stage4RevocationEvidencePack:
        case_tuple = tuple(cases)
        by_name = {item.case_name: item for item in case_tuple}
        missing = [name for name in EVIDENCE_CASE_NAMES if name not in by_name]
        if missing:
            raise RevocationServiceError(
                "REVOCATION_EVIDENCE_INCOMPLETE",
                "all 11 evidence cases are required",
                details={"missing_cases": missing},
            )
        if len(by_name) != len(case_tuple) or any(
            not item.test_case_id or not item.evidence_ids for item in case_tuple
        ):
            raise RevocationServiceError(
                "REVOCATION_EVIDENCE_INVALID",
                "evidence cases require unique names and raw evidence IDs",
            )
        ordered = tuple(by_name[name] for name in EVIDENCE_CASE_NAMES)
        payload = {
            "design_decision_id": "DECK-GATE-DEC-019",
            "revocation_policy_revision": REVOCATION_POLICY_REVISION,
            "tested_release_or_commit": tested_release_or_commit,
            "test_environment": test_environment,
            "test_run_id": test_run_id,
            "generated_at": generated_at.isoformat(),
            "independent_reviewer_id": independent_reviewer_id,
            "independent_reviewer_signature": independent_reviewer_signature,
            "rollout_approval_id": rollout_approval_id,
            "cases": [asdict(item) for item in ordered],
        }
        manifest_hash = _sha256_json(payload)
        return Stage4RevocationEvidencePack(
            evidence_pack_id="s4rep_" + manifest_hash.split(":", 1)[1][:32],
            design_decision_id="DECK-GATE-DEC-019",
            revocation_policy_revision=REVOCATION_POLICY_REVISION,
            tested_release_or_commit=tested_release_or_commit,
            test_environment=test_environment,
            test_run_id=test_run_id,
            generated_at=generated_at,
            independent_reviewer_id=independent_reviewer_id,
            independent_reviewer_signature=independent_reviewer_signature,
            rollout_approval_id=rollout_approval_id,
            cases=ordered,
            evidence_manifest_sha256=manifest_hash,
            production_gate_satisfied=bool(
                independent_reviewer_id
                and independent_reviewer_signature
                and rollout_approval_id
            ),
        )

    def _request(
        self,
        idempotency_key: str,
        level: RevocationLevel,
        target_type: str,
        target_key: str,
        environment_ids: list[str],
        tenant_or_project_ids: list[str],
        reason_code: str,
        incident_id: str | None,
        requested_by: str,
        approved_by: str | None,
        requested_grace_seconds: int | None,
    ) -> RevocationRequest:
        try:
            normalized_level = RevocationLevel(level)
        except ValueError as exc:
            raise RevocationServiceError(
                REVOCATION_TARGET_INVALID, "unknown revocation level"
            ) from exc
        normalized_type = _TARGET_ALIASES.get(target_type.strip(), target_type.strip())
        if normalized_type not in _TARGET_TYPES:
            raise RevocationServiceError(
                REVOCATION_TARGET_INVALID, "unknown revocation target_type"
            )
        normalized_key = target_key.strip()
        if not normalized_key or (
            normalized_type == "runtime_plugin_digest"
            and not _DIGEST_PATTERN.fullmatch(normalized_key)
        ):
            raise RevocationServiceError(
                REVOCATION_TARGET_INVALID, "target_key is not canonical"
            )
        if normalized_type == "signing_identity" and len(normalized_key.split("|")) != 4:
            raise RevocationServiceError(
                REVOCATION_TARGET_INVALID,
                "signing_identity requires trust_domain|issuer|subject|key_fingerprint",
            )
        if normalized_type == "capability_policy" and "@" not in normalized_key:
            raise RevocationServiceError(
                REVOCATION_TARGET_INVALID,
                "capability_policy requires policy_id@policy_revision",
            )
        environments = self._scope(environment_ids, "environment_ids")
        tenants = self._scope(tenant_or_project_ids, "tenant_or_project_ids")
        required_strings = {
            "idempotency_key": idempotency_key,
            "reason_code": reason_code,
            "requested_by": requested_by,
        }
        if any(not value.strip() for value in required_strings.values()):
            raise RevocationServiceError(
                REVOCATION_TARGET_INVALID, "request identity and reason fields are required"
            )
        if normalized_level in {RevocationLevel.REVOKE, RevocationLevel.EMERGENCY} and not (
            incident_id and incident_id.strip()
        ):
            raise RevocationServiceError(
                REVOCATION_INCIDENT_REQUIRED,
                "REVOKE and EMERGENCY require incident_id",
            )
        if normalized_level is RevocationLevel.DISABLE and requested_grace_seconds is not None:
            raise RevocationServiceError(
                REVOCATION_GRACE_OUT_OF_RANGE, "DISABLE has no grace period"
            )
        if normalized_level is RevocationLevel.REVOKE and (
            requested_grace_seconds is not None
            and not 0 <= requested_grace_seconds <= MAX_REVOKE_GRACE_SECONDS
        ):
            raise RevocationServiceError(
                REVOCATION_GRACE_OUT_OF_RANGE,
                "REVOKE grace must be between 0 and 300 seconds",
            )
        if normalized_level is RevocationLevel.EMERGENCY and requested_grace_seconds not in {
            None,
            0,
        }:
            raise RevocationServiceError(
                REVOCATION_GRACE_OUT_OF_RANGE, "EMERGENCY grace is fixed at zero"
            )
        return RevocationRequest(
            idempotency_key=idempotency_key.strip(),
            level=normalized_level,
            target_type=normalized_type,
            target_key=normalized_key,
            environment_ids=environments,
            tenant_or_project_ids=tenants,
            reason_code=reason_code.strip(),
            incident_id=incident_id.strip() if incident_id else None,
            requested_by=requested_by.strip(),
            approved_by=approved_by.strip() if approved_by else None,
            requested_grace_seconds=requested_grace_seconds,
        )

    def _validate_authorization(
        self,
        request: RevocationRequest,
        authorization: RevocationAuthorization,
        now: datetime,
    ) -> None:
        if not authorization.allowed or not authorization.executor_is_machine:
            raise RevocationServiceError(
                REVOCATION_AUTHORIZATION_DENIED,
                authorization.denial_reason or "authorization denied fail-closed",
            )
        if request.target_type in {"signing_identity", "capability_policy"} and (
            request.level is RevocationLevel.DISABLE
        ):
            raise RevocationServiceError(
                REVOCATION_SCOPE_APPROVAL_REQUIRED,
                "DISABLE cannot target global signing identity or policy scope",
            )
        if (
            not set(request.environment_ids).issubset(
                authorization.allowed_environment_ids
            )
            or not set(request.tenant_or_project_ids).issubset(
                authorization.allowed_tenant_or_project_ids
            )
            or (request.target_type, request.target_key)
            not in authorization.allowed_targets
        ):
            raise RevocationServiceError(
                REVOCATION_SCOPE_APPROVAL_REQUIRED,
                "requested scope exceeds the signed authorization",
                details={
                    "environment_count": len(request.environment_ids),
                    "tenant_or_project_count": len(request.tenant_or_project_ids),
                },
            )
        if request.level is RevocationLevel.DISABLE:
            valid = authorization.actor_role == "DeckOperator" and "deck.disable" in authorization.actor_permissions
        elif request.level is RevocationLevel.REVOKE:
            valid = (
                authorization.actor_role == "SecurityResponder"
                and "security.revocation.propose" in authorization.actor_permissions
                and request.approved_by is not None
                and request.approved_by != request.requested_by
                and authorization.approver_role == "SecurityApprover"
                and "security.revocation.approve" in authorization.approver_permissions
                and authorization.reviewer_id not in {request.requested_by, request.approved_by}
            )
        else:
            expiry = authorization.break_glass_expires_at
            valid = (
                authorization.actor_role == "SecurityResponder"
                and "security.revocation.break_glass" in authorization.actor_permissions
                and expiry is not None
                and now < self._as_utc(expiry) <= now + timedelta(seconds=BREAK_GLASS_MAX_SECONDS)
                and (request.approved_by is None or request.approved_by != request.requested_by)
                and authorization.reviewer_id != request.requested_by
                and authorization.reviewer_id != request.approved_by
                and (
                    request.approved_by is None
                    or (
                        authorization.approver_role == "SecurityApprover"
                        and "security.revocation.approve"
                        in authorization.approver_permissions
                    )
                )
            )
        if not valid:
            raise RevocationServiceError(
                REVOCATION_AUTHORIZATION_DENIED,
                "revocation role separation or required permission was not satisfied",
            )

    @staticmethod
    def _validate_resolution_scope(
        request: RevocationRequest, resolution: ImpactResolution
    ) -> None:
        if not set(resolution.resolved_environment_ids).issubset(
            request.environment_ids
        ) or not set(resolution.resolved_tenant_or_project_ids).issubset(
            request.tenant_or_project_ids
        ):
            raise RevocationServiceError(
                REVOCATION_SCOPE_APPROVAL_REQUIRED,
                "impact resolution crossed the approved scope; resolution was not truncated",
                details={
                    "resolved_environment_count": len(
                        resolution.resolved_environment_ids
                    ),
                    "resolved_tenant_or_project_count": len(
                        resolution.resolved_tenant_or_project_ids
                    ),
                },
            )

    @staticmethod
    def _time_contract(
        request: RevocationRequest, effective_at: datetime
    ) -> tuple[int | None, datetime | None]:
        if request.level is RevocationLevel.DISABLE:
            return None, None
        grace = (
            0
            if request.level is RevocationLevel.EMERGENCY
            else (
                DEFAULT_REVOKE_GRACE_SECONDS
                if request.requested_grace_seconds is None
                else request.requested_grace_seconds
            )
        )
        return grace, effective_at + timedelta(seconds=grace)

    @staticmethod
    def _scope(values: Iterable[str], field_name: str) -> tuple[str, ...]:
        normalized = tuple(sorted(set(item.strip() for item in values)))
        if not normalized or "" in normalized:
            raise RevocationServiceError(
                REVOCATION_SCOPE_APPROVAL_REQUIRED,
                f"{field_name} must contain a non-empty minimum scope",
            )
        return normalized

    def _impact_manifest(
        self,
        request: RevocationRequest,
        resolution: ImpactResolution,
        resolved_at: datetime,
    ) -> RevocationImpactManifest:
        canonical = resolution.canonical()
        payload = {
            "target_type": request.target_type,
            "target_key": request.target_key,
            "environment_ids": request.environment_ids,
            "tenant_or_project_ids": request.tenant_or_project_ids,
            "resolution": canonical,
            "resolved_at": resolved_at.isoformat(),
        }
        digest = _sha256_json(payload)
        counts = tuple(
            sorted(
                (name, len(value))
                for name, value in canonical.items()
                if isinstance(value, list)
            )
        )
        return RevocationImpactManifest(
            impact_manifest_id="rim_" + digest.split(":", 1)[1][:32],
            manifest_sha256=digest,
            target_type=request.target_type,
            target_key=request.target_key,
            resolved_at=resolved_at,
            resolution=ImpactResolution(
                **{
                    key: tuple(value) if isinstance(value, list) else value
                    for key, value in canonical.items()
                }
            ),
            counts=counts,
        )

    def _notifications(
        self, record: SecurityRevocationRecord, resolution: ImpactResolution
    ) -> tuple[NotificationOutboxEntry, ...]:
        recipients: set[tuple[str | None, str, str]] = {
            (None, "security-oncall", "effective"),
            (None, record.requested_by, "effective"),
        }
        for run_id in resolution.workflow_run_ids:
            run = self.run_coordinator.get(run_id)
            recipients.add((run_id, run.owner_id, "effective"))
            recipients.add((run_id, run.started_by_user_id, "effective"))
        return tuple(
            NotificationOutboxEntry(
                notification_id="ntf_"
                + hashlib.sha256(
                    f"{record.revocation_id}|{run_id}|{recipient}|{phase}".encode()
                ).hexdigest()[:32],
                revocation_id=record.revocation_id,
                workflow_run_id=run_id,
                recipient_id=recipient,
                notification_phase=phase,
                created_at=record.effective_at,
                next_attempt_at=record.effective_at,
            )
            for run_id, recipient, phase in sorted(
                recipients, key=lambda value: (value[0] or "", value[1], value[2])
            )
        )

    def _append_unconfirmed_incident(
        self,
        record: SecurityRevocationRecord,
        command: CancellationCommand,
        occurred_at: datetime,
    ) -> None:
        if any(
            item.revocation_id == record.revocation_id
            and item.workflow_run_id == command.workflow_run_id
            and item.incident_type == SECURITY_TERMINATION_UNCONFIRMED
            for item in self.repository.incidents
        ):
            return
        self.repository.append_incident(
            Incident(
                incident_id=f"inc_{uuid.uuid4().hex}",
                incident_type=SECURITY_TERMINATION_UNCONFIRMED,
                revocation_id=record.revocation_id,
                workflow_run_id=command.workflow_run_id,
                created_at=occurred_at,
                details=(("command_id", command.command_id),),
            )
        )

    def _audit(
        self,
        event_type: str,
        record: SecurityRevocationRecord,
        *,
        run_id: str | None = None,
        command_id: str | None = None,
        delivery_attempt: int | None = None,
        termination_mode: str | None = None,
        before: str | None = None,
        after: str | None = None,
        receipt_id: str | None = None,
        occurred_at: datetime | None = None,
    ) -> AuditEvent:
        return AuditEvent(
            event_id=f"evt_{uuid.uuid4().hex}",
            event_type=event_type,
            occurred_at=occurred_at or self._now(),
            revocation_id=record.revocation_id,
            workflow_run_id=run_id,
            command_id=command_id,
            delivery_attempt=delivery_attempt,
            termination_mode=termination_mode,
            before_state=before,
            after_state=after,
            receipt_id=receipt_id,
        )

    def _result(
        self, record: SecurityRevocationRecord, *, replayed: bool = False
    ) -> RevocationResult:
        manifest = self.repository.manifests[record.impact_manifest_id]
        return RevocationResult(
            revocation_id=record.revocation_id,
            impact_manifest_id=record.impact_manifest_id,
            manifest_sha256=record.manifest_sha256,
            effective_at=record.effective_at,
            effective_grace_seconds=record.effective_grace_seconds,
            grace_deadline_at=record.grace_deadline_at,
            processed_workflow_run_ids=manifest.resolution.workflow_run_ids,
            replayed=replayed,
        )

    def _now(self) -> datetime:
        return self._as_utc(self._clock())

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("clock values must be timezone-aware")
        return value.astimezone(UTC)

    @staticmethod
    def _command_id(revocation_id: str, run_id: str) -> str:
        return "scc_" + hashlib.sha256(
            f"{revocation_id}|{run_id}".encode()
        ).hexdigest()[:32]
