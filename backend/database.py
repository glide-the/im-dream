#!/usr/bin/env python3
# [Input] Consume PostgreSQL connections, filesystem paths, JSON data, and optional session text extraction,
#         and memory workspace defaults.
# [Output] Provide persistence helpers for users, sessions, decks, voices, reports,
#          auth/OAuth state, Claude Agent threads/messages, and voice partition
#          Memory configs; user creation commits only after Admin-owned billing
#          identity/default-Free triggers complete.
# [Pos] database node in backend
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
# [Sync] 2026-08-17: CAS-update the current Agent inside an already bound Chat Deck.
"""
PostgreSQL runtime persistence helpers for Ink & Memory.

Schema:
- users: User accounts (email, password_hash)
- user_sessions: Editor sessions (editor state JSON)
- daily_pictures: Generated images (base64)
- user_preferences: Voice configs, meta prompts, etc.
"""

import logging
from collections.abc import Iterator, Mapping
from datetime import datetime, timedelta, timezone
from threading import RLock
from typing import Any, Optional, Union
import json
from psycopg import Error as PostgresError
from psycopg import IntegrityError as PostgresIntegrityError
from psycopg.errors import ForeignKeyViolation
from psycopg.pq import TransactionStatus

try:
    from persistence.postgres import PostgresPool
