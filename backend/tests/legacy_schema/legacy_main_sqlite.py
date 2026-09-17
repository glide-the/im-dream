#!/usr/bin/env python3
"""Migration-only builders for the historical Dream SQLite schema.

This module is deliberately isolated from ``database`` so the Dream runtime
cannot open, initialize, or fall back to SQLite.  It exists only to reproduce
the audited 43-table source contract used by manifest generation and offline
migration rehearsal.
"""

from __future__ import annotations

import json
import logging
import sqlite3

logger = logging.getLogger(__name__)


def _default_memory_workspace_config() -> dict:
    from memory_workspace_defaults import default_memory_workspace_config

    return default_memory_workspace_config()


def _default_memory_workspace_config_json() -> str:
    return json.dumps(_default_memory_workspace_config(), ensure_ascii=False)


def _backfill_default_memory_workspace_config(db) -> None:
    """Backfill voices that predate voices.memory_workspace_config.

    This writes the default config into the partition table so runtime Memory
    workspace initialization still reads from ``voices.memory_workspace_config``
    rather than from project template files.
    """

    try:
        db.execute(
            """
            UPDATE voices
            SET memory_workspace_config = ?
            WHERE memory_workspace_config IS NULL OR TRIM(memory_workspace_config) = ''
            """,
            (_default_memory_workspace_config_json(),),
        )
        db.commit()
    except Exception as exc:
        logger.warning("Memory workspace config backfill skipped: %s", exc)

_STORY_WORKSPACE_REVIEW_COLUMNS = (
    (
        "status",
        "TEXT NOT NULL DEFAULT 'active' "
        "CHECK(status IN ('active', 'archived'))",
        "TEXT",
        True,
        "'active'",
    ),
    (
        "review_notes",
        "TEXT CHECK(review_notes IS NULL OR length(review_notes) <= 2000)",
        "TEXT",
        False,
        None,
    ),
    ("confirmed_at", "DATETIME", "DATETIME", False, None),
    ("archived_at", "DATETIME", "DATETIME", False, None),
)


def _migrate_story_workspace_review_persistence(db):
    """Add and verify the character/scene review-persistence columns."""

    tables = ("story_workspace_characters", "story_workspace_scenes")
    savepoint = "story_workspace_review_persistence"
    db.execute(f"SAVEPOINT {savepoint}")
    try:
        for table in tables:
            existing = {
                row[1] for row in db.execute(f"PRAGMA table_info({table})").fetchall()
            }
            for column, declaration, _, _, _ in _STORY_WORKSPACE_REVIEW_COLUMNS:
                if column not in existing:
                    db.execute(
                        f"ALTER TABLE {table} ADD COLUMN {column} {declaration}"
                    )

        for table in tables:
            columns = {
                row[1]: row
                for row in db.execute(f"PRAGMA table_info({table})").fetchall()
            }
            for column, _, expected_type, expected_not_null, expected_default in (
                _STORY_WORKSPACE_REVIEW_COLUMNS
            ):
                row = columns.get(column)
                if row is None:
                    raise RuntimeError(f"{table}.{column} migration did not complete")
                actual = (row[2].upper(), bool(row[3]), row[4])
                expected = (expected_type, expected_not_null, expected_default)
                if actual != expected:
                    raise RuntimeError(
                        f"{table}.{column} has incompatible schema: "
                        f"expected {expected}, got {actual}"
                    )

            table_sql_row = db.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?",
                (table,),
            ).fetchone()
            normalized_sql = " ".join(table_sql_row[0].lower().split())
            required_checks = (
                "check(status in ('active', 'archived'))",
                "check(review_notes is null or length(review_notes) <= 2000)",
            )
            if any(check not in normalized_sql for check in required_checks):
                raise RuntimeError(f"{table} review constraints are incomplete")

        db.execute(f"RELEASE SAVEPOINT {savepoint}")
    except Exception:
        db.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
        db.execute(f"RELEASE SAVEPOINT {savepoint}")
        raise


def create_event_tables(db):
    """Create the authoritative append-only canonical event audit store."""

    db.execute("""
    CREATE TABLE IF NOT EXISTS events (
      event_id TEXT PRIMARY KEY,
      event_type TEXT NOT NULL,
      event_version INTEGER NOT NULL CHECK(event_version >= 1),
      occurred_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      workspace_id TEXT NOT NULL,
      aggregate_id TEXT NOT NULL,
      aggregate_version INTEGER NOT NULL CHECK(aggregate_version >= 1),
      correlation_id TEXT NOT NULL,
      causation_id TEXT,
      payload_json TEXT NOT NULL,
      UNIQUE(aggregate_id, aggregate_version)
    )
    """)
    for index_sql in (
        "CREATE INDEX IF NOT EXISTS idx_events_aggregate "
        "ON events(aggregate_id, aggregate_version)",
        "CREATE INDEX IF NOT EXISTS idx_events_type "
        "ON events(event_type, occurred_at)",
        "CREATE INDEX IF NOT EXISTS idx_events_correlation "
        "ON events(correlation_id)",
    ):
        db.execute(index_sql)
    for trigger_name, operation in (
        ("events_no_update", "UPDATE"),
        ("events_no_delete", "DELETE"),
    ):
        db.execute(
            f"""
            CREATE TRIGGER IF NOT EXISTS {trigger_name}
            BEFORE {operation} ON events
            BEGIN
              SELECT RAISE(ABORT, 'events is append-only');
            END
            """
        )


