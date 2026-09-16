#!/usr/bin/env python3
# [Sync] 2026-09-16: retire builtin Claude Plugin ref backfill after Registry183-184 ownership moved to Admin.
# [Sync] 2026-09-16: retire zero-caller Deck/Voice/version SQL helpers after public routes adopted Admin DTO operations.
# [Sync] 2026-09-15: reuse the unchanged pure Voice Memory projection outside the database module.
# [Sync] 2026-09-15: nine old social helpers refuse before I/O; public friends use Admin DTOs.
# [Sync] 2026-09-15: retire direct SystemConfig SQL; all production consumers use Admin contracts.
# [Sync] 2026-09-15: retire Reflections section-config writes; the ownerless background reader remains pending.
# [Input] Consume PostgreSQL connections, filesystem paths, JSON data, and optional session text extraction,
#         and memory workspace defaults.
# [Output] Provide remaining persistence helpers for users, sessions, reports,
#          legacy auth/OAuth state, Claude Agent threads/messages and voice
#          partition Memory configs; public Deck/Voice/version and builtin Plugin
#          reconciliation operations are absent and use Admin DTOs.
# [Pos] database node in backend
# [Sync] 2026-09-14: reuse the pure Chat final-history validator; remaining SQL is pending Admin migration.
# [Sync] 2026-06-06: add procedural Memory workspace default config seeding,
#                    backfill, and voice fork/sync propagation.
# [Sync] 2026-06-16: list_sessions_in_range can include full text for Agent
#                    fuzzy cross-session retrieval without changing existing
#                    lightweight callers.
# [Sync] 2026-06-23: add Google OAuth, refresh-token, and Device Flow tables
#                    plus helper functions while preserving the existing users table.
# [Sync] 2026-06-27: add Chat thread search candidates with extracted message
#                    text for Claude Agent history retrieval.
# [Sync] 2026-07-09: allow Chat thread lists to page newest-first with
#                    limit/offset so the frontend history panel can scroll load.
# [Sync] 2026-08-01: add the Story Workspace schema, indexes, and rollback helper.
# [Sync] 2026-08-14: distinguish duplicate email from unavailable transactional
#                    user/default-Free provisioning and verify the complete Free
#                    subscription/default-model postcondition before commit.
# [Sync] 2026-08-14: make first-login preference writes a single PostgreSQL
#                    upsert so concurrent hydration cannot race on the PK.
# [Sync] 2026-08-14: make screenplay roles the active Deck default, retire
#                    untouched legacy forks from business reads, and atomically
#                    persist verified default plugin refs for new Decks.
# [Sync] 2026-08-14: decorate Deck sharing eligibility, exclude self-owned community
#                    results, and enforce publish/fork policy before writes.
# [Sync] 2026-08-14: repair only untouched screenplay defaults with zero plugin
#                    refs while preserving every explicit user selection.
# [Sync] 2026-08-14: keep PostgreSQL community Deck aggregation valid by grouping author display names.
# [Sync] 2026-08-14: include the configured active system-default Deck in the
#                    collectable community projection without reviving retired defaults.
# [Sync] 2026-08-15: make default reconciliation provision a missing user-owned
#                    screenplay Deck under the actor row lock for legacy accounts.
# [Sync] 2026-08-14: decorate Deck list/detail reads with capability-derived
#                    Chat/Dream Agent type and optimistic binding revision.
# [Sync] 2026-08-16: delete mutable Deck plugin refs in the owned Deck transaction;
#                    preserve child/runtime history behind an explicit conflict.
# [Sync] 2026-08-16: lock the Deck aggregate for every effective form mutation
#                    and advance its Admin-capability-backed draft revision.
# [Sync] 2026-08-17: distinguish related Chat threads from immutable runtime snapshots;
#                    allow unused plugin bindings to be cleaned before Deck deletion.
# [Sync] 2026-08-31: remove the daily-picture mutation helper; historical picture
#                    reads and explicit legacy-data import remain.
# [Sync] 2026-08-17: CAS-update the current Agent inside an already bound Chat Deck.
# [Sync] 2026-09-02: add stable keyset Chat message pages and a lightweight latest-id read;
#                    keep the legacy full-history reader for explicit compatibility consumers.
# [Sync] 2026-09-02: make message-id NULL ordering explicit and split the nullable legacy
#                    tail so Admin Drizzle 0042 serves each keyset page without rescanning newer rows.
# [Sync] 2026-09-02: persist a strict assistant final projection, omit canonical
#                    process parts from paged reads, and expose an exact-id detail read.
"""
PostgreSQL runtime persistence helpers for Ink & Memory.

Schema:
- users: User accounts (email, password_hash)
- user_sessions: Editor sessions (editor state JSON)
- daily_pictures: Historical timeline images (base64)
- user_preferences: Voice configs, meta prompts, etc.
"""

import logging
from collections.abc import Iterator, Mapping
from datetime import datetime, timedelta
from threading import RLock
from typing import Any, Optional, Union
import json
from chat_message_projection import validate_chat_history_final_projection as _validate_chat_history_final_projection
from voice_projection import _parse_voice_row
from psycopg import Error as PostgresError
from psycopg import IntegrityError as PostgresIntegrityError
from psycopg.errors import ForeignKeyViolation
from psycopg.pq import TransactionStatus

try:
    from tests.legacy_persistence.postgres import PostgresPool
except ModuleNotFoundError:  # pragma: no cover - package import compatibility
    from backend.tests.legacy_persistence.postgres import PostgresPool

logger = logging.getLogger(__name__)


class ChatMessageIdentityConflict(RuntimeError):
    """A message id is already bound to a different immutable envelope."""

    code = "CHAT_MESSAGE_IDENTITY_CONFLICT"
    status_code = 409

    def __init__(self, message_id: str) -> None:
        self.message_id = message_id
        super().__init__(self.code)


class UserRegistrationUnavailable(RuntimeError):
    """The canonical user/default-Free registration transaction could not commit."""

    code = "USER_REGISTRATION_UNAVAILABLE"

    def __init__(self) -> None:
        super().__init__(self.code)


class DeckDeletionConflict(RuntimeError):
    """The owned Deck still has a business dependency that must be preserved."""

    code = "DECK_DELETE_CONFLICT"

    _MESSAGES = {
        "child_decks": "Deck cannot be deleted while derived Decks still reference it.",
        "related_threads": "Deck cannot be deleted while related Chat conversations still exist.",
        "runtime_history": "Deck cannot be deleted because it has immutable runtime history.",
        "referenced_records": "Deck cannot be deleted because it is still referenced.",
    }

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(self._MESSAGES.get(reason, self._MESSAGES["referenced_records"]))


class PostgresRow(Mapping[str, object]):
    """Small named-and-positional mapping returned by psycopg.

    Existing domain services use both named lookup and positional lookup while
    they are moved behind repositories.  Keeping that row behaviour at the
    driver boundary avoids leaking tuple/dict branching through the domain;
    it does not translate SQL or provide a SQLite fallback.
    """

    __slots__ = ("_names", "_values", "_positions")

    def __init__(self, names: tuple[str, ...], values: tuple[object, ...]) -> None:
        self._names = names
        self._values = values
        self._positions = {name: index for index, name in enumerate(names)}

    def __getitem__(self, key: str | int) -> object:
        if isinstance(key, int):
            return self._values[key]
        return self._values[self._positions[key]]

    def __iter__(self) -> Iterator[str]:
        return iter(self._names)

    def __len__(self) -> int:
        return len(self._names)

    def keys(self) -> tuple[str, ...]:
        return self._names


def _postgres_row_factory(cursor):
    names = tuple(column.name for column in (cursor.description or ()))

    def make_row(values: tuple[object, ...]) -> PostgresRow:
        return PostgresRow(names, values)

    return make_row


class _PooledConnectionLease:
    """Connection facade whose ``close`` returns the lease to the pool."""

    __slots__ = ("_pool", "_connection", "_closed")

    def __init__(self, pool: PostgresPool, connection) -> None:
        self._pool = pool
        self._connection = connection
        self._closed = False

    def __getattr__(self, name: str):
        return getattr(self._connection, name)

    def __enter__(self):
        if self._closed:
            raise RuntimeError("PostgreSQL connection lease is closed")
        return self

    @property
    def in_transaction(self) -> bool:
        return self._connection.info.transaction_status is not TransactionStatus.IDLE

    def __exit__(self, exc_type, exc, traceback) -> bool:
        if exc_type is None:
            self._connection.commit()
        else:
            self._connection.rollback()
        return False

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            if self._connection.info.transaction_status is not TransactionStatus.IDLE:
                self._connection.rollback()
        finally:
            self._pool.raw_pool.putconn(self._connection)


_runtime_pool: PostgresPool | None = None
_runtime_pool_lock = RLock()
def _open_runtime_pool() -> PostgresPool:
    global _runtime_pool
    with _runtime_pool_lock:
        if _runtime_pool is not None and _runtime_pool.opened:
            return _runtime_pool
        pool = PostgresPool.from_env(
            application_name="ink-dream-memory-runtime",
            connection_kwargs={"row_factory": _postgres_row_factory},
        )
        pool.open()
        _runtime_pool = pool
        return pool