except ModuleNotFoundError:  # pragma: no cover - package import compatibility
    from backend.persistence.postgres import PostgresPool

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
        from backend.schema.capabilities import (
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


def replace_deck_claude_plugin_refs(
    db, deck_id: str, refs: list[dict]
) -> None:
    """Atomically replace a Deck's Claude plugin references.

    *refs* items: {plugin_installation_id, package_spec, resolved_version,
    artifact_digest, enabled, order_index}.  Validation (ready status, digest
    verification, CLI compatibility) happens in the service layer before this
    write; this helper only persists the validated set.
    """
    from services.deck.content_versioning import advance_deck_draft_revision

    now = datetime.now(timezone.utc).isoformat()
    with db:
        deck = db.execute(
            "SELECT id FROM decks WHERE id = %s FOR UPDATE", (deck_id,)
        ).fetchone()
        if deck is None:
            raise ValueError("Deck not found")
        existing = db.execute(
            """
            SELECT plugin_installation_id, package_spec, resolved_version,
                   artifact_digest, enabled, order_index
            FROM deck_claude_plugin_refs
            WHERE deck_id = %s
            ORDER BY order_index, plugin_installation_id
            """,
            (deck_id,),
        ).fetchall()
        current_projection = [
            {
                "plugin_installation_id": str(row["plugin_installation_id"]),
                "package_spec": row["package_spec"],
                "resolved_version": row["resolved_version"],
                "artifact_digest": row["artifact_digest"],
                "enabled": bool(row["enabled"]),
                "order_index": int(row["order_index"]),
            }
            for row in existing
        ]
        requested_projection = [
            {
                "plugin_installation_id": str(ref["plugin_installation_id"]),
                "package_spec": ref["package_spec"],
                "resolved_version": ref["resolved_version"],
                "artifact_digest": ref["artifact_digest"],
                "enabled": bool(ref.get("enabled", True)),
                "order_index": int(ref.get("order_index", position)),
            }
            for position, ref in enumerate(refs)
        ]
        if current_projection == requested_projection:
            return
        db.execute("DELETE FROM deck_claude_plugin_refs WHERE deck_id = %s", (deck_id,))
        for position, ref in enumerate(refs):
            db.execute(
                """
                INSERT INTO deck_claude_plugin_refs (
                    deck_id, plugin_installation_id, package_spec,
                    resolved_version, artifact_digest, enabled, order_index,
                    created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    deck_id,
                    ref["plugin_installation_id"],
                    ref["package_spec"],
                    ref["resolved_version"],
                    ref["artifact_digest"],
                    1 if ref.get("enabled", True) else 0,
                    int(ref.get("order_index", position)),
                    now,
                    now,
                ),
            )
        advance_deck_draft_revision(db, deck_id)


def list_deck_claude_plugin_refs(db, deck_id: str) -> list[dict]:
    """All Claude plugin references for a Deck (enabled and disabled)."""
    cursor = db.execute(
        """
        SELECT r.*, i.status AS installation_status, i.source_type,
               i.claude_cli_version, i.manifest_json
        FROM deck_claude_plugin_refs r
        JOIN claude_plugin_installations i ON i.id = r.plugin_installation_id
        WHERE r.deck_id = %s
        ORDER BY r.order_index, r.created_at, r.plugin_installation_id
        """,
        (deck_id,),
    )
    return [dict(row) for row in cursor.fetchall()]


def backfill_builtin_deck_plugin_refs(db, builtin_installation_id: str,
                                      package_spec: str, resolved_version: str,
                                      artifact_digest: str) -> int:
    """One-time migration: bind decks using the legacy built-in Deck Plugin to
    the new platform-builtin Claude plugin installation.

    Legacy signal: an active ``deck_plugin_bindings`` row for
    ``ink.dream.story-workflow``.  Idempotent via an explicit primary-key
    conflict policy.  Returns the
    number of refs created.  Old threads and the legacy workflow tables are
    untouched.
    """
    rows = db.execute(
        """
        SELECT DISTINCT deck_id FROM deck_plugin_bindings
        WHERE status = 'active' AND deck_plugin_id = 'ink.dream.story-workflow'
        """
    ).fetchall()
    now = datetime.now(timezone.utc).isoformat()
    created = 0
    with db:
        for row in rows:
            cursor = db.execute(
                """
                INSERT INTO deck_claude_plugin_refs (
                    deck_id, plugin_installation_id, package_spec,
                    resolved_version, artifact_digest, enabled, order_index,
                    created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, 1, 0, %s, %s)
                ON CONFLICT (deck_id, plugin_installation_id) DO NOTHING
                """,
                (
                    row[0],
                    builtin_installation_id,
                    package_spec,
                    resolved_version,
                    artifact_digest,
                    now,
                    now,
                ),
            )
            created += cursor.rowcount
    return created


def seed_system_decks():
    """Seed only the active screenplay template when invoked explicitly.

    Runtime startup does not call this helper. Admin/Drizzle remains the owner
    of shared database rollout; this helper is retained for explicit fixture or
    import flows that already have the published Deck tables.
    """

    import config

    template = config.SCREENPLAY_DECK_TEMPLATE
    memory_config_json = _default_memory_workspace_config_json()
    db = get_db()
    try:
        db.execute(
            """
            INSERT INTO decks (
                id, name, name_zh, name_en, description, description_zh,
                description_en, icon, color, is_system, enabled,
                has_local_changes, order_index
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE, TRUE, FALSE, 0)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                name_zh = EXCLUDED.name_zh,
                name_en = EXCLUDED.name_en,
                description = EXCLUDED.description,
                description_zh = EXCLUDED.description_zh,
                description_en = EXCLUDED.description_en,
                icon = EXCLUDED.icon,
                color = EXCLUDED.color,
                enabled = TRUE,
                order_index = 0,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                template["id"], template["name"], template["name_zh"],
                template["name_en"], template["description"],
                template["description_zh"], template["description_en"],
                template["icon"], template["color"],
            ),
        )
        for order, voice in enumerate(template["voices"]):
            db.execute(
                """
                INSERT INTO voices (
                    id, deck_id, name, name_zh, name_en, system_prompt, icon,
                    color, is_system, enabled, has_local_changes, order_index,
                    memory_workspace_config
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE, TRUE, FALSE, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    deck_id = EXCLUDED.deck_id,
                    name = EXCLUDED.name,
                    name_zh = EXCLUDED.name_zh,
                    name_en = EXCLUDED.name_en,
                    system_prompt = EXCLUDED.system_prompt,
                    icon = EXCLUDED.icon,
                    color = EXCLUDED.color,
                    enabled = TRUE,
                    order_index = EXCLUDED.order_index,
                    memory_workspace_config = EXCLUDED.memory_workspace_config,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    voice["id"], template["id"], voice["name"],
                    voice["name_zh"], voice["name_en"], voice["system_prompt"],
                    voice["icon"], voice["color"], order, memory_config_json,
                ),
            )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

# ========== Deck CRUD ==========


def _retired_system_deck_visibility(alias: str = "d") -> tuple[str, list[str]]:
    """Hide untouched retired-template forks while preserving user work."""

    import config

    retired_ids = list(config.RETIRED_SYSTEM_DECK_IDS)
    if not retired_ids:
        return "", []
    placeholders = ",".join("%s" for _ in retired_ids)
    clause = f"""
        AND (
            {alias}.parent_id IS NULL
            OR {alias}.parent_id NOT IN ({placeholders})
            OR {alias}.has_local_changes IS TRUE
            OR EXISTS (
                SELECT 1 FROM voices changed_voice
                WHERE changed_voice.deck_id = {alias}.id
                  AND changed_voice.has_local_changes IS TRUE
            )
        )
    """
    return clause, retired_ids


def get_user_decks(user_id: int):
    """
    Get all user's own decks (forked from system templates).
    Returns list of deck dicts with voice counts.

    @@@ Users only see their own forked copies, never system decks directly
    """
    visibility_sql, visibility_params = _retired_system_deck_visibility()
    db = get_db()
    try:
        rows = db.execute(f"""
        SELECT d.*,
               COUNT(v.id) FILTER (WHERE v.enabled IS TRUE) as voice_count,
               COUNT(v.id) as total_voice_count
        FROM decks d
        LEFT JOIN voices v ON d.id = v.deck_id
        WHERE d.owner_id = %s
        {visibility_sql}
        GROUP BY d.id
        ORDER BY d.order_index, d.created_at
        """, (user_id, *visibility_params)).fetchall()
        decks = [dict(row) for row in rows]
        from services.deck.agent_type import decorate_decks_with_agent_type
        from services.deck.content_versioning import decorate_decks_with_content_version_state
        from services.deck.sharing import decorate_decks_with_sharing_policy
        decorate_decks_with_agent_type(db, decks)
        decorate_decks_with_content_version_state(db, decks)
        decorate_decks_with_sharing_policy(decks)
        return decks
    finally:
        db.close()

def get_published_decks(exclude_owner_id: Optional[int] = None):
    """
    Get collectable Decks for the community store.

    The projection includes the configured active system default plus Decks
    published by other actors. Retired system defaults remain excluded.
    Returns list of deck dicts with voice counts and author info.
    """
    import config

    db = get_db()
    try:
        rows = db.execute("""
        SELECT d.*, COUNT(v.id) as voice_count, u.display_name as author_display_name
        FROM decks d
        LEFT JOIN voices v ON d.id = v.deck_id AND v.enabled IS TRUE
        LEFT JOIN users u ON d.owner_id = u.id
        WHERE ((d.is_system IS TRUE AND d.id = %s) OR d.published IS TRUE)
          AND (%s IS NULL OR d.owner_id IS NULL OR d.owner_id <> %s)
        GROUP BY d.id, u.display_name
        ORDER BY d.install_count DESC, d.created_at DESC
        """, (
            config.DEFAULT_SYSTEM_DECK_ID,
            exclude_owner_id,
            exclude_owner_id,
        )).fetchall()
        decks = [dict(row) for row in rows]
        from services.deck.agent_type import decorate_decks_with_agent_type
        from services.deck.content_versioning import decorate_decks_with_content_version_state
        from services.deck.sharing import decorate_decks_with_sharing_policy
        decorate_decks_with_agent_type(db, decks)
        decorate_decks_with_content_version_state(db, decks)
        decorate_decks_with_sharing_policy(decks)
        return decks
    finally:
        db.close()

def publish_deck(deck_id: str, user_id: int):
    """
    Publish a deck to community store.
    @@@ Breaks parent chain - published deck becomes standalone
    """
    db = get_db()
    try:
        deck_row = db.execute(
            "SELECT * FROM decks WHERE id = %s AND owner_id = %s FOR UPDATE",
            (deck_id, user_id),
        ).fetchone()
        if deck_row is None:
            raise ValueError("Deck not found or not owned by user")
        deck = dict(deck_row)
        voice_rows = db.execute(
            "SELECT * FROM voices WHERE deck_id = %s ORDER BY order_index, created_at",
            (deck_id,),
        ).fetchall()
        deck["voices"] = [dict(row) for row in voice_rows]
        from services.deck.sharing import require_publishable
        require_publishable(deck)

        # Get user's display name for author_name
        user = db.execute("SELECT display_name FROM users WHERE id = %s", (user_id,)).fetchone()
        author_name = user['display_name'] if user and user['display_name'] else f"User {user_id}"

        db.execute("""
        UPDATE decks
        SET published = TRUE,
            author_name = %s,
            parent_id = NULL
        WHERE id = %s AND owner_id = %s
        """, (author_name, deck_id, user_id))
        db.commit()
    finally:
        db.close()

def unpublish_deck(deck_id: str, user_id: int):
    """
    Unpublish a deck from community store.
    """
    db = get_db()
    try:
        db.execute("""
        UPDATE decks
        SET published = FALSE
        WHERE id = %s AND owner_id = %s
        """, (deck_id, user_id))
        db.commit()
    finally:
        db.close()

def increment_deck_install_count(deck_id: str):
    """
    Increment install counter when deck is forked from store.
    """
    db = get_db()
    try:
        db.execute("""
        UPDATE decks
        SET install_count = install_count + 1
        WHERE id = %s
        """, (deck_id,))
        db.commit()
    finally:
        db.close()


def _parse_voice_row(row: dict) -> dict:
    """Parse a raw voices DB row, deserialising JSON columns."""
    raw_config = row.get("memory_workspace_config")
    if raw_config and isinstance(raw_config, str):
        try:
            row["memory_workspace_config"] = json.loads(raw_config)
        except (json.JSONDecodeError, ValueError):
            row["memory_workspace_config"] = None
    return row


def get_deck_with_voices(user_id: int, deck_id: str):
    """
    Get full deck details with all voices.
    Returns None if deck doesn't exist or user doesn't own it.

    @@@ Users only access their own forked decks
    """
    db = get_db()
    try:
        # Get deck (must be user's own)
        deck_row = db.execute("""
        SELECT * FROM decks
        WHERE id = %s AND owner_id = %s
        """, (deck_id, user_id)).fetchone()

        if not deck_row:
            return None

        deck = dict(deck_row)
        from services.deck.agent_type import decorate_decks_with_agent_type
        from services.deck.content_versioning import decorate_decks_with_content_version_state
        from services.deck.sharing import decorate_decks_with_sharing_policy
        decorate_decks_with_agent_type(db, [deck])
        decorate_decks_with_content_version_state(db, [deck])

        # Get voices in this deck
        voice_rows = db.execute("""
        SELECT * FROM voices
        WHERE deck_id = %s
        ORDER BY order_index, created_at
        """, (deck_id,)).fetchall()

        deck['voices'] = [_parse_voice_row(dict(row)) for row in voice_rows]
        decorate_decks_with_sharing_policy([deck])
        return deck
    finally:
        db.close()

def _verified_default_deck_plugin_installation(db, default_plugin_ref: dict) -> dict:
    """Lock and re-check the installation snapshot before a Deck ref write."""

    installation = db.execute(
        """
        SELECT id, package_name, marketplace, resolved_version,
               artifact_digest, status
        FROM claude_plugin_installations
        WHERE id = %s
        FOR SHARE
        """,
        (default_plugin_ref["plugin_installation_id"],),
    ).fetchone()
    expected = (
        default_plugin_ref["package_name"],
        default_plugin_ref["resolved_version"],
        default_plugin_ref["artifact_digest"],
    )
    actual = (
        installation["package_name"] if installation else None,
        installation["resolved_version"] if installation else None,
        installation["artifact_digest"] if installation else None,
    )
    if installation is None or installation["status"] != "ready" or actual != expected:
        raise ValueError("DEFAULT_DECK_PLUGIN_UNAVAILABLE")
    return installation


def _upsert_default_deck_plugin_ref(db, deck_id: str, default_plugin_ref: dict) -> None:
    """Persist one enabled configured ref without removing other selections."""

    installation = _verified_default_deck_plugin_installation(db, default_plugin_ref)
    db.execute(
        """
        INSERT INTO deck_claude_plugin_refs (
            deck_id, plugin_installation_id, package_spec,
            resolved_version, artifact_digest, enabled, order_index,
            created_at, updated_at
        ) VALUES (%s, %s, %s, %s, %s, 1, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ON CONFLICT (deck_id, plugin_installation_id) DO UPDATE SET
            package_spec = EXCLUDED.package_spec,
            resolved_version = EXCLUDED.resolved_version,
            artifact_digest = EXCLUDED.artifact_digest,
            enabled = 1,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            deck_id,
            installation["id"],
            f"{installation['package_name']}@{installation['marketplace']}",
            installation["resolved_version"],
            installation["artifact_digest"],
        ),
    )