def create_tables(db):
    """Create all database tables."""
    print("📦 Creating database tables...")

    create_event_tables(db)

    # Users table
    db.execute("""
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      email TEXT UNIQUE NOT NULL,
      password_hash TEXT NOT NULL,
      display_name TEXT,
      avatar_url TEXT,
      role TEXT DEFAULT 'user',
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    for column_sql in (
        "ALTER TABLE users ADD COLUMN avatar_url TEXT",
        "ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'",
        "ALTER TABLE users ADD COLUMN updated_at DATETIME",
    ):
        try:
            db.execute(column_sql)
        except Exception:
            pass
    db.execute(
        """
        UPDATE users
        SET updated_at = COALESCE(updated_at, created_at, CURRENT_TIMESTAMP),
            role = COALESCE(role, 'user')
        """
    )

    # User sessions (editor states)
    db.execute("""
    CREATE TABLE IF NOT EXISTS user_sessions (
      id TEXT PRIMARY KEY,
      user_id INTEGER NOT NULL,
      name TEXT,
      editor_state_json TEXT NOT NULL,
      labels TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    )
    """)
    db.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON user_sessions(user_id)")

    # Migration: add labels column for Agent-note collaboration (2026-05-31).
    try:
        db.execute("ALTER TABLE user_sessions ADD COLUMN labels TEXT")
    except Exception:
        pass

    # Daily pictures (generated images) - no UNIQUE constraint, allows multiple per day
    db.execute("""
    CREATE TABLE IF NOT EXISTS daily_pictures (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      date TEXT NOT NULL,
      image_base64 TEXT NOT NULL,
      prompt TEXT,
      thumbnail_base64 TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    )
    """)
    db.execute("CREATE INDEX IF NOT EXISTS idx_pictures_user_date ON daily_pictures(user_id, date)")

    # User preferences (voice configs, meta prompts, etc.)
    db.execute("""
    CREATE TABLE IF NOT EXISTS user_preferences (
      user_id INTEGER PRIMARY KEY,
      voice_configs_json TEXT,
      meta_prompt TEXT,
      state_config_json TEXT,
      selected_state TEXT,
      timezone TEXT,
      first_login_completed INTEGER DEFAULT 0,
      system_config_json TEXT,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    )
    """)

    try:
        db.execute("ALTER TABLE user_preferences ADD COLUMN timezone TEXT")
    except Exception:
        pass

    try:
        db.execute("ALTER TABLE user_preferences ADD COLUMN system_config_json TEXT")
    except Exception:
        pass

    # Auth sessions
    db.execute("""
    CREATE TABLE IF NOT EXISTS auth_sessions (
      token TEXT PRIMARY KEY,
      user_id INTEGER NOT NULL,
      expires_at DATETIME NOT NULL,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    )
    """)
    db.execute("CREATE INDEX IF NOT EXISTS idx_auth_user ON auth_sessions(user_id)")

    # OAuth account bindings. Google access/id/refresh tokens are optional and
    # must be encrypted by the caller before storage.
    db.execute("""
    CREATE TABLE IF NOT EXISTS oauth_accounts (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      provider TEXT NOT NULL,
      provider_sub TEXT NOT NULL,
      email TEXT NOT NULL,
      access_token_encrypted TEXT,
      refresh_token_encrypted TEXT,
      id_token_encrypted TEXT,
      expires_at DATETIME,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      UNIQUE(provider, provider_sub),
      FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    )
    """)
    db.execute("CREATE INDEX IF NOT EXISTS idx_oauth_accounts_user ON oauth_accounts(user_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_oauth_accounts_email ON oauth_accounts(email)")

    # Refresh tokens are opaque outside the server; only hashes are persisted.
    db.execute("""
    CREATE TABLE IF NOT EXISTS refresh_tokens (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      token_hash TEXT UNIQUE NOT NULL,
      expires_at DATETIME NOT NULL,
      revoked_at DATETIME,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    )
    """)
    db.execute("CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON refresh_tokens(user_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_refresh_tokens_expires ON refresh_tokens(expires_at)")

    # OAuth 2.0 Device Authorization Grant state.
    db.execute("""
    CREATE TABLE IF NOT EXISTS device_authorizations (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      client_id TEXT NOT NULL,
      device_code_hash TEXT UNIQUE NOT NULL,
      user_code_hash TEXT UNIQUE NOT NULL,
      user_id INTEGER,
      scope TEXT,
      status TEXT NOT NULL,
      interval_seconds INTEGER NOT NULL,
      last_poll_at DATETIME,
      expires_at DATETIME NOT NULL,
      approved_at DATETIME,
      consumed_at DATETIME,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    )
    """)
    db.execute("CREATE INDEX IF NOT EXISTS idx_device_authorizations_device_code_hash ON device_authorizations(device_code_hash)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_device_authorizations_user_code_hash ON device_authorizations(user_code_hash)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_device_authorizations_status_expires ON device_authorizations(status, expires_at)")

    # Analysis reports
    db.execute("""
    CREATE TABLE IF NOT EXISTS analysis_reports (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      report_type TEXT NOT NULL,
      report_data_json TEXT NOT NULL,
      all_notes_text TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    )
    """)
    db.execute("CREATE INDEX IF NOT EXISTS idx_reports_user ON analysis_reports(user_id, created_at)")

    # @@@ Decks table - organize voices into themed collections
    db.execute("""
    CREATE TABLE IF NOT EXISTS decks (
      id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      name_zh TEXT,
      name_en TEXT,
      description TEXT,
      description_zh TEXT,
      description_en TEXT,
      icon TEXT,
      color TEXT,
      is_system BOOLEAN DEFAULT 0,
      parent_id TEXT,
      owner_id INTEGER,
      enabled BOOLEAN DEFAULT 1,
      has_local_changes BOOLEAN DEFAULT 0,
      order_index INTEGER,
      published BOOLEAN DEFAULT 0,
      author_name TEXT,
      install_count INTEGER DEFAULT 0,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (parent_id) REFERENCES decks(id),
      FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)
    db.execute("CREATE INDEX IF NOT EXISTS idx_decks_owner ON decks(owner_id)")

    # @@@ Migration: Add publishing columns to existing decks table
    try:
        db.execute("ALTER TABLE decks ADD COLUMN published BOOLEAN DEFAULT 0")
    except:
        pass  # Column already exists
    try:
        db.execute("ALTER TABLE decks ADD COLUMN author_name TEXT")
    except:
        pass
    try:
        db.execute("ALTER TABLE decks ADD COLUMN install_count INTEGER DEFAULT 0")
    except:
        pass

    # @@@ Voices table - individual voice personas within decks
    db.execute("""
    CREATE TABLE IF NOT EXISTS voices (
      id TEXT PRIMARY KEY,
      deck_id TEXT NOT NULL,
      name TEXT NOT NULL,
      name_zh TEXT,
      name_en TEXT,
      system_prompt TEXT NOT NULL,
      icon TEXT,
      color TEXT,
      is_system BOOLEAN DEFAULT 0,
      parent_id TEXT,
      owner_id INTEGER,
      enabled BOOLEAN DEFAULT 1,
      has_local_changes BOOLEAN DEFAULT 0,
      order_index INTEGER,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (deck_id) REFERENCES decks(id) ON DELETE CASCADE,
      FOREIGN KEY (parent_id) REFERENCES voices(id),
      FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)
    db.execute("CREATE INDEX IF NOT EXISTS idx_voices_deck ON voices(deck_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_voices_owner ON voices(owner_id)")

    # @@@ Migration: add thread_id column for Claude-agent thread association
    try:
        db.execute("ALTER TABLE voices ADD COLUMN thread_id TEXT")
        db.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists

    # @@@ Migration: add memory_workspace_config column for per-voice memory workspace configuration
    try:
        db.execute("ALTER TABLE voices ADD COLUMN memory_workspace_config TEXT")
        db.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists
    _backfill_default_memory_workspace_config(db)

    # @@@ Friendships table - bidirectional friend relationships
    db.execute("""
    CREATE TABLE IF NOT EXISTS friendships (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      friend_id INTEGER NOT NULL,
      status TEXT NOT NULL CHECK(status IN ('pending', 'accepted', 'rejected')),
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
      FOREIGN KEY (friend_id) REFERENCES users (id) ON DELETE CASCADE,
      UNIQUE(user_id, friend_id)
    )
    """)
    db.execute("CREATE INDEX IF NOT EXISTS idx_friendships_user ON friendships(user_id, status)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_friendships_friend ON friendships(friend_id, status)")

    # @@@ Friend invites table - one-time invite codes
    db.execute("""
    CREATE TABLE IF NOT EXISTS friend_invites (
      code TEXT PRIMARY KEY,
      user_id INTEGER NOT NULL,
      expires_at DATETIME NOT NULL,
      used_by INTEGER,
      used_at DATETIME,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
      FOREIGN KEY (used_by) REFERENCES users (id) ON DELETE SET NULL
    )
    """)
    db.execute("CREATE INDEX IF NOT EXISTS idx_invites_user ON friend_invites(user_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_invites_expires ON friend_invites(expires_at)")

    # @@@ Claude Agent chat threads
    db.execute("""
    CREATE TABLE IF NOT EXISTS chat_thread (
      id TEXT PRIMARY KEY,
      user_id INTEGER NOT NULL,
      title TEXT,
      deck_id TEXT,
      voice_id TEXT,
      claude_session_id TEXT,
      agent_contract_version TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
      FOREIGN KEY (deck_id) REFERENCES decks (id) ON DELETE SET NULL,
      FOREIGN KEY (voice_id) REFERENCES voices (id) ON DELETE SET NULL
    )
    """)
    db.execute("CREATE INDEX IF NOT EXISTS idx_chat_thread_user ON chat_thread(user_id, updated_at)")
    # Migration: add Deck provenance and Claude resume fields.
    for _col, _type in (("deck_id", "TEXT"), ("voice_id", "TEXT"), ("claude_session_id", "TEXT"), ("agent_contract_version", "TEXT")):
        try:
            db.execute(f"ALTER TABLE chat_thread ADD COLUMN {_col} {_type}")
        except Exception:
            pass  # Column already exists

    # @@@ Claude Agent chat messages (one row per user/assistant turn)
    # Schema fully aligned with better-chatbot ChatMessageTable (schema.pg.ts):
    #   id TEXT PK (AI-SDK message ID), thread_id FK, role, parts JSON array, metadata JSON, created_at
    # No `content` column — exactly matching better-chatbot where text lives inside parts[].text.
    db.execute("""
    CREATE TABLE IF NOT EXISTS chat_message (
      id TEXT PRIMARY KEY,
      thread_id TEXT NOT NULL,
      role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
      parts TEXT NOT NULL DEFAULT '[]',
      metadata TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (thread_id) REFERENCES chat_thread (id) ON DELETE CASCADE
    )
    """)
    db.execute("CREATE INDEX IF NOT EXISTS idx_chat_message_thread ON chat_message(thread_id, created_at)")
    # Migration: add metadata column for databases pre-dating this column.
    try:
        db.execute("ALTER TABLE chat_message ADD COLUMN metadata TEXT")
        db.commit()
    except sqlite3.OperationalError as exc:
        if "duplicate column name" not in str(exc).lower():
            logger.warning("Unexpected error adding metadata column: %s", exc)
    # Migration: add parts column (replaces parts_json) for databases pre-dating this column.
    # parts is NOT NULL with default '[]'; existing rows with parts_json data are backfilled below.
    try:
        db.execute("ALTER TABLE chat_message ADD COLUMN parts TEXT NOT NULL DEFAULT '[]'")
        db.commit()
    except sqlite3.OperationalError as exc:
        if "duplicate column name" not in str(exc).lower():
            logger.warning("Unexpected error adding parts column: %s", exc)
    # Backfill: copy parts_json → parts for rows that still have the old column populated.
    # For rows with no parts_json, build a text part from the content column if it exists.
    # Both columns (parts_json, content) may not exist on new or already-migrated DBs —
    # skip silently in that case, matching the pattern used by the DROP COLUMN blocks below.
    try:
        db.execute("""
            UPDATE chat_message
            SET parts = parts_json
            WHERE parts_json IS NOT NULL AND parts = '[]'
        """)
        db.commit()
    except sqlite3.OperationalError as exc:
        msg = str(exc).lower()
        if "no such column" not in msg and "unknown column" not in msg:
            logger.warning("Parts backfill migration warning (non-fatal): %s", exc)
    try:
        # content column may still exist on old DBs — use it as fallback text source.
        db.execute("""
            UPDATE chat_message
            SET parts = json_array(json_object('type', 'text', 'text', content))
            WHERE (parts_json IS NULL OR parts_json = '') AND parts = '[]'
              AND content IS NOT NULL
        """)
        db.commit()
    except sqlite3.OperationalError as exc:
        msg = str(exc).lower()
        if "no such column" not in msg and "unknown column" not in msg:
            logger.warning("Parts backfill migration warning (non-fatal): %s", exc)
    # Migration: drop legacy content column (not in better-chatbot schema).
    # SQLite supports DROP COLUMN since 3.35.0 (2021); skip gracefully on older builds.
    try:
        db.execute("ALTER TABLE chat_message DROP COLUMN content")
        db.commit()
    except sqlite3.OperationalError as exc:
        msg = str(exc).lower()
        if "no such column" in msg or "unknown column" in msg or "cannot drop" in msg:
            pass  # already dropped or not present on new DBs
        else:
            logger.warning("Drop content column warning (non-fatal): %s", exc)
    # Migration: drop legacy parts_json column (superseded by parts).
    try:
        db.execute("ALTER TABLE chat_message DROP COLUMN parts_json")
        db.commit()
    except sqlite3.OperationalError as exc:
        msg = str(exc).lower()
        if "no such column" in msg or "unknown column" in msg or "cannot drop" in msg:
            pass
        else:
            logger.warning("Drop parts_json column warning (non-fatal): %s", exc)

    # Story Workspace tables. Keep parent tables before their dependants so the
    # same migration works with foreign-key enforcement enabled.
    db.execute("""
    CREATE TABLE IF NOT EXISTS story_workspace_workspaces (
      id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      owner_id INTEGER NOT NULL,
      settings TEXT DEFAULT '{}',
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (owner_id) REFERENCES users (id)
    )
    """)

    db.execute("""
    CREATE TABLE IF NOT EXISTS story_workspace_stories (
      id TEXT PRIMARY KEY,
      identifier TEXT NOT NULL,
      title TEXT NOT NULL,
      description TEXT,
      status TEXT NOT NULL DEFAULT 'draft'
        CHECK(status IN ('draft', 'published', 'archived')),
      review_status TEXT NOT NULL DEFAULT 'pending'
        CHECK(review_status IN ('pending', 'confirmed', 'rejected')),
      type TEXT NOT NULL DEFAULT 'short'
        CHECK(type IN ('short', 'long', 'script', 'outline')),
      content TEXT,
      author_id INTEGER NOT NULL,
      workspace_id TEXT NOT NULL,
      character_count INTEGER NOT NULL DEFAULT 0,
      scene_count INTEGER NOT NULL DEFAULT 0,
      agent_generated INTEGER NOT NULL DEFAULT 1
        CHECK(agent_generated IN (0, 1)),
      agent_session_id TEXT,
      review_notes TEXT,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      confirmed_at DATETIME,
      published_at DATETIME,
      FOREIGN KEY (author_id) REFERENCES users (id),
      FOREIGN KEY (workspace_id) REFERENCES story_workspace_workspaces (id)
    )
    """)

    db.execute("""
    CREATE TABLE IF NOT EXISTS story_workspace_characters (
      id TEXT PRIMARY KEY,
      identifier TEXT NOT NULL,
      name TEXT NOT NULL,
      avatar_url TEXT,
      identity TEXT,
      personality TEXT,
      background TEXT,
      catchphrase TEXT,
      tags TEXT DEFAULT '[]',
      notes TEXT,
      author_id INTEGER NOT NULL,
      workspace_id TEXT NOT NULL,
      story_count INTEGER NOT NULL DEFAULT 0,
      review_status TEXT NOT NULL DEFAULT 'pending'
        CHECK(review_status IN ('pending', 'confirmed', 'rejected')),
      agent_generated INTEGER NOT NULL DEFAULT 1
        CHECK(agent_generated IN (0, 1)),
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      status TEXT NOT NULL DEFAULT 'active'
        CHECK(status IN ('active', 'archived')),
      review_notes TEXT
        CHECK(review_notes IS NULL OR length(review_notes) <= 2000),
      confirmed_at DATETIME,
      archived_at DATETIME,
      FOREIGN KEY (author_id) REFERENCES users (id),
      FOREIGN KEY (workspace_id) REFERENCES story_workspace_workspaces (id)
    )
    """)

    db.execute("""
    CREATE TABLE IF NOT EXISTS story_workspace_scenes (
      id TEXT PRIMARY KEY,
      identifier TEXT NOT NULL,
      name TEXT NOT NULL,
      description TEXT,
      story_id TEXT,
      author_id INTEGER NOT NULL,
      workspace_id TEXT NOT NULL,
      character_count INTEGER NOT NULL DEFAULT 0,
      order_index INTEGER NOT NULL DEFAULT 0,
      review_status TEXT NOT NULL DEFAULT 'pending'
        CHECK(review_status IN ('pending', 'confirmed', 'rejected')),
      agent_generated INTEGER NOT NULL DEFAULT 1
        CHECK(agent_generated IN (0, 1)),
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      status TEXT NOT NULL DEFAULT 'active'
        CHECK(status IN ('active', 'archived')),
      review_notes TEXT
        CHECK(review_notes IS NULL OR length(review_notes) <= 2000),
      confirmed_at DATETIME,
      archived_at DATETIME,
      FOREIGN KEY (story_id) REFERENCES story_workspace_stories (id),
      FOREIGN KEY (author_id) REFERENCES users (id),
      FOREIGN KEY (workspace_id) REFERENCES story_workspace_workspaces (id)
    )
    """)

    _migrate_story_workspace_review_persistence(db)

    db.execute("""
    CREATE TABLE IF NOT EXISTS story_workspace_story_characters (
      story_id TEXT NOT NULL,
      character_id TEXT NOT NULL,
      role_type TEXT,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (story_id, character_id),
      FOREIGN KEY (story_id) REFERENCES story_workspace_stories (id),
      FOREIGN KEY (character_id) REFERENCES story_workspace_characters (id)
    )
    """)

    db.execute("""
    CREATE TABLE IF NOT EXISTS story_workspace_scene_characters (
      scene_id TEXT NOT NULL,
      character_id TEXT NOT NULL,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (scene_id, character_id),
      FOREIGN KEY (scene_id) REFERENCES story_workspace_scenes (id),
      FOREIGN KEY (character_id) REFERENCES story_workspace_characters (id)
    )
    """)

    story_workspace_indexes = (
        "CREATE INDEX IF NOT EXISTS idx_sw_workspaces_owner "
        "ON story_workspace_workspaces(owner_id)",
        "CREATE INDEX IF NOT EXISTS idx_sw_stories_author "
        "ON story_workspace_stories(author_id, updated_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_sw_stories_review_status "
        "ON story_workspace_stories(review_status, updated_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_sw_stories_status "
        "ON story_workspace_stories(status, updated_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_sw_stories_type "
        "ON story_workspace_stories(type, updated_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_sw_stories_search "
        "ON story_workspace_stories(title)",
        "CREATE INDEX IF NOT EXISTS idx_sw_stories_agent "
        "ON story_workspace_stories(agent_session_id)",
        "CREATE INDEX IF NOT EXISTS idx_sw_characters_author "
        "ON story_workspace_characters(author_id, updated_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_sw_characters_name "
        "ON story_workspace_characters(name)",
        "CREATE INDEX IF NOT EXISTS idx_sw_characters_review "
        "ON story_workspace_characters(review_status, updated_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_sw_scenes_story "
        "ON story_workspace_scenes(story_id, order_index)",
        "CREATE INDEX IF NOT EXISTS idx_sw_scenes_author "
        "ON story_workspace_scenes(author_id, updated_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_sw_scenes_review "
        "ON story_workspace_scenes(review_status, updated_at DESC)",
    )
    for index_sql in story_workspace_indexes:
        db.execute(index_sql)

    # Versioned Deck Plugin workflow manifests. Published manifest content is
    # immutable; lifecycle changes are recorded in the separate status column.
    db.execute("""
    CREATE TABLE IF NOT EXISTS deck_plugin_releases (
      id TEXT PRIMARY KEY,
      deck_plugin_id TEXT NOT NULL,
      deck_plugin_version TEXT NOT NULL,
      display_name TEXT NOT NULL,
      description TEXT,
      author TEXT,
      status TEXT NOT NULL DEFAULT 'draft'
        CHECK(status IN ('draft', 'validating', 'published', 'deprecated', 'revoked')),
      manifest_json TEXT NOT NULL,
      manifest_hash TEXT NOT NULL,
      workflow_definition_ref TEXT NOT NULL,
      input_schema_ref TEXT,
      output_schema_ref TEXT,
      capabilities_json TEXT,
      compatibility_json TEXT,
      deck_runtime_contract_json TEXT,
      runtime_spec_json TEXT,
      dependencies_json TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      published_at DATETIME,
      UNIQUE(deck_plugin_id, deck_plugin_version)
    )
    """)
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_deck_plugin_releases_id_version "
        "ON deck_plugin_releases(deck_plugin_id, deck_plugin_version)"
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_deck_plugin_releases_status "
        "ON deck_plugin_releases(status)"
    )

    # Immutable runtime dependency resolution for a published Deck Plugin release.
    db.execute("""
    CREATE TABLE IF NOT EXISTS deck_runtime_plugin_locks (
      id TEXT PRIMARY KEY,
      deck_plugin_id TEXT NOT NULL,
      deck_plugin_version TEXT NOT NULL,
      deck_plugin_manifest_hash TEXT NOT NULL,
      lock_json TEXT NOT NULL,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      UNIQUE(deck_plugin_id, deck_plugin_version),
      FOREIGN KEY (deck_plugin_id, deck_plugin_version)
        REFERENCES deck_plugin_releases(deck_plugin_id, deck_plugin_version)
        ON DELETE RESTRICT
    )
    """)
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_runtime_locks_deck_plugin "
        "ON deck_runtime_plugin_locks(deck_plugin_id, deck_plugin_version)"
    )

    # Deck-domain installation control plane. Runtime cache/materialization state
    # remains separate; pending columns only coordinate an atomic version switch.
    db.execute("""
    CREATE TABLE IF NOT EXISTS deck_plugin_installations (
      id TEXT PRIMARY KEY,
      scope_type TEXT NOT NULL
        CHECK(scope_type IN ('instance', 'workspace')),
      scope_id TEXT NOT NULL,
      deck_plugin_id TEXT NOT NULL,
      installed_versions_json TEXT NOT NULL DEFAULT '[]',
      default_version TEXT,
      status TEXT NOT NULL DEFAULT 'installing'
        CHECK(status IN (
          'installing', 'ready', 'disabled', 'error',
          'upgrade_pending', 'uninstalled'
        )),
      approved_capabilities_json TEXT NOT NULL DEFAULT '[]',
      source_policy_id TEXT NOT NULL,
      last_error_code TEXT,
      last_error_summary TEXT,
      pending_version TEXT,
      pending_capabilities_json TEXT,
      revision INTEGER NOT NULL DEFAULT 0,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      UNIQUE(scope_type, scope_id, deck_plugin_id)
    )
    """)
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_installations_deck_plugin "
        "ON deck_plugin_installations(deck_plugin_id)"
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_installations_scope "
        "ON deck_plugin_installations(scope_type, scope_id)"
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_installations_status "
        "ON deck_plugin_installations(status)"
    )

    # Versioned next-run Deck Plugin bindings. Each update keeps the previous
    # revision as stale audit history and atomically creates one active revision.
    db.execute("""
    CREATE TABLE IF NOT EXISTS deck_plugin_bindings (
      deck_plugin_binding_id TEXT PRIMARY KEY,
      deck_id TEXT NOT NULL,
      workspace_id TEXT NOT NULL,
      creator_id TEXT NOT NULL,
      deck_plugin_id TEXT NOT NULL,
      deck_plugin_version TEXT NOT NULL,
      binding_revision INTEGER NOT NULL CHECK(binding_revision >= 1),
      status TEXT NOT NULL DEFAULT 'active'
        CHECK(status IN ('active', 'stale')),
      applied_to TEXT NOT NULL DEFAULT 'next_run'
        CHECK(applied_to = 'next_run'),
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      UNIQUE(deck_id, binding_revision),
      FOREIGN KEY (deck_id) REFERENCES decks(id) ON DELETE RESTRICT,
      FOREIGN KEY (deck_plugin_id, deck_plugin_version)
        REFERENCES deck_plugin_releases(deck_plugin_id, deck_plugin_version)
        ON DELETE RESTRICT
    )
    """)
    db.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_deck_plugin_bindings_active_deck "
        "ON deck_plugin_bindings(deck_id) WHERE status = 'active'"
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_deck_plugin_bindings_deck_revision "
        "ON deck_plugin_bindings(deck_id, binding_revision DESC)"
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_deck_plugin_bindings_workspace "
        "ON deck_plugin_bindings(workspace_id, updated_at DESC)"
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_deck_plugin_bindings_release "
        "ON deck_plugin_bindings(deck_plugin_id, deck_plugin_version)"
    )

    # Deck-owned immutable runtime snapshots. Story Workspace receives only the
    # snapshot identifier and sanitized summary hash during preflight.
    db.execute("""
    CREATE TABLE IF NOT EXISTS deck_runtime_snapshots (
      deck_runtime_snapshot_id TEXT PRIMARY KEY,
      deck_id TEXT NOT NULL,
      deck_plugin_binding_id TEXT NOT NULL,
      binding_revision INTEGER NOT NULL CHECK(binding_revision >= 1),
      deck_runtime_profile_id TEXT NOT NULL,
      snapshot_contract TEXT NOT NULL,
      config_hash TEXT NOT NULL,
      config_json TEXT NOT NULL,
      sanitized_summary_hash TEXT NOT NULL,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      UNIQUE(deck_id, binding_revision, deck_runtime_profile_id, config_hash),
      FOREIGN KEY (deck_id) REFERENCES decks(id) ON DELETE RESTRICT,
      FOREIGN KEY (deck_plugin_binding_id)
        REFERENCES deck_plugin_bindings(deck_plugin_binding_id) ON DELETE RESTRICT
    )
    """)
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_deck_runtime_snapshots_deck "
        "ON deck_runtime_snapshots(deck_id, binding_revision, created_at DESC)"
    )
    for trigger_name, operation in (
        ("deck_runtime_snapshots_no_update", "UPDATE"),
        ("deck_runtime_snapshots_no_delete", "DELETE"),
    ):
        db.execute(
            f"""
            CREATE TRIGGER IF NOT EXISTS {trigger_name}
            BEFORE {operation} ON deck_runtime_snapshots
            BEGIN
              SELECT RAISE(ABORT, 'deck_runtime_snapshots is append-only');
            END
            """
        )

    # Story Workspace owns only the preflight record. Deck remains the single
    # owner of immutable runtime snapshots; this table stores the controlled ID
    # and a sanitized summary hash, never prompt, secret, or runtime config data.
    db.execute("""
    CREATE TABLE IF NOT EXISTS workflow_preflights (
      workflow_preflight_id TEXT PRIMARY KEY,
      request_fingerprint TEXT NOT NULL,
      deck_id TEXT NOT NULL,
      binding_revision INTEGER NOT NULL CHECK(binding_revision >= 0),
      deck_plugin_id TEXT NOT NULL,
      deck_plugin_version TEXT NOT NULL,
      runtime_plugin_lock_id TEXT NOT NULL,
      deck_runtime_profile_id TEXT NOT NULL,
      deck_runtime_snapshot_id TEXT,
      deck_runtime_snapshot_summary_hash TEXT,
      input_hash TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'checking'
        CHECK(status IN ('checking', 'passed', 'failed', 'expired')),
      error_code TEXT,
      failed_check TEXT,
      expires_at DATETIME NOT NULL,
      preflight_token_hash TEXT UNIQUE,
      consumed_at DATETIME,
      created_by TEXT NOT NULL,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      CHECK(
        (status = 'failed' AND error_code IS NOT NULL AND failed_check IS NOT NULL)
        OR
        (status != 'failed' AND error_code IS NULL AND failed_check IS NULL)
      )
    )
    """)
    db.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_workflow_preflights_active_request "
        "ON workflow_preflights(request_fingerprint) "
        "WHERE status IN ('checking', 'passed') AND consumed_at IS NULL"
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_workflow_preflights_deck_revision "
        "ON workflow_preflights(deck_id, binding_revision)"
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_workflow_preflights_status_expiry "
        "ON workflow_preflights(status, expires_at)"
    )

    # Reflections section configs — per-user custom prompt files for each section.
    # Falls back to reflections_config.py defaults when no row exists.
    db.execute("""
    CREATE TABLE IF NOT EXISTS reflections_section_configs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      section TEXT NOT NULL CHECK(section IN ('echoes', 'traits', 'patterns')),
      prompt_files TEXT NOT NULL DEFAULT '{}',
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      UNIQUE(user_id, section),
      FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    )
    """)
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_reflections_cfg_user "
        "ON reflections_section_configs(user_id, section)"
    )

    # Reflections-agent async task metadata.  The Reflections page should read
    # task/result truth from these tables instead of relying on frontend memory.
    db.execute("""
    CREATE TABLE IF NOT EXISTS reflection_task (
      id TEXT PRIMARY KEY,
      user_id INTEGER NOT NULL,
      status TEXT NOT NULL,
      sections TEXT NOT NULL DEFAULT '[]',
      input_snapshot TEXT NOT NULL DEFAULT '{}',
      workspace_path TEXT,
      agent_contract_version TEXT,
      error_summary TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      started_at DATETIME,
      completed_at DATETIME,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    )
    """)
    db.execute("CREATE INDEX IF NOT EXISTS idx_reflection_task_user ON reflection_task(user_id, updated_at)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_reflection_task_status ON reflection_task(status)")

    # Reflections-agent structured section results.
    db.execute("""
    CREATE TABLE IF NOT EXISTS reflection_result (
      id TEXT PRIMARY KEY,
      task_id TEXT NOT NULL,
      user_id INTEGER NOT NULL,
      section TEXT NOT NULL CHECK(section IN ('echoes', 'traits', 'patterns')),
      title TEXT NOT NULL,
      description TEXT NOT NULL,
      related_session_ids TEXT NOT NULL DEFAULT '[]',
      evidence TEXT,
      confidence TEXT NOT NULL CHECK(confidence IN ('high', 'medium', 'low')),
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (task_id) REFERENCES reflection_task (id) ON DELETE CASCADE,
      FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    )
    """)
    db.execute("CREATE INDEX IF NOT EXISTS idx_reflection_result_task ON reflection_result(task_id, section)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_reflection_result_user ON reflection_result(user_id, created_at)")

    # Reflections-agent lifecycle/event audit log, populated by the minimal
    # TaskPersistenceObserver.
    db.execute("""
    CREATE TABLE IF NOT EXISTS reflection_task_event (
      id TEXT PRIMARY KEY,
      task_id TEXT NOT NULL,
      sequence INTEGER,
      event_type TEXT NOT NULL,
      payload TEXT NOT NULL DEFAULT '{}',
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (task_id) REFERENCES reflection_task (id) ON DELETE CASCADE
    )
    """)
    db.execute("CREATE INDEX IF NOT EXISTS idx_reflection_task_event_task ON reflection_task_event(task_id, sequence, created_at)")
    db.commit()

    print("✅ Tables created")


def create_workflow_run_tables(db):
    """Create the run-owned schema when the Workflow Run service is enabled.

    Keeping this activation explicit preserves the Preflight/Binding contract:
    those services do not create pseudo run storage merely by initializing their
    own dependencies.
    """

    db.execute("""
    CREATE TABLE IF NOT EXISTS workflow_runs (
      id TEXT PRIMARY KEY,
      workspace_id TEXT NOT NULL,
      deck_plugin_id TEXT NOT NULL,
      deck_plugin_version TEXT NOT NULL,
      workflow_definition_ref TEXT NOT NULL,
      deck_runtime_snapshot_id TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'preflight'
        CHECK(status IN (
          'preflight', 'queued', 'running', 'output_validating',
          'pending_review', 'confirmed', 'rejected',
          'completed', 'failed', 'cancelled'
        )),
      failed_step TEXT,
      error_code TEXT,
      retry_of_run_id TEXT,
      deck_plugin_manifest_hash TEXT NOT NULL,
      deck_plugin_binding_id TEXT NOT NULL,
      binding_revision INTEGER NOT NULL CHECK(binding_revision >= 1),
      runtime_plugin_lock_id TEXT NOT NULL,
      runtime_load_receipt_id TEXT,
      workflow_preflight_id TEXT NOT NULL,
      agent_session_id TEXT,
      source_voice_thread_id TEXT,
      source_message_id TEXT,
      source_message_time DATETIME,
      idempotency_key TEXT NOT NULL,
      input_hash TEXT NOT NULL,
      semantic_fingerprint TEXT NOT NULL,
      status_version INTEGER NOT NULL DEFAULT 1 CHECK(status_version >= 1),
      created_by TEXT NOT NULL,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      started_at DATETIME,
      completed_at DATETIME,
      UNIQUE(workspace_id, created_by, idempotency_key),
      FOREIGN KEY (retry_of_run_id) REFERENCES workflow_runs(id) ON DELETE RESTRICT,
      FOREIGN KEY (deck_plugin_binding_id)
        REFERENCES deck_plugin_bindings(deck_plugin_binding_id) ON DELETE RESTRICT,
      FOREIGN KEY (runtime_plugin_lock_id)
        REFERENCES deck_runtime_plugin_locks(id) ON DELETE RESTRICT,
      FOREIGN KEY (workflow_preflight_id)
        REFERENCES workflow_preflights(workflow_preflight_id) ON DELETE RESTRICT
    )
    """)
    workflow_run_columns = {
        row[1] for row in db.execute("PRAGMA table_info(workflow_runs)").fetchall()
    }
    for column_name, column_type in (
        ("source_message_id", "TEXT"),
        ("source_message_time", "DATETIME"),
    ):
        if column_name not in workflow_run_columns:
            db.execute(
                f"ALTER TABLE workflow_runs ADD COLUMN {column_name} {column_type}"
            )
    db.execute("""
    CREATE TABLE IF NOT EXISTS workflow_run_token_consumptions (
      token_digest TEXT PRIMARY KEY,
      workflow_run_id TEXT NOT NULL,
      workflow_preflight_id TEXT NOT NULL,
      workspace_id TEXT NOT NULL,
      actor_id TEXT NOT NULL,
      idempotency_key TEXT NOT NULL,
      semantic_fingerprint TEXT NOT NULL,
      consumed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (workflow_run_id) REFERENCES workflow_runs(id) ON DELETE RESTRICT,
      FOREIGN KEY (workflow_preflight_id)
        REFERENCES workflow_preflights(workflow_preflight_id) ON DELETE RESTRICT
    )
    """)
    db.execute("""
    CREATE TABLE IF NOT EXISTS workflow_run_transitions (
      id TEXT PRIMARY KEY,
      workflow_run_id TEXT NOT NULL,
      transition_seq INTEGER NOT NULL CHECK(transition_seq >= 1),
      from_status TEXT,
      to_status TEXT NOT NULL,
      actor_id TEXT NOT NULL,
      reason_code TEXT,
      failed_step TEXT,
      error_code TEXT,
      occurred_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      UNIQUE(workflow_run_id, transition_seq),
      FOREIGN KEY (workflow_run_id) REFERENCES workflow_runs(id) ON DELETE RESTRICT
    )
    """)
    for index_sql in (
        "CREATE INDEX IF NOT EXISTS idx_workflow_runs_deck_plugin "
        "ON workflow_runs(deck_plugin_id, deck_plugin_version)",
        "CREATE INDEX IF NOT EXISTS idx_workflow_runs_status "
        "ON workflow_runs(status)",
        "CREATE INDEX IF NOT EXISTS idx_workflow_runs_idempotency "
        "ON workflow_runs(workspace_id, created_by, idempotency_key)",
        "CREATE INDEX IF NOT EXISTS idx_workflow_runs_retry "
        "ON workflow_runs(retry_of_run_id)",
        "CREATE INDEX IF NOT EXISTS idx_workflow_run_token_consumptions_run "
        "ON workflow_run_token_consumptions(workflow_run_id)",
        "CREATE INDEX IF NOT EXISTS idx_workflow_run_transitions_run "
        "ON workflow_run_transitions(workflow_run_id, transition_seq)",
    ):
        db.execute(index_sql)

    for trigger_name, table_name, operation in (
        ("workflow_run_token_consumptions_no_update", "workflow_run_token_consumptions", "UPDATE"),
        ("workflow_run_token_consumptions_no_delete", "workflow_run_token_consumptions", "DELETE"),
        ("workflow_run_transitions_no_update", "workflow_run_transitions", "UPDATE"),
        ("workflow_run_transitions_no_delete", "workflow_run_transitions", "DELETE"),
    ):
        db.execute(
            f"""
            CREATE TRIGGER IF NOT EXISTS {trigger_name}
            BEFORE {operation} ON {table_name}
            BEGIN
              SELECT RAISE(ABORT, '{table_name} is append-only');
            END
            """
        )

    db.execute("""
    CREATE TRIGGER IF NOT EXISTS workflow_runs_immutable_provenance
    BEFORE UPDATE ON workflow_runs
    WHEN OLD.id IS NOT NEW.id
      OR OLD.workspace_id IS NOT NEW.workspace_id
      OR OLD.deck_plugin_id IS NOT NEW.deck_plugin_id
      OR OLD.deck_plugin_version IS NOT NEW.deck_plugin_version
      OR OLD.workflow_definition_ref IS NOT NEW.workflow_definition_ref
      OR OLD.deck_runtime_snapshot_id IS NOT NEW.deck_runtime_snapshot_id
      OR OLD.retry_of_run_id IS NOT NEW.retry_of_run_id
      OR OLD.deck_plugin_manifest_hash IS NOT NEW.deck_plugin_manifest_hash
      OR OLD.deck_plugin_binding_id IS NOT NEW.deck_plugin_binding_id
      OR OLD.binding_revision IS NOT NEW.binding_revision
      OR OLD.runtime_plugin_lock_id IS NOT NEW.runtime_plugin_lock_id
      OR OLD.workflow_preflight_id IS NOT NEW.workflow_preflight_id
      OR OLD.source_voice_thread_id IS NOT NEW.source_voice_thread_id
      OR OLD.idempotency_key IS NOT NEW.idempotency_key
      OR OLD.input_hash IS NOT NEW.input_hash
      OR OLD.semantic_fingerprint IS NOT NEW.semantic_fingerprint
      OR OLD.created_by IS NOT NEW.created_by
      OR OLD.created_at IS NOT NEW.created_at
      OR (
        OLD.runtime_load_receipt_id IS NOT NEW.runtime_load_receipt_id
        AND NOT (
          OLD.runtime_load_receipt_id IS NULL
          AND NEW.runtime_load_receipt_id IS NOT NULL
          AND OLD.status = 'queued'
          AND NEW.status = 'running'
        )
      )
    BEGIN
      SELECT RAISE(ABORT, 'workflow run provenance is immutable');
    END
    """)
    db.execute("""
    CREATE TRIGGER IF NOT EXISTS workflow_runs_status_version_guard
    BEFORE UPDATE ON workflow_runs
    WHEN (
      OLD.status IS NOT NEW.status
      AND NEW.status_version != OLD.status_version + 1
    ) OR (
      OLD.status IS NEW.status
      AND NEW.status_version != OLD.status_version
    )
    BEGIN
      SELECT RAISE(ABORT, 'workflow run status_version mismatch');
    END
    """)
    db.execute("""
    CREATE TRIGGER IF NOT EXISTS workflow_runs_voice_source_insert_guard
    BEFORE INSERT ON workflow_runs
    WHEN (
      (NEW.source_voice_thread_id IS NOT NULL)
      + (NEW.source_message_id IS NOT NULL)
      + (NEW.source_message_time IS NOT NULL)
    ) NOT IN (0, 3)
    BEGIN
      SELECT RAISE(ABORT, 'Voice source requires thread, message, and time');
    END
    """)
    db.execute("""
    CREATE TRIGGER IF NOT EXISTS workflow_runs_voice_source_immutable
    BEFORE UPDATE ON workflow_runs
    WHEN OLD.source_voice_thread_id IS NOT NEW.source_voice_thread_id
      OR OLD.source_message_id IS NOT NEW.source_message_id
      OR OLD.source_message_time IS NOT NEW.source_message_time
    BEGIN
      SELECT RAISE(ABORT, 'workflow run Voice source is immutable');
    END
    """)
    db.commit()


def create_runtime_plugin_tables(db):
    """Append task_008 materialization, reconcile, and receipt storage."""

    create_workflow_run_tables(db)
    db.execute("""
    CREATE TABLE IF NOT EXISTS runtime_plugin_materializations (
      runtime_materialization_id TEXT PRIMARY KEY,
      runtime_environment_id TEXT NOT NULL,
      runtime_pool_id TEXT NOT NULL,
      runtime_node_id TEXT NOT NULL,
      claude_code_plugin_id TEXT NOT NULL,
      resolved_version TEXT NOT NULL,
      artifact_digest TEXT NOT NULL,
      materialized_digest TEXT,
      artifact_set_hash TEXT NOT NULL,
      policy_revision TEXT NOT NULL,
      declaration_status TEXT NOT NULL
        CHECK(declaration_status IN ('undeclared', 'declared', 'disabled')),
      materialization_status TEXT NOT NULL
        CHECK(materialization_status IN ('missing', 'materializing', 'materialized', 'failed')),
      activation_status TEXT NOT NULL
        CHECK(activation_status IN ('inactive', 'loadable', 'loaded', 'load_failed')),
      materialization_key TEXT NOT NULL UNIQUE,
      attempt_id TEXT NOT NULL,
      attempt_count INTEGER NOT NULL CHECK(attempt_count >= 1),
      verification_status TEXT
        CHECK(verification_status IS NULL OR verification_status IN ('verified', 'legacy_unverified')),
      signature_bundle_ref TEXT,
      retention_state TEXT,
      restore_source_ref TEXT,
      cache_ref TEXT,
      last_error TEXT,
      created_at DATETIME NOT NULL,
      updated_at DATETIME NOT NULL,
      CHECK(runtime_pool_id = runtime_environment_id)
    )
    """)
    db.execute("""
    CREATE TABLE IF NOT EXISTS runtime_plugin_reconcile_attempts (
      attempt_id TEXT PRIMARY KEY,
      workflow_run_id TEXT,
      reconcile_path TEXT NOT NULL CHECK(reconcile_path IN ('headless', 'cli')),
      claude_code_plugin_id TEXT,
      resolved_version TEXT,
      runtime_node_id TEXT,
      policy_revision TEXT NOT NULL,
      argv_json TEXT,
      timeout_seconds INTEGER,
      exit_code INTEGER,
      stdout_summary TEXT,
      stderr_summary TEXT,
      result_status TEXT NOT NULL CHECK(result_status IN ('succeeded', 'failed')),
      error_code TEXT,
      created_at DATETIME NOT NULL,
      FOREIGN KEY (workflow_run_id) REFERENCES workflow_runs(id) ON DELETE RESTRICT
    )
    """)
    db.execute("""
    CREATE TABLE IF NOT EXISTS runtime_load_receipts (
      receipt_id TEXT PRIMARY KEY,
      workflow_run_id TEXT NOT NULL,
      runtime_plugin_lock_id TEXT NOT NULL,
      runtime_plugin_lock_digest TEXT NOT NULL,
      runtime_environment_id TEXT NOT NULL,
      runtime_pool_id TEXT NOT NULL,
      distribution_mode TEXT NOT NULL CHECK(distribution_mode = 'local_persistent'),
      runtime_node_id TEXT NOT NULL,
      artifact_set_hash TEXT NOT NULL,
      policy_revision TEXT NOT NULL,
      deployment_tier TEXT NOT NULL CHECK(deployment_tier = 'local'),
      scope TEXT NOT NULL CHECK(scope = 'session'),
      readiness_state TEXT NOT NULL CHECK(readiness_state = 'session_loaded'),
      required_entries_ready INTEGER NOT NULL CHECK(required_entries_ready IN (0, 1)),
      created_at DATETIME NOT NULL,
      CHECK(runtime_pool_id = runtime_environment_id),
      FOREIGN KEY (workflow_run_id) REFERENCES workflow_runs(id) ON DELETE RESTRICT,
      FOREIGN KEY (runtime_plugin_lock_id)
        REFERENCES deck_runtime_plugin_locks(id) ON DELETE RESTRICT
    )
    """)
    db.execute("""
    CREATE TABLE IF NOT EXISTS runtime_load_receipt_entries (
      receipt_id TEXT NOT NULL,
      claude_code_plugin_id TEXT NOT NULL,
      resolved_version TEXT NOT NULL,
      artifact_digest TEXT NOT NULL,
      materialized_digest TEXT NOT NULL,
      verification_status TEXT NOT NULL
        CHECK(verification_status IN ('verified', 'legacy_unverified')),
      signature_bundle_ref TEXT,
      retention_state TEXT NOT NULL,
      restore_source_ref TEXT,
      required INTEGER NOT NULL CHECK(required IN (0, 1)),
      loaded_capabilities_json TEXT NOT NULL,
      load_status TEXT NOT NULL CHECK(load_status IN ('loaded', 'load_failed', 'skipped')),
      loaded_at DATETIME NOT NULL,
      PRIMARY KEY (receipt_id, claude_code_plugin_id),
      FOREIGN KEY (receipt_id) REFERENCES runtime_load_receipts(receipt_id)
        ON DELETE RESTRICT
    )
    """)

    for index_sql in (
        "CREATE INDEX IF NOT EXISTS idx_runtime_materializations_lookup "
        "ON runtime_plugin_materializations(runtime_environment_id, runtime_node_id, claude_code_plugin_id)",
        "CREATE INDEX IF NOT EXISTS idx_runtime_materializations_status "
        "ON runtime_plugin_materializations(materialization_status, activation_status)",
        "CREATE INDEX IF NOT EXISTS idx_runtime_reconcile_attempts_run "
        "ON runtime_plugin_reconcile_attempts(workflow_run_id, created_at)",
        "CREATE INDEX IF NOT EXISTS idx_runtime_load_receipts_run "
        "ON runtime_load_receipts(workflow_run_id, created_at)",
        "CREATE INDEX IF NOT EXISTS idx_runtime_load_receipts_placement "
        "ON runtime_load_receipts(runtime_environment_id, runtime_node_id)",
    ):
        db.execute(index_sql)

    for trigger_name, table_name, operation in (
        ("runtime_reconcile_attempts_no_update", "runtime_plugin_reconcile_attempts", "UPDATE"),
        ("runtime_reconcile_attempts_no_delete", "runtime_plugin_reconcile_attempts", "DELETE"),
        ("runtime_load_receipts_no_update", "runtime_load_receipts", "UPDATE"),
        ("runtime_load_receipts_no_delete", "runtime_load_receipts", "DELETE"),
        ("runtime_load_receipt_entries_no_update", "runtime_load_receipt_entries", "UPDATE"),
        ("runtime_load_receipt_entries_no_delete", "runtime_load_receipt_entries", "DELETE"),
    ):
        db.execute(
            f"""
            CREATE TRIGGER IF NOT EXISTS {trigger_name}
            BEFORE {operation} ON {table_name}
            BEGIN
              SELECT RAISE(ABORT, '{table_name} is append-only');
            END
            """
        )

    db.execute("""
    CREATE TRIGGER IF NOT EXISTS runtime_materializations_immutable_identity
    BEFORE UPDATE ON runtime_plugin_materializations
    WHEN OLD.runtime_materialization_id IS NOT NEW.runtime_materialization_id
      OR OLD.runtime_environment_id IS NOT NEW.runtime_environment_id
      OR OLD.runtime_pool_id IS NOT NEW.runtime_pool_id
      OR OLD.runtime_node_id IS NOT NEW.runtime_node_id
      OR OLD.claude_code_plugin_id IS NOT NEW.claude_code_plugin_id
      OR OLD.resolved_version IS NOT NEW.resolved_version
      OR OLD.artifact_digest IS NOT NEW.artifact_digest
      OR OLD.artifact_set_hash IS NOT NEW.artifact_set_hash
      OR OLD.policy_revision IS NOT NEW.policy_revision
      OR OLD.materialization_key IS NOT NEW.materialization_key
      OR OLD.created_at IS NOT NEW.created_at
    BEGIN
      SELECT RAISE(ABORT, 'runtime materialization identity is immutable');
    END
    """)
    db.execute("""
    CREATE TRIGGER IF NOT EXISTS workflow_runs_runtime_receipt_binding_guard
    BEFORE UPDATE OF runtime_load_receipt_id ON workflow_runs
    WHEN NEW.runtime_load_receipt_id IS NOT NULL
      AND OLD.runtime_load_receipt_id IS NOT NEW.runtime_load_receipt_id
      AND NOT EXISTS (
        SELECT 1
        FROM runtime_load_receipts AS receipt
        WHERE receipt.receipt_id = NEW.runtime_load_receipt_id
          AND receipt.workflow_run_id = NEW.id
      )
    BEGIN
      SELECT RAISE(ABORT, 'runtime load receipt is missing or bound to another run');
    END
    """)
    db.commit()


def create_agent_session_tables(db):
    """Append task_009 run-scoped Session storage and binding guards."""

    create_runtime_plugin_tables(db)
    db.execute("""
    CREATE TABLE IF NOT EXISTS agent_sessions (
      agent_session_id TEXT PRIMARY KEY,
      workflow_run_id TEXT NOT NULL,
      runtime_load_receipt_id TEXT NOT NULL,
      runtime_environment_id TEXT NOT NULL,
      runtime_pool_id TEXT NOT NULL,
      distribution_mode TEXT NOT NULL CHECK(distribution_mode = 'local_persistent'),
      runtime_node_id TEXT NOT NULL,
      artifact_set_hash TEXT NOT NULL,
      policy_revision TEXT NOT NULL,
      deployment_tier TEXT NOT NULL CHECK(deployment_tier = 'local'),
      runtime_plugin_lock_id TEXT NOT NULL,
      runtime_plugin_lock_digest TEXT NOT NULL,
      settings_json TEXT NOT NULL,
      settings_hash TEXT NOT NULL,
      plugin_set_hash TEXT NOT NULL,
      session_request_key TEXT NOT NULL UNIQUE,
      attempt_number INTEGER NOT NULL CHECK(attempt_number >= 1),
      status TEXT NOT NULL CHECK(status IN ('creating', 'active', 'terminated', 'failed')),
      error_code TEXT,
      termination_reason_code TEXT,
      created_at DATETIME NOT NULL,
      started_at DATETIME,
      terminated_at DATETIME,
      lease_expires_at DATETIME,
      owner_token TEXT,
      remote_session_ref TEXT,
      UNIQUE(workflow_run_id, attempt_number),
      CHECK(runtime_pool_id = runtime_environment_id),
      FOREIGN KEY (workflow_run_id) REFERENCES workflow_runs(id) ON DELETE RESTRICT,
      FOREIGN KEY (runtime_load_receipt_id)
        REFERENCES runtime_load_receipts(receipt_id) ON DELETE RESTRICT,
      FOREIGN KEY (runtime_plugin_lock_id)
        REFERENCES deck_runtime_plugin_locks(id) ON DELETE RESTRICT
    )
    """)
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_agent_sessions_run "
        "ON agent_sessions(workflow_run_id, attempt_number)"
    )
    db.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_sessions_one_live_run "
        "ON agent_sessions(workflow_run_id) "
        "WHERE status IN ('creating', 'active')"
    )
    db.execute("""
    CREATE TRIGGER IF NOT EXISTS agent_sessions_immutable_binding
    BEFORE UPDATE ON agent_sessions
    WHEN OLD.agent_session_id IS NOT NEW.agent_session_id
      OR OLD.workflow_run_id IS NOT NEW.workflow_run_id
      OR OLD.runtime_load_receipt_id IS NOT NEW.runtime_load_receipt_id
      OR OLD.runtime_environment_id IS NOT NEW.runtime_environment_id
      OR OLD.runtime_pool_id IS NOT NEW.runtime_pool_id
      OR OLD.distribution_mode IS NOT NEW.distribution_mode
      OR OLD.runtime_node_id IS NOT NEW.runtime_node_id
      OR OLD.artifact_set_hash IS NOT NEW.artifact_set_hash
      OR OLD.policy_revision IS NOT NEW.policy_revision
      OR OLD.deployment_tier IS NOT NEW.deployment_tier
      OR OLD.runtime_plugin_lock_id IS NOT NEW.runtime_plugin_lock_id
      OR OLD.runtime_plugin_lock_digest IS NOT NEW.runtime_plugin_lock_digest
      OR OLD.settings_json IS NOT NEW.settings_json
      OR OLD.settings_hash IS NOT NEW.settings_hash
      OR OLD.plugin_set_hash IS NOT NEW.plugin_set_hash
      OR OLD.session_request_key IS NOT NEW.session_request_key
      OR OLD.attempt_number IS NOT NEW.attempt_number
      OR OLD.created_at IS NOT NEW.created_at
    BEGIN
      SELECT RAISE(ABORT, 'agent session binding is immutable');
    END
    """)
    db.execute("""
    CREATE TRIGGER IF NOT EXISTS agent_sessions_status_guard
    BEFORE UPDATE OF status ON agent_sessions
    WHEN OLD.status IS NOT NEW.status
      AND NOT (
        (OLD.status = 'creating' AND NEW.status IN ('active', 'failed'))
        OR (OLD.status = 'active' AND NEW.status IN ('terminated', 'failed'))
      )
    BEGIN
      SELECT RAISE(ABORT, 'agent session transition is not allowed');
    END
    """)
    db.execute("""
    CREATE TRIGGER IF NOT EXISTS agent_sessions_lifecycle_insert_guard
    BEFORE INSERT ON agent_sessions
    WHEN NEW.status != 'creating'
      OR NEW.started_at IS NOT NULL
      OR NEW.terminated_at IS NOT NULL
      OR NEW.error_code IS NOT NULL
      OR NEW.termination_reason_code IS NOT NULL
      OR NEW.lease_expires_at IS NULL
    BEGIN
      SELECT RAISE(ABORT, 'new agent session must start with a creating lease');
    END
    """)
    db.execute("""
    CREATE TRIGGER IF NOT EXISTS agent_sessions_lifecycle_update_guard
    BEFORE UPDATE ON agent_sessions
    WHEN (NEW.status = 'active' AND (
        NEW.started_at IS NULL OR NEW.terminated_at IS NOT NULL
        OR NEW.error_code IS NOT NULL OR NEW.termination_reason_code IS NOT NULL
      ))
      OR (NEW.status = 'terminated' AND (
        NEW.started_at IS NULL OR NEW.terminated_at IS NULL
        OR NEW.error_code IS NOT NULL OR NEW.termination_reason_code IS NULL
      ))
      OR (NEW.status = 'failed' AND (
        NEW.terminated_at IS NULL OR NEW.error_code IS NULL
        OR NEW.termination_reason_code IS NULL
      ))
    BEGIN
      SELECT RAISE(ABORT, 'agent session lifecycle fields are inconsistent');
    END
    """)
    db.execute("""
    CREATE TRIGGER IF NOT EXISTS workflow_runs_joint_session_binding_guard
    BEFORE UPDATE ON workflow_runs
    WHEN (NEW.runtime_load_receipt_id IS NULL) != (NEW.agent_session_id IS NULL)
      OR (
        OLD.runtime_load_receipt_id IS NULL
        AND OLD.agent_session_id IS NULL
        AND NEW.runtime_load_receipt_id IS NOT NULL
        AND NOT (OLD.status = 'queued' AND NEW.status = 'running')
      )
      OR (
        OLD.runtime_load_receipt_id IS NOT NULL
        AND (
          OLD.runtime_load_receipt_id IS NOT NEW.runtime_load_receipt_id
          OR OLD.agent_session_id IS NOT NEW.agent_session_id
        )
      )
      OR (
        NEW.status IN (
          'running', 'output_validating', 'pending_review', 'confirmed',
          'rejected', 'completed'
        )
        AND NEW.runtime_load_receipt_id IS NULL
      )
      OR (
        NEW.status IN ('preflight', 'queued')
        AND NEW.runtime_load_receipt_id IS NOT NULL
      )
      OR (
        NEW.agent_session_id IS NOT NULL
        AND (
          NEW.agent_session_id = NEW.source_voice_thread_id
          OR NEW.agent_session_id = NEW.source_message_id
        )
      )
      OR (
        NEW.agent_session_id IS NOT NULL
        AND OLD.agent_session_id IS NULL
        AND NOT EXISTS (
          SELECT 1 FROM agent_sessions AS session
          WHERE session.agent_session_id = NEW.agent_session_id
            AND session.workflow_run_id = NEW.id
            AND session.runtime_load_receipt_id = NEW.runtime_load_receipt_id
            AND session.runtime_plugin_lock_id = NEW.runtime_plugin_lock_id
            AND session.status = 'active'
        )
      )
    BEGIN
      SELECT RAISE(ABORT, 'workflow run receipt and session binding is invalid');
    END
    """)
    db.commit()


def create_claude_plugin_tables(db):
    """Shared Claude Code plugin installation storage (deck-integration-delta).

    These tables back the real-CLI plugin pipeline:

    - ``claude_plugin_installations``: shared, digest-pinned install records
      produced by real ``claude plugin install`` executions inside the
      server-managed runtime root (or server-declared platform-builtin
      sources).  A row only exists for successful installs (status ready);
      failures live only in ``claude_plugin_operations``.
    - ``claude_plugin_operations``: per-operation evidence pointers (argv,
      cwd, CLI version, exit code, evidence file path).
    - ``deck_claude_plugin_refs``: Deck → installation references.  Decks
      never store paths, settings JSON, workflows, or SDK plugin options.
    """

    db.execute("""
    CREATE TABLE IF NOT EXISTS claude_plugin_installations (
      id TEXT PRIMARY KEY,
      requested_package_spec TEXT NOT NULL,
      package_name TEXT NOT NULL,
      marketplace TEXT NOT NULL,
      requested_version TEXT,
      resolved_version TEXT NOT NULL,
      source_type TEXT NOT NULL
        CHECK(source_type IN ('claude-official', 'marketplace', 'github', 'platform-builtin')),
      artifact_digest TEXT NOT NULL,
      artifact_path TEXT NOT NULL,
      claude_cli_version TEXT NOT NULL,
      cli_git_commit_sha TEXT,
      manifest_json TEXT,
      component_inventory_json TEXT NOT NULL DEFAULT '{}',
      compatibility_json TEXT NOT NULL DEFAULT '{}',
      status TEXT NOT NULL DEFAULT 'installing'
        CHECK(status IN ('installing', 'ready', 'error', 'uninstalled')),
      operation_id TEXT NOT NULL,
      error_code TEXT,
      error_summary TEXT,
      file_count INTEGER NOT NULL DEFAULT 0,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      installed_at DATETIME,
      UNIQUE(package_name, marketplace, resolved_version, artifact_digest)
    )
    """)
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_claude_plugin_installations_status "
        "ON claude_plugin_installations(status)"
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_claude_plugin_installations_pkg "
        "ON claude_plugin_installations(package_name, marketplace)"
    )

    db.execute("""
    CREATE TABLE IF NOT EXISTS claude_plugin_operations (
      id TEXT PRIMARY KEY,
      operation_kind TEXT NOT NULL
        CHECK(operation_kind IN ('install', 'uninstall', 'validate', 'revalidate')),
      requested_package_spec TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'queued'
        CHECK(status IN ('queued', 'running', 'ready', 'error')),
      phase TEXT NOT NULL DEFAULT 'queued',
      progress INTEGER NOT NULL DEFAULT 0,
      message TEXT,
      executable TEXT,
      argv_json TEXT,
      cwd TEXT,
      cli_version TEXT,
      exit_code INTEGER,
      evidence_path TEXT,
      installation_id TEXT,
      error_code TEXT,
      error_summary TEXT,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      finished_at DATETIME
    )
    """)
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_claude_plugin_operations_status "
        "ON claude_plugin_operations(status, created_at)"
    )

    db.execute("""
    CREATE TABLE IF NOT EXISTS deck_claude_plugin_refs (
      deck_id TEXT NOT NULL,
      plugin_installation_id TEXT NOT NULL,
      package_spec TEXT NOT NULL,
      resolved_version TEXT NOT NULL,
      artifact_digest TEXT NOT NULL,
      enabled INTEGER NOT NULL DEFAULT 1,
      order_index INTEGER NOT NULL DEFAULT 0,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (deck_id, plugin_installation_id),
      FOREIGN KEY (deck_id) REFERENCES decks(id) ON DELETE RESTRICT,
      FOREIGN KEY (plugin_installation_id)
        REFERENCES claude_plugin_installations(id) ON DELETE RESTRICT
    )
    """)
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_deck_claude_plugin_refs_deck "
        "ON deck_claude_plugin_refs(deck_id, enabled, order_index)"
    )
    db.commit()


def drop_story_workspace_tables(db) -> None:
    """Drop legacy Story Workspace tables in an explicit SQLite test fixture."""

    tables = (
        "story_workspace_scene_characters",
        "story_workspace_story_characters",
        "story_workspace_scenes",
        "story_workspace_characters",
        "story_workspace_stories",
        "story_workspace_workspaces",
    )
    for table in tables:
        db.execute(f"DROP TABLE IF EXISTS {table}")
    db.commit()
