#!/usr/bin/env python3
# [Input] Consume PostgreSQL connections, filesystem paths, JSON data, and optional session text extraction,
#         and memory workspace defaults.
# [Output] Provide persistence helpers for users, sessions, decks, voices, reports,
#          auth/OAuth state, Claude Agent threads/messages, and voice partition
#          Memory configs.
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
from typing import Optional, Union
import json
from psycopg import IntegrityError as PostgresIntegrityError
from psycopg.pq import TransactionStatus

try:
    from persistence.postgres import PostgresPool
except ModuleNotFoundError:  # pragma: no cover - package import compatibility
    from backend.persistence.postgres import PostgresPool

logger = logging.getLogger(__name__)


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
_DREAM_ALEMBIC_HEAD = "20260809_06"


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
    """Open PostgreSQL and fail closed unless Dream Alembic is at head.

    Runtime startup never creates, alters, seeds, or migrates schema.  Schema
    ownership belongs to the reviewed Dream Alembic command.
    """

    db = get_db()
    try:
        row = db.execute(
            "SELECT version_num FROM dream_alembic_version LIMIT 1"
        ).fetchone()
        if row is None or str(row["version_num"]) != _DREAM_ALEMBIC_HEAD:
            raise RuntimeError("Dream PostgreSQL schema is not at the required Alembic head")
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
    now = datetime.now(timezone.utc).isoformat()
    with db:
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
    """Seed system decks and voices. Idempotent - safe to call multiple times."""
    db = get_db()

    # Check if already seeded
    existing = db.execute("SELECT COUNT(*) FROM decks WHERE is_system IS TRUE").fetchone()[0]
    if existing > 0:
        print("⏭️  System decks already seeded, skipping")
        db.close()
        return

    print("🌱 Seeding system decks...")

    # ========== Deck 1: Introspection Deck ==========
    db.execute("""
    INSERT INTO decks (id, name, name_zh, name_en, description, description_zh, description_en, icon, color, is_system, enabled, has_local_changes, order_index)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, ('introspection_deck', '内省卡组', '内省卡组', 'Introspection Deck',
          '内心对话原型', '内心对话原型', 'Inner dialogue archetypes',
          'brain', 'purple', True, True, False, 0))

    # Import config to get existing voice prompts
    import config
    memory_config_json = _default_memory_workspace_config_json()

    # Introspection voices (from existing VOICE_ARCHETYPES)
    introspection_voices = [
        ('holder', config.VOICE_ARCHETYPES['holder']['name'], '接纳者', 'The Holder',
         config.VOICE_ARCHETYPES['holder']['systemPrompt'], 'heart', 'pink', 0),
        ('starter', config.VOICE_ARCHETYPES['starter']['name'], '启动者', 'The Starter',
         config.VOICE_ARCHETYPES['starter']['systemPrompt'], 'fist', 'yellow', 1),
        ('mirror', config.VOICE_ARCHETYPES['mirror']['name'], '照镜者', 'The Mirror',
         config.VOICE_ARCHETYPES['mirror']['systemPrompt'], 'eye', 'green', 2),
        ('weaver', config.VOICE_ARCHETYPES['weaver']['name'], '连接者', 'The Weaver',
         config.VOICE_ARCHETYPES['weaver']['systemPrompt'], 'compass', 'purple', 3),
        ('absurdist', config.VOICE_ARCHETYPES['absurdist']['name'], '幽默者', 'The Absurdist',
         config.VOICE_ARCHETYPES['absurdist']['systemPrompt'], 'masks', 'pink', 4),
    ]

    for voice_id, name, name_zh, name_en, prompt, icon, color, order in introspection_voices:
        db.execute("""
        INSERT INTO voices (id, deck_id, name, name_zh, name_en, system_prompt, icon, color, is_system, enabled, has_local_changes, order_index, memory_workspace_config)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, FALSE, %s, %s)
        """, (voice_id, 'introspection_deck', name, name_zh, name_en, prompt, icon, color, True, True, order, memory_config_json))

    # ========== Deck 2: Scholar Deck ==========
    db.execute("""
    INSERT INTO decks (id, name, name_zh, name_en, description, description_zh, description_en, icon, color, is_system, enabled, has_local_changes, order_index)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, ('scholar_deck', '学者卡组', '学者卡组', 'Scholar Deck',
          '从学术角度分析思考', '从学术角度分析思考', 'Analyze from academic perspectives',
          'lightbulb', 'blue', True, True, False, 1))

    # Scholar voices (placeholder prompts - TODO: write detailed prompts)
    scholar_voices = [
        ('linguist', '语言学家', '语言学家', 'Linguist',
         'Analyze from linguistic structure, semantics, and pragmatics.', 'compass', 'blue', 0),
        ('painter', '画家', '画家', 'Painter',
         'Analyze from aesthetics, visual imagery, and mood.', 'eye', 'pink', 1),
        ('physicist', '物理学家', '物理学家', 'Physicist',
         'Analyze using physics laws, mechanics, and energy.', 'lightbulb', 'yellow', 2),
        ('computer_scientist', '计算机科学家', '计算机科学家', 'Computer Scientist',
         'Analyze using algorithms, data structures, and complexity.', 'brain', 'purple', 3),
        ('doctor', '医生', '医生', 'Doctor',
         'Analyze from medical, physiological, and psychological health perspectives.', 'heart', 'pink', 4),
        ('historian', '历史学家', '历史学家', 'Historian',
         'Provide historical context, cultural background, and patterns.', 'compass', 'green', 5),
    ]

    for voice_id, name, name_zh, name_en, prompt, icon, color, order in scholar_voices:
        db.execute("""
        INSERT INTO voices (id, deck_id, name, name_zh, name_en, system_prompt, icon, color, is_system, enabled, has_local_changes, order_index, memory_workspace_config)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, FALSE, %s, %s)
        """, (voice_id, 'scholar_deck', name, name_zh, name_en, prompt, icon, color, True, True, order, memory_config_json))

    # ========== Deck 3: Philosophy Deck ==========
    db.execute("""
    INSERT INTO decks (id, name, name_zh, name_en, description, description_zh, description_en, icon, color, is_system, enabled, has_local_changes, order_index)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, ('philosophy_deck', '哲学卡组', '哲学卡组', 'Philosophy Deck',
          '不同哲学流派的审视', '不同哲学流派的审视', 'Examine through philosophical lenses',
          'cloud', 'purple', True, True, False, 2))

    # Philosophy voices (placeholder prompts - TODO: write detailed prompts)
    philosophy_voices = [
        ('stoic', '斯多葛派', '斯多葛派', 'Stoic',
         'Emphasize reason, self-control, and acceptance of the uncontrollable.', 'shield', 'blue', 0),
        ('taoist', '道家', '道家', 'Taoist',
         'Emphasize wu-wei (effortless action), natural flow, and simplicity.', 'wind', 'green', 1),
        ('existentialist', '存在主义者', '存在主义者', 'Existentialist',
         'Emphasize choice, freedom, responsibility, and creating meaning.', 'question', 'purple', 2),
        ('pragmatist', '实用主义者', '实用主义者', 'Pragmatist',
         'Focus on practical effects, usefulness, and real-world results.', 'fist', 'yellow', 3),
    ]

    for voice_id, name, name_zh, name_en, prompt, icon, color, order in philosophy_voices:
        db.execute("""
        INSERT INTO voices (id, deck_id, name, name_zh, name_en, system_prompt, icon, color, is_system, enabled, has_local_changes, order_index, memory_workspace_config)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, FALSE, %s, %s)
        """, (voice_id, 'philosophy_deck', name, name_zh, name_en, prompt, icon, color, True, True, order, memory_config_json))

    db.commit()
    db.close()
    print("✅ System decks seeded (3 decks, 15 voices)")

# ========== Deck CRUD ==========

def get_user_decks(user_id: int):
    """
    Get all user's own decks (forked from system templates).
    Returns list of deck dicts with voice counts.

    @@@ Users only see their own forked copies, never system decks directly
    """
    db = get_db()
    try:
        rows = db.execute("""
        SELECT d.*, COUNT(v.id) as voice_count
        FROM decks d
        LEFT JOIN voices v ON d.id = v.deck_id AND v.enabled IS TRUE
        WHERE d.owner_id = %s
        GROUP BY d.id
        ORDER BY d.order_index, d.created_at
        """, (user_id,)).fetchall()
        return [dict(row) for row in rows]
    finally:
        db.close()

def get_published_decks():
    """
    Get all published decks (community deck store).
    Returns list of deck dicts with voice counts and author info.
    """
    db = get_db()
    try:
        rows = db.execute("""
        SELECT d.*, COUNT(v.id) as voice_count, u.display_name as author_display_name
        FROM decks d
        LEFT JOIN voices v ON d.id = v.deck_id AND v.enabled IS TRUE
        LEFT JOIN users u ON d.owner_id = u.id
        WHERE d.published IS TRUE
        GROUP BY d.id
        ORDER BY d.install_count DESC, d.created_at DESC
        """).fetchall()
        return [dict(row) for row in rows]
    finally:
        db.close()

def publish_deck(deck_id: str, user_id: int):
    """
    Publish a deck to community store.
    @@@ Breaks parent chain - published deck becomes standalone
    """
    db = get_db()
    try:
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

        # Get voices in this deck
        voice_rows = db.execute("""
        SELECT * FROM voices
        WHERE deck_id = %s
        ORDER BY order_index, created_at
        """, (deck_id,)).fetchall()

        deck['voices'] = [_parse_voice_row(dict(row)) for row in voice_rows]
        return deck
    finally:
        db.close()

def create_deck(user_id: int, name: str, description: str = None,
                name_zh: str = None, name_en: str = None,
                description_zh: str = None, description_en: str = None,
                icon: str = None, color: str = None,
                order_index: int = None) -> str:
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

        db.commit()
        return deck_id
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
        # Check ownership
        deck = db.execute(
            "SELECT owner_id FROM decks WHERE id = %s",
            (deck_id,)
        ).fetchone()

        if not deck or deck['owner_id'] != user_id:
            return False

        # Build update query
        allowed_fields = ['name', 'name_zh', 'name_en', 'description', 'description_zh',
                         'description_en', 'icon', 'color', 'enabled', 'order_index']
        content_fields = ['name', 'name_zh', 'name_en', 'description', 'description_zh',
                         'description_en', 'icon', 'color']

        update_fields = []
        params = []
        for field in allowed_fields:
            if field in updates:
                value = bool(updates[field]) if field == "enabled" else updates[field]
                update_fields.append(f"{field} = %s")
                params.append(value)

        if not update_fields:
            return True  # No updates

        # @@@ Mark as locally changed if content fields are modified
        has_content_change = any(field in updates for field in content_fields)
        if has_content_change:
            update_fields.append("has_local_changes = TRUE")

        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        params.append(deck_id)

        db.execute(
            f"UPDATE decks SET {', '.join(update_fields)} WHERE id = %s",
            params
        )
        db.commit()
        return True
    finally:
        db.close()

def delete_deck(user_id: int, deck_id: str) -> bool:
    """
    Delete a user's deck. Only works if user owns the deck.
    Cascades to delete all voices in the deck.
    Returns True if deleted, False if not found or permission denied.
    """
    db = get_db()
    try:
        # Check ownership
        deck = db.execute(
            "SELECT owner_id FROM decks WHERE id = %s",
            (deck_id,)
        ).fetchone()

        if not deck or deck['owner_id'] != user_id:
            return False

        db.execute("DELETE FROM decks WHERE id = %s", (deck_id,))
        db.commit()
        return True
    finally:
        db.close()

def auto_fork_system_decks(user_id: int):
    """
    Auto-fork all system decks for a new user.
    Called on user registration/first login.
    """
    # @@@ Get deck list then close connection BEFORE forking (avoid deadlock)
    db = get_db()
    try:
        system_decks = db.execute(
            "SELECT id FROM decks WHERE is_system IS TRUE ORDER BY order_index"
        ).fetchall()
        deck_ids = [deck['id'] for deck in system_decks]
    finally:
        db.close()

    # Fork each deck (each fork opens its own connection)
    # @@@ Only enable introspection deck by default
    for deck_id in deck_ids:
        should_enable = (deck_id == 'introspection_deck')
        fork_deck(user_id, deck_id, enabled=should_enable)

    print(f"✅ Auto-forked {len(deck_ids)} system decks for user {user_id}")

def fork_deck(user_id: int, deck_id: str, enabled: bool = True) -> str:
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
            "SELECT * FROM decks WHERE id = %s AND owner_id = %s",
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
    db = get_db()
    try:
        # Get all user's enabled decks
        enabled_decks = db.execute("""
        SELECT id FROM decks
        WHERE owner_id = %s AND enabled IS TRUE
        ORDER BY order_index, created_at
        """, (user_id,)).fetchall()

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
            "SELECT owner_id FROM decks WHERE id = %s",
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

        db.commit()
        return voice_id
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
        # Check ownership
        voice = db.execute(
            "SELECT owner_id FROM voices WHERE id = %s",
            (voice_id,)
        ).fetchone()

        if not voice or voice['owner_id'] != user_id:
            return False

        # Build update query
        allowed_fields = ['name', 'name_zh', 'name_en', 'system_prompt',
                         'icon', 'color', 'enabled', 'order_index', 'thread_id',
                         'memory_workspace_config']
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
                    value = json.dumps(value, ensure_ascii=False)
                update_fields.append(f"{field} = %s")
                params.append(value)

        if not update_fields:
            return True  # No updates

        # @@@ Mark as locally changed if content fields are modified
        has_content_change = any(field in updates for field in content_fields)
        if has_content_change:
            update_fields.append("has_local_changes = TRUE")

        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        params.append(voice_id)

        db.execute(
            f"UPDATE voices SET {', '.join(update_fields)} WHERE id = %s",
            params
        )
        db.commit()
        return True
    finally:
        db.close()

def delete_voice(user_id: int, voice_id: str) -> bool:
    """
    Delete a user's voice. Only works if user owns the voice.
    Returns True if deleted, False if not found or permission denied.
    """
    db = get_db()
    try:
        # Check ownership
        voice = db.execute(
            "SELECT owner_id FROM voices WHERE id = %s",
            (voice_id,)
        ).fetchone()

        if not voice or voice['owner_id'] != user_id:
            return False

        db.execute("DELETE FROM voices WHERE id = %s", (voice_id,))
        db.commit()
        return True
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
            "SELECT owner_id FROM decks WHERE id = %s",
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
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0, %s, %s, 1, %s, %s)
        """, (new_voice_id,
              target_deck_id,
              source_voice['name'],
              source_voice['name_zh'],
              source_voice['name_en'],
              source_voice['system_prompt'],
              source_voice['icon'],
              source_voice['color'],
              voice_id,  # parent_id tracks fork source
              user_id,
              order_index,
              memory_config_json))

        db.commit()
        return new_voice_id
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
    """Create a new user. Returns user_id."""
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
        db.commit()
        return user_id
    except PostgresIntegrityError:
        db.rollback()
        raise ValueError("Email already exists")
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
    """Save or update user preferences."""
    db = get_db()
    try:
        # Check if preferences exist
        existing = db.execute("SELECT user_id FROM user_preferences WHERE user_id = %s", (user_id,)).fetchone()

        if existing:
            # Update
            updates = []
            params = []
            if voice_configs is not None:
                updates.append("voice_configs_json = %s")
                params.append(json.dumps(voice_configs))
            if meta_prompt is not None:
                updates.append("meta_prompt = %s")
                params.append(meta_prompt)
            if state_config is not None:
                updates.append("state_config_json = %s")
                params.append(json.dumps(state_config))
            if selected_state is not None:
                updates.append("selected_state = %s")
                params.append(selected_state)
            if timezone is not None:
                updates.append("timezone = %s")
                params.append(timezone)

            if updates:
                updates.append("updated_at = CURRENT_TIMESTAMP")
                params.append(user_id)
                db.execute(f"UPDATE user_preferences SET {', '.join(updates)} WHERE user_id = %s", params)
        else:
            # Insert
            db.execute("""
            INSERT INTO user_preferences (user_id, voice_configs_json, meta_prompt, state_config_json, selected_state, timezone)
            VALUES (%s, %s, %s, %s, %s, %s)
            """, (user_id,
                  json.dumps(voice_configs) if voice_configs else None,
                  meta_prompt,
                  json.dumps(state_config) if state_config else None,
                  selected_state,
                  timezone))

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