def _insert_default_screenplay_deck(
    db,
    user_id: int,
    default_plugin_ref: dict,
) -> str:
    """Insert the configured user-owned screenplay Deck in the caller transaction."""

    import config
    import uuid

    template = config.SCREENPLAY_DECK_TEMPLATE
    deck_id = str(uuid.uuid4())
    memory_config_json = _default_memory_workspace_config_json()
    max_order = db.execute(
        "SELECT MAX(order_index) AS max_order FROM decks WHERE owner_id = %s",
        (user_id,),
    ).fetchone()["max_order"]
    db.execute(
        """
        INSERT INTO decks (
            id, name, name_zh, name_en, description, description_zh,
            description_en, icon, color, is_system, owner_id, enabled,
            has_local_changes, order_index
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, FALSE, %s, TRUE, FALSE, %s)
        """,
        (
            deck_id, template["name"], template["name_zh"], template["name_en"],
            template["description"], template["description_zh"],
            template["description_en"], template["icon"], template["color"],
            user_id, (max_order or 0) + 1,
        ),
    )
    for order, voice in enumerate(template["voices"]):
        db.execute(
            """
            INSERT INTO voices (
                id, deck_id, name, name_zh, name_en, system_prompt, icon,
                color, is_system, owner_id, enabled, has_local_changes,
                order_index, memory_workspace_config
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, FALSE, %s, TRUE, FALSE, %s, %s)
            """,
            (
                str(uuid.uuid4()), deck_id, voice["name"], voice["name_zh"],
                voice["name_en"], voice["system_prompt"], voice["icon"],
                voice["color"], user_id, order, memory_config_json,
            ),
        )
    _upsert_default_deck_plugin_ref(db, deck_id, default_plugin_ref)
    return deck_id