def close_db() -> None:
    """Close the process-wide PostgreSQL pool; safe to call repeatedly."""

    global _runtime_pool
    with _runtime_pool_lock:
        pool, _runtime_pool = _runtime_pool, None
    if pool is not None:
        pool.close()


def _default_memory_workspace_config() -> dict:
    """Return the default procedural Memory config for voice partition rows."""

    from memory_workspace_defaults import default_memory_workspace_config

    return default_memory_workspace_config()


def _default_memory_workspace_config_json() -> str:
    return json.dumps(_default_memory_workspace_config(), ensure_ascii=False)


def _memory_workspace_config_json(memory_workspace_config: Optional[dict]) -> str:
    """Serialize an explicit config or the default procedural config."""

    config = memory_workspace_config if memory_workspace_config else _default_memory_workspace_config()
    return json.dumps(config, ensure_ascii=False)


def _utcnow_sql() -> str:
    """Return a stable UTC timestamp string accepted by PostgreSQL."""

    return datetime.utcnow().replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S")


def _datetime_to_sql(value: datetime) -> str:
    """Serialize datetimes for PostgreSQL temporal parameters."""

    return value.replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S")


def _parse_sql_datetime(value: Optional[str]) -> Optional[datetime]:
    """Parse project temporal values returned by PostgreSQL or legacy imports."""

    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        try:
            return datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S")
        except Exception:
            return None


def parse_sql_datetime(value: Optional[str]) -> Optional[datetime]:
    """Parse project DATETIME strings for route/service callers."""

    return _parse_sql_datetime(value)


def get_db() -> _PooledConnectionLease:
    """Acquire a PostgreSQL connection; no SQLite/JSON/in-memory fallback."""

    pool = _open_runtime_pool()
    connection = pool.raw_pool.getconn(timeout=pool.config.timeout)
    return _PooledConnectionLease(pool, connection)

def init_db():
    """Open PostgreSQL and fail closed unless required capabilities exist.

    Runtime startup never creates, alters, seeds, or migrates schema.  Schema
    DDL ownership belongs to Admin/Drizzle. Frozen legacy migration receipts
    are historical audit data and are never accepted as runtime authority.
    """

    try:
        from schema.capabilities import (
            REQUIRED_RUNTIME_CAPABILITIES,
            inspect_schema_authority,
        )
    except ModuleNotFoundError:  # pragma: no cover - package import compatibility
        from backend.tests.legacy_schema.capabilities import (
            REQUIRED_RUNTIME_CAPABILITIES,
            inspect_schema_authority,
        )

    db = get_db()
    try:
        receipt = inspect_schema_authority(
            db,
            required_capabilities=REQUIRED_RUNTIME_CAPABILITIES,
        )
        db.rollback()
    except Exception:
        db.rollback()
        db.close()
        close_db()
        raise
    else:
        db.close()


# ========== User Management ==========

def create_user(
    email: str,
    password_hash: str,
    display_name: str = None,
    avatar_url: str = None,
    role: str = "user",
) -> int:
    """Create a user only when Admin-owned Free/default-model provisioning is complete."""
    db = get_db()
    try:
        normalized_email = email.strip().lower()
        cursor = db.execute(
            """
            INSERT INTO users (email, password_hash, display_name, avatar_url, role, updated_at)
            VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            RETURNING id
            """,
            (normalized_email, password_hash, display_name, avatar_url, role or "user")
        )
        user_id = int(cursor.fetchone()["id"])
        registration = db.execute(
            """
            SELECT subscription.id
            FROM platform_users AS platform_user
            JOIN subscriptions AS subscription
              ON subscription.platform_user_id = platform_user.id
             AND subscription.status = 'active'
            JOIN subscription_plan_versions AS version
              ON version.id = subscription.plan_version_id
             AND version.status = 'published'
            JOIN subscription_plans AS plan
              ON plan.id = version.plan_id
             AND plan.code = 'free'
             AND plan.status = 'active'
            JOIN subscription_plan_entitlements AS entitlement
              ON entitlement.plan_version_id = version.id
             AND entitlement.enabled = TRUE
             AND entitlement.is_default = TRUE
             AND entitlement.gateway_scopes @> ARRAY['messages:create']::text[]
            JOIN ai_models AS model
              ON model.id = entitlement.model_id
             AND model.enabled = TRUE
            JOIN subscription_usage_allowances AS allowance
              ON allowance.subscription_id = subscription.id
             AND allowance.period_number = subscription.current_period_number
             AND allowance.granted_tokens > 0
            JOIN subscription_events AS event
              ON event.subscription_id = subscription.id
             AND event.event_type = 'activated'
            WHERE platform_user.source = 'ink-dream'
              AND platform_user.external_user_id = %s
              AND platform_user.status = 'active'
            LIMIT 1
            """,
            (str(user_id),),
        ).fetchone()
        if registration is None:
            raise UserRegistrationUnavailable()
        db.commit()
        return user_id
    except UserRegistrationUnavailable:
        db.rollback()
        raise
    except PostgresIntegrityError as exc:
        db.rollback()
        constraint_name = getattr(getattr(exc, "diag", None), "constraint_name", None)
        if constraint_name in {"users_email_uidx", "users_email_unique"}:
            raise ValueError("Email already exists") from None
        raise UserRegistrationUnavailable() from None
    except PostgresError:
        db.rollback()
        raise UserRegistrationUnavailable() from None
    finally:
        db.close()