def bind_chat_thread_voice(thread_id: str, user_id: int, voice_id: str) -> bool:
    """Bind one Agent once; an existing conversation cannot switch persona."""
    db = get_db()
    try:
        cursor = db.execute(
            """
            UPDATE chat_thread
            SET voice_id = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND user_id = %s AND voice_id IS NULL
            """,
            (voice_id, thread_id, user_id),
        )
        db.commit()
        if cursor.rowcount == 1:
            return True
        row = db.execute(
            "SELECT voice_id FROM chat_thread WHERE id = %s AND user_id = %s",
            (thread_id, user_id),
        ).fetchone()
        return bool(row and row["voice_id"] == voice_id)
    finally:
        db.close()


def list_chat_threads(user_id: int, limit: Optional[int] = None, offset: int = 0) -> list[dict]:
    """List chat threads for a user, newest first, optionally paged."""
    db = get_db()
    try:
        if limit is not None:
            rows = db.execute(
                """
                SELECT id, title, deck_id, voice_id, created_at, updated_at
                FROM chat_thread
                WHERE user_id = %s
                ORDER BY updated_at DESC
                LIMIT %s OFFSET %s
                """,
                (user_id, limit, max(0, offset)),
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT id, title, deck_id, voice_id, created_at, updated_at FROM chat_thread WHERE user_id = %s ORDER BY updated_at DESC",
                (user_id,),
            ).fetchall()
        return [dict(row) for row in rows]
    finally:
        db.close()