def reconcile_default_screenplay_deck_plugin_ref(
    user_id: int,
    default_plugin_ref: dict,
) -> dict:
    """Ensure one untouched screenplay default and repair its empty refs.

    Existing refs, including a user's explicit deselection/replacement state,
    are never overwritten.  The fallback fingerprint is derived entirely from
    the configured template because fallback Decks have no shared parent row.
    The actor row lock serializes missing-default creation across tabs.
    """

    import config

    template = config.SCREENPLAY_DECK_TEMPLATE
    role_names = [voice["name"] for voice in template["voices"]]
    role_placeholders = ",".join("%s" for _ in role_names)
    db = get_db()
    try:
        actor = db.execute(
            "SELECT id FROM users WHERE id = %s FOR UPDATE",
            (user_id,),
        ).fetchone()
        if actor is None:
            raise ValueError("DEFAULT_DECK_ACTOR_NOT_FOUND")

        deck = db.execute(
            f"""
            SELECT d.id
            FROM decks d
            WHERE d.owner_id = %s
              AND d.is_system IS FALSE
              AND d.has_local_changes IS FALSE
              AND (
                d.parent_id = %s
                OR (
                  d.parent_id IS NULL
                  AND d.name = %s
                  AND d.name_zh = %s
                  AND d.name_en = %s
                  AND (SELECT COUNT(*) FROM voices v WHERE v.deck_id = d.id) = %s
                  AND NOT EXISTS (
                    SELECT 1
                    FROM voices v
                    WHERE v.deck_id = d.id
                      AND (
                        v.has_local_changes IS TRUE
                        OR COALESCE(v.name_zh, v.name) NOT IN ({role_placeholders})
                      )
                  )
                )
              )
            ORDER BY d.created_at
            LIMIT 1
            FOR UPDATE
            """,
            (
                user_id,
                config.DEFAULT_SYSTEM_DECK_ID,
                template["name"],
                template["name_zh"],
                template["name_en"],
                len(role_names),
                *role_names,
            ),
        ).fetchone()
        if deck is None:
            deck_id = _insert_default_screenplay_deck(db, user_id, default_plugin_ref)
            db.commit()
            return {"deck_id": deck_id, "reconciled": True, "reason": "default_created"}

        existing_ref = db.execute(
            "SELECT 1 FROM deck_claude_plugin_refs WHERE deck_id = %s LIMIT 1",
            (deck["id"],),
        ).fetchone()
        if existing_ref is not None:
            db.rollback()
            return {
                "deck_id": deck["id"],
                "reconciled": False,
                "reason": "refs_preserved",
            }

        _upsert_default_deck_plugin_ref(db, deck["id"], default_plugin_ref)
        from services.deck.content_versioning import advance_deck_draft_revision
        advance_deck_draft_revision(db, deck["id"])
        db.commit()
        return {"deck_id": deck["id"], "reconciled": True, "reason": "missing_ref"}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def create_deck(user_id: int, name: str, description: str = None,
                name_zh: str = None, name_en: str = None,
                description_zh: str = None, description_en: str = None,
                icon: str = None, color: str = None,
                order_index: int = None,
                default_plugin_ref: Optional[dict] = None) -> str:
    """
    Create a new user deck. Returns deck_id.
    """
    import uuid

    db = get_db()
    try:
        deck_id = str(uuid.uuid4())

        # Get max order_index if not provided
        if order_index is None:
            max_order = db.execute(
                "SELECT MAX(order_index) as max_order FROM decks WHERE owner_id = %s",
                (user_id,)
            ).fetchone()['max_order']
            order_index = (max_order or 0) + 1

        db.execute("""
        INSERT INTO decks (id, name, name_zh, name_en, description, description_zh, description_en,
                          icon, color, is_system, owner_id, enabled, has_local_changes, order_index)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, FALSE, %s, TRUE, FALSE, %s)
        """, (deck_id, name, name_zh, name_en, description, description_zh, description_en,
              icon, color, user_id, order_index))

        if default_plugin_ref is not None:
            _upsert_default_deck_plugin_ref(db, deck_id, default_plugin_ref)

        db.commit()
        return deck_id
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def update_deck(user_id: int, deck_id: str, updates: dict) -> bool:
    """
    Update a user's deck. Only works if user owns the deck.
    Returns True if updated, False if not found or permission denied.

    Updates dict can contain: name, name_zh, name_en, description, description_zh,
    description_en, icon, color, enabled, order_index

    @@@ Content changes (name, description, icon, color) → has_local_changes = 1
    @@@ Preference changes (enabled, order_index) → don't affect has_local_changes
    """
    db = get_db()
    try:
        from services.deck.content_versioning import advance_deck_draft_revision

        allowed_fields = ['name', 'name_zh', 'name_en', 'description', 'description_zh',
                         'description_en', 'icon', 'color', 'enabled', 'order_index']
        # Lock the aggregate before comparing or writing so a commit snapshot
        # cannot race with a form mutation.
        deck = db.execute(
            f"SELECT owner_id, {', '.join(allowed_fields)} FROM decks WHERE id = %s FOR UPDATE",
            (deck_id,)
        ).fetchone()

        if not deck or deck['owner_id'] != user_id:
            return False

        content_fields = ['name', 'name_zh', 'name_en', 'description', 'description_zh',
                         'description_en', 'icon', 'color']

        update_fields = []
        params = []
        for field in allowed_fields:
            if field in updates:
                value = bool(updates[field]) if field == "enabled" else updates[field]
                current = bool(deck[field]) if field == "enabled" else deck[field]
                if current == value:
                    continue
                update_fields.append(f"{field} = %s")
                params.append(value)

        if not update_fields:
            db.rollback()
            return True  # No updates

        # @@@ Mark as locally changed if content fields are modified
        changed_fields = {field.split(" =", 1)[0] for field in update_fields}
        has_content_change = any(field in changed_fields for field in content_fields)
        if has_content_change:
            update_fields.append("has_local_changes = TRUE")

        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        params.append(deck_id)

        db.execute(
            f"UPDATE decks SET {', '.join(update_fields)} WHERE id = %s",
            params
        )
        advance_deck_draft_revision(db, deck_id)
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def delete_deck(user_id: int, deck_id: str) -> bool:
    """
    Delete a user's deck. Only works if user owns the deck.
    Deletes mutable Claude plugin refs and unused plugin bindings explicitly,
    then lets the database cascade voices. Related Chat threads, derived Decks,
    and immutable runtime snapshots block deletion.
    Returns True if deleted, False if not found or permission denied.
    """
    db = get_db()
    try:
        # Lock the aggregate so a concurrent reference cannot be attached
        # between the dependency check and the final DELETE.
        deck = db.execute(
            "SELECT owner_id FROM decks WHERE id = %s FOR UPDATE",
            (deck_id,)
        ).fetchone()

        if not deck or deck['owner_id'] != user_id:
            return False

        child_deck = db.execute(
            "SELECT 1 FROM decks WHERE parent_id = %s LIMIT 1",
            (deck_id,),
        ).fetchone()
        if child_deck is not None:
            raise DeckDeletionConflict("child_decks")

        related_thread = db.execute(
            "SELECT 1 FROM chat_thread WHERE deck_id = %s LIMIT 1",
            (deck_id,),
        ).fetchone()
        if related_thread is not None:
            raise DeckDeletionConflict("related_threads")

        runtime_history = db.execute(
            """
            SELECT 1 FROM deck_runtime_snapshots WHERE deck_id = %s
            LIMIT 1
            """,
            (deck_id,),
        ).fetchone()
        if runtime_history is not None:
            raise DeckDeletionConflict("runtime_history")

        db.execute(
            "DELETE FROM deck_claude_plugin_refs WHERE deck_id = %s",
            (deck_id,),
        )
        db.execute(
            "DELETE FROM deck_plugin_bindings WHERE deck_id = %s",
            (deck_id,),
        )
        db.execute("DELETE FROM decks WHERE id = %s", (deck_id,))
        db.commit()
        return True
    except DeckDeletionConflict:
        db.rollback()
        raise
    except ForeignKeyViolation as exc:
        db.rollback()
        raise DeckDeletionConflict("referenced_records") from exc
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def auto_fork_system_decks(user_id: int, default_plugin_ref: dict) -> str:
    """
    Provision the one active screenplay Deck for a new user.
    Called on user registration/first login.
    """
    import config

    # Resolve the shared template before fork_deck opens its own lease.
    db = get_db()
    try:
        system_deck = db.execute(
            "SELECT id FROM decks WHERE id = %s AND is_system IS TRUE",
            (config.DEFAULT_SYSTEM_DECK_ID,),
        ).fetchone()
    finally:
        db.close()

    if system_deck is not None:
        deck_id = fork_deck(
            user_id,
            system_deck["id"],
            enabled=True,
            default_plugin_ref=default_plugin_ref,
        )
    else:
        deck_id = create_default_screenplay_deck(
            user_id,
            default_plugin_ref=default_plugin_ref,
        )
    print(f"✅ Provisioned screenplay Deck {deck_id} for user {user_id}")
    return deck_id