def get_user_by_email(email: str):
    """Get user by email. Returns dict or None."""
    db = get_db()
    try:
        normalized_email = email.strip().lower()
        row = db.execute(
            """
            SELECT id, email, password_hash, display_name, avatar_url, role, created_at, updated_at
            FROM users
            WHERE email = %s
            """,
            (normalized_email,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        db.close()

def get_user_by_id(user_id: int):
    """Get user by ID. Returns dict or None."""
    db = get_db()
    try:
        row = db.execute(
            """
            SELECT id, email, display_name, avatar_url, role, created_at, updated_at
            FROM users
            WHERE id = %s
            """,
            (user_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        db.close()


def get_user_by_oauth_account(provider: str, provider_sub: str) -> Optional[dict]:
    """Return the local user bound to an OAuth provider subject."""

    db = get_db()
    try:
        row = db.execute(
            """
            SELECT u.id, u.email, u.display_name, u.avatar_url, u.role, u.created_at, u.updated_at
            FROM oauth_accounts oa
            JOIN users u ON u.id = oa.user_id
            WHERE oa.provider = %s AND oa.provider_sub = %s
            LIMIT 1
            """,
            (provider, provider_sub),
        ).fetchone()
        return dict(row) if row else None
    finally:
        db.close()


def upsert_oauth_account(
    user_id: int,
    provider: str,
    provider_sub: str,
    email: str,
    access_token_encrypted: Optional[str] = None,
    refresh_token_encrypted: Optional[str] = None,
    id_token_encrypted: Optional[str] = None,
    expires_at: Optional[datetime] = None,
) -> None:
    """Create or update a user's OAuth account binding."""

    db = get_db()
    try:
        db.execute(
            """
            INSERT INTO oauth_accounts (
              user_id, provider, provider_sub, email,
              access_token_encrypted, refresh_token_encrypted, id_token_encrypted,
              expires_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT(provider, provider_sub) DO UPDATE SET
              user_id = excluded.user_id,
              email = excluded.email,
              access_token_encrypted = COALESCE(excluded.access_token_encrypted, oauth_accounts.access_token_encrypted),
              refresh_token_encrypted = COALESCE(excluded.refresh_token_encrypted, oauth_accounts.refresh_token_encrypted),
              id_token_encrypted = COALESCE(excluded.id_token_encrypted, oauth_accounts.id_token_encrypted),
              expires_at = COALESCE(excluded.expires_at, oauth_accounts.expires_at),
              updated_at = CURRENT_TIMESTAMP
            """,
            (
                user_id,
                provider,
                provider_sub,
                email.strip().lower(),
                access_token_encrypted,
                refresh_token_encrypted,
                id_token_encrypted,
                _datetime_to_sql(expires_at) if expires_at else None,
            ),
        )
        db.commit()
    finally:
        db.close()


def create_refresh_token(user_id: int, token_hash: str, expires_at: datetime) -> None:
    """Persist a hashed refresh token."""

    db = get_db()
    try:
        db.execute(
            """
            INSERT INTO refresh_tokens (user_id, token_hash, expires_at)
            VALUES (%s, %s, %s)
            """,
            (user_id, token_hash, _datetime_to_sql(expires_at)),
        )
        db.commit()
    finally:
        db.close()


def get_refresh_token(token_hash: str) -> Optional[dict]:
    """Return a non-revoked refresh token row if present."""

    db = get_db()
    try:
        row = db.execute(
            """
            SELECT id, user_id, token_hash, expires_at, revoked_at, created_at
            FROM refresh_tokens
            WHERE token_hash = %s AND revoked_at IS NULL
            LIMIT 1
            """,
            (token_hash,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        db.close()


def revoke_refresh_token(token_hash: str) -> bool:
    """Revoke a refresh token by hash."""

    db = get_db()
    try:
        cursor = db.execute(
            """
            UPDATE refresh_tokens
            SET revoked_at = CURRENT_TIMESTAMP
            WHERE token_hash = %s AND revoked_at IS NULL
            """,
            (token_hash,),
        )
        db.commit()
        return cursor.rowcount > 0
    finally:
        db.close()


def revoke_user_refresh_tokens(user_id: int) -> int:
    """Revoke all active refresh tokens for a user."""

    db = get_db()
    try:
        cursor = db.execute(
            """
            UPDATE refresh_tokens
            SET revoked_at = CURRENT_TIMESTAMP
            WHERE user_id = %s AND revoked_at IS NULL
            """,
            (user_id,),
        )
        db.commit()
        return cursor.rowcount
    finally:
        db.close()


def create_device_authorization(
    client_id: str,
    device_code_hash: str,
    user_code_hash: str,
    scope: str,
    interval_seconds: int,
    expires_at: datetime,
) -> int:
    """Create a pending OAuth Device Authorization row."""

    db = get_db()
    try:
        cursor = db.execute(
            """
            INSERT INTO device_authorizations (
              client_id, device_code_hash, user_code_hash, scope,
              status, interval_seconds, expires_at, updated_at
            )
            VALUES (%s, %s, %s, %s, 'pending', %s, %s, CURRENT_TIMESTAMP)
            RETURNING id
            """,
            (
                client_id,
                device_code_hash,
                user_code_hash,
                scope,
                interval_seconds,
                _datetime_to_sql(expires_at),
            ),
        )
        authorization_id = int(cursor.fetchone()["id"])
        db.commit()
        return authorization_id
    finally:
        db.close()


def get_device_authorization_by_device_code_hash(device_code_hash: str) -> Optional[dict]:
    """Return a device authorization by hashed device_code."""

    db = get_db()
    try:
        row = db.execute(
            """
            SELECT *
            FROM device_authorizations
            WHERE device_code_hash = %s
            LIMIT 1
            """,
            (device_code_hash,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        db.close()


def get_device_authorization_by_user_code_hash(user_code_hash: str) -> Optional[dict]:
    """Return a device authorization by hashed user_code."""

    db = get_db()
    try:
        row = db.execute(
            """
            SELECT *
            FROM device_authorizations
            WHERE user_code_hash = %s
            LIMIT 1
            """,
            (user_code_hash,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        db.close()


def update_device_authorization_status(
    authorization_id: int,
    status: str,
    user_id: Optional[int] = None,
) -> None:
    """Set a device authorization status and relevant transition timestamps."""

    timestamp_column = {
        "approved": "approved_at",
        "consumed": "consumed_at",
    }.get(status)
    assignments = ["status = %s", "updated_at = CURRENT_TIMESTAMP"]
    params: list[object] = [status]
    if user_id is not None:
        assignments.append("user_id = %s")
        params.append(user_id)
    if timestamp_column:
        assignments.append(f"{timestamp_column} = CURRENT_TIMESTAMP")
    params.append(authorization_id)

    db = get_db()
    try:
        db.execute(
            f"UPDATE device_authorizations SET {', '.join(assignments)} WHERE id = %s",
            tuple(params),
        )
        db.commit()
    finally:
        db.close()


def record_device_authorization_poll(authorization_id: int, interval_seconds: Optional[int] = None) -> None:
    """Record a token polling attempt and optional new interval."""

    db = get_db()
    try:
        if interval_seconds is None:
            db.execute(
                """
                UPDATE device_authorizations
                SET last_poll_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (authorization_id,),
            )
        else:
            db.execute(
                """
                UPDATE device_authorizations
                SET last_poll_at = CURRENT_TIMESTAMP,
                    interval_seconds = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (interval_seconds, authorization_id),
            )
        db.commit()
    finally:
        db.close()


def device_authorization_is_expired(authorization: dict) -> bool:
    """Return whether a device authorization has expired."""

    expires_at = _parse_sql_datetime(authorization.get("expires_at"))
    return bool(expires_at and expires_at <= datetime.utcnow())


def device_authorization_poll_too_fast(authorization: dict) -> bool:
    """Return whether the current poll violates the authorization interval."""

    last_poll_at = _parse_sql_datetime(authorization.get("last_poll_at"))
    if not last_poll_at:
        return False
    interval = int(authorization.get("interval_seconds") or 5)
    return datetime.utcnow() < last_poll_at + timedelta(seconds=interval)

# ========== Session Storage ==========

def _normalize_created_at(created_at: Optional[Union[str, datetime]]) -> Optional[str]:
    if created_at is None:
        return None
    if isinstance(created_at, datetime):
        return created_at.strftime("%Y-%m-%d %H:%M:%S")
    return str(created_at)


def _parse_labels(raw: Optional[str]) -> list:
    """Parse a JSON-encoded labels string into a Python list. Returns [] on error."""
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else []
    except Exception:
        return []


def _extract_session_text(editor_state_json: str) -> tuple[str, str]:
    """Return ``(first_line, full_text)`` from text cells in an editor state JSON."""
    try:
        state = json.loads(editor_state_json)
        text_cells = [
            c.get("content", "").strip()
            for c in state.get("cells", [])
            if c.get("type") == "text" and c.get("content", "").strip()
        ]
    except Exception:
        return "", ""

    full_text = "\n\n".join(text_cells).strip()
    first_line = full_text.split("\n")[0][:30] if full_text else ""
    return first_line, full_text


def _extract_chat_parts_text(parts_json: str) -> str:
    """Return searchable plain text from a persisted UIMessage parts JSON."""
    try:
        parts = json.loads(parts_json) if parts_json else []
    except Exception:
        return ""

    texts: list[str] = []
    for part in parts if isinstance(parts, list) else []:
        if not isinstance(part, dict):
            continue
        if part.get("type") == "text":
            text = str(part.get("text") or "").strip()
            if text:
                texts.append(text)
    return "\n".join(texts).strip()


def save_session(user_id: int, session_id: str, editor_state: dict, name: str = None,
                 created_at: Optional[Union[str, datetime]] = None,
                 labels: Optional[list] = None):
    """Save or update a user session."""
    db = get_db()
    try:
        created_at_value = _normalize_created_at(created_at)
        labels_json = json.dumps(labels, ensure_ascii=False) if labels is not None else None
        db.execute("""
        INSERT INTO user_sessions (id, user_id, name, editor_state_json, labels, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, COALESCE(%s, CURRENT_TIMESTAMP), CURRENT_TIMESTAMP)
        ON CONFLICT(id) DO UPDATE SET
          editor_state_json = excluded.editor_state_json,
          name = COALESCE(excluded.name, user_sessions.name),
          labels = COALESCE(excluded.labels, user_sessions.labels),
          updated_at = CURRENT_TIMESTAMP
        """, (session_id, user_id, name, json.dumps(editor_state), labels_json, created_at_value))
        db.commit()
    finally:
        db.close()

def get_session(user_id: int, session_id: str):
    """Get a specific session. Returns dict or None."""
    db = get_db()
    try:
        row = db.execute("""
        SELECT id, name, editor_state_json, labels, created_at, updated_at
        FROM user_sessions
        WHERE user_id = %s AND id = %s
        """, (user_id, session_id)).fetchone()

        if row:
            result = dict(row)
            result['editor_state'] = json.loads(result['editor_state_json'])
            del result['editor_state_json']
            try:
                result['labels'] = json.loads(result['labels']) if result.get('labels') else []
            except Exception:
                result['labels'] = []
            return result
        return None
    finally:
        db.close()

def get_sessions_batch(user_id: int, session_ids: list[str]) -> list[dict]:
    """Fetch multiple sessions in a single query (includes full editor_state)."""
    if not session_ids:
        return []

    db = get_db()
    try:
        placeholders = ",".join("%s" for _ in session_ids)
        query = f"""
        SELECT id, name, editor_state_json, labels, created_at, updated_at
        FROM user_sessions
        WHERE user_id = %s AND id IN ({placeholders})
        """
        rows = db.execute(query, (user_id, *session_ids)).fetchall()
        sessions = []
        for row in rows:
            try:
                state = json.loads(row["editor_state_json"])
            except Exception:
                state = {}
            try:
                labels = json.loads(row["labels"]) if row["labels"] else []
            except Exception:
                labels = []
            sessions.append(
                {
                    "id": row["id"],
                    "name": row["name"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "labels": labels,
                    "editor_state": state,
                }
            )
        return sessions
    finally:
        db.close()

def list_sessions(user_id: int):
    """List all sessions for a user with a lightweight preview."""
    db = get_db()
    try:
        rows = db.execute("""
        SELECT id, name, editor_state_json, labels, created_at, updated_at
        FROM user_sessions
        WHERE user_id = %s
        ORDER BY updated_at DESC
        """, (user_id,)).fetchall()

        results = []
        for row in rows:
            first_line, _full_text = _extract_session_text(row["editor_state_json"])

            results.append(
                {
                    "id": row["id"],
                    "name": row["name"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "labels": _parse_labels(row["labels"]),
                    "first_line": first_line,
                }
            )
        return results
    finally:
        db.close()

def list_sessions_in_range(
    user_id: int,
    start_date: Optional[str],
    end_date: Optional[str],
    include_text: bool = False,
):
    """
    List sessions within an optional date range (UTC timestamps stored in DB).
    Dates are strings YYYY-MM-DD and compared against created_at/updated_at dates.
    ``include_text=True`` adds full text-cell content for Agent-side fuzzy search.
    """
    db = get_db()
    try:
        rows = db.execute(f"""
        SELECT id, name, editor_state_json, labels, created_at, updated_at
        FROM user_sessions
        WHERE user_id = %s
          AND (CAST(%s AS date) IS NULL OR date(COALESCE(created_at, updated_at)) >= CAST(%s AS date))
          AND (CAST(%s AS date) IS NULL OR date(COALESCE(created_at, updated_at)) <= CAST(%s AS date))
        ORDER BY updated_at DESC
        """, (user_id, start_date, start_date, end_date, end_date)).fetchall()

        results = []
        for row in rows:
            first_line, full_text = _extract_session_text(row["editor_state_json"])

            item = {
                "id": row["id"],
                "name": row["name"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "labels": _parse_labels(row["labels"]),
                "first_line": first_line,
            }
            if include_text:
                item["text"] = full_text
            results.append(item)
        return results
    finally:
        db.close()

def get_all_sessions_with_text(user_id: int) -> list[dict]:
    """
    Get all sessions for a user with text extracted from text cells.
    Returns [{id, name, created_at, updated_at, text}]
    """
    db = get_db()
    try:
        rows = db.execute("""
        SELECT id, name, editor_state_json, created_at, updated_at
        FROM user_sessions
        WHERE user_id = %s
        ORDER BY updated_at DESC
        """, (user_id,)).fetchall()

        sessions = []
        for row in rows:
            try:
                state = json.loads(row['editor_state_json'])
                text = '\n\n'.join(
                    cell.get('content', '')
                    for cell in state.get('cells', [])
                    if cell.get('type') == 'text' and cell.get('content', '').strip()
                ).strip()
            except Exception:
                text = ''

            item = {
                'id': row['id'],
                'name': row['name'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at'],
                'text': text,
            }
            sessions.append(item)
        return sessions
    finally:
        db.close()

def delete_session(user_id: int, session_id: str):
    """Delete a session."""
    db = get_db()
    try:
        db.execute("DELETE FROM user_sessions WHERE user_id = %s AND id = %s", (user_id, session_id))
        db.commit()
    finally:
        db.close()

# ========== Timeline Auto-Generation Helpers ==========

def get_users_with_activity_on_date(target_date: str, timezone: str = 'Asia/Shanghai') -> list[int]:
    """
    Get user IDs who updated sessions on target_date (local timezone).

    Args:
        target_date: Date string in YYYY-MM-DD format (local timezone)
        timezone: Timezone name (default: Asia/Shanghai for Beijing)

    Returns:
        List of user_ids with non-empty sessions on that date

    @@@ Timezone handling - SQLite stores UTC, we convert to local timezone for date matching
    """
    from datetime import datetime
    from zoneinfo import ZoneInfo

    db = get_db()
    try:
        # @@@ Convert target_date (local) to UTC range for database query
        # Example: 2025-01-17 in Beijing = 2025-01-16 16:00 UTC to 2025-01-17 16:00 UTC
        tz = ZoneInfo(timezone)
        local_date = datetime.strptime(target_date, '%Y-%m-%d').replace(tzinfo=tz)

        # Get start and end of day in UTC
        start_of_day_local = local_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day_local = local_date.replace(hour=23, minute=59, second=59, microsecond=999999)

        start_utc = start_of_day_local.astimezone(ZoneInfo('UTC'))
        end_utc = end_of_day_local.astimezone(ZoneInfo('UTC'))

        # Query sessions updated in this UTC range
        rows = db.execute("""
            SELECT DISTINCT user_id, editor_state_json
            FROM user_sessions
            WHERE updated_at >= %s AND updated_at <= %s
        """, (start_utc.isoformat(), end_utc.isoformat())).fetchall()

        # Filter users with non-empty content
        user_ids = []
        for row in rows:
            try:
                state = json.loads(row['editor_state_json'])
                # Check if has any text cells with content
                has_content = any(
                    cell.get('type') == 'text' and cell.get('content', '').strip()
                    for cell in state.get('cells', [])
                )
                if has_content and row['user_id'] not in user_ids:
                    user_ids.append(row['user_id'])
            except (json.JSONDecodeError, KeyError):
                continue

        return user_ids
    finally:
        db.close()

def extract_text_from_sessions_on_date(user_id: int, target_date: str, timezone: str = 'Asia/Shanghai') -> str:
    """
    Extract all text from user's sessions updated on target_date (local timezone).

    Args:
        user_id: User ID
        target_date: Date string in YYYY-MM-DD format (local timezone)
        timezone: Timezone name (default: Asia/Shanghai for Beijing)

    Returns:
        Concatenated text from all text cells, joined with double newlines

    @@@ Replicates frontend's getAllNotesFromSessions() logic but date-filtered
    @@@ Timezone handling - SQLite stores UTC, we convert to local timezone for date matching
    """
    from datetime import datetime
    from zoneinfo import ZoneInfo

    db = get_db()
    try:
        # @@@ Convert target_date (local) to UTC range for database query
        tz = ZoneInfo(timezone)
        local_date = datetime.strptime(target_date, '%Y-%m-%d').replace(tzinfo=tz)

        start_of_day_local = local_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day_local = local_date.replace(hour=23, minute=59, second=59, microsecond=999999)

        start_utc = start_of_day_local.astimezone(ZoneInfo('UTC'))
        end_utc = end_of_day_local.astimezone(ZoneInfo('UTC'))

        # Get sessions updated in this UTC range
        rows = db.execute("""
            SELECT editor_state_json
            FROM user_sessions
            WHERE user_id = %s
              AND updated_at >= %s
              AND updated_at <= %s
            ORDER BY updated_at DESC
        """, (user_id, start_utc.isoformat(), end_utc.isoformat())).fetchall()

        # Extract text from each session
        all_text = []
        for row in rows:
            try:
                state = json.loads(row['editor_state_json'])
                # @@@ Same logic as frontend: filter text cells, extract content
                text = '\n\n'.join(
                    cell['content']
                    for cell in state.get('cells', [])
                    if cell.get('type') == 'text' and cell.get('content', '').strip()
                )
                if text.strip():
                    all_text.append(text)
            except (json.JSONDecodeError, KeyError):
                continue

        return '\n\n'.join(all_text)
    finally:
        db.close()

# ========== Historical Daily Pictures ==========

def get_daily_pictures(user_id: int, limit: int = 30):
    """Get recent daily pictures (returns ONLY thumbnails for fast timeline loading)."""
    db = get_db()
    try:
        # @@@ Use COALESCE to return thumbnail, fallback to full image only if needed
        # This prevents loading full images when thumbnails exist
        rows = db.execute("""
        SELECT date, COALESCE(thumbnail_base64, image_base64) as base64, prompt, created_at
        FROM daily_pictures
        WHERE user_id = %s
        ORDER BY date DESC
        LIMIT %s
        """, (user_id, limit)).fetchall()
        return [{
            'date': row['date'],
            'base64': row['base64'],
            'prompt': row['prompt'] or '',
            'created_at': row['created_at']
        } for row in rows]
    finally:
        db.close()

def get_daily_picture_full(user_id: int, date: str):
    """Get full resolution image for a specific date (on-demand loading)."""
    db = get_db()
    try:
        row = db.execute("""
        SELECT image_base64
        FROM daily_pictures
        WHERE user_id = %s AND date = %s
        ORDER BY created_at DESC
        LIMIT 1
        """, (user_id, date)).fetchone()

        if row:
            return row['image_base64']
        return None
    finally:
        db.close()


def get_friend_picture_full(user_id: int, friend_id: int, date: str):
    """Retired: use the current-actor Admin social DTO consumer."""
    _retired_social_data_access()

# ========== User Preferences ==========

def save_preferences(user_id: int, voice_configs: dict = None, meta_prompt: str = None,
                    state_config: dict = None, selected_state: str = None, timezone: str = None):
    """Atomically merge user preferences without a first-login insert race."""
    db = get_db()
    try:
        db.execute("""
            INSERT INTO user_preferences (user_id, voice_configs_json, meta_prompt, state_config_json, selected_state, timezone)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
                voice_configs_json = COALESCE(EXCLUDED.voice_configs_json, user_preferences.voice_configs_json),
                meta_prompt = COALESCE(EXCLUDED.meta_prompt, user_preferences.meta_prompt),
                state_config_json = COALESCE(EXCLUDED.state_config_json, user_preferences.state_config_json),
                selected_state = COALESCE(EXCLUDED.selected_state, user_preferences.selected_state),
                timezone = COALESCE(EXCLUDED.timezone, user_preferences.timezone),
                updated_at = CURRENT_TIMESTAMP
            """, (
                user_id,
                json.dumps(voice_configs) if voice_configs is not None else None,
                meta_prompt,
                json.dumps(state_config) if state_config is not None else None,
                selected_state,
                timezone,
            ))

        db.commit()
    finally:
        db.close()

def get_preferences(user_id: int):
    """Get user preferences. Returns dict or None."""
    db = get_db()
    try:
        row = db.execute("""
        SELECT voice_configs_json, meta_prompt, state_config_json, selected_state,
               timezone, first_login_completed, updated_at
        FROM user_preferences
        WHERE user_id = %s
        """, (user_id,)).fetchone()

        if row:
            result = dict(row)
            result['voice_configs'] = json.loads(result['voice_configs_json']) if result['voice_configs_json'] else None
            result['state_config'] = json.loads(result['state_config_json']) if result['state_config_json'] else None
            del result['voice_configs_json']
            del result['state_config_json']
            return result
        return None
    finally:
        db.close()

def get_system_config(user_id: int) -> dict:
    """Retired compatibility symbol; SystemConfig reads require Admin authority."""

    del user_id
    raise RuntimeError("SystemConfig persistence is owned by Admin")


def save_system_config(user_id: int, patch: dict) -> None:
    """Retired compatibility symbol; SystemConfig writes require Admin authority."""

    del user_id, patch
    raise RuntimeError("SystemConfig persistence is owned by Admin")


def set_first_login_completed(user_id: int):
    """Mark user's first login as completed."""
    db = get_db()
    try:
        # Check if preferences exist
        existing = db.execute("SELECT user_id FROM user_preferences WHERE user_id = %s", (user_id,)).fetchone()

        if existing:
            # Update existing
            db.execute("""
            UPDATE user_preferences
            SET first_login_completed = 1, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s
            """, (user_id,))
        else:
            # Insert new
            db.execute("""
            INSERT INTO user_preferences (user_id, first_login_completed)
            VALUES (%s, 1)
            """, (user_id,))

        db.commit()
    finally:
        db.close()

# ========== Analysis Reports ==========

def save_analysis_report(user_id: int, report_type: str, report_data: dict, all_notes_text: str = None):
    """Save an analysis report."""
    db = get_db()
    try:
        db.execute("""
        INSERT INTO analysis_reports (user_id, report_type, report_data_json, all_notes_text)
        VALUES (%s, %s, %s, %s)
        """, (user_id, report_type, json.dumps(report_data), all_notes_text))
        db.commit()
    finally:
        db.close()

def get_analysis_reports(user_id: int, limit: int = 10):
    """Get recent analysis reports."""
    db = get_db()
    try:
        rows = db.execute("""
        SELECT id, report_type, report_data_json, created_at
        FROM analysis_reports
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT %s
        """, (user_id, limit)).fetchall()

        results = []
        for row in rows:
            result = dict(row)
            result['report_data'] = json.loads(result['report_data_json'])
            del result['report_data_json']
            results.append(result)
        return results
    finally:
        db.close()

# ========== Bulk Import (for localStorage migration) ==========

def import_user_data(user_id: int, sessions: list, pictures: list, preferences: dict, reports: list = None):
    """
    Bulk import user data from localStorage migration.

    Args:
        user_id: User ID
        sessions: List of {id, name, editor_state}
        pictures: List of {date, image_base64, prompt}
        preferences: {voice_configs, meta_prompt, state_config, selected_state}
        reports: Optional list of {type, data, allNotes, timestamp}
    """
    db = get_db()
    try:
        # Import sessions
        for session in sessions:
            db.execute("""
            INSERT INTO user_sessions (id, user_id, name, editor_state_json)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
              user_id = excluded.user_id,
              name = excluded.name,
              editor_state_json = excluded.editor_state_json,
              updated_at = CURRENT_TIMESTAMP
            """, (session['id'], user_id, session.get('name'), json.dumps(session['editor_state'])))

        # Import pictures
        for picture in pictures:
            db.execute("""
            INSERT INTO daily_pictures (user_id, date, image_base64, prompt)
            VALUES (%s, %s, %s, %s)
            """, (user_id, picture['date'], picture['image_base64'], picture.get('prompt')))

        # Import preferences
        if preferences:
            db.execute("""
            INSERT INTO user_preferences
            (user_id, voice_configs_json, meta_prompt, state_config_json, selected_state)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
              voice_configs_json = excluded.voice_configs_json,
              meta_prompt = excluded.meta_prompt,
              state_config_json = excluded.state_config_json,
              selected_state = excluded.selected_state,
              updated_at = CURRENT_TIMESTAMP
            """, (user_id,
                  json.dumps(preferences.get('voice_configs')) if preferences.get('voice_configs') else None,
                  preferences.get('meta_prompt'),
                  json.dumps(preferences.get('state_config')) if preferences.get('state_config') else None,
                  preferences.get('selected_state')))

        # Import analysis reports
        if reports:
            for report in reports:
                db.execute("""
                INSERT INTO analysis_reports (user_id, report_type, report_data_json, all_notes_text)
                VALUES (%s, %s, %s, %s)
                """, (user_id, report.get('type', 'unknown'), json.dumps(report.get('data', {})), report.get('allNotes')))

        db.commit()
        print(f"✅ Imported {len(sessions)} sessions, {len(pictures)} pictures, {len(reports or [])} reports for user {user_id}")
    finally:
        db.close()

# ========== Friend System ==========

def _retired_social_data_access() -> None:
    from services.admin_data.errors import AdminDataError
    raise AdminDataError("ADMIN_DATA_ACCESS_RETIRED", 503)


def generate_invite_code(user_id: int) -> dict:
    """Retired: use the current-actor Admin social DTO consumer."""
    _retired_social_data_access()

def use_invite_code(code: str, requesting_user_id: int) -> dict:
    """Retired: use the current-actor Admin social DTO consumer."""
    _retired_social_data_access()

def get_friend_requests(user_id: int) -> list:
    """Retired: use the current-actor Admin social DTO consumer."""
    _retired_social_data_access()

def accept_friend_request(request_id: int, user_id: int) -> dict:
    """Retired: use the current-actor Admin social DTO consumer."""
    _retired_social_data_access()

def reject_friend_request(request_id: int, user_id: int) -> dict:
    """Retired: use the current-actor Admin social DTO consumer."""
    _retired_social_data_access()

def get_friends(user_id: int) -> list:
    """Retired: use the current-actor Admin social DTO consumer."""
    _retired_social_data_access()

def remove_friend(user_id: int, friend_id: int) -> dict:
    """Retired: use the current-actor Admin social DTO consumer."""
    _retired_social_data_access()

def get_friend_timeline(user_id: int, friend_id: int, limit: int = 30) -> list:
    """Retired: use the current-actor Admin social DTO consumer."""
    _retired_social_data_access()

def get_daily_pictures_range(user_id: int, start_date: Optional[str], end_date: Optional[str], limit: int = 30) -> list[dict]:
    """
    Get daily pictures within a date range (thumbnails preferred). Limits results.
    """
    db = get_db()
    try:
        rows = db.execute("""
        SELECT date, COALESCE(thumbnail_base64, image_base64) as base64, prompt, created_at
        FROM daily_pictures
        WHERE user_id = %s
          AND (CAST(%s AS date) IS NULL OR date(date) >= CAST(%s AS date))
          AND (CAST(%s AS date) IS NULL OR date(date) <= CAST(%s AS date))
        ORDER BY date DESC
        LIMIT %s
        """, (user_id, start_date, start_date, end_date, end_date, limit)).fetchall()

        return [{
            "date": row['date'],
            "base64": row['base64'],
            "prompt": row['prompt'],
            "created_at": row['created_at']
        } for row in rows]
    finally:
        db.close()


# ========== Claude Agent Chat Thread CRUD ==========

def create_chat_thread(
    user_id: int,
    deck_id: Optional[str] = None,
    voice_id: Optional[str] = None,
    title: Optional[str] = None,
) -> str:
    """Create a new chat thread for the user. Returns the thread_id (UUID)."""
    import uuid
    thread_id = str(uuid.uuid4())
    db = get_db()
    try:
        db.execute(
            "INSERT INTO chat_thread (id, user_id, title, deck_id, voice_id) VALUES (%s, %s, %s, %s, %s)",
            (thread_id, user_id, title, deck_id, voice_id),
        )
        db.commit()
        return thread_id
    finally:
        db.close()


def get_chat_thread(thread_id: str, user_id: int) -> Optional[dict]:
    """Return the chat_thread row if it belongs to user_id, else None."""
    db = get_db()
    try:
        row = db.execute(
            "SELECT id, user_id, title, deck_id, voice_id, claude_session_id, agent_contract_version, created_at, updated_at"
            " FROM chat_thread WHERE id = %s AND user_id = %s",
            (thread_id, user_id),
        ).fetchone()
        return dict(row) if row else None
    finally:
        db.close()


def bind_chat_thread_deck(thread_id: str, user_id: int, deck_id: str) -> bool:
    """Bind a Deck once; an existing conversation cannot switch provenance."""
    db = get_db()
    try:
        cursor = db.execute(
            """
            UPDATE chat_thread
            SET deck_id = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND user_id = %s AND deck_id IS NULL
            """,
            (deck_id, thread_id, user_id),
        )
        db.commit()
        if cursor.rowcount == 1:
            return True
        row = db.execute(
            "SELECT deck_id FROM chat_thread WHERE id = %s AND user_id = %s",
            (thread_id, user_id),
        ).fetchone()
        return bool(row and row["deck_id"] == deck_id)
    finally:
        db.close()


def select_chat_thread_voice(
    thread_id: str,
    user_id: int,
    deck_id: str,
    voice_id: str,
    expected_voice_id: Optional[str],
) -> bool:
    """Select the current Agent with CAS while preserving the Thread Deck."""
    db = get_db()
    try:
        cursor = db.execute(
            """
            UPDATE chat_thread
            SET voice_id = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
              AND user_id = %s
              AND deck_id = %s
              AND voice_id IS NOT DISTINCT FROM %s
            """,
            (voice_id, thread_id, user_id, deck_id, expected_voice_id),
        )
        db.commit()
        return cursor.rowcount == 1
    finally:
        db.close()


def list_chat_threads(
    user_id: int,
    limit: Optional[int] = None,
    offset: int = 0,
    deck_id: Optional[str] = None,
) -> list[dict]:
    """List owned chat threads, optionally constrained to one Deck and paged."""
    db = get_db()
    try:
        where = "WHERE user_id = %s"
        parameters: list[Any] = [user_id]
        if deck_id is not None:
            where += " AND deck_id = %s"
            parameters.append(deck_id)
        if limit is not None:
            parameters.extend((limit, max(0, offset)))
            rows = db.execute(
                f"""
                SELECT id, title, deck_id, voice_id, created_at, updated_at
                FROM chat_thread
                {where}
                ORDER BY updated_at DESC
                LIMIT %s OFFSET %s
                """,
                tuple(parameters),
            ).fetchall()
        else:
            rows = db.execute(
                f"SELECT id, title, deck_id, voice_id, created_at, updated_at FROM chat_thread {where} ORDER BY updated_at DESC",
                tuple(parameters),
            ).fetchall()
        return [dict(row) for row in rows]
    finally:
        db.close()


def list_chat_threads_for_search(
    user_id: int,
    deck_id: Optional[str] = None,
) -> list[dict]:
    """List owned chat search candidates, optionally constrained to one Deck."""
    db = get_db()
    try:
        deck_filter = " AND t.deck_id = %s" if deck_id is not None else ""
        parameters: tuple[object, ...] = (user_id, deck_id) if deck_id is not None else (user_id,)
        rows = db.execute(
            f"""
            SELECT
              t.id,
              t.title,
              t.deck_id,
              t.voice_id,
              t.created_at,
              t.updated_at,
              m.parts AS message_parts
            FROM chat_thread t
            LEFT JOIN chat_message m ON m.thread_id = t.id
            WHERE t.user_id = %s{deck_filter}
            ORDER BY t.updated_at DESC, m.created_at ASC
            """,
            parameters,
        ).fetchall()

        by_thread: dict[str, dict] = {}
        message_texts: dict[str, list[str]] = {}
        for row in rows:
            thread_id = row["id"]
            if thread_id not in by_thread:
                by_thread[thread_id] = {
                    "id": row["id"],
                    "title": row["title"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "deck_id": row["deck_id"],
                    "voice_id": row["voice_id"],
                    "messages_text": "",
                }
                message_texts[thread_id] = []

            message_text = _extract_chat_parts_text(row["message_parts"] or "")
            if message_text:
                message_texts[thread_id].append(message_text)

        for thread_id, item in by_thread.items():
            item["messages_text"] = "\n\n".join(message_texts.get(thread_id, []))

        return list(by_thread.values())
    finally:
        db.close()


def delete_chat_thread(thread_id: str, user_id: int) -> bool:
    """Delete a chat thread (cascades to messages). Returns True if deleted."""
    db = get_db()
    try:
        cursor = db.execute(
            "DELETE FROM chat_thread WHERE id = %s AND user_id = %s",
            (thread_id, user_id),
        )
        db.commit()
        return cursor.rowcount > 0
    finally:
        db.close()


def update_chat_thread_title(thread_id: str, title: str) -> None:
    """Set or update the title of a chat thread."""
    db = get_db()
    try:
        db.execute(
            "UPDATE chat_thread SET title = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
            (title, thread_id),
        )
        db.commit()
    finally:
        db.close()


def update_chat_thread_claude_session(
    thread_id: str,
    claude_session_id: str,
    agent_contract_version: str,
) -> None:
    """Persist the Claude SDK session ID and contract version on a chat thread.

    Called by the agent service after each successful turn so subsequent turns
    can resume the correct transcript file.
    """
    db = get_db()
    try:
        db.execute(
            "UPDATE chat_thread"
            " SET claude_session_id = %s, agent_contract_version = %s, updated_at = CURRENT_TIMESTAMP"
            " WHERE id = %s",
            (claude_session_id, agent_contract_version, thread_id),
        )
        db.commit()
    finally:
        db.close()


def _touch_chat_thread(db, thread_id: str) -> None:
    """Bump the updated_at timestamp of a thread (same connection, no commit)."""
    db.execute(
        "UPDATE chat_thread SET updated_at = CURRENT_TIMESTAMP WHERE id = %s",
        (thread_id,),
    )


def _chat_message_json_value(
    value: object,
    *,
    field: str,
    expected_type: type,
    nullable: bool = False,
) -> object:
    """Decode and type-check one Chat JSON field for semantic CAS comparison."""

    decoded = value
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field} must be valid JSON") from exc
    if nullable and decoded is None:
        return None
    if not isinstance(decoded, expected_type):
        raise ValueError(f"{field} has an invalid JSON shape")
    return decoded


def _canonical_chat_message_json(value: object) -> str:
    """Canonicalize JSON so key order/whitespace never changes identity."""

    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def save_chat_message(
    thread_id: str,
    role: str,
    parts: list,
    message_id: Optional[str] = None,
    metadata: Optional[dict] = None,
    history_final_text: Optional[str] = None,
    history_process_available: bool = False,
    history_projection_version: Optional[int] = None,
    # Deprecated aliases kept for one-release backward compatibility.
    parts_json: Optional[str] = None,
    metadata_json: Optional[str] = None,
) -> str:
    """Insert one immutable chat-message identity or accept an exact replay.

    Fully aligned with better-chatbot ChatMessageTable — no ``content`` column.
    Text lives inside ``parts`` as ``{type: "text", text: "..."}`` entries.

      - ``parts``    list[dict] — UIMessage['parts'] array; required; serialized internally.
      - ``metadata`` dict       — ChatMetadata (usage / chatModel / toolCount); nullable.
      - ``message_id`` — AI-SDK message.id from the frontend; auto-generated if omitted.

    A supplied id is permanently bound to its thread, role, parts and metadata.
    JSON object key order and whitespace are ignored for exact replay; any
    semantic difference raises :class:`ChatMessageIdentityConflict`.  This
    function never reparents or overwrites an existing row.
    """
    import uuid
    if not message_id:
        message_id = str(uuid.uuid4())

    # Resolve parts: prefer list param, fall back to deprecated string param.
    if parts_json is not None and not parts:
        parts_value = _chat_message_json_value(
            parts_json,
            field="parts",
            expected_type=list,
        )
    else:
        parts_value = _chat_message_json_value(
            parts,
            field="parts",
            expected_type=list,
        )
    parts_str = _canonical_chat_message_json(parts_value)

    # Resolve metadata: prefer dict param, fall back to deprecated string param.
    if metadata is not None:
        metadata_value = _chat_message_json_value(
            metadata,
            field="metadata",
            expected_type=dict,
            nullable=True,
        )
    elif metadata_json is not None:
        metadata_value = _chat_message_json_value(
            metadata_json,
            field="metadata",
            expected_type=dict,
            nullable=True,
        )
    else:
        metadata_value = None
    metadata_str: Optional[str] = (
        _canonical_chat_message_json(metadata_value)
        if metadata_value is not None
        else None
    )
    _validate_chat_history_final_projection(
        role=role,
        parts=parts_value,
        metadata=metadata_value,
        history_final_text=history_final_text,
        history_process_available=history_process_available,
        history_projection_version=history_projection_version,
    )

    db = get_db()
    try:
        inserted = db.execute(
            """
            INSERT INTO chat_message (
                id, thread_id, role, parts, metadata,
                history_final_text, history_process_available,
                history_projection_version
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            RETURNING id
            """,
            (
                message_id,
                thread_id,
                role,
                parts_str,
                metadata_str,
                history_final_text,
                history_process_available,
                history_projection_version,
            ),
        ).fetchone()
        if inserted is not None:
            _touch_chat_thread(db, thread_id)
            db.commit()
            return message_id

        existing = db.execute(
            "SELECT thread_id, role, parts, metadata "
            "FROM chat_message WHERE id = %s",
            (message_id,),
        ).fetchone()
        if existing is None:
            raise ChatMessageIdentityConflict(message_id)
        try:
            existing_parts = _chat_message_json_value(
                existing["parts"],
                field="stored parts",
                expected_type=list,
            )
            existing_metadata = _chat_message_json_value(
                existing["metadata"],
                field="stored metadata",
                expected_type=dict,
                nullable=True,
            )
            existing_thread_id = existing["thread_id"]
            existing_role = existing["role"]
            existing_parts_str = _canonical_chat_message_json(existing_parts)
            existing_metadata_str = (
                _canonical_chat_message_json(existing_metadata)
                if existing_metadata is not None
                else None
            )
        except (KeyError, TypeError, ValueError):
            raise ChatMessageIdentityConflict(message_id) from None
        if not (
            existing_thread_id == thread_id
            and existing_role == role
            and existing_parts_str == parts_str
            and existing_metadata_str == metadata_str
        ):
            raise ChatMessageIdentityConflict(message_id)
        # Exact replay is a read-only success: do not reorder the thread.
        db.commit()
        return message_id
    finally:
        db.close()


def _decode_chat_message_rows(rows: list[Mapping[str, object]]) -> list[dict]:
    """Decode Chat JSON or the row-level final projection, fail closed."""

    results: list[dict] = []
    for row in rows:
        message = dict(row)
        # Keep SQL NULL (a valid "no metadata" value) distinguishable
        # from a corrupt stored JSON envelope.  The HTTP projection uses
        # this internal flag to withhold message parts fail-closed; the
        # flag itself is never part of the client response allowlist.
        message["metadata_decode_error"] = False
        projected_final = message.get("history_final_text")
        projection_version = message.get("history_projection_version")
        process_available = message.get("history_process_available")
        valid_projection = (
            message.get("role") == "assistant"
            and isinstance(projection_version, int)
            and not isinstance(projection_version, bool)
            and projection_version == 1
            and isinstance(projected_final, str)
            and bool(projected_final.strip())
            and isinstance(process_available, bool)
        )
        if valid_projection:
            message["parts"] = [{"type": "text", "text": projected_final}]
        else:
            try:
                message["parts"] = (
                    json.loads(message["parts"]) if message["parts"] else []
                )
            except Exception:
                message["parts"] = []
        if message.get("metadata"):
            try:
                message["metadata"] = json.loads(message["metadata"])
                if not isinstance(message["metadata"], dict):
                    # A stored JSON scalar/array (including literal null)
                    # is not the SQL NULL "no metadata" state.  Preserve
                    # that distinction so the client projection fails
                    # closed even when JSON decoding itself succeeds.
                    message["metadata_decode_error"] = True
            except Exception:
                message["metadata"] = None
                message["metadata_decode_error"] = True
        results.append(message)
    return results


def list_chat_messages(thread_id: str) -> list[dict]:
    """Return all messages for a thread in chronological order.

    Fully aligned with better-chatbot ChatRepository.selectMessagesByThreadId:
    returns ``parts`` as a parsed Python list and ``metadata`` as a parsed dict
    (or None) so callers receive UIMessage-compatible objects directly.
    """
    db = get_db()
    try:
        rows = db.execute(
            "SELECT id, role, parts, metadata, created_at "
            "FROM chat_message WHERE thread_id = %s "
            "ORDER BY created_at ASC NULLS FIRST, id ASC",
            (thread_id,),
        ).fetchall()
        return _decode_chat_message_rows(rows)
    finally:
        db.close()


def list_chat_message_page(
    thread_id: str,
    limit: int,
    *,
    before_created_at: datetime | None = None,
    before_id: str | None = None,
    before_created_at_is_null: bool = False,
) -> dict[str, object]:
    """Return one newest-to-older keyset page, exposed in chronological order.

    ``before_id is None`` selects the newest page.  A cursor whose timestamp is
    SQL NULL sets ``before_created_at_is_null`` so NULL peers continue by id.
    The newest page's latest identity is taken from the same row snapshot, not
    from a second query that could drift during status stabilization.
    """

    if limit < 1:
        raise ValueError("limit must be positive")
    if before_id is None and (before_created_at is not None or before_created_at_is_null):
        raise ValueError("cursor boundary requires before_id")
    if before_id is not None and before_created_at is None and not before_created_at_is_null:
        raise ValueError("cursor boundary timestamp kind is required")
    if before_created_at is not None and before_created_at_is_null:
        raise ValueError("cursor boundary timestamp is ambiguous")

    db = get_db()
    try:
        select_page = (
            "SELECT id, role, "
            "CASE WHEN role = 'assistant' "
            "AND history_projection_version = 1 "
            "AND history_final_text IS NOT NULL "
            "AND btrim(history_final_text) <> '' "
            "THEN NULL ELSE parts END AS parts, "
            "metadata, created_at, history_final_text, "
            "history_process_available, history_projection_version "
            "FROM chat_message WHERE "
        )
        order_page = (
            " ORDER BY created_at DESC NULLS LAST, id DESC NULLS LAST "
            "LIMIT %s"
        )
        page_size = limit + 1
        if before_id is None:
            rows = db.execute(
                select_page + "thread_id = %s" + order_page,
                (thread_id, page_size),
            ).fetchall()
        elif before_created_at_is_null:
            rows = db.execute(
                select_page
                + "thread_id = %s AND created_at IS NULL AND id < %s"
                + order_page,
                (thread_id, before_id, page_size),
            ).fetchall()
        else:
            # A row-value boundary lets PostgreSQL start the exact composite
            # index scan at the cursor.  Mixing legacy NULL timestamps into
            # the same OR predicate would demote the boundary to a filter and
            # rescan all newer rows, so NULL-tail rows fill only the remainder.
            nonnull_rows = db.execute(
                select_page
                + "thread_id = %s AND (created_at, id) < (%s, %s)"
                + order_page,
                (thread_id, before_created_at, before_id, page_size),
            ).fetchall()
            rows = list(nonnull_rows)
            remaining = page_size - len(rows)
            if remaining > 0:
                null_rows = db.execute(
                    select_page + "thread_id = %s AND created_at IS NULL" + order_page,
                    (thread_id, remaining),
                ).fetchall()
                rows.extend(null_rows)
        latest_message_id = (
            str(rows[0]["id"])
            if before_id is None and rows
            else None
        )
        has_more = len(rows) > limit
        page_rows = rows[:limit]
        messages = _decode_chat_message_rows(list(reversed(page_rows)))
        return {
            "messages": messages,
            "has_more": has_more,
            "latest_message_id": latest_message_id,
        }
    finally:
        db.close()


def get_chat_message_process_detail(
    thread_id: str,
    message_id: str,
) -> Optional[dict]:
    """Return one projected assistant's canonical process message by exact id."""

    db = get_db()
    try:
        row = db.execute(
            "SELECT id, role, parts, metadata, created_at "
            "FROM chat_message "
            "WHERE thread_id = %s AND id = %s AND role = 'assistant' "
            "AND history_projection_version = 1 "
            "AND history_process_available = true",
            (thread_id, message_id),
        ).fetchone()
        if row is None:
            return None
        messages = _decode_chat_message_rows([row])
        return messages[0] if messages else None
    finally:
        db.close()


def get_latest_chat_message_id(thread_id: str) -> str | None:
    """Read only the current stable latest Chat message identity."""

    db = get_db()
    try:
        row = db.execute(
            "SELECT id FROM chat_message WHERE thread_id = %s "
            "ORDER BY created_at DESC NULLS LAST, id DESC NULLS LAST LIMIT 1",
            (thread_id,),
        ).fetchone()
        return str(row["id"]) if row is not None else None
    finally:
        db.close()


def get_voice_memory_config_by_thread(thread_id: str) -> Optional[dict]:
    """Return the parsed memory_workspace_config for the voice associated with *thread_id*.

    Voices are linked to threads via the ``voices.thread_id`` column that is
    set when ``ensureVoiceThread`` creates or reuses a thread for a voice.

    Returns:
        dict  — parsed JSON config, self-healed to the default procedural config
                when the row exists but config is empty/invalid.
        None  — when no matching voice is found.
    """
    if not thread_id:
        return None
    db = get_db()
    try:
        row = db.execute(
            "SELECT id, memory_workspace_config FROM voices WHERE thread_id = %s LIMIT 1",
            (thread_id,),
        ).fetchone()
        if row is None:
            return None
        parsed = _parse_voice_row(dict(row))
        config = parsed.get("memory_workspace_config")
        if isinstance(config, dict):
            return config

        config = _default_memory_workspace_config()
        db.execute(
            "UPDATE voices SET memory_workspace_config = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
            (json.dumps(config, ensure_ascii=False), parsed["id"]),
        )
        db.commit()
        return config
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Reflections section config helpers
# ---------------------------------------------------------------------------


def get_reflections_section_config(user_id: int, section: str) -> Optional[dict]:
    """Return the user's custom prompt_files for *section*, or None if not set.

    Returns the parsed ``prompt_files`` dict on success, or ``None`` when the
    user has no custom config for this section (caller should fall back to the
    static default in ``reflections_config.py``).
    """
    db = get_db()
    try:
        row = db.execute(
            "SELECT prompt_files FROM reflections_section_configs "
            "WHERE user_id = %s AND section = %s LIMIT 1",
            (user_id, section),
        ).fetchone()
        if row is None:
            return None
        try:
            parsed = json.loads(row["prompt_files"] or "{}")
            return parsed if isinstance(parsed, dict) else None
        except (json.JSONDecodeError, TypeError):
            return None
    finally:
        db.close()


def save_reflections_section_config(user_id: int, section: str, prompt_files: dict) -> None:
    """Reject the retired Dream-side Reflections configuration writer."""

    del user_id, section, prompt_files
    raise RuntimeError("Reflections section configuration persistence is owned by Admin")


def delete_reflections_section_config(user_id: int, section: str) -> bool:
    """Reject the retired Dream-side Reflections configuration deleter."""

    del user_id, section
    raise RuntimeError("Reflections section configuration persistence is owned by Admin")


# ---------------------------------------------------------------------------
# Reflections-agent async task persistence
# ---------------------------------------------------------------------------


def _parse_json_obj(value: Optional[str], fallback):
    if not value:
        return fallback
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, type(fallback)) else fallback
    except (json.JSONDecodeError, TypeError):
        return fallback


def _reflection_task_from_row(row) -> Optional[dict]:
    if row is None:
        return None
    item = dict(row)
    item["sections"] = _parse_json_obj(item.get("sections"), [])
    item["input_snapshot"] = _parse_json_obj(item.get("input_snapshot"), {})
    return item


def _reflection_result_from_row(row) -> dict:
    item = dict(row)
    item["related_session_ids"] = _parse_json_obj(item.get("related_session_ids"), [])
    return item


def _reflection_event_from_row(row) -> dict:
    item = dict(row)
    item["payload"] = _parse_json_obj(item.get("payload"), {})
    return item


def create_reflection_task(
    user_id: int,
    sections: list[str],
    input_snapshot: Optional[dict] = None,
    agent_contract_version: str = "reflections-agent-v1",
    task_id: Optional[str] = None,
) -> str:
    """Create a Reflections-agent task and return its task id."""
    import uuid

    task_id = task_id or str(uuid.uuid4())
    db = get_db()
    try:
        db.execute(
            """
            INSERT INTO reflection_task (
              id, user_id, status, sections, input_snapshot,
              agent_contract_version, updated_at
            )
            VALUES (%s, %s, 'CREATED', %s, %s, %s, CURRENT_TIMESTAMP)
            """,
            (
                task_id,
                user_id,
                json.dumps(sections, ensure_ascii=False),
                json.dumps(input_snapshot or {}, ensure_ascii=False),
                agent_contract_version,
            ),
        )
        db.commit()
        return task_id
    finally:
        db.close()


def update_reflection_task_status(
    task_id: str,
    status: str,
    *,
    workspace_path: Optional[str] = None,
    input_snapshot: Optional[dict] = None,
    error_summary: Optional[str] = None,
    started_at: Optional[str] = None,
    completed_at: Optional[str] = None,
) -> None:
    """Update task lifecycle status and optional metadata fields."""
    assignments = ["status = %s", "updated_at = CURRENT_TIMESTAMP"]
    params: list = [status]
    optional_fields = {
        "workspace_path": workspace_path,
        "input_snapshot": json.dumps(input_snapshot, ensure_ascii=False) if input_snapshot is not None else None,
        "error_summary": error_summary,
        "started_at": started_at,
        "completed_at": completed_at,
    }
    for field, value in optional_fields.items():
        if value is not None:
            assignments.append(f"{field} = %s")
            params.append(value)
    params.append(task_id)

    db = get_db()
    try:
        db.execute(
            f"UPDATE reflection_task SET {', '.join(assignments)} WHERE id = %s",
            tuple(params),
        )
        db.commit()
    finally:
        db.close()


def get_reflection_task(task_id: str, user_id: Optional[int] = None) -> Optional[dict]:
    """Return a Reflections-agent task, optionally scoped to a user."""
    db = get_db()
    try:
        if user_id is None:
            row = db.execute("SELECT * FROM reflection_task WHERE id = %s LIMIT 1", (task_id,)).fetchone()
        else:
            row = db.execute(
                "SELECT * FROM reflection_task WHERE id = %s AND user_id = %s LIMIT 1",
                (task_id, user_id),
            ).fetchone()
        return _reflection_task_from_row(row)
    finally:
        db.close()


def get_latest_reflection_task(user_id: int) -> Optional[dict]:
    """Return the latest Reflections-agent task for a user."""
    db = get_db()
    try:
        row = db.execute(
            """
            SELECT * FROM reflection_task
            WHERE user_id = %s
            ORDER BY updated_at DESC, created_at DESC
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()
        return _reflection_task_from_row(row)
    finally:
        db.close()


def replace_reflection_section_results(
    task_id: str,
    user_id: int,
    section: str,
    results: list[dict],
) -> None:
    """Replace all persisted results for one task section."""
    import uuid

    db = get_db()
    try:
        db.execute(
            "DELETE FROM reflection_result WHERE task_id = %s AND user_id = %s AND section = %s",
            (task_id, user_id, section),
        )
        for item in results:
            db.execute(
                """
                INSERT INTO reflection_result (
                  id, task_id, user_id, section, title, description,
                  related_session_ids, evidence, confidence
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    str(uuid.uuid4()),
                    task_id,
                    user_id,
                    section,
                    item.get("title") or "",
                    item.get("description") or "",
                    json.dumps(item.get("related_session_ids") or [], ensure_ascii=False),
                    item.get("evidence") or "",
                    item.get("confidence") or "low",
                ),
            )
        db.commit()
    finally:
        db.close()


def list_reflection_results(task_id: str, user_id: int) -> list[dict]:
    """List structured Reflections results for a task."""
    db = get_db()
    try:
        rows = db.execute(
            """
            SELECT r.*
            FROM reflection_result r
            JOIN reflection_task t ON t.id = r.task_id
            WHERE r.task_id = %s AND r.user_id = %s AND t.user_id = %s
            ORDER BY r.section, r.created_at, r.id
            """,
            (task_id, user_id, user_id),
        ).fetchall()
        return [_reflection_result_from_row(row) for row in rows]
    finally:
        db.close()


def list_latest_reflection_results(user_id: int) -> list[dict]:
    """Return results for the latest completed or partially completed task."""
    db = get_db()
    try:
        task_row = db.execute(
            """
            SELECT *
            FROM reflection_task
            WHERE user_id = %s AND status IN ('COMPLETED', 'PARTIAL_FAILED')
            ORDER BY completed_at DESC, updated_at DESC
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()
        task = _reflection_task_from_row(task_row)
        if not task:
            return []
    finally:
        db.close()
    return list_reflection_results(task["id"], user_id)


def append_reflection_task_event(
    task_id: str,
    event_type: str,
    payload: Optional[dict] = None,
    *,
    event_id: Optional[str] = None,
    sequence: Optional[int] = None,
    created_at: Optional[str] = None,
) -> str:
    """Append a Reflections task event and return its id."""
    import uuid

    event_id = event_id or str(uuid.uuid4())
    db = get_db()
    try:
        db.execute(
            """
            INSERT INTO reflection_task_event (
              id, task_id, sequence, event_type, payload, created_at
            )
            VALUES (%s, %s, %s, %s, %s, COALESCE(%s, CURRENT_TIMESTAMP))
            ON CONFLICT (id) DO NOTHING
            """,
            (
                event_id,
                task_id,
                sequence,
                event_type,
                json.dumps(payload or {}, ensure_ascii=False),
                created_at,
            ),
        )
        db.commit()
        return event_id
    finally:
        db.close()


def list_reflection_task_events(
    task_id: str,
    user_id: int,
    after_event_id: Optional[str] = None,
) -> list[dict]:
    """List persisted task events, optionally after a specific event id."""
    db = get_db()
    try:
        after_sequence = None
        if after_event_id:
            row = db.execute(
                """
                SELECT e.sequence
                FROM reflection_task_event e
                JOIN reflection_task t ON t.id = e.task_id
                WHERE e.id = %s AND e.task_id = %s AND t.user_id = %s
                LIMIT 1
                """,
                (after_event_id, task_id, user_id),
            ).fetchone()
            if row is not None:
                after_sequence = row["sequence"]

        if after_sequence is None:
            rows = db.execute(
                """
                SELECT e.*
                FROM reflection_task_event e
                JOIN reflection_task t ON t.id = e.task_id
                WHERE e.task_id = %s AND t.user_id = %s
                ORDER BY e.sequence, e.created_at
                """,
                (task_id, user_id),
            ).fetchall()
        else:
            rows = db.execute(
                """
                SELECT e.*
                FROM reflection_task_event e
                JOIN reflection_task t ON t.id = e.task_id
                WHERE e.task_id = %s AND t.user_id = %s AND e.sequence > %s
                ORDER BY e.sequence, e.created_at
                """,
                (task_id, user_id, after_sequence),
            ).fetchall()
        return [_reflection_event_from_row(row) for row in rows]
    finally:
        db.close()


if __name__ == "__main__":
    # Initialize database
    init_db()