def list_chat_threads_for_search(user_id: int) -> list[dict]:
    """List chat thread search candidates with aggregated message text."""
    db = get_db()
    try:
        rows = db.execute(
            """
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
            WHERE t.user_id = %s
            ORDER BY t.updated_at DESC, m.created_at ASC
            """,
            (user_id,),
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
    """Persist one chat message. Returns the message_id.

    Fully aligned with better-chatbot ChatMessageTable — no ``content`` column.
    Text lives inside ``parts`` as ``{type: "text", text: "..."}`` entries.

      - ``parts``    list[dict] — UIMessage['parts'] array; required; serialized internally.
      - ``metadata`` dict       — ChatMetadata (usage / chatModel / toolCount); nullable.
      - ``message_id`` — AI-SDK message.id from the frontend; auto-generated if omitted.
    """
    import uuid
    if not message_id:
        message_id = str(uuid.uuid4())

    # Resolve parts: prefer list param, fall back to deprecated string param.
    if parts_json is not None and not parts:
        parts_str = parts_json
    else:
        parts_str = json.dumps(parts, ensure_ascii=False)

    # Resolve metadata: prefer dict param, fall back to deprecated string param.
    if metadata is not None:
        metadata_str: Optional[str] = json.dumps(metadata, ensure_ascii=False)
    elif metadata_json is not None:
        metadata_str = metadata_json
    else:
        metadata_str = None

    db = get_db()
    try:
        db.execute(
            """
            INSERT INTO chat_message (id, thread_id, role, parts, metadata)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
              thread_id = excluded.thread_id,
              role = excluded.role,
              parts = excluded.parts,
              metadata = excluded.metadata
            """,
            (message_id, thread_id, role, parts_str, metadata_str),
        )
        _touch_chat_thread(db, thread_id)
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
            try:
                m["parts"] = json.loads(m["parts"]) if m["parts"] else []
            except Exception:
                m["parts"] = []
            if m.get("metadata"):
                try:
                    m["metadata"] = json.loads(m["metadata"])
                except Exception:
                    m["metadata"] = None
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