def create_default_screenplay_deck(user_id: int, default_plugin_ref: dict) -> str:
    """Create the configured screenplay template as a user-owned Deck.

    This fallback writes only normal Deck/Voice rows for the registering user;
    it never creates shared schema or system rows at runtime.
    """

    db = get_db()
    try:
        deck_id = _insert_default_screenplay_deck(db, user_id, default_plugin_ref)
        db.commit()
        return deck_id
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def fork_deck(
    user_id: int,
    deck_id: str,
    enabled: bool = True,
    default_plugin_ref: Optional[dict] = None,
) -> str:
    """
    Fork a deck to create user's own copy.
    Copies deck + all voices. Returns new deck_id.

    Args:
        user_id: The user who is forking the deck
        deck_id: ID of the deck to fork
        enabled: Whether the forked deck should be enabled (default: True)
    """
    import uuid

    db = get_db()
    try:
        # Get source deck
        source_deck = db.execute("SELECT * FROM decks WHERE id = %s", (deck_id,)).fetchone()
        if not source_deck:
            raise ValueError(f"Deck {deck_id} not found")
        from services.deck.sharing import require_collectable
        require_collectable(dict(source_deck), user_id)

        # Create new deck ID
        new_deck_id = str(uuid.uuid4())

        # Copy deck (has_local_changes = 0 initially, synced with parent)
        db.execute("""
        INSERT INTO decks (id, name, name_zh, name_en, description, description_zh, description_en,
                          icon, color, is_system, parent_id, owner_id, enabled, has_local_changes, order_index)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, FALSE, %s, %s, %s, FALSE, %s)
        """, (new_deck_id,
              source_deck['name'],
              source_deck['name_zh'],
              source_deck['name_en'],
              source_deck['description'],
              source_deck['description_zh'],
              source_deck['description_en'],
              source_deck['icon'],
              source_deck['color'],
              deck_id,  # parent_id tracks fork source
              user_id,
              bool(enabled),
              source_deck['order_index']))

        # Copy all voices
        source_voices = db.execute(
            "SELECT * FROM voices WHERE deck_id = %s ORDER BY order_index",
            (deck_id,)
        ).fetchall()

        for voice in source_voices:
            new_voice_id = str(uuid.uuid4())
            memory_config_json = voice["memory_workspace_config"] or _default_memory_workspace_config_json()
            db.execute("""
            INSERT INTO voices (id, deck_id, name, name_zh, name_en, system_prompt,
                              icon, color, is_system, parent_id, owner_id, enabled, has_local_changes, order_index, memory_workspace_config)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, FALSE, %s, %s, TRUE, FALSE, %s, %s)
            """, (new_voice_id,
                  new_deck_id,
                  voice['name'],
                  voice['name_zh'],
                  voice['name_en'],
                  voice['system_prompt'],
                  voice['icon'],
                  voice['color'],
                  voice['id'],  # parent_id tracks fork source
                  user_id,
                  voice['order_index'],
                  memory_config_json))

        # A system/community Deck's verified plugin selection is part of the
        # template. The fork stores the same installation references, never
        # filesystem paths or mutable discovery state.
        db.execute(
            """
            INSERT INTO deck_claude_plugin_refs (
                deck_id, plugin_installation_id, package_spec,
                resolved_version, artifact_digest, enabled, order_index,
                created_at, updated_at
            )
            SELECT %s, plugin_installation_id, package_spec,
                   resolved_version, artifact_digest, enabled, order_index,
                   CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            FROM deck_claude_plugin_refs
            WHERE deck_id = %s
            """,
            (new_deck_id, deck_id),
        )

        if default_plugin_ref is not None:
            _upsert_default_deck_plugin_ref(db, new_deck_id, default_plugin_ref)

        db.commit()
        return new_deck_id
    finally:
        db.close()

def sync_deck_with_parent(user_id: int, deck_id: str, force: bool = False) -> dict:
    """
    Sync user's forked deck with parent template (complete reset).

    Deletes all user's voices and re-creates from parent template.
    This ensures deleted voices reappear and new parent voices are added.

    Returns: {"success": True, "synced_voices": N}
    Raises ValueError if deck not found, no parent, or parent missing
    """
    import uuid

    db = get_db()
    try:
        # Get user's deck
        deck = db.execute(
            "SELECT * FROM decks WHERE id = %s AND owner_id = %s FOR UPDATE",
            (deck_id, user_id)
        ).fetchone()

        if not deck:
            raise ValueError("Deck not found or permission denied")

        if not deck['parent_id']:
            raise ValueError("Deck is not a fork (no parent)")

        # Get parent deck
        parent = db.execute(
            "SELECT * FROM decks WHERE id = %s",
            (deck['parent_id'],)
        ).fetchone()

        if not parent:
            raise ValueError("Parent deck not found")

        # @@@ Step 1: Sync deck metadata (preserve user preferences like enabled/order)
        db.execute("""
        UPDATE decks SET
            name = %s, name_zh = %s, name_en = %s,
            description = %s, description_zh = %s, description_en = %s,
            icon = %s, color = %s,
            has_local_changes = FALSE,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
        """, (parent['name'], parent['name_zh'], parent['name_en'],
              parent['description'], parent['description_zh'], parent['description_en'],
              parent['icon'], parent['color'],
              deck_id))

        # @@@ Step 2: Delete ALL user's voices in this deck
        db.execute("DELETE FROM voices WHERE deck_id = %s", (deck_id,))

        # @@@ Step 3: Re-create all voices from parent (fresh copy)
        parent_voices = db.execute(
            "SELECT * FROM voices WHERE deck_id = %s ORDER BY order_index",
            (deck['parent_id'],)
        ).fetchall()

        synced_count = 0
        for parent_voice in parent_voices:
            new_voice_id = str(uuid.uuid4())
            memory_config_json = parent_voice["memory_workspace_config"] or _default_memory_workspace_config_json()
            db.execute("""
            INSERT INTO voices (id, deck_id, name, name_zh, name_en, system_prompt,
                              icon, color, is_system, parent_id, owner_id, enabled, has_local_changes, order_index, memory_workspace_config)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, FALSE, %s, %s, TRUE, FALSE, %s, %s)
            """, (new_voice_id,
                  deck_id,  # User's deck
                  parent_voice['name'],
                  parent_voice['name_zh'],
                  parent_voice['name_en'],
                  parent_voice['system_prompt'],
                  parent_voice['icon'],
                  parent_voice['color'],
                  parent_voice['id'],  # parent_id tracks original
                  user_id,
                  parent_voice['order_index'],
                  memory_config_json))
            synced_count += 1

        from services.deck.content_versioning import advance_deck_draft_revision
        advance_deck_draft_revision(db, deck_id)
        db.commit()
        return {"success": True, "synced_voices": synced_count}
    finally:
        db.close()

def load_voices_from_user_decks(user_id: int) -> dict:
    """
    Load all enabled voices from user's enabled decks for LLM analysis.

    Returns dict format: {voice_id: {name, systemPrompt, icon, color}}
    Compatible with analyze_stateless() expectations.
    """
    visibility_sql, visibility_params = _retired_system_deck_visibility()
    db = get_db()
    try:
        # Get all user's enabled decks
        enabled_decks = db.execute(f"""
        SELECT d.id FROM decks d
        WHERE d.owner_id = %s AND d.enabled IS TRUE
        {visibility_sql}
        ORDER BY d.order_index, d.created_at
        """, (user_id, *visibility_params)).fetchall()

        if not enabled_decks:
            return {}

        deck_ids = [deck['id'] for deck in enabled_decks]

        # Get all enabled voices from these decks
        placeholders = ','.join('%s' for _ in deck_ids)
        voices = db.execute(f"""
        SELECT id, name, system_prompt, icon, color
        FROM voices
        WHERE deck_id IN ({placeholders}) AND enabled IS TRUE
        ORDER BY order_index, created_at
        """, deck_ids).fetchall()

        # Convert to expected format
        voice_dict = {}
        for voice in voices:
            voice_dict[voice['id']] = {
                'name': voice['name'],
                'systemPrompt': voice['system_prompt'],
                'icon': voice['icon'],
                'color': voice['color']
            }

        return voice_dict
    finally:
        db.close()

# ========== Voice CRUD ==========

def create_voice(user_id: int, deck_id: str, name: str, system_prompt: str,
                name_zh: str = None, name_en: str = None,
                icon: str = None, color: str = None,
                order_index: int = None,
                memory_workspace_config: dict = None) -> str:
    """
    Create a new voice in a user's deck.
    Returns voice_id.
    """
    import uuid

    db = get_db()
    try:
        # Check deck ownership
        deck = db.execute(
            "SELECT owner_id FROM decks WHERE id = %s FOR UPDATE",
            (deck_id,)
        ).fetchone()

        if not deck or deck['owner_id'] != user_id:
            raise ValueError("Deck not found or permission denied")

        voice_id = str(uuid.uuid4())

        # Get max order_index if not provided
        if order_index is None:
            max_order = db.execute(
                "SELECT MAX(order_index) as max_order FROM voices WHERE deck_id = %s",
                (deck_id,)
            ).fetchone()['max_order']
            order_index = (max_order or 0) + 1

        memory_config_json = _memory_workspace_config_json(memory_workspace_config)

        db.execute("""
        INSERT INTO voices (id, deck_id, name, name_zh, name_en, system_prompt,
                           icon, color, is_system, owner_id, enabled, has_local_changes,
                           order_index, memory_workspace_config)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, FALSE, %s, TRUE, FALSE, %s, %s)
        """, (voice_id, deck_id, name, name_zh, name_en, system_prompt,
              icon, color, user_id, order_index, memory_config_json))

        from services.deck.content_versioning import advance_deck_draft_revision
        advance_deck_draft_revision(db, deck_id)
        db.commit()
        return voice_id
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def update_voice(user_id: int, voice_id: str, updates: dict) -> bool:
    """
    Update a user's voice. Only works if user owns the voice.
    Returns True if updated, False if not found or permission denied.

    Updates dict can contain: name, name_zh, name_en, system_prompt,
    icon, color, enabled, order_index

    @@@ Content changes (name, system_prompt, icon, color) → has_local_changes = 1
    @@@ Preference changes (enabled, order_index) → don't affect has_local_changes
    """
    db = get_db()
    try:
        voice_ref = db.execute(
            "SELECT deck_id FROM voices WHERE id = %s", (voice_id,)
        ).fetchone()
        if voice_ref is None:
            db.rollback()
            return False
        deck_id = str(voice_ref["deck_id"])
        deck = db.execute(
            "SELECT owner_id FROM decks WHERE id = %s FOR UPDATE", (deck_id,)
        ).fetchone()
        if deck is None or deck["owner_id"] != user_id:
            db.rollback()
            return False

        allowed_fields = ['name', 'name_zh', 'name_en', 'system_prompt',
                         'icon', 'color', 'enabled', 'order_index', 'thread_id',
                         'memory_workspace_config']
        voice = db.execute(
            f"SELECT owner_id, {', '.join(allowed_fields)} FROM voices WHERE id = %s FOR UPDATE",
            (voice_id,)
        ).fetchone()

        if not voice or voice['owner_id'] != user_id:
            return False

        content_fields = ['name', 'name_zh', 'name_en', 'system_prompt',
                         'icon', 'color']

        update_fields = []
        params = []
        for field in allowed_fields:
            if field in updates:
                value = updates[field]
                if field == "enabled":
                    value = bool(value)
                # Serialise memory_workspace_config dict to JSON string.
                if field == 'memory_workspace_config' and isinstance(value, dict):
                    value = json.dumps(value, ensure_ascii=False, sort_keys=True)
                current = voice[field]
                if field == 'memory_workspace_config':
                    try:
                        current = json.dumps(
                            json.loads(current) if isinstance(current, str) else current,
                            ensure_ascii=False,
                            sort_keys=True,
                        )
                    except (TypeError, ValueError, json.JSONDecodeError):
                        pass
                if field == "enabled":
                    current = bool(current)
                if current == value:
                    continue
                update_fields.append(f"{field} = %s")
                params.append(value)

        if not update_fields:
            db.rollback()
            return True  # No updates

        # @@@ Mark as locally changed if content fields are modified
        changed_fields = {field.split(" =", 1)[0] for field in update_fields}
        has_content_change = any(field in changed_fields for field in content_fields)
        if has_content_change:
            update_fields.append("has_local_changes = TRUE")

        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        params.append(voice_id)

        db.execute(
            f"UPDATE voices SET {', '.join(update_fields)} WHERE id = %s",
            params
        )
        versioned_fields = set(allowed_fields) - {"thread_id"}
        if changed_fields & versioned_fields:
            from services.deck.content_versioning import advance_deck_draft_revision
            advance_deck_draft_revision(db, deck_id)
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def delete_voice(user_id: int, voice_id: str) -> bool:
    """
    Delete a user's voice. Only works if user owns the voice.
    Returns True if deleted, False if not found or permission denied.
    """
    db = get_db()
    try:
        voice_ref = db.execute(
            "SELECT deck_id FROM voices WHERE id = %s", (voice_id,)
        ).fetchone()
        if voice_ref is None:
            db.rollback()
            return False
        deck_id = str(voice_ref["deck_id"])
        deck = db.execute(
            "SELECT owner_id FROM decks WHERE id = %s FOR UPDATE", (deck_id,)
        ).fetchone()
        voice = db.execute(
            "SELECT owner_id FROM voices WHERE id = %s FOR UPDATE", (voice_id,)
        ).fetchone()

        if not deck or deck['owner_id'] != user_id or not voice or voice['owner_id'] != user_id:
            db.rollback()
            return False

        db.execute("DELETE FROM voices WHERE id = %s", (voice_id,))
        from services.deck.content_versioning import advance_deck_draft_revision
        advance_deck_draft_revision(db, deck_id)
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def fork_voice(user_id: int, voice_id: str, target_deck_id: str) -> str:
    """
    Fork a voice to a user's deck.
    Returns new voice_id.
    """
    import uuid

    db = get_db()
    try:
        # Check target deck ownership
        deck = db.execute(
            "SELECT owner_id FROM decks WHERE id = %s FOR UPDATE",
            (target_deck_id,)
        ).fetchone()

        if not deck or deck['owner_id'] != user_id:
            raise ValueError("Target deck not found or permission denied")

        # Get source voice
        source_voice = db.execute("SELECT * FROM voices WHERE id = %s", (voice_id,)).fetchone()
        if not source_voice:
            raise ValueError(f"Voice {voice_id} not found")

        # Create new voice
        new_voice_id = str(uuid.uuid4())

        # Get max order_index in target deck
        max_order = db.execute(
            "SELECT MAX(order_index) as max_order FROM voices WHERE deck_id = %s",
            (target_deck_id,)
        ).fetchone()['max_order']
        order_index = (max_order or 0) + 1
        memory_config_json = source_voice["memory_workspace_config"] or _default_memory_workspace_config_json()

        db.execute("""
        INSERT INTO voices (id, deck_id, name, name_zh, name_en, system_prompt,
                           icon, color, is_system, parent_id, owner_id, enabled, order_index, memory_workspace_config)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (new_voice_id,
              target_deck_id,
              source_voice['name'],
              source_voice['name_zh'],
              source_voice['name_en'],
              source_voice['system_prompt'],
              source_voice['icon'],
              source_voice['color'],
              False,
              voice_id,  # parent_id tracks fork source
              user_id,
              True,
              order_index,
              memory_config_json))

        from services.deck.content_versioning import advance_deck_draft_revision
        advance_deck_draft_revision(db, target_deck_id)
        db.commit()
        return new_voice_id
    except Exception:
        db.rollback()
        raise
    finally:
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

# ========== Daily Pictures ==========

def save_daily_picture(user_id: int, date: str, image_base64: str, prompt: str = None, thumbnail_base64: str = None):
    """Save daily picture (replaces any existing picture for this user+date)."""
    db = get_db()
    try:
        # @@@ Delete old pictures for this user+date combination first
        # This ensures only ONE picture per day while avoiding UNIQUE constraint timezone issues
        db.execute("""
        DELETE FROM daily_pictures
        WHERE user_id = %s AND date = %s
        """, (user_id, date))

        # Insert the new picture
        db.execute("""
        INSERT INTO daily_pictures (user_id, date, image_base64, thumbnail_base64, prompt)
        VALUES (%s, %s, %s, %s, %s)
        """, (user_id, date, image_base64, thumbnail_base64, prompt))

        db.commit()
    finally:
        db.close()

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
    """Get full resolution image for a friend's specific date if users are friends."""
    db = get_db()
    try:
        friendship = db.execute("""
        SELECT id FROM friendships
        WHERE status = 'accepted' AND (
          (user_id = %s AND friend_id = %s) OR
          (user_id = %s AND friend_id = %s)
        )
        """, (user_id, friend_id, friend_id, user_id)).fetchone()

        if not friendship:
            return None

        row = db.execute("""
        SELECT image_base64
        FROM daily_pictures
        WHERE user_id = %s AND date = %s
        ORDER BY created_at DESC
        LIMIT 1
        """, (friend_id, date)).fetchone()

        if row:
            return row['image_base64']
        return None
    finally:
        db.close()

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
    """Get per-user system config.

    Known keys include model/provider/system_prompt, workspace_enabled
    (file workspace + per-thread Bash sandbox), sandbox_network_mode,
    sandbox_network_allowed_domains, sandbox_fs_allowed_write_paths,
    im_full_access_enabled, theme, and env_vars.

    Returns an empty dict when no config has been saved yet.
    """
    db = get_db()
    try:
        row = db.execute(
            "SELECT system_config_json FROM user_preferences WHERE user_id = %s",
            (user_id,),
        ).fetchone()
        if row and row["system_config_json"]:
            return json.loads(row["system_config_json"])
        return {}
    finally:
        db.close()


def save_system_config(user_id: int, patch: dict) -> None:
    """Merge *patch* into the stored system config for *user_id*.

    Unknown keys are preserved so that future fields are not dropped on save.
    """
    db = get_db()
    try:
        existing = db.execute(
            "SELECT system_config_json FROM user_preferences WHERE user_id = %s",
            (user_id,),
        ).fetchone()
        if existing:
            current = json.loads(existing["system_config_json"]) if existing["system_config_json"] else {}
            current.update(patch)
            db.execute(
                "UPDATE user_preferences SET system_config_json = %s, updated_at = CURRENT_TIMESTAMP WHERE user_id = %s",
                (json.dumps(current), user_id),
            )
        else:
            db.execute(
                "INSERT INTO user_preferences (user_id, system_config_json) VALUES (%s, %s)",
                (user_id, json.dumps(patch)),
            )
        db.commit()
    finally:
        db.close()


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

def generate_invite_code(user_id: int) -> dict:
    """
    Generate a new friend invite code (6 chars, 7 days validity).
    Returns: {code, expires_at}
    """
    import random
    import string
    from datetime import datetime, timedelta

    db = get_db()
    try:
        # Generate unique 6-character code
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            # Check if code already exists and is not expired
            existing = db.execute(
                "SELECT code FROM friend_invites WHERE code = %s AND expires_at > CURRENT_TIMESTAMP",
                (code,)
            ).fetchone()
            if not existing:
                break

        expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        db.execute("""
        INSERT INTO friend_invites (code, user_id, expires_at)
        VALUES (%s, %s, %s)
        """, (code, user_id, expires_at))

        db.commit()
        return {"code": code, "expires_at": expires_at}
    finally:
        db.close()

def use_invite_code(code: str, requesting_user_id: int) -> dict:
    """
    Use an invite code to send a friend request.
    Returns: {success, friend_request_id, inviter_id, inviter_name} or {success: False, error}
    """
    from datetime import datetime

    db = get_db()
    try:
        # Validate invite code
        invite = db.execute("""
        SELECT user_id, expires_at, used_by
        FROM friend_invites
        WHERE code = %s
        """, (code,)).fetchone()

        if not invite:
            return {"success": False, "error": "Invalid invite code"}

        if invite['used_by']:
            return {"success": False, "error": "Invite code already used"}

        invite_expires_at = _parse_sql_datetime(invite['expires_at'])
        if invite_expires_at is None:
            return {"success": False, "error": "Invite code expired"}
        if invite_expires_at.tzinfo is None:
            invite_expires_at = invite_expires_at.replace(tzinfo=timezone.utc)
        if invite_expires_at < datetime.now(timezone.utc):
            return {"success": False, "error": "Invite code expired"}

        inviter_id = invite['user_id']

        if inviter_id == requesting_user_id:
            return {"success": False, "error": "Cannot add yourself as friend"}

        # Check if friendship already exists
        existing = db.execute("""
        SELECT id, status FROM friendships
        WHERE (user_id = %s AND friend_id = %s) OR (user_id = %s AND friend_id = %s)
        """, (requesting_user_id, inviter_id, inviter_id, requesting_user_id)).fetchone()

        if existing:
            if existing['status'] == 'accepted':
                return {"success": False, "error": "Already friends"}
            elif existing['status'] == 'pending':
                return {"success": False, "error": "Friend request already pending"}

        # Get inviter's display name
        inviter = db.execute(
            "SELECT display_name, email FROM users WHERE id = %s",
            (inviter_id,)
        ).fetchone()

        # Create friendship request (requesting_user sends request to inviter)
        cursor = db.execute("""
        INSERT INTO friendships (user_id, friend_id, status)
        VALUES (%s, %s, 'pending')
        RETURNING id
        """, (requesting_user_id, inviter_id))

        friend_request_id = int(cursor.fetchone()["id"])

        # Mark invite as used
        db.execute("""
        UPDATE friend_invites
        SET used_by = %s, used_at = CURRENT_TIMESTAMP
        WHERE code = %s
        """, (requesting_user_id, code))

        db.commit()

        return {
            "success": True,
            "friend_request_id": friend_request_id,
            "inviter_id": inviter_id,
            "inviter_name": inviter['display_name'] or inviter['email']
        }
    finally:
        db.close()

def get_friend_requests(user_id: int) -> list:
    """
    Get all pending friend requests FOR this user (others wanting to be friends).
    Returns: [{id, requester_id, requester_name, created_at}]
    """
    db = get_db()
    try:
        rows = db.execute("""
        SELECT f.id, f.user_id as requester_id, u.display_name, u.email, f.created_at
        FROM friendships f
        JOIN users u ON f.user_id = u.id
        WHERE f.friend_id = %s AND f.status = 'pending'
        ORDER BY f.created_at DESC
        """, (user_id,)).fetchall()

        return [{
            "id": row['id'],
            "requester_id": row['requester_id'],
            "requester_name": row['display_name'] or row['email'],
            "created_at": row['created_at']
        } for row in rows]
    finally:
        db.close()

def accept_friend_request(request_id: int, user_id: int) -> dict:
    """
    Accept a friend request. user_id must be the friend_id in the request.
    Returns: {success, error%s}
    """
    db = get_db()
    try:
        # Verify this request is for current user and is pending
        request = db.execute("""
        SELECT user_id, friend_id, status
        FROM friendships
        WHERE id = %s
        """, (request_id,)).fetchone()

        if not request:
            return {"success": False, "error": "Request not found"}

        if request['friend_id'] != user_id:
            return {"success": False, "error": "Permission denied"}

        if request['status'] != 'pending':
            return {"success": False, "error": f"Request already {request['status']}"}

        # Update status to accepted
        db.execute("""
        UPDATE friendships
        SET status = 'accepted', updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
        """, (request_id,))

        db.commit()
        return {"success": True}
    finally:
        db.close()

def reject_friend_request(request_id: int, user_id: int) -> dict:
    """
    Reject a friend request. user_id must be the friend_id in the request.
    Returns: {success, error%s}
    """
    db = get_db()
    try:
        # Verify this request is for current user and is pending
        request = db.execute("""
        SELECT user_id, friend_id, status
        FROM friendships
        WHERE id = %s
        """, (request_id,)).fetchone()

        if not request:
            return {"success": False, "error": "Request not found"}

        if request['friend_id'] != user_id:
            return {"success": False, "error": "Permission denied"}

        if request['status'] != 'pending':
            return {"success": False, "error": f"Request already {request['status']}"}

        # Update status to rejected
        db.execute("""
        UPDATE friendships
        SET status = 'rejected', updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
        """, (request_id,))

        db.commit()
        return {"success": True}
    finally:
        db.close()

def get_friends(user_id: int) -> list:
    """
    Get all accepted friends for this user.
    Returns: [{friend_id, friend_name, friend_email, since}]
    """
    db = get_db()
    try:
        # Get friends where I sent the request
        rows1 = db.execute("""
        SELECT f.friend_id as friend_id, u.display_name, u.email, f.updated_at
        FROM friendships f
        JOIN users u ON f.friend_id = u.id
        WHERE f.user_id = %s AND f.status = 'accepted'
        """, (user_id,)).fetchall()

        # Get friends where they sent the request
        rows2 = db.execute("""
        SELECT f.user_id as friend_id, u.display_name, u.email, f.updated_at
        FROM friendships f
        JOIN users u ON f.user_id = u.id
        WHERE f.friend_id = %s AND f.status = 'accepted'
        """, (user_id,)).fetchall()

        all_friends = []
        for row in rows1 + rows2:
            all_friends.append({
                "friend_id": row['friend_id'],
                "friend_name": row['display_name'] or row['email'],
                "friend_email": row['email'],
                "since": row['updated_at']
            })

        # Sort by most recent first
        all_friends.sort(key=lambda x: x['since'], reverse=True)

        return all_friends
    finally:
        db.close()

def remove_friend(user_id: int, friend_id: int) -> dict:
    """
    Remove a friend relationship.
    Returns: {success, error%s}
    """
    db = get_db()
    try:
        # Delete the friendship (bidirectional - delete either direction)
        result = db.execute("""
        DELETE FROM friendships
        WHERE status = 'accepted' AND (
          (user_id = %s AND friend_id = %s) OR
          (user_id = %s AND friend_id = %s)
        )
        """, (user_id, friend_id, friend_id, user_id))

        if result.rowcount == 0:
            return {"success": False, "error": "Friendship not found"}

        db.commit()
        return {"success": True}
    finally:
        db.close()

def get_friend_timeline(user_id: int, friend_id: int, limit: int = 30) -> list:
    """
    Get friend's timeline pictures (only if they are friends).
    Returns: [{date, base64, prompt, created_at}] or None if not friends
    """
    db = get_db()
    try:
        # Check if they are friends
        friendship = db.execute("""
        SELECT id FROM friendships
        WHERE status = 'accepted' AND (
          (user_id = %s AND friend_id = %s) OR
          (user_id = %s AND friend_id = %s)
        )
        """, (user_id, friend_id, friend_id, user_id)).fetchone()

        if not friendship:
            return None  # Not friends, no access

        # Get friend's timeline pictures (thumbnails)
        rows = db.execute("""
        SELECT date, COALESCE(thumbnail_base64, image_base64) as base64, prompt, created_at
        FROM daily_pictures
        WHERE user_id = %s
        ORDER BY date DESC
        LIMIT %s
        """, (friend_id, limit)).fetchall()

        return [{
            "date": row['date'],
            "base64": row['base64'],
            "prompt": row['prompt'],
            "created_at": row['created_at']
        } for row in rows]
    finally:
        db.close()

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

    db = get_db()
    try:
        inserted = db.execute(
            """
            INSERT INTO chat_message (id, thread_id, role, parts, metadata)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            RETURNING id
            """,
            (message_id, thread_id, role, parts_str, metadata_str),
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


def list_chat_messages(thread_id: str) -> list[dict]:
    """Return all messages for a thread in chronological order.

    Fully aligned with better-chatbot ChatRepository.selectMessagesByThreadId:
    returns ``parts`` as a parsed Python list and ``metadata`` as a parsed dict
    (or None) so callers receive UIMessage-compatible objects directly.
    """
    db = get_db()
    try:
        rows = db.execute(
            "SELECT id, role, parts, metadata, created_at FROM chat_message WHERE thread_id = %s ORDER BY created_at ASC",
            (thread_id,),
        ).fetchall()
        results = []
        for row in rows:
            m = dict(row)
            # Keep SQL NULL (a valid "no metadata" value) distinguishable
            # from a corrupt stored JSON envelope.  The HTTP projection uses
            # this internal flag to withhold message parts fail-closed; the
            # flag itself is never part of the client response allowlist.
            m["metadata_decode_error"] = False
            try:
                m["parts"] = json.loads(m["parts"]) if m["parts"] else []
            except Exception:
                m["parts"] = []
            if m.get("metadata"):
                try:
                    m["metadata"] = json.loads(m["metadata"])
                    if not isinstance(m["metadata"], dict):
                        # A stored JSON scalar/array (including literal null)
                        # is not the SQL NULL "no metadata" state.  Preserve
                        # that distinction so the client projection fails
                        # closed even when JSON decoding itself succeeds.
                        m["metadata_decode_error"] = True
                except Exception:
                    m["metadata"] = None
                    m["metadata_decode_error"] = True
            results.append(m)
        return results
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
    """Upsert user's custom prompt_files for *section*.

    ``prompt_files`` is a dict of ``{filename: content}`` for the five memory
    workspace prompt files.  Only known filenames are accepted by the route
    layer; this function stores whatever is provided without validation.
    """
    db = get_db()
    try:
        db.execute(
            """
            INSERT INTO reflections_section_configs (user_id, section, prompt_files, updated_at)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id, section) DO UPDATE SET
                prompt_files = excluded.prompt_files,
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, section, json.dumps(prompt_files, ensure_ascii=False)),
        )
        db.commit()
    finally:
        db.close()


def delete_reflections_section_config(user_id: int, section: str) -> bool:
    """Delete user's custom config for *section*, reverting to the static default.

    Returns True if a row was deleted, False if none existed.
    """
    db = get_db()
    try:
        cursor = db.execute(
            "DELETE FROM reflections_section_configs WHERE user_id = %s AND section = %s",
            (user_id, section),
        )
        db.commit()
        return cursor.rowcount > 0
    finally:
        db.close()


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
